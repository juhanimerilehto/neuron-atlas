"""Independent evidence linkage, grid coverage, review transport and budget audit."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from reference import fingerprint, write_json
from familylab import analysis, data

OUT = ROOT / 'campaigns' / data.CAMPAIGN


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def audit():
    manifest = read(OUT / 'manifest.json')
    identity = fingerprint(manifest)
    assert hashlib.sha256((ROOT / 'family-runtime-lock.json').read_bytes()).hexdigest() == manifest['runtime_lock_sha256']
    from familylab.runtime import verify
    verify()
    if manifest.get('parent_provenance_sha256'):
        assert hashlib.sha256((OUT / 'parent-provenance.json').read_bytes()).hexdigest() == manifest['parent_provenance_sha256']
    for path, digest in manifest['sources'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    for filename, field in [('prefix-bank.json', 'prefix_bank_sha256'), ('preflight.json', 'preflight_sha256'),
                            ('selection.json', 'selection_metadata_sha256'), ('weight-comparison.json', 'weight_comparison_sha256')]:
        assert hashlib.sha256((OUT / filename).read_bytes()).hexdigest() == manifest[field]
    for name in data.MODELS:
        model = read(OUT / name / 'model.json')
        for filename, expected in model['files'].items():
            path = Path(model['weight_path']) if filename == 'model.safetensors' else Path(model['snapshot']) / filename
            with path.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected['sha256'], filename
        for filename, field in [('calibration.json', 'calibration_sha256'), ('native-calibration.json', 'native_calibration_sha256')]:
            assert hashlib.sha256((OUT / name / filename).read_bytes()).hexdigest() == manifest[field][name]
    bank = read(OUT / 'prefix-bank.json')
    counts, pair_count = {}, 0
    for name in data.MODELS:
        coverage, generated, stages = {}, {}, {}
        journal_identity = fingerprint({'parent': identity, 'model': name})
        with sqlite3.connect(f'file:{(OUT / name / "jobs.sqlite").as_posix()}?mode=ro', uri=True) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            for key, cfg_json, result_json, state in db.execute('SELECT id,config,result,status FROM jobs'):
                assert state == 'complete'
                cfg, result = json.loads(cfg_json), json.loads(result_json)
                assert key == fingerprint({'identity': journal_identity, 'config': cfg})
                assert 0 <= cfg['layer'] < data.LAYERS and 0 <= cfg['neuron'] < data.WIDTH
                stages[cfg['stage']] = stages.get(cfg['stage'], 0) + 1
                if cfg['type'] == 'distribution':
                    assert result['checkpoints'] == bank[cfg['prompt']]['checkpoints']
                    assert len(result['js']) == len(result['checkpoints'])
                    assert all(0 <= value <= .694 for value in result['js'])
                    if cfg['stage'] == 'screen':
                        coverage.setdefault(cfg['coordinate'], set()).add(cfg['setting'])
                else:
                    generated[fingerprint({'identity': identity, 'model': name, 'config': cfg})] = (cfg, result)
        assert sum(stages.values()) <= data.JOB_CEILING
        assert stages['screen'] == data.COORDINATES * len(data.BROAD)
        assert len(coverage) == data.COORDINATES and all(v == set(data.BROAD) for v in coverage.values())
        for stage in ('discovery', 'validation', 'locked_test', 'long', 'replication', 'random_controls'):
            seen = set()
            for cid, cases in read(OUT / name / (stage + '.json')).items():
                for pair in cases:
                    cfg, measured = generated[pair['id']]
                    assert pair['id'] not in seen
                    seen.add(pair['id'])
                    assert cfg['coordinate'] == cid and cfg['stage'] == pair['stage'] == stage
                    assert (pair['prompt'], pair['condition'], pair['random_index']) == (cfg['prompt'], cfg['setting'], cfg.get('random_index'))
                    assert pair['baseline'] == measured['batch_baseline']['text']
                    assert pair['baseline_token_ids'] == measured['batch_baseline']['token_ids']
                    assert pair['steered'] == measured['text'] and pair['token_ids'] == measured['token_ids']
                    assert pair['termination'] == measured['termination'] and pair['intervention'] == measured['intervention']
                    pair_count += 1
            assert len(seen) == stages.get(stage, 0)
        counts[name] = stages
    reviewers = {}
    for folder, model, ceiling in [('codex', 'gpt-6.1-terra', 700), ('codex-confirm', 'gpt-6.1-sol', 100)]:
        directory = OUT / folder
        requests = len(list(directory.glob('*.attempt-*.request.json')))
        assert requests <= ceiling
        accepted = 0
        for path in directory.glob('*.analysis.json'):
            review = read(path)
            key = review['input_sha256']
            bundle = read(directory / (key + '.bundle.json'))
            wire, mapping = analysis.compact(bundle)
            assert wire == read(directory / (key + '.wire.json'))
            assert mapping == read(directory / (key + '.reference-map.json'))
            assert review['wire_sha256'] == fingerprint(wire) and review['reference_map_sha256'] == fingerprint(mapping)
            assert review['requested_model'] == model
            assert key == fingerprint({'bundle': bundle, 'instruction': analysis.contract.INSTRUCTION,
                                       'schema': analysis.contract.schema(), 'model': model, 'effort': 'medium'})
            stem = directory / f"{key}.attempt-{review['winning_attempt']}"
            raw = read(Path(str(stem) + '.response.json'))
            analysis.validate(raw, wire)
            assert analysis.contract.expand(raw, mapping) == review['analysis']
            assert read(Path(str(stem) + '.execution.json'))['returncode'] == 0
            events = [json.loads(line) for line in Path(str(stem) + '.events.jsonl').read_text(encoding='utf-8').splitlines() if line.startswith('{')]
            assert any(e.get('type') == 'turn.completed' for e in events)
            assert not any(e.get('item', {}).get('type') in ['command_execution', 'mcp_tool_call', 'web_search', 'file_change'] for e in events)
            accepted += 1
        reviewers[folder] = {'accepted': accepted, 'requests': requests, 'ceiling': ceiling}
    finalists = read(OUT / 'frozen-finalists.json')
    assert len(finalists) <= 12 and all(len(settings) <= 2 for settings in finalists.values())
    from familylab.campaign import Run
    validation_reviews = {p.stem: read(p) for p in (OUT / 'reviews/validation').glob('*.json')}
    validation_pairs = {name: read(OUT / name / 'validation.json') for name in data.MODELS}
    assert Run.nominations(None, validation_reviews, validation_pairs, 'validation', 6, 0) == finalists
    settings_by_phase = {'discovery': read(OUT / 'discovery-settings.json'), 'validation': read(OUT / 'validation-plan.json'), 'locked_test': finalists}
    for phase, settings in settings_by_phase.items():
        folders = ('reviews', 'confirmations') if phase == 'locked_test' else ('reviews',)
        for folder in folders:
            accepted = {p.stem for p in (OUT / folder / phase).glob('*.json')}
            failed = {p.stem for p in (OUT / 'review-failures' / folder / phase).glob('*.json')}
            assert accepted.isdisjoint(failed) and accepted | failed == settings.keys()
            for cid in failed:
                failure = read(OUT / 'review-failures' / folder / phase / (cid + '.json'))
                directory = OUT / ('codex' if folder == 'reviews' else 'codex-confirm')
                key = failure['input_sha256']
                assert (directory / (key + '.attempt-2.error.json')).exists()
                assert not (directory / (key + '.analysis.json')).exists()
    records = [r for r in read(ROOT / 'site-source/catalogue.json')['records'] if r.get('campaign_id', '').startswith(data.CAMPAIGN)]
    for record in records:
        gate = record.get('paired_gate')
        if gate:
            assert record['component_id'] in finalists
            assert record['hypothesis']['best_condition'] in finalists[record['component_id']]
            assert (record['state'] == 'Extreme mode observed') == gate['passed']
            if gate.get('review_status') == 'incomplete':
                assert not gate['passed'] and record['state'] == 'Final review incomplete'
    result = {'passed': True, 'campaign_id': data.CAMPAIGN, 'manifest_sha256': identity, 'all_stage_counts': counts,
              'reviewers': reviewers, 'exact_pairs_linked_to_raw_jobs': pair_count, 'catalogue_records': len(records),
              'extreme_gate_passes': sum(bool((r.get('paired_gate') or {}).get('passed')) for r in records),
              'review_gaps': [read(p) for p in (OUT / 'review-failures').glob('*/*/*.json')],
              'scope': 'All job identities, full coordinate grid, exact saved pairs, raw accepted review linkage, frozen sources, request ceilings and explicit missing reviews.'}
    write_json(OUT / 'independent-audit.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    audit()
