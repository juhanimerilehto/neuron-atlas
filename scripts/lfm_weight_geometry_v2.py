"""Post hoc CPU-only weight geometry; no generation, activation edit or new review request."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import torch
from safetensors import safe_open
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
PARENT = ROOT / 'campaigns/paired-lfm25-350m-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def cosine(a, b):
    if torch.equal(a,b): return 1.0
    return float(torch.nn.functional.cosine_similarity(a.double().reshape(1,-1), b.double().reshape(1,-1)).clamp(-1,1).item())


def tokens(scores, tokenizer, largest):
    values, ids = torch.topk(scores, 16, largest=largest)
    return [{'token_id': int(i), 'token': tokenizer.id_to_token(int(i)),
             'decoded': tokenizer.decode([int(i)], skip_special_tokens=False), 'score': float(v)}
            for i, v in zip(ids, values)]


@torch.inference_mode()
def main():
    torch.set_num_threads(2)
    target = PROGRAM / 'posthoc-weight-geometry-v2.json'
    if target.exists():
        saved = read(target)
        assert saved['analysis_source_sha256'] == digest(Path(__file__))
        print('Existing post hoc weight comparison retained.'); return
    models = {name: read(PARENT / name / 'model.json') for name in ('original', 'abliterated')}
    frozen = read(PROGRAM / 'stages/01-confirm-p9/manifest.json')['models']
    paths = {name: Path(model['snapshot']) / 'model.safetensors' for name, model in models.items()}
    for name, path in paths.items():
        assert digest(path) == frozen[name]['files']['model.safetensors']['sha256']
    tokenizer = Tokenizer.from_file(str(Path(models['original']['snapshot']) / 'tokenizer.json'))
    selected = [(2,3420), (2,3030), (3,2589), (5,4206), (10,4198), (5,3454), (0,3732), (0,3694)]
    manifest = {'analysis_kind': 'Post hoc descriptive weight comparison, separate from the five intervention studies.',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'analysis_source_sha256': digest(Path(__file__)),
        'models': {name: {'repository': model['repository'], 'revision': model['revision'],
            'weights_sha256': frozen[name]['files']['model.safetensors']['sha256']} for name, model in models.items()},
        'runtime': {'torch': torch.__version__, 'device': 'cpu', 'threads': 2},
        'scope': 'No new inference configurations or reviewer requests. The selected coordinates are the existing dose-study pool, not selected by readout words. Four seeded random real coordinates per selected layer provide descriptive reference readouts; they are not the intervention campaign random-direction controls.',
        'readout_definition': 'For each checkpoint separately, score(token,j)=embedding[token] dot normalize(W2[:,j]). Tied embeddings are required. Positive and negative lists are scores along the positive and negative output direction, not predictions at a requested dose.',
        'limitations': 'These static scores omit normalization, the current residual state, the gate and input activations, and all subsequent attention/convolution/MLP processing. They are not causal neuron labels, calibrated token probabilities, a trained tuned lens or a substitute for measured generation. Weight cosine similarity does not establish functional equivalence.',
        'reference': 'https://arxiv.org/abs/2303.08112', 'layers': [], 'selected_coordinates': [], 'reference_coordinates': [],
        'versioned_reason': 'The retained first descriptive pass used FP32 cosine arithmetic and produced small values above one. This pass uses bounded FP64 cosines, explicit exact equality, and a complete named-tensor comparison.',
        'predecessor_sha256': digest(PROGRAM / 'posthoc-weight-geometry.json')}
    with safe_open(paths['original'], framework='pt', device='cpu') as original, safe_open(paths['abliterated'], framework='pt', device='cpu') as edited:
        archives = {'original': original, 'abliterated': edited}
        assert set(original.keys()) == set(edited.keys())
        tensor_comparison = []
        for key in original.keys():
            a, b = original.get_tensor(key), edited.get_tensor(key)
            assert a.shape == b.shape and a.dtype == b.dtype
            equal = torch.equal(a,b)
            tensor_comparison.append({'tensor': key, 'shape': list(a.shape), 'dtype': str(a.dtype), 'exact_equal': equal,
                'changed_elements': 0 if equal else int((a != b).count_nonzero()),
                'relative_frobenius_change': 0.0 if equal else float((b.float()-a.float()).norm()/a.float().norm())})
        manifest['named_tensor_comparison'] = tensor_comparison
        embedding = {}
        for name, archive in archives.items():
            config = read(Path(models[name]['snapshot']) / 'config.json')
            assert config.get('tie_word_embeddings', config.get('tie_embedding')) is True and 'lm_head.weight' not in archive.keys()
            embedding[name] = archive.get_tensor('model.embed_tokens.weight').float()
        a, b = embedding['original'], embedding['abliterated']
        manifest['embedding_relative_frobenius_change'] = float((b-a).norm()/a.norm())
        generator = torch.Generator().manual_seed(2026112706)
        for layer in range(16):
            key = f'model.layers.{layer}.feed_forward.w2.weight'
            wa, wb = original.get_tensor(key).float(), edited.get_tensor(key).float()
            norms_a, norms_b = wa.norm(dim=0), wb.norm(dim=0)
            exact_columns = (wa == wb).all(dim=0)
            cosines = torch.nn.functional.cosine_similarity(wa.double(),wb.double(),dim=0).clamp(-1,1)
            cosines[exact_columns] = 1.0
            manifest['layers'].append({'layer': layer, 'shape': list(wa.shape),
                'w2_exact_equal': bool(torch.equal(wa,wb)), 'exact_equal_columns': int(exact_columns.sum()),
                'relative_frobenius_change_w2': float((wb-wa).norm()/wa.norm()),
                'column_cosine_min': float(cosines.min()), 'column_cosine_median': float(cosines.median()),
                'column_cosine_max': float(cosines.max())})
            chosen = [neuron for which,neuron in selected if which == layer]
            if not chosen: continue
            references = [int(n) for n in torch.randperm(wa.shape[1], generator=generator).tolist() if n not in chosen][:4]
            neurons = chosen + references
            matrices = {'original': wa, 'abliterated': wb}
            scores = {name: embedding[name] @ torch.nn.functional.normalize(matrix[:,neurons], dim=0) for name,matrix in matrices.items()}
            for index, neuron in enumerate(neurons):
                item = {'coordinate': f'L{layer}-N{neuron}', 'output_column_cosine': float(cosines[neuron]),
                        'output_column_exact_equal': bool(exact_columns[neuron]),
                        'output_norm_ratio_edited_over_original': float(norms_b[neuron]/norms_a[neuron]), 'readouts': {}}
                for gate in ('w1', 'w3'):
                    gate_key = f'model.layers.{layer}.feed_forward.{gate}.weight'
                    row_a = original.get_slice(gate_key)[neuron:neuron+1].float()
                    row_b = edited.get_slice(gate_key)[neuron:neuron+1].float()
                    item[gate + '_input_row_cosine'] = cosine(row_a, row_b)
                    item[gate + '_input_row_exact_equal'] = bool(torch.equal(row_a,row_b))
                for name in archives:
                    own_scores = scores[name][:,index]
                    item['readouts'][name] = {'positive': tokens(own_scores, tokenizer, True), 'negative': tokens(own_scores, tokenizer, False)}
                item['positive_top16_token_overlap'] = len({r['token_id'] for r in item['readouts']['original']['positive']} &
                    {r['token_id'] for r in item['readouts']['abliterated']['positive']})
                manifest['selected_coordinates' if neuron in chosen else 'reference_coordinates'].append(item)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    first = next(r for r in manifest['selected_coordinates'] if r['coordinate']=='L2-N3420')
    print(json.dumps({'output': str(target.relative_to(ROOT)), 'selected_coordinates': len(manifest['selected_coordinates']),
        'reference_coordinates': len(manifest['reference_coordinates']), 'L2-N3420': {k:v for k,v in first.items() if k!='readouts'},
        'embedding_relative_frobenius_change': manifest['embedding_relative_frobenius_change']}))


if __name__ == '__main__': main()
