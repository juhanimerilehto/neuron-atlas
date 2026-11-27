"""Publish each validated profile separately; retain failed and exploratory outcomes."""
from collections import Counter
from pathlib import Path
import re
import sys
from lfmfollow.core_v1 import ROOT, PROGRAM, MODELS, read, digest
from lfmfollow.publish_v1 import decision, interpretation, old_pair
from reference import write_json, fingerprint


def main():
    stage = sys.argv[1]
    assert stage in ('02-dose-response', '03-missed-candidates', '04-timing-operators', '05-neuron-pairs')
    directory = PROGRAM / 'stages' / stage
    audit = read(directory / 'independent-audit.json'); assert audit['passed']
    assert read(directory / 'status.json')['stage'] == 'measurements_complete', 'Worker completion event is missing; diagnose before publication'
    gaps = [read(p) for p in (directory / 'review-failures').glob('*.json')]
    assert sorted(map(fingerprint, gaps)) == sorted(map(fingerprint, audit['review_gaps'])), 'Audit gap ledger differs from saved failures'
    manifest = read(directory / 'manifest.json'); protocol = manifest['protocol']
    validation = read(directory / 'analyses/validation.json')
    primary = read(directory / 'analyses/locked_test.json')
    independent = read(directory / 'analyses/sol-locked_test.json')
    all_pairs = read(directory / 'pairs.json')
    variants = read(directory / 'validation-plan.json')['variants']
    finalists = read(directory / 'frozen-finalists.json')['variants']
    final_keys = {(v['component'], v['id']) for v in finalists}
    hypotheses = read(directory / 'frozen-hypotheses.json')
    base = PROGRAM.name + '-' + stage
    evidence = ROOT / 'site-source/evidence' / base
    records, gates, profiles = [], [], []
    proposals = []
    factorial_examples = {}
    for variant in variants:
        if variant.get('arm') in ('A', 'B'):
            continue  # Factorial single arms are controls for the pair record.
        component, condition = variant['component'], variant['id']
        tested = (component, condition) in final_keys
        for name in MODELS:
            source = validation[name].get(component, {}).get(condition)
            if not source:
                continue  # Missing review stays an explicit gap, never a fabricated score.
            effect = source['effect']; passed_validation = effect['change_strength'] >= 3 and effect['coherence'] >= 3 and source['hits'] >= 4
            own_pairs = [p for p in all_pairs[name][component] if p['condition'] == condition]
            validation_pairs = [p for p in own_pairs if p['stage'] == 'validation']
            assert len(validation_pairs) == source['n'] == 8
            frozen_label = next((e['label'] for e in hypotheses[name].get(component, []) if e['condition'] == condition), None)
            label = frozen_label or effect['label'] or 'No supported qualitative label · ' + component
            first = primary[name].get(component, {}).get(condition)
            second = independent[name].get(component, {}).get(condition)
            gate = None; passed = False; state = 'Validation observation'
            per_reviewer = {}
            if tested:
                final_pairs = [p for p in own_pairs if p['stage'] in ('locked_test', 'long', 'replication', 'random_controls')]
                if first: per_reviewer['primary'] = decision(first['effect'], final_pairs, protocol['gate'])
                if second: per_reviewer['independent'] = decision(second['effect'], final_pairs, protocol['gate'])
                if first and second:
                    a, b = per_reviewer['primary'], per_reviewer['independent']
                    passed = bool(passed_validation and a['passed'] and b['passed'])
                    gate = {'passed': passed, 'primary': a, 'independent': b, 'primary_selection_eligible': True,
                            'scope': 'Fresh held-out assessment of this exact operator, timing and site configuration.'}
                    per_reviewer = {'primary': a, 'independent': b}
                    state = 'Extreme mode observed' if passed else 'Tested observation'
                else:
                    gate = {'passed': False, 'review_status': 'incomplete', 'missing_reviewers':
                            [who for who, value in [('Terra', first), ('Sol', second)] if not value],
                            'primary': per_reviewer.get('primary'), 'independent': per_reviewer.get('independent')}
                    state = 'Final review incomplete'
            campaign = base + '-' + name
            slug = re.sub('[^a-z0-9-]', '-', condition.lower().replace('.', 'dot'))
            record_id = campaign + '-' + component + '-' + slug
            representative = validation_pairs[0] if validation_pairs else None
            if first and second:
                common = set(first['effect']['matching_ids']) & set(second['effect']['matching_ids'])
                bad = set().union(*(set(e['effect'][k]) for e in (first, second) for k in
                                    ('baseline_defect_ids', 'repetition_ids', 'collapse_ids')))
                representative = next((p for p in own_pairs if p['stage'] == 'locked_test' and p['id'] in common-bad), None)
                representative = representative or next((p for p in own_pairs if p['stage'] == 'locked_test' and p['id'] in common), None)
            val = {'change': effect['change_strength'], 'coherence': effect['coherence'], 'matches': source['hits'], 'n': 8, 'passed': passed_validation}
            final_neurons = [p for p in own_pairs if p['kind'] == 'neuron' and p['stage'] in ('locked_test', 'long', 'replication')]
            exposed = sum(bool(p['intervention'].get('applied_to_generated_sequence', p['intervention'].get('max_abs_activation_delta', 0) > 0)) for p in final_neurons)
            outcome = {'record_id': record_id, 'coordinate': component, 'checkpoint': name, 'condition': condition,
                'label': label, 'passed': passed, 'preferred_on_card': True, 'validation': val,
                'primary': per_reviewer.get('primary'), 'independent': per_reviewer.get('independent'),
                'example_id': representative['id'] if representative else None, 'selection_track': variant.get('selection_track'),
                'variant': variant, 'exposure': {'applied': exposed, 'n': len(final_neurons)},
                'review_input_sha256': {'validation': source['review_input_sha256'],
                    'primary': first['review_input_sha256'] if first else None,
                    'independent': second['review_input_sha256'] if second else None}}
            profiles.append(outcome)
            if tested: gates.append(outcome)
            model = read(ROOT / 'campaigns/paired-lfm25-350m-v1' / name / 'model.json')
            site = variant['sites'][0]
            summary = f'Validation matched {source["hits"]}/8 at this exact profile. '
            if tested and first and second:
                summary += f'Terra matched {sum(per_reviewer["primary"]["matches"].values())}/32; Sol {sum(per_reviewer["independent"]["matches"].values())}/32. '
            elif tested:
                summary += 'Final review is incomplete after the saved attempts. '
            else:
                summary += 'This profile has validation-only evidence. '
            detail = {'id': record_id, 'component_id': component, 'campaign_id': campaign, 'condition_record': True,
                'measurement_type': 'open_ended_neuron_pair' if variant.get('arm') == 'AB' else 'open_ended_neuron',
                'model': 'LFM2.5-350M' + ('' if name == 'original' else '-abliterated (s3nh)'),
                'repository': model['repository'], 'revision': model['revision'], 'synthetic': False,
                'manifest_sha256': audit['manifest_sha256'], 'calibration_sha256': manifest['calibration_sha256'][name],
                'label': label, 'summary': summary, 'state': state, 'category': 'Other', 'effect': effect['change_strength'], 'n': 8,
                'layer': site['layer'], 'neuron': site['neuron'], 'mlp_width': 4608, 'layer_count': 16,
                'paired_checkpoint': True, 'dose_unit': variant['dose_unit'], 'operator': site['operator'], 'timing': variant['timing'],
                'intervention_sites': variant['sites'], 'intervention_description': variant['description'] +
                    ('; constellation location is anchored to the first site of this pair.' if variant.get('arm') == 'AB' else ''),
                'score_axes': {'change': effect['change_strength'], 'coherence': effect['coherence']},
                'validation_hits': source['hits'], 'hypothesis': interpretation(effect, {'input_sha256': source['review_input_sha256']})['hypothesis'],
                'validation_analysis': interpretation(effect, {'input_sha256': source['review_input_sha256']}),
                'validation_pairs': [old_pair(p) for p in validation_pairs], 'paired_gate': gate,
                'primary_test_settings': [condition] if tested else [],
                'selection_audit_ref': 'evidence/' + PROGRAM.name + '/' + stage + '/frozen-finalists.json',
                'artifact_url': 'evidence/' + campaign + '/' + component + '-' + slug + '.json'}
            detail['hypothesis']['label'] = label
            detail['hypothesis']['followup_proposals'] = source['followup_tests']
            if tested:
                for field, phase in [('test_pairs', 'locked_test'), ('long_pairs', 'long'), ('replication_pairs', 'replication'), ('control_pairs', 'random_controls')]:
                    detail[field] = [old_pair(p) for p in own_pairs if p['stage'] == phase]
                for field, value in [('test_analysis', first), ('confirmation_analysis', second)]:
                    if value: detail[field] = interpretation(value['effect'], {'input_sha256': value['review_input_sha256']})
            if variant.get('arm') == 'AB' and tested:
                outcome['factorial_arms'] = {}
                examples = []
                factorial_case = representative if representative and representative['stage'] in ('locked_test', 'long', 'replication') else next(
                    (p for p in own_pairs if p['kind'] == 'neuron' and p['stage'] == 'locked_test'), None)
                for arm in ('A', 'B', 'AB'):
                    own = next(v for v in finalists if v['component'] == component and v['level'] == variant['level'] and v['arm'] == arm)
                    arm_pairs = [p for p in all_pairs[name][component] if p['condition'] == own['id'] and p['stage'] in ('locked_test','long','replication','random_controls')]
                    values = {}
                    for who, analyses in [('primary', primary), ('independent', independent)]:
                        item = analyses[name].get(component, {}).get(own['id'])
                        values[who] = decision(item['effect'], arm_pairs, protocol['gate']) if item else None
                    outcome['factorial_arms'][arm] = {'condition': own['id'], **values}
                    example = next((p for p in arm_pairs if factorial_case and p['kind'] == 'neuron'
                        and p['stage'] == factorial_case['stage'] and p['prompt'] == factorial_case['prompt']), None)
                    if example:
                        examples.append({k: example[k] for k in ('id', 'prompt', 'baseline', 'steered', 'termination')} |
                            {'arm': arm, 'condition': own['id'], 'phase': example['stage'], 'sites': own['sites']})
                if factorial_case:
                    assert len(examples) == 3
                    factorial_examples[record_id] = examples
                    detail['factorial_examples_ref'] = 'evidence/' + base + '/factorial-examples.json'
            write_json(ROOT / 'site-source' / detail['artifact_url'], detail)
            exclude = {'validation_pairs','test_pairs','long_pairs','replication_pairs','control_pairs','validation_analysis','test_analysis','confirmation_analysis'}
            records.append({k: v for k, v in detail.items() if k not in exclude})
            proposals += [{'record_id': record_id, 'review_input_sha256': source['review_input_sha256'],
                           'proposal': text, 'execution_status': 'Suggestion retained; not arbitrary executable instructions.'} for text in source['followup_tests']]
    catalogue_path = ROOT / 'site-source/catalogue.json'; catalogue = read(catalogue_path)
    catalogue['records'] = [r for r in catalogue['records'] if not r.get('campaign_id','').startswith(base + '-')] + records
    write_json(catalogue_path, catalogue)
    result = {'campaign_id': base, 'observations': len(records), 'states': dict(Counter(r['state'] for r in records)),
        'qualified_frozen_condition_count': sum(g['passed'] for g in gates), 'condition_gates': gates, 'profiles': profiles,
        'review_gaps': audit['review_gaps'], 'discovery_profile_count': len(protocol['variants']),
        'validation_profile_count': len(variants), 'frozen_profile_count_including_factorial_controls': len(finalists),
        'scope': protocol['scope'], 'derived_source_sha256': digest(Path(__file__))}
    write_json(evidence / 'outcomes.json', result); write_json(directory / 'outcomes.json', result)
    if factorial_examples:
        write_json(evidence / 'factorial-examples.json', factorial_examples)
    write_json(directory / 'reviewer-proposals.json', proposals)
    lines = ['# LFM depth: ' + stage, '',
        f'This stage measured {sum(sum(v.values()) for v in audit["counts"].values()):,} configurations in the pinned LFM pair. '
        f'It generated {len(protocol["variants"])} discovery profiles on 16 ordinary prompts per checkpoint, advanced {len(variants)} profiles to eight fresh validation prompts, '
        f'and froze {len(finalists)} profiles including any factorial controls for held-out tests. The catalogue adds {len(records)} separately identified assessed profile records.', '',
        'Earlier records are preserved. Each new card identifies an exact dose/operator/timing/site configuration. Discovery prompts and scores are not held-out evidence. '
        'Later partitions use disjoint prompt strings but share task templates; this is not a claim of broad out-of-distribution generalization. '
        'Final reviewers see frozen descriptions without validation ratings or notes, with original-versus-edited identity concealed by A/B aliases.', '',
        '| Checkpoint | Profile | Validation | Terra / Sol final matches | Terra / Sol repetition | Terra / Sol collapse | Terra / Sol random matches | Stability criteria |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for row in profiles:
        a, b = row['primary'], row['independent']
        cells = [str(sum(a['matches'].values())) + ' / ' + str(sum(b['matches'].values())),
                 str(a['repetition_flags'])+' / '+str(b['repetition_flags']), str(a['collapse_flags'])+' / '+str(b['collapse_flags']),
                 str(a['random_matches'])+' / '+str(b['random_matches'])] if a and b else ['—'] * 4
        verdict = 'Met' if row['passed'] else 'Not met' if a and b else 'Review incomplete' if (row['coordinate'],row['condition']) in final_keys else 'Validation only'
        lines.append('| ' + ' | '.join([row['checkpoint'], row['variant']['description'], str(row['validation']['matches'])+'/8', *cells, verdict]) + ' |')
    lines += ['', 'Task loss and baseline defects are retained separately in the [complete outcomes](../site-source/evidence/' + base + '/outcomes.json). '
        'Passing the criterion does not require task correctness or random-direction specificity. Four seeded random directions are used on eight prompts per frozen setting. '
        'Exposure counts identify cases where a scheduled timing window actually changed an activation before that response ended; a response ending before a late window is retained as an assigned-profile observation.', '',
        'For neuron pairs, single arms and the AB arm are assessed against the same frozen AB description. AB-versus-single differences alone do not establish synergy: total perturbation sizes differ. '
        'Per-projection matched controls and local write diagnostics are retained; cross-layer norms are not a single net residual norm. '
        'Pair cards include a prompt-matched A/B/AB illustration with each arm\'s actual unmodified baseline.', '',
        f'The independent audit linked {audit["exact_pairs_linked_to_raw_jobs"]:,} exact pairs to raw completed jobs. Review gaps: {len(audit["review_gaps"])}. '
        'Unassessed profiles remain explicit gaps, not negative semantic findings. [Programme protocol](lfm-depth-20261127-v1.md).']
    (ROOT / 'docs' / ('campaign-' + base + '.md')).write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print({'stage': stage, 'observations': len(records), 'qualified_conditions': result['qualified_frozen_condition_count']}, flush=True)


if __name__ == '__main__': main()
