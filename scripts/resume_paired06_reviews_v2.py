"""Review-only continuation after the preserved over-limit requests; never reruns inference."""
import argparse
import ctypes
import hashlib
import json
import msvcrt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from paired06.campaign import Run, prepare, read, status, OUT
from paired06 import analysis
from reference import fingerprint, write_json
from paired06.publish import export
from paired06_review_transport_v2 import VERSION, TransportReviewer, compact, versioned, original_compact
from audit_paired06_selection import main as audit_selection


def inputs():
    manifest, models = prepare()
    finalists = read(OUT / 'frozen-finalists.json')
    hypotheses = read(OUT / 'frozen-hypotheses.json')
    combined = {name: {cid: [] for cid in finalists} for name in models}
    for name in models:
        for stage in ('locked_test', 'long', 'replication', 'random_controls'):
            pairs = read(OUT / name / (stage + '.json'))
            for cid in finalists:
                combined[name][cid].extend(pairs[cid])
    sizes = {}
    for i, cid in enumerate(finalists):
        bundle = analysis.bundle('locked_test', f'locked_test_{i}', [cid], combined, finalists, models, hypotheses)
        old_wire, old_map = original_compact(bundle)
        revised = versioned(bundle)
        wire, mapping = compact(revised)
        assert mapping == old_map and wire['baselines'] == old_wire['baselines']
        for before, after in zip(old_wire['items'], wire['items']):
            assert before['settings'] == after['settings']
            assert len(before['pairs']) == len(after['pairs'])
            for a, b in zip(before['pairs'], after['pairs']):
                assert {k: v for k, v in a.items() if k not in {'token_ids', 'baseline_token_ids', 'intervention', 'diagnostics'}} == b
        prompt = analysis.contract.INSTRUCTION + '\nEVIDENCE:\n' + json.dumps(wire, ensure_ascii=False)
        assert len(prompt) < 950000
        sizes[cid] = {'prompt_characters': len(prompt), 'pairs': sum(len(i['pairs']) for i in wire['items'])}
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in
              [Path(__file__), ROOT / 'scripts/paired06_review_transport_v2.py']}
    plan = {'version': VERSION, 'manifest_sha256': fingerprint(manifest), 'sources_sha256': hashes,
            'failed_input_sha256': '0d7ea2c68b92ee7225c9c8211f16d1e731712adf1aae169c11ce944c508708ba',
            'scope': 'Only review transport changes. Full text evidence, references, settings, models, '
                     'prompts, hypotheses, semantic instructions and all measurements are preserved. '
                     'Token arrays and numerical worker metadata stay in the full raw bundles. '
                     'Old attempts remain counted in the original 700/100 ceilings. Existing accepted reviews are reused.',
            'sizes': sizes, 'primary_request_ceiling': 700, 'confirmation_request_ceiling': 100}
    path = OUT / 'review-transport-v2.json'
    if path.exists():
        assert read(path) == plan, 'Versioned recovery inputs or sources changed'
    else:
        write_json(path, plan)
    return manifest, models, finalists, hypotheses, combined, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    manifest, models, finalists, hypotheses, combined, plan = inputs()
    if args.dry_run:
        print(json.dumps({'version': VERSION, 'verified_bundles': len(finalists),
                          'largest_prompt_characters': max(x['prompt_characters'] for x in plan['sizes'].values()),
                          'full_text_and_reference_equivalence': True}), flush=True)
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
            primary = run.reviews('locked_test', combined, finalists, hypotheses)
            confirmation = run.reviews('locked_test', combined, finalists, hypotheses, True)
            validation = {name: read(OUT / name / 'validation.json') for name in models}
            reviews = {cid: read(OUT / 'reviews/validation' / (cid + '.json')) for cid in read(OUT / 'validation-plan.json')}
            run.audit(reviews, primary, confirmation)
            audit = read(OUT / 'audit.json')
            audit['review_transport_recovery'] = VERSION
            write_json(OUT / 'audit.json', audit)
            export(run, validation, reviews, stage='complete', final_pairs=combined, final_reviews=primary, confirmations=confirmation)
            run.progress('complete', review_transport=VERSION, coordinates_per_model=86016,
                         shared_generated_candidates=len(read(OUT / 'shared-shortlist.json')),
                         validation_candidates=len(reviews), tested_candidates=len(finalists))
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
