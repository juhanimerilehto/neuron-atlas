"""Reviewer availability fixtures, counted inside the frozen request ceilings."""
from pathlib import Path
from familylab import analysis, data


def main():
    out = Path(__file__).resolve().parents[1] / 'campaigns' / data.CAMPAIGN
    bundle = {'namespace': 'reviewer_preflight', 'phase': 'discovery', 'items': [{
        'component_id': 'preflight__L0-N0', 'model': data.SPEC['models']['original'][0],
        'revision': data.SPEC['models']['original'][1], 'settings': ['off'], 'pairs': [{
            'id': 'preflight_case', 'prompt': 'What is 2 plus 2?', 'condition': 'off', 'stage': 'discovery',
            'kind': 'neuron', 'random_index': None, 'baseline': '4', 'steered': '4', 'termination': 'eos'}]}],
        'scope': 'Synthetic identity fixture for transport availability only. Not a model measurement or catalogue finding.'}
    for directory, model, ceiling in [('codex', 'gpt-6.1-terra', 700), ('codex-confirm', 'gpt-6.1-sol', 100)]:
        result = analysis.Reviewer(out / directory, model=model, limit=ceiling).review(bundle)
        assert result['analysis']['items'][0]['condition_effects'][0]['change_strength'] == 0
        print(model, 'identity fixture accepted; request counted in campaign ceiling', flush=True)


if __name__ == '__main__':
    main()
