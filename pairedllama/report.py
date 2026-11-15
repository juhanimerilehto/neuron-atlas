"""Public report and paired descriptive outcomes, separate from frozen numerical selection."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'campaigns/paired-llama32-1b-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_report():
    audit = read(OUT / 'independent-audit.json')
    assert audit['passed']
    records = [r for r in read(ROOT / 'site-source/catalogue.json')['records'] if r.get('campaign_id', '').startswith('paired-llama32-1b-v1')]
    finalists = read(OUT / 'frozen-finalists.json')
    by_coordinate = {}
    for r in records:
        by_coordinate.setdefault(r['component_id'], {})['original' if r['model'] == 'Llama-3.2-1B-Instruct' else 'abliterated'] = r
    differences = []
    primary_pairs = {name: {cid: [] for cid in finalists} for name in ('original', 'abliterated')}
    for name in primary_pairs:
        for stage in ('locked_test', 'long', 'replication'):
            for cid, rows in read(OUT / name / (stage + '.json')).items():
                primary_pairs[name][cid].extend(rows)
    for cid, conditions in finalists.items():
        for reviewer, folder in [('primary', 'reviews'), ('independent', 'confirmations')]:
            path = OUT / folder / 'locked_test' / (cid + '.json')
            if not path.exists():
                continue
            review = read(path)
            items = {name: next(i for i in review['analysis']['items'] if i['component_id'] == name + '__' + cid)
                     for name in primary_pairs}
            for condition in conditions:
                stats = {}
                for name in primary_pairs:
                    effect = next(e for e in items[name]['condition_effects'] if e['condition'] == condition)
                    ids = {p['id'] for p in primary_pairs[name][cid] if p['condition'] == condition and p['kind'] == 'neuron'}
                    assert len(ids) == 32
                    stats[name] = {field: len(ids & set(effect[field])) for field in
                                   ('repetition_ids', 'collapse_ids', 'task_loss_ids', 'baseline_defect_ids')}
                    stats[name].update({'change': effect['change_strength'], 'coherence': effect['coherence']})
                differences.append({'coordinate': cid, 'reviewer': reviewer, 'condition': condition,
                                    'original': stats['original'], 'abliterated': stats['abliterated'],
                                    'repetition_delta_abliterated_minus_original': stats['abliterated']['repetition_ids'] - stats['original']['repetition_ids'],
                                    'collapse_delta_abliterated_minus_original': stats['abliterated']['collapse_ids'] - stats['original']['collapse_ids']})
    summary = {'campaign_id': 'paired-llama32-1b-v1', 'observations': len(records), 'tested_coordinates': len(finalists),
               'states': dict(Counter(r['state'] for r in records)), 'gate_passes': audit['extreme_gate_passes'],
               'review_gaps': audit['review_gaps'], 'same_dose_checkpoint_comparisons': differences,
               'scope': 'Selected coordinates, finite prompts and ordinal LLM judgments; no population or single-cause inference.'}
    write_path = ROOT / 'site-source/evidence/paired-llama32-1b-v1/outcomes.json'
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    jobs = sum(sum(v.values()) for v in audit['all_stage_counts'].values())
    lines = ['# Paired Llama 3.2 1B results', '',
             f'This experiment screened all 131,072 MLP coordinates in each checkpoint, completing {jobs:,} measured configurations. '
             f'The catalogue contains {len(records)} model-specific observations. {audit["extreme_gate_passes"]} meet the full declared stability criteria under both reviewers.', '',
             'The original model is meta-llama/Llama-3.2-1B-Instruct; its derivative is ai-anytime/Llama-3.2-1B-Instruct-abliterated. '
             'Both used the original runtime configuration, tokenizer, template and calibration scale. Each intervention has its own same-batch unmodified baseline.', '',
             'Terra and Sol are language-model reviewers. Ratings are fallible. Changes, coherence, repetition and collapse are recorded separately. '
             'The strict pass/fail threshold is not evidence that rejected settings produced no behavioral change.', '',
             '## Paired checkpoint differences', '',
             'All frozen primary coordinate/dose combinations are compared, including both doses when the checkpoints nominated different settings. This avoids filtering the comparison by each model’s preferred displayed dose.', '',
             '| Reviewer | Comparable settings | Abliterated more repetitive | Abliterated less repetitive | Equal repetition |', '|---|---:|---:|---:|---:|']
    for reviewer, label in [('primary', 'Terra'), ('independent', 'Sol')]:
        rows = [r for r in differences if r['reviewer'] == reviewer]
        values = [r['repetition_delta_abliterated_minus_original'] for r in rows]
        lines.append(f'| {label} | {len(rows)} | {sum(v > 0 for v in values)} | {sum(v < 0 for v in values)} | {sum(v == 0 for v in values)} |')
    lines += ['', 'For context, the earlier Qwen3-0.6B comparison found higher repetition in the abliterated checkpoint at five of eight selected settings under each reviewer. '
              'A second family and a different community editing implementation introduce multiple changed factors, so these comparisons cannot isolate abliteration as a sole cause.', '',
              '## Recorded observations', '', '| Model | Coordinate | Label | State |', '|---|---|---|---|']
    for r in records:
        lines.append(f"| {r['model']} | {r['component_id']} | {r['label'].replace('|', '/')} | {r['state']} |")
    lines += ['', f'Independent audit linked {audit["exact_pairs_linked_to_raw_jobs"]:,} exact generation pairs to completed raw jobs. '
              f'{len(audit["review_gaps"])} review bundles remain explicit gaps. Exhausted invalid responses were preserved rather than repaired or repeatedly retried.', '',
              'Full coordinate coverage applies to the fixed numerical grid. Prompts, doses and free-generation candidates are finite samples. '
              'Shared ordinary prompts and unchanged scoring criteria support comparison with Qwen, but family, size and editing method differ. '
              'These are descriptive intervention results rather than a general safety, refusal or capability ranking.', '',
              '[Catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · [Protocol](paired-llama32-1b-v1.md) · '
              '[Independent audit](../site-source/evidence/paired-llama32-1b-v1/independent-audit.json)', '']
    (ROOT / 'docs/campaign-paired-llama32-1b-v1.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary


if __name__ == '__main__':
    write_report()
