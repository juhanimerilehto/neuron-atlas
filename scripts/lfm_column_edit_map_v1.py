"""CPU-only post hoc column-edit geometry; a future sampling frame, not a behavior screen."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import torch
from safetensors import safe_open

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT/'campaigns/lfm-depth-20261127-v1'
PARENT = ROOT/'campaigns/paired-lfm25-350m-v1'
QUANTILES = (0., .01, .1, .25, .5, .75, .9, .99, 1.)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()


def quantiles(values):
    result = torch.quantile(values, torch.tensor(QUANTILES,dtype=values.dtype))
    return {str(q): float(v) for q,v in zip(QUANTILES,result)}


@torch.inference_mode()
def main():
    torch.set_num_threads(2)
    target = PROGRAM/'posthoc-column-edit-map-v1.json'
    if target.exists():
        assert read(target)['analysis_source_sha256'] == digest(Path(__file__))
        print('Existing column geometry retained.'); return
    models = {n:read(PARENT/n/'model.json') for n in ('original','abliterated')}
    pinned = read(PROGRAM/'stages/01-confirm-p9/manifest.json')['models']
    paths = {n:Path(m['snapshot'])/'model.safetensors' for n,m in models.items()}
    for n,path in paths.items(): assert digest(path) == pinned[n]['files']['model.safetensors']['sha256']
    geometry = read(PROGRAM/'posthoc-weight-geometry-v2.json')
    stage_path = PROGRAM/'stages/04-timing-operators/manifest.json'
    stage = read(stage_path)
    sites = {(s['layer'],s['neuron']) for v in stage['protocol']['variants'] for s in v['sites']}
    layers, selected = [], []
    with safe_open(paths['original'],framework='pt',device='cpu') as first, safe_open(paths['abliterated'],framework='pt',device='cpu') as second:
        for layer in range(16):
            key = f'model.layers.{layer}.feed_forward.w2.weight'
            a,b = first.get_tensor(key).double(), second.get_tensor(key).double()
            assert a.shape == b.shape == (1024,4608)
            na,nb = a.norm(dim=0), b.norm(dim=0)
            assert bool((na>0).all()) and bool((nb>0).all())
            equal = (a==b).all(dim=0)
            cosines = ((a*b).sum(dim=0)/(na*nb)).clamp(-1,1)
            cosines[equal] = 1.
            angles = torch.acos(cosines)*180/math.pi
            relative_delta = (b-a).norm(dim=0)/na
            norm_ratio = nb/na
            prior = geometry['layers'][layer]
            assert int(equal.sum()) == prior['exact_equal_columns']
            assert abs(float(cosines.min())-prior['column_cosine_min']) < 1e-12
            def record(n):
                return {'coordinate':f'L{layer}-N{n}','neuron':n,'exact_equal':bool(equal[n]),
                    'column_cosine':float(cosines[n]),'angle_degrees':float(angles[n]),
                    'relative_column_l2_change':float(relative_delta[n]),'norm_ratio_edited_over_original':float(norm_ratio[n])}
            ranking = sorted(range(4608),key=lambda n:(float(cosines[n]),n))
            layers.append({'layer':layer,'columns':4608,'exact_equal_columns':int(equal.sum()),
                'angle_degrees_quantiles':quantiles(angles),'relative_column_l2_change_quantiles':quantiles(relative_delta),
                'norm_ratio_quantiles':quantiles(norm_ratio),
                'most_rotated': [record(n) for n in ranking[:16]],
                'least_rotated': [record(n) for n in sorted(range(4608),key=lambda n:(-float(cosines[n]),n))[:16]]})
            selected.extend(record(n) for l,n in sorted(sites) if l==layer)
    result = {'analysis_kind':'Post hoc geometric coverage and future sampling frame; not a behavioral finding',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'analysis_source_sha256':digest(Path(__file__)),
        'geometry_input_sha256':digest(PROGRAM/'posthoc-weight-geometry-v2.json'),
        'already_frozen_timing_manifest_sha256':digest(stage_path),
        'models':{n:{'repository':m['repository'],'revision':m['revision'],'weights_sha256':pinned[n]['files']['model.safetensors']['sha256']} for n,m in models.items()},
        'runtime':{'torch':torch.__version__,'device':'cpu','threads':2,'arithmetic':'float64'},
        'quantiles':'Linear interpolation at quantiles 0, .01, .1, .25, .5, .75, .9, .99, 1. Exact equal columns have angle zero.',
        'columns':sum(l['columns'] for l in layers),'changed_columns':sum(l['columns']-l['exact_equal_columns'] for l in layers),
        'layers':layers,'already_selected_timing_coordinates':selected,
        'limitations':'Angles and relative column norms do not measure behavioral or refusal effects. Input activations and downstream processing also matter. Top/least-rotated lists are deterministic geometric selections, not uniformly sampled controls. This analysis was created after the timing study froze; it does not change that study or select any new generation jobs. No model weights are edited and no inference or reviewer requests are issued.'}
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'columns':result['columns'],'changed_columns':result['changed_columns'],
        'late_layer_angle_medians':{str(l['layer']):l['angle_degrees_quantiles']['0.5'] for l in layers if l['layer']>=10},
        'selected_timing_coordinates':selected,'measured_jobs_created':0}))


if __name__ == '__main__': main()
