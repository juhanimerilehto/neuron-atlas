"""Full-sequence individual-neuron clamps, fast distribution screens, paired anchors."""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import torch
spec=importlib.util.spec_from_file_location('frozen_pilot_worker',Path(__file__).resolve().parents[1]/'extreme/worker.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
PilotWorker=module.Worker

class Worker(PilotWorker):
    @contextmanager
    def hook(self,configs):
        layer=configs[0]['layer'];module=self.layers[layer].mlp.down_proj;n=len(configs);handles=[];captured={}
        rows=torch.arange(n,device=self.device);neurons=torch.tensor([c['neuron'] for c in configs],device=self.device)
        norms=module.weight[:,neurons].detach().float().norm(dim=0)
        nominal=torch.tensor([0. if c['condition'] in ['baseline','off'] else self.cal[str(layer)]['activation_abs_max'][c['neuron']]*c.get('factor',1.)*(1 if c['condition']=='positive' else -1) for c in configs],device=self.device)
        targets=nominal.to(module.weight.dtype).float()
        baseline=torch.tensor([c['condition']=='baseline' for c in configs],device=self.device)
        random=torch.tensor([c.get('random_index') is not None for c in configs],device=self.device)
        any_random=any(c.get('random_index') is not None for c in configs)
        vectors=[]
        if any_random:
            for c in configs:
                g=torch.Generator().manual_seed(770000+layer*1000+c.get('random_index',0))
                v=torch.randn(module.out_features,generator=g).to(self.device);vectors.append(v/v.norm())
            vectors=torch.stack(vectors)
        maximum=torch.zeros(n,device=self.device);steps=0
        def pre(module,args):
            nonlocal steps
            values=args[0];natural=values[rows,:,neurons].float();delta=torch.where(baseline[:,None],torch.zeros_like(natural),targets[:,None]-natural)
            captured['delta']=delta;maximum.copy_(torch.maximum(maximum,delta.abs().amax(1)));steps+=1
            x=values.clone();x[rows,:,neurons]=torch.where((baseline|random)[:,None],natural,targets[:,None]).to(values.dtype);return (x,)
        def post(module,args,output):
            if not any_random:return output
            x=output.clone();x+=(vectors[:,None,:]*(captured['delta']*norms[:,None]*random[:,None])[:,:,None]).to(output.dtype);return x
        try:
            handles=[module.register_forward_pre_hook(pre),module.register_forward_hook(post)]
            yield {'max_delta':maximum,'column_norms':norms,'targets':targets,'nominal_targets':nominal,'steps':lambda:steps}
        finally:
            for h in handles:h.remove()
    @torch.inference_mode()
    def generate(self,configs):
        assert len({(c['layer'],c['prompt'],c['max_tokens']) for c in configs})==1
        anchor={**configs[0],'condition':'baseline'};anchor.pop('random_index',None);all_configs=configs+[anchor]
        inputs=self.encode(configs[0]['prompt']);length=inputs.input_ids.shape[1];values={k:v.repeat(len(all_configs),1) for k,v in inputs.items()}
        with self.hook(all_configs) as d:
            output=self.model.generate(**values,max_new_tokens=configs[0]['max_tokens'],do_sample=False,use_cache=True,
                pad_token_id=self.tok.eos_token_id,temperature=None,top_p=None,top_k=None,logits_to_keep=1)
        result=[]
        for row in output[:,length:].tolist():
            stop=next((i for i,t in enumerate(row) if t in self.eos),None)
            if stop is not None:row=row[:stop+1]
            result.append({'text':self.tok.decode(row,skip_special_tokens=True),'token_ids':row,'termination':'eos' if row and row[-1] in self.eos else 'max_tokens'})
        delta=d['max_delta'].cpu().tolist();norms=d['column_norms'].cpu().tolist();targets=d['targets'].cpu().tolist();nominal=d['nominal_targets'].cpu().tolist()
        for i,v in enumerate(result[:-1]):
            v['batch_baseline']=result[-1];v['batch_width']=len(all_configs)
            v['intervention']={'target_activation':targets[i],'nominal_target_activation':nominal[i],
                'max_abs_activation_delta':delta[i],'max_residual_write_norm':delta[i]*norms[i],
                'residual_norm_ratio':delta[i]*norms[i]/self.cal[str(configs[i]['layer'])]['median_residual_l2'],
                'hook_steps':d['steps'](),'position_policy':'All unpadded prompt and cached decode positions; maximum includes internal finished-row steps.'}
        return result[:-1]
    @torch.inference_mode()
    def distributions(self,configs):
        assert len({(c['layer'],c['prompt']) for c in configs})==1
        anchor={**configs[0],'condition':'baseline'};anchor.pop('random_index',None);all_configs=configs+[anchor]
        inputs=self.encode(configs[0]['prompt']);values={k:v.repeat(len(all_configs),1) for k,v in inputs.items()}
        with self.hook(all_configs):logits=self.model(**values,use_cache=False,logits_to_keep=1).logits[:,-1].float()
        assert torch.isfinite(logits).all(),'Non-finite distribution logits'
        logp=logits.log_softmax(-1);p=logp.exp();base=logp[-1];bp=p[-1]
        midpoint=torch.logaddexp(logp,base[None,:])-torch.log(torch.tensor(2.,device=self.device))
        js=(.5*(p*(logp-midpoint)).sum(-1)+.5*(bp[None,:]*(base[None,:]-midpoint)).sum(-1)).clamp_min(0)
        kl=(bp[None,:]*(base[None,:]-logp)).sum(-1).clamp_min(0);entropy=-(p*logp).sum(-1)
        top=logp.topk(8,dim=-1);ids=top.indices.cpu().tolist();lp=top.values.cpu().tolist();j=js.cpu().tolist();k=kl.cpu().tolist();h=entropy.cpu().tolist()
        summary=[{'entropy':h[i],'top_tokens':[{'id':token,'text':self.tok.decode([token]),'logprob':value} for token,value in zip(ids[i],lp[i])]} for i in range(len(all_configs))]
        return [{'js':j[i],'kl':k[i],**summary[i],'batch_baseline':summary[-1],'batch_width':len(all_configs)} for i in range(len(configs))]
