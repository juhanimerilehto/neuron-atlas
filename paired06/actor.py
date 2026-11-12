"""Shared-prefix screening at several answer positions using the frozen clamp hook."""
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'exhaust'))
from actor import Worker as ClampWorker


class Worker(ClampWorker):
    @torch.inference_mode()
    def prefix_scores(self, configs, prefix):
        device = self.device
        anchor = {**configs[0], 'condition': 'baseline'}
        anchor.pop('random_index', None)
        inputs = torch.tensor(prefix['input_ids'], device=device)[None, :].repeat(len(configs) + 1, 1)
        positions = torch.tensor(prefix['positions'], device=device)
        with self.hook(configs + [anchor]):
            logits = self.model(input_ids=inputs, attention_mask=torch.ones_like(inputs), use_cache=False,
                                logits_to_keep=positions).logits.float()
        assert logits.shape[:2] == (len(configs) + 1, len(prefix['positions']))
        assert torch.isfinite(logits).all()
        logp = logits.log_softmax(-1)
        p = logp.exp()
        base = logp[-1:]
        bp = p[-1:]
        midpoint = torch.logaddexp(logp, base) - torch.log(torch.tensor(2., device=device))
        js = (.5 * (p * (logp - midpoint)).sum(-1) + .5 * (bp * (base - midpoint)).sum(-1)).clamp_min(0)
        kl = (bp * (base - logp)).sum(-1).clamp_min(0)
        assert js.max().item() <= .694
        js, kl = js.cpu().tolist(), kl.cpu().tolist()
        top = logp.argmax(-1).cpu().tolist()
        return [{'checkpoints': prefix['checkpoints'], 'js': js[i], 'kl': kl[i],
                 'top_token_ids': top[i], 'baseline_top_token_ids': top[-1],
                 'batch_width': len(configs) + 1} for i in range(len(configs))]
