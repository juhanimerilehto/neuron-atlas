"""Map each architecture's actual gated-MLP output projection onto the verified clamp."""
from types import SimpleNamespace
from pairedllama.actor import Worker as PrefixWorker


class LayerAdapter:
    def __init__(self, layer, projection):
        self.layer = layer
        self.mlp = SimpleNamespace(down_proj=projection)

    def __getattr__(self, name):
        return getattr(self.layer, name)


class Worker(PrefixWorker):
    def __init__(self, model, tokenizer, calibration=None):
        super().__init__(model, tokenizer, calibration)
        family = model.config.model_type
        assert family in ('lfm2', 'granitemoehybrid')
        self.layers = [LayerAdapter(layer, layer.feed_forward.w2 if family == 'lfm2'
                                    else layer.shared_mlp.output_linear) for layer in model.model.layers]

    def encode(self, prompt):
        text = self.tok.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False, thinking=False)
        return self.tok(text, add_special_tokens=False, return_tensors='pt').to(self.device)

    def generate(self, configs):
        results = super().generate(configs)
        multiplier = abs(float(getattr(self.model.config, 'residual_multiplier', 1.)))
        for result in results:
            metrics = result['intervention']
            metrics['max_residual_write_norm'] *= multiplier
            metrics['residual_norm_ratio'] *= multiplier
            metrics['post_projection_residual_multiplier'] = multiplier
        return results
