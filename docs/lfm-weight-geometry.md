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

## The reported creator recipe matches the edit locations

The creator metadata names an older base commit, `b9d6e4e…`, while our frozen experiment pins `9921cd4d…`. A [public Hugging Face metadata check](../site-source/evidence/lfm-depth-20261127-v1/posthoc-base-origin-v1.json) confirms that both revisions reference the exact same 708,984,464-byte weight file, SHA-256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`. No model download or revision change was needed.

The supplied Heretic v1.4.0 recipe selects layer-specific directions, full row normalization and a rank-three approximation. Its component windows predict attention/convolution edits in layers 3–15 and MLP output edits in layers 10–15, exactly matching the observed matrices. The [recipe audit](../site-source/evidence/lfm-depth-20261127-v1/posthoc-creator-recipe-v1.json) binds the creator files and [pinned implementation](https://github.com/p-e-w/heretic/blob/6ea3b8d778d047b4b3b7c5b843e21c5bea98ee8d/src/heretic/model.py). This checks provenance and edit locations; we have not independently reproduced the creator's refusal benchmark.

## Low-rank edits with layer-dependent directions

For all nineteen changed matrices, a CPU-only FP64 power-iteration analysis estimates that one leading component accounts for **98.49–99.90% of the squared difference norm**. Two deterministic independent starts agree to within `5.6e-16` in these energy fractions. These are approximate leading-component estimates; quantization and normalization mean the saved differences need not have exact rank one.

The dominant output directions differ across matrices: pairwise absolute cosine has median **0.277** and minimum **0.0053**. Within each layer 10–15, its MLP and attention/convolution changes are much more aligned, with absolute cosines **0.9875–0.9992**. This pattern fits the layer-dependent recipe. It does not identify one shared global direction or establish what behavior any inferred direction mediates. The [full rank diagnostics](../site-source/evidence/lfm-depth-20261127-v1/posthoc-edit-rank-v1.json) retain every matrix, pairwise similarity and projection-fit residual.

For context, [Arditi et al.](https://arxiv.org/html/2406.11717) describe a residual-direction orthogonalization method. Our simple projection-fit diagnostics omit the creator recipe's row normalization and approximation; a poor fit to that simpler formula is not evidence that the supplied implementation is wrong. No new activations, weights, generations or reviewer requests were changed for these supplementary analyses.

## The confirmed coordinate is shared

L2 N3420's W1/W3 input rows and W2 output column are exactly equal between the checkpoints. The token embeddings and all weights through block 2 are also equal. Thus an identical token prefix reaches an identical early computation, subject to the same numerical execution; later edited blocks can still change the output and subsequent generated-token history. Shared early weights do not establish that the complete models are functionally equivalent.

In the separate prospective +9x experiment, each reviewer matched the same 29 of 32 prompts in both checkpoints. This observation and the weight comparison give useful context for the paired similarity, but no causal mediation experiment has isolated which later edits preserve or alter this mode. [Confirmation results](campaign-lfm-depth-20261127-v1-01-confirm-p9.md).

## Static vocabulary projections

For eight coordinates already selected for the dose study, the supplement computes `embedding[token] · normalize(W2[:, neuron])` separately in each checkpoint. It retains the highest and lowest sixteen token scores, with twenty seeded reference coordinates from the same layers. These references are real neuron columns normalized to unit length; they are distinct from the generation campaign's matched random-direction controls. No generated response, new activation intervention or reviewer request was added.

The negative lists contain the lowest signed scores under that positive column, equivalently the highest-ranked tokens under its negation. Saved values retain the original signed dot product. An actual clamp changes the residual contribution by `(target − natural_activation) × W2[:, neuron]`, so the sign of a requested target alone does not determine the change at every token.

The positive readout for L2 N3420 includes **naval, doctrine, bilateral, kinetic and diplomatic** among its top sixteen tokens. The negative readout for L2 N3030 starts with **agro, agriculture, agricultural, fertilizers, manure, fertilizer, agrí and livestock**. These signs align with the already measured positive diplomatic/military and negative agricultural takeovers. Those two neurons' output columns and embeddings are unchanged, so the corresponding readouts are identical across the checkpoints.

This alignment is a post hoc clue. The readout omits the current residual state, normalization, natural activation, gating and all later attention/convolution/MLP processing. It is not a calibrated token probability or a complete functional label. Other measured modes have less obviously aligned token lists; all eight and the seeded references remain in the download. The [Tuned Lens paper](https://arxiv.org/abs/2303.08112) documents brittleness even for direct hidden-state readouts; this simpler weight-column projection should receive no stronger interpretation.

The retained first descriptive pass used FP32 cosine arithmetic, which produced tiny rounding excursions above one. The separately versioned second pass uses bounded FP64 cosines and explicit exact-equality checks. Both source versions and the predecessor output hash are preserved. This correction changes the supplementary arithmetic, not any campaign generation or behavioral verdict.

## How widely the output columns changed

The complete column check finds **46,080 exactly shared W2 columns** in layers 0–9 and **27,648 changed columns** in layers 10–15: every output column in those six later layers differs. These are counts of saved weight columns, not counts of changed behavioral functions. A separate post hoc FP64 calculation measures each original/edited column's angle and norm ratio, retaining quantiles and the sixteen most/least rotated columns per layer.

| Layer | Median column angle | 99th percentile angle | Largest angle | Coordinate at largest angle |
|---|---:|---:|---:|---|
| 10 | 1.76° | 8.71° | 17.21° | L10 N3582 |
| 11 | 1.91° | 8.09° | 23.04° | L11 N2777 |
| 12 | 1.80° | 7.13° | 14.48° | L12 N1071 |
| 13 | 1.84° | 7.97° | 30.16° | L13 N1465 |
| 14 | 1.49° | 6.19° | 27.56° | L14 N4221 |
| 15 | 1.42° | 6.03° | 13.70° | L15 N424 |

Quantiles use linear interpolation. The existing timing study's late coordinates are L10 N4198 and L13 N4194, selected from earlier behavioral validation or its disclosed backfill. Their output columns rotate by 1.15° and 0.44°, respectively. L13 N1465, the most rotated column overall, has a relative column L2 change of 0.509 and an edited/original norm ratio of 0.949. A small matrix-wide difference therefore does not imply the same geometric change for every neuron.

This map was computed **after the timing study froze**. It does not change that study's selections, sources, interventions or gates. The [column-edit data](../site-source/evidence/lfm-depth-20261127-v1/posthoc-column-edit-map-v1.json) bind the pinned weights, predecessor geometry, source and already frozen timing manifest. Equal-column counts and minimum cosines are independently checked against the earlier complete geometry output.

A possible future inquiry is to compare the most rotated columns with low-rotation columns within the same layers, matched on original output norm and ordinary activation statistics, then use shared fresh prompts and independent confirmation. That inquiry has not been executed or added to the finite programme. Rotation alone does not predict a behavioral effect, identify a refusal feature or establish a causal explanation for paired similarities.

## How this informs the remaining work

Before the timing/operator and pair stages started, their candidate-pool rules were adapted to reserve two coordinates from layers with changed MLP output matrices. Earlier validation nominations select the candidates, with disclosed prior-validation backfills if necessary; no held-out scores are used. The pair design includes a pair between these two candidates. This adds edited-region coverage while preserving the existing configuration and reviewer ceilings. The numerical sampling stage already covers every layer. The [recorded design amendment](../site-source/evidence/lfm-depth-20261127-v1/adaptive-design-late-region-v1.json) precedes those stages' source freezes and first measurements.
