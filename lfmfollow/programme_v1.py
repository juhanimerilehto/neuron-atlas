"""Finite detached stage queue, bounded recovery and explicit pending publication."""
import ctypes
from datetime import datetime, timezone
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time
from lfmfollow.core_v1 import ROOT, PROGRAM, MODELS, JOB_LIMIT, PRIMARY_LIMIT, SECONDARY_LIMIT, read, digest, event
from reference import write_json


def invoke(module, args, stage):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    log = PROGRAM / 'logs' / (stamp + '-' + stage + '-' + module + '.log'); log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('ab') as output:
        process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_lfm_followup.py'), module, *args],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'},
            creationflags=subprocess.CREATE_NO_WINDOW)
        event(PROGRAM, 'running', current_stage=stage, worker_pid=process.pid, log=log.relative_to(ROOT).as_posix())
        return process.wait()


def wait_for_module(module, stage):
    deadline = time.monotonic() + 12 * 3600
    while not (ROOT / 'lfmfollow' / (module + '.py')).exists():
        event(PROGRAM, 'awaiting_versioned_module', current_stage=stage, required_module=module,
              scope='Evidence and budgets retained; this stage has not started.')
        if time.monotonic() > deadline:
            raise RuntimeError('Required versioned module is pending; resume this finite queue after implementation')
        time.sleep(30)


def receipt_valid(directory):
    path = directory / 'publication-receipt.json'
    if not path.exists():
        return False
    receipt = read(path)
    assert receipt['pages_verified'] and len(receipt['commit_sha']) == 40
    assert receipt['independent_audit_sha256'] == digest(directory / 'independent-audit.json')
    return True


def main():
    PROGRAM.mkdir(parents=True, exist_ok=True)
    with (PROGRAM / '.programme.lock').open('a+b') as lock:
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            stages = read(PROGRAM / 'programme.json')['finite_stages']
            first = PROGRAM / 'stages' / stages[0]
            assert read(first / 'independent-audit.json')['passed'], 'Complete the prospective confirmation first'
            for stage in stages[1:]:
                directory = PROGRAM / 'stages' / stage
                if stage in ('04-timing-operators', '05-neuron-pairs'):
                    wait_for_module('preflight_timing_v2', stage)
                    if not (PROGRAM / 'timing-preflight-v2.json').exists():
                        assert invoke('preflight_timing_v2', [], stage) == 0, 'Timing conformance needs diagnosis before jobs'
                audit_path = directory / 'independent-audit.json'
                for attempt in range(3):
                    if audit_path.exists() and read(audit_path)['passed']:
                        break
                    code = invoke('explore_v1', [stage], stage)
                    if code == 0 and audit_path.exists() and read(audit_path)['passed']:
                        break
                    event(PROGRAM, 'recoverable_process_exit', current_stage=stage, attempt=attempt + 1,
                          returncode=code, completed_evidence_preserved=True)
                    time.sleep(15)
                else:
                    raise RuntimeError('Three process exits; frozen stage needs attention')
                wait_for_module('publish_v2', stage)
                if not (directory / 'outcomes.json').exists():
                    assert invoke('publish_v2', [stage], stage) == 0, 'Assessed export needs diagnosis'
                pending = [s for s in stages if (PROGRAM / 'stages' / s / 'independent-audit.json').exists()
                           and not receipt_valid(PROGRAM / 'stages' / s)]
                write_json(PROGRAM / 'pending-publications.json', pending)
                event(PROGRAM, 'stage_audited_and_exported', current_stage=stage, pending_publications=pending)
            audits = {stage: read(PROGRAM / 'stages' / stage / 'independent-audit.json') for stage in stages}
            counts = {name: sum(sum(a['counts'][name].values()) for a in audits.values()) for name in MODELS}
            requests = {'codex': len(list((PROGRAM / 'codex').glob('*.attempt-*.request.json'))),
                        'codex-confirm': len(list((PROGRAM / 'codex-confirm').glob('*.attempt-*.request.json')))}
            assert all(c <= JOB_LIMIT for c in counts.values()) and requests['codex'] <= PRIMARY_LIMIT and requests['codex-confirm'] <= SECONDARY_LIMIT
            write_json(PROGRAM / 'independent-audit.json', {'passed': all(a['passed'] for a in audits.values()),
                'counts': counts, 'requests': requests, 'stage_audit_sha256': {s: digest(PROGRAM / 'stages' / s / 'independent-audit.json') for s in stages},
                'review_gaps': [g for a in audits.values() for g in a['review_gaps']], 'scope': 'Finite programme count, ceiling and stage-audit aggregation.'})
            lines = ['# LFM depth programme results', '', 'Five bounded studies in the pinned LFM pair. Per-stage reports retain all assessed outcomes, controls and limitations.', '',
                     '| Study | Original configurations | Edited configurations | Assessed observations | Qualified frozen conditions |', '|---|---:|---:|---:|---:|']
            for stage in stages:
                outcome = read(PROGRAM / 'stages' / stage / 'outcomes.json'); audit = audits[stage]
                lines.append(f'| [{stage}](campaign-{PROGRAM.name}-{stage}.md) | {sum(audit["counts"]["original"].values())} | {sum(audit["counts"]["abliterated"].values())} | {outcome["observations"]} | {outcome["qualified_frozen_condition_count"]} |')
            (ROOT / 'docs' / ('campaign-' + PROGRAM.name + '.md')).write_text('\n'.join(lines) + '\n', encoding='utf-8')
            deadline = time.monotonic() + 12 * 3600
            while not all(receipt_valid(PROGRAM / 'stages' / stage) for stage in stages):
                pending = [s for s in stages if not receipt_valid(PROGRAM / 'stages' / s)]
                write_json(PROGRAM / 'pending-publications.json', pending)
                event(PROGRAM, 'awaiting_verified_publication', pending_stages=pending)
                if time.monotonic() > deadline:
                    event(PROGRAM, 'publication_pending', reason='Finite measurement queue complete; connected publication remains resumable.')
                    return
                time.sleep(30)
            write_json(PROGRAM / 'pending-publications.json', [])
            event(PROGRAM, 'complete', counts=counts, requests=requests)
        except BaseException as error:
            event(PROGRAM, 'needs_attention', error_type=type(error).__name__, error=str(error)); raise
        finally:
            if awake: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
