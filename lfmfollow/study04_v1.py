"""Operator and timing profiles selected from previous validation, not their test verdicts."""
from lfmfollow.core_v1 import PROGRAM, read, digest
from lfmfollow.design_v1 import variant, plan, nominate


def build():
    pool = []
    provenance = {}
    for stage in ('02-dose-response', '03-missed-candidates'):
        path = PROGRAM / 'stages' / stage / 'frozen-finalists.json'
        provenance[stage] = digest(path)
        pool += read(path)['variants']
    pool.sort(key=lambda v: (-v['nomination']['change'], -v['nomination']['hits']/v['nomination']['n'],
                            -v['nomination']['coherence'], v['nomination']['tie_key']))
    selected = [variant('L2-N3420', 9.)]; used = {'L2-N3420'}
    for v in pool + [variant('L2-N3030', -15), variant('L3-N2589', 9), variant('L5-N4206', 15),
                      variant('L10-N4198', 3), variant('L5-N3454', -8)]:
        if v['component'] in used:
            continue
        selected.append(v); used.add(v['component'])
        if len(selected) == 6:
            break
    timings = ['all', 'prompt', 'decode', 'window_8_24', 'pulse_16']
    variants = []
    for v in selected:
        value = v['sites'][0]['value']
        clamps = [0, .75*value, value, 1.25*value, -value] if value else [-1, -.5, 0, .5, 1]
        for operator, values in [('clamp', clamps), ('add', [-3, -1, 1, 3]), ('scale', [0, -1, 2, 4])]:
            for timing in timings:
                variants += [variant(v['component'], number, operator, timing) for number in values]
    result = plan('04-timing-operators', 2, variants, 2026112704, 'lfmfollow.timed_actor_v1')
    result['candidate_provenance'] = {'source_selection_sha256': provenance, 'base_profiles': selected,
        'rule': 'Force the original +9x question, then choose unique coordinates by earlier validation nomination scores; known parent candidates backfill. Held-out scores are not consulted.'}
    result['timing_semantics'] = 'Prediction index 0 is the last prompt position. Prompt-only includes all prompt tokens; decode-only starts with cached call 1. Window [8,24) and pulse 16 affect those predicted response positions. Exposures after a row finished are excluded.'
    result['operator_units'] = 'Clamp and add use original-checkpoint activation maxima. Scale is a dimensionless multiplier. These grids are not equal-amplitude comparisons; report local linearized write norms and actual exposure.'
    result['selection']['discovery_queues'] = 'Per operator: two consistent plus one rare condition, then up to three other global conditions, maximum twelve. Seeded ties.'
    result['selection']['final_queues'] = 'Up to two conditions per operator, with one consistent and one rare when available; consistency fills an empty rare slot.'
    return result


def stratified(analyses, variants, final=False):
    result, ranking, seen = [], [], set()
    for operator in ('clamp', 'add', 'scale'):
        subset = [v for v in variants if v['sites'][0]['operator'] == operator]
        chosen, rows = nominate(analyses, subset, 1 if final else 2, 1, seed=2026112705 if final else 2026112704)
        if final and len(chosen) < 2:
            extra, _ = nominate(analyses, subset, 2, 0, seed=2026112705)
            chosen += [v for v in extra if (v['component'], v['id']) not in {(r['component'], r['id']) for r in chosen}][:2-len(chosen)]
        ranking += rows
        for v in chosen:
            key = v['component'], v['id']
            if key not in seen:
                result.append(v); seen.add(key)
    if not final and len(result) < 12:
        more, _ = nominate(analyses, variants, 8, 4, seed=2026112704)
        result += [v for v in more if (v['component'], v['id']) not in seen][:12-len(result)]
    return result, ranking


def select_validation(analyses, variants):
    return stratified(analyses, variants)


def select_final(analyses, variants):
    return stratified(analyses, variants, True)
