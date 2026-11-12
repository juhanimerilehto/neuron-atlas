"""Refresh catalogue presentation from preserved campaign artifacts without inference or reviews."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from reference import fingerprint
from paired06.publish import export
from audit_paired06_selection import main as selection_audit

OUT = ROOT / 'campaigns/paired-qwen06-late-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    selection_audit()
    manifest = read(OUT / 'manifest.json')
    models = {name: read(OUT / name / 'model.json') for name in ('original', 'abliterated')}
    run = SimpleNamespace(manifest=manifest, identity=fingerprint(manifest), models=models)
    validation = {name: read(OUT / name / 'validation.json') for name in models}
    reviews = {cid: read(OUT / 'reviews/validation' / (cid + '.json')) for cid in read(OUT / 'validation-plan.json')}
    if not (OUT / 'audit.json').exists():
        export(run, validation, reviews, stage='validation_complete')
        return
    assert read(OUT / 'audit.json')['passed']
    finalists = read(OUT / 'frozen-finalists.json')
    combined = {name: {cid: [] for cid in finalists} for name in models}
    for name in models:
        for stage in ('locked_test', 'long', 'replication', 'random_controls'):
            pairs = read(OUT / name / (stage + '.json'))
            for cid in finalists:
                combined[name][cid].extend(pairs[cid])
    final_reviews = {cid: read(OUT / 'reviews/locked_test' / (cid + '.json')) for cid in finalists
                     if (OUT / 'reviews/locked_test' / (cid + '.json')).exists()}
    confirmations = {cid: read(OUT / 'confirmations/locked_test' / (cid + '.json')) for cid in finalists
                     if (OUT / 'confirmations/locked_test' / (cid + '.json')).exists()}
    export(run, validation, reviews, stage='complete', final_pairs=combined,
           final_reviews=final_reviews, confirmations=confirmations)


if __name__ == '__main__':
    main()
