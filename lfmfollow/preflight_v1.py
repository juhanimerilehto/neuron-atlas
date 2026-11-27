"""Real native GPU checks for the fixed prospective +9x confirmation."""
import gc
from pathlib import Path
import torch
from tokenizers import Tokenizer
from familylab import campaign as legacy
from familylab.preflight import load
from lfmfollow.core_v1 import PARENT, digest, read
from lfmfollow.confirmation_v1 import STAGE, TEST, LONG, REPLICATION
from reference import write_json


@torch.inference_mode()
def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    target = STAGE / 'preflight.json'
    if target.exists():
        report = read(target)
        assert report['passed'] and report['source_sha256'] == digest(Path(__file__))
        print('Saved preflight retained.', flush=True)
        return
    assert not (STAGE / 'manifest.json').exists()
    legacy.prepare()
    torch.set_num_threads(4); torch.backends.cuda.matmul.allow_tf32 = False
    results = {}
    for name in ('original', 'abliterated'):
        info = read(PARENT / name / 'model.json')
        assert digest(info['weight_path']) == info['files']['model.safetensors']['sha256']
        _, worker = load(name)
        worker.cal = read(PARENT / name / 'calibration.json')
        backend = Tokenizer.from_file(str(Path(info['snapshot']) / 'tokenizer.json'))
        assert backend.get_vocab(with_added_tokens=True) == worker.tok.get_vocab()
        for prompt in TEST + LONG + REPLICATION:
            rendered = worker.tok.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=False,
                add_generation_prompt=True, enable_thinking=False, thinking=False)
            assert backend.encode(rendered, add_special_tokens=False).ids == worker.encode(prompt).input_ids[0].tolist()
        prompt = 'Explain the everyday purpose of a kitchen timer.'
        conformance = worker.conformance(prompt, 2, 3420)
        assert conformance['passed'], conformance
        cfg = {'prompt': prompt, 'layer': 2, 'neuron': 3420, 'condition': 'positive', 'factor': 9., 'max_tokens': 12}
        encoded = worker.encode(prompt)
        projection = worker.layers[2].mlp.down_proj
        scalar = torch.tensor(9 * worker.cal['2']['activation_abs_max'][3420], dtype=projection.weight.dtype, device=worker.device)
        def manual(module, args):
            value = args[0].clone(); value[:, :, 3420] = scalar; return (value,)
        handle = projection.register_forward_pre_hook(manual)
        try:
            expected = worker.model(**encoded, use_cache=False, logits_to_keep=1).logits.float()
        finally:
            handle.remove()
        with worker.hook([cfg]):
            actual = worker.model(**encoded, use_cache=False, logits_to_keep=1).logits.float()
        error = (expected - actual).abs().max().item()
        assert error == 0., error
        generations = worker.generate([{**cfg, 'condition': 'baseline'}, cfg])
        assert generations[0]['token_ids'] == generations[0]['batch_baseline']['token_ids']
        assert generations[1]['intervention']['target_activation'] == scalar.float().item()
        assert generations[1]['intervention']['hook_steps'] > 1
        results[name] = {'passed': True, 'weight_sha256': info['files']['model.safetensors']['sha256'],
            'conformance': conformance, 'manual_p9_logit_error': error,
            'untouched_row_matches_anchor': True, 'fresh_prompt_tokenizations_checked': 32,
            'bf16_target': scalar.float().item(), 'peak_cuda_bytes': torch.cuda.max_memory_allocated()}
        print(name + ' preflight passed', flush=True)
        del worker; gc.collect(); torch.cuda.empty_cache()
    write_json(target, {'passed': True, 'models': results, 'source_sha256': digest(Path(__file__))})


if __name__ == '__main__':
    main()
