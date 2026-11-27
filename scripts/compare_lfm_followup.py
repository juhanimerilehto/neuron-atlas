"""Descriptive, prompt-matched checkpoint comparisons; never changes a stability verdict."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(stage):
    directory = PROGRAM / 'stages' / stage
    assert read(directory / 'independent-audit.json')['passed']
    assert read(directory / 'status.json')['stage'] == 'measurements_complete'
    pairs = read(directory / 'pairs.json')
    inputs = {'pairs.json': sha(directory / 'pairs.json'), 'independent-audit.json': sha(directory / 'independent-audit.json')}
    if stage == '01-confirm-p9':
        component, condition = 'L2-N3420', 'p9'
        profiles = [(component, condition)]
        description = read(directory / 'manifest.json')['protocol']['frozen_description']
        hypotheses = {name: {component: [{'condition': condition, 'label': description}]} for name in pairs}
        analyses = {}
        for who, folder in [('Terra', 'reviews'), ('Sol', 'confirmations')]:
            path = directory / folder / 'locked_test' / (component + '.json')
            record = read(path); inputs[path.relative_to(directory).as_posix()] = sha(path)
            analyses[who] = {name: {component: {condition: {'effect': next(i for i in record['analysis']['items']
                if i['component_id'] == alias + '__' + component)['condition_effects'][0]}}}
                for name, alias in [('original', 'A'), ('abliterated', 'B')]}
    else:
        profiles = [(v['component'], v['id']) for v in read(directory / 'frozen-finalists.json')['variants']]
        hypotheses = read(directory / 'frozen-hypotheses.json')
        analyses = {}
        for who, file in [('Terra', 'locked_test.json'), ('Sol', 'sol-locked_test.json')]:
            path = directory / 'analyses' / file
            analyses[who] = read(path); inputs[path.relative_to(directory).as_posix()] = sha(path)
        inputs['frozen-hypotheses.json'] = sha(directory / 'frozen-hypotheses.json')
    output = []
    for component, condition in profiles:
        rows = {name: {(p['stage'], p['prompt']): p for p in pairs[name][component]
            if p['condition'] == condition and p['kind'] == 'neuron' and p['stage'] in ('locked_test', 'long', 'replication')}
            for name in pairs}
        assert set(rows['original']) == set(rows['abliterated']) and len(rows['original']) == 32
        labels = {name: next(v['label'] for v in hypotheses[name][component] if v['condition'] == condition) for name in pairs}
        result = {'component': component, 'condition': condition, 'frozen_descriptions': labels,
                  'identical_frozen_description': labels['original'] == labels['abliterated'], 'reviewers': {}}
        for who, values in analyses.items():
            effects = {name: values[name].get(component, {}).get(condition, {}).get('effect') for name in pairs}
            if not all(effects.values()):
                result['reviewers'][who] = {'status': 'incomplete', 'missing_checkpoints': [n for n,e in effects.items() if not e]}
                continue
            flags = {}
            for field in ('matching_ids', 'repetition_ids', 'collapse_ids', 'task_loss_ids', 'baseline_defect_ids'):
                sets = {name: {key for key,p in rows[name].items() if p['id'] in effects[name][field]} for name in pairs}
                a, b = sets['original'], sets['abliterated']
                flags[field] = {'both': len(a & b), 'original_only': len(a - b), 'edited_only': len(b - a), 'neither': 32-len(a | b)}
            result['reviewers'][who] = {'status': 'complete', 'n': 32, 'matched_prompt_flags': flags}
        output.append(result)
    value = {'stage': stage, 'analysis_status': 'Post hoc descriptive comparison; does not alter frozen selection or gates.',
        'interpretation': 'Counts pair the same prompt and phase. If frozen descriptions differ, matching counts refer to each checkpoint own description and are not a common-target efficacy comparison. Equal counts do not establish mechanistic equivalence or a general effect of abliteration.',
        'input_sha256': inputs, 'analysis_source_sha256': sha(Path(__file__)), 'profiles': output}
    path = directory / 'paired-checkpoint-comparison.json'
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=read(PROGRAM / 'programme.json')['finite_stages'])
    args = parser.parse_args()
    value = compare(args.stage)
    print(json.dumps({'stage': args.stage, 'paired_profiles': len(value['profiles'])}))
