"""Derive dose-specific confirmation outcomes and append new records without rewriting history."""
from collections import Counter
from pathlib import Path
from lfmfollow.core_v1 import ROOT, PROGRAM, PARENT, MODELS, digest, read
from lfmfollow.confirmation_v1 import STAGE
from reference import write_json


def decision(effect, pairs, thresholds):
    selected = [p for p in pairs if p['kind'] == 'neuron' and p['condition'] == effect['condition']]
    phases = {phase: {p['id'] for p in selected if p['stage'] == phase}
              for phase in ('locked_test', 'long', 'replication')}
    assert {k: len(v) for k, v in phases.items()} == {'locked_test': 16, 'long': 8, 'replication': 8}
    ids = set().union(*phases.values())
    hits = {k: len(v & set(effect['matching_ids'])) for k, v in phases.items()}
    repetition, collapse = (len(ids & set(effect[k])) for k in ('repetition_ids', 'collapse_ids'))
    passed = (effect['hypothesis_supported'] is True and effect['change_strength'] >= thresholds['change_min']
        and effect['coherence'] >= thresholds['coherence_min'] and hits['locked_test'] >= thresholds['heldout_matches_min']
        and hits['long'] >= thresholds['long_matches_min'] and hits['replication'] >= thresholds['replication_matches_min']
        and repetition <= thresholds['repetition_max'] and collapse <= thresholds['collapse_max'])
    controls = {p['id'] for p in pairs if p['kind'] == 'random_direction' and p['condition'] == effect['condition']}
    assert len(controls) == 32
    return {'passed': passed, 'matches': hits, 'repetition_flags': repetition, 'collapse_flags': collapse,
            'change': effect['change_strength'], 'coherence': effect['coherence'],
            'hypothesis_supported': effect['hypothesis_supported'],
            'task_loss': len(ids & set(effect['task_loss_ids'])), 'baseline_defects': len(ids & set(effect['baseline_defect_ids'])),
            'random_matches': len(controls & set(effect['similar_random_ids']))}


def interpretation(effect, review):
    return {'review_input_sha256': review['input_sha256'], 'hypothesis': {
        'label': effect['label'], 'summary': effect['note'], 'best_condition': effect['condition'],
        'extremity': effect['change_strength'], 'length_only': False,
        'coherent_change_ids': effect['matching_ids'] if effect['coherence'] >= 3 else [],
        'dramatic_change_ids': effect['matching_ids'], 'degeneration_ids': sorted(set(effect['repetition_ids'] + effect['collapse_ids']))}}


def old_pair(pair):
    return {'id': pair['id'], 'prompt': pair['prompt'], 'condition': pair['condition'], 'stage': pair['stage'],
        'random_index': pair['random_index'], 'baseline': {'text': pair['baseline'], 'token_ids': pair['baseline_token_ids']},
        'steered': {'text': pair['steered'], 'token_ids': pair['token_ids'], 'termination': pair['termination'], 'intervention': pair['intervention']}}


def main():
    audit = read(STAGE / 'independent-audit.json'); assert audit['passed'] and not audit['review_gaps']
    manifest = read(STAGE / 'manifest.json'); cases = read(STAGE / 'pairs.json'); cid = 'L2-N3420'
    primary = read(STAGE / 'reviews/locked_test' / (cid + '.json'))
    independent = read(STAGE / 'confirmations/locked_test' / (cid + '.json'))
    prior = read(PARENT / 'reviews/validation' / (cid + '.json'))
    base = PROGRAM.name + '-' + STAGE.name
    outcomes, records = [], []
    clean_prompts = []
    for name, alias in [('original', 'A'), ('abliterated', 'B')]:
        effects = [next(e for i in r['analysis']['items'] if i['component_id'] == alias + '__' + cid
                        for e in i['condition_effects'] if e['condition'] == 'p9') for r in (primary, independent)]
        matched = set(effects[0]['matching_ids']) & set(effects[1]['matching_ids'])
        excluded = set().union(*(set(e[k]) for e in effects for k in ('baseline_defect_ids', 'collapse_ids', 'repetition_ids')))
        clean_prompts.append({p['prompt'] for p in cases[name][cid] if p['stage'] == 'locked_test' and p['id'] in matched - excluded})
    common_prompts = sorted(set.intersection(*clean_prompts))
    evidence = ROOT / 'site-source/evidence' / base
    evidence.mkdir(parents=True, exist_ok=True)
    for name, alias in [('original', 'A'), ('abliterated', 'B')]:
        effects = [next(e for i in review['analysis']['items'] if i['component_id'] == alias + '__' + cid
                        for e in i['condition_effects'] if e['condition'] == 'p9') for review in (primary, independent)]
        gates = [decision(e, cases[name][cid], manifest['protocol']['gate']) for e in effects]
        old = next(e for i in prior['analysis']['items'] if i['component_id'] == name + '__' + cid
                   for e in i['condition_effects'] if e['condition'] == 'p9')
        validation_pairs = [p for p in read(PARENT / name / 'validation.json')[cid] if p['condition'] == 'p9' and p['kind'] == 'neuron']
        val_hits = len({p['id'] for p in validation_pairs} & set(old['matching_ids']))
        validation = {'change': old['change_strength'], 'coherence': old['coherence'], 'matches': val_hits, 'n': 8,
                      'source': 'Previous campaign validation; not new validation data.', 'passed': old['change_strength'] >= 3 and old['coherence'] >= 3 and val_hits >= 4}
        passed = validation['passed'] and all(g['passed'] for g in gates)
        common = set(effects[0]['matching_ids']) & set(effects[1]['matching_ids'])
        flags = set().union(*(set(e[k]) for e in effects for k in ('baseline_defect_ids', 'collapse_ids', 'repetition_ids')))
        example = next((p for p in cases[name][cid] if p['kind'] == 'neuron' and p['stage'] == 'locked_test' and p['id'] in common - flags), None)
        if common_prompts:
            example = next(p for p in cases[name][cid] if p['kind'] == 'neuron' and p['stage'] == 'locked_test' and p['prompt'] == common_prompts[0])
        example = example or next((p for p in cases[name][cid] if p['kind'] == 'neuron' and p['stage'] == 'locked_test' and p['id'] in common), None)
        outcome = {'coordinate': cid, 'checkpoint': name, 'condition': 'p9', 'label': independent['analysis']['items'][0]['overview'],
            'passed': passed, 'preferred_on_card': True, 'validation': validation, 'primary': gates[0], 'independent': gates[1],
            'example_id': example['id'] if example else None,
            'example_basis': 'Post-audit illustration; both reviewers matched the effect. Baseline/quality flags are retained in the raw assessments.',
            'review_input_sha256': {'primary': primary['input_sha256'], 'independent': independent['input_sha256']}}
        outcome['label'] = effects[1]['label']
        outcomes.append(outcome)
        model = read(PARENT / name / 'model.json'); campaign = base + '-' + name
        label = manifest['protocol']['frozen_description']
        chosen = interpretation(old, prior)['hypothesis']
        detail = {'id': campaign + '-' + cid, 'component_id': cid, 'campaign_id': campaign,
            'measurement_type': 'open_ended_neuron', 'model': 'LFM2.5-350M' + ('' if name == 'original' else '-abliterated (s3nh)'),
            'repository': model['repository'], 'revision': model['revision'], 'synthetic': False,
            'manifest_sha256': audit['manifest_sha256'], 'calibration_sha256': manifest['calibration_sha256'][name],
            'label': label, 'summary': f'Prospective +9x confirmation on 32 fresh ordinary prompts. Terra matched {sum(gates[0]["matches"].values())}/32; Sol {sum(gates[1]["matches"].values())}/32. Previous validation: {val_hits}/8; it is not counted as new validation.',
            'category': 'Other', 'state': 'Extreme mode observed' if passed else 'Tested observation',
            'effect': min(g['change'] for g in gates), 'n': 8, 'layer': 2, 'neuron': 3420,
            'mlp_width': 4608, 'layer_count': 16, 'hypothesis': chosen,
            'validation_analysis': interpretation(old, prior), 'validation_pairs': [old_pair(p) for p in validation_pairs],
            'test_analysis': interpretation(effects[0], primary), 'confirmation_analysis': interpretation(effects[1], independent),
            'paired_checkpoint': True, 'dose_unit': 'Signed multiple of the original checkpoint calibration maximum',
            'score_axes': {'change': min(g['change'] for g in gates), 'coherence': min(g['coherence'] for g in gates)},
            'validation_hits': val_hits, 'paired_gate': {'passed': passed, 'primary': gates[0], 'independent': gates[1],
                'primary_selection_eligible': True, 'scope': 'Publicly preregistered prospective confirmation at +9x.'},
            'primary_test_settings': ['p9'], 'selection_audit_ref': 'evidence/' + PROGRAM.name + '/' + STAGE.name + '/manifest.json',
            'artifact_url': 'evidence/' + campaign + '/' + cid + '.json'}
        for field, phase in [('test_pairs', 'locked_test'), ('long_pairs', 'long'), ('replication_pairs', 'replication'), ('control_pairs', 'random_controls')]:
            detail[field] = [old_pair(p) for p in cases[name][cid] if p['stage'] == phase]
        write_json(ROOT / 'site-source' / detail['artifact_url'], detail)
        records.append({k: v for k, v in detail.items() if k not in ('validation_pairs', 'test_pairs', 'long_pairs', 'replication_pairs', 'control_pairs', 'test_analysis', 'confirmation_analysis', 'validation_analysis')})
    catalogue_path = ROOT / 'site-source/catalogue.json'; catalogue = read(catalogue_path)
    catalogue['records'] = [r for r in catalogue['records'] if not r.get('campaign_id', '').startswith(base + '-')] + records
    write_json(catalogue_path, catalogue)
    result = {'campaign_id': base, 'observations': len(records), 'states': dict(Counter(r['state'] for r in records)),
        'qualified_frozen_condition_count': sum(r['passed'] for r in outcomes), 'condition_gates': outcomes,
        'review_gaps': [], 'scope': 'New prospective confirmation; previous validation remains explicitly attributed.',
        'derived_source_sha256': digest(Path(__file__))}
    write_json(evidence / 'outcomes.json', result); write_json(STAGE / 'outcomes.json', result)
    lines = ['# LFM +9x prospective confirmation', '',
        'This study tested L2 N3420 at +9x on 32 fresh ordinary prompts in each pinned LFM checkpoint, with 32 matched random-direction controls per checkpoint. The plan, prompts and source hashes were publicly committed and verified before measured jobs began. The frozen description was diplomatic and military reframing.', '',
        'Checkpoint aliases concealed original-versus-edited identity from Terra and Sol. Previous ratings and notes were withheld. Each reviewer received the frozen description, exact paired texts and controls, without the other reviewer\'s verdict. Prior 8/8 validation observations are references to the earlier campaign, not new data.', '',
        '| Checkpoint | Terra matches | Sol matches | Terra / Sol repetition | Terra / Sol collapse | Terra / Sol task loss | Terra / Sol random matches | Both criteria |',
        '|---|---:|---:|---:|---:|---:|---:|---|']
    for row in outcomes:
        a, b = row['primary'], row['independent']
        lines.append(f'| {row["checkpoint"]} | {sum(a["matches"].values())}/32 | {sum(b["matches"].values())}/32 | {a["repetition_flags"]} / {b["repetition_flags"]} | {a["collapse_flags"]} / {b["collapse_flags"]} | {a["task_loss"]} / {b["task_loss"]} | {a["random_matches"]} / {b["random_matches"]} | {"Met" if row["passed"] else "Not met"} |')
    lines += ['', 'Matching a description does not mean answering the task. Baseline defects and all separate phase counts are retained in the [outcomes](../site-source/evidence/' + base + '/outcomes.json). Random controls are four seeded directions on eight prompts; their counts are descriptive, not independent population estimates.', '',
        f'The independent audit linked {audit["exact_pairs_linked_to_raw_jobs"]} exact pairs to raw completed jobs and found no review gaps. [Public preregistration](lfm-depth-20261127-v1.md).']
    (ROOT / 'docs' / ('campaign-' + base + '.md')).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print({'observations': len(records), 'conditions_meeting_criteria': result['qualified_frozen_condition_count']}, flush=True)


if __name__ == '__main__':
    main()
