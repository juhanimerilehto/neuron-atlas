# LFM2.5-350M: full-coordinate neuron campaign

Authorized on 25 November 2026 as part of the finite LFM-then-Granite sequence. 16 layers × 4,608 actual gated-MLP coordinates = 73,728 coordinates per checkpoint. There are 2 checkpoint(s). LFM is the original/abliterated pair; Granite is the dense, all-attention 4.0-350M single-model survey.

## Frozen methods

Screen every coordinate at off and ±4/±12 original-calibration maxima. Score next-token distributions at response positions 0, 8, 16, 32 and 64 on common original-model continuations. The clamp targets the input to LFM feed_forward.w2 or Granite shared_mlp.output_linear. All prompt and cached decode positions are unpadded. Parameters are unchanged. Each physical batch retains an unmodified anchor. Native calibration is retained separately; paired models share original targets and token IDs.

Per layer and checkpoint, nominate three early and three distinct delayed-effect leaders, plus two shared seeded random coordinates. Fine-screen the union with 17 settings on two ordinary continuations. Generate a shared 13-setting ladder on four ordinary prompts at 128 tokens. Terra labels effects freely without a preferred topic or novelty score. Validate the union of twelve readable and four mixed nominations per checkpoint on eight fresh prompts at 192 tokens. Freeze six readable nominations per checkpoint for held-out tests. Zero mixed quota is enforced.

Finalists receive sixteen held-out prompts (256 tokens), eight longer prompts (384), eight replication prompts (256), and four matched random directions on eight held-out prompts per setting. Terra and independent Sol assess the frozen descriptions, each against its own baseline. Compare every frozen coordinate/dose across paired checkpoints, including regressions, improvements and reviewer disagreements.

The declared gate requires validation/final change and coherence at least 3/4, validation matches ≥4/8, held-out ≥8/16, longer ≥4/8 and replication ≥4/8, with ≤2 repetition and ≤2 collapse flags among the 32 neuron outputs. Both final reviewers must support the description and meet the criteria. Task loss and baseline defects are separate measures: passing does not mean the original task was answered.

## Budget and evidence

Ceiling: 420,000 configurations per checkpoint; conservative algorithmic maximum: 393,792. A configuration contains several numerical position scores or one generated condition; same-batch anchors are additional physical rows. Terra has a 700-request ceiling and Sol 100, including the small synthetic identity fixture used solely to verify reviewer availability. Fixtures never become catalogue measurements. Two attempts per bundle; invalid exhausted replies remain explicit gaps. All raw replies, execution events, wires and reference maps are retained.

The pinned model revisions, downloaded file hashes, real projection shapes, tokenizer checks and GPU conformance are bound by manifest.json, selection.json, weight-comparison.json and preflight.json. Runtime: isolated Transformers 5.24.0 with Torch 2.7.1+cu118; requirements and critical source hashes are recorded. Numerical sources freeze before jobs begin. No automatic source edits or reset of review attempts is permitted after freezing.

Full coverage applies to the fixed numerical grid, not every possible dose or prompt. Exact response pairs and token IDs are linked to SQLite jobs by the independent final audit. Semantic labels remain fallible LLM judgments.

[Queue and recovery instructions](family-campaign-operations.md) · [Catalogue](https://juhanimerilehto.github.io/neuron-atlas/)

## LFM provenance

Original: [LiquidAI/LFM2.5-350M](https://huggingface.co/LiquidAI/LFM2.5-350M), revision `9921cd4d82c0e3986887aa4b376f9446729ef8a3`. Derivative: [s3nh/LFM2.5-350M-abliterated](https://huggingface.co/s3nh/LFM2.5-350M-abliterated), revision `3b5076fba033be25cb354990e7d03d883cf43b2c`. The publisher names parent revision `b9d6e4e2d75f440b12a2b4d731c808004ecbbd89`; its weight-file hash is identical to the acquired original. Exact CPU comparison finds 19 changed and 129 equal tensors. Changes include convolution output projections, attention output projections and MLP outputs. This inventory does not establish the rank of the edit or validate publisher behavioral claims. The raw FFN configuration says 6656; native gated-width adjustment yields 4608, verified in every actual weight matrix.
