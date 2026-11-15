# Single-neuron interventions: Qwen3-0.6B and its abliterated variant

This experiment compared Qwen3-0.6B with Huihui-Qwen3-0.6B-abliterated-v2 by clamping one MLP activation at a time and asking both checkpoints the same ordinary questions. The interventions changed activations during inference; model weights were not edited.

**The checkpoints showed similar kinds of behavioral change, but differed in how often the changed responses repeated or broke down.** The clearest shared effects were English-to-Chinese responses and generic support/help replies replacing the requested answer. The abliterated checkpoint was more repetitive at several matched settings, while some settings favored it. These findings do not establish that either model is generally better, safer, or more steerable.

The experiment screened all 86,016 MLP coordinates in each checkpoint and completed 914,288 measured configurations. Most configurations measured token probabilities; 34,544 generated responses were paired with their own unmodified baselines. The catalogue contains 38 model-specific records: 19 shared coordinates, each observed in two checkpoints.

## Differences between the checkpoints

The following examples use the same coordinate, clamp target, prompts and generation limits in both checkpoints. Terra and Sol are language-model reviewers used through Codex to assess the saved before-and-after responses. Counts below are Sol's judgments on 32 neuron-intervention responses per setting (16 held-out, 8 longer and 8 replication responses). Collapse means the reviewer judged that the output had broken down, for example into malformed or unusable text. A repetition flag and a collapse flag can apply to the same response.

| Matched intervention | Shared observed effect | Original: repetition / collapse | Abliterated: repetition / collapse | Comparison |
|---|---|---|---|---|
| L0-N262 at +5× | Chinese-language responses | 12/32 · 5/32 | 16/32 · 10/32 | More repetition and collapse in the abliterated checkpoint. |
| L7-N2500 at +8× | Generic support/help replaces requested answers | 2/32 · 1/32 | 7/32 · 4/32 | More repetition and collapse in the abliterated checkpoint. |
| L15-N59 at −12× | Predominantly Chinese responses | 5/32 · 1/32 | 3/32 · 0/32 | Less repetition and collapse in the abliterated checkpoint. |
| L10-N400 at −3× | Language switching, sometimes with malformed text | 9/32 · 2/32 | 8/32 · 1/32 | A smaller improvement in the abliterated checkpoint. |

At L0 N262 (+5×), both reviewers identified the language change in all 32 responses from each checkpoint. The difference was therefore in the quality of the changed output, rather than whether a language switch occurred. At L7 N2500 (+8×), Sol matched the support/help pattern in 30/32 original-model responses and 31/32 abliterated-model responses, but flagged substantially more repetition in the latter. At L15 N59 (−12×), both had 31/32 matches, and the abliterated checkpoint had fewer repetition and collapse flags.

Across all eight primary coordinates, Terra rated the abliterated checkpoint as more repetitive at 5/8 settings; Sol did so at 5/8 settings. These are descriptive comparisons of a selected set of interventions. The coordinates and prompts are not independent random samples, and the reviewers can disagree about individual cases.

**Interpretation:** the experiment found changes in the strength and reliability of shared effects. It did not establish a distinct, repeatable behavior unique to the abliterated checkpoint. Ordinary prompts were used to look for unrequested shifts; this was not a refusal or harmful-request benchmark.

## What the stability threshold means

Of the eight primary coordinate/setting pairs tested in each model, 0 satisfied all criteria under both reviewers. This does not mean that the interventions had no effect. A language shift can recur across nearly every prompt and still fail the criterion because three responses repeat: the prespecified limit was two repetition flags among 32 responses.

Passing required change and coherence ratings of at least 3/4, enough matches on fresh prompts (4/8 validation, 8/16 held-out, 4/8 longer and 4/8 replication), no more than two repetition and two collapse flags, and support for the description selected before held-out testing. Both reviewers had to agree that the criteria were met. This is an experiment-specific decision rule, not a certification or a claim that every failed observation is incoherent.

## How the comparison was controlled

Both checkpoints used the original Qwen3-0.6B chat template, identical input token IDs, greedy decoding and thinking disabled. Clamp targets used the original checkpoint's activation calibration in both models. Every intervention response was compared with an unmodified response from the same checkpoint and physical batch. This distinguishes an intervention effect from differences already present in the models' baseline answers.

A dose such as +5× means clamping the coordinate to five times its original-model calibration maximum. It does not mean multiplying its naturally varying activation by five. Matching a coordinate number across the checkpoints identifies the same architectural position, but does not prove it represents an identical feature. Exact checkpoint revisions and the procedure are in the [protocol](paired-qwen06-late-v1.md).

## Measurement coverage

A configuration is one intervention setting on one prompt. A numerical screening configuration contains several token-position scores; it is not a full generated answer. The table separates these stages.

| Stage | Original | Abliterated |
|---|---:|---:|
| screen | 430,080 | 430,080 |
| fine | 9,792 | 9,792 |
| discovery | 14,976 | 14,976 |
| validation | 824 | 824 |
| locked test | 368 | 368 |
| long | 184 | 184 |
| replication | 184 | 184 |
| random controls | 736 | 736 |

The shared shortlist contained 288 coordinates: 114 selected for opening-token effects, 119 for later-position effects and 56 sampled randomly (these groups can overlap). 118 coordinates were selected for later-position effects without also being selected for opening-token effects. Screening measured positions 0, 8, 16, 32 and 64 along the same original-model continuation. Fine-dose probes used two additional normal continuations; free generation used four discovery prompts, eight fresh validation prompts, sixteen held-out prompts, eight longer prompts and eight replication prompts.

The intended readable finalist set is eight shared coordinates, assessed in both checkpoints. Both reviewers assessed each of these coordinates, and their responses passed format and evidence-reference checks. A selection error also advanced exploratory settings, giving eighteen total tested coordinates. The error, the validation-only reconstruction of the primary set, and the preserved extra measurements are documented in the [protocol](paired-qwen06-late-v1.md).

## Primary finalist outcomes

Doses are signed multiples of the original checkpoint calibration maximum. T = the Terra reviewer; S = the independent Sol reviewer. Matches are held-out /16, longer /8, replication /8. Repetition and collapse are separate flags over the 32 selected-condition neuron outputs. The gate permits at most two flags of each kind and requires both reviewers, the frozen hypothesis and validation criteria to pass.

| Coordinate | Model | Clamp target | Matches T | Matches S | Repetition (T, S) | Collapse (T, S) |
|---|---|---|---|---|---|---|
| L0-N262 | Original | +5× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (10, 12) | (2, 5) |
| L0-N262 | Abliterated | +5× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (11, 16) | (7, 10) |
| L5-N7 | Original | −15× | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | (2, 3) | (0, 0) |
| L5-N7 | Abliterated | −15× | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | (3, 4) | (1, 1) |
| L7-N92 | Original | +12× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (3, 7) | (0, 0) |
| L7-N92 | Abliterated | +12× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (4, 6) | (0, 0) |
| L7-N2500 | Original | +8× | 13/16 · 8/8 · 8/8 | 15/16 · 8/8 · 7/8 | (3, 2) | (1, 1) |
| L7-N2500 | Abliterated | +8× | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | (6, 7) | (4, 4) |
| L10-N400 | Original | −3× | 14/16 · 5/8 · 8/8 | 14/16 · 5/8 · 8/8 | (8, 9) | (2, 2) |
| L10-N400 | Abliterated | −3× | 14/16 · 5/8 · 8/8 | 14/16 · 5/8 · 8/8 | (6, 8) | (1, 1) |
| L11-N223 | Original | +12× | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | (4, 7) | (0, 1) |
| L11-N223 | Abliterated | +12× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (8, 11) | (1, 3) |
| L14-N178 | Original | −12× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (4, 5) | (1, 2) |
| L14-N178 | Abliterated | −12× | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | (4, 9) | (1, 3) |
| L15-N59 | Original | −12× | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | (3, 5) | (1, 1) |
| L15-N59 | Abliterated | −12× | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | (1, 3) | (0, 0) |

The closest reviewer disagreements were:

- Original L5 N7 at −15×: Terra passed it; Sol flagged three repetitive cases, above the two-case limit.
- Abliterated L15 N59 at −12×: Terra passed it; Sol likewise flagged three repetitive cases.
- Original L7 N2500 at +8×: Sol passed the support/help shift; Terra flagged three repetitive cases.

The thresholds were not changed after seeing these results. For the Chinese-language primary settings, the reviewers usually found no matching random-direction cases among the 32 controls at that setting. For the support shift at L7 N2500, both cited 3/32 original-model controls; the abliterated counts were 1/32 (Terra) and 4/32 (Sol). These are finite rubric judgments, not significance estimates or proof that a coordinate uniquely encodes a behavior.

## Catalogue coverage and missing assessment

The 38 records comprise 16 with status “Tested observation”, 18 with status “Exploratory tested observation”, 2 with status “Validation observation”, 2 with status “Final review incomplete”. Exploratory outputs included punctuation/fragment collapse, prompt echo, repeated questions, imagined correction narratives and food/storage substitutions. They remain available as measured observations rather than being described as coherent stable modes.

Exploratory L1 N1418 has no accepted Terra final review: both replies used random-control IDs in a neuron-only diagnostic field. Both were rejected and preserved. Sol completed all eighteen bundles, but that does not substitute for the missing Terra assessment. The two checkpoint records are explicitly marked “Final review incomplete.” No extra semantic retries were granted.

## Data provenance and limits

The independent audit linked 34,544 generation pairs to completed raw jobs, checked the full coordinate grid, job identities, SQLite integrity, frozen worker hashes, unchanged recovery sources, reviewer wire/reference hashes and winning raw responses. It also checked the primary/exploratory selection correction and explicit review gaps. These checks establish evidence linkage and consistency; the language-model ratings remain fallible judgments.

- Terra: 324 accepted review bundles; 330 requests counted against a 700-request ceiling.
- Sol: 18 accepted review bundles; 18 requests counted against a 100-request ceiling.

Rejected over-limit requests remain counted. One separate historical transport diagnostic was used before the new campaign and is excluded from its discoveries.

Numerical coverage is exhaustive for the declared coordinate/dose grid. Behavioral coverage is a finite sample: the broad screen used one normal prompt and a shared teacher-forced prefix, and only a shortlist received free generation. Later-position screening can expose effects missed by the first token, but cannot guarantee discovery of every trajectory-dependent mode. Token caps, greedy decoding, BF16 rounding and a small calibration set limit generalization. Both models used the original chat template and original activation scale. The comparison concerns these two pinned checkpoints; it does not isolate abliteration as the sole cause of any difference.

[Browse the catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · [Independent audit](../site-source/evidence/paired-qwen06-late-v1/independent-audit.json) · [Paired outcomes](../site-source/evidence/paired-qwen06-late-v1/comparison.json)
