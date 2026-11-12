"""Publish measured validation records and final decisions into the existing catalogue."""
import copy
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from paired06 import data, analysis
from reference import write_json


def old_pair(pair):
    return {'id': pair['id'], 'prompt': pair['prompt'], 'condition': pair['condition'], 'stage': pair['stage'],
            'random_index': pair['random_index'],
            'baseline': {'text': pair['baseline'], 'token_ids': pair['baseline_token_ids']},
            'steered': {'text': pair['steered'], 'token_ids': pair['token_ids'], 'termination': pair['termination'],
                        'intervention': pair['intervention']}, 'metrics': pair['diagnostics']}


def interpretation(item, effect, review):
    return {'review_input_sha256': review['input_sha256'], 'hypothesis': {
        'label': effect['label'], 'summary': effect['note'], 'best_condition': effect['condition'],
        'extremity': effect['change_strength'], 'length_only': False,
        'coherent_change_ids': [key for key in effect['matching_ids'] if key not in effect['collapse_ids']] if effect['coherence'] >= 3 else [],
        'dramatic_change_ids': effect['matching_ids'],
        'degeneration_ids': sorted(set(effect['collapse_ids'] + effect['repetition_ids'])),
        'contradicting_ids': [], 'alternative_explanations': [], 'followup_proposals': item['followup_tests']}}


def decision(effect, pairs, supported=True):
    by_stage = {stage: {p['id'] for p in pairs if p['kind'] == 'neuron' and p['condition'] == effect['condition'] and p['stage'] == stage}
                for stage in ('locked_test', 'long', 'replication')}
    selected = set().union(*by_stage.values())
    matches = set(effect['matching_ids'])
    hits = {stage: len(matches & ids) for stage, ids in by_stage.items()}
    repetition = len(set(effect['repetition_ids']) & selected)
    collapse = len(set(effect['collapse_ids']) & selected)
    passed = (supported and effect['change_strength'] >= 3 and effect['coherence'] >= 3
              and hits['locked_test'] >= 8 and hits['long'] >= 4 and hits['replication'] >= 4
              and repetition <= 2 and collapse <= 2)
    return {'passed': bool(passed), 'matches': hits, 'repetition_flags': repetition, 'collapse_flags': collapse,
            'change': effect['change_strength'], 'coherence': effect['coherence'], 'hypothesis_supported': supported}


def export(run, validation, validation_reviews, stage, final_pairs=None, final_reviews=None, confirmations=None):
    out = ROOT / 'campaigns' / data.CAMPAIGN
    site = ROOT / 'site-source'
    catalogue_path = site / 'catalogue.json'
    catalogue = json.loads(catalogue_path.read_text(encoding='utf-8'))
    records = []
    comparisons = []
    for cid, review in validation_reviews.items():
        compared = {'coordinate': cid, 'checkpoints': {}}
        for name in data.MODELS:
            model = run.models[name]
            component_id = name + '__' + cid
            item = next(item for item in review['analysis']['items'] if item['component_id'] == component_id)
            effect = analysis.best(item, 'validation', validation[name][cid])
            if final_pairs and cid in final_pairs[name]:
                frozen = json.loads((out / 'frozen-finalists.json').read_text(encoding='utf-8'))[cid]
                nominated_item = {**item, 'condition_effects': [e for e in item['condition_effects'] if e['condition'] in frozen]}
                effect = analysis.best(nominated_item, 'validation', validation[name][cid])
            campaign_id = data.CAMPAIGN + '-' + name
            layer, neuron = cid.split('-N')
            state = 'Validation observation'
            detail = {'id': campaign_id + '-' + cid, 'component_id': cid, 'campaign_id': campaign_id,
                      'measurement_type': 'open_ended_neuron', 'model': 'Qwen3-0.6B' if name == 'original' else 'Huihui-Qwen3-0.6B-abliterated-v2',
                      'repository': model['repository'], 'revision': model['revision'], 'synthetic': False,
                      'manifest_sha256': run.identity, 'calibration_sha256': run.manifest['calibration_sha256'][name],
                      'label': effect['label'] or f'No supported qualitative label · {cid}', 'summary': effect['note'],
                      'category': 'Other', 'state': state, 'effect': effect['change_strength'], 'n': effect['n'],
                      'layer': int(layer[1:]), 'neuron': int(neuron), 'mlp_width': 3072, 'layer_count': 28,
                      'hypothesis': interpretation(item, effect, review)['hypothesis'],
                      'validation_analysis': interpretation(item, effect, review), 'calibration_contexts': 16,
                      'condition_assessments': item['condition_effects'],
                      'validation_pairs': [old_pair(pair) for pair in validation[name][cid]],
                      'paired_checkpoint': True, 'dose_unit': 'Signed multiple of the original checkpoint calibration maximum',
                      'operator': run.manifest['intervention'], 'score_axes': {'change': effect['change_strength'], 'coherence': effect['coherence']},
                      'validation_hits': effect['hits'], 'source_coordinate': cid,
                      'artifact_url': f'evidence/{campaign_id}/{cid}.json'}
            final_decision = None
            if final_pairs and cid in final_pairs[name]:
                pairs = final_pairs[name][cid]
                final_item = next(item for item in final_reviews[cid]['analysis']['items'] if item['component_id'] == component_id)
                confirm_item = next(item for item in confirmations[cid]['analysis']['items'] if item['component_id'] == component_id)
                final_effect = next((e for e in final_item['condition_effects'] if e['condition'] == effect['condition']), None)
                confirm_effect = next((e for e in confirm_item['condition_effects'] if e['condition'] == effect['condition']), None)
                if final_effect and confirm_effect:
                    primary = decision(final_effect, pairs, final_effect['hypothesis_supported'] is True)
                    independent = decision(confirm_effect, pairs, confirm_effect['hypothesis_supported'] is True)
                    passed = (primary['passed'] and independent['passed'] and effect['change_strength'] >= 3
                              and effect['coherence'] >= 3 and effect['hits'] >= 4)
                    final_decision = {'passed': passed, 'primary': primary, 'independent': independent,
                                      'scope': run.manifest['gate']}
                    detail['state'] = 'Extreme mode observed' if passed else 'Tested observation'
                    detail['test_analysis'] = interpretation(final_item, final_effect, final_reviews[cid])
                    detail['confirmation_analysis'] = interpretation(confirm_item, confirm_effect, confirmations[cid])
                for field, phases in [('test_pairs', ['locked_test']), ('long_pairs', ['long']),
                                      ('replication_pairs', ['replication']), ('control_pairs', ['random_controls'])]:
                    detail[field] = [old_pair(pair) for pair in pairs if pair['stage'] in phases]
            detail['paired_gate'] = final_decision
            write_json(site / detail['artifact_url'], detail)
            summary_fields = ('id', 'component_id', 'campaign_id', 'measurement_type', 'model', 'repository', 'revision',
                              'synthetic', 'manifest_sha256', 'calibration_sha256', 'label', 'summary', 'category',
                              'state', 'effect', 'n', 'layer', 'neuron', 'mlp_width', 'layer_count', 'hypothesis',
                              'artifact_url', 'paired_checkpoint', 'score_axes', 'validation_hits', 'paired_gate')
            record = {key: detail[key] for key in summary_fields}
            record['detail_ref'] = True
            records.append(record)
            compared['checkpoints'][name] = {'record_id': detail['id'], 'setting': effect['condition'],
                                             'label': effect['label'], 'validation_hits': effect['hits'],
                                             'validation_n': effect['n'], 'state': detail['state'], 'final_gate': final_decision}
            evidence_dir = site / 'evidence' / campaign_id
            for review_name, values, folder in [('validation', review, 'codex'),
                                               ('test', (final_reviews or {}).get(cid), 'codex'),
                                               ('confirmation', (confirmations or {}).get(cid), 'codex-confirm')]:
                if not values:
                    continue
                key = values['input_sha256']
                for suffix in ('analysis', 'reference-map'):
                    source = out / folder / f'{key}.{suffix}.json'
                    destination = evidence_dir / folder / source.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
            for source, filename in [(out / 'manifest.json', 'manifest.json'), (out / name / 'calibration.json', 'calibration.json'),
                                     (out / 'preflight.json', 'conformance.json')]:
                shutil.copyfile(source, evidence_dir / filename)
            if (out / 'audit.json').exists():
                shutil.copyfile(out / 'audit.json', evidence_dir / 'audit.json')
        comparisons.append(compared)
    keep = [r for r in catalogue['records'] if not r.get('campaign_id', '').startswith(data.CAMPAIGN)]
    catalogue['records'] = keep + records
    catalogue['paired06'] = {'campaign_id': data.CAMPAIGN, 'stage': stage,
                              'records': len(records), 'comparison_ref': 'evidence/' + data.CAMPAIGN + '/comparison.json'}
    write_json(site / catalogue['paired06']['comparison_ref'], {'campaign_id': data.CAMPAIGN, 'stage': stage,
                                                               'scope': run.manifest['scope'], 'coordinates': comparisons})
    write_json(catalogue_path, catalogue)
    write_json(out / 'catalogue-export.json', {'stage': stage, 'records': len(records),
                                               'passed': sum(r['state'] == 'Extreme mode observed' for r in records),
                                               'comparisons': len(comparisons)})
    print(json.dumps({'catalogue_updated': True, 'records_added': len(records), 'stage': stage}), flush=True)
