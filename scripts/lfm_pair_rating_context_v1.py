"""Post hoc reviewer-context diagnostic on identical repeated final single-arm outputs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'campaigns/lfm-depth-20261127-v1/stages/05-neuron-pairs'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert read(D / 'independent-audit.json')['passed']
    assert read(D / 'status.json')['stage'] == 'measurements_complete'
    pairs = read(D / 'pairs.json')
    analyses = {who: read(D / 'analyses' / file) for who, file in
        [('Terra', 'locked_test.json'), ('Sol', 'sol-locked_test.json')]}
    components = ('PAIR-L2-N3420-L3-N2550', 'PAIR-L2-N3420-L5-N4206', 'PAIR-L2-N3420-L1-N4341')
    result = {}
    for checkpoint, data in pairs.items():
        cases = {c: {(r['stage'], r['prompt']): r for r in data[c] if r['kind'] == 'neuron'
            and r['condition'] == 'pair__A__p1' and r['stage'] in ('locked_test', 'long', 'replication')}
            for c in components}
        keys = set(cases[components[0]])
        assert len(keys) == 32 and all(set(rows) == keys for rows in cases.values())
        for key in keys:
            rows = [cases[c][key] for c in components]
            assert all(r['config']['sites'] == [{'layer': 2, 'neuron': 3420, 'operator': 'clamp', 'value': 9.0}]
                and r['config']['timing'] == 'all' for r in rows)
            assert len({json.dumps([r['baseline_token_ids'], r['baseline'], r['token_ids'], r['steered']], ensure_ascii=False)
                for r in rows}) == 1, 'Only identical paired outputs can support this context diagnostic'
        reviewers = {}
        for who, analysis in analyses.items():
            flags = {}
            for field in ('repetition', 'collapse', 'task_loss', 'baseline_defect'):
                sets = {c: {key for key, row in cases[c].items()
                    if row['id'] in analysis[checkpoint][c]['pair__A__p1']['effect'][field + '_ids']}
                    for c in components}
                flags[field] = {'counts_by_bundle': {c: len(v) for c, v in sets.items()},
                    'discordant_prompts': [{'phase': key[0], 'prompt': key[1],
                        'flags_by_bundle': {c: key in sets[c] for c in components},
                        'case_ids_by_bundle': {c: cases[c][key]['id'] for c in components}}
                        for key in sorted(keys) if len({key in values for values in sets.values()}) > 1]}
            reviewers[who] = flags
        result[checkpoint] = {'identical_prompt_output_groups': 32, 'reviewers': reviewers}
    inputs = ('pairs.json', 'independent-audit.json', 'analyses/locked_test.json', 'analyses/sol-locked_test.json')
    output = {'schema': 'lfm-pair-rating-context-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'analysis_source_sha256': sha(Path(__file__)), 'input_sha256': {name: sha(D / name) for name in inputs},
        'scope': 'Post hoc identical-output check of L2 N3420 +9x single-arm ratings across three pair bundles. '
                 'Matching labels are deliberately excluded: each bundle has its own frozen AB description. '
                 'Diagnostic quality and task/baseline flags should be interpreted cautiously when they vary '
                 'on the same saved texts. This detects inconsistency, without identifying its cause or ground truth. '
                 'No review was rerun and no frozen gate or rating was changed.', 'checkpoints': result}
    target = D / 'posthoc-rating-context-v1.json'
    assert not target.exists(), 'Retain saved analysis; version any correction.'
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({n: {w: {f: {'counts': v['counts_by_bundle'], 'discordant': len(v['discordant_prompts'])}
        for f, v in flags.items()} for w, flags in row['reviewers'].items()} for n, row in result.items()}))


if __name__ == '__main__':
    main()
