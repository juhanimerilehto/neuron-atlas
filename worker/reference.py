"""Single-owner, sequential PyTorch reference worker. No arbitrary code or remote analysis."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import torch


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temp.replace(path)


@dataclass
class Intervention:
    layer: int
    direction: torch.Tensor
    dose: float
    scale: float


class ReferenceWorker:
    def __init__(self, model, tokenizer):
        self.model = model.eval()
        self.tokenizer = tokenizer
        self.device = next(model.parameters()).device
        self.layers = model.model.layers
        self.busy = False
        for layer in self.layers:
            assert layer.mlp.down_proj.weight.ndim == 2

    def encode(self, prompt):
        text = self.tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}],
            tokenize=False, add_generation_prompt=True)
        return self.tokenizer(text, return_tensors='pt', add_special_tokens=False).to(self.device)

    def column(self, layer, neuron):
        vector = self.layers[layer].mlp.down_proj.weight[:, neuron].detach().float()
        norm = vector.norm()
        if norm < 1e-8:
            raise ValueError('Near-zero down-projection column')
        return vector / norm

    @contextmanager
    def intervention(self, spec=None, batch_mask=None):
        if spec is None:
            yield
            return
        if self.busy:
            raise RuntimeError('One intervention owner per model instance')
        self.busy = True
        handle = None
        try:
            if not 0 <= spec.layer < len(self.layers):
                raise ValueError('Invalid layer')
            vector = spec.direction.to(self.device).float()
            if vector.shape != (self.model.config.hidden_size,) or not torch.isfinite(vector).all():
                raise ValueError('Invalid direction')
            if abs(vector.norm().item() - 1) > 1e-4:
                raise ValueError('Direction must have unit norm')
            def hook(module, inputs, output):
                # Each unpadded single-prompt call: last prefill position, then each cached decode input.
                result = output.clone()
                mask = torch.ones(output.shape[0], device=output.device, dtype=output.dtype)
                if batch_mask is not None:
                    mask = batch_mask.to(output.device, output.dtype)
                    if mask.shape != (output.shape[0],):
                        raise ValueError('Invalid per-example mask')
                result[:, -1, :] += mask[:, None] * vector.to(output.dtype) * spec.dose * spec.scale
                return result
            handle = self.layers[spec.layer].mlp.down_proj.register_forward_hook(hook)
            yield
        finally:
            if handle is not None:
                handle.remove()
            self.busy = False

    @torch.inference_mode()
    def distribution(self, prompt, spec=None):
        inputs = self.encode(prompt)
        with self.intervention(spec):
            logits = self.model(**inputs, use_cache=False).logits[0, -1].float()
        if not torch.isfinite(logits).all():
            raise ValueError('Non-finite logits')
        return logits.log_softmax(-1)

    @torch.inference_mode()
    def generate(self, prompt, spec=None, max_tokens=48):
        inputs = self.encode(prompt)
        prefix_length = inputs.input_ids.shape[1]
        start = time.perf_counter()
        with self.intervention(spec):
            output = self.model.generate(**inputs, do_sample=False, max_new_tokens=max_tokens,
                use_cache=True, pad_token_id=self.tokenizer.eos_token_id)
        ids = output[0, prefix_length:].tolist()
        return {'text': self.tokenizer.decode(ids, skip_special_tokens=True), 'token_ids': ids,
            'elapsed_seconds': time.perf_counter() - start,
            'termination': 'eos' if ids and ids[-1] == self.tokenizer.eos_token_id else 'max_tokens'}

    @torch.inference_mode()
    def calibrate(self, prompts, layers):
        norms = {layer: [] for layer in layers}
        activation = {layer: [] for layer in layers}
        handles = []
        try:
            for layer in layers:
                def residual_hook(module, args, output, index=layer):
                    norms[index].append(output[0][0, -1].float().norm().item())
                def activation_hook(module, args, index=layer):
                    activation[index].append(args[0][0, -1].detach().float().cpu())
                handles.append(self.layers[layer].register_forward_hook(residual_hook))
                handles.append(self.layers[layer].mlp.down_proj.register_forward_pre_hook(activation_hook))
            for prompt in prompts:
                self.distribution(prompt)
        finally:
            for h in handles:
                h.remove()
        return {str(layer): {'median_residual_l2': float(torch.tensor(norms[layer]).median()),
            'residual_l2_samples': norms[layer], 'positions': 'last unpadded prompt token',
            'activation_mean': torch.stack(activation[layer]).mean(0).tolist(),
            'activation_abs_max': torch.stack(activation[layer]).abs().max(0).values.tolist()}
            for layer in layers}

    @torch.inference_mode()
    def conformance(self, prompt, layer, neuron, scale):
        spec = Intervention(layer, self.column(layer, neuron), .15, scale)
        base = self.distribution(prompt)
        zero = self.distribution(prompt, Intervention(layer, spec.direction, 0, scale))
        self.distribution(prompt, spec)
        restored = self.distribution(prompt)
        down = self.layers[layer].mlp.down_proj
        torch.manual_seed(999)
        a = torch.randn(2, 3, down.in_features, device=self.device)
        delta = .15 * scale / down.weight[:, neuron].float().norm()
        modified = a.clone()
        modified[:, -1, neuron] += delta
        expected = down(a).clone()
        expected[:, -1] += spec.direction * .15 * scale
        equivalence = (down(modified) - expected).abs().max().item()
        inputs = self.encode(prompt)
        paired = {k: v.repeat(2, 1) for k, v in inputs.items()}
        unmodified = self.model(**paired, use_cache=False).logits
        with self.intervention(spec, torch.tensor([1, 0])):
            changed = self.model(**paired, use_cache=False).logits
        isolation = (changed[1] - unmodified[1]).abs().max().item()
        # Cached step vs full replay with exactly the same intervention positions.
        with self.intervention(spec):
            prefill = self.model(**inputs, use_cache=True)
            next_id = prefill.logits[:, -1].argmax(-1, keepdim=True)
            cached = self.model(input_ids=next_id, past_key_values=prefill.past_key_values,
                attention_mask=torch.ones(1, inputs.input_ids.shape[1] + 1, device=self.device), use_cache=True).logits[:, -1]
        def replay_hook(module, args, output):
            value = output.clone()
            value[:, -2:] += spec.direction * spec.dose * scale
            return value
        h = down.register_forward_hook(replay_hook)
        try:
            replay = self.model(input_ids=torch.cat([inputs.input_ids, next_id], dim=1), use_cache=False).logits[:, -1]
        finally:
            h.remove()
        errors = {'zero_dose': (base-zero).abs().max().item(), 'hook_removal': (base-restored).abs().max().item(),
            'pre_post_down_equivalence': equivalence, 'batch_isolation': isolation,
            'cached_decode_replay': (cached-replay).abs().max().item()}
        return {'passed': all(v < 2e-4 for v in errors.values()), 'max_abs_errors': errors,
            'tolerance': 2e-4, 'padding_policy': 'No padded inputs accepted by campaign; single-example inference only.'}


class JobStore:
    """Sequential single-worker journal with atomic artifacts and idempotent keys."""
    def __init__(self, root, identity, max_jobs=2500, max_seconds=1200):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        self.max_jobs = max_jobs
        self.deadline = time.monotonic() + max_seconds
        self.db = sqlite3.connect(self.root / 'jobs.sqlite')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT, artifact TEXT, error TEXT)')
        self.db.commit()

    def run(self, config, action):
        key = fingerprint({'identity': self.identity, 'job': config})
        row = self.db.execute('SELECT status,artifact FROM jobs WHERE id=?', (key,)).fetchone()
        if row and row[0] == 'complete':
            path = self.root / row[1]
            value = json.loads(path.read_text(encoding='utf-8'))
            if value['job_id'] != key or value['config'] != config:
                raise ValueError('Artifact identity mismatch')
            return value['result']
        count = self.db.execute('SELECT count(*) FROM jobs').fetchone()[0]
        if (not row and count >= self.max_jobs) or time.monotonic() > self.deadline:
            raise RuntimeError('Campaign job/time budget reached')
        self.db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?)', (key, 'running', None, None))
        self.db.commit()
        try:
            result = action()
            relative = 'artifacts/' + key + '.json'
            write_json(self.root / relative, {'job_id': key, 'config': config, 'result': result})
            self.db.execute('UPDATE jobs SET status=?,artifact=? WHERE id=?', ('complete', relative, key))
            self.db.commit()
            return result
        except Exception as exc:
            self.db.execute('UPDATE jobs SET status=?,error=? WHERE id=?', ('failed', str(exc), key))
            self.db.commit()
            raise
