"""Bounded open-ended single-neuron off/on discovery on normal prompts."""
from datetime import datetime,timezone
from pathlib import Path
import gzip,hashlib,json,msvcrt,sys
import numpy as np
import torch,transformers
from transformers import AutoModelForCausalLM,AutoTokenizer
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'worker'),str(ROOT/'engine')]
from reference import fingerprint,write_json
from batched import BatchJournal
from worker import Worker
from quality import score
from analyze import review
import data
NAME='extreme-qwen-pilot-v2';LAYERS=[7,13,19,25];CONDITIONS=['off','positive','negative'];LIMIT=2500

def main():
    out=ROOT/'campaigns'/NAME;out.mkdir(parents=True,exist_ok=True)
    with (out/'.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:run(out)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def run(out):
    read=lambda name:json.loads((out/name).read_text(encoding='utf-8'))
    info=read('model.json');sources=list((ROOT/'extreme').glob('*.py'))+[ROOT/'worker/reference.py',ROOT/'engine/batched.py']
    manifest={'campaign_id':NAME,'model':info['repository'],'revision':info['revision'],'layers':LAYERS,'conditions':CONDITIONS,
        'dtype':'bfloat16','attention':'sdpa','thinking':False,'decode':'greedy','seed':20261104,'budget':LIMIT,
        'datasets':{k:getattr(data,k) for k in ['SCREEN','VALIDATION','TEST','LONG','GUARDS','CALIBRATION']},
        'operator':'A single MLP pre-down coordinate is set to zero, +calibration_abs_max, or -calibration_abs_max at ALL unpadded prompt positions and every decode input.',
        'pool':'Per layer: 16 largest calibration max-activation times down-column norm, plus 16 uniformly sampled other coordinates.',
        'selection':'Open-ended Codex review of ALL 128 neurons, 3 conditions x 4 normal prompts; rank six for 8-context validation, then three for locked test.',
        'analysis':'Eight discovery batches of 16 neurons; one six-neuron validation review; one three-neuron test/long/control review. Twelve-request cap.',
        'limits':{'screen_tokens':96,'validation_tokens':128,'test_tokens':160,'long_tokens':256,'max_batch_interventions':8},
        'gate':'Codex extremity >=3; coherent matching shift on >=4 validation, >=8 locked-test, >=4 longer prompts; <=2 locked-test repetition flags and <=2 Codex degeneration IDs. Scoped exploratory result, not general stability.',
        'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    if (out/'manifest.json').exists():assert read('manifest.json')==manifest,'Frozen campaign source or protocol changed'
    else:write_json(out/'manifest.json',manifest)
    identity=fingerprint(manifest)
    if not (out/'runtime.json').exists():write_json(out/'runtime.json',{'started_utc':datetime.now(timezone.utc).isoformat()})
    started=datetime.fromisoformat(read('runtime.json')['started_utc'])
    journal=BatchJournal(out/'jobs.sqlite',identity,LIMIT)
    def status(stage,**extra):
        value={'campaign_id':NAME,'stage':stage,'completed_jobs':journal.completed(),'admitted_jobs':journal.count,'budget':LIMIT,
            'timestamp_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':(datetime.now(timezone.utc)-started).total_seconds(),**extra}
        write_json(out/'status.json',value);print(json.dumps(value),flush=True)
    torch.set_num_threads(4);torch.manual_seed(20261104);torch.backends.cuda.matmul.allow_tf32=False
    status('loading_model')
    model=AutoModelForCausalLM.from_pretrained(info['snapshot'],local_files_only=True,trust_remote_code=False,torch_dtype=torch.bfloat16,
        attn_implementation='sdpa',use_safetensors=True).to('cuda').eval()
    tok=AutoTokenizer.from_pretrained(info['snapshot'],local_files_only=True,trust_remote_code=False);worker=Worker(model,tok)
    write_json(out/'environment.json',{'torch':torch.__version__,'transformers':transformers.__version__,'python':sys.version,
        'model_parameters':sum(p.numel() for p in model.parameters()),'gpu':torch.cuda.get_device_name(),
        'model_allocated_bytes':torch.cuda.memory_allocated(),'tokenizer_eos_id':tok.eos_token_id,'generation_eos_ids':sorted(worker.eos)})
    status('calibration');samples=[]
    for prompt in data.CALIBRATION:
        c={'type':'calibration','prompt':prompt,'layers':LAYERS}
        samples.extend(journal.run([c],lambda configs:[worker.calibration_sample(v['prompt'],LAYERS) for v in configs]))
    cal={str(l):{'activation_abs_max':np.max([s[str(l)]['activation_abs_max'] for s in samples],axis=0).tolist(),
        'median_residual_l2':float(np.median([s[str(l)]['residual_l2'] for s in samples])),
        'residual_samples':[s[str(l)]['residual_l2'] for s in samples],
        'scope':'Activation extrema over every token of eight normal calibration prompts; not a global natural bound.'} for l in LAYERS}
    write_json(out/'calibration.json',cal);worker.cal=cal;calhash=fingerprint(cal)
    check=worker.conformance(data.CALIBRATION[0],LAYERS[0],17);write_json(out/'conformance.json',check)
    assert check['passed'],'Worker conformance failed'
    pool=[];rng=np.random.default_rng(20261104)
    for l in LAYERS:
        norms=model.model.layers[l].mlp.down_proj.weight.detach().float().norm(dim=0).cpu().numpy()
        ranked=np.argsort(-np.array(cal[str(l)]['activation_abs_max'])*norms)[:16].tolist()
        random=rng.choice([i for i in range(len(norms)) if i not in ranked],16,replace=False).tolist()
        pool.extend({'id':f'L{l}-N{n}','layer':l,'neuron':n,'selection_origin':'active' if n in ranked else 'random'} for n in ranked+random)
    write_json(out/'neuron-pool.json',pool)
    def config(c,prompt,condition,stage,limit,random_index=None):
        v={'type':'generation','stage':stage,'prompt':prompt,'layer':c['layer'],'neuron':c['neuron'],'condition':condition,
            'max_tokens':limit,'calibration_sha256':calhash}
        if random_index is not None:v['random_index']=random_index
        return v
    def action(configs):
        try:values=worker.generate(configs)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if len(configs)==1:raise
            split=len(configs)//2;return action(configs[:split])+action(configs[split:])
        for v in values:v['batch_key']=fingerprint(configs)
        return values
    def generate(components,prompts,stage,limit,conditions=CONDITIONS,random_controls=False):
        result={c['id']:[] for c in components}
        for pi,prompt in enumerate(prompts):
            for l in sorted({c['layer'] for c in components}):
                settings=[]
                for c in components:
                    if c['layer']!=l:continue
                    for condition in ([c['hypothesis']['best_condition']] if random_controls else conditions):
                        for ri in (range(4) if random_controls else [None]):settings.append((c,config(c,prompt,condition,stage,limit,ri)))
                for i in range(0,len(settings),8):
                    batch=settings[i:i+8];values=journal.run([v for c,v in batch],action)
                    for (c,cfg),v in zip(batch,values):
                        result[c['id']].append({'id':fingerprint({'identity':identity,'config':cfg}),
                            'prompt':prompt,'condition':cfg['condition'],'random_index':cfg.get('random_index'),
                            'baseline':v['batch_baseline'],'steered':v,'metrics':{'baseline':score(v['batch_baseline']['text']),'steered':score(v['text'])}})
            status(stage,prompts_completed=pi+1,total_prompts=len(prompts))
        return result
    def interpret(components,pairs,phase):
        items=[]
        for c in components:
            item={'component_id':c['id'],'layer':c['layer'],'neuron':c['neuron'],
                'clamps':{'off':0.,'positive':cal[str(c['layer'])]['activation_abs_max'][c['neuron']],
                    'negative':-cal[str(c['layer'])]['activation_abs_max'][c['neuron']]},
                'pairs':[{'id':p['id'],'prompt':p['prompt'],'condition':p['condition'],'random_index':p.get('random_index'),
                    'baseline':p['baseline']['text'],'steered':p['steered']['text'],'termination':p['steered']['termination'],
                    'diagnostics':p['metrics'],'write':p['steered']['intervention']} for p in pairs[c['id']]]}
            if phase=='locked_test':item['frozen_hypothesis']=c['hypothesis']
            items.append(item)
        bundle={'phase':phase,'model':manifest['model'],'revision':info['revision'],'operator':manifest['operator'],
            'scope':'All prompts are normal, with no instruction to induce a target mode. Text and termination are complete; token IDs retained in raw artifacts but excluded from semantic input.',
            'items':items}
        status('codex_'+phase,components=[c['id'] for c in components])
        try:
            value=review(bundle,out/'codex');found={a['component_id']:a for a in value['analysis']['items']}
            return {c['id']:{'hypothesis':found[c['id']],'review_input_sha256':value['input_sha256']} for c in components}
        except Exception as exc:
            write_json(out/'analysis-errors'/f'{phase}-{fingerprint([c["id"] for c in components])}.json',{'error':str(exc)})
            return {c['id']:{'hypothesis':{'component_id':c['id'],'label':None,'summary':'Semantic review unavailable; no supported interpretation.',
                'category':'Other','best_condition':'off','extremity':0,'coherent_change_ids':[],'dramatic_change_ids':[],
                'degeneration_ids':[],'contradicting_ids':[],'alternative_explanations':[],'followup_proposals':[]},'analysis_error':str(exc)} for c in components}
    def rank(c):
        h=c['hypothesis'];return (h['extremity'],len(h['dramatic_change_ids']),len(h['coherent_change_ids']),-len(h['degeneration_ids']))
    status('screen',neurons=len(pool));screen=generate(pool,data.SCREEN,'screen',96);analyses={}
    for i in range(0,len(pool),16):analyses.update(interpret(pool[i:i+16],screen,'discovery'))
    ranked=[{**c,**analyses[c['id']]} for c in pool];write_json(out/'discovery-summary.json',ranked)
    selected=sorted(ranked,key=rank,reverse=True)[:6];write_json(out/'validation-candidates.json',selected)
    validation=generate(selected,data.VALIDATION,'validation',128);va=interpret(selected,validation,'validation')
    selected=[{**c,**va[c['id']]} for c in selected];write_json(out/'validation-summary.json',selected)
    finalists=sorted(selected,key=rank,reverse=True)[:3];write_json(out/'frozen-candidates.json',finalists)
    records=[]
    for c in selected:
        records.append({**c,'id':NAME+'-'+c['id'],'component_id':c['id'],'campaign_id':NAME,'measurement_type':'open_ended_neuron',
            'model':'Qwen3-1.7B','revision':info['revision'],'synthetic':False,'manifest_sha256':identity,'calibration_sha256':calhash,
            'label':c['hypothesis']['label'] or f'Unlabelled neuron effect · {c["id"]}','summary':c['hypothesis']['summary'],
            'category':c['hypothesis']['category'],'state':'Validated candidate','effect':c['hypothesis']['extremity'],'n':8,
            'screen_pairs':screen[c['id']],'validation_pairs':validation[c['id']],
            'discovery_analysis':analyses[c['id']],'validation_analysis':va[c['id']],
            'artifact_url':f'evidence/{NAME}/{c["id"]}.json'})
    def export():
        write_json(out/'findings.json',records)
        for r in records:write_json(ROOT/'dist'/r['artifact_url'],r)
    export()
    test=generate(finalists,data.TEST,'locked_test',160);long=generate(finalists,data.LONG,'long',256)
    controls=generate(finalists,data.TEST[:8],'random_controls',128,random_controls=True)
    guards=generate(finalists,[p for p,a in data.GUARDS],'guards',96)
    combined={c['id']:test[c['id']]+long[c['id']]+controls[c['id']] for c in finalists};ta=interpret(finalists,combined,'locked_test')
    for r in records:
        cid=r['component_id'];final=next((c for c in finalists if c['id']==cid),None)
        if not final:r['state']='Validation observation';continue
        h=ta[cid]['hypothesis'];chosen=final['hypothesis']['best_condition'];tp=[p for p in test[cid] if p['condition']==chosen]
        lp=[p for p in long[cid] if p['condition']==chosen];dramatic=set(h['dramatic_change_ids']);degenerate=set(h['degeneration_ids'])
        test_hits=sum(p['id'] in dramatic for p in tp);long_hits=sum(p['id'] in dramatic for p in lp)
        val_hits=len(final['hypothesis']['dramatic_change_ids']);repetitions=sum(p['metrics']['steered']['repetition'] for p in tp)
        selected_ids={p['id'] for p in tp+lp};selected_degeneration=degenerate & selected_ids
        passed=final['hypothesis']['label'] is not None and h['label'] is not None and final['hypothesis']['extremity']>=3 and h['extremity']>=3 and val_hits>=4 and test_hits>=8 and long_hits>=4 and repetitions<=2 and len(selected_degeneration)<=2
        r.update({'test_pairs':test[cid],'long_pairs':long[cid],'control_pairs':controls[cid],'guard_pairs':guards[cid],
            'test_analysis':ta[cid],'n':16,'state':'Extreme mode observed' if passed else 'Tested observation',
            'mode_check':{'passed':passed,'condition':chosen,'validation_hits':val_hits,'test_hits':test_hits,'long_hits':long_hits,
                'test_repetition_flags':repetitions,'codex_degeneration_ids':sorted(selected_degeneration),
                'scope':'Open-ended Codex-assessed change in one greedy pilot; no general reliability, unique neuron function or model intent claim.'}})
        export()
    status('archiving');ledger=[];artifacts=out/'artifacts';artifacts.mkdir(exist_ok=True)
    cursor=journal.db.execute('SELECT id,config,result FROM jobs ORDER BY id');i=0
    while rows:=cursor.fetchmany(500):
        path=artifacts/f'jobs-{i:03d}.jsonl.gz'
        with gzip.open(path,'wt',encoding='utf-8') as stream:
            for key,c,v in rows:stream.write(json.dumps({'job_id':key,'config':json.loads(c),'result':json.loads(v)},ensure_ascii=False)+'\n')
        ledger.append({'path':str(path.relative_to(out)),'jobs':len(rows),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()});i+=1
    write_json(out/'artifact-ledger.json',ledger)
    status('complete',catalogued=len(records),tested=len(finalists),extreme_modes=sum(r.get('mode_check',{}).get('passed',False) for r in records),
        peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),codex_requests=len(list((out/'codex').glob('*.request.json'))))
    export();journal.db.close()

if __name__=='__main__':main()
