"""Qwen non-thinking worker: single-neuron clamping with paired batch anchors."""
from contextlib import contextmanager
import torch
import numpy as np

class Worker:
    def __init__(self,model,tokenizer,calibration=None):
        self.model=model.eval();self.tok=tokenizer;self.layers=model.model.layers;self.device=next(model.parameters()).device;self.cal=calibration
        eos=model.generation_config.eos_token_id
        self.eos=set(eos if isinstance(eos,list) else [eos])
    def encode(self,prompt):
        text=self.tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        return self.tok(text,add_special_tokens=False,return_tensors='pt').to(self.device)
    @contextmanager
    def hook(self,configs):
        layer=configs[0]['layer'];module=self.layers[layer].mlp.down_proj;handles=[];captured={};n=len(configs)
        rows=torch.arange(n,device=self.device);neurons=torch.tensor([c['neuron'] for c in configs],device=self.device)
        norms=module.weight[:,neurons].detach().float().norm(dim=0)
        targets=torch.tensor([0. if c['condition'] in ['baseline','off'] else self.cal[str(layer)]['activation_abs_max'][c['neuron']]*(1 if c['condition']=='positive' else -1) for c in configs],device=self.device)
        baselines=torch.tensor([c['condition']=='baseline' for c in configs],device=self.device)
        any_random=any(c.get('random_index') is not None for c in configs)
        randoms=torch.tensor([c.get('random_index') is not None for c in configs],device=self.device)
        vectors=[]
        for c in configs:
            g=torch.Generator().manual_seed(910000+layer*100+c.get('random_index',0))
            v=torch.randn(module.out_features,generator=g).to(self.device);vectors.append(v/v.norm())
        vectors=torch.stack(vectors);max_delta=torch.zeros(n,device=self.device);steps=0
        def pre(module,args):
            nonlocal steps
            values=args[0];natural=values[rows,:,neurons].float();delta=torch.where(baselines[:,None],torch.zeros_like(natural),targets[:,None]-natural)
            captured['delta']=delta;max_delta.copy_(torch.maximum(max_delta,delta.abs().amax(1)));steps+=1
            result=values.clone();result[rows,:,neurons]=torch.where((baselines|randoms)[:,None],natural,targets[:,None]).to(values.dtype)
            return (result,)
        def post(module,args,output):
            if not any_random:return output
            result=output.clone();result+=(vectors[:,None,:]*(captured['delta']*norms[:,None]*randoms[:,None])[:,:,None]).to(output.dtype);return result
        try:
            handles=[module.register_forward_pre_hook(pre),module.register_forward_hook(post)]
            diagnostics={'max_delta':max_delta,'column_norms':norms,'targets':targets,'steps':lambda:steps}
            yield diagnostics
        finally:
            for handle in handles:handle.remove()
    @torch.inference_mode()
    def generate(self,configs):
        assert len({(c['layer'],c['prompt'],c['max_tokens']) for c in configs})==1
        anchor={**configs[0],'condition':'baseline'};anchor.pop('random_index',None);all_configs=configs+[anchor]
        inputs=self.encode(configs[0]['prompt']);length=inputs.input_ids.shape[1]
        values={k:v.repeat(len(all_configs),1) for k,v in inputs.items()}
        with self.hook(all_configs) as d:
            output=self.model.generate(**values,max_new_tokens=configs[0]['max_tokens'],do_sample=False,use_cache=True,
                pad_token_id=self.tok.eos_token_id,temperature=None,top_p=None,top_k=None)
        result=[]
        for row in output[:,length:].tolist():
            stop=next((i for i,t in enumerate(row) if t in self.eos),None)
            if stop is not None:row=row[:stop+1]
            result.append({'text':self.tok.decode(row,skip_special_tokens=True),'token_ids':row,'termination':'eos' if row and row[-1] in self.eos else 'max_tokens'})
        delta=d['max_delta'].cpu().tolist();norms=d['column_norms'].cpu().tolist();targets=d['targets'].cpu().tolist()
        for i,r in enumerate(result[:-1]):
            r['batch_baseline']=result[-1];r['batch_width']=len(all_configs)
            r['intervention']={'target_activation':targets[i],'max_abs_activation_delta':delta[i],
                'max_residual_write_norm':delta[i]*norms[i],'residual_norm_ratio':delta[i]*norms[i]/self.cal[str(configs[i]['layer'])]['median_residual_l2'],
                'hook_steps':d['steps'](),'position_policy':'All unpadded prompt positions and every cached decode input.'}
        return result[:-1]
    @torch.inference_mode()
    def calibration_sample(self,prompt,layers):
        handles=[];saved={str(l):{} for l in layers}
        for l in layers:
            def pre(module,args,index=l):saved[str(index)]['activation_abs_max']=args[0][0].float().abs().amax(0).cpu().tolist()
            def post(module,args,output,index=l):
                value=output[0] if isinstance(output,tuple) else output
                saved[str(index)]['residual_l2']=value[0,-1].float().norm().item()
            handles += [self.layers[l].mlp.down_proj.register_forward_pre_hook(pre),self.layers[l].register_forward_hook(post)]
        try:self.model(**self.encode(prompt),use_cache=False)
        finally:
            for h in handles:h.remove()
        return saved
    @torch.inference_mode()
    def conformance(self,prompt,layer,neuron):
        inputs=self.encode(prompt);base=self.model(**inputs,use_cache=False).logits[:,-1].float()
        cfg={'prompt':prompt,'layer':layer,'neuron':neuron,'condition':'baseline','max_tokens':8}
        with self.hook([cfg]):zero=self.model(**inputs,use_cache=False).logits[:,-1].float()
        with self.hook([{**cfg,'condition':'off'}]):self.model(**inputs,use_cache=False)
        restored=self.model(**inputs,use_cache=False).logits[:,-1].float()
        paired={k:v.repeat(2,1) for k,v in inputs.items()}
        plain=self.model(**paired,use_cache=False).logits[:,-1].float()
        with self.hook([{**cfg,'condition':'off'},cfg]):changed=self.model(**paired,use_cache=False).logits[:,-1].float()
        with self.hook([{**cfg,'condition':'off'}]):
            prefill=self.model(**inputs,use_cache=True);next_id=prefill.logits[:,-1].argmax(-1,keepdim=True)
            cached=self.model(input_ids=next_id,past_key_values=prefill.past_key_values,
                attention_mask=torch.ones(1,inputs.input_ids.shape[1]+1,device=self.device,dtype=torch.long),use_cache=True).logits[:,-1].float()
        def replay_hook(module,args):
            value=args[0].clone();value[:,:,neuron]=0;return (value,)
        handle=self.layers[layer].mlp.down_proj.register_forward_pre_hook(replay_hook)
        try:replayed=self.model(input_ids=torch.cat([inputs.input_ids,next_id],dim=1),use_cache=False).logits[:,-1].float()
        finally:handle.remove()
        cache_error=(cached-replayed).abs().max().item()
        errors={'baseline_hook':(base-zero).abs().max().item(),'hook_removal':(base-restored).abs().max().item(),
            'batch_anchor_isolation':(plain[1]-changed[1]).abs().max().item()}
        return {'passed':max(errors.values())<1e-5 and cache_error<=.25,'max_abs_logit_errors':errors,
            'cached_decode_replay_error':cache_error,'cached_decode_tolerance_bf16':.25,
            'single_vs_batch_bf16_logit_difference':(plain[0]-base[0]).abs().max().item(),
            'dtype':'bfloat16','comparison_policy':'Every generation includes an unmodified anchor in the SAME batch; cross-batch BF16 equality is not assumed.',
            'thinking_enabled':False,'unpadded':True}
