"""Post hoc saved-token repetition measurements; no inference or behavioral verdicts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
FIELDS = ('matching_ids', 'repetition_ids', 'collapse_ids', 'baseline_defect_ids', 'task_loss_ids')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(tokens):
    def duplicate_fraction(sequence):
        count = len(sequence) - 3
        return 1 - len({tuple(sequence[i:i+4]) for i in range(count)}) / count if count > 0 else None
    longest = current = 0
    previous = None
    for token in tokens:
        current = current + 1 if token == previous else 1
        longest = max(longest, current)
        previous = token
    return {'tokens': len(tokens), 'duplicate_fourgram_fraction': duplicate_fraction(tokens),
            'last_64_tokens_duplicate_fourgram_fraction': duplicate_fraction(tokens[-64:]),
            'longest_identical_token_run': longest}


def summarize(rows, side):
    keys = metrics([])
    return {key: median(values) if (values := [r[side][key] for r in rows if r[side][key] is not None]) else None
            for key in keys}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=read(PROGRAM/'programme.json')['finite_stages'])
    args = parser.parse_args()
    directory = PROGRAM/'stages'/args.stage
    target = directory/'posthoc-repetition-v1.json'
    if target.exists():
        assert read(target)['analysis_source_sha256'] == sha(Path(__file__))
        print('Existing descriptive repetition analysis retained.'); return
    assert read(directory/'status.json')['stage'] == 'measurements_complete'
    assert read(directory/'independent-audit.json')['passed']
    pairs, outcomes = read(directory/'pairs.json'), read(directory/'outcomes.json')
    inputs = {name: sha(directory/name) for name in ('pairs.json','outcomes.json','independent-audit.json')}
    effects = {}
    for who, filename in [('Terra','locked_test.json'), ('Sol','sol-locked_test.json')]:
        if args.stage == '01-confirm-p9':
            path = directory/('reviews' if who == 'Terra' else 'confirmations')/'locked_test/L2-N3420.json'
            value = read(path)
            effects[who] = {name: {'L2-N3420': {'p9': next(i for i in value['analysis']['items']
                if i['component_id'] == alias+'__L2-N3420')['condition_effects'][0]}}
                for name, alias in [('original','A'),('abliterated','B')]}
        else:
            path = directory/'analyses'/filename
            effects[who] = {name: {component: {condition: item['effect'] for condition,item in conditions.items()}
                for component,conditions in components.items()} for name,components in read(path).items()}
        inputs[path.relative_to(directory).as_posix()] = sha(path)
    profiles = []
    for gate in outcomes['condition_gates']:
        name, component, condition = gate['checkpoint'], gate['coordinate'], gate['condition']
        selected = [p for p in pairs[name][component] if p['condition'] == condition and
                    p['stage'] in ('locked_test','long','replication','random_controls')]
        assert sum(p['kind'] == 'neuron' for p in selected) == 32
        assert sum(p['kind'] == 'random_direction' for p in selected) == 32 and len(selected) == 64
        records = []
        for pair in selected:
            ratings = {who: effects[who][name].get(component,{}).get(condition) for who in effects}
            fields = FIELDS if pair['kind'] == 'neuron' else ('similar_random_ids',)
            flags = {who: {field: pair['id'] in value[field] for field in fields} if value else None
                     for who,value in ratings.items()}
            records.append({'id': pair['id'], 'phase': pair['stage'], 'kind': pair['kind'],
                'termination': pair['termination'], 'baseline': metrics(pair['baseline_token_ids']),
                'steered': metrics(pair['token_ids']), 'reviewer_flags': flags})
        summaries = {}
        for kind in ('neuron','random_direction'):
            subset = [r for r in records if r['kind'] == kind]
            summaries[kind] = {'n': len(subset), 'baseline_medians': summarize(subset,'baseline'),
                               'steered_medians': summarize(subset,'steered')}
        profiles.append({'checkpoint': name, 'component': component, 'condition': condition,
                         'frozen_gate_passed': gate['passed'], 'summary': summaries, 'cases': records})
    result = {'stage': args.stage, 'analysis_kind': 'Post hoc descriptive saved-token statistics',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'analysis_source_sha256': sha(Path(__file__)),
        'input_sha256': inputs, 'profiles': profiles,
        'metric_definitions': {'duplicate_fourgram_fraction': '1 - distinct contiguous token fourgrams / total contiguous token fourgrams; null with fewer than four tokens. Overlapping fourgrams count.',
            'last_64_tokens_duplicate_fourgram_fraction': 'The same calculation restricted to the last at most 64 stored generated tokens.',
            'longest_identical_token_run': 'Maximum consecutive run of a single stored token ID; zero for empty sequences.'},
        'interpretation': 'No thresholds, new judgments or changes to frozen gates. Token repetition is not semantic collapse, factuality, coherence or task preservation. Length, tokenization and truncation affect these descriptive statistics. Saved generated IDs include whatever special tokens the worker retained. Only final catalogue conditions are summarized; auxiliary single-neuron arms of a pair are outside this summary. Control ratings concern a frozen effect description, so neuron-only reviewer flag fields need not classify control quality. Baselines and four-direction controls are reused and are not independent samples.'}
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'stage': args.stage, 'profiles': len(profiles), 'measured_jobs_created': 0}))


if __name__ == '__main__': main()
