"""100k admitted intervention jobs: broad screening, generated behavior, Codex and follow-ups."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import msvcrt
from pathlib import Path
import random
import re
import sys
import time
import numpy as np
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'worker'))
from reference import ReferenceWorker, fingerprint, write_json
from batched import BatchedWorker,BatchJournal
from codex_analysis import analyze

CAMPAIGN='behavior-100k-v1'
DISCOVERY=['Suggest a way to spend a free afternoon.','Tell me about a forest.',
    'Give advice for learning a new skill.','Explain how a bicycle works.']
VALIDATION=['How can I organize a small kitchen?','Suggest something to do on a rainy day.',
    'Explain why people enjoy music.','What should I pack for a short trip?',
    'Describe a quiet village.','How can a beginner start drawing?',
    'What happens when ice melts?','Recommend a way to welcome a guest.']
TEST=['Tell me about the ocean.','Suggest a healthy morning habit.',
    'Explain the purpose of a compass.','Describe a friendly robot.',
    'Give advice for keeping a journal.','Name things needed to plant a seed.',
    'Explain what a bridge does.','Suggest a way to celebrate finishing a project.']
FOLLOWUP=['Explain how to keep a room tidy.','Describe the feeling of a cool breeze.',
    'Recommend an activity for a family evening.','Tell me about an old library.']
CALIBRATION=['Explain gravity briefly.','Name an animal.','Tell me about a mountain.',
    'How do you make tea?','Write a short thank-you note.','What is a triangle?',
    'Suggest a simple meal.','Describe a cloudy sky.']
ROBUSTNESS=['Explain what makes a good neighbor.','Describe a train station.',
    'Suggest a creative hobby.','Give advice for planning a busy week.',
    'Tell me about a lake.','What can someone learn from cooking?',
    'Explain the purpose of a calendar.','Describe a pleasant walk.']
BEHAVIORS={
 'list':{'category':'Structure','words':['1','-','*','[','First','Here'],
    'description':'List-related response opening; Here/First are screening cues, not proof of a list.'},
 'french':{'category':'Language','words':['Le','La','Les','Je','Il','Une','Un','Bonjour','Voici','Pour','Vous','Nous'],
    'description':'French-associated opening tokens; overlapping words can occur in English.'},
 'uncertainty':{'category':'Style','words':['Maybe','Perhaps','Possibly','Probably','Likely','Unfortunately'],
    'description':'Hedging/uncertainty-associated openings; Unfortunately is affective rather than calibrated uncertainty.'},
 'affirmation':{'category':'Style','words':['Yes','Sure','Absolutely','Certainly','Indeed','Great','Good'],
    'description':'Affirmative/positive openings; not a measure of correctness or helpfulness.'}}


def text_metrics(text):
    words=re.findall(r"[\w']+",text.lower())
    grams=[tuple(words[i:i+3]) for i in range(max(0,len(words)-2))]
    french=sum(w in {'le','la','les','des','une','un','vous','nous','pour','avec','dans','est','que','je','et','de','du','voici','il'} for w in words)
    return {'list':bool(re.search(r'^\s*(?:\d+[.)]|[-*•])\s',text,re.M)),
        'french':french>=3 and french/max(1,len(words))>=.12,
        'uncertainty':bool(re.search(r'\b(maybe|perhaps|possibly|probably|might|uncertain|not sure|may be)\b',text,re.I)),
        'affirmation':bool(re.search(r'^\s*(yes|sure|absolutely|certainly|indeed|great|good)\b',text,re.I)),
        'words':len(words),'trigram_repetition':1-len(set(grams))/max(1,len(grams)) if grams else 0.}


def main():
    out=ROOT/'campaigns'/CAMPAIGN;out.mkdir(parents=True,exist_ok=True)
    with (out/'.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:run(out)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


def run(out):
    started=time.perf_counter();torch.set_num_threads(4);torch.manual_seed(2718)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    device='cuda' if torch.cuda.is_available() else 'cpu'
    if device!='cuda':raise RuntimeError('This 100k campaign requires the checked CUDA device')
    model_info=json.loads((ROOT/'campaigns/bracket-pilot-v1/model.json').read_text(encoding='utf-8'))
    tokenizer=AutoTokenizer.from_pretrained(model_info['snapshot'],local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(model_info['snapshot'],local_files_only=True,trust_remote_code=False,
        torch_dtype=torch.float32,attn_implementation='eager',use_safetensors=True).to(device).eval()
    reference=ReferenceWorker(model,tokenizer);worker=BatchedWorker(reference)
    layers=[4,9,14,19,24,29];doses=[-.6,-.3,.3,.6];rng=random.Random(2718)
    neurons={str(l):sorted(rng.sample(range(reference.layers[l].mlp.down_proj.in_features),950)) for l in layers}
    targets={b:sorted({ids[0] for word in spec['words'] for v in [word,' '+word]
        if len(ids:=tokenizer.encode(v,add_special_tokens=False))==1}) for b,spec in BEHAVIORS.items()}
    source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ROOT/'worker/reference.py',*sorted((ROOT/'engine').glob('*.py'))]}
    manifest={'campaign_id':CAMPAIGN,'schema_version':2,'model':{k:v for k,v in model_info.items() if k!='snapshot'},
        'source_hash':fingerprint(source),'sources':source,'seed':2718,'layers':layers,'neurons':neurons,'doses':doses,
        'max_jobs':100000,'planned_screen_jobs':91200,'batch_size':32,'dtype':'float32','device':device,
        'torch':torch.__version__,'behaviors':BEHAVIORS,'targets':targets,'discovery':DISCOVERY,'validation':VALIDATION,
        'locked_test':TEST,'followup':FOLLOWUP,'robustness':ROBUSTNESS,'calibration':CALIBRATION,
        'selection':'Top three distinct neuron-dose candidates per behavior by absolute screening probability gain; mean KL <= 1.5.',
        'random_controls':64,'max_codex_calls':12,'max_tokens_per_generation':48,
        'budget_semantics':'One job is one intervention/prompt distribution or generation; batched rows remain separate jobs. Unsteered calibration/conformance excluded.',
        'notes':'All first-token signals are screening proxies; generated lexical detectors are imperfect and labels remain hypotheses.'}
    path=out/'manifest.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=manifest:
        raise RuntimeError('Frozen campaign protocol changed; use a new campaign version')
    write_json(path,manifest)
    journal=BatchJournal(out/'jobs.sqlite',fingerprint(manifest),100000)
    def status(stage,**extra):
        value={'campaign_id':CAMPAIGN,'stage':stage,'completed_jobs':journal.completed(),'admitted_jobs':journal.count,
            'budget':100000,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'elapsed_this_invocation_seconds':time.perf_counter()-started,**extra}
        write_json(out/'status.json',value);print(json.dumps(value),flush=True)
    status('calibrating')
    cal_path=out/'calibration.json'
    calibration=json.loads(cal_path.read_text(encoding='utf-8')) if cal_path.exists() else reference.calibrate(CALIBRATION,layers)
    write_json(cal_path,calibration)
    check=reference.conformance(DISCOVERY[0],14,83,calibration['14']['median_residual_l2'])
    batch_check=worker.conformance(DISCOVERY[0],14,calibration['14']['median_residual_l2'])
    write_json(out/'conformance.json',{'reference':check,'batched':batch_check})
    if not check['passed'] or not batch_check['passed']:raise RuntimeError('Conformance failed')
    baseline={};directions={}
    def base(prompt):
        if prompt not in baseline:baseline[prompt]=reference.distribution(prompt)
        return baseline[prompt]
    def pushes(configs):
        values=[]
        for c in configs:
            key=(c['layer'],c['kind'],c['index'])
            if key not in directions:
                if c['kind']=='neuron':v=reference.column(c['layer'],c['index'])
                else:
                    generator=torch.Generator().manual_seed(900000+c['layer']*10000+c['index'])
                    v=torch.randn(model.config.hidden_size,generator=generator).to(device);v=v/v.norm()
                directions[key]=v
            values.append(directions[key]*c['dose']*calibration[str(c['layer'])]['median_residual_l2'])
        return torch.stack(values)
    def score_batch(configs):
        c=configs[0];assert all(v['prompt']==c['prompt'] and v['layer']==c['layer'] for v in configs)
        original=base(c['prompt'])
        changed=worker.distributions(c['prompt'],c['layer'],pushes(configs))
        kl=(original.exp()[None,:]*(original[None,:]-changed)).sum(-1)
        scores={b:torch.logsumexp(changed[:,ids],-1).exp() for b,ids in targets.items()}
        original_scores={b:torch.logsumexp(original[ids],-1).exp().item() for b,ids in targets.items()}
        tops=changed.topk(5,dim=-1)
        cpu={b:v.cpu().tolist() for b,v in scores.items()};kls=kl.cpu().tolist();indices=tops.indices.cpu().tolist();top_values=tops.values.cpu().tolist()
        return [{'probabilities':{b:cpu[b][i] for b in targets},'baseline_probabilities':original_scores,
            'kl':max(0.,kls[i]),'top_tokens':[{'id':idx,'text':tokenizer.decode([idx]),'logprob':value} for idx,value in zip(indices[i],top_values[i])]}
            for i in range(len(configs))]
    def measure(configs):return journal.run(configs,score_batch)
    def config(prompt,layer,kind,index,dose,stage='screen'):
        return {'type':'distribution','stage':stage,'prompt':prompt,'layer':layer,'kind':kind,'index':index,'dose':dose}
    screen=[]
    for layer in layers:
        layer_summary={n:{d:[] for d in doses} for n in neurons[str(layer)]}
        for prompt in DISCOVERY:
            for dose in doses:
                ns=neurons[str(layer)]
                for offset in range(0,len(ns),32):
                    subset=ns[offset:offset+32];configs=[config(prompt,layer,'neuron',n,dose) for n in subset]
                    for n,value in zip(subset,measure(configs)):layer_summary[n][dose].append(value)
            status('screening',layer=layer,prompt=prompt)
        for n,by_dose in layer_summary.items():
            for dose,values in by_dose.items():
                screen.append({'layer':layer,'neuron':n,'dose':dose,'mean_kl':float(np.mean([v['kl'] for v in values])),
                    'gains':{b:float(np.mean([v['probabilities'][b]-v['baseline_probabilities'][b] for v in values])) for b in targets}})
        write_json(out/'screen-summary.json',screen)
    chosen=[]
    for b in targets:
        used=set()
        for c in sorted([v for v in screen if v['mean_kl']<=1.5],key=lambda v:v['gains'][b],reverse=True):
            if (c['layer'],c['neuron']) not in used:
                chosen.append({**c,'behavior':b});used.add((c['layer'],c['neuron']))
            if len(used)==3:break
    write_json(out/'frozen-candidates.json',chosen);status('validation',candidate_count=len(chosen))
    records=[]
    prior=json.loads((ROOT/'dist/evidence/bracket-pilot-v1/catalogue-snapshot.json').read_text(encoding='utf-8')) if (ROOT/'dist/evidence/bracket-pilot-v1/catalogue-snapshot.json').exists() else json.loads((ROOT/'dist/catalogue.json').read_text(encoding='utf-8'))
    prior_records=[r for r in prior['records'] if not r['id'].startswith(CAMPAIGN)]
    def export():
        for r in records:write_json(ROOT/'dist'/r['artifact_url'],r)
        write_json(ROOT/'dist/catalogue.json',{'schema_version':2,'synthetic':False,'campaign_id':CAMPAIGN,
            'status':json.loads((out/'status.json').read_text(encoding='utf-8')),'records':prior_records+records})
        write_json(out/'findings.json',records)
    def aggregate(values,b):
        delta=[math.log(max(v['probabilities'][b],1e-30))-math.log(max(v['baseline_probabilities'][b],1e-30)) for v in values]
        return {'mean_delta_logprob':float(np.mean(delta)),
            'mean_probability_delta':float(np.mean([v['probabilities'][b]-v['baseline_probabilities'][b] for v in values])),
            'mean_kl':float(np.mean([v['kl'] for v in values])),'positive_contexts':sum(v>0 for v in delta),'n':len(values)}
    def generate_configs(configs):
        c=configs[0];ablate=[v['index'] if v.get('operation')=='ablate' else None for v in configs]
        return worker.generate(c['prompt'],c['layer'],pushes(configs),max_tokens=48,ablate=ablate if any(v is not None for v in ablate) else None)
    def generations(prompt,c):
        configs=[{'type':'generation','stage':'validation','prompt':prompt,'layer':c['layer'],'kind':'neuron',
            'index':c['neuron'],'dose':d} for d in [0,c['dose'],-c['dose']]]
        values=journal.run(configs,generate_configs)
        return {'prompt':prompt,'baseline':values[0],'steered':values[1],'opposite':values[2],
            'lexical_metrics':{k:text_metrics(v['text']) for k,v in zip(['baseline','steered','opposite'],values)}}
    for ordinal,c in enumerate(chosen):
        layer,n,dose,b=c['layer'],c['neuron'],c['dose'],c['behavior']
        validation=[measure([config(p,layer,'neuron',n,dose,'validation')])[0] for p in VALIDATION]
        controls_by_prompt=[]
        for prompt in VALIDATION:
            controls_by_prompt.append([value for start in range(0,64,32) for value in measure([config(prompt,layer,'random',i,dose,'validation') for i in range(start,start+32)])])
        controls=[aggregate([row[i] for row in controls_by_prompt],b) for i in range(64)]
        metrics=aggregate(validation,b)
        exceedance=(1+sum(v['mean_probability_delta']>=metrics['mean_probability_delta'] for v in controls))/65
        gens=[generations(p,c) for p in VALIDATION]
        lexical={k:sum(g['lexical_metrics'][k][b] for g in gens)/len(gens) for k in ['baseline','steered','opposite']}
        evidence=[]
        for p,v in zip(VALIDATION,validation):
            evidence.append({'prompt':p,'baseline_target_probability':v['baseline_probabilities'][b],
                'target_probability':v['probabilities'][b],'delta_logprob':math.log(max(v['probabilities'][b],1e-30)/max(v['baseline_probabilities'][b],1e-30)),
                'baseline_top_token':tokenizer.decode([base(p).argmax().item()]),'steered_top_token':v['top_tokens'][0]['text']})
        delta=np.array([v['delta_logprob'] for v in evidence]);bootstrap=np.random.default_rng(2718).choice(delta,(2000,8),replace=True).mean(1)
        record={'id':f'{CAMPAIGN}-L{layer}-N{n}-{b}','category':BEHAVIORS[b]['category'],
            'label':f'{b.title()} candidate · L{layer} N{n}','behavior':b,
            'summary':f"{lexical['baseline']*100:.0f}% → {lexical['steered']*100:.0f}% generated {b} lexical-detector rate; eight validation contexts.",
            'model':'SmolLM2-135M-Instruct','revision':model_info['revision'],'layer':layer,'neuron':n,
            'effect':metrics['mean_probability_delta']*100,'state':'Observed','synthetic':False,'n':8,'dose':dose,
            'scale':calibration[str(layer)]['median_residual_l2'],'dose_unit':'median last-prompt layer-output residual L2 norm',
            'operation':'normalized down-column addition','token_policy':'last prompt and each decode input',
            'target_token_ids':targets[b],'metric':f'{b} opening-token proxy probability change (percentage points)',
            'baseline':gens[0]['baseline']['text'],'steered':gens[0]['steered']['text'],
            'limitations':['Screening tokens and generated lexical detectors are proxies, not semantic truth.',
                'Eight validation contexts; candidates selected from 22,800 neuron-dose combinations.',
                'Control exceedance is based on absolute probability gain, uncorrected for the large search.',
                'No independent model replication; quality changes are not a capability guarantee.'],
            'validation':metrics,'generated_behavior_rates':lexical,'ci95_delta_logprob':np.quantile(bootstrap,[.025,.975]).tolist(),
            'random_control_exceedance':exceedance,'random_controls':controls,'evidence':evidence,'generations':gens,
            'conformance':{'passed':True,'reference':check,'batched':batch_check},
            'dose_response':[{'dose':v['dose'],'mean_delta_logprob':None,'mean_probability_delta':v['gains'][b]} for v in screen if v['layer']==layer and v['neuron']==n],
            'manifest_sha256':fingerprint(manifest),'calibration_sha256':fingerprint(calibration),'campaign_id':CAMPAIGN,
            'artifact_url':f'evidence/{CAMPAIGN}/L{layer}-N{n}-{b}.json','analyzer':'Codex analysis pending'}
        status('codex_analysis',candidate=record['id'],candidate_index=ordinal+1)
        try:
            record['codex_analysis']=analyze(record,out/'codex')
            hypothesis=record['codex_analysis']['analysis']
            if hypothesis['proposed_label']:record['label']=hypothesis['proposed_label']
            record['analyzer']='Codex CLI · schema and reference validated'
        except Exception as exc:
            record['analysis_error']=str(exc);record['analyzer']='Codex unavailable; analysis pending'
        # Test data is read only after the label and follow-up proposals have been frozen.
        tests=[measure([config(p,layer,'neuron',n,dose,'locked_test')])[0] for p in TEST]
        record['locked_test']=aggregate(tests,b)
        record['locked_test_generations']=[]
        for p in TEST[:4]:
            cfg=[{'type':'generation','stage':'locked_test','prompt':p,'layer':layer,'kind':'neuron','index':n,'dose':d} for d in [0,dose]]
            values=journal.run(cfg,generate_configs)
            record['locked_test_generations'].append({'prompt':p,'baseline':values[0],'steered':values[1],
                'lexical_metrics':{'baseline':text_metrics(values[0]['text']),'steered':text_metrics(values[1]['text'])}})
        record['followup_results']=[]
        for proposal in record.get('codex_analysis',{}).get('analysis',{}).get('followup_proposals',[]):
            operation=proposal['operation'];amount=proposal['dose'] if operation=='narrow_dose' else dose
            for p in FOLLOWUP:
                cfg={'type':'generation','stage':'codex_followup','prompt':p,'layer':layer,'kind':'neuron','index':n,
                    'dose':0 if operation=='ablate' else amount,'operation':operation}
                value=journal.run([cfg],generate_configs)[0]
                record['followup_results'].append({'proposal':proposal,'prompt':p,'result':value,'lexical_metrics':text_metrics(value['text'])})
        records.append(record);status('cataloguing',candidate=record['id'],catalogued=len(records));export()
    # Spend the remaining admitted-job budget on a prespecified fresh-context robustness grid.
    # Test results do not influence this grid or candidate selection.
    status('robustness',catalogued=len(records))
    robustness=[]
    for c in chosen:
        for dose in [-.75,-.45,-.15,.15,.45,.75]:
            for p in ROBUSTNESS:
                configs=[config(p,c['layer'],'random',i,dose,'robustness') for i in range(256)]
                configs.insert(0,config(p,c['layer'],'neuron',c['neuron'],dose,'robustness'))
                remaining=100000-journal.count
                if remaining<=0:break
                # Existing compatible controls are cache hits; admission remains capped transactionally.
                new=[]
                for cfg in configs:
                    key=fingerprint({'identity':journal.identity,'config':cfg})
                    exists=journal.db.execute('SELECT 1 FROM jobs WHERE id=?',(key,)).fetchone()
                    if exists or remaining>0:
                        new.append(cfg)
                        if not exists:remaining-=1
                if not new:break
                values=[value for start in range(0,len(new),32) for value in measure(new[start:start+32])]
                robustness.append({'candidate':c,'prompt':p,'dose':dose,'jobs':len(values),'mean_kl':float(np.mean([v['kl'] for v in values]))})
            if journal.count>=100000:break
        if journal.count>=100000:break
    write_json(out/'robustness-summary.json',robustness)
    for record in records:
        record['robustness_summary']={'status':'measured within remaining budget','scope':'predeclared fresh-context dose grid; per-job results retained in journal'}
    # Export all job data as compressed JSONL shards, avoiding 100k tiny files.
    artifact_dir=out/'artifacts';artifact_dir.mkdir(exist_ok=True)
    cursor=journal.db.execute('SELECT id,config,result FROM jobs ORDER BY id')
    shard=0;ledger=[]
    while rows:=cursor.fetchmany(2000):
        target=artifact_dir/f'jobs-{shard:03d}.jsonl.gz'
        with gzip.open(target,'wt',encoding='utf-8') as stream:
            for key,cfg,result in rows:stream.write(json.dumps({'job_id':key,'config':json.loads(cfg),'result':json.loads(result)},ensure_ascii=False)+'\n')
        ledger.append({'path':str(target.relative_to(out)),'jobs':len(rows),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()});shard+=1
    write_json(out/'artifact-ledger.json',ledger)
    status('complete',catalogued=len(records),codex_labels=sum('codex_analysis' in r for r in records),
        peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated())
    export()
    for name in ['manifest.json','conformance.json','status.json']:
        write_json(ROOT/'dist/evidence'/CAMPAIGN/name,json.loads((out/name).read_text(encoding='utf-8')))
    journal.db.close()


if __name__=='__main__':main()
