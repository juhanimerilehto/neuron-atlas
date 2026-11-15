# Full-coordinate paired Llama 3.2 1B experiment

This experiment compares [meta-llama/Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) at `9213176726f574b556790deb65791e0c5aa438b6` with [ai-anytime/Llama-3.2-1B-Instruct-abliterated](https://huggingface.co/ai-anytime/Llama-3.2-1B-Instruct-abliterated) at `a64c62f24f7da804fe16aa9ad0624767d22efffc`. The original and derivative weight files are pinned and hashed. Both contain 1,235,814,400 stored parameters, 16 layers and 8,192 MLP coordinates per layer. Built with Llama; model weights remain subject to their upstream Llama 3.2 license and are not distributed in this repository.

## Research question and controls

The preceding Qwen3-0.6B comparison found similar kinds of behavioral change in both checkpoints, with differences in repetition and collapse. This experiment asks whether that descriptive pattern also occurs in a Llama pair. Family, size and community editing implementation differ, so agreement across pairs would not isolate a single cause.

Both checkpoints receive the same ordinary prompts, original-model tokenizer, chat template, generation configuration and rotary-position settings. The derivative's Transformers 5 serialization is normalized to the verified equivalent original configuration in the pinned Transformers 4.51.3 environment. Inference uses BF16, SDPA and greedy decoding. We load one model at a time and preserve other GPU workloads.

Local tensor comparison found identical names, shapes and dtypes. Thirty-three tensors differ: the embedding and the attention-output/MLP-output matrices. The remaining 113 tensors are exactly equal. This inventories the weight changes; it does not prove their rank or validate upstream behavioral claims. Metadata records the author's single-direction editing procedure separately.

The intervention clamps one pre-down-projection MLP coordinate at all unpadded prompt and decode positions. Targets are signed multiples of the original checkpoint's calibration maximum. Both models use those identical target values; native calibration is also retained. An unmodified anchor is included in every physical batch, accounting for BF16 differences between batch shapes. Model parameters are not edited by this experiment.

## Numerical screen and shared shortlist

All **131,072 coordinates per checkpoint** are screened at off and ±4/±12 calibration maxima: **655,360 configurations per model**, or **1,310,720 across the pair**. Each configuration scores the same original-model continuation at answer positions 0, 8, 16, 32 and 64, retaining only positions valid before the source continuation ends. One configuration contains several position scores; it is not a complete generated answer.

Each model/layer nominates three opening-token JS-divergence leaders and three different leaders by positive later-minus-opening divergence. Two seeded random coordinates per layer are sampled outside both leader sets and shared by the checkpoints. Their union yields between 128 and 224 coordinates, tested in both models. The seed is 2026111501.

Fine screening uses two further ordinary continuations and 17 settings (off and both signs at 0.5, 1, 2, 3, 4, 6, 8 and 12). Each coordinate receives a shared 13-setting generation ladder chosen from both checkpoints' fine scores. Discovery generates 128-token responses to four ordinary prompts. The prompt lists match the earlier Qwen experiment; they were fixed before inspecting Llama outputs.

## Interpretation and follow-up tests

Codex Terra (`gpt-6.1-terra`, medium reasoning) reviews every supplied paired output and names effects freely. Change and coherence are separate 0–4 ordinal ratings. Repetition, collapse, task loss and baseline defects are recorded separately. No topic, moral valence or novelty label receives selection priority. The checkpoint name is not evidence of an effect. Reviewer text, source references and proposed follow-ups are retained.

The union of twelve readable and four mixed/collapsed nominations per checkpoint advances to validation on eight fresh prompts, 192 tokens, and refined doses. Reviewed observations are appended to the catalogue. The union of six readable nominations per checkpoint, at their nominated settings, is then frozen for held-out testing. The zero-mixed-quota case is explicitly enforced: at most twelve coordinates and two settings per coordinate advance.

Both checkpoints receive sixteen held-out prompts at 256 tokens, eight longer prompts at 384 tokens, eight replication prompts at 256 tokens, and four matched random directions on eight held-out prompts per setting. Frozen validation descriptions are assessed by Terra and independent Sol (`gpt-6.1-sol`, medium reasoning).

The unchanged strict gate requires validation and final change/coherence of at least 3/4, at least 4/8 validation matches, 8/16 held-out matches, 4/8 longer matches and 4/8 replication matches, and no more than two repetition and two collapse flags across the 32 selected-condition neuron outputs. Both final reviewers must support the frozen description and meet the final criteria. A failed gate does not imply no behavioral effect.

## Paired descriptive comparison

The primary comparison includes **every frozen coordinate/dose combination in both checkpoints**, even when the models nominate different preferred settings. For each reviewer, compare repetition and collapse counts over the same 32 neuron outputs. Retain task-loss and baseline-defect counts, change/coherence ratings, effect matches, controls and counterexamples. Displaying a preferred dose must not filter the primary checkpoint comparison.

These are descriptive results for selected coordinates and finite prompt sets. Reused prompts, selection and multiple settings mean they are not independent population samples. Neither a higher repetition count nor a pass/fail total establishes a general safety or capability ranking.

## Budgets, validation and publication

The frozen ceiling is **700,000 configurations per model**, with a conservative algorithmic upper bound of 680,512: 655,360 broad + 7,616 fine + 11,648 discovery + 4,352 validation + 1,536 final/control configurations. Logical counts exclude same-batch baseline anchor rows. Starting physical batch sizes are 16 screening rows and 8 generation rows; CUDA memory failures halve a physical batch while retaining a new untouched anchor for each smaller batch.

Primary reviewer requests have a 700-request ceiling; independent requests have a 100-request ceiling. Maximum candidate counts and two attempts per bundle fit these ceilings. Numerical worker metadata and token-ID arrays stay in the raw archive but are omitted from reviewer transport. Full prompts, before/after text, controls and canonical references are preserved. A transport-size check runs before dispatch. Invalid responses are never silently edited. Two exhausted attempts become an explicit review gap; other candidates continue. Missing final assessments cannot pass the gate.

The manifest binds model identities, source hashes, prompt lists, calibration, prefix bank, preflight, tensor inventory, selection and budgets. SQLite journals support resumable bounded work. Regression tests cover causal later-position scores, untouched anchors, hook cleanup, zero-quota nominations and review-text preservation. The actual GPU preflight must pass before the manifest is frozen.

A final independent audit checks all job identities and coordinate coverage, exact saved generation pairs against their completed raw jobs, acquired file hashes, calibration/prefix identities, reviewer wires/reference maps and winning raw replies, budget adherence and explicit missing reviews. Public catalogue snapshots contain measured observations and exact selected before/after examples. Progress panels are timestamped publication snapshots. The temporary 30-minute monitor recovers failures within the frozen scope and publishes reviewed snapshots until final audit and deployment verification, then stops.
