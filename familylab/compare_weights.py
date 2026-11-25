"""Exact CPU tensor inventory; verify real MLP width instead of raw config labels."""
import json
from pathlib import Path
import torch
from safetensors import safe_open
from familylab import data
from worker.reference import write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'campaigns' / data.CAMPAIGN


def main():
    torch.set_num_threads(4)
    models = {name: json.loads((OUT / name / 'model.json').read_text()) for name in data.MODELS}
    changed, unchanged, dimensions = [], [], []
    with safe_open(models['original']['weight_path'], framework='pt', device='cpu') as original:
        keys = list(original.keys())
        for layer in range(data.LAYERS):
            key = f'model.layers.{layer}.' + ('feed_forward.w2.weight' if data.FAMILY == 'lfm' else 'shared_mlp.output_linear.weight')
            shape = original.get_slice(key).get_shape()
            assert shape[1] == data.WIDTH
            dimensions.append({'layer': layer, 'output_projection': key, 'shape': shape})
        if 'abliterated' in models:
            with safe_open(models['abliterated']['weight_path'], framework='pt', device='cpu') as edited:
                assert set(keys) == set(edited.keys())
                for key in keys:
                    a, b = original.get_tensor(key), edited.get_tensor(key)
                    assert a.shape == b.shape and a.dtype == b.dtype
                    if torch.equal(a, b):
                        unchanged.append(key)
                    else:
                        delta = b.float() - a.float()
                        changed.append({'tensor': key, 'shape': list(a.shape), 'delta_l2': delta.norm().item(), 'max_abs_delta': delta.abs().max().item()})
            allowed = ('feed_forward.w2.weight', 'self_attn.out_proj.weight', 'conv.out_proj.weight', 'embed_tokens.weight', 'lm_head.weight')
            unexpected = [row['tensor'] for row in changed if not row['tensor'].endswith(allowed)]
            if unexpected:
                write_json(OUT / 'weight-comparison-preflight.json', {'changed': changed, 'unchanged': unchanged, 'unexpected': unexpected})
            assert changed and not unexpected, 'Unexpected tensor edits require provenance review: ' + repr(unexpected)
    result = {'same_tensor_names_shapes_dtypes': True, 'changed': changed, 'unchanged': unchanged,
        'mlp_geometry': dimensions, 'paired_comparison': len(models) > 1,
        'scope': 'Exact CPU weight inventory and actual gated-MLP output shapes. No behavioral or low-rank claim is implied.'}
    write_json(OUT / 'weight-comparison.json', result)
    print(json.dumps({'changed': len(changed), 'unchanged': len(unchanged), 'layers': data.LAYERS, 'width': data.WIDTH}), flush=True)


if __name__ == '__main__':
    main()
