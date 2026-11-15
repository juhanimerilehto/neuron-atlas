"""Check tensor identities and inventory differences before interpreting a community derivative."""
import json
from pathlib import Path
import sys

from safetensors import safe_open
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from reference import write_json
from pairedllama import data

OUT = ROOT / 'campaigns' / data.CAMPAIGN


def main():
    torch.set_num_threads(4)
    models = {name: json.loads((OUT / name / 'model.json').read_text(encoding='utf-8')) for name in data.MODELS}
    changed, unchanged, parameters = [], [], 0
    with safe_open(models['original']['weight_path'], framework='pt', device='cpu') as a, safe_open(models['abliterated']['weight_path'], framework='pt', device='cpu') as b:
        assert set(a.keys()) == set(b.keys()), 'Tensor names differ'
        for key in a.keys():
            x, y = a.get_tensor(key), b.get_tensor(key)
            assert x.shape == y.shape and x.dtype == y.dtype, key
            parameters += x.numel()
            if torch.equal(x, y):
                unchanged.append(key)
            else:
                delta = y.float() - x.float()
                changed.append({'tensor': key, 'shape': list(x.shape), 'max_abs_delta': delta.abs().max().item(),
                                'delta_l2': delta.norm().item(), 'original_l2': x.float().norm().item()})
    expected = ('embed_tokens.weight', 'self_attn.o_proj.weight', 'mlp.down_proj.weight', 'lm_head.weight')
    unexpected = [x['tensor'] for x in changed if not x['tensor'].endswith(expected)]
    result = {'same_tensor_names_shapes_dtypes': True, 'parameters_in_stored_tensors': parameters,
              'changed': changed, 'unchanged': unchanged, 'unexpected_changed_tensors': unexpected,
              'scope': 'Exact tensor comparisons and difference norms. This does not prove a rank-one edit or validate upstream behavioral claims.'}
    assert changed and not unexpected, 'Changes extend beyond the documented residual-writing tensor classes'
    write_json(OUT / 'weight-comparison.json', result)
    print(json.dumps({'changed_tensors': len(changed), 'unchanged_tensors': len(unchanged),
                      'unexpected_changed_tensors': unexpected, 'parameters': parameters}), flush=True)


if __name__ == '__main__':
    main()
