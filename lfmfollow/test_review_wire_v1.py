"""Replay real accepted evidence through the new compact wire without making API calls."""
from copy import deepcopy
import json
from lfmfollow import review_v2, review_v1
from lfmfollow.core_v1 import PROGRAM, read


def main():
    stage = PROGRAM / 'stages/01-confirm-p9'; cases = deepcopy(read(stage / 'pairs.json')); cid = 'L2-N3420'
    for name in cases:
        for pair in cases[name][cid]:
            pair['config']['nomination'] = {'prior_score_sentinel': 'MUST_NOT_REACH_REVIEWER', 'change_strength': 999}
    hypotheses = {name: {cid: [{'condition': 'p9', 'label': 'Diplomatic and military reframing'}]} for name in cases}
    bundle = review_v2.bundle('offline-wire-test', cid, cases, ['p9'], hypotheses)
    wire, mapping = review_v2.compact(bundle); encoded = json.dumps(wire)
    assert 'MUST_NOT_REACH_REVIEWER' not in encoded and '"config"' not in encoded and len(encoded) < 950000
    assert {i['model'] for i in wire['items']} == {'checkpoint-A','checkpoint-B'}
    accepted = read(stage / 'reviews/locked_test' / (cid+'.json'))['analysis']
    review_v1.validate(accepted, bundle)
    inverse = {value: key for key, value in mapping.items()}; assert len(inverse)==len(mapping)==128
    compact_analysis = deepcopy(accepted)
    compact_analysis['reviewed_evidence_ids'] = [inverse[k] for k in compact_analysis['reviewed_evidence_ids']]
    for item in compact_analysis['items']:
        for effect in item['condition_effects']:
            for field in review_v1.analysis.FIELDS:
                effect[field] = [inverse[k] for k in effect[field]]
    review_v1.validate(compact_analysis, wire)
    assert review_v1.analysis.contract.expand(compact_analysis, mapping) == accepted
    print('All 128 real accepted pairs replayed through the new wire; checkpoint identities and prior-score metadata withheld. Zero API calls.')


if __name__ == '__main__': main()
