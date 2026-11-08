"""Offline correctness tests with a tiny random Llama; no model downloads needed."""
import tempfile
import unittest
from pathlib import Path
import torch
from transformers import LlamaConfig, LlamaForCausalLM
from reference import ReferenceWorker, Intervention, JobStore


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(3)
        self.model=LlamaForCausalLM(LlamaConfig(vocab_size=32,hidden_size=16,intermediate_size=24,
            num_hidden_layers=2,num_attention_heads=2,num_key_value_heads=2)).eval()
        self.worker=ReferenceWorker(self.model,None)

    def test_hook_removal_on_exception(self):
        with self.assertRaisesRegex(RuntimeError,'expected'):
            with self.worker.intervention(Intervention(0,self.worker.column(0,1),.2,1)):
                raise RuntimeError('expected')
        self.assertFalse(self.worker.busy)
        self.assertEqual(len(self.model.model.layers[0].mlp.down_proj._forward_hooks),0)

    def test_mask_isolates_batch(self):
        inputs=torch.tensor([[1,2,3],[1,2,3]])
        with torch.no_grad():
            base=self.model(inputs).logits
            with self.worker.intervention(Intervention(0,self.worker.column(0,1),.2,1),torch.tensor([1,0])):
                changed=self.model(inputs).logits
        torch.testing.assert_close(base[1],changed[1],rtol=0,atol=0)
        self.assertGreater((base[0,-1]-changed[0,-1]).abs().max().item(),1e-5)
        torch.testing.assert_close(base[:,:-1],changed[:,:-1],rtol=0,atol=0)

    def test_invalid_direction_cleans_state(self):
        with self.assertRaises(ValueError):
            with self.worker.intervention(Intervention(0,torch.zeros(16),.2,1)):
                pass
        self.assertFalse(self.worker.busy)

    def test_resume_and_budget(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as path:
            store=JobStore(Path(path),{'version':1},max_jobs=1)
            try:
                self.assertEqual(store.run({'x':1},lambda:{'value':7}),{'value':7})
                self.assertEqual(store.run({'x':1},lambda:None),{'value':7})
                with self.assertRaisesRegex(RuntimeError,'budget'):
                    store.run({'x':2},lambda:{})
            finally:
                store.db.close()


if __name__=='__main__':
    unittest.main()
