"""Read the finite LFM programme without loading a model or changing evidence."""
import argparse
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'


def optional(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def snapshot():
    programme = optional(PROGRAM / 'programme.json')
    if not programme: return {'status': 'not_created'}
    totals = {'original': 0, 'abliterated': 0}; stages = []
    for stage in programme['finite_stages']:
        directory = PROGRAM / 'stages' / stage
        journals = {}
        for name in totals:
            path = directory / name / 'jobs.sqlite'
            rows = []
            if path.exists():
                with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
                    rows = [{'phase': p, 'status': s, 'count': n} for p, s, n in db.execute(
                        "SELECT json_extract(config,'$.stage'),status,count(*) FROM jobs GROUP BY 1,2")]
                totals[name] += sum(r['count'] for r in rows if r['status'] == 'complete')
            journals[name] = rows
        audit = optional(directory / 'independent-audit.json')
        outcome = optional(directory / 'outcomes.json')
        stages.append({'id': stage, 'status': optional(directory / 'status.json'), 'journals': journals,
            'audit_passed': audit['passed'] if audit else None,
            'outcome': {k: outcome.get(k) for k in ('observations','qualified_frozen_condition_count','review_gaps')} if outcome else None,
            'published': (optional(directory / 'publication-receipt.json') or {}).get('pages_verified', False)})
    return {'recorded_service': optional(ROOT / '.cache/lfm-followup-service.json'),
        'status': optional(PROGRAM / 'status.json'), 'completed_configurations': totals,
        'reviewer_requests': {folder: len(list((PROGRAM / folder).glob('*.attempt-*.request.json'))) for folder in ('codex','codex-confirm')},
        'budgets': programme['budgets'], 'stages': stages,
        'last_verified_publication': optional(ROOT / '.cache/publication-state.json'),
        'publication_outbox': optional(ROOT / '.cache/lfm-followup-publication-outbox.json')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--compact', action='store_true'); args = parser.parse_args()
    value = snapshot()
    if args.compact and value.get('stages'):
        value = {k: value[k] for k in ('status','completed_configurations','reviewer_requests','budgets')} | {
            'stages': [{k: s[k] for k in ('id','audit_passed','outcome','published')} for s in value['stages']]}
    print(json.dumps(value, indent=2, ensure_ascii=True))
