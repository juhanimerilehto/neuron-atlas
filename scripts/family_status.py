"""Read durable LFM/Granite progress without importing the inference runtime."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from familylab.specs import SPECS


def read_optional(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def snapshot():
    campaigns = {}
    for family, spec in SPECS.items():
        out = ROOT / 'campaigns' / spec['campaign']
        journals = {}
        for model in spec['models']:
            path = out / model / 'jobs.sqlite'
            if not path.exists():
                journals[model] = []
                continue
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=10)) as db:
                rows = db.execute("SELECT json_extract(config, '$.stage'), status, count(*) "
                                  "FROM jobs GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
            journals[model] = [{'stage': stage, 'status': status, 'count': count}
                               for stage, status, count in rows]
        audit = read_optional(out / 'independent-audit.json')
        campaigns[family] = {
            'campaign_id': spec['campaign'],
            'status': read_optional(out / 'status.json'),
            'journals': journals,
            'reviewer_requests': {folder: len(list((out / folder).glob('*.attempt-*.request.json')))
                                  for folder in ('codex', 'codex-confirm')},
            'audit': ({key: audit.get(key) for key in ('passed', 'extreme_gate_passes', 'review_gaps')}
                      if audit else None),
            'catalogue_export': read_optional(out / 'catalogue-export.json'),
            'publication_receipt': read_optional(out / 'publication-receipt.json'),
        }
    return {'queue_service': read_optional(ROOT / '.cache/family-queue-service.json'),
            'queue_state': read_optional(ROOT / '.cache/family-queue-state.json'),
            'campaigns': campaigns}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2, ensure_ascii=True))
