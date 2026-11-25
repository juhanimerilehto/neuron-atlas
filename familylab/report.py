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


def write_report():
    audit = read(OUT / 'independent-audit.json')
    assert audit['passed']
    records = [r for r in read(ROOT / 'site-source/catalogue.json')['records']
               if r.get('campaign_id', '').startswith(data.CAMPAIGN)]
    finalists = read(OUT / 'frozen-finalists.json')
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
                    models[name] = {k: len(ids & set(effect[k])) for k in
                        ('matching_ids', 'repetition_ids', 'collapse_ids', 'task_loss_ids', 'baseline_defect_ids')}
                    models[name].update({k: effect[k] for k in ('label', 'change_strength', 'coherence', 'hypothesis_supported')})
                comparisons.append({'coordinate': cid, 'condition': condition, 'reviewer': reviewer, 'models': models})
    summary = {'campaign_id': data.CAMPAIGN, 'observations': len(records),
        'states': dict(Counter(r['state'] for r in records)), 'tested_coordinates': len(finalists),
        'tested_coordinate_dose_settings': sum(map(len, finalists.values())), 'gate_passes': audit['extreme_gate_passes'],
        'review_gaps': audit['review_gaps'], 'matched_settings': comparisons,
        'scope': 'Finite prompts and selected settings; ordinal LLM judgments. A repeatable mode may abandon the requested task.'}
    write_json(ROOT / 'site-source/evidence' / data.CAMPAIGN / 'outcomes.json', summary)
    jobs = sum(sum(v.values()) for v in audit['all_stage_counts'].values())
    lines = [f'# {data.SPEC["label"]} neuron-intervention results', '',
        f'The fixed numerical grid screened all {data.COORDINATES:,} MLP coordinates in each checkpoint. '
        f'The full pipeline completed {jobs:,} configurations and added {len(records)} model-specific catalogue observations. '
        f'{audit["extreme_gate_passes"]} records meet the declared stability criteria under both reviewers.', '',
        'Ordinary prompts were fixed before inspecting outputs. Interventions clamp one actual gated-MLP output coordinate; '
        'weights remain unchanged. Every physical batch includes an unmodified anchor. '
        'Task loss, repetition, collapse and baseline defects are reported separately from strength and coherence.', '',
        '## Checkpoints', '']
    for name, (repo, revision) in data.SPEC['models'].items():
        lines.append(f'- {name}: [{repo}](https://huggingface.co/{repo}/tree/{revision}), revision `{revision}`.')
    if len(data.MODELS) > 1:
        lines += ['', 'Both checkpoints use original-model tokenization, runtime settings, calibration targets and shared continuations. '
            'The following comparisons include every frozen coordinate/dose in both checkpoints, not only each preferred displayed dose.', '',
            '| Reviewer | Settings | Derivative more repetitive | Less repetitive | Equal |', '|---|---:|---:|---:|---:|']
        for reviewer in ('Terra', 'Sol'):
            rows = [x for x in comparisons if x['reviewer'] == reviewer]
            delta = [x['models']['abliterated']['repetition_ids'] - x['models']['original']['repetition_ids'] for x in rows]
            lines.append(f'| {reviewer} | {len(rows)} | {sum(x > 0 for x in delta)} | {sum(x < 0 for x in delta)} | {sum(x == 0 for x in delta)} |')
    lines += ['', '## Held-out outcomes', '',
        'Each row below uses Sol ratings on the same 32 neuron outputs: 16 held-out, eight longer and eight replication prompts. '
        'Random directions are retained separately in the evidence. Passing the declared gate does not require task correctness.', '',
        '| Coordinate | Dose | Checkpoint | Effect matches | Repetition | Collapse | Task loss | Change / coherence |',
        '|---|---|---|---:|---:|---:|---:|---|']
    for row in comparisons:
        if row['reviewer'] != 'Sol':
            continue
        for name, stats in row['models'].items():
            lines.append(f'| {row["coordinate"]} | {row["condition"]} | {name} | {stats["matching_ids"]} | '
                f'{stats["repetition_ids"]} | {stats["collapse_ids"]} | {stats["task_loss_ids"]} | '
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
