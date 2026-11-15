"""Regression tests for later-position causal scoring and unchanged batch anchors."""
from pathlib import Path
import sys
import unittest

import torch
from transformers import LlamaConfig, LlamaForCausalLM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pairedllama.actor import Worker


class LaterPositions(unittest.TestCase):
    def test_review_transport_preserves_evidence(self):
        from pairedllama import analysis
        import json
        pairs = {name: {'L1-N1': [{'id': str(i) * 64, 'prompt': 'Describe a garden.', 'baseline': 'A garden.',
                                 'steered': 'A quiet garden.', 'condition': 'p4', 'stage': 'discovery',
                                 'kind': 'neuron', 'random_index': None, 'token_ids': [3] * 2000,
                                 'baseline_token_ids': [2] * 2000, 'intervention': {}, 'diagnostics': {}}]}
                 for i, name in enumerate(('original', 'abliterated'))}
        models = {name: {'repository': name, 'revision': 'pinned'} for name in pairs}
        original = analysis.bundle('discovery', 'transport-test', ['L1-N1'], pairs, {'L1-N1': ['p4']}, models)
        wire, mapping = analysis.compact(original)
        self.assertEqual(set(mapping.values()), {'0' * 64, '1' * 64})
        for source, item in zip(original['items'], wire['items']):
            self.assertEqual(item['pairs'][0]['steered'], source['pairs'][0]['steered'])
            self.assertEqual(wire['baselines'][item['pairs'][0]['baseline_ref']], source['pairs'][0]['baseline'])
            self.assertNotIn('token_ids', item['pairs'][0])
            self.assertEqual(len(source['pairs'][0]['token_ids']), 2000)
        self.assertLess(len(json.dumps(wire)), len(json.dumps(original)))

    def test_zero_mixed_quota(self):
        from pairedllama.campaign import Run
        fake = {'L1-N1': {'analysis': {'items': []}}}
        pairs = {name: {'L1-N1': [{'id': name+'-n', 'condition': 'p4', 'kind': 'neuron'}]} for name in ('original', 'abliterated')}
        for name in pairs:
            fake['L1-N1']['analysis']['items'].append({'component_id': name+'__L1-N1', 'condition_effects': [{'condition': 'p4', 'coherence': 1, 'change_strength': 4, 'matching_ids': [name+'-n']}]})
        self.assertEqual(Run.nominations(None, fake, pairs, 'validation', 6, 0), {})

    def test_same_prefix_at_each_position(self):
        torch.manual_seed(19)
        model = LlamaForCausalLM(LlamaConfig(vocab_size=32, hidden_size=16, intermediate_size=24,
                                          num_hidden_layers=2, num_attention_heads=2, num_key_value_heads=1,
                                          head_dim=8, eos_token_id=2, attn_implementation='eager')).eval()
        worker = Worker(model, None, {str(layer): {'activation_abs_max': [1.] * 24} for layer in range(2)})
        configs = [{'layer': 0, 'neuron': 5, 'condition': 'baseline', 'factor': 1.},
                   {'layer': 0, 'neuron': 5, 'condition': 'negative', 'factor': 4.},
                   {'layer': 1, 'neuron': 8, 'condition': 'positive', 'factor': 4.}]
        prefix = {'input_ids': [1, 6, 7, 9, 12, 15], 'positions': [1, 3, 5], 'checkpoints': [0, 2, 4]}
        values = worker.prefix_scores(configs, prefix)
        self.assertLess(max(values[0]['js']), 1e-7)
        self.assertTrue(any(max(value['js']) > 1e-5 for value in values[1:]))
        for index, position in enumerate(prefix['positions']):
            cropped = {'input_ids': prefix['input_ids'][:position + 1], 'positions': [position],
                       'checkpoints': [prefix['checkpoints'][index]]}
            direct = worker.prefix_scores(configs, cropped)
            for full, cut in zip(values, direct):
                self.assertAlmostEqual(full['js'][index], cut['js'][0], places=6)
                self.assertEqual(full['baseline_top_token_ids'][index], cut['baseline_top_token_ids'][0])
        for layer in worker.layers:
            self.assertFalse(layer.mlp.down_proj._forward_pre_hooks)
            self.assertFalse(layer.mlp.down_proj._forward_hooks)


if __name__ == '__main__':
    unittest.main()
