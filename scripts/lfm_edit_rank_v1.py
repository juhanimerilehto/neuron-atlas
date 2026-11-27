"""Post hoc CPU-only rank/projection diagnostics of existing checkpoint differences."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import torch
from safetensors import safe_open

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
PARENT = ROOT / 'campaigns/paired-lfm25-350m-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()


def component(matrix, seed):
    generator = torch.Generator().manual_seed(seed)
    u = torch.randn(matrix.shape[0], generator=generator, dtype=torch.float64)
    u /= u.norm()
    converged = False
    for iteration in range(32):
        v = matrix.T @ u
        v /= v.norm()
        following = matrix @ v
        following /= following.norm()
        change = min(float((following-u).norm()), float((following+u).norm()))
        u = following
        if change < 1e-12:
            converged = True
            break
    sigma = (matrix.T @ u).norm()
    fraction = float(sigma.square()/matrix.square().sum())
    assert -1e-12 <= fraction <= 1+1e-12
    return u, {'largest_component_energy_fraction_estimate': min(1., max(0.,fraction)),
               'singular_value_estimate':float(sigma), 'iterations':iteration+1, 'converged':converged}


def projection_fit(original, delta, direction):
    prediction = -direction[:,None] * (direction @ original)[None,:]
    multiplier = (delta*prediction).sum()/prediction.square().sum()
    return {'fitted_projection_multiplier':float(multiplier),
        'relative_error_with_fitted_multiplier':float((delta-multiplier*prediction).norm()/delta.norm()),
        'relative_error_at_unit_multiplier':float((delta-prediction).norm()/delta.norm())}


@torch.inference_mode()
def main():
    torch.set_num_threads(2)
    target = PROGRAM / 'posthoc-edit-rank-v1.json'
    if target.exists():
        assert read(target)['analysis_source_sha256'] == digest(Path(__file__))
        print('Existing checkpoint-rank diagnosis retained.'); return
    geometry = PROGRAM / 'posthoc-weight-geometry-v2.json'
    source = read(geometry)
    changed = [row for row in source['named_tensor_comparison'] if not row['exact_equal']]
    assert len(changed) == 19
    paths = {name:Path(read(PARENT/name/'model.json')['snapshot'])/'model.safetensors' for name in ('original','abliterated')}
    for name,path in paths.items(): assert digest(path) == source['models'][name]['weights_sha256']
    rows, vectors = [], []
    with safe_open(paths['original'], framework='pt', device='cpu') as original, safe_open(paths['abliterated'], framework='pt', device='cpu') as edited:
        for index, item in enumerate(changed):
            key = item['tensor']
            a, b = original.get_tensor(key).double(), edited.get_tensor(key).double()
            delta = b-a
            assert delta.ndim == 2 and delta.shape[0] == 1024 and delta.norm()>0
            u, first = component(delta, 2026112707+index)
            other_u, second = component(delta, 2026112807+index)
            rows.append({'tensor':key,'shape':list(delta.shape), **first,
                'independent_start_energy_difference':abs(first['largest_component_energy_fraction_estimate']-second['largest_component_energy_fraction_estimate']),
                'independent_start_absolute_direction_cosine':min(1.,abs(float(u@other_u))),
                'own_direction_projection_fit':projection_fit(a,delta,u)})
            vectors.append(u)
        common = vectors[0]
        for row,u in zip(rows,vectors):
            a = original.get_tensor(row['tensor']).double()
            delta = edited.get_tensor(row['tensor']).double()-a
            row['absolute_cosine_with_reference_direction'] = min(1.,abs(float(common@u)))
            row['reference_direction_projection_fit'] = projection_fit(a,delta,common)
    stack = torch.stack(vectors)
    similarity = (stack @ stack.T).abs().clamp(0,1)
    off_diagonal = similarity[torch.triu(torch.ones_like(similarity,dtype=torch.bool),diagonal=1)]
    result = {'analysis_kind':'Post hoc geometry of the complete set of changed named tensors; no inference or weight modification.',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'analysis_source_sha256':digest(Path(__file__)),
        'geometry_input_sha256':digest(geometry),'models':source['models'],'runtime':{'torch':torch.__version__,'device':'cpu','threads':2},
        'method':'FP64 alternating power iteration, two deterministic independent starts per changed matrix, at most 32 iterations and 1e-12 sign-invariant convergence tolerance. Energy fraction is sigma_estimate squared divided by squared Frobenius norm. Fits compare delta to -alpha*u*(u.T*W_original).',
        'reference_tensor':rows[0]['tensor'],'tensor_order':[r['tensor'] for r in rows], 'per_tensor':rows,
        'absolute_direction_cosines':similarity.tolist(),
        'summary':{'changed_tensors':len(rows),'minimum_rank_one_energy_fraction_estimate':min(r['largest_component_energy_fraction_estimate'] for r in rows),
            'maximum_rank_one_energy_fraction_estimate':max(r['largest_component_energy_fraction_estimate'] for r in rows),
            'minimum_pairwise_absolute_direction_cosine':float(off_diagonal.min()),
            'median_pairwise_absolute_direction_cosine':float(off_diagonal.median()),
            'maximum_independent_start_energy_difference':max(r['independent_start_energy_difference'] for r in rows)},
        'limitations':'A near rank-one checkpoint difference is not proof of a refusal direction, a causal behavioral mechanism, harmlessness or semantic equivalence. Quantized weight differences need not have exact rank one. Power iteration gives an approximation, not a full singular-value spectrum. Complete unit vectors and edited weights are not exported.',
        'reference':'https://arxiv.org/html/2406.11717'}
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps(result['summary']))


if __name__ == '__main__': main()
