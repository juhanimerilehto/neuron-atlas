"""Run a bounded real, exploratory neuron campaign and export traceable catalogue records."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import time
import msvcrt
import numpy as np
import psutil
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
from reference import ReferenceWorker, Intervention, JobStore, fingerprint, write_json

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ['Name three fruits.', 'Give two tips for better sleep.', 'What is water made of?',
    'Suggest a weekend activity.', 'Describe a friendly dog.', 'Name a color.']
VALIDATION = ['How can I organize a small desk?', 'Recommend supplies for a picnic.',
    'What does a thermometer measure?', 'Explain why leaves are green.',
    'Write a greeting for a new colleague.', 'Describe the sound of rain.',
    'Suggest an indoor hobby.', 'What is the capital of Italy?']
CALIBRATION = ['Explain gravity briefly.', 'Name an animal.', 'Tell me about a mountain.',
    'How do you make tea?', 'Write a short thank-you note.', 'What is a triangle?',
    'Suggest a simple meal.', 'Describe a cloudy sky.']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--campaign', default='bracket-pilot-v1')
    args = parser.parse_args()
    if args.campaign != 'bracket-pilot-v1':
        raise ValueError('Only the preregistered pilot is implemented')
    out = ROOT / 'campaigns' / args.campaign
    out.mkdir(parents=True, exist_ok=True)
    with (out / '.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            run(out)
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def run(out):
    started = time.perf_counter()
    torch.set_num_threads(4)
    torch.manual_seed(1729)
    np.random.seed(1729)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model_info = json.loads((out / 'model.json').read_text(encoding='utf-8'))
    snapshot = model_info['snapshot']
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    resources = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'ram_total_bytes': psutil.virtual_memory().total, 'ram_available_bytes': psutil.virtual_memory().available,
        'cpu_logical': psutil.cpu_count(), 'cpu_physical': psutil.cpu_count(logical=False),
        'device': device, 'gpu': torch.cuda.get_device_name(0) if device == 'cuda' else None,
        'gpu_free_total_bytes': list(torch.cuda.mem_get_info()) if device == 'cuda' else None,
        'disk_free_bytes': psutil.disk_usage(str(ROOT)).free}
    write_json(out / 'resources.json', resources)
    print('Loading pinned model on ' + device, flush=True)
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False,
        torch_dtype=torch.float32, attn_implementation='eager', use_safetensors=True).to(device).eval()
    worker = ReferenceWorker(model, tokenizer)
    layers = [len(worker.layers)//2, len(worker.layers)*3//4]
    rng = random.Random(1729)
    neurons = {str(layer): sorted(rng.sample(range(worker.layers[layer].mlp.down_proj.in_features), 24)) for layer in layers}
    target_ids = sorted({tokenizer.encode(t, add_special_tokens=False)[0] for t in ['[', ' [']
        if len(tokenizer.encode(t, add_special_tokens=False)) == 1})
    if not target_ids:
        raise ValueError('Expected single-token bracket targets')
    source_hash = fingerprint({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT/'worker').glob('*.py'))})
    manifest = {'schema_version': 1, 'campaign_id': out.name, 'model': {k:v for k,v in model_info.items() if k!='snapshot'},
        'code_hash': source_hash, 'device': device, 'dtype': 'float32', 'torch': torch.__version__,
        'transformers': transformers.__version__, 'numpy': np.__version__, 'python': platform.python_version(),
        'seed':1729, 'layers':layers, 'neurons':neurons, 'doses':[-.3,-.15,.15,.3],
        'target_token_ids':target_ids, 'target_tokens':[tokenizer.decode([i]) for i in target_ids],
        'metric':'log probability of first-token bracket set; natural logarithm',
        'position_policy':'last unpadded prompt token; every decode input for generations',
        'operation':'normalized down-column write addition at MLP down-projection output',
        'calibration_prompts':CALIBRATION, 'discovery_prompts':DISCOVERY, 'validation_prompts':VALIDATION,
        'random_directions_per_layer':16, 'selection':'top two neuron-dose combinations per layer with distinct neurons by discovery mean target logprob delta',
        'claim_policy':'exploratory observations only; no confirmatory test or capability claim',
        'max_jobs':2500, 'max_seconds_per_invocation':1200, 'max_generation_tokens':48,
        'chat_template_hash':hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()}
    manifest_path = out/'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding='utf-8')) != manifest:
        raise RuntimeError('Campaign identity changed. Use a new campaign directory/version.')
    write_json(manifest_path, manifest)
    calibration_path=out/'calibration.json'
    if calibration_path.exists():
        calibration=json.loads(calibration_path.read_text(encoding='utf-8'))
    else:
        calibration=worker.calibrate(CALIBRATION,layers)
        write_json(calibration_path,calibration)
    conformance=worker.conformance(DISCOVERY[0],layers[0],neurons[str(layers[0])][0],calibration[str(layers[0])]['median_residual_l2'])
    write_json(out/'conformance.json',conformance)
    if not conformance['passed']:
        raise RuntimeError('Model conformance failed: '+str(conformance))
    print('Conformance passed: '+str(conformance['max_abs_errors']),flush=True)
    identity={'manifest':fingerprint(manifest),'calibration':fingerprint(calibration)}
    store=JobStore(out,identity,max_jobs=2500,max_seconds=1200)
    baselines={}
    def baseline(prompt):
        if prompt not in baselines:
            baselines[prompt]=worker.distribution(prompt)
        return baselines[prompt]
    def measure(prompt,layer,kind,index,dose):
        config={'type':'distribution','prompt':prompt,'layer':layer,'kind':kind,'index':index,'dose':dose}
        def action():
            base=baseline(prompt)
            spec=make_spec(layer,kind,index,dose)
            changed=worker.distribution(prompt,spec)
            target=torch.logsumexp(changed[target_ids],0).item()
            original=torch.logsumexp(base[target_ids],0).item()
            values,indices=changed.topk(8)
            kl=(base.exp()*(base-changed)).sum().item()
            return {'baseline_target_logprob':original,'target_logprob':target,
                'delta_logprob':target-original,'baseline_target_probability':math.exp(original),
                'target_probability':math.exp(target),'kl_baseline_to_steered':max(0.,kl),
                'entropy':-(changed.exp()*changed).sum().item(),
                'baseline_top_token':tokenizer.decode([base.argmax().item()]),
                'steered_top_token':tokenizer.decode([changed.argmax().item()]),
                'top_token_changed':bool(base.argmax()!=changed.argmax()),
                'top_tokens':[{'id':i,'text':tokenizer.decode([i]),'logprob':v} for i,v in zip(indices.tolist(),values.tolist())]}
        return store.run(config,action)
    def make_spec(layer,kind,index,dose):
        if kind=='neuron':
            direction=worker.column(layer,index)
        else:
            generator=torch.Generator(device='cpu').manual_seed(100000+layer*1000+index)
            direction=torch.randn(model.config.hidden_size,generator=generator)
            direction=direction/direction.norm()
        return Intervention(layer,direction,dose,calibration[str(layer)]['median_residual_l2'])
    def aggregate(results):
        return {'mean_delta_logprob':float(np.mean([r['delta_logprob'] for r in results])),
            'mean_probability_delta':float(np.mean([r['target_probability']-r['baseline_target_probability'] for r in results])),
            'mean_kl':float(np.mean([r['kl_baseline_to_steered'] for r in results])),
            'positive_contexts':sum(r['delta_logprob']>0 for r in results),'n':len(results)}
    screen=[]
    for layer in layers:
        for neuron in neurons[str(layer)]:
            for dose in manifest['doses']:
                values=[measure(p,layer,'neuron',neuron,dose) for p in DISCOVERY]
                screen.append({'layer':layer,'neuron':neuron,'dose':dose,**aggregate(values)})
        print(f'Screened layer {layer}: {len(screen)} neuron-dose combinations',flush=True)
    write_json(out/'screen.json',screen)
    candidates=[]
    for layer in layers:
        used=set()
        for candidate in sorted([r for r in screen if r['layer']==layer],key=lambda x:x['mean_delta_logprob'],reverse=True):
            if candidate['neuron'] not in used:
                candidates.append(candidate);used.add(candidate['neuron'])
            if len(used)==2:
                break
    write_json(out/'frozen-candidates.json',candidates)
    print('Frozen candidates: '+str([(c['layer'],c['neuron'],c['dose']) for c in candidates]),flush=True)
    entries=[]
    for c in candidates:
        layer,neuron,dose=c['layer'],c['neuron'],c['dose']
        validation=[measure(p,layer,'neuron',neuron,dose) for p in VALIDATION]
        metrics=aggregate(validation)
        controls=[aggregate([measure(p,layer,'random',i,dose) for p in VALIDATION]) for i in range(16)]
        write_json(out/f'controls-L{layer}-N{neuron}.json',controls)
        empirical=(1+sum(r['mean_delta_logprob']>=metrics['mean_delta_logprob'] for r in controls))/17
        values=np.array([r['delta_logprob'] for r in validation])
        bootstrap=np.random.default_rng(1729).choice(values,(2000,len(values)),replace=True).mean(1)
        ci=np.quantile(bootstrap,[.025,.975]).tolist()
        generations=[]
        for p in VALIDATION[:3]:
            def generate(kind,amount):
                spec=None if kind=='baseline' else make_spec(layer,'neuron',neuron,amount)
                config={'type':'generation','prompt':p,'layer':layer if spec else None,
                    'neuron':neuron if spec else None,'dose':amount if spec else 0,'max_tokens':48}
                return store.run(config,lambda:worker.generate(p,spec))
            generations.append({'prompt':p,'baseline':generate('baseline',0),
                'steered':generate('neuron',dose),'opposite':generate('neuron',-dose)})
        evidence=[{'prompt':p,**r} for p,r in zip(VALIDATION,validation)]
        limitations=['Exploratory sample: 24 neurons in each of two layers; no full sweep.',
            'Eight validation prompts, no locked confirmatory test or independent replication.',
            'Target is a first-token bracket set; this does not establish JSON validity or useful format control.',
            'Sixteen random directions provide a coarse empirical reference; no multiple-comparison correction.',
            'Bootstrap interval is descriptive over these eight contexts; it does not establish broad generalization.',
            'KL and entropy are distributional diagnostics, not capability preservation measurements.']
        entry={'id':f'{out.name}-L{layer}-N{neuron}','category':'Structure',
            'label':f'Bracket-onset candidate · L{layer} N{neuron}',
            'summary':f"Mean first-token bracket probability changed by {metrics['mean_probability_delta']*100:+.3f} percentage points on eight validation prompts.",
            'model':'SmolLM2-135M-Instruct','revision':model_info['revision'],'layer':layer,'neuron':neuron,
            'effect':metrics['mean_probability_delta']*100,'state':'Observed','synthetic':False,
            'metric':'First-token bracket probability change (percentage points)','n':len(validation),
            'dose':dose,'dose_unit':'median last-prompt layer-output residual L2 norm',
            'scale':calibration[str(layer)]['median_residual_l2'],'operation':manifest['operation'],
            'token_policy':manifest['position_policy'],'target_token_ids':target_ids,
            'baseline':generations[0]['baseline']['text'],'steered':generations[0]['steered']['text'],
            'limitations':limitations,'validation':metrics,'discovery':c,'ci95_delta_logprob':ci,
            'random_control_exceedance':empirical,'random_controls':controls,'evidence':evidence,
            'generations':generations,'conformance':conformance,
            'dose_response':[r for r in screen if r['layer']==layer and r['neuron']==neuron],
            'manifest_sha256':fingerprint(manifest),'calibration_sha256':fingerprint(calibration),
            'analyzer':'deterministic target metric; no LLM analysis',
            'artifact_url':f'evidence/{out.name}/L{layer}-N{neuron}.json'}
        write_json(ROOT/'dist'/entry['artifact_url'],entry)
        entries.append(entry)
        print(f"Candidate L{layer} N{neuron}: delta logp {metrics['mean_delta_logprob']:.3f}, control exceedance {empirical:.3f}",flush=True)
    summary={'campaign_id':out.name,'completed_utc':datetime.now(timezone.utc).isoformat(),
        'elapsed_seconds':time.perf_counter()-started,'jobs':store.db.execute('SELECT status,count(*) FROM jobs GROUP BY status').fetchall(),
        'peak_gpu_allocated_bytes':torch.cuda.max_memory_allocated() if device=='cuda' else None,
        'records':entries,'manifest':manifest,'resources':resources,'conformance':conformance}
    write_json(out/'summary.json',summary)
    write_json(ROOT/'dist'/'catalogue.json',{'schema_version':1,'synthetic':False,'campaign_id':out.name,
        'completed_utc':summary['completed_utc'],'records':entries})
    write_json(ROOT/'dist'/'evidence'/out.name/'manifest.json',manifest)
    write_json(ROOT/'dist'/'evidence'/out.name/'conformance.json',conformance)
    print(f"COMPLETE: {len(entries)} records, {summary['elapsed_seconds']:.1f}s, {summary['jobs']}",flush=True)


if __name__ == '__main__':
    main()
