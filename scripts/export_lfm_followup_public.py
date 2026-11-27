"""Copy bounded follow-up provenance and progress; never publish raw attempts or credentials."""
import json
from pathlib import Path
import shutil
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'


def export(target):
    if not (PROGRAM / 'programme.json').exists():
        return
    programme = json.loads((PROGRAM / 'programme.json').read_text(encoding='utf-8'))
    destination = target / 'evidence' / PROGRAM.name
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROGRAM / 'programme.json', destination / 'programme.json')
    for name in ('timing-preflight-v2.json',):
        if (PROGRAM / name).exists(): shutil.copyfile(PROGRAM / name, destination / name)
    diagnostic = PROGRAM / 'diagnostics/timing-preflight-v1-failure.json'
    if diagnostic.exists():
        (destination / 'diagnostics').mkdir(exist_ok=True)
        shutil.copyfile(diagnostic, destination / 'diagnostics' / diagnostic.name)
    stages = []
    totals = {'original': 0, 'abliterated': 0}
    for stage_id in programme['finite_stages']:
        directory = PROGRAM / 'stages' / stage_id
        stage = {'id': stage_id, 'stage': 'not_started', 'counts': {}}
        if (directory / 'manifest.json').exists():
            stage['stage'] = 'preregistered'
        if (directory / 'status.json').exists():
            stage.update(json.loads((directory / 'status.json').read_text(encoding='utf-8')))
        stage['audit_passed'] = (directory / 'independent-audit.json').exists() and json.loads(
            (directory / 'independent-audit.json').read_text(encoding='utf-8'))['passed']
        for name in totals:
            journal = directory / name / 'jobs.sqlite'
            count = 0
            if journal.exists():
                with sqlite3.connect(journal.resolve().as_uri() + '?mode=ro', uri=True) as db:
                    count = db.execute("SELECT count(*) FROM jobs WHERE status='complete'").fetchone()[0]
            stage['counts'][name] = count
            totals[name] += count
        for filename in ('manifest.json', 'preflight.json', 'independent-audit.json', 'outcomes.json',
                         'selection.json', 'validation-plan.json', 'frozen-finalists.json', 'frozen-hypotheses.json', 'report-examples.json'):
            if (directory / filename).exists():
                out = destination / stage_id / filename
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(directory / filename, out)
        for source in (ROOT / 'site-source/evidence').glob(PROGRAM.name + '-' + stage_id + '/*.json'):
            out = target / 'evidence' / source.parent.name / source.name
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, out)
        stages.append(stage)
    catalogue = json.loads((ROOT / 'site-source/catalogue.json').read_text(encoding='utf-8'))
    progress = {'program_id': PROGRAM.name, 'scope': 'Focused follow-up; counts are new measured configurations, not another exhaustive coordinate sweep.',
                'published_findings': sum(r.get('campaign_id', '').startswith(PROGRAM.name + '-') for r in catalogue['records']),
                'budgets': programme['budgets'], 'counts': totals, 'stages': stages}
    (target / 'campaign-progress-lfm-depth.json').write_text(json.dumps(progress, ensure_ascii=False) + '\n', encoding='utf-8')
    for source in (ROOT / 'docs').glob('campaign-lfm-depth-*.md'):
        shutil.copyfile(source, target.parent / 'docs' / source.name)
