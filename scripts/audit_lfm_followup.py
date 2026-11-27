"""Read-only cross-stage integrity check, independent of model and reviewer execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
CHECKPOINTS = ('original', 'abliterated')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def check(partial=False, require_publication=False, verify_weights=False):
    programme = read(PROGRAM / 'programme.json')
    budgets = programme['budgets']
    totals = dict.fromkeys(CHECKPOINTS, 0)
    stages = []
    seen_prompts = set()
    pinned_models = None
    catalogue = read(ROOT / 'site-source/catalogue.json')['records']
    assert len({r['id'] for r in catalogue}) == len(catalogue)
    for stage in programme['finite_stages']:
        directory = PROGRAM / 'stages' / stage
        if not (directory / 'manifest.json').exists():
            assert partial, f'{stage}: manifest is missing'
            stages.append({'id': stage, 'checked': False})
            continue
        manifest = read(directory / 'manifest.json')
        manifest_identity = identity(manifest)
        assert manifest['stage_id'] == stage and manifest['program_id'] == PROGRAM.name
        if pinned_models is None:
            pinned_models = manifest['models']
        assert manifest['models'] == pinned_models, f'{stage}: checkpoint identity changed'
        for filename, expected in manifest['sources'].items():
            assert digest(ROOT / filename) == expected, f'{stage}: source mismatch {filename}'
        for filename, expected in manifest['protocol'].get('external_input_sha256', {}).items():
            assert digest(ROOT / filename) == expected, f'{stage}: external input mismatch {filename}'
        assert digest(directory / 'preflight.json') == manifest['preflight_sha256']
        assert digest(ROOT / 'family-runtime-lock.json') == manifest['runtime_lock_sha256']
        for name in CHECKPOINTS:
            assert digest(ROOT / 'campaigns/paired-lfm25-350m-v1' / name / 'calibration.json') == manifest['calibration_sha256'][name]
        partitions = manifest['protocol']['prompts']
        if 'random_controls' in partitions:
            assert partitions['random_controls'] == partitions['locked_test'][:8]
        prompts = [p for phase, values in partitions.items() if phase != 'random_controls' for p in values]
        assert len(prompts) == len(set(prompts)), f'{stage}: prompt partitions overlap'
        assert not seen_prompts.intersection(prompts), f'{stage}: earlier study prompts reused'
        seen_prompts.update(prompts)
        audit_path = directory / 'independent-audit.json'
        finished = audit_path.exists() and read(directory / 'status.json')['stage'] == 'measurements_complete'
        assert partial or finished, f'{stage}: measurements are incomplete'
        audit = read(audit_path) if finished else None
        if audit:
            assert audit['passed'] and audit['manifest_sha256'] == manifest_identity
            gaps = [read(p) for p in (directory / 'review-failures').glob('*.json')]
            assert sorted(map(identity, gaps)) == sorted(map(identity, audit['review_gaps']))
            for filename, source in [('posthoc-token-prefix-v1.json','lfm_token_prefix_v1.py'),
                                     ('posthoc-repetition-v1.json','lfm_repetition_diagnostics_v1.py')]:
                supplement_path = directory / filename
                if supplement_path.exists():
                    supplement = read(supplement_path)
                    assert supplement['analysis_source_sha256'] == digest(ROOT / 'scripts' / source)
                    for input_name, expected in supplement['input_sha256'].items():
                        assert digest(directory / input_name) == expected
        all_pairs = read(directory / 'pairs.json') if finished else None
        pair_count = 0
        counts = {}
        for name in CHECKPOINTS:
            path = directory / name / 'jobs.sqlite'
            if not path.exists():
                assert partial and not finished
                continue
            with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
                journal_identity = identity({'parent': manifest_identity, 'model': name})
                assert db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0] == journal_identity
                total, completed = db.execute("SELECT count(*),sum(status='complete') FROM jobs").fetchone()
                totals[name] += total
                if finished:
                    assert total == completed
                    counts[name] = dict(db.execute("SELECT json_extract(config,'$.stage'),count(*) FROM jobs GROUP BY 1"))
                    assert counts[name] == audit['counts'][name]
                    pairs = [p for values in all_pairs[name].values() for p in values]
                    assert len(pairs) == len({p['id'] for p in pairs}) == total
                    for pair in pairs:
                        row = db.execute('SELECT config,result FROM jobs WHERE id=?', (pair['id'],)).fetchone()
                        assert row, f'{stage}: missing job {pair["id"]}'
                        cfg, raw = map(json.loads, row)
                        assert pair['id'] == identity({'identity': journal_identity, 'config': cfg})
                        assert cfg == pair['config'] and cfg['prompt'] == pair['prompt']
                        assert (raw['text'], raw['token_ids']) == (pair['steered'], pair['token_ids'])
                        assert (raw['batch_baseline']['text'], raw['batch_baseline']['token_ids']) == (pair['baseline'], pair['baseline_token_ids'])
                    pair_count += len(pairs)
        if finished:
            assert pair_count == audit['exact_pairs_linked_to_raw_jobs']
            outcomes = read(directory / 'outcomes.json')
            rows = [r for r in catalogue if r.get('campaign_id', '').startswith(PROGRAM.name + '-' + stage + '-')]
            assert len(rows) == outcomes['observations']
            displayed = sum(bool((r.get('paired_gate') or {}).get('passed')) for r in rows)
            assert displayed == outcomes['qualified_frozen_condition_count'] == sum(g['passed'] for g in outcomes['condition_gates'])
            receipt_path = directory / 'publication-receipt.json'
            receipt = read(receipt_path) if receipt_path.exists() else None
            if require_publication: assert receipt, f'{stage}: verified publication receipt is missing'
            if receipt:
                assert receipt['pages_verified'] is True and len(receipt['commit_sha']) == 40 and all(c in '0123456789abcdef' for c in receipt['commit_sha'])
                assert receipt['independent_audit_sha256'] == digest(audit_path)
                completion = read(directory / 'completion.json')
                assert completion['independent_audit_sha256'] == digest(audit_path)
                assert completion['report_sha256'] == digest(ROOT / completion['report'])
                assert completion['outcomes_sha256'] == digest(directory / 'outcomes.json')
        stages.append({'id': stage, 'checked': True, 'measurements_complete': finished,
                       'manifest_identity': manifest_identity, 'counts': counts, 'exact_pairs_checked': pair_count,
                       'verified_publication_commit': receipt['commit_sha'] if finished and receipt else None})
    requests = {folder: len(list((PROGRAM / folder).glob('*.attempt-*.request.json'))) for folder in ('codex', 'codex-confirm')}
    assert all(n <= budgets['configurations_per_checkpoint'] for n in totals.values())
    assert requests['codex'] <= budgets['primary_reviewer_requests'] and requests['codex-confirm'] <= budgets['secondary_reviewer_requests']
    supplements_checked = []
    for filename, source_name in [('posthoc-weight-geometry.json','lfm_weight_geometry.py'),
                                  ('posthoc-weight-geometry-v2.json','lfm_weight_geometry_v2.py'),
                                  ('posthoc-edit-rank-v1.json','lfm_edit_rank_v1.py'),
                                  ('posthoc-creator-recipe-v1.json','lfm_creator_recipe_v1.py'),
                                  ('posthoc-column-edit-map-v1.json','lfm_column_edit_map_v1.py')]:
        path = PROGRAM / filename
        if not path.exists(): continue
        supplement = read(path)
        assert supplement['analysis_source_sha256'] == digest(ROOT / 'scripts' / source_name)
        for key in ('geometry_input_sha256','geometry_sha256'):
            if key in supplement: assert supplement[key] == digest(PROGRAM / 'posthoc-weight-geometry-v2.json')
        if 'predecessor_sha256' in supplement:
            assert supplement['predecessor_sha256'] == digest(PROGRAM / 'posthoc-weight-geometry.json')
        if 'already_frozen_timing_manifest_sha256' in supplement:
            assert supplement['already_frozen_timing_manifest_sha256'] == digest(PROGRAM / 'stages/04-timing-operators/manifest.json')
        supplements_checked.append(filename)
    origin_path = PROGRAM / 'posthoc-base-origin-v1.json'
    if origin_path.exists():
        origin = read(origin_path)
        assert origin['metadata_response_sha256'] == digest(PROGRAM / 'diagnostics/upstream-base-origin-response.json')
        assert origin['campaign_weight_sha256'] == pinned_models['original']['files']['model.safetensors']['sha256']
        assert origin['creator_revision_weight_sha256'] == origin['campaign_weight_sha256'] and origin['identical_weight_file'] is True
        supplements_checked.append(origin_path.name)
    if verify_weights:
        for name, expected in pinned_models.items():
            model = read(ROOT / 'campaigns/paired-lfm25-350m-v1' / name / 'model.json')
            assert (model['repository'], model['revision']) == (expected['repository'], expected['revision'])
            for filename, info in expected['files'].items():
                path = Path(model['snapshot']) / filename
                assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256'], f'Checkpoint file changed: {name}/{filename}'
    complete = all(s.get('measurements_complete') for s in stages)
    if complete and (PROGRAM / 'independent-audit.json').exists():
        aggregate = read(PROGRAM / 'independent-audit.json')
        assert aggregate['passed'] and aggregate['counts'] == totals and aggregate['requests'] == requests
        for stage, expected in aggregate['stage_audit_sha256'].items():
            assert digest(PROGRAM / 'stages' / stage / 'independent-audit.json') == expected
    return {'passed': True, 'programme_complete': complete, 'partial_check': partial,
            'checker_source_sha256': digest(Path(__file__)),
            'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'configurations_including_pending': totals,
            'requests': requests, 'stages': stages, 'weights_rehashed': verify_weights,
            'supplementary_source_input_checks': supplements_checked,
            'publication_receipts_required': require_publication,
            'scope': 'Independent read-only journal, identity, frozen-source, prompt-disjointness, catalogue and ceiling checks. Does not replace raw reviewer schema replay or deployment byte verification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partial', action='store_true')
    parser.add_argument('--require-publication', action='store_true')
    parser.add_argument('--verify-weights', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check(args.partial, args.require_publication, args.verify_weights)
    payload = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
    print(payload)
