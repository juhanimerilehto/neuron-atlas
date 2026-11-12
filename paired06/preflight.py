"""Calibrate, freeze shared normal continuations, and check the late-position worker."""
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'worker'))
from paired06.actor import Worker
from paired06 import data
from reference import fingerprint, write_json

OUT = ROOT / 'campaigns' / data.CAMPAIGN


def load(name):
    info = json.loads((OUT / name / 'model.json').read_text(encoding='utf-8'))
    model = AutoModelForCausalLM.from_pretrained(info['snapshot'], local_files_only=True, trust_remote_code=False,
                                              use_safetensors=True, torch_dtype=torch.bfloat16,
                                              attn_implementation='sdpa').to('cuda').eval()
    tokenizer = AutoTokenizer.from_pretrained(info['snapshot'], local_files_only=True, trust_remote_code=False)
    original_info = json.loads((OUT / 'original' / 'model.json').read_text(encoding='utf-8'))
    original_tokenizer = AutoTokenizer.from_pretrained(original_info['snapshot'], local_files_only=True, trust_remote_code=False)
    assert tokenizer.get_vocab() == original_tokenizer.get_vocab(), 'The paired checkpoints need the same token IDs'
    tokenizer.chat_template = original_tokenizer.chat_template
    return info, Worker(model, tokenizer)


def calibrate(worker):
    layers = list(range(len(worker.layers)))
    samples = [worker.calibration_sample(prompt, layers) for prompt in data.CALIBRATION]
    return {str(layer): {'activation_abs_max': np.max([sample[str(layer)]['activation_abs_max'] for sample in samples], axis=0).tolist(),
                         'median_residual_l2': float(np.median([sample[str(layer)]['residual_l2'] for sample in samples]))}
            for layer in layers}


def baseline(worker, prompt):
    encoded = worker.encode(prompt)
    result = worker.model.generate(**encoded, max_new_tokens=64, do_sample=False, use_cache=True,
                                   logits_to_keep=1, pad_token_id=worker.tok.eos_token_id,
                                   temperature=None, top_p=None, top_k=None)
    continuation = result[0, encoded.input_ids.shape[1]:].tolist()
    continuation = continuation[:next((i for i, token in enumerate(continuation) if token in worker.eos), len(continuation))]
    points = [point for point in data.CHECKPOINTS if point <= len(continuation)]
    assert any(point >= 32 for point in points), 'Screening baseline too short for later-token screening'
    prompt_ids = encoded.input_ids[0].tolist()
    return {'prompt': prompt, 'input_ids': prompt_ids + continuation, 'continuation_ids': continuation,
            'continuation_text': worker.tok.decode(continuation, skip_special_tokens=True),
            'checkpoints': points, 'positions': [len(prompt_ids) - 1 + point for point in points]}


def main():
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(data.SEED)
    report = {'models': {}, 'batch_size': 128}
    report['chat_template_policy'] = 'Both checkpoints use the original Qwen3-0.6B chat template with thinking disabled.'
    shared_calibration = None
    bank = None
    vocabulary = None
    for name in data.MODELS:
        info, worker = load(name)
        actual_vocabulary = fingerprint(worker.tok.get_vocab())
        vocabulary = vocabulary or actual_vocabulary
        assert vocabulary == actual_vocabulary, 'Tokenizer vocabulary differs'
        config = info['config']
        assert config['model_type'] == 'qwen3' and config['num_hidden_layers'] == 28 and config['intermediate_size'] == 3072
        native = calibrate(worker)
        write_json(OUT / name / 'native-calibration.json', native)
        if name == 'original':
            shared_calibration = native
            bank = {prompt: baseline(worker, prompt) for prompt in data.SCREEN + data.FINE}
            write_json(OUT / 'prefix-bank.json', bank)
        worker.cal = shared_calibration
        write_json(OUT / name / 'calibration.json', shared_calibration)
        for prompt, prefix in bank.items():
            assert prefix['input_ids'][:-len(prefix['continuation_ids'])] == worker.encode(prompt).input_ids[0].tolist()
        conformance = worker.conformance('Explain what a window blind does.', 4, 17)
        assert conformance['passed'], conformance
        prompt = data.SCREEN[0]
        configs = [{'layer': layer, 'neuron': neuron, 'condition': sign, 'factor': 4., 'prompt': prompt,
                    'max_tokens': 24} for layer, neuron, sign in [(4, 17, 'baseline'), (9, 21, 'negative'), (17, 33, 'positive')]]
        torch.cuda.synchronize()
        start = time.perf_counter()
        values = worker.prefix_scores(configs, bank[prompt])
        assert max(values[0]['js']) < 1e-7 and max(values[0]['kl']) < 1e-7
        many = [configs[0]] + [{**configs[1], 'neuron': i} for i in range(127)]
        batch = worker.prefix_scores(many, bank[prompt])
        assert max(batch[0]['js']) < 1e-7
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        # Independently attach the same coordinate clamp; verify all requested logits positions.
        chosen = configs[1]
        module = worker.layers[chosen['layer']].mlp.down_proj
        target = -4 * shared_calibration[str(chosen['layer'])]['activation_abs_max'][chosen['neuron']]
        def manual(module, args):
            x = args[0].clone()
            x[..., chosen['neuron']] = target
            return (x,)
        inputs = torch.tensor(bank[prompt]['input_ids'], device=worker.device)[None, :].repeat(4, 1)
        handle = module.register_forward_pre_hook(manual)
        with torch.inference_mode():
            reference = worker.model(input_ids=inputs, attention_mask=torch.ones_like(inputs), use_cache=False,
                                     logits_to_keep=torch.tensor(bank[prompt]['positions'], device=worker.device)).logits
        handle.remove()
        with worker.hook([chosen] * 4), torch.inference_mode():
            actual = worker.model(input_ids=inputs, attention_mask=torch.ones_like(inputs), use_cache=False,
                                  logits_to_keep=torch.tensor(bank[prompt]['positions'], device=worker.device)).logits
        assert torch.equal(reference, actual), 'Late-position worker differs from explicit clamp'
        assert not module._forward_pre_hooks and not module._forward_hooks
        report['models'][name] = {'repository': info['repository'], 'revision': info['revision'],
                                  'parameters': sum(p.numel() for p in worker.model.parameters()),
                                  'vocabulary_sha256': actual_vocabulary, 'conformance': conformance,
                                  'late_position_explicit_clamp_identical': True,
                                  'screen_batch_seconds': elapsed, 'peak_gpu_bytes': torch.cuda.max_memory_allocated(),
                                  'checkpoints': bank[prompt]['checkpoints']}
        print(json.dumps({'model': name, **report['models'][name]}), flush=True)
        del worker, reference, actual, inputs
        gc.collect()
        torch.cuda.empty_cache()
    report['passed'] = True
    write_json(OUT / 'preflight.json', report)


if __name__ == '__main__':
    main()
