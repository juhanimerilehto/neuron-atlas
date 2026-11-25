"""Architecture tests for causality, hook isolation and cleanup on tiny random models."""
import torch
from transformers import Lfm2Config, Lfm2ForCausalLM, GraniteMoeHybridConfig, GraniteMoeHybridForCausalLM
from familylab.actor import Worker


class Tokenizer:
    pass


def check(model):
    worker = Worker(model.eval(), Tokenizer())
    worker.cal = {str(i): {'activation_abs_max': [1.] * layer.mlp.down_proj.in_features,
                           'median_residual_l2': 1.} for i, layer in enumerate(worker.layers)}
    ids = [1, 4, 8, 5, 3, 9, 2]
    prefix = {'input_ids': ids, 'positions': [2, 4, 6], 'checkpoints': [0, 2, 4]}
    configs = [{'layer': 0, 'neuron': 1, 'condition': 'negative', 'factor': 4.},
               {'layer': 2, 'neuron': 2, 'condition': 'positive', 'factor': 3.},
               {'layer': 1, 'neuron': 1, 'condition': 'baseline'}]
    scores = worker.prefix_scores(configs, prefix)
    assert max(scores[2]['js']) < 1e-7
    for point, position in enumerate(prefix['positions']):
        cropped = worker.prefix_scores(configs, {'input_ids': ids[:position + 1], 'positions': [position], 'checkpoints': [0]})
        assert all(abs(scores[i]['js'][point] - cropped[i]['js'][0]) < 1e-5 for i in range(3)), 'Later-token score leaked future inputs'
    assert all(not layer.mlp.down_proj._forward_pre_hooks and not layer.mlp.down_proj._forward_hooks for layer in worker.layers)
    print(model.config.model_type, 'causal prefix scores, untouched anchor and hook cleanup passed', flush=True)


def main():
    torch.manual_seed(37)
    torch.set_num_threads(2)
    lfm = Lfm2Config(vocab_size=32, hidden_size=32, intermediate_size=48, num_hidden_layers=3,
        num_attention_heads=4, num_key_value_heads=2, block_auto_adjust_ff_dim=False,
        layer_types=['conv', 'full_attention', 'conv'], max_position_embeddings=128)
    granite = GraniteMoeHybridConfig(vocab_size=32, hidden_size=32, intermediate_size=48,
        shared_intermediate_size=48, num_hidden_layers=3, num_attention_heads=4, num_key_value_heads=2,
        num_local_experts=0, num_experts_per_tok=0, layer_types=['attention'] * 3,
        mamba_n_heads=4, max_position_embeddings=128)
    with torch.inference_mode():
        check(Lfm2ForCausalLM(lfm))
        check(GraniteMoeHybridForCausalLM(granite))
    from familylab import data
    from familylab.campaign import Run
    fake = {'L1-N1': {'analysis': {'items': []}}}
    pairs = {name: {'L1-N1': [{'id': name + '-n', 'condition': 'p4', 'kind': 'neuron'}]} for name in data.MODELS}
    for name in pairs:
        fake['L1-N1']['analysis']['items'].append({'component_id': name + '__L1-N1',
            'condition_effects': [{'condition': 'p4', 'coherence': 1, 'change_strength': 4, 'matching_ids': [name + '-n']}]})
    assert Run.nominations(None, fake, pairs, 'validation', 6, 0) == {}, 'Zero mixed quota admitted collapsed candidates'
    print('Final nomination excludes mixed candidates when their quota is zero', flush=True)


if __name__ == '__main__':
    main()
