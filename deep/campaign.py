"""Exactly 100k measured configurations, broad neuron coverage and open-ended reviews."""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import copy,gc,gzip,hashlib,json,msvcrt,sys
from pathlib import Path
import numpy as np
import torch,transformers
from transformers import AutoModelForCausalLM,AutoTokenizer
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'deep'),str(ROOT/'worker'),str(ROOT/'engine'),str(ROOT/'wide')]
from reference import fingerprint,write_json
from batched import BatchJournal
from actor import Worker
from quality import score
from review import Reviewer
import data
NAME='deep-qwen-100k-v1';LIMIT=100000
ALLOCATION={'calibration':16,'screen':71680,'fine':7616,'discovery':11648,'validation':640,'locked_test':288,'long':144,
    'random_controls':192,'guards':48,'replication':48,'distribution_controls':7680}

def rank(c):
    h=c['hypothesis'];strong=h['extremity']>=3 and not h['length_only']
    novelty={'new_mode':3,'related_mode':2,'unclear':1,'previous_mode':0}[h['novelty']]
    return (strong,novelty if strong else 0,h['extremity'],not h['length_only'],novelty,
        len(h['dramatic_change_ids']),len(h['coherent_change_ids']),-len(h['degeneration_ids']))
def select(values,n,cap=2):
    result=[];counts={}
    for c in sorted(values,key=rank,reverse=True):
        if counts.get(c['layer'],0)>=cap:continue
        result.append(c);counts[c['layer']]=counts.get(c['layer'],0)+1
        if len(result)==n:return result
    raise RuntimeError('Not enough distinct layers/candidates')

def historical_context():
    pool_paths=[ROOT/'campaigns/wide-qwen-100k-v1/neuron-pool.json',ROOT/'campaigns/extreme-qwen-pilot-v2/neuron-pool.json']
    modes_path=ROOT/'campaigns/wide-qwen-100k-v1/findings.json'
    manifests=sorted((ROOT/'campaigns').glob('*/manifest.json'));manifests=[p for p in manifests if p.parent.name!=NAME]
    inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pool_paths+[modes_path]+manifests}
    excluded={}
    for p in pool_paths:
        for c in json.loads(p.read_text(encoding='utf-8')):excluded[(c['layer'],c['neuron'])]={'layer':c['layer'],'neuron':c['neuron']}
    def strings(value):
        if isinstance(value,str):yield value
        elif isinstance(value,list):
            for v in value:yield from strings(v)
        elif isinstance(value,dict):
            for v in value.values():yield from strings(v)
    prompts=set()
    for p in manifests:prompts.update(strings(json.loads(p.read_text(encoding='utf-8')).get('datasets',{})))
    known=[]
    for r in json.loads(modes_path.read_text(encoding='utf-8')):
        h=r.get('test_analysis',r['validation_analysis'])['hypothesis']
        known.append({'prior_id':r['id'],'label':r['label'],'summary':h['summary'],'previous_state':r['state']})
    return {'inputs':inputs,'excluded_coordinates':[excluded[k] for k in sorted(excluded)],'prior_prompt_strings':sorted(prompts),'known_modes':known}

def main():
    out=ROOT/'campaigns'/NAME;out.mkdir(parents=True,exist_ok=True)
    with (out/'.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:run(out)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def run(out):
    read=lambda name:json.loads((out/name).read_text(encoding='utf-8'))
    info=read('model.json');sources=list((ROOT/'deep').glob('*.py'))+[ROOT/'wide/actor.py',ROOT/'wide/quality.py',ROOT/'extreme/worker.py',ROOT/'worker/reference.py',ROOT/'engine/batched.py']
    history=historical_context()
    if (out/'historical-context.json').exists():assert read('historical-context.json')==history,'Historical context changed'
    else:write_json(out/'historical-context.json',history)
    known=history['known_modes'];excluded={l:set() for l in data.LAYERS}
    for c in history['excluded_coordinates']:excluded[c['layer']].add(c['neuron'])
    current_prompts=[p for group in data.groups for p in group]
    assert not set(current_prompts)&set(history['prior_prompt_strings']),'Historical prompt collision'
    manifest={'campaign_id':NAME,'model':info['repository'],'revision':info['revision'],'seed':2026110402,'budget':LIMIT,
        'layers':data.LAYERS,'settings':data.SETTINGS,'broad_settings':data.BROAD,'pool_per_layer':512,'active_per_layer':128,'random_per_layer':384,
        'history_inputs':history['inputs'],'known_modes':known,
        'generated_candidates_per_layer':8,'shortlist_tracks':{'moderate_js':3,'extreme_js':3,'random':2},
        'dtype':'bfloat16','attention':'sdpa','logits_to_keep':1,'thinking':False,'decode':'greedy',
        'datasets':{k:getattr(data,k) for k in ['CALIBRATION','SCREEN','FINE','DISCOVERY','VALIDATION','TEST','LONG','GUARDS','REPLICATION']},
        'batches':{'distribution':128,'generation':32,'codex_workers':2,'codex_pending':4,'codex_requests':40},
        'tokens':{'discovery':80,'validation':128,'test':192,'long':256,'controls':192,'guards':96,'replication':160},
        'allocation':ALLOCATION,
        'operator':'One pre-down MLP coordinate clamped to zero or a signed multiple of its calibration maximum. Broad doses ±4/12; fine grid ±0.5/1/2/3/4/6/8/12; generation uses the nearest six magnitudes around the largest fine-proxy shift; validation refines chosen signed magnitude by ±25%. BF16-rounded targets at all prompt/decode positions. Parameters unchanged.',
        'selection':'Exclude all previously pooled Qwen coordinates. Per layer: top 3 off/±4 JS, top 3 distinct ±12 JS, 2 random; fine screen all 224. Review 13-setting generation ladders for all 224. Prefer new strong modes relative to the fixed prior library; select 16 then 6, maximum 2 per layer.',
        'gate':'Val/test extremity >=3, length_only false, matching coherent cases >=4/8 val, >=8/16 test, >=4/8 long and >=4/8 replication; <=2 test loop flags and <=2 selected test/long/replication degeneration flags.',
        'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    manifest=json.loads(json.dumps(manifest));assert sum(manifest['allocation'].values())==LIMIT
    if (out/'manifest.json').exists():assert read('manifest.json')==manifest,'Frozen protocol/source changed'
    else:write_json(out/'manifest.json',manifest)
    if (out/'status.json').exists() and read('status.json')['stage']=='complete':print('Completed measurements retained.');return
    identity=fingerprint(manifest)
    if not (out/'runtime.json').exists():write_json(out/'runtime.json',{'started_utc':datetime.now(timezone.utc).isoformat()})
    started=datetime.fromisoformat(read('runtime.json')['started_utc']);journal=BatchJournal(out/'jobs.sqlite',identity,LIMIT)
    reviewer=Reviewer(out/'codex',40)
    def status(stage,**extra):
        value={'campaign_id':NAME,'engine':'deep_single_neuron','stage':stage,'completed_jobs':journal.completed(),'admitted_jobs':journal.count,
            'budget':LIMIT,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':(datetime.now(timezone.utc)-started).total_seconds(),
            'screened_neurons':14336,'generated_candidates':224,**extra}
        write_json(out/'status.json',value);print(json.dumps(value),flush=True)
    torch.set_num_threads(4);torch.manual_seed(2026110402);torch.backends.cuda.matmul.allow_tf32=False
    status('loading_model')
    model=AutoModelForCausalLM.from_pretrained(info['snapshot'],local_files_only=True,trust_remote_code=False,
        torch_dtype=torch.bfloat16,attn_implementation='sdpa',use_safetensors=True).to('cuda').eval()
    tok=AutoTokenizer.from_pretrained(info['snapshot'],local_files_only=True,trust_remote_code=False);worker=Worker(model,tok)
    write_json(out/'environment.json',{'torch':torch.__version__,'transformers':transformers.__version__,'python':sys.version,
        'gpu':torch.cuda.get_device_name(),'model_parameters':sum(p.numel() for p in model.parameters()),
        'generation_eos_ids':sorted(worker.eos),'tokenizer_eos_id':tok.eos_token_id})
    samples=[]
    for p in data.CALIBRATION:
        samples.extend(journal.run([{'type':'calibration','prompt':p,'layers':data.LAYERS}],lambda cs:[worker.calibration_sample(c['prompt'],data.LAYERS) for c in cs]))
    cal={str(l):{'activation_abs_max':np.max([s[str(l)]['activation_abs_max'] for s in samples],axis=0).tolist(),
        'median_residual_l2':float(np.median([s[str(l)]['residual_l2'] for s in samples])),
        'residual_samples':[s[str(l)]['residual_l2'] for s in samples],
        'scope':'All-token activation extrema over 16 ordinary calibration prompts; not a global natural bound.'} for l in data.LAYERS}
    write_json(out/'calibration.json',cal);calhash=fingerprint(cal);worker.cal=cal
    check=worker.conformance('Briefly describe a tree.',7,17);write_json(out/'conformance.json',check);assert check['passed']
    rng=np.random.default_rng(2026110402);pool=[]
    for l in data.LAYERS:
        norms=model.model.layers[l].mlp.down_proj.weight.detach().float().norm(dim=0).cpu().numpy()
        active=[int(n) for n in np.argsort(-np.array(cal[str(l)]['activation_abs_max'])*norms,kind='stable') if n not in excluded[l]][:128]
        random=rng.choice([n for n in range(len(norms)) if n not in active and n not in excluded[l]],384,replace=False).tolist()
        pool += [{'id':f'L{l}-N{n}','layer':l,'neuron':n,'pool_origin':'active' if n in active else 'random'} for n in active+random]
    write_json(out/'neuron-pool.json',pool)
    def cfg(c,p,s,stage,limit=None,ri=None):
        condition,factor=data.setting(s)
        value={'type':'generation' if limit is not None else 'distribution','stage':stage,'prompt':p,'layer':c['layer'],'neuron':c['neuron'],
            'setting':s,'condition':condition,'factor':factor,'calibration_sha256':calhash}
        if limit is not None:value['max_tokens']=limit
        if ri is not None:value['random_index']=ri
        return value
    def perform(configs):
        failed=False
        try:values=worker.generate(configs) if configs[0]['type']=='generation' else worker.distributions(configs)
        except torch.cuda.OutOfMemoryError:failed=True
        if failed:
            gc.collect();torch.cuda.empty_cache()
            if len(configs)==1:raise RuntimeError('GPU out of memory at single-case batch')
            i=len(configs)//2;return perform(configs[:i])+perform(configs[i:])
        key=fingerprint(configs)
        for i,v in enumerate(values):v['batch_key']=key;v['batch_offset']=i
        return values
    def execute(configs):
        result={};groups={}
        for c in configs:groups.setdefault((c['prompt'],c['type'],c.get('max_tokens')),[]).append(c)
        for values in groups.values():
            size=32 if values[0]['type']=='generation' else 128
            for i in range(0,len(values),size):
                batch=values[i:i+size];outputs=journal.run(batch,perform)
                result.update({fingerprint(c):v for c,v in zip(batch,outputs)})
        return result
    summaries=[];generated=[]
    for l in data.LAYERS:
        components=[c for c in pool if c['layer']==l];configs=[cfg(c,p,s,'screen') for p in data.SCREEN for c in components for s in data.BROAD]
        values=execute(configs);layer=[]
        for c in components:
            means={}
            for s in data.BROAD:
                rows=[values[fingerprint(cfg(c,p,s,'screen'))] for p in data.SCREEN]
                means[s]={k:float(np.mean([v[k] for v in rows])) for k in ['js','kl','entropy']}
            layer.append({**c,'means':means})
        used=set();chosen=[]
        for track,settings in [('moderate_js',data.BROAD[:3]),('extreme_js',data.BROAD[3:])]:
            count=0
            for c in sorted(layer,key=lambda c:max(c['means'][s]['js'] for s in settings),reverse=True):
                if c['id'] in used:continue
                chosen.append({**c,'shortlist_track':track});used.add(c['id']);count+=1
                if count==3:break
        rest=[c for c in layer if c['id'] not in used];indices=np.random.default_rng(20261104200+l).choice(len(rest),2,replace=False)
        chosen += [{**rest[int(i)],'shortlist_track':'random'} for i in indices]
        summaries+=layer;generated+=chosen;write_json(out/f'screen-L{l:02}.json',layer);status('screen',layers_completed=l+1,total_layers=28)
    write_json(out/'screen-summary.json',summaries);write_json(out/'broad-shortlist.json',generated);assert journal.count==71696
    for l in data.LAYERS:
        cs=[c for c in generated if c['layer']==l];configs=[cfg(c,p,s,'fine') for p in data.FINE for c in cs for s in data.SETTINGS]
        values=execute(configs)
        for c in cs:
            c['fine_means']={s:{k:float(np.mean([values[fingerprint(cfg(c,p,s,'fine'))][k] for p in data.FINE])) for k in ['js','kl','entropy']} for s in data.SETTINGS}
            c['generation_settings']=data.generation_settings(c['fine_means'])
        status('fine',layers_completed=l+1,total_layers=28)
    write_json(out/'generated-pool.json',generated);assert journal.count==79312
    def generate(components,prompts,stage,limit,settings='all',random_controls=False):
        result={c['id']:[] for c in components}
        for i,p in enumerate(prompts):
            configs=[];owners=[]
            for c in components:
                choices=c['generation_settings'] if settings=='all' else data.validation_settings(c['hypothesis']['best_condition']) if settings=='validation' else data.trio(c['hypothesis']['best_condition']) if settings=='trio' else [c['hypothesis']['best_condition']]
                for s in choices:
                    for ri in (range(4) if random_controls else [None]):configs.append(cfg(c,p,s,stage,limit,ri));owners.append(c['id'])
            values=execute(configs)
            for owner,c in zip(owners,configs):
                v=values[fingerprint(c)];result[owner].append({'id':fingerprint({'identity':identity,'config':c}),'prompt':p,'condition':c['setting'],
                    'stage':stage,'random_index':c.get('random_index'),'baseline':v['batch_baseline'],'steered':v,
                    'metrics':{'baseline':score(v['batch_baseline']['text']),'steered':score(v['text'])}})
            status(stage,prompts_completed=i+1,total_prompts=len(prompts))
        return result
    def bundle(components,pairs,phase,namespace):
        items=[]
        for c in components:
            rows=pairs[c['id']]
            item={'component_id':c['id'],'layer':c['layer'],'neuron':c['neuron'],'settings':list(dict.fromkeys(p['condition'] for p in rows)),
                'pairs':[{'id':p['id'],'prompt':p['prompt'],'condition':p['condition'],'stage':p['stage'],
                    'kind':'random_direction' if p['random_index'] is not None else 'neuron','random_index':p['random_index'],
                    'baseline':p['baseline']['text'],'steered':p['steered']['text'],'termination':p['steered']['termination'],
                    'diagnostics':{m:{k:v for k,v in metrics.items() if k!='scope'} for m,metrics in p['metrics'].items()},
                    'intervention':p['steered']['intervention']} for p in rows]}
            if phase=='locked_test':
                item['frozen_hypothesis']={k:copy.deepcopy(c['hypothesis'][k]) for k in ['label','summary','best_condition','extremity','length_only','novelty','related_prior_ids','alternative_explanations']}
                item['prior_context_notice']='This is the PRIOR VALIDATION hypothesis. Its v-prefixed references are not current t-prefixed test evidence.'
            items.append(item)
        return {'phase':phase,'namespace':namespace,'known_modes':known,'model':manifest['model'],'revision':info['revision'],'operator':manifest['operator'],
            'scope':'Full paired text and termination supplied for all generated cases in this bundle; token IDs retained in raw artifacts. Normal prompts only. Proxy scores are not behavioral evidence.',
            'items':items}
    def interpret(payload):
        value=reviewer.review(payload);found={v['component_id']:v for v in value['analysis']['items']}
        return {c['component_id']:{'hypothesis':found[c['component_id']],'review_input_sha256':value['input_sha256']} for c in payload['items']}
    discovery={};da={};pending={}
    with ThreadPoolExecutor(max_workers=2) as executor:
        for l in data.LAYERS:
            cs=[c for c in generated if c['layer']==l];pairs=generate(cs,data.DISCOVERY,'discovery',80);discovery.update(pairs)
            future=executor.submit(interpret,bundle(cs,pairs,'discovery',f'd{l:02}'));pending[future]=l
            while len(pending)>=4:
                done,_=wait(pending,return_when=FIRST_COMPLETED)
                for f in done:
                    layer=pending.pop(f);answer=f.result();da.update(answer);write_json(out/f'discovery-analysis-L{layer:02}.json',answer)
                status('discovery_review',reviewed_neurons=len(da),generated_layers=l+1)
        for f,layer in list(pending.items()):
            answer=f.result();da.update(answer);write_json(out/f'discovery-analysis-L{layer:02}.json',answer);status('discovery_review',reviewed_neurons=len(da),generated_layers=28)
        ranked=[{**c,**da[c['id']]} for c in generated];write_json(out/'discovery-summary.json',ranked)
        selected=select(ranked,16);write_json(out/'validation-candidates.json',selected)
        vp=generate(selected,data.VALIDATION,'validation',128,'validation');va={}
        futures=[executor.submit(interpret,bundle(selected[i:i+8],vp,'validation',f'v{i//8:02}')) for i in range(0,16,8)]
        for f in futures:va.update(f.result())
        selected=[{**c,**va[c['id']]} for c in selected];write_json(out/'validation-summary.json',selected)
        finalists=select(selected,6);write_json(out/'frozen-candidates.json',finalists)
        records=[]
        for c in selected:
            records.append({**c,'component_id':c['id'],'id':NAME+'-'+c['id'],'campaign_id':NAME,'measurement_type':'open_ended_neuron',
                'model':'Qwen3-1.7B','revision':info['revision'],'synthetic':False,'manifest_sha256':identity,'calibration_sha256':calhash,
                'label':c['hypothesis']['label'] or 'Unlabelled neuron effect · '+c['id'],'summary':c['hypothesis']['summary'],
                'category':c['hypothesis']['category'],'state':'Validation observation','effect':c['hypothesis']['extremity'],'n':8,
                'screen_pairs':discovery[c['id']],'validation_pairs':vp[c['id']],'discovery_analysis':da[c['id']],
                'validation_analysis':va[c['id']],'artifact_url':f'evidence/{NAME}/{c["id"]}.json'})
        write_json(out/'findings.json',records)
        tp=generate(finalists,data.TEST,'locked_test',192,'trio');lp=generate(finalists,data.LONG,'long',256,'trio')
        cp=generate(finalists,data.TEST[:8],'random_controls',192,'best',True)
        gp=generate(finalists,[p for p,a in data.GUARDS],'guards',96,'best')
        rp=generate(finalists,data.REPLICATION,'replication',160,'best')
        combined={c['id']:tp[c['id']]+lp[c['id']]+cp[c['id']]+rp[c['id']] for c in finalists}
        futures=[executor.submit(interpret,bundle(finalists[i:i+3],combined,'locked_test',f't{i//3:02}')) for i in range(0,6,3)]
        status('distribution_controls')
        configs=[]
        for p in data.REPLICATION:
            for c in finalists:
                configs += [cfg(c,p,s,'distribution_controls') for s in data.SETTINGS]
                configs += [cfg(c,p,c['hypothesis']['best_condition'],'distribution_controls',ri=i) for i in range(143)]
        execute(configs);assert journal.count==LIMIT
        ta={}
        for f in futures:ta.update(f.result())
        for r in records:
            cid=r['component_id'];final=next((c for c in finalists if c['id']==cid),None)
            if final is None:continue
            h=ta[cid]['hypothesis'];v=r['hypothesis'];chosen=v['best_condition'];dramatic=set(h['dramatic_change_ids']);degen=set(h['degeneration_ids'])
            test=[p for p in tp[cid] if p['condition']==chosen];long=[p for p in lp[cid] if p['condition']==chosen];rep=rp[cid]
            vh=len(v['dramatic_change_ids']);th=sum(p['id'] in dramatic for p in test);lh=sum(p['id'] in dramatic for p in long);rh=sum(p['id'] in dramatic for p in rep)
            bad=degen&{p['id'] for p in test+long+rep};loops=sum(p['metrics']['steered']['repetition'] for p in test)
            passed=v['label'] is not None and h['label'] is not None and not v['length_only'] and not h['length_only'] and v['extremity']>=3 and h['extremity']>=3 and vh>=4 and th>=8 and lh>=4 and rh>=4 and loops<=2 and len(bad)<=2
            r.update({'test_pairs':tp[cid],'long_pairs':lp[cid],'control_pairs':cp[cid],'guard_pairs':gp[cid],'replication_pairs':rp[cid],
                'test_analysis':ta[cid],'n':16,'state':'Extreme mode observed' if passed else 'Tested observation',
                'mode_check':{'passed':passed,'condition':chosen,'novelty':v['novelty'],'validation_hits':vh,'test_hits':th,'long_hits':lh,'replication_hits':rh,
                    'test_repetition_flags':loops,'codex_degeneration_ids':sorted(bad),
                    'scope':'Greedy, single-checkpoint, open-ended Codex-assessed held-out mode change; no global reliability or unique neuron-function claim.'}})
        write_json(out/'findings.json',records)
    status('archiving');artifacts=out/'artifacts';artifacts.mkdir(exist_ok=True);ledger=[];i=0
    cursor=journal.db.execute('SELECT id,config,result FROM jobs ORDER BY id')
    while rows:=cursor.fetchmany(2000):
        path=artifacts/f'jobs-{i:03d}.jsonl.gz'
        with gzip.open(path,'wt',encoding='utf-8') as stream:
            for key,c,v in rows:stream.write(json.dumps({'job_id':key,'config':json.loads(c),'result':json.loads(v)},ensure_ascii=False)+'\n')
        ledger.append({'path':str(path.relative_to(out)),'jobs':len(rows),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()});i+=1
    write_json(out/'artifact-ledger.json',ledger)
    status('complete',catalogued=len(records),tested=6,extreme_modes=sum(r.get('mode_check',{}).get('passed',False) for r in records),
        novel_extreme_modes=sum(r.get('mode_check',{}).get('passed',False) and r['hypothesis']['novelty']=='new_mode' for r in records),
        peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),codex_requests=len(list((out/'codex').glob('*.attempt-*.request.json'))))
    journal.db.close()

if __name__=='__main__':main()
