"""Offline UI fixture only: combine a public snapshot with synthetic formatter examples."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    target = ROOT / '.cache/lfm-view-format-fixture'
    target.mkdir(exist_ok=True)
    (target / 'SYNTHETIC-FIXTURE-DO-NOT-PUBLISH.txt').write_text('Offline view verification only. Synthetic records are not discoveries. Never prepare a public release from this directory.\n', encoding='utf-8')
    source = ROOT / read(ROOT / '.cache/publication-state.json')['directory']
    fixture = ROOT / '.cache/lfm-publisher-format-fixture'
    shutil.copytree(source / 'site-source', target / 'site-source', dirs_exist_ok=True)
    site = target / 'site-source'
    shutil.copyfile(ROOT / 'public-release/public-view.js', site / 'public-view.js')
    (target / 'scripts').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'public-release/scripts/check_public_snapshot.mjs', target / 'scripts/check_public_snapshot.mjs')
    stage = '05-neuron-pairs'; prefix = 'lfm-depth-20261127-v1-' + stage
    catalogue = read(site / 'catalogue.json')
    assert not any(r.get('campaign_id','').startswith(prefix) for r in catalogue['records']), 'Fixture requires a baseline without real pair-stage records'
    rows = [r for r in read(fixture / 'site-source/catalogue.json')['records'] if r.get('condition_record')]
    evidence = {}
    cases = read(fixture / 'campaigns/lfm-depth-20261127-v1/stages' / stage / 'pairs.json')
    for row in rows:
        row['public_finding_ref'] = 'evidence/findings/synthetic-lfm-view-fixture.json'
        name = 'abliterated' if row['campaign_id'].endswith('-abliterated') else 'original'
        evidence[row['id']] = [{'id': p['id'], 'prompt': p['prompt'], 'condition': p['condition'], 'phase': p['stage'],
            'kind': p['kind'], 'baseline': p['baseline'], 'steered': p['steered'], 'termination': p['termination']}
            for p in cases[name][row['component_id']] if p['condition'] == row['hypothesis']['best_condition']]
    catalogue['records'] += rows
    write(site / 'catalogue.json', catalogue)
    write(site / 'evidence/findings/synthetic-lfm-view-fixture.json', evidence)
    destination = site / 'evidence' / prefix
    shutil.copytree(fixture / 'site-source/evidence' / prefix, destination, dirs_exist_ok=True)
    snapshot = read(site / 'snapshot.json')
    snapshot['findings'] += len(rows)
    snapshot['findings_with_examples'] += sum(bool(v) for v in evidence.values())
    write(site / 'snapshot.json', snapshot)
    # Exercise the real assessment-index exporter against an isolated synthetic source tree.
    export_fixture = ROOT / '.cache/lfm-followup-export-fixture'
    shutil.copytree(fixture, export_fixture, dirs_exist_ok=True)
    programme = read(ROOT / 'campaigns/lfm-depth-20261127-v1/programme.json')
    programme['finite_stages'] = [stage]
    programme['scope'] = 'Synthetic offline export fixture; not measured findings.'
    program_dir = export_fixture / 'campaigns/lfm-depth-20261127-v1'
    write(program_dir / 'programme.json', programme)
    write(program_dir / 'stages' / stage / 'status.json', {'stage': 'measurements_complete', 'synthetic_fixture': True})
    (target / 'docs').mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT))
    from scripts import export_lfm_followup_public
    export_lfm_followup_public.ROOT = export_fixture
    export_lfm_followup_public.PROGRAM = program_dir
    export_lfm_followup_public.export(site)
    print(json.dumps({'fixture': str(target), 'synthetic_profile_cards_added': len(rows), 'measured_jobs_created': 0, 'real_catalogue_modified': False}))


if __name__ == '__main__': main()
