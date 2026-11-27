"""Deterministic interventions and two nomination tracks, without favored topics."""
import math
import re
from reference import fingerprint
from familylab.data import setting


def plan(stage, prompt_index, variants, seed, actor='familylab.actor', validation_limit=12, final_limit=6):
    from lfmfollow.prompts_v1 import partition
    return {'kind': 'adaptive_exploration_then_fresh_confirmation', 'stage_id': stage, 'seed': seed,
        'actor_module': actor, 'variants': variants, 'prompts': partition(prompt_index),
        'token_limits': {'discovery': 128, 'validation': 192, 'locked_test': 256, 'long': 384, 'replication': 256, 'random_controls': 256},
        'selection': {'validation_max': validation_limit, 'final_settings_max': final_limit,
            'discovery_queues': 'Eight consistent plus four rare interpretable conditions; at most two per component. Fixed-seed hash tie-breaks.',
            'final_queues': 'Four consistent plus two rare interpretable conditions. Rare conditions may be tested even when validation is too sparse to qualify.',
            'no_preferred_topics': True},
        'gate': {'change_min': 3, 'coherence_min': 3, 'heldout_matches_min': 8, 'long_matches_min': 4,
                 'replication_matches_min': 4, 'repetition_max': 2, 'collapse_max': 2,
                 'validation_matches_min': 4, 'validation_n': 8, 'both_reviewers_required': True},
        'budget_upper_bound_per_checkpoint': len(variants) * 16 + validation_limit * 8 + final_limit * 64,
        'scope': 'Shared prompt templates across partitions are disclosed. Exact prompt strings are disjoint from the parent, initial confirmation and other stages. '
        'These finite tasks do not establish out-of-distribution generalization. Separate raters see frozen descriptions without validation scores or notes. '
        'Task loss, baseline defects, repetition, collapse, rare effects and random matches are separate from the stability decision.'}


def variant(coordinate, value, operator='clamp', timing='all'):
    match = re.fullmatch(r'L(\d+)-N(\d+)', coordinate)
    assert match and int(match[1]) < 16 and int(match[2]) < 4608
    assert operator in ('clamp', 'add', 'scale')
    label = setting(value)
    key = label if operator == 'clamp' and timing == 'all' else operator + '__' + timing + '__' + label
    return {'component': coordinate, 'id': key, 'dose': label, 'timing': timing,
            'sites': [{'layer': int(match[1]), 'neuron': int(match[2]), 'operator': operator, 'value': value}],
            'description': f'{operator}; {timing}; {coordinate}; value {value:g}',
            'dose_unit': 'Activation multiplier' if operator == 'scale' else 'Original-checkpoint maximum absolute activation units'}


def pair_variant(first, second, level, arm):
    assert arm in ('A', 'B', 'AB') and first['component'] != second['component']
    sites = []
    for selected, record in [('A', first), ('B', second)]:
        if selected in arm:
            sites.append({**record['sites'][0], 'value': record['sites'][0]['value'] * level, 'operator': 'clamp'})
    component = 'PAIR-' + first['component'] + '-' + second['component']
    return {'component': component, 'id': 'pair__' + arm + '__' + setting(level), 'dose': setting(level),
            'timing': 'all', 'sites': sites, 'pair_members': [first['component'], second['component']],
            'arm': arm, 'level': level, 'description': f'Pair {first["component"]} / {second["component"]}; arm {arm}; dose factor {level:g}',
            'dose_unit': 'Multiplier of the two individually recorded clamp targets'}


def nominate(analyses, variants, consistent=8, rare=4, seed=20261127, max_per_component=2):
    definitions = {(v['component'], v['id']): v for v in variants}
    rows = []
    for checkpoint, components in analyses.items():
        for component, effects in components.items():
            for key, source in effects.items():
                effect = source['effect']; n = source['n']; hits = source['hits']
                if (component, key) not in definitions or not n or not hits or effect['change_strength'] < 3:
                    continue
                clean = set(effect['matching_ids']) - set(effect['repetition_ids']) - set(effect['collapse_ids'])
                rows.append({'component': component, 'condition': key, 'checkpoint': checkpoint,
                    'change': effect['change_strength'], 'coherence': effect['coherence'], 'hits': hits, 'n': n,
                    'clean_matches': len(clean), 'review_input_sha256': source['review_input_sha256'],
                    'tie_key': fingerprint({'seed': seed, 'component': component, 'condition': key})})
    selected, used, per_component = [], set(), {}
    tracks = [('consistency', consistent), ('rare_interpretable', rare)]
    for track, count in tracks:
        if count <= 0:
            continue
        pool = [r for r in rows if r['coherence'] >= 3 and r['hits'] >= math.ceil(r['n'] / 2)] if track == 'consistency' else [r for r in rows
                if r['coherence'] >= 2 and 0 < r['hits'] <= r['n'] / 2 and r['clean_matches'] > 0]
        pool.sort(key=lambda r: (-r['change'], -(r['hits']/r['n']) if track == 'consistency' else r['hits']/r['n'],
                                  -r['coherence'], r['tie_key']))
        added = 0
        for row in pool:
            key = row['component'], row['condition']
            if key in used or per_component.get(row['component'], 0) >= max_per_component:
                continue
            selected.append({**definitions[key], 'selection_track': track, 'nomination': row})
            used.add(key); per_component[row['component']] = per_component.get(row['component'], 0) + 1
            added += 1
            if added == count:
                break
    return selected, rows
