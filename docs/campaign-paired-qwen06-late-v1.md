# Paired Qwen3-0.6B campaign results

The campaign completed **914,288 measured jobs** across Qwen3-0.6B and its Huihui abliterated v2 variant. All 86,016 MLP coordinates in each checkpoint were screened. The catalogue contains 38 new observations across 19 shared coordinates. **0 passed the full stability gate under both reviewers.**

The clearest recurrent changes were English-to-Chinese responses and generic support/help replies displacing the requested answer. These are substantial qualitative changes. Repetition and occasional collapse prevented stable-mode certification at the tested doses. A failed gate does not erase the observed change.

## Scope and evidence

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

The shared shortlist contained 288 coordinates: 114 early, 119 late, 56 random route memberships (memberships can overlap). 118 coordinates entered through a late-position route without an early-position route. Screening measured positions 0, 8, 16, 32 and 64 along the same original-model continuation. Fine-dose probes used two additional normal continuations; free generation used four discovery prompts, eight fresh validation prompts, sixteen held-out prompts, eight longer prompts and eight replication prompts.

The intended readable finalist set is eight shared coordinates, assessed in both checkpoints. All received accepted Terra and independent Sol final reviews. The zero-quota selection defect also advanced exploratory settings at eighteen total tested coordinates; the validation-only reconstruction and preserved extra measurements are documented in the [protocol](paired-qwen06-late-v1.md).

## Primary finalist outcomes

Doses are signed multiples of the original checkpoint calibration maximum. T = Terra; S = Sol. Matches are held-out /16, longer /8, replication /8. Repetition and collapse are separate flags over the 32 selected-condition neuron outputs. The gate permits at most two flags of each kind and requires both reviewers, the frozen hypothesis and validation criteria to pass.

| Coordinate | Model | Dose | Matches T | Matches S | Repetition T/S | Collapse T/S |
|---|---|---|---|---|---|---|
| L0-N262 | Original | p5 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 10/12 | 2/5 |
| L0-N262 | Abliterated | p5 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 11/16 | 7/10 |
| L5-N7 | Original | n15 | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | 2/3 | 0/0 |
| L5-N7 | Abliterated | n15 | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | 3/4 | 1/1 |
| L7-N92 | Original | p12 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 3/7 | 0/0 |
| L7-N92 | Abliterated | p12 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 4/6 | 0/0 |
| L7-N2500 | Original | p8 | 13/16 · 8/8 · 8/8 | 15/16 · 8/8 · 7/8 | 3/2 | 1/1 |
| L7-N2500 | Abliterated | p8 | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | 6/7 | 4/4 |
| L10-N400 | Original | n3 | 14/16 · 5/8 · 8/8 | 14/16 · 5/8 · 8/8 | 8/9 | 2/2 |
| L10-N400 | Abliterated | n3 | 14/16 · 5/8 · 8/8 | 14/16 · 5/8 · 8/8 | 6/8 | 1/1 |
| L11-N223 | Original | p12 | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | 4/7 | 0/1 |
| L11-N223 | Abliterated | p12 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 8/11 | 1/3 |
| L14-N178 | Original | n12 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 4/5 | 1/2 |
| L14-N178 | Abliterated | n12 | 16/16 · 8/8 · 8/8 | 16/16 · 8/8 · 8/8 | 4/9 | 1/3 |
| L15-N59 | Original | n12 | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | 3/5 | 1/1 |
| L15-N59 | Abliterated | n12 | 15/16 · 8/8 · 8/8 | 15/16 · 8/8 · 8/8 | 1/3 | 0/0 |

The closest reviewer disagreements were:

- Original L5 N7 at −15×: Terra passed it; Sol flagged three repetitive cases, above the two-case limit.
- Abliterated L15 N59 at −12×: Terra passed it; Sol likewise flagged three repetitive cases.
- Original L7 N2500 at +8×: Sol passed the support/help shift; Terra flagged three repetitive cases.

These decisions were retained without changing thresholds after seeing the results. For the Chinese-language primary settings, the reviewers usually found no matching random-direction cases among the 32 controls at that setting. For the support shift at L7 N2500, both cited 3/32 original-model controls; the abliterated counts were 1/32 (Terra) and 4/32 (Sol). These are finite rubric judgments, not significance estimates or proof that a coordinate uniquely encodes a behavior.

## Other observations and review gap

The 38 records comprise 16 with status “Tested observation”, 18 with status “Exploratory tested observation”, 2 with status “Validation observation”, 2 with status “Final review incomplete”. Exploratory outputs included punctuation/fragment collapse, prompt echo, repeated questions, imagined correction narratives and food/storage substitutions. They remain available as measured observations rather than being described as coherent stable modes.

Exploratory L1 N1418 has no accepted Terra final review: both replies used random-control IDs in a neuron-only diagnostic field. Both were rejected and preserved. Sol completed all eighteen bundles, but that does not substitute for the missing Terra assessment. The two checkpoint records are explicitly marked “Final review incomplete.” No extra semantic retries were granted.

## Audit and limits

The independent audit linked 34,544 generation pairs to completed raw jobs, checked the full coordinate grid, job identities, SQLite integrity, frozen worker hashes, unchanged recovery sources, reviewer wire/reference hashes and winning raw responses. It also checked the primary/exploratory selection correction and explicit review gaps.

- Terra: 324 accepted review bundles; 330 requests counted against a 700-request ceiling.
- Sol: 18 accepted review bundles; 18 requests counted against a 100-request ceiling.

Rejected over-limit requests remain counted. One separate historical transport diagnostic was used before the new campaign and is excluded from its discoveries.

Numerical coverage is exhaustive for the declared coordinate/dose grid. Behavioral coverage is a finite sample: the broad screen used one normal prompt and a shared teacher-forced prefix, and only a shortlist received free generation. Later-position screening can expose effects missed by the first token, but cannot guarantee discovery of every trajectory-dependent mode. Token caps, greedy decoding, BF16 rounding and a small calibration set limit generalization. Both models used the original chat template and original activation scale. The comparison concerns these two pinned checkpoints; it does not isolate abliteration as the sole cause of any difference.

[Browse the catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · [Independent audit](../site-source/evidence/paired-qwen06-late-v1/independent-audit.json) · [Paired outcomes](../site-source/evidence/paired-qwen06-late-v1/comparison.json)
