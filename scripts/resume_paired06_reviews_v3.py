"""Finish bounded reviews, retaining exhausted invalid reviews as explicit gaps."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import ctypes
import hashlib
import json
import msvcrt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from resume_paired06_reviews_v2 import inputs, OUT, read, Run, TransportReviewer, write_json, export, status
from audit_paired06_selection import main as audit_selection
from paired06 import analysis

VERSION = 'paired06.review-gaps.v3'


def reviews(run, combined, finalists, hypotheses, independent=False):
    folder = 'confirmations' if independent else 'reviews'
    reviewer = run.confirmation if independent else run.reviewer
    saved = OUT / folder / 'locked_test'
    failures = OUT / 'review-failures' / folder
    saved.mkdir(parents=True, exist_ok=True)
    failures.mkdir(parents=True, exist_ok=True)
    result = {}
    failed = {}
    pending = {}

    def consume(cid, future):
        try:
            result[cid] = future.result()
            write_json(saved / (cid + '.json'), result[cid])
        except RuntimeError as error:
            if str(error) != 'Two review attempts failed validation; original evidence retained':
                raise
            # No repair, synthetic score, or additional request is permitted here.
            exhausted = []
            for path in reviewer.directory.glob('*.attempt-2.error.json'):
                key = path.name.split('.')[0]
                if (reviewer.directory / (key + '.analysis.json')).exists():
                    continue
                bundle_path = reviewer.directory / (key + '.bundle.json')
                bundle = read(bundle_path)
                if bundle['phase'] == 'locked_test' and all(i['component_id'].endswith('__' + cid) for i in bundle['items']):
                    exhausted.append(key)
            assert exhausted, 'Failure lacks preserved exhausted attempts'
            failed[cid] = {'coordinate': cid, 'requested_model': reviewer.model, 'status': 'review_unavailable',
                           'reason': str(error), 'exhausted_input_sha256': sorted(exhausted),
                           'scope': 'Both original attempts remain rejected. No semantic correction or fresh attempt budget.'}
            write_json(failures / (cid + '.json'), failed[cid])
        run.progress('codex_locked_test', accepted=len(result), rejected=len(failed), total=len(finalists), independent=independent)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for index, cid in enumerate(finalists):
            path = saved / (cid + '.json')
            failure = failures / (cid + '.json')
            if path.exists():
                result[cid] = read(path)
                continue
            if failure.exists():
                failed[cid] = read(failure)
                continue
            bundle = analysis.bundle('locked_test', f'locked_test_{index}', [cid], combined, finalists, run.models, hypotheses)
            pending[cid] = pool.submit(reviewer.review, bundle)
            if len(pending) >= 4:
                first = next(iter(pending))
                consume(first, pending.pop(first))
        for cid, future in pending.items():
            consume(cid, future)
    return result, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    manifest, models, finalists, hypotheses, combined, _ = inputs()
    plan = {'version': VERSION, 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'transport': 'paired06.review-transport.v2', 'semantic_attempts_per_bundle': 2,
            'scope': 'Continue remaining primary and independent reviews under original request ceilings. '
                     'Exhausted invalid replies stay rejected and are published as review gaps. No new scores or labels are fabricated.'}
    path = OUT / 'review-gaps-v3.json'
    if path.exists():
        assert read(path) == plan
    else:
        write_json(path, plan)
    if args.dry_run:
        print(json.dumps({'version': VERSION, 'verified_bundles': len(finalists), 'provider_requests': 0}), flush=True)
        return
    with (OUT / '.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            audit_selection()
            run = Run(manifest, models)
            run.reviewer = TransportReviewer(OUT / 'codex', 'gpt-6.1-terra', 700)
            run.confirmation = TransportReviewer(OUT / 'codex-confirm', 'gpt-6.1-sol', 100)
            primary, primary_failed = reviews(run, combined, finalists, hypotheses)
            confirmation, confirm_failed = reviews(run, combined, finalists, hypotheses, True)
            validation = {name: read(OUT / name / 'validation.json') for name in models}
            validation_reviews = {cid: read(OUT / 'reviews/validation' / (cid + '.json')) for cid in read(OUT / 'validation-plan.json')}
            run.audit(validation_reviews, primary, confirmation)
            primary_coordinates = set(read(OUT / 'selection-audit-v1.json')['primary_settings'])
            gaps = {'primary': primary_failed, 'independent': confirm_failed}
            write_json(OUT / 'review-gaps.json', gaps)
            audit = read(OUT / 'audit.json')
            audit.update({'review_transport_recovery': 'paired06.review-transport.v2', 'review_gap_policy': VERSION,
                          'review_gaps': gaps, 'all_primary_finalists_reviewed': primary_coordinates <= primary.keys() & confirmation.keys()})
            write_json(OUT / 'audit.json', audit)
            export(run, validation, validation_reviews, stage='complete', final_pairs=combined, final_reviews=primary, confirmations=confirmation)
            run.progress('complete', review_gap_policy=VERSION, primary_review_gaps=len(primary_failed),
                         independent_review_gaps=len(confirm_failed), coordinates_per_model=86016,
                         shared_generated_candidates=len(read(OUT / 'shared-shortlist.json')),
                         validation_candidates=len(validation_reviews), tested_candidates=len(finalists))
        except BaseException as error:
            status('failed', error_type=type(error).__name__, error=str(error), recovery_version=VERSION)
            raise
        finally:
            if awake:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
