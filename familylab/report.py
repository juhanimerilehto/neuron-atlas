"""Present complete audited measurements without confusing task loss with model capability."""
import json
from collections import Counter
from pathlib import Path
from familylab import data
from worker.reference import write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'campaigns' / data.CAMPAIGN


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def screening_provenance():
    shortlist = read(OUT / 'shared-shortlist.json')
    plan = read(OUT / 'validation-plan.json')
    cache, result = {}, {}
    for cid in plan:
        layer = shortlist[cid]['layer']
        models = {}
        for name in data.MODELS:
            key = name, layer
            if key not in cache:
                rows = read(OUT / name / f'screen-L{layer:02}.json')
                ranks = {metric: {row['coordinate']: rank for rank, row in enumerate(
                    sorted(rows, key=lambda row: (-row[metric], row['neuron'])), 1)}
                    for metric in ('early', 'delayed')}
                cache[key] = {row['coordinate']: {
                    **{metric: row[metric] for metric in ('early', 'late', 'delayed')},
                    'early_rank_in_layer': ranks['early'][row['coordinate']],
                    'delayed_rank_in_layer': ranks['delayed'][row['coordinate']],
                } for row in rows}
            models[name] = cache[key][cid]
        result[cid] = {'tracks': shortlist[cid]['tracks'], 'models': models}
    return result


def condition_results(finalists, records):
    from familylab.publish import decision
    validation = {name: read(OUT / name / 'validation.json') for name in data.MODELS}
    phases = {name: {stage: read(OUT / name / (stage + '.json'))
                     for stage in ('locked_test', 'long', 'replication')} for name in data.MODELS}
    result = []
    for cid, conditions in finalists.items():
        reviews = {}
        for phase, folder in [('validation', 'reviews'), ('primary', 'reviews'), ('independent', 'confirmations')]:
            path = OUT / folder / ('validation' if phase == 'validation' else 'locked_test') / (cid + '.json')
            reviews[phase] = read(path) if path.exists() else None
        for name in data.MODELS:
            record = next(r for r in records if r['component_id'] == cid and r['campaign_id'] == data.CAMPAIGN + '-' + name)
            assert set(conditions) <= set(record['primary_test_settings'])
            cases = sum([phases[name][stage][cid] for stage in phases[name]], [])
            for condition in conditions:
                effects = {}
                for phase, review in reviews.items():
                    item = next((i for i in review['analysis']['items'] if i['component_id'] == name + '__' + cid), None) if review else None
                    effects[phase] = next((e for e in item['condition_effects'] if e['condition'] == condition), None) if item else None
                ve = effects['validation']
                ids = {p['id'] for p in validation[name][cid] if p['condition'] == condition and p['kind'] == 'neuron'}
                assert ve and len(ids) == 8
                val = {'change': ve['change_strength'], 'coherence': ve['coherence'],
                       'matches': len(ids & set(ve['matching_ids'])), 'n': len(ids)}
                val['passed'] = val['change'] >= 3 and val['coherence'] >= 3 and val['matches'] >= 4
                gates = {phase: decision(effects[phase], cases, effects[phase]['hypothesis_supported'] is True)
                         if effects[phase] else None for phase in ('primary', 'independent')}
                passed = bool(val['passed'] and all(gate and gate['passed'] for gate in gates.values()))
                preferred = record['hypothesis']['best_condition'] == condition
                if preferred:
                    assert passed == bool((record.get('paired_gate') or {}).get('passed'))
                common = set.intersection(*(set(effects[phase]['matching_ids']) for phase in gates)) if all(effects[phase] for phase in gates) else set()
                defects = set().union(*(set(effects[phase]['repetition_ids'] + effects[phase]['collapse_ids']) for phase in gates if effects[phase]))
                task_loss = set.intersection(*(set(effects[phase]['task_loss_ids']) for phase in gates)) if all(effects[phase] for phase in gates) else set()
                example, basis = None, None
                for pool, description in (((common & task_loss) - defects, 'Both reviewers matched the effect and flagged task loss, with no repetition/collapse flag.'),
                                           (common - defects, 'Both reviewers matched the effect, with no repetition/collapse flag.'),
                                           (common, 'Both reviewers matched the effect.')):
                    example = next((p['id'] for p in cases if p['condition'] == condition and p['stage'] == 'locked_test' and p['id'] in pool), None)
                    if example:
                        basis = description
                        break
                result.append({'coordinate': cid, 'checkpoint': name, 'condition': condition,
                    'label': (effects['independent'] or ve)['label'], 'passed': passed,
                    'preferred_on_card': preferred, 'validation': val, **gates, 'example_id': example, 'example_basis': basis,
                    'review_input_sha256': {phase: review['input_sha256'] if review else None for phase, review in reviews.items()}})
    return result


def write_report():
    audit = read(OUT / 'independent-audit.json')
    assert audit['passed']
    records = [r for r in read(ROOT / 'site-source/catalogue.json')['records']
               if r.get('campaign_id', '').startswith(data.CAMPAIGN)]
    finalists = read(OUT / 'frozen-finalists.json')
    condition_gates = condition_results(finalists, records)
    qualifying = [row for row in condition_gates if row['passed']]
    comparisons = []
    for cid, conditions in finalists.items():
        for reviewer, folder in [('Terra', 'reviews'), ('Sol', 'confirmations')]:
            path = OUT / folder / 'locked_test' / (cid + '.json')
            if not path.exists():
                continue
            review = read(path)
            for condition in conditions:
                models = {}
                for name in data.MODELS:
                    item = next(i for i in review['analysis']['items'] if i['component_id'] == name + '__' + cid)
                    effect = next(e for e in item['condition_effects'] if e['condition'] == condition)
                    cases = sum([read(OUT / name / (stage + '.json'))[cid]
                                 for stage in ('locked_test', 'long', 'replication')], [])
                    ids = {p['id'] for p in cases if p['condition'] == condition and p['kind'] == 'neuron'}
                    assert len(ids) == 32
                    controls = read(OUT / name / 'random_controls.json')[cid]
                    control_ids = {p['id'] for p in controls if p['condition'] == condition and p['kind'] == 'random_direction'}
                    assert len(control_ids) == 32
                    models[name] = {k: len(ids & set(effect[k])) for k in
                        ('matching_ids', 'repetition_ids', 'collapse_ids', 'task_loss_ids', 'baseline_defect_ids')}
                    models[name].update({k: effect[k] for k in ('label', 'change_strength', 'coherence', 'hypothesis_supported')})
                    models[name]['similar_random_ids'] = len(control_ids & set(effect['similar_random_ids']))
                comparisons.append({'coordinate': cid, 'condition': condition, 'reviewer': reviewer, 'models': models})
    provenance = screening_provenance()
    late_only = [cid for cid, row in provenance.items()
                 if any(track.endswith(':late') for track in row['tracks'])
                 and not any(track.endswith(':early') for track in row['tracks'])]
    write_json(ROOT / 'site-source/evidence' / data.CAMPAIGN / 'screening-provenance.json', {
        'campaign_id': data.CAMPAIGN,
        'scope': 'Within-layer ranks use the frozen score definitions and neuron-index tie-breaks. Selection tracks record fixed per-layer quotas.',
        'coordinates': provenance})
    summary = {'campaign_id': data.CAMPAIGN, 'observations': len(records),
        'states': dict(Counter(r['state'] for r in records)), 'tested_coordinates': len(finalists),
        'tested_coordinate_dose_settings': sum(map(len, finalists.values())), 'frozen_settings': finalists,
        'gate_passes': audit['extreme_gate_passes'],
        'qualified_frozen_condition_count': len(qualifying), 'condition_gates': condition_gates,
        'review_gaps': audit['review_gaps'], 'matched_settings': comparisons,
        'late_only_validation_coordinates': late_only,
        'screening_provenance_ref': 'evidence/' + data.CAMPAIGN + '/screening-provenance.json',
        'scope': 'Finite prompts and selected settings; ordinal LLM judgments. A repeatable mode may abandon the requested task.'}
    write_json(ROOT / 'site-source/evidence' / data.CAMPAIGN / 'outcomes.json', summary)
    jobs = sum(sum(v.values()) for v in audit['all_stage_counts'].values())
    lines = [f'# {data.SPEC["label"]} neuron-intervention results', '',
        f'The fixed numerical grid screened all {data.COORDINATES:,} MLP coordinates in each checkpoint. '
        f'The full pipeline completed {jobs:,} configurations and added {len(records)} model-specific catalogue observations. '
        f'{audit["extreme_gate_passes"]} preferred catalogue records meet the declared stability criteria under both reviewers. '
        f'Across all frozen settings, {len(qualifying)} checkpoint/coordinate/dose conditions meet the same criteria.', '',
        'Ordinary prompts were fixed before inspecting outputs. Interventions clamp one gated hidden activation immediately before the MLP output projection; '
        'weights remain unchanged. Doses are signed multiples of the maximum absolute activation measured for that coordinate '
        'in the original checkpoint calibration. Every physical batch includes an unmodified anchor. '
        'Task loss, repetition, collapse and baseline defects are reported separately from strength and coherence.', '',
        'Both final reviewers receive the frozen validation hypotheses, including validation ratings, notes and evidence references. '
        'Sol receives a separate request without Terra\'s held-out verdict. The second-model assessment therefore shares nomination '
        'information with the primary review.', '',
        '## Checkpoints', '']
    for name, (repo, revision) in data.SPEC['models'].items():
        lines.append(f'- {name}: [{repo}](https://huggingface.co/{repo}/tree/{revision}), revision `{revision}`.')
    if data.FAMILY == 'lfm':
        inventory = read(OUT / 'weight-comparison.json')
        changed = [item['tensor'] for item in inventory['changed']]
        classes = {key: sum(marker in name for name in changed) for key, marker in
                   (('MLP', '.feed_forward.'), ('attention', '.self_attn.'), ('convolution', '.conv.'))}
        lines += ['', f"Exact CPU comparison found {len(changed)} changed and {len(inventory['unchanged'])} identical tensors, "
            f"with matching names, shapes and dtypes: {classes['MLP']} MLP, {classes['attention']} attention and "
            f"{classes['convolution']} convolution output projections changed. The derivative publisher's documented "
            'parent weights match the acquired original file hash. This inventory does not establish edit rank or '
            'independently verify the publisher\'s refusal benchmarks. The paired result concerns all these checkpoint edits together. '
            f'[Weight inventory](../site-source/evidence/{data.CAMPAIGN}/weight-comparison.json) · '
            f'[Parent verification](../site-source/evidence/{data.CAMPAIGN}/parent-provenance.json)']
    if len(data.MODELS) > 1:
        lines += ['', 'Both checkpoints use original-model tokenization, runtime settings, calibration targets and shared continuations. '
            'The following comparisons include every frozen coordinate/dose in both checkpoints, not only each preferred displayed dose.', '',
            '| Reviewer | Settings | Derivative more repetitive | Less repetitive | Equal |', '|---|---:|---:|---:|---:|']
        for reviewer in ('Terra', 'Sol'):
            rows = [x for x in comparisons if x['reviewer'] == reviewer]
            delta = [x['models']['abliterated']['repetition_ids'] - x['models']['original']['repetition_ids'] for x in rows]
            lines.append(f'| {reviewer} | {len(rows)} | {sum(x > 0 for x in delta)} | {sum(x < 0 for x in delta)} | {sum(x == 0 for x in delta)} |')
    lines += ['', '## Frozen settings meeting the criteria', '',
        'Each catalogue card displays one validation-selected setting per coordinate and checkpoint. '
        'This table includes every frozen setting meeting the criteria, including additional settings on the same coordinate.', '',
        '| Checkpoint | Coordinate | Dose | Effect label | Selected on card |', '|---|---|---|---|---|']
    for row in qualifying:
        label = (row['label'] or 'No supported label').replace('|', '/').replace('\n', ' ')
        lines.append(f'| {row["checkpoint"]} | {row["coordinate"]} | {row["condition"]} | {label} | '
                     f'{"Yes" if row["preferred_on_card"] else "No"} |')
    if not qualifying:
        lines += ['', 'No frozen coordinate/dose condition met all the criteria under both reviewers.']
    lines += ['', '## Later-token screening', '',
        f'{len(late_only)} of {len(provenance)} validation coordinates entered the shared shortlist through delayed-effect ranking '
        'with no early-rank nomination in any checkpoint. These are selection-provenance counts under fixed per-layer quotas. '
        f'[Within-layer ranks and selection paths](../site-source/evidence/{data.CAMPAIGN}/screening-provenance.json).', '',
        '## Held-out outcomes', '',
        'Each row below uses Sol ratings on the same 32 neuron outputs: 16 held-out, eight longer and eight replication prompts. '
        'The random-match column counts the same description among 32 matched random-direction outputs per setting '
        '(four directions on eight prompts). Held-out claims apply to the listed coordinate/dose settings. '
        'Other dose-grid results retain validation-only evidence. Passing the declared gate does not require task correctness '
        'or random-direction specificity.', '',
        '| Coordinate | Dose | Checkpoint | Effect label | Effect matches | Random matches | Repetition | Collapse | Task loss | Baseline defects | Change / coherence |',
        '|---|---|---|---|---:|---:|---:|---:|---:|---:|---|']
    for row in comparisons:
        if row['reviewer'] != 'Sol':
            continue
        for name, stats in row['models'].items():
            label = (stats['label'] or 'No supported label').replace('|', '/').replace('\n', ' ')
            lines.append(f'| {row["coordinate"]} | {row["condition"]} | {name} | {label} | {stats["matching_ids"]} | '
                f'{stats["similar_random_ids"]} | {stats["repetition_ids"]} | {stats["collapse_ids"]} | {stats["task_loss_ids"]} | {stats["baseline_defect_ids"]} | '
                f'{stats["change_strength"]}/4 / {stats["coherence"]}/4 |')
    lines += ['', '## Catalogue observations', '', '| Checkpoint | Coordinate | Label | Evidence state |', '|---|---|---|---|']
    for r in records:
        lines.append(f'| {r["model"]} | {r["component_id"]} | {r["label"].replace("|", "/")} | {r["state"]} |')
    lines += ['', f'The independent audit linked {audit["exact_pairs_linked_to_raw_jobs"]:,} exact generation pairs to raw completed jobs. '
        f'Terra used {audit["reviewers"]["codex"]["requests"]}/700 requests; Sol used '
        f'{audit["reviewers"]["codex-confirm"]["requests"]}/100. Review gaps: {len(audit["review_gaps"])}.', '',
        'Reviewers are fallible language models. These selected interventions and finite prompts do not establish a population-wide '
        'ranking, a persistent model personality, or a single cause of cross-family differences. '
        'The numerical grid is exhaustive; the space of prompts and possible activation targets is not.', '',
        '[Browse the catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · '
        f'[Protocol]({data.CAMPAIGN}.md) · [Independent audit](../site-source/evidence/{data.CAMPAIGN}/independent-audit.json)', '']
    (ROOT / 'docs' / ('campaign-' + data.CAMPAIGN + '.md')).write_text('\n'.join(lines), encoding='utf-8')
    return summary
