# Where the LFM checkpoint weights differ

A post hoc, CPU-only comparison of the two pinned weight files found **19 changed named tensors out of 148**. The other 129 tensors are exactly equal in their saved BF16 values. This counts tensors, not their importance or the fraction of all parameters changed. Both complete weight-file hashes were verified against the first confirmation manifest before comparison.

| Weight group | Comparison |
|---|---|
| Token embeddings and all normalization weights | Exactly equal |
| All MLP input/gate matrices, W1 and W3 | Exactly equal |
| MLP output matrices, W2, layers 0–9 | Exactly equal |
| MLP output matrices, W2, layers 10–15 | Changed |
| Attention/convolution output projections, layers 0–2 | Exactly equal |
| Attention/convolution output projections, layers 3–15 | Changed |

For the six changed W2 matrices, the Frobenius norm of the difference is about 3.7–5.3% of the original matrix norm. That is a change-magnitude ratio, not the percentage of elements edited. The [complete comparison](../site-source/evidence/lfm-depth-20261127-v1/posthoc-weight-geometry-v2.json) records shapes, exact equality, changed-element counts and norm ratios for every named tensor. Checkpoint configuration and chat-template files differ too; the intervention campaign deliberately uses the original tokenizer, effective configuration and native runtime for both weight sets.

## The confirmed coordinate is shared

L2 N3420's W1/W3 input rows and W2 output column are exactly equal between the checkpoints. The token embeddings and all weights through block 2 are also equal. Thus an identical token prefix reaches an identical early computation, subject to the same numerical execution; later edited blocks can still change the output and subsequent generated-token history. Shared early weights do not establish that the complete models are functionally equivalent.

In the separate prospective +9x experiment, each reviewer matched the same 29 of 32 prompts in both checkpoints. This observation and the weight comparison give useful context for the paired similarity, but no causal mediation experiment has isolated which later edits preserve or alter this mode. [Confirmation results](campaign-lfm-depth-20261127-v1-01-confirm-p9.md).

## Static vocabulary projections

For eight coordinates already selected for the dose study, the supplement computes `embedding[token] · normalize(W2[:, neuron])` separately in each checkpoint. It retains the highest and lowest sixteen token scores, with twenty seeded reference coordinates from the same layers. These references are real neuron columns normalized to unit length; they are distinct from the generation campaign's matched random-direction controls. No generated response, new activation intervention or reviewer request was added.

The positive readout for L2 N3420 includes **naval, doctrine, bilateral, kinetic and diplomatic** among its top sixteen tokens. The negative readout for L2 N3030 starts with **agro, agriculture, agricultural, fertilizers, manure, fertilizer, agrí and livestock**. These signs align with the already measured positive diplomatic/military and negative agricultural takeovers. Those two neurons' output columns and embeddings are unchanged, so the corresponding readouts are identical across the checkpoints.

This alignment is a post hoc clue. The readout omits the current residual state, normalization, natural activation, gating and all later attention/convolution/MLP processing. It is not a calibrated token probability or a complete functional label. Other measured modes have less obviously aligned token lists; all eight and the seeded references remain in the download. The [Tuned Lens paper](https://arxiv.org/abs/2303.08112) documents brittleness even for direct hidden-state readouts; this simpler weight-column projection should receive no stronger interpretation.

The retained first descriptive pass used FP32 cosine arithmetic, which produced tiny rounding excursions above one. The separately versioned second pass uses bounded FP64 cosines and explicit exact-equality checks. Both source versions and the predecessor output hash are preserved. This correction changes the supplementary arithmetic, not any campaign generation or behavioral verdict.

## How this informs the remaining work

Before the timing/operator and pair stages started, their candidate-pool rules were adapted to reserve two coordinates from layers with changed MLP output matrices. Earlier validation nominations select the candidates, with disclosed prior-validation backfills if necessary; no held-out scores are used. The pair design includes a pair between these two candidates. This adds edited-region coverage while preserving the existing configuration and reviewer ceilings. The numerical sampling stage already covers every layer. The [recorded design amendment](../site-source/evidence/lfm-depth-20261127-v1/adaptive-design-late-region-v1.json) precedes those stages' source freezes and first measurements.
