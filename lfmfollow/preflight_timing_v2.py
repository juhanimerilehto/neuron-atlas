"""Versioned timing check: exact cached manual reference; full-prefix drift is diagnostic."""
from contextlib import contextmanager
import gc
from pathlib import Path
import torch
from familylab.preflight import load
from lfmfollow.core_v1 import PROGRAM, PARENT, read, digest
from lfmfollow.timed_actor_v1 import Worker
from reference import write_json


@contextmanager
def independent_hook(worker, sites, timing, prompt_length, full_prefix=False):
    handles = []
    by_layer = {}
    for site in sites:
        by_layer.setdefault(site['layer'], []).append(site)
    def attach(layer, selected_sites):
        calls = [0]
        def pre(module, args):
            x = args[0].clone(); step = calls[0]; calls[0] += 1
            absolute = list(range(x.shape[1])) if full_prefix or step == 0 else [prompt_length + step - 1]
            assert len(absolute) == x.shape[1]
            selected = []
            for position in absolute:
                prediction = position - (prompt_length - 1)
                if timing == 'all': active = True
                elif timing == 'prompt': active = position < prompt_length
                elif timing == 'decode': active = position >= prompt_length
                elif timing.startswith('window_'):
                    start, end = map(int, timing.split('_')[1:]); active = start <= prediction < end
                else: active = prediction == int(timing.split('_')[1])
                selected.append(active)
            mask = torch.tensor(selected, device=worker.device)[None, :]
            for site in selected_sites:
                neuron = site['neuron']; source = x[:, :, neuron].float()
                amount = site['value'] * worker.cal[str(layer)]['activation_abs_max'][neuron]
                if site['operator'] == 'scale': desired = source * site['value']
                elif site['operator'] == 'add': desired = source + amount
                else: desired = torch.full_like(source, amount)
                x[:, :, neuron] = torch.where(mask, desired.to(x.dtype), x[:, :, neuron])
            return (x,)
        handles.append(worker.layers[layer].mlp.down_proj.register_forward_pre_hook(pre))
    try:
        for layer, sites_at_layer in by_layer.items(): attach(layer, sites_at_layer)
        yield
    finally:
        for handle in handles: handle.remove()


@torch.inference_mode()
def cached(worker, encoded, forced, steps):
    output = worker.model(**encoded, use_cache=True, logits_to_keep=1)
    result = [output.logits[:, -1].float().clone()]; cache = output.past_key_values
    for step in range(1, steps + 1):
        output = worker.model(input_ids=torch.tensor([[forced[step-1]]], device=worker.device), past_key_values=cache,
            attention_mask=torch.ones(1, encoded.input_ids.shape[1]+step, dtype=torch.long, device=worker.device),
            use_cache=True, logits_to_keep=1)
        result.append(output.logits[:, -1].float().clone()); cache = output.past_key_values
    return result


@torch.inference_mode()
def main():
    target = PROGRAM / 'timing-preflight-v2.json'
    actor_sha = digest(Path(__file__).with_name('timed_actor_v1.py'))
    if target.exists():
        saved = read(target); assert saved['passed'] and saved['actor_source_sha256'] == actor_sha
        assert saved['preflight_source_sha256'] == digest(Path(__file__))
        print('Versioned cached-reference preflight retained.', flush=True); return
    torch.set_num_threads(4); torch.backends.cuda.matmul.allow_tf32 = False
    results = {}
    for name in ('original', 'abliterated'):
        _, native = load(name); worker = Worker(native.model, native.tok); worker.cal = read(PARENT / name / 'calibration.json')
        prompt = 'Explain why a paper kite can stay in the air.'; encoded = worker.encode(prompt); length = encoded.input_ids.shape[1]
        forced = worker.tok.encode(' A light wind can lift a carefully made paper kite above the grass on a sunny afternoon and gently carry it toward a nearby tree.', add_special_tokens=False)
        profiles = [([{'layer': 2, 'neuron': 3420, 'operator': op, 'value': value}], timing, 4)
                    for op, value in [('clamp', 3.), ('add', 1.), ('scale', 2.)]
                    for timing in ('all', 'prompt', 'decode', 'window_2_4', 'pulse_2')]
        profiles += [([{'layer': 2, 'neuron': 3420, 'operator': 'clamp', 'value': 3.}], timing, 18)
                     for timing in ('window_8_24', 'pulse_16')]
        profiles += [([{'layer': 2, 'neuron': 3420, 'operator': 'clamp', 'value': 3.},
                       {'layer': 5, 'neuron': 4206, 'operator': 'clamp', 'value': -2.}], 'all', 4)]
        checks = []
        for sites, timing, steps in profiles:
            assert len(forced) >= steps
            cfg = {'condition': 'positive', 'sites': sites, 'timing': timing}
            with worker.hook([cfg]): actual = cached(worker, encoded, forced, steps)
            with independent_hook(worker, sites, timing, length): expected = cached(worker, encoded, forced, steps)
            errors = [(a-b).abs().max().item() for a, b in zip(actual, expected)]
            assert max(errors) == 0., (name, sites, timing, errors)
            replay_errors = []
            for step, value in enumerate(actual):
                ids = torch.cat([encoded.input_ids, torch.tensor([forced[:step]], dtype=torch.long, device=worker.device)], dim=1)
                with independent_hook(worker, sites, timing, length, full_prefix=True):
                    replay = worker.model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False, logits_to_keep=1).logits[:, -1].float()
                replay_errors.append((value-replay).abs().max().item())
            checks.append({'sites': sites, 'timing': timing, 'teacher_forced_steps': steps,
                'max_cached_vs_independent_cached_error': max(errors), 'full_prefix_replay_errors_diagnostic': replay_errors})
        cfg = {'prompt': prompt, 'layer': 2, 'neuron': 3420, 'condition': 'positive', 'factor': 9., 'max_tokens': 12}
        native.cal = worker.cal
        a, b = native.generate([cfg]), worker.generate([cfg])
        assert a[0]['token_ids'] == b[0]['token_ids'] and a[0]['batch_baseline']['token_ids'] == b[0]['batch_baseline']['token_ids']
        isolated = worker.generate([cfg, {**cfg, 'condition': 'baseline'}])
        assert isolated[1]['token_ids'] == isolated[1]['batch_baseline']['token_ids']
        results[name] = {'passed': True, 'checks': checks, 'all_position_clamp_matches_native': True,
            'untouched_row_isolation': True, 'full_prefix_diagnostic_max': max(max(r['full_prefix_replay_errors_diagnostic']) for r in checks)}
        print(name + ' exact cached-reference conformance passed', flush=True)
        del native, worker, a, b, isolated, actual, expected; gc.collect(); torch.cuda.empty_cache()
    write_json(target, {'passed': True, 'models': results, 'actor_source_sha256': actor_sha,
        'preflight_source_sha256': digest(Path(__file__)),
        'versioned_reason': 'v1 rejected a 0.28125 BF16 cached/full-prefix discrepancy. v2 requires exact equality with an independently coded manual cached intervention; full-prefix drift remains recorded, not represented as exact equivalence.',
        'predecessor_failure_sha256': digest(PROGRAM / 'diagnostics/timing-preflight-v1-failure.json')})


if __name__ == '__main__': main()
