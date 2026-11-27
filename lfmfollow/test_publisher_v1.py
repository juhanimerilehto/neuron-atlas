"""Offline synthetic formatting fixtures; never enter the measurement programme or catalogue."""
from copy import deepcopy
from pathlib import Path
import sys
from lfmfollow import publish_v2
from lfmfollow.design_v1 import variant, pair_variant
from lfmfollow.core_v1 import ROOT, read
from reference import fingerprint, write_json


def main():
    fixture = ROOT / '.cache/lfm-publisher-format-fixture'
    fixture.mkdir(exist_ok=True)
    (fixture / 'docs').mkdir(exist_ok=True)
    (fixture / 'SYNTHETIC-FIXTURE.txt').write_text('Formatter test data only. These are not model discoveries and must never be published.\n', encoding='utf-8')
    publish_v2.ROOT = fixture
    publish_v2.PROGRAM = fixture / 'campaigns/lfm-depth-20261127-v1'
    stage = publish_v2.PROGRAM / 'stages/05-neuron-pairs'
    write_json(stage / 'status.json', {'stage': 'measurements_complete'})
    first, second = variant('L2-N3420', 9), variant('L5-N4206', 15)
    alternate = variant('L2-N3420', 10)
    arms = [pair_variant(first, second, 1., arm) for arm in ('A', 'B', 'AB')]
    variants = [first, alternate, *arms]
    finals = [first, *arms]
    final_keys = {(v['component'], v['id']) for v in finals}
    gate = {'change_min': 3, 'coherence_min': 3, 'heldout_matches_min': 8,
            'long_matches_min': 4, 'replication_matches_min': 4, 'repetition_max': 2, 'collapse_max': 2}
    write_json(stage / 'manifest.json', {'protocol': {'gate': gate, 'variants': variants, 'scope': 'Synthetic formatting fixture.'},
        'calibration_sha256': {name: 'a'*64 for name in ('original','abliterated')}})
    write_json(stage / 'independent-audit.json', {'passed': True, 'synthetic_fixture': True,
        'manifest_sha256': 'b'*64, 'counts': {'original': {'fixture': 1}, 'abliterated': {'fixture': 1}},
        'review_gaps': [], 'exact_pairs_linked_to_raw_jobs': 0})
    write_json(stage / 'validation-plan.json', {'variants': variants})
    write_json(stage / 'frozen-finalists.json', {'variants': finals})
    cases = {name: {} for name in ('original','abliterated')}
    analyses = {phase: {name: {} for name in cases} for phase in ('validation','locked_test','sol-locked_test')}
    hypotheses = {name: {} for name in cases}
    for name in cases:
        write_json(fixture / 'campaigns/paired-lfm25-350m-v1' / name / 'model.json',
            {'repository': 'synthetic-fixture/' + name, 'revision': '0'*40})
        for v in variants:
            component, condition = v['component'], v['id']
            counts = {'validation': 8}
            if (component, condition) in final_keys:
                counts.update(locked_test=16, long=8, replication=8, random_controls=32)
                hypotheses[name].setdefault(component, []).append({'condition': condition, 'label': 'Synthetic fixture effect'})
            rows = []
            for phase, count in counts.items():
                for i in range(count):
                    rows.append({'id': fingerprint([name, component, condition, phase, i]), 'prompt': 'Fixture prompt ' + str(i),
                        'condition': condition, 'stage': phase, 'kind': 'random_direction' if phase=='random_controls' else 'neuron',
                        'random_index': i % 4 if phase=='random_controls' else None,
                        'baseline': 'Synthetic baseline.', 'steered': 'Synthetic changed text.', 'token_ids': [1],
                        'baseline_token_ids': [2], 'termination': 'eos', 'intervention': {'applied_to_generated_sequence': True}})
            cases[name].setdefault(component, []).extend(rows)
            for analysis_phase in analyses:
                selected = [p for p in rows if p['kind']=='neuron' and
                    (p['stage']=='validation' if analysis_phase=='validation' else p['stage'] in ('locked_test','long','replication'))]
                if not selected: continue
                effect = {'condition': condition, 'label': 'Synthetic fixture effect', 'note': 'Formatter test, not a measurement.',
                    'change_strength': 4, 'coherence': 4, 'hypothesis_supported': None if analysis_phase=='validation' else True,
                    'matching_ids': [p['id'] for p in selected], 'repetition_ids': [], 'collapse_ids': [],
                    'task_loss_ids': [], 'baseline_defect_ids': [], 'similar_random_ids': []}
                analyses[analysis_phase][name].setdefault(component, {})[condition] = {
                    'effect': effect, 'n': len(selected), 'hits': len(selected), 'review_input_sha256': 'c'*64, 'followup_tests': []}
    write_json(stage / 'pairs.json', cases); write_json(stage / 'frozen-hypotheses.json', hypotheses)
    for phase, value in analyses.items(): write_json(stage / 'analyses' / (phase+'.json'), value)
    write_json(fixture / 'site-source/catalogue.json', {'records': [{'id': 'preserved-fixture', 'campaign_id': 'old-fixture'}]})
    sys.argv = ['publish_v2', '05-neuron-pairs']; publish_v2.main()
    records = read(fixture / 'site-source/catalogue.json')['records']; result = read(stage / 'outcomes.json')
    assert len(records)==7 and len({r['id'] for r in records})==7
    assert records[0] == {'id': 'preserved-fixture', 'campaign_id': 'old-fixture'}
    assert result['observations']==6 and result['qualified_frozen_condition_count']==4
    assert all(set(r['factorial_arms'])=={'A','B','AB'} for r in result['profiles'] if r['coordinate'].startswith('PAIR-'))
    factorial_examples = read(fixture / 'site-source/evidence/lfm-depth-20261127-v1-05-neuron-pairs/factorial-examples.json')
    for record in records:
        if not record.get('factorial_examples_ref'): continue
        examples = factorial_examples[record['id']]
        assert [e['arm'] for e in examples] == ['A', 'B', 'AB']
        assert len({e['prompt'] for e in examples}) == len({e['phase'] for e in examples}) == 1
        name = 'abliterated' if record['campaign_id'].endswith('-abliterated') else 'original'
        raw = {p['id']:p for p in cases[name][record['component_id']]}
        assert all(e['baseline'] == raw[e['id']]['baseline'] and e['steered'] == raw[e['id']]['steered'] for e in examples)
    # An unavailable independent assessment must remove the positive verdict, without deleting other records.
    missing = deepcopy(analyses['sol-locked_test']); missing['original']['L2-N3420'].pop('p9')
    missing['original'][arms[-1]['component']].pop(arms[-1]['id'])
    write_json(stage / 'analyses/sol-locked_test.json', missing); publish_v2.main()
    result = read(stage / 'outcomes.json'); records = read(fixture / 'site-source/catalogue.json')['records']
    assert result['qualified_frozen_condition_count']==2 and len(records)==7
    assert sum(r.get('state')=='Final review incomplete' for r in records) == 2
    assert len(read(fixture / 'site-source/evidence/lfm-depth-20261127-v1-05-neuron-pairs/factorial-examples.json')) == 2
    write_json(stage / 'status.json', {'stage': 'failed'})
    try:
        publish_v2.main()
    except AssertionError:
        pass
    else:
        raise AssertionError('Incomplete worker termination was incorrectly accepted for publication')
    assert read(fixture / 'site-source/catalogue.json')['records'] == records
    assert len(read(ROOT / 'site-source/catalogue.json')['records']) >= 356
    print('Offline fixture passed: separate profile cards, history preservation, factorial controls, idempotence and missing-review veto. No measured jobs or real catalogue records created.')


if __name__ == '__main__': main()
