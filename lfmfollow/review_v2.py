"""Keep condition chunks auditable and support separately frozen checkpoint descriptions."""
from lfmfollow import review_v1
Reviewer = review_v1.Reviewer
_base_compact = review_v1.analysis.compact


def compact(bundle):
    wire, mapping = _base_compact(bundle)
    for item in wire['items']:
        for pair in item['pairs']:
            pair.pop('config', None)
    return wire, mapping


review_v1.analysis.compact = compact
review_v1.analysis.contract.compact = compact


def bundle(stage, component, cases, conditions, hypotheses=None):
    items = []
    for name, alias in [('original', 'A'), ('abliterated', 'B')]:
        rows = [p for p in cases[name][component] if p['condition'] in conditions]
        item = {'component_id': alias + '__' + component, 'model': 'checkpoint-' + alias,
                'settings': conditions, 'pairs': rows}
        if hypotheses:
            item['proposed_hypothesis'] = [e for e in hypotheses[name][component] if e['condition'] in conditions]
        items.append(item)
    return {'namespace': stage, 'phase': 'locked_test' if hypotheses else 'discovery', 'items': items,
        'scope': 'Paired ordinary-prompt responses; checkpoint identity is blinded. Each condition is an explicitly defined operator/timing/site configuration. '
        'Label effects without a preferred topic. Other condition chunks are neither evidence of absence nor context for an unmeasured claim.'}
