# Related work for the LFM depth programme

The programme combines established intervention and evaluation ideas with checkpoint-specific empirical tests. The catalogue's observations are not claims that these methods or behaviors were discovered here first.

- [How to use and interpret activation patching](https://arxiv.org/html/2404.15255v1): exploration, confirmation, redundancy and limits of causal interpretation. Our constant clamps differ from resampling natural activations.
- [Information-Theoretic Design of Sparse Autoencoder-Based Steering](https://arxiv.org/html/2611.01378v1): timed pulses and downstream diagnostics. Its SAE-distribution measurements differ from our raw-coordinate and next-token measurements.
- [SAIF](https://arxiv.org/html/2502.11356v1): feature calibration and instruction position. Learned SAE features are not individual MLP neurons.
- [Causal Language Control via Sparse Feature Steering](https://arxiv.org/html/2507.13410v2): separates language change from semantic preservation, motivating separate task-loss reporting.
- [Does Steering Break Your Model?](https://arxiv.org/abs/2610.07722): evaluates efficacy together with side effects across operating points.
- [Forecasting Side Effects of Activation Steering](https://arxiv.org/abs/2608.11227): motivates checking behavioral interactions rather than a single target score.

The prospective +9x test has a public preregistration. Later stages adapt from earlier validation results and freeze their own plans before execution. Shared prompt templates, finite selection, ordinal LLM judgments and numerical precision limits remain explicit. The local knowledge library retains longer methodological notes, proposals and the versioned cache-check diagnosis. [Programme protocol](lfm-depth-20261127-v1.md).

## Static readouts and checkpoint geometry

Belrose et al., [Eliciting Latent Predictions from Transformers with the Tuned Lens](https://arxiv.org/abs/2303.08112), describe brittleness in the earlier direct logit lens and train affine probes to improve readouts. Our supplementary static projection of a single MLP output column into tied vocabulary embeddings is weaker than a trained lens: it omits residual context, normalization, gating and later layers. Its token lists are descriptive clues, separate from the campaign's generated-response evidence. [Measured checkpoint comparison](lfm-weight-geometry.md).
