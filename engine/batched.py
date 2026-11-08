"""Batched same-prompt interventions with per-row directions and a bounded journal."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import sys
import time
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'worker'))
from reference import fingerprint


class BatchJournal:
    def __init__(self,path,identity,limit=100000):
        self.identity=identity;self.limit=limit
        self.db=sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT)')
        saved=self.db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()
        if saved and saved[0]!=identity:
            raise ValueError('Journal protocol identity changed')
        self.db.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)',('identity',identity))
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, config TEXT NOT NULL, result TEXT, status TEXT NOT NULL)')
        self.db.commit()
        self.count=self.db.execute('SELECT count(*) FROM jobs').fetchone()[0]

    def run(self,configs,action):
        keys=[fingerprint({'identity':self.identity,'config':c}) for c in configs]
        if len(set(keys))!=len(keys):
            raise ValueError('Duplicate batch job IDs')
        existing={k:self.db.execute('SELECT status,result FROM jobs WHERE id=?',(k,)).fetchone() for k in keys}
        missing=[i for i,k in enumerate(keys) if not existing[k] or existing[k][0]!='complete']
        new=sum(existing[keys[i]] is None for i in missing)
        if self.count+new>self.limit:
            raise RuntimeError('100,000-job budget exhausted')
        if missing:
            with self.db:
                for i in missing:
                    self.db.execute('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?)',
                        (keys[i],json.dumps(configs[i],sort_keys=True),None,'pending'))
            self.count+=new
            results=action([configs[i] for i in missing])
            if len(results)!=len(missing):
                raise ValueError('Result cardinality mismatch')
            with self.db:
                for i,result in zip(missing,results):
                    encoded=json.dumps(result,allow_nan=False,ensure_ascii=False)
                    self.db.execute("UPDATE jobs SET result=?,status='complete' WHERE id=?",(encoded,keys[i]))
            for i,result in zip(missing,results):
                existing[keys[i]]=('complete',json.dumps(result))
        return [json.loads(existing[k][1]) for k in keys]

    def completed(self):
        return self.db.execute("SELECT count(*) FROM jobs WHERE status='complete'").fetchone()[0]


class BatchedWorker:
    def __init__(self,reference):
        self.reference=reference;self.model=reference.model;self.device=reference.device

    @contextmanager
    def hook(self,layer,pushes,ablate=None):
        handles=[]
        try:
            module=self.reference.layers[layer].mlp.down_proj
            if ablate is not None:
                def pre_hook(module,args):
                    x=args[0].clone()
                    for row,coordinate in enumerate(ablate):
                        if coordinate is not None:
                            x[row,-1,coordinate]=0
                    return (x,)
                handles.append(module.register_forward_pre_hook(pre_hook))
            def post_hook(module,args,output):
                x=output.clone();x[:,-1,:]+=pushes.to(output.dtype);return x
            handles.append(module.register_forward_hook(post_hook))
            yield
        finally:
            for handle in handles:handle.remove()

    @torch.inference_mode()
    def distributions(self,prompt,layer,pushes,ablate=None):
        inputs=self.reference.encode(prompt)
        batch=len(pushes)
        values={k:v.repeat(batch,1) for k,v in inputs.items()}
        with self.hook(layer,pushes,ablate):
            logits=self.model(**values,use_cache=False).logits[:,-1,:].float()
        if not torch.isfinite(logits).all():raise ValueError('Non-finite logits')
        return logits.log_softmax(-1)

    @torch.inference_mode()
    def generate(self,prompt,layer,pushes,max_tokens=48,ablate=None):
        inputs=self.reference.encode(prompt);batch=len(pushes);length=inputs.input_ids.shape[1]
        values={k:v.repeat(batch,1) for k,v in inputs.items()}
        with self.hook(layer,pushes,ablate):
            output=self.model.generate(**values,max_new_tokens=max_tokens,do_sample=False,use_cache=True,
                pad_token_id=self.reference.tokenizer.eos_token_id)
        result=[];eos=self.reference.tokenizer.eos_token_id
        for row in output[:,length:].tolist():
            if eos in row:row=row[:row.index(eos)+1]
            result.append({'text':self.reference.tokenizer.decode(row,skip_special_tokens=True),
                'token_ids':row,'termination':'eos' if row and row[-1]==eos else 'max_tokens'})
        return result

    @torch.inference_mode()
    def conformance(self,prompt,layer,scale):
        from reference import Intervention
        directions=torch.stack([self.reference.column(layer,i) for i in [17,83,201]])
        doses=torch.tensor([.15,-.3,0],device=self.device)
        pushes=directions*doses[:,None]*scale
        batched=self.distributions(prompt,layer,pushes)
        individual=torch.stack([self.reference.distribution(prompt,Intervention(layer,v,float(d),scale)) for v,d in zip(directions,doses)])
        error=(batched-individual).abs().max().item()
        bg=self.generate(prompt,layer,pushes,max_tokens=8)
        single=[self.reference.generate(prompt,Intervention(layer,v,float(d),scale),max_tokens=8) for v,d in zip(directions,doses)]
        agreement=[a['token_ids']==b['token_ids'] for a,b in zip(bg,single)]
        return {'passed':error<2e-4 and all(agreement),'max_logprob_error':error,
            'greedy_token_agreement':agreement,'batch_size':3,'padding':'same unpadded prompt repeated'}
