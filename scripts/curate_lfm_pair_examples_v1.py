"""Select disclosed arithmetic illustrations from audited pair evidence; no new ratings."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'campaigns/lfm-depth-20261127-v1/stages/05-neuron-pairs'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert read(DIRECTORY / 'status.json')['stage'] == 'measurements_complete'
    assert read(DIRECTORY / 'independent-audit.json')['passed']
    pairs = read(DIRECTORY / 'pairs.json')
    analyses = {who: read(DIRECTORY / 'analyses' / file) for who, file in
        [('Terra', 'locked_test.json'), ('Sol', 'sol-locked_test.json')]}
    panels = []
    prompt = 'Calculate 31 plus 17.'
    for component in ('PAIR-L2-N3420-L1-N4341', 'PAIR-L2-N3420-L5-N4206'):
        panel = {'component': component, 'prompt': prompt, 'checkpoints': {}}
        for checkpoint, components in pairs.items():
            rows = [r for r in components[component] if r['kind'] == 'neuron'
                and r['stage'] == 'locked_test' and r['prompt'] == prompt]
            assert len(rows) == 3 and {r['config']['variant']['arm'] for r in rows} == {'A', 'B', 'AB'}
            examples = []
            for row in sorted(rows, key=lambda r: ('A', 'B', 'AB').index(r['config']['variant']['arm'])):
                ratings = {}
                for who, analysis in analyses.items():
                    item = analysis[checkpoint][component].get(row['condition'])
                    assert item, 'A missing review must remain unavailable, not silently become false flags'
                    effect = item['effect']
                    ratings[who] = {'frozen_description': effect['label'],
                        **{field: row['id'] in effect[field + '_ids'] for field in
                           ('matching', 'repetition', 'collapse', 'task_loss', 'baseline_defect')},
                        'review_input_sha256': item['review_input_sha256']}
                examples.append({field: row[field] for field in
                    ('id', 'condition', 'stage', 'prompt', 'baseline', 'steered', 'termination', 'token_ids', 'baseline_token_ids')}
                    | {'arm': row['config']['variant']['arm'], 'sites': row['config']['sites'], 'ratings': ratings})
            panel['checkpoints'][checkpoint] = examples
        panels.append(panel)
    inputs = ('pairs.json', 'independent-audit.json', 'analyses/locked_test.json', 'analyses/sol-locked_test.json')
    result = {'schema': 'lfm-pair-report-examples-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'analysis_source_sha256': sha(Path(__file__)), 'input_sha256': {name: sha(DIRECTORY / name) for name in inputs},
        'selection': 'Post hoc illustrations selected after observing the arithmetic responses. '
                     'The same locked prompt and all three arms are shown in both checkpoints. '
                     'Selection is not a prevalence estimate, an independent test, or a gate revision. '
                     'Each arm is rated against its checkpoint\'s frozen AB description; not matching it does not imply no other effect.',
        'panels': panels}
    target = DIRECTORY / 'report-factorial-examples.json'
    assert not target.exists(), 'Retain saved curation; use a versioned correction if needed.'
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'panels': len(panels), 'cases': sum(len(rows) for p in panels for rows in p['checkpoints'].values())}))


if __name__ == '__main__':
    main()
