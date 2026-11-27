"""Check timing/operators against independent full-prefix hooks in the native recurrent model."""
import gc
from pathlib import Path
import torch
from familylab.preflight import load
from lfmfollow.core_v1 import PROGRAM, PARENT, read, digest
from lfmfollow.timed_actor_v1 import Worker
from reference import write_json


@torch.inference_mode()
def main():
    target = PROGRAM / 'timing-preflight.json'
    if target.exists():
        report = read(target)
        assert report['passed'] and report['actor_source_sha256'] == digest(Path(__file__).with_name('timed_actor_v1.py'))
        assert report['preflight_source_sha256'] == digest(Path(__file__))
        print('Saved timing preflight retained.', flush=True); return
    torch.set_num_threads(4); torch.backends.cuda.matmul.allow_tf32 = False
    results = {}
    for name in ('original', 'abliterated'):
        _, native = load(name); worker = Worker(native.model, native.tok)
        worker.cal = read(PARENT / name / 'calibration.json')
        prompt = 'Explain why a paper kite can stay in the air.'
        encoded = worker.encode(prompt); prompt_length = encoded.input_ids.shape[1]
        forced = worker.tok.encode(' A light wind can lift a carefully made paper kite above the grass on a sunny afternoon.', add_special_tokens=False)
        tests = []
        for operator, value in [('clamp', 3.), ('add', 1.), ('scale', 2.)]:
            tests += [(operator, value, timing, 4) for timing in ('all', 'prompt', 'decode', 'window_2_4', 'pulse_2')]
        tests += [('clamp', 3., 'window_8_24', 18), ('clamp', 3., 'pulse_16', 18)]
        checks = []
        for operator, value, timing, steps in tests:
            assert len(forced) >= steps
            site = {'layer': 2, 'neuron': 3420, 'operator': operator, 'value': value}
            cfg = {'prompt': prompt, 'layer': 2, 'neuron': 3420, 'condition': 'positive',
                   'sites': [site], 'timing': timing, 'max_tokens': 8}
            cached_logits = []
            with worker.hook([cfg]):
                output = worker.model(**encoded, use_cache=True, logits_to_keep=1)
                cached_logits.append(output.logits[:, -1].float().clone()); cache = output.past_key_values
                for step in range(1, steps + 1):
                    output = worker.model(input_ids=torch.tensor([[forced[step-1]]], device=worker.device),
                        past_key_values=cache, attention_mask=torch.ones(1, prompt_length+step, dtype=torch.long, device=worker.device),
                        use_cache=True, logits_to_keep=1)
                    cached_logits.append(output.logits[:, -1].float().clone()); cache = output.past_key_values
            errors = []
            for step, cached in enumerate(cached_logits):
                ids = torch.cat([encoded.input_ids, torch.tensor([forced[:step]], dtype=torch.long, device=worker.device)], dim=1)
                def manual(module, args):
                    x = args[0].clone(); source = x[:, :, 3420].float()
                    active = []
                    for position in range(x.shape[1]):
                        prediction = position - (prompt_length - 1)
                        if timing == 'all': selected = True
                        elif timing == 'prompt': selected = position < prompt_length
                        elif timing == 'decode': selected = position >= prompt_length
                        elif timing.startswith('window_'):
                            start, end = map(int, timing.split('_')[1:]); selected = start <= prediction < end
                        else: selected = prediction == int(timing.split('_')[1])
                        active.append(selected)
                    mask = torch.tensor(active, device=worker.device)[None, :]
                    amount = value * worker.cal['2']['activation_abs_max'][3420]
                    desired = source * value if operator == 'scale' else source + amount if operator == 'add' else torch.full_like(source, amount)
                    x[:, :, 3420] = torch.where(mask, desired.to(x.dtype), x[:, :, 3420]); return (x,)
                handle = worker.layers[2].mlp.down_proj.register_forward_pre_hook(manual)
                try:
                    replay = worker.model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False, logits_to_keep=1).logits[:, -1].float()
                finally:
                    handle.remove()
                errors.append((cached-replay).abs().max().item())
            maximum = max(errors); assert maximum <= .25, (name, operator, timing, errors)
            checks.append({'operator': operator, 'timing': timing, 'value': value, 'teacher_forced_steps': steps,
                           'max_abs_cached_vs_independent_replay_error': maximum})
        cfg = {'prompt': prompt, 'layer': 2, 'neuron': 3420, 'condition': 'positive', 'factor': 9., 'max_tokens': 12}
        native.cal = worker.cal
        a = native.generate([cfg]); b = worker.generate([cfg])
        assert a[0]['token_ids'] == b[0]['token_ids'] and a[0]['batch_baseline']['token_ids'] == b[0]['batch_baseline']['token_ids']
        isolated = worker.generate([cfg, {**cfg, 'condition': 'baseline'}])
        assert isolated[1]['token_ids'] == isolated[1]['batch_baseline']['token_ids']
        results[name] = {'passed': True, 'checks': checks, 'replay_tolerance': .25,
                         'all_position_clamp_matches_native_worker': True, 'untouched_row_isolation': True}
        print(name + ' timing/operator preflight passed', flush=True)
        del native, worker, output, cache; gc.collect(); torch.cuda.empty_cache()
    write_json(target, {'passed': True, 'models': results,
        'actor_source_sha256': digest(Path(__file__).with_name('timed_actor_v1.py')), 'preflight_source_sha256': digest(Path(__file__))})


if __name__ == '__main__':
    main()
