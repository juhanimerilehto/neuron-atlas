"""Regression tests for later-position causal scoring and unchanged batch anchors."""
from pathlib import Path
import sys
import unittest

import torch
from transformers import Qwen3Config, Qwen3ForCausalLM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paired06.actor import Worker


class LaterPositions(unittest.TestCase):
    def test_same_prefix_at_each_position(self):
        torch.manual_seed(19)
        model = Qwen3ForCausalLM(Qwen3Config(vocab_size=32, hidden_size=16, intermediate_size=24,
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
