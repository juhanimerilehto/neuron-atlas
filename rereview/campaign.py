"""Retrospective, novelty-free interpretation of every saved exhaustive candidate."""
import collections,copy,ctypes,hashlib,json,msvcrt,os,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from reviewer import Reviewer,INSTRUCTION,schema,compact,expand,validate,fingerprint,save,FIELDS

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'campaigns/extremity-rereview-v1'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SCOPE='Retrospective interpretation of existing paired generations. No new model inference or new locked tests. Novelty excluded from ranking. Change and coherence are independent ordinal judgments.'

def prepare():
    OUT.mkdir(exist_ok=True);tasks=[];sources={};counts=collections.Counter()
    for i in range(1,11):
        base=ROOT/f'campaigns/exhaust-qwen-v1-s{i:02}';a=read(base/'audit.json');aa=read(base/'archive-audit.json')
        assert a['passed'] and aa['passed']
        for filename in ['manifest.json','audit.json','archive-audit.json','findings.json']:
            p=base/filename;sources[p.relative_to(ROOT).as_posix()]=sha(p)
        groups={
            'validation':{c['review_input_sha256'] for c in read(base/'validation-summary.json')},
            'discovery':{c['review_input_sha256'] for c in read(base/'discovery-summary.json')},
            'locked_test':{r['test_analysis']['review_input_sha256'] for r in read(base/'findings.json') if 'test_analysis' in r}}
        for phase,keys in groups.items():
            for key in sorted(keys):
                path=base/'codex'/f'{key}.bundle.json';b=read(path);assert b['phase']==phase
                relative=path.relative_to(ROOT).as_posix();sources[relative]=sha(path)
                tasks.append({'id':f's{i:02}-{b["namespace"]}','shard':i,'phase':phase,'source':relative,'sha256':sha(path),
                    'component_ids':[item['component_id'] for item in b['items']]})
                counts[phase]+=len(b['items'])
    assert counts=={'discovery':2240,'validation':160,'locked_test':60}
    def priority(t):return 0 if t['phase']=='validation' and ((t['shard']==4 and 'L7-N3649' in t['component_ids']) or (t['shard']==3 and 'L10-N3451' in t['component_ids'])) else 1
    tasks.sort(key=lambda t:({'validation':0,'discovery':1,'locked_test':2}[t['phase']],priority(t),t['shard'],t['id']))
    workers={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'rereview').glob('*.py')}
    manifest={'campaign_id':OUT.name,'scope':SCOPE,'source_campaign':'exhaust-qwen-v1','primary_model':'gpt-6.1-terra',
        'confirmation_model':'gpt-6.1-sol','reasoning_effort':'medium','resolved_upstream_checkpoints':None,
        'primary_request_ceiling':400,'confirmation_request_ceiling':26,'parallel_requests':2,
        'tasks':tasks,'sources':sources,'worker_sources':workers,'original_worker_sources':read(ROOT/'campaigns/exhaust-qwen-v1/manifest.json')['sources'],'schema_sha256':fingerprint(schema()),
        'instruction_sha256':hashlib.sha256(INSTRUCTION.encode()).hexdigest(),'candidate_counts':dict(counts),
        'ranking':'Change strength, matching fraction, prompt count, coherence. No novelty, topic or layer preference. Readable (coherence >=3) and mixed/collapsed queues are separate; neither is discarded.',
        'confirmation_selection':'User-nominated L7-N3649 n8 and L10-N3451 p15, then top 24 readable and top 24 mixed/collapsed settings, deduplicated by coordinate and dose; up to 50 nominations in batches of four.',
        'publication':'Original 236 catalogue records and original judgments are unchanged. New retrospective sidecar, raw reviews, provenance and proposed fresh tests are separate.'}
    path=OUT/'manifest.json'
    if path.exists():assert read(path)==manifest,'Frozen re-review protocol changed'
    else:save(path,manifest)
    return manifest

def bundle(task):
    assert sha(ROOT/task['source'])==task['sha256'];original=read(ROOT/task['source'])
    b={k:original[k] for k in ['model','revision','operator']}
    b.update(phase=task['phase'],namespace='rv_'+task['id'].replace('-','_'),scope=SCOPE,items=[])
    for source in original['items']:
        item={k:copy.deepcopy(source[k]) for k in ['component_id','layer','neuron','settings']}
        item['pairs']=[{k:copy.deepcopy(p[k]) for k in ['id','prompt','condition','stage','kind','random_index','baseline','steered','termination','diagnostics']} for p in source['pairs']]
        b['items'].append(item)
    return b

def row_rank(row):return(row['change_strength'],row['hits']/max(row['n'],1),row['n'],row['coherence'])

def collect(manifest):
    components={};rows=[]
    for task in manifest['tasks']:
        ref=OUT/'task-results'/f'{task["id"]}.json'
        if not ref.exists():continue
        result=read(OUT/'codex'/f'{read(ref)["review_input_sha256"]}.analysis.json');b=bundle(task)
        for source,analysis in zip(b['items'],result['analysis']['items']):
            # Structured results are permitted to reorder components.
            analysis=next(x for x in result['analysis']['items'] if x['component_id']==source['component_id'])
            cid=f'exhaust-qwen-v1-s{task["shard"]:02}-{source["component_id"]}'
            c=components.setdefault(cid,{'id':cid,'component_id':source['component_id'],'source_campaign':f'exhaust-qwen-v1-s{task["shard"]:02}',
                'layer':source['layer'],'neuron':source['neuron'],'model':b['model'],'revision':b['revision'],'pairs':{},'assessments':[],
                'scope':SCOPE,'synthetic':False})
            for p in source['pairs']:
                if p['id'] in c['pairs']:assert c['pairs'][p['id']]==p
                c['pairs'][p['id']]=p
            c['assessments'].append({'phase':task['phase'],'review_input_sha256':result['input_sha256'],**analysis})
            for e in analysis['condition_effects']:
                pairs=[p for p in source['pairs'] if p['kind']=='neuron' and p['condition']==e['condition']]
                row={'id':cid,'component_id':source['component_id'],'layer':source['layer'],'neuron':source['neuron'],
                    'phase':task['phase'],'condition':e['condition'],'label':e['label'],'change_strength':e['change_strength'],'coherence':e['coherence'],
                    'hits':len(e['matching_ids']),'n':len(pairs),'note':e['note'],'repetition_flags':len(e['repetition_ids']),
                    'collapse_flags':len(e['collapse_ids']),'task_loss_flags':len(e['task_loss_ids']),
                    'evidence_state':('Previously collected held-out evidence; retrospective review' if task['phase']=='locked_test' else 'Validation only; fresh held-out tests needed' if task['phase']=='validation' else 'Discovery only; validation needed'),
                    'detail_ref':f'evidence/{OUT.name}/components/{cid}.json'}
                rows.append(row)
    for row in rows:
        c=components[row['id']]
        phases=sorted({a['phase'] for a in c['assessments'] if any(e['condition']==row['condition'] for e in a['condition_effects'])})
        row['available_evidence_phases']=phases
        row['other_phase_scores']=[{'phase':a['phase'],'change_strength':e['change_strength'],'coherence':e['coherence'],'hits':len(e['matching_ids'])}
            for a in c['assessments'] for e in a['condition_effects'] if e['condition']==row['condition'] and a['phase']!=row['phase']]
        row['evidence_state']='Previously collected held-out evidence; retrospective review' if 'locked_test' in phases else 'Validation available; fresh held-out tests needed' if 'validation' in phases else 'Discovery only; validation needed'
    return components,rows

def best_entries(rows,quality=None):
    best={}
    for row in rows:
        if quality=='readable' and row['coherence']<3:continue
        if quality=='mixed' and row['coherence']>=3:continue
        if row['id'] not in best or row_rank(row)>row_rank(best[row['id']]):best[row['id']]=row
    return sorted(best.values(),key=row_rank,reverse=True)

def nominations(components,rows):
    chosen=[];seen=set()
    def add(row,reason):
        key=(row['id'],row['condition'])
        if key not in seen:chosen.append({**row,'selection_reason':reason});seen.add(key)
    for cid,condition in [('exhaust-qwen-v1-s04-L7-N3649','n8'),('exhaust-qwen-v1-s03-L10-N3451','p15')]:
        candidates=[r for r in rows if r['id']==cid and r['condition']==condition];assert candidates
        add(max(candidates,key=lambda r:r['n']),'Explicit user-interest nomination; independent of rank')
    for quality in ['readable','mixed']:
        count=0
        for row in best_entries(rows,quality):
            if row['change_strength']<2:continue
            if (row['id'],row['condition']) in seen:continue
            add(row,f'Top {quality} queue; novelty excluded');count+=1
            if count==24:break
    return chosen

def confirmation_bundle(nominees,components,index):
    result={'phase':'confirmation','namespace':f'rc_{index:02}','scope':SCOPE,'model':'Qwen/Qwen3-1.7B','items':[]}
    for row in nominees:
        c=components[row['id']];pairs=[p for p in c['pairs'].values() if p['condition']==row['condition']]
        assert pairs and any(p['kind']=='neuron' for p in pairs)
        result['items'].append({'component_id':row['id']+'__'+row['condition'],'layer':c['layer'],'neuron':c['neuron'],
            'settings':[row['condition']],'proposed_hypothesis':{'label':row['label'] or 'Reported qualitative change','description':row['note']},'pairs':pairs})
    return result

def audit_review(directory,key,b):
    value=read(directory/f'{key}.analysis.json');wire,mapping=compact(b)
    expected=fingerprint({'bundle':b,'instruction':INSTRUCTION,'schema':schema(),'model':value['requested_model'],'effort':'medium'})
    assert expected==key and read(directory/f'{key}.bundle.json')==b
    assert read(directory/f'{key}.wire.json')==wire and read(directory/f'{key}.reference-map.json')==mapping
    assert read(directory/f'{key}.schema.json')==schema() and value['wire_sha256']==fingerprint(wire)
    stem=directory/f'{key}.attempt-{value["winning_attempt"]}'
    raw=read(str(stem)+'.response.json');validate(raw,wire);assert expand(raw,mapping)==value['analysis'];validate(value['analysis'],b)
    request=read(str(stem)+'.request.json');command=request['command']
    assert command[command.index('--model')+1]==value['requested_model'] and 'model_reasoning_effort="medium"' in command
    assert request['prompt_sha256']==hashlib.sha256((INSTRUCTION+'\nEVIDENCE:\n'+json.dumps(wire,ensure_ascii=False)).encode()).hexdigest()
    assert read(str(stem)+'.execution.json')['returncode']==0
    return value

def run(manifest):
    primary=Reviewer(OUT/'codex');confirmation=Reviewer(OUT/'codex-confirm','gpt-6.1-sol',26)
    started=time.monotonic()
    def verify():
        assert all(sha(ROOT/p)==v for p,v in manifest['worker_sources'].items())
        assert all(sha(ROOT/p)==v for p,v in manifest['original_worker_sources'].items())
    def status(stage,**extra):
        value={'campaign_id':OUT.name,'stage':stage,'completed_primary':len(list((OUT/'task-results').glob('*.json'))),
            'primary_total':320,'accepted_terra_reviews':len(list((OUT/'codex').glob('*.analysis.json'))),
            'accepted_sol_reviews':len(list((OUT/'codex-confirm').glob('*.analysis.json'))),'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'elapsed_this_process_seconds':time.monotonic()-started,'scope':SCOPE,**extra}
        save(OUT/'status.json',value);print(json.dumps(value),flush=True)
    def interpret(task):
        verify();b=bundle(task);v=primary.review(b)
        save(OUT/'task-results'/f'{task["id"]}.json',{'task_id':task['id'],'review_input_sha256':v['input_sha256'],'original_bundle_sha256':task['sha256']})
    status('starting')
    try:
        for phase in ['validation','discovery','locked_test']:
            tasks=[t for t in manifest['tasks'] if t['phase']==phase and not (OUT/'task-results'/f'{t["id"]}.json').exists()]
            status('reviewing_'+phase)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures={pool.submit(interpret,t):t for t in tasks}
                try:
                    for future in as_completed(futures):future.result();status('reviewing_'+phase,last_completed=futures[future]['id'])
                except BaseException:
                    for future in futures:future.cancel()
                    raise
            if phase=='validation':
                _,rows=collect(manifest);save(OUT/'validation-preview.json',{'scope':SCOPE,'entries':best_entries(rows),'readable':best_entries(rows,'readable'),'mixed':best_entries(rows,'mixed')})
        status('nominating_independent_checks');components,rows=collect(manifest);assert len(components)==2240
        nominated=nominations(components,rows)
        path=OUT/'confirmation-plan.json'
        if path.exists():assert read(path)==nominated
        else:save(path,nominated)
        confirmations={}
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks={pool.submit(confirmation.review,confirmation_bundle(nominated[i:i+4],components,i//4)):i for i in range(0,len(nominated),4)}
            for future in as_completed(tasks):
                v=future.result();i=tasks[future];save(OUT/'confirmation-results'/f'c{i//4:02}.json',{'review_input_sha256':v['input_sha256']})
                status('independent_confirmation',nominations=len(nominated))
        status('auditing')
        all_ids=set();pair_count=0;condition_count=0
        for task in manifest['tasks']:
            ref=read(OUT/'task-results'/f'{task["id"]}.json');b=bundle(task)
            value=audit_review(OUT/'codex',ref['review_input_sha256'],b);assert value['requested_model']=='gpt-6.1-terra'
            for item in b['items']:
                for pair in item['pairs']:assert pair['id'] not in all_ids;all_ids.add(pair['id']);pair_count+=1
            condition_count+=sum(len(item['condition_effects']) for item in value['analysis']['items'])
        assert pair_count==129600
        for i in range(0,len(nominated),4):
            key=read(OUT/'confirmation-results'/f'c{i//4:02}.json')['review_input_sha256']
            value=audit_review(OUT/'codex-confirm',key,confirmation_bundle(nominated[i:i+4],components,i//4));assert value['requested_model']=='gpt-6.1-sol'
            for row,item in zip(nominated[i:i+4],confirmation_bundle(nominated[i:i+4],components,i//4)['items']):
                a=next(v for v in value['analysis']['items'] if v['component_id']==item['component_id'])
                confirmations[row['id']+'__'+row['condition']]={'review_input_sha256':key,'assessment':a}
        assert all(sha(ROOT/p)==v for p,v in manifest['sources'].items());verify()
        audit={'passed':True,'primary_reviews':320,'confirmed_nominations':len(nominated),'generation_pairs_rechecked':pair_count,
            'conditions_assessed':condition_count,'components':len(components),'manifest_sha256':fingerprint(manifest),
            'scope':'Checks original source hashes, exact raw pair preservation, every supplied condition and model reference, schema, explicit model commands, ranking and raw-response linkage. Semantic scores remain fallible; this is not fresh model replication.'}
        save(OUT/'audit.json',audit)
        evidence=ROOT/'site-source/evidence'/OUT.name;evidence.mkdir(exist_ok=True)
        for cid,c in components.items():
            c['confirmations']={k.split('__',1)[1]:v for k,v in confirmations.items() if k.startswith(cid+'__')}
            c['pairs']=list(c['pairs'].values());save(evidence/'components'/f'{cid}.json',c)
        for row in rows:row['confirmation']=confirmations.get(row['id']+'__'+row['condition'])
        index={'schema_version':'extremity-rereview.v1','synthetic':False,'scope':SCOPE,'status':'complete','components':2240,
            'entries':best_entries(rows),'readable':best_entries(rows,'readable'),'mixed':best_entries(rows,'mixed'),
            'all_condition_count':len(rows),'nominations':nominated,'audit_ref':f'evidence/{OUT.name}/audit.json',
            'report_ref':f'evidence/{OUT.name}/report.md','reviewers':['gpt-6.1-terra','gpt-6.1-sol']}
        save(evidence/'index.json',index)
        import shutil
        for name in ['manifest.json','audit.json','confirmation-plan.json']:shutil.copy2(OUT/name,evidence/name)
        for folder in ['codex','codex-confirm']:
            for file in (OUT/folder).glob('*.json'):
                target=evidence/folder/file.name;target.parent.mkdir(exist_ok=True);shutil.copy2(file,target)
        lines=['# Extremity-first retrospective re-review','',SCOPE,'',
            f'Fresh Terra interpretation of all 2,240 discovery candidates, 160 validation records and 60 previously tested finalists: {pair_count:,} paired generations and {condition_count:,} condition assessments. Sol independently assessed {len(nominated)} nominated coordinate/dose effects. Original judgments and the 236 catalogue records are preserved.','',
            'Every dose is assessed; behavioral change and coherence have separate scores. Novelty is excluded from ranking. Readable and mixed/collapsed changes have separate queues. Rankings are descriptive priorities, not statistical confidence or new stability passes. A previously untested candidate remains untested. Fresh held-out prompts are still needed before claims of replicated stability.','',
            '## Readable changes','', '| Coordinate | Setting | Phase | Change / coherence | Matches | Description |','| --- | --- | --- | --- | --- | --- |']
        for row in index['readable'][:30]:lines.append(f"| {row['component_id']} ({row['id'].split('-s')[1][:2]}) | {row['condition']} | {row['phase']} | {row['change_strength']}/4 · {row['coherence']}/4 | {row['hits']}/{row['n']} | {str(row['label']).replace('|','/')} |")
        lines+=['','## User-nominated overlooked candidates','']
        for row in nominated[:2]:
            c=confirmations[row['id']+'__'+row['condition']]['assessment']['condition_effects'][0]
            lines += [f"- {row['component_id']} {row['condition']}: Terra {row['change_strength']}/4 change, {row['coherence']}/4 coherence, {row['hits']}/{row['n']} matches. Sol supports nominated interpretation: {c['hypothesis_supported']}; {c['note']}"]
        lines+=['','Full per-condition scores, paired text, counterexamples and unexecuted follow-up proposals are in the sidecar. Pure looping can rank as a large change while remaining in the mixed/collapse queue; it is not promoted to a coherent persona.','']
        report='\n'.join(lines);(evidence/'report.md').write_text(report,encoding='utf-8');(ROOT/'docs/extremity-rereview-v1.md').write_text(report,encoding='utf-8')
        save(evidence/'export-complete.json',{'audit_passed':True,'manifest_sha256':fingerprint(manifest),'components':2240})
        status('complete',components=2240,conditions=condition_count,nominations=len(nominated))
    except BaseException as exc:status('failed',error_type=type(exc).__name__,error=str(exc));raise

if __name__=='__main__':
    manifest=prepare()
    if '--prepare-only' not in sys.argv:
        with (OUT/'.runner.lock').open('a+b') as lock:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint32];kernel.SetThreadExecutionState.restype=ctypes.c_uint32
            try:
                assert kernel.SetThreadExecutionState(0x80000001),'Temporary sleep-prevention request failed'
                run(manifest)
            finally:kernel.SetThreadExecutionState(0x80000000)
