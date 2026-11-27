"""Copy bounded follow-up provenance and progress; never publish raw attempts or credentials."""
import json
from datetime import datetime, timezone
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
    for name in ('timing-preflight-v2.json', 'posthoc-weight-geometry-v2.json', 'adaptive-design-late-region-v1.json',
                 'posthoc-edit-rank-v1.json', 'posthoc-base-origin-v1.json', 'posthoc-creator-recipe-v1.json', 'posthoc-column-edit-map-v1.json'):
        if (PROGRAM / name).exists(): shutil.copyfile(PROGRAM / name, destination / name)
    for name in ('independent-audit.json','final-integrity-check.json','process-exit-verification.json'):
        if (PROGRAM / name).exists(): shutil.copyfile(PROGRAM / name, destination / name)
    diagnostic = PROGRAM / 'diagnostics/timing-preflight-v1-failure.json'
    if diagnostic.exists():
        (destination / 'diagnostics').mkdir(exist_ok=True)
        shutil.copyfile(diagnostic, destination / 'diagnostics' / diagnostic.name)
    for diagnostic in (PROGRAM / 'diagnostics').glob('review-*.json'):
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
        report_name = 'campaign-' + PROGRAM.name + '-' + stage_id + '.md'
        if (ROOT / 'docs' / report_name).exists():
            stage['report_ref'] = 'https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/' + report_name
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
        for filename in ('manifest.json', 'preflight.json', 'premeasurement-registration.json', 'preregistration-receipt.json', 'independent-audit.json', 'outcomes.json',
                         'selection.json', 'validation-plan.json', 'frozen-finalists.json', 'frozen-hypotheses.json', 'report-examples.json', 'report-factorial-examples.json', 'reviewer-proposals.json', 'paired-checkpoint-comparison.json', 'posthoc-token-prefix-v1.json', 'posthoc-repetition-v1.json', 'posthoc-exposure-check-v1.json', 'posthoc-pair-repeatability-v1.json', 'posthoc-rating-context-v1.json', 'review-diagnostics-latest.json'):
            if (directory / filename).exists():
                out = destination / stage_id / filename
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(directory / filename, out)
                if filename == 'review-diagnostics-latest.json':
                    stage['review_diagnostics_ref'] = out.relative_to(target).as_posix()
        if stage['audit_passed']:
            if stage_id in ('04-timing-operators','05-neuron-pairs'):
                assert json.loads((directory/'posthoc-exposure-check-v1.json').read_text(encoding='utf-8'))['passed'], 'Saved timing exposure needs independent diagnosis before public export'
            assessed = []
            pair_path = directory / 'pairs.json'
            pairs = json.loads(pair_path.read_text(encoding='utf-8'))
            for phase in ('discovery', 'validation', 'locked_test', 'sol-locked_test'):
                analysis_path = directory / 'analyses' / (phase + '.json')
                if not analysis_path.exists(): continue
                analyses = json.loads(analysis_path.read_text(encoding='utf-8'))
                for name, components in analyses.items():
                    for component, conditions in components.items():
                        for condition, item in conditions.items():
                            effect = item['effect']
                            phases = ('locked_test', 'long', 'replication') if phase.endswith('locked_test') else (phase,)
                            ids = {p['id'] for p in pairs[name][component] if p['kind'] == 'neuron' and p['condition'] == condition and p['stage'] in phases}
                            assert len(ids) == item['n']
                            entry = {'checkpoint': name, 'component': component, 'condition': condition,
                                'phase': 'locked_test' if phase.endswith('locked_test') else phase,
                                'reviewer': 'Sol' if phase.startswith('sol-') else 'Terra',
                                'label': effect['label'], 'note': effect['note'], 'change': effect['change_strength'],
                                'coherence': effect['coherence'], 'matches': item['hits'], 'n': item['n'],
                                'repetition': len(ids & set(effect['repetition_ids'])), 'collapse': len(ids & set(effect['collapse_ids'])),
                                'task_loss': len(ids & set(effect['task_loss_ids'])), 'baseline_defects': len(ids & set(effect['baseline_defect_ids'])),
                                'review_input_sha256': item['review_input_sha256']}
                            if stage_id in ('04-timing-operators','05-neuron-pairs'):
                                own = [p for p in pairs[name][component] if p['id'] in ids]
                                entry['recorded_exposure'] = {'applied':sum(p['intervention']['applied_to_generated_sequence'] for p in own), 'n':len(own)}
                            assessed.append(entry)
            if assessed:
                out = destination / stage_id / 'assessed-profile-index.json'
                out.parent.mkdir(parents=True, exist_ok=True)
                index = {'stage': stage_id, 'scope': 'All accepted condition assessments, including settings not advanced to the catalogue. Exploratory ratings are not held-out findings; omitted review groups remain explicit gaps in the outcomes.', 'assessments': assessed}
                if stage_id in ('04-timing-operators','05-neuron-pairs'):
                    index['recorded_exposure_definition'] = 'applied counts neuron cases with a recorded nonzero activation intervention before the response ended; n keeps every assigned case. This is not a count of behavioral matches. Cases ending before a scheduled window remain in the matching denominator.'
                out.write_text(json.dumps(index, ensure_ascii=False) + '\n', encoding='utf-8')
                stage['assessments_ref'] = out.relative_to(target).as_posix()
                stage['assessed_condition_reviews'] = len(assessed)
            outcome_path = directory / 'outcomes.json'
            if outcome_path.exists():
                outcome = json.loads(outcome_path.read_text(encoding='utf-8'))
                stage['qualified_conditions'] = outcome['qualified_frozen_condition_count']
                stage['review_gap_count'] = len(outcome['review_gaps'])
        for source in (ROOT / 'site-source/evidence').glob(PROGRAM.name + '-' + stage_id + '/*.json'):
            out = target / 'evidence' / source.parent.name / source.name
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, out)
        stages.append(stage)
    catalogue = json.loads((ROOT / 'site-source/catalogue.json').read_text(encoding='utf-8'))
    progress = {'program_id': PROGRAM.name, 'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Focused follow-up; counts are new measured configurations, not another exhaustive coordinate sweep.',
                'published_findings': sum(r.get('campaign_id', '').startswith(PROGRAM.name + '-') for r in catalogue['records']),
                'budgets': programme['budgets'], 'counts': totals, 'stages': stages}
    (target / 'campaign-progress-lfm-depth.json').write_text(json.dumps(progress, ensure_ascii=False) + '\n', encoding='utf-8')
    for source in (ROOT / 'docs').glob('campaign-lfm-depth-*.md'):
        shutil.copyfile(source, target.parent / 'docs' / source.name)
