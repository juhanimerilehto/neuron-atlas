"""Reuse the validated evidence contract with blinded checkpoint names and no old scores."""
from familylab import analysis

analysis.contract.INSTRUCTION += '''
This is a separately preregistered LFM follow-up. Checkpoint aliases A/B conceal original-versus-edited identity.
When proposed_hypothesis is supplied, assess that description independently; prior scores, prior notes and the other reviewer's answers are withheld.
When no hypothesis is supplied, label freely. Rare interpretable changes are eligible even if other prompts do not show them.
Do not infer a model's intentions or experiences from its text. A recurring phrase can be a coherent effect and still be collapse; keep all diagnostic axes separate.
'''
Reviewer = analysis.Reviewer
validate = analysis.validate
fingerprint = analysis.contract.fingerprint


def bundle(stage, coordinate, cases, hypotheses=None):
    items = []
    for name, alias in [('original', 'A'), ('abliterated', 'B')]:
        pairs = cases[name][coordinate]
        item = {'component_id': alias + '__' + coordinate, 'model': 'checkpoint-' + alias,
                'settings': sorted({p['condition'] for p in pairs if p['kind'] == 'neuron'}),
                'pairs': pairs}
        if hypotheses:
            item['proposed_hypothesis'] = hypotheses[coordinate]
        items.append(item)
    return {'namespace': stage + '_' + coordinate, 'phase': 'locked_test' if hypotheses else 'discovery',
            'items': items, 'scope': 'Every response is compared with its own same-batch baseline. '
            'Ordinary prompts do not request the anomalous mode. Moral valence has no selection weight.'}
