"""Bounded factorial pair observations with individual arms and matched random controls."""
import itertools
import numpy as np
from lfmfollow.core_v1 import ROOT, PROGRAM, PARENT, MODELS, read, digest
from lfmfollow.design_v1 import variant, pair_variant, plan, nominate


def build():
    pool, provenance = [], {}
    for stage in ('02-dose-response', '03-missed-candidates'):
        path = PROGRAM / 'stages' / stage / 'frozen-finalists.json'; provenance[stage] = digest(path)
        pool += read(path)['variants']
    pool.sort(key=lambda v: (-v['nomination']['change'], -v['nomination']['hits']/v['nomination']['n'],
                            -v['nomination']['coherence'], v['nomination']['tie_key']))
    fallback = [variant('L2-N3420', 9), variant('L2-N3030', -15), variant('L3-N2589', 9),
                variant('L5-N4206', 15), variant('L10-N4198', 3), variant('L5-N3454', -8),
                variant('L1-N0', 4), variant('L8-N0', -4)]
    geometry = PROGRAM / 'posthoc-weight-geometry-v2.json'
    edited_layers = {row['layer'] for row in read(geometry)['layers'] if not row['w2_exact_equal']}
    unique, seen = [variant('L2-N3420', 9)], {'L2-N3420'}
    late = [v for v in pool if v['sites'][0]['layer'] in edited_layers]
    late += [variant('L10-N4198', 3), variant('L14-N1700', -3)]
    for v in late:
        if v['component'] in seen: continue
        assert v['sites'][0]['layer'] in edited_layers
        unique.append(v); seen.add(v['component'])
        if len(unique) == 3: break
    assert len(unique) == 3
    for v in pool + fallback:
        if v['component'] not in seen:
            unique.append(v); seen.add(v['component'])
        if len(unique) == 8:
            break
    combinations = list(itertools.combinations(unique, 2)); rng = np.random.default_rng(2026112705)
    late_pair = next(i for i,(a,b) in enumerate(combinations) if a['component']==unique[1]['component'] and b['component']==unique[2]['component'])
    remainder = [i for i in range(len(combinations)) if i != late_pair]
    indices = sorted([late_pair, *rng.choice(remainder, min(15, len(remainder)), replace=False).tolist()])
    selected = [combinations[i] for i in indices]
    variants = [pair_variant(a, b, level, arm) for a, b in selected for level in (.5, 1., 1.5, 2.) for arm in ('A', 'B', 'AB')]
    result = plan('05-neuron-pairs', 3, variants, 2026112705, 'lfmfollow.timed_actor_v1', validation_limit=24, final_limit=18)
    result['candidate_provenance'] = {'source_selection_sha256': provenance, 'pool': unique,
        'sampled_pair_indices': indices, 'pair_frame_n': len(combinations),
        'edited_w2_layers': sorted(edited_layers), 'reserved_late_pair_index': late_pair,
        'rule': 'Force L2 N3420 +9x and two coordinates from layers with edited W2; fill by validation nominations. Reserve their late/late pair, then sample fifteen other pairs with the fixed seed. Parent-validation L10 N4198 +3 and L14 N1700 -3 may backfill; they are not claimed stable.',
        'fallback_scope': 'L1 N0 and L8 N0 are deterministic uncharacterized backfills, not claimed discoveries.'}
    result['external_input_sha256'] = {path.relative_to(ROOT).as_posix(): digest(path) for path in
        [geometry, PROGRAM / 'adaptive-design-late-region-v1.json', *[PARENT / 'reviews/validation' / (cid + '.json') for cid in ('L10-N4198','L14-N1700')]]}
    result['selection']['discovery_queues'] = 'Nominate six consistent plus two rare AB conditions, at most one level per pair; validate both single arms at the same level.'
    result['selection']['final_queues'] = 'Nominate four consistent plus two rare AB conditions, at most one level per pair; test both single arms at the same level.'
    result['factorial_interpretation'] = ('All three final arms are assessed against the frozen AB description, without earlier scores. Only AB is eligible as a pair discovery; single arms are controls. '
        'AB-versus-single differences alone are not evidence of synergy because perturbation magnitudes differ. Four random controls match aggregate within-projection write magnitude; local norms are not net cross-layer norms.')
    return result


def expand(analyses, variants, consistent, rare, seed):
    ab = [v for v in variants if v['arm'] == 'AB']
    selected, ranking = nominate(analyses, ab, consistent, rare, seed, max_per_component=1)
    expanded = []
    for v in selected:
        for arm in ('A', 'B', 'AB'):
            own = next(r for r in variants if r['component'] == v['component'] and r['level'] == v['level'] and r['arm'] == arm)
            expanded.append({**own, 'selection_track': v['selection_track'] if arm == 'AB' else 'factorial_control',
                'nomination': v['nomination'], 'factorial_description_condition': v['id']})
    return expanded, ranking


def select_validation(analyses, variants):
    return expand(analyses, variants, 6, 2, 2026112705)


def select_final(analyses, variants):
    return expand(analyses, variants, 4, 2, 2026112706)


def freeze_hypotheses(finalists, validation):
    result = {name: {} for name in MODELS}
    for v in finalists:
        ab = v['factorial_description_condition']; component = v['component']
        fallback = next((validation[name].get(component, {}).get(ab) for name in MODELS
            if validation[name].get(component, {}).get(ab, {}).get('effect', {}).get('label')), None)
        assert fallback
        for name in MODELS:
            own = validation[name].get(component, {}).get(ab)
            effect = own['effect'] if own and own['effect']['label'] else fallback['effect']
            result[name].setdefault(component, []).append({'condition': v['id'], 'label': effect['label']})
    return result
