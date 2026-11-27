"""Budget and timing semantics that would invalidate entire campaigns if wrong."""
from types import SimpleNamespace
import torch
from lfmfollow.design_v1 import nominate, variant
from lfmfollow.prompts_v1 import validate_partitions
from lfmfollow.timed_actor_v1 import Worker, position_mask


def main():
    validate_partitions()
    assert position_mask('prompt', 0, 4, 'cpu').tolist() == [True] * 4
    assert not position_mask('decode', 0, 4, 'cpu').any()
    assert position_mask('window_0_2', 0, 4, 'cpu').tolist() == [False, False, False, True]
    assert position_mask('window_2_4', 2, 1, 'cpu').item()
    assert not position_mask('window_2_4', 4, 1, 'cpu').item()
    assert position_mask('pulse_16', 16, 1, 'cpu').item()
    assert not position_mask('pulse_16', 15, 1, 'cpu').item()
    projection = torch.nn.Linear(4608, 3, bias=False)
    with torch.no_grad():
        projection.weight.zero_(); projection.weight[:, 7] = torch.tensor([1., 2., 2.])
    worker = object.__new__(Worker); worker.device = torch.device('cpu')
    worker.layers = [SimpleNamespace(mlp=SimpleNamespace(down_proj=projection))]
    worker.cal = {'0': {'activation_abs_max': [2.] * 4608}}
    inputs = torch.ones(2, 4, 4608)
    for operator, value, expected in [('clamp', 3., 6.), ('add', 3., 7.), ('scale', 3., 3.)]:
        cfg = {'condition': 'positive', 'sites': [{'layer': 0, 'neuron': 7, 'operator': operator, 'value': value}], 'timing': 'decode'}
        with worker.hook([cfg, {'condition': 'baseline'}]):
            prefill = projection(inputs)
            decoded = projection(inputs[:, :1])
        assert torch.equal(prefill[0], torch.tensor([[1., 2., 2.]]).repeat(4, 1))
        assert torch.allclose(decoded[0, 0], torch.tensor([1., 2., 2.]) * expected)
        assert torch.equal(decoded[1, 0], torch.tensor([1., 2., 2.]))
        assert not projection._forward_pre_hooks and not projection._forward_hooks
    # Matched random write magnitude is measured independently from the normal clamp output.
    base = projection(inputs[:1])
    cfg = {'condition': 'positive', 'sites': [{'layer': 0, 'neuron': 7, 'operator': 'clamp', 'value': 3.}], 'timing': 'all'}
    with worker.hook([cfg]): normal = projection(inputs[:1])
    with worker.hook([{**cfg, 'random_index': 0}]): random = projection(inputs[:1])
    assert torch.allclose((normal-base).norm(dim=-1), (random-base).norm(dim=-1), atol=1e-5)
    effect = {'change_strength': 4, 'coherence': 4, 'matching_ids': ['x'], 'repetition_ids': [], 'collapse_ids': []}
    analysis = {'original': {'L2-N3420': {'p9': {'effect': effect, 'n': 1, 'hits': 1, 'review_input_sha256': 'a' * 64}}}}
    assert not nominate(analysis, [variant('L2-N3420', 9)], 0, 0)[0]
    assert len(nominate(analysis, [variant('L2-N3420', 9)], 1, 0)[0]) == 1
    print('Timing, operator units, hook cleanup, anchor isolation, control norms, fresh partitions and zero quotas passed.')


if __name__ == '__main__':
    main()
