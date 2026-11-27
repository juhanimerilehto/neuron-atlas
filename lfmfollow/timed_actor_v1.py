"""Timed, row-isolated MLP interventions; preserve native LFM cache behavior."""
from contextlib import contextmanager
import re
import torch
from familylab.actor import Worker as NativeWorker


def position_mask(timing, call, length, device):
    positions = torch.arange(1 - length, 1, device=device) if call == 0 else torch.full((length,), call, device=device)
    if timing == 'all':
        return torch.ones(length, dtype=torch.bool, device=device)
    if timing == 'prompt':
        return positions <= 0
    if timing == 'decode':
        return positions > 0
    window = re.fullmatch(r'window_(\d+)_(\d+)', timing)
    if window:
        start, end = map(int, window.groups()); assert 0 <= start < end <= 512
        return (positions >= start) & (positions < end)
    pulse = re.fullmatch(r'pulse_(\d+)', timing)
    assert pulse and int(pulse[1]) < 512
    return positions == int(pulse[1])


class Worker(NativeWorker):
    @contextmanager
    def hook(self, configs):
        handles, groups, trace, calls = [], {}, [], {}
        for row, cfg in enumerate(configs):
            if cfg['condition'] == 'baseline':
                continue
            sites = cfg.get('sites') or [{'layer': cfg['layer'], 'neuron': cfg['neuron'], 'operator': 'clamp',
                'value': cfg.get('factor', 1.) * (1 if cfg['condition'] == 'positive' else -1) if cfg['condition'] != 'off' else 0.}]
            assert len({(s['layer'], s['neuron']) for s in sites}) == len(sites)
            for site in sites:
                assert 0 <= site['layer'] < 16 and 0 <= site['neuron'] < 4608
                groups.setdefault(site['layer'], {}).setdefault(row, []).append(site)
        def attach(layer, rows):
            projection = self.layers[layer].mlp.down_proj
            calls[layer] = 0
            captured = {}
            directions = {}
            for row in rows:
                if configs[row].get('random_index') is not None:
                    generator = torch.Generator().manual_seed(990000 + layer * 1000 + configs[row]['random_index'])
                    vector = torch.randn(projection.out_features, generator=generator).to(self.device)
                    directions[row] = vector / vector.norm()
            def pre(module, args):
                original = args[0]; changed = original.clone(); call = calls[layer]; calls[layer] += 1
                pushes = {}; norms = torch.zeros(len(configs), device=self.device)
                active = torch.zeros(len(configs), dtype=torch.bool, device=self.device)
                for row, sites in rows.items():
                    mask = position_mask(configs[row].get('timing', 'all'), call, original.shape[1], self.device)
                    indices = torch.tensor([s['neuron'] for s in sites], device=self.device)
                    natural = original[row].index_select(1, indices)
                    targets = []
                    for column, site in enumerate(sites):
                        source = natural[:, column].float(); value = site['value']
                        if site['operator'] == 'scale':
                            target = source * value
                        else:
                            target_value = value * self.cal[str(layer)]['activation_abs_max'][site['neuron']]
                            target = torch.full_like(source, target_value) if site['operator'] == 'clamp' else source + target_value
                        targets.append(torch.where(mask, target.to(original.dtype), natural[:, column]))
                    desired = torch.stack(targets, dim=1)
                    delta = desired.float() - natural.float()
                    write = delta @ projection.weight[:, indices].detach().float().T
                    requested_norm = write.norm(dim=-1)
                    norms[row] = requested_norm.max()
                    active[row] = (delta != 0).any()
                    if row in directions:
                        pushes[row] = (requested_norm[:, None] * directions[row][None, :]).to(original.dtype)
                    else:
                        for column, site in enumerate(sites):
                            changed[row, :, site['neuron']] = desired[:, column]
                captured['pushes'] = pushes
                trace.append({'layer': layer, 'call': call, 'norms': norms, 'active': active})
                return (changed,)
            def post(module, args, output):
                if not captured.get('pushes'):
                    return output
                result = output.clone()
                for row, push in captured['pushes'].items():
                    result[row] += push
                return result
            handles.extend([projection.register_forward_pre_hook(pre), projection.register_forward_hook(post)])
        try:
            for layer, rows in groups.items():
                attach(layer, rows)
            yield {'trace': trace, 'calls': calls}
        finally:
            for handle in handles:
                handle.remove()

    @torch.inference_mode()
    def generate(self, configs):
        assert len({(c['prompt'], c['max_tokens']) for c in configs}) == 1
        anchor = {**configs[0], 'condition': 'baseline'}; anchor.pop('random_index', None)
        all_configs = configs + [anchor]
        inputs = self.encode(configs[0]['prompt']); length = inputs.input_ids.shape[1]
        values = {k: v.repeat(len(all_configs), 1) for k, v in inputs.items()}
        with self.hook(all_configs) as diagnostics:
            output = self.model.generate(**values, max_new_tokens=configs[0]['max_tokens'], do_sample=False,
                use_cache=True, pad_token_id=self.tok.eos_token_id, temperature=None, top_p=None, top_k=None, logits_to_keep=1)
        result = []
        for tokens in output[:, length:].tolist():
            stop = next((i for i, token in enumerate(tokens) if token in self.eos), None)
            if stop is not None:
                tokens = tokens[:stop + 1]
            result.append({'text': self.tok.decode(tokens, skip_special_tokens=True), 'token_ids': tokens,
                'termination': 'eos' if tokens and tokens[-1] in self.eos else 'max_tokens'})
        for row, value in enumerate(result[:-1]):
            valid = [entry for entry in diagnostics['trace'] if entry['call'] < len(value['token_ids'])]
            positions = sorted({entry['call'] for entry in valid if bool(entry['active'][row])})
            maximum = max([float(entry['norms'][row]) for entry in valid] or [0.])
            value.update(batch_baseline=result[-1], batch_width=len(all_configs))
            value['intervention'] = {'sites': configs[row].get('sites'), 'timing': configs[row].get('timing', 'all'),
                'applied_to_generated_sequence': bool(positions), 'active_prediction_positions': positions,
                'max_per_projection_linearized_write_l2': maximum,
                'position_policy': 'Prediction index 0 is the last prompt position; cached call k predicts response token k. '
                    'All/prompt also intervene on earlier prompt tokens. Exposure diagnostics exclude internal steps after this row finished.',
                'random_control_policy': 'Four fixed directions per layer; aggregate within-projection write norm from BF16 input deltas and projection weights, then BF16-rounded output addition. '
                    'Across different layers these are local norms, not a single net residual norm.'}
        return result[:-1]
