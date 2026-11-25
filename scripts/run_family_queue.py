"""Finite detached queue: measured LFM -> verified publication -> measured Granite -> publication."""
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from familylab.specs import SPECS
STATE = ROOT / '.cache/family-queue-state.json'
EVENTS = ROOT / '.cache/family-queue-events.jsonl'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def event(stage, **fields):
    value = {'queue_id': 'lfm-then-granite-20261125-v1', 'stage': stage,
             'timestamp_utc': datetime.now(timezone.utc).isoformat(), **fields}
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(STATE)
    with EVENTS.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value) + '\n')
    print(json.dumps(value), flush=True)


def validate_receipt(out):
    receipt = out / 'publication-receipt.json'
    if not receipt.exists():
        return False
    value = read(receipt)
    assert value['campaign_id'] == out.name and value['pages_verified'] is True
    assert value['independent_audit_sha256'] == hashlib.sha256((out / 'independent-audit.json').read_bytes()).hexdigest()
    assert len(value['commit_sha']) == 40
    return True


def main():
    with (ROOT / '.cache/family-queue.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        for family in ('lfm', 'granite'):
            out = ROOT / 'campaigns' / SPECS[family]['campaign']
            assert read(out / 'preflight.json')['passed']
            assert (out / 'manifest.json').exists()
            status = out / 'status.json'
            for attempt in range(3):
                if status.exists() and read(status)['stage'] == 'complete':
                    break
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                log = out / 'logs' / (stamp + '-campaign.log')
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open('ab') as stream:
                    process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_family.py'), family, 'campaign'],
                        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                        env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'},
                        creationflags=subprocess.CREATE_NO_WINDOW)
                    event('running', family=family, campaign_id=out.name, worker_pid=process.pid,
                          log=log.relative_to(ROOT).as_posix(), recovery_attempt=attempt)
                    code = process.wait()
                if code == 0 and status.exists() and read(status)['stage'] == 'complete':
                    break
                event('recoverable_process_exit', family=family, returncode=code, recovery_attempt=attempt,
                      evidence_preserved=True)
                time.sleep(15)
            else:
                event('needs_attention', family=family, reason='Three process exits; evidence and budgets retained')
                return
            assert read(out / 'independent-audit.json')['passed']
            if not validate_receipt(out):
                event('awaiting_verified_publication', family=family, campaign_id=out.name,
                      next_action='Prepare snapshot, publish with expected-head lease, verify Pages, write publication-receipt.json')
                deadline = time.monotonic() + 12 * 3600
                while not validate_receipt(out):
                    if time.monotonic() > deadline:
                        event('publication_pending', family=family, campaign_id=out.name,
                              reason='Safe publication barrier retained; rerun launcher after publication to continue')
                        return
                    time.sleep(15)
            event('campaign_complete', family=family, campaign_id=out.name)
        event('complete', campaigns=[x['campaign'] for x in SPECS.values()])


if __name__ == '__main__':
    main()
