"""Post hoc consistency of repeated single-neuron controls; no inference or gate changes."""
from collections import defaultdict, Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'campaigns/lfm-depth-20261127-v1/stages/05-neuron-pairs'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def first_difference(a, b):
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def main():
    assert read(DIRECTORY / 'status.json')['stage'] == 'measurements_complete'
    assert read(DIRECTORY / 'independent-audit.json')['passed']
    pairs = read(DIRECTORY / 'pairs.json')
    results = {}
    for checkpoint, components in pairs.items():
        groups = defaultdict(list)
        for rows in components.values():
            for row in rows:
                if row['kind'] != 'neuron':
                    continue
                cfg = row['config']
                variant = cfg['variant']
                arm = variant['arm']
                assert len(cfg['sites']) == (2 if arm == 'AB' else 1)
                assert cfg['sites'] == variant['sites'] and cfg['timing'] == variant['timing']
                if arm == 'AB':
                    continue
                key = canonical({'sites': cfg['sites'], 'timing': cfg['timing'],
                    'stage': row['stage'], 'prompt': row['prompt'], 'max_tokens': cfg['max_tokens']})
                groups[key].append(row)
        repeated = [(key, rows) for key, rows in groups.items() if len(rows) > 1]
        by_phase = Counter()
        agreements = Counter()
        differences = []
        for key, rows in repeated:
            by_phase[rows[0]['stage']] += 1
            base_equal = len({canonical([r['baseline_token_ids'], r['baseline']]) for r in rows}) == 1
            output_equal = len({canonical([r['token_ids'], r['steered']]) for r in rows}) == 1
            agreements['baseline_exact_groups'] += base_equal
            agreements['steered_exact_groups'] += output_equal
            if not base_equal or not output_equal:
                ref = rows[0]
                differences.append({'intervention': json.loads(key), 'case_ids': [r['id'] for r in rows],
                    'baseline_exact': base_equal, 'steered_exact': output_equal,
                    'first_token_difference_from_first': [first_difference(ref['token_ids'], r['token_ids'])
                        if ref['token_ids'] != r['token_ids'] else None for r in rows]})
        results[checkpoint] = {'repeated_single_setting_prompt_groups': len(repeated),
            'physical_cases_in_repeated_groups': sum(len(rows) for _, rows in repeated),
            'groups_by_phase': dict(by_phase), **dict(agreements), 'nonidentical_groups': len(differences),
            'differences': differences}
    result = {'schema': 'lfm-pair-repeatability-v1', 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'analysis_source_sha256': digest(Path(__file__)),
        'input_sha256': {name: digest(DIRECTORY / name) for name in ('pairs.json', 'independent-audit.json')},
        'scope': 'Repeated single interventions within the same checkpoint, phase, prompt and token cap. '
                 'Pair membership and A/B role are excluded from grouping. Exact saved tokens and text are compared. '
                 'This is post hoc numerical repeatability, not an extra behavioral review or a gate revision. '
                 'Any differences can include batch-composition effects under BF16 greedy decoding.',
        'checkpoints': results}
    destination = DIRECTORY / 'posthoc-pair-repeatability-v1.json'
    assert not destination.exists(), 'Retain an existing immutable analysis; version any correction.'
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({name: {k: v for k, v in row.items() if k != 'differences'} for name, row in results.items()}))


if __name__ == '__main__':
    main()
