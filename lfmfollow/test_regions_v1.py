"""Offline candidate-plan fixtures; no measured configurations or reviewer calls."""
from pathlib import Path
import shutil
from lfmfollow import study04_v1, study05_v1
from lfmfollow.core_v1 import ROOT, PROGRAM, read
from lfmfollow.design_v1 import variant
from reference import write_json


def main():
    fixture = ROOT / '.cache/lfm-region-plan-fixture'
    fixture.mkdir(exist_ok=True)
    (fixture / 'SYNTHETIC-FIXTURE.txt').write_text('Candidate planning fixtures only; no generated measurements or discoveries.\n', encoding='utf-8')
    for filename in ('posthoc-weight-geometry-v2.json','adaptive-design-late-region-v1.json'):
        shutil.copyfile(PROGRAM / filename, fixture / filename)
    write_json(fixture / 'stages/02-dose-response/frozen-finalists.json', read(PROGRAM / 'stages/02-dose-response/frozen-finalists.json'))
    study04_v1.PROGRAM = study05_v1.PROGRAM = fixture
    for supplied in (False, True):
        choices = []
        if supplied:
            for i, cid in enumerate(('L11-N45','L12-N46')):
                choices.append({**variant(cid,3), 'nomination': {'change':4,'hits':7,'n':8,'coherence':4,'tie_key':str(i)}})
        write_json(fixture / 'stages/03-missed-candidates/frozen-finalists.json', {'variants':choices})
        timing, pairs = study04_v1.build(), study05_v1.build()
        assert len(timing['variants']) == 390 and timing['budget_upper_bound_per_checkpoint'] == 6720
        assert len(pairs['variants']) == 192 and pairs['budget_upper_bound_per_checkpoint'] == 4416
        for pool in (timing['candidate_provenance']['base_profiles'],pairs['candidate_provenance']['pool']):
            assert pool[0]['component'] == 'L2-N3420' and pool[0]['sites'][0]['value'] == 9
            assert len({v['component'] for v in pool}) == len(pool)
            late = {v['component'] for v in pool[:3] if v['sites'][0]['layer'] >= 10}
            assert late == ({'L11-N45','L12-N46'} if supplied else {'L10-N4198','L14-N1700'})
        provenance = pairs['candidate_provenance']
        assert len(provenance['sampled_pair_indices']) == len(set(provenance['sampled_pair_indices'])) == 16
        assert provenance['reserved_late_pair_index'] in provenance['sampled_pair_indices']
        late_components = {v['component'] for v in provenance['pool'][1:3]}
        assert any(set(v['pair_members']) == late_components and v['arm']=='AB' for v in pairs['variants'])
    print('Offline plans passed: edited-layer coverage, nominated candidates and explicit fallback paths, reserved late pair, unique pools and unchanged budgets. No measured jobs or reviews created.')


if __name__ == '__main__': main()
