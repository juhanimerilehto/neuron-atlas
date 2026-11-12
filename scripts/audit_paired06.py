"""Independently link every exported pair to its completed, bounded measured job."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'worker'))
from reference import fingerprint, write_json
from audit_paired06_selection import build_audit

OUT = ROOT / 'campaigns/paired-qwen06-late-v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    manifest = read(OUT / 'manifest.json')
    assert read(OUT / 'audit.json')['passed']
    selection = build_audit()
    assert selection == read(OUT / 'selection-audit-v1.json')
    parent_identity = fingerprint(manifest)
    for relative, expected in manifest['sources'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    bank = read(OUT / 'prefix-bank.json')
    counts = {}
    checked_pairs = 0
    for name in ('original', 'abliterated'):
        identity = fingerprint({'parent': parent_identity, 'model': name})
        stages = {}
        coverage = {}
        generations = {}
        with sqlite3.connect(f'file:{(OUT / name / "jobs.sqlite").as_posix()}?mode=ro', uri=True) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            rows = 0
            for key, cfg_json, result_json, state in db.execute('SELECT id,config,result,status FROM jobs'):
                cfg, result = json.loads(cfg_json), json.loads(result_json)
                assert state == 'complete'
                assert key == fingerprint({'identity': identity, 'config': cfg})
                stages[cfg['stage']] = stages.get(cfg['stage'], 0) + 1
                assert 0 <= cfg['layer'] < 28 and 0 <= cfg['neuron'] < 3072
                if cfg['type'] == 'distribution':
                    assert result['checkpoints'] == bank[cfg['prompt']]['checkpoints']
                    assert len(result['js']) == len(result['checkpoints'])
                    assert all(0 <= value <= .694 for value in result['js'])
                    assert all(value >= 0 for value in result['kl'])
                    if cfg['stage'] == 'screen':
                        coverage.setdefault((cfg['layer'], cfg['neuron']), set()).add(cfg['setting'])
                else:
                    pair_id = fingerprint({'identity': parent_identity, 'model': name, 'config': cfg})
                    generations[pair_id] = (cfg, result)
                rows += 1
        assert rows <= 500000 and stages['screen'] == 86016 * 5
        assert len(coverage) == 86016 and all(value == set(manifest['broad_settings']) for value in coverage.values())
        for stage in ('discovery', 'validation', 'locked_test', 'long', 'replication', 'random_controls'):
            pairs = read(OUT / name / f'{stage}.json')
            seen = set()
            for cid, cases in pairs.items():
                for pair in cases:
                    cfg, measured = generations[pair['id']]
                    assert pair['id'] not in seen
                    seen.add(pair['id'])
                    assert cfg['coordinate'] == cid and cfg['stage'] == stage == pair['stage']
                    assert (pair['prompt'], pair['condition'], pair['random_index']) == (cfg['prompt'], cfg['setting'], cfg.get('random_index'))
                    assert pair['baseline'] == measured['batch_baseline']['text']
                    assert pair['baseline_token_ids'] == measured['batch_baseline']['token_ids']
                    assert pair['steered'] == measured['text'] and pair['token_ids'] == measured['token_ids']
                    assert pair['termination'] == measured['termination'] and pair['intervention'] == measured['intervention']
                    checked_pairs += 1
            assert len(seen) == stages[stage]
        counts[name] = stages
    catalogue = read(ROOT / 'site-source/catalogue.json')
    recovery_path = OUT / 'review-transport-v2.json'
    review_counts = {}
    gap_plan = OUT / 'review-gaps-v3.json'
    if gap_plan.exists():
        assert hashlib.sha256((ROOT / 'scripts/resume_paired06_reviews_v3.py').read_bytes()).hexdigest() == read(gap_plan)['source_sha256']
        gaps = read(OUT / 'review-gaps.json')
        finalists = read(OUT / 'frozen-finalists.json')
        for category, folder in [('primary', 'reviews'), ('independent', 'confirmations')]:
            accepted_coordinates = {p.stem for p in (OUT / folder / 'locked_test').glob('*.json')}
            assert accepted_coordinates.isdisjoint(gaps[category])
            assert accepted_coordinates | gaps[category].keys() == finalists.keys()
            for cid, gap in gaps[category].items():
                assert gap['status'] == 'review_unavailable'
                assert gap == read(OUT / 'review-failures' / folder / (cid + '.json'))
                evidence_dir = OUT / ('codex' if folder == 'reviews' else 'codex-confirm')
                for key in gap['exhausted_input_sha256']:
                    assert not (evidence_dir / (key + '.analysis.json')).exists()
                    assert (evidence_dir / (key + '.attempt-2.error.json')).exists()
    if recovery_path.exists():
        recovery = read(recovery_path)
        for filename, expected in recovery['sources_sha256'].items():
            assert hashlib.sha256((ROOT / 'scripts' / filename).read_bytes()).hexdigest() == expected
        from paired06_review_transport_v2 import compact, analysis
        contract = analysis.contract
        for folder, model, ceiling in [('codex', 'gpt-6.1-terra', 700), ('codex-confirm', 'gpt-6.1-sol', 100)]:
            directory = OUT / folder
            attempts = len(list(directory.glob('*.attempt-*.request.json')))
            assert attempts <= ceiling
            accepted = 0
            for path in directory.glob('*.analysis.json'):
                review = read(path)
                key = review['input_sha256']
                bundle = read(directory / (key + '.bundle.json'))
                wire, mapping = compact(bundle)
                assert wire == read(directory / (key + '.wire.json'))
                assert mapping == read(directory / (key + '.reference-map.json'))
                assert review['wire_sha256'] == contract.fingerprint(wire)
                assert review['reference_map_sha256'] == contract.fingerprint(mapping)
                assert review['requested_model'] == model
                assert key == contract.fingerprint({'bundle': bundle, 'instruction': contract.INSTRUCTION,
                                                     'schema': contract.schema(), 'model': model, 'effort': 'medium'})
                stem = directory / f"{key}.attempt-{review['winning_attempt']}"
                raw = read(Path(str(stem) + '.response.json'))
                contract.validate(raw, wire)
                assert contract.expand(raw, mapping) == review['analysis']
                assert read(Path(str(stem) + '.execution.json'))['returncode'] == 0
                events = [json.loads(line) for line in Path(str(stem) + '.events.jsonl').read_text(encoding='utf-8').splitlines() if line.startswith('{')]
                assert any(e.get('type') == 'turn.completed' for e in events)
                assert not any(e.get('item', {}).get('type') in ['command_execution', 'mcp_tool_call', 'web_search', 'file_change'] for e in events)
                accepted += 1
            review_counts[folder] = {'accepted': accepted, 'attempts': attempts, 'ceiling': ceiling}
    for record in catalogue['records']:
        if not record.get('campaign_id', '').startswith('paired-qwen06-late-v1'):
            continue
        cid = record['component_id']
        assert record['primary_test_settings'] == selection['primary_settings'].get(cid, [])
        gate = record.get('paired_gate')
        if gate:
            eligible = record['hypothesis']['best_condition'] in selection['primary_settings'].get(cid, [])
            assert gate['primary_selection_eligible'] == eligible
            assert gate['passed'] == (gate['unadjusted_gate_passed'] and eligible)
            assert (record['state'] == 'Extreme mode observed') == gate['passed']
    result = {'passed': True, 'manifest_sha256': parent_identity, 'all_stage_counts': counts,
              'selection_correction_version': selection['version'], 'primary_coordinates': selection['primary_coordinates'],
              'actual_tested_coordinates': selection['actual_tested_coordinates'],
              'review_transport_and_raw_response_checks': review_counts,
              'exact_pairs_linked_to_raw_jobs': checked_pairs, 'scope': 'SQLite integrity, all job keys, '
              'coordinate coverage, fixed checkpoints, frozen sources and exact texts/token IDs for every exported pair.'}
    write_json(OUT / 'independent-audit.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
