"""Fine dose curves on known coordinates, with new prompts and seeded nominations."""
from lfmfollow.core_v1 import PARENT, read, digest
from lfmfollow.design_v1 import variant, plan


def build():
    known = ['L2-N3420', 'L2-N3030', 'L3-N2589', 'L5-N4206', 'L10-N4198', 'L5-N3454']
    parent = read(PARENT / 'validation-plan.json')
    extra = sorted(set(parent) - set(known))[:2]
    coordinates = known + extra
    values = [-15, -12, -10, -9.5, -9, -8.5, -8, -6, -4, -3, -2, 0,
              2, 3, 4, 6, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 12, 15]
    variants = [variant(cid, value) for cid in coordinates for value in values]
    value = plan('02-dose-response', 0, variants, 2026112702)
    value['candidate_provenance'] = {'known_six': known, 'additional_two': extra,
        'additional_rule': 'First two other coordinates in lexical order from the frozen parent validation plan; no new responses consulted.',
        'parent_validation_plan_sha256': digest(PARENT / 'validation-plan.json')}
    return value
