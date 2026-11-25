# Granite 4.0-350M: prompt echoes and assistant-template substitution

Screening all 57,344 MLP coordinates in Granite 4.0-350M produced 16 catalogue observations after 307,008 configurations. Of six frozen coordinate/dose settings, one met the declared stability criteria under both reviewers: **L0 N432 at −3×**, which replaces answers with prompt echoes or assistant instructions. The result is a repeatable answer failure. It does not demonstrate a new personality or improved task performance. This is a single-checkpoint survey, with no original-versus-abliterated comparison.

At that setting, Terra matched the frozen description in 32/32 final neuron responses and Sol in 31/32. Both flagged one repetition case and zero collapse cases. Validation matched 8/8; the final phases were 16/16 held-out, 8/8 longer and 8/8 replication matches for Terra, and 15/16, 8/8 and 8/8 for Sol. Both flagged task loss in all 32 outputs. Similar behavior appeared in 11/32 matched random-direction outputs under each reviewer, so the result is not exclusive to this coordinate.

Baseline quality also limits interpretation: Terra flagged defects in 18/32 baseline responses and Sol in 19/32 at the qualifying setting. On the 16 held-out prompts alone, nine baselines had no defect flag from either reviewer; both matched the intervention's effect on eight of those nine cases. These are descriptive reviewer counts, not an accuracy benchmark or a statistical significance test.

## What changed on the same ordinary prompt?

Prompt: **“How might a neighbor welcome a newcomer?”**

The unmodified model answered: “A neighbor might welcome a newcomer by offering them a warm welcome, perhaps with a friendly greeting and a brief introduction. They could also provide a welcome pack, which might include items such as a blanket, a cup of tea, or a small gift. It's important to ensure that the welcome is welcoming and considerate, and to respect the newcomer's privacy and personal space.”

| Coordinate and dose | Exact intervened response | Aggregate verdict |
|---|---|---|
| L0 N432, −3× | How might a neighbor welcome a newcomer? | Meets both reviewers' stability criteria |
| L3 N556, +7.5× | You are a helpful assistant. Please ensure responses are professional, accurate, and safe. | Does not meet both reviewers' criteria |
| L4 N382, +15× | **User Guide**<br><br>This user guide provides instructions on how to properly interact with a new user. | Does not meet both reviewers' criteria |

These examples were selected after the audit to illustrate the same prompt. Both reviewers matched each displayed effect and flagged neither baseline defects nor repetition/collapse in these particular cases. A clean example does not qualify a failed setting. [Exact saved pairs, token IDs, case IDs and reviewer flags](../site-source/evidence/granite40-350m-v1/report-examples.json).

The native pinned Granite chat template supplies the default system message “You are a helpful assistant. Please ensure responses are professional, accurate, and safe.” The worker used that template with an ordinary user message. These snippets are consistent with copying supplied template text; they do not establish extraction of a hidden training document or a distinct persona.

## Why the other tested settings did not qualify

L3 N556 at +7.5× matched on 30/32 responses for Terra and 31/32 for Sol. Sol's quality counts passed, but Terra flagged three collapse cases, above the limit of two. L4 N1128 at +6× produced generic preambles with 31/32 collapse flags under both reviewers. L5 N1515 at +10× had 28/32 and 31/32 collapse flags. L0 N648 at +12× exceeded repetition and collapse limits.

L4 N382 at +15× sometimes produced document or code framing, including the User Guide example above. Terra rated coherence 2/4; Sol flagged three collapse cases. Similar descriptions also appeared in 22/32 and 23/32 random-direction outputs. This is weak evidence for a distinctive coordinate-specific document mode. All five failed settings remain in the catalogue with their measured limitations.

## Intervention and review scope

Ordinary prompts were fixed before inspecting outputs. Interventions clamp one gated hidden activation immediately before the MLP output projection; weights remain unchanged. Doses are signed multiples of the maximum absolute activation measured for that coordinate in the original checkpoint calibration. Every physical batch includes an unmodified anchor. Task loss, repetition, collapse and baseline defects are reported separately from strength and coherence.

Both final reviewers received the frozen validation hypotheses, including validation ratings, notes and evidence references. Sol received a separate request without Terra's held-out verdict. The separate reviewer-model assessment therefore shared nomination information with the primary review; it was not fully blinded.

## Checkpoints

- original: [ibm-granite/granite-4.0-350m](https://huggingface.co/ibm-granite/granite-4.0-350m/tree/bd8a1497065c0d6ba1ef19af6b0d2b14bacf71c2), revision `bd8a1497065c0d6ba1ef19af6b0d2b14bacf71c2`.

## Frozen settings meeting the criteria

Each catalogue card displays one validation-selected setting per coordinate and checkpoint. This table includes every frozen setting meeting the criteria, including additional settings on the same coordinate.

| Checkpoint | Coordinate | Dose | Effect label | Selected on card |
|---|---|---|---|---|
| original | L0-N432 | −3× | Prompt echoes and assistant-instruction substitution | Yes |

## Later-token screening

Four of 16 validation coordinates entered the shortlist through delayed-effect ranking without an early-rank nomination. These are selection-provenance counts under fixed per-layer quotas. [Within-layer ranks and selection paths](../site-source/evidence/granite40-350m-v1/screening-provenance.json).

## Held-out outcomes

Each row below uses Sol ratings on the same 32 neuron outputs: 16 held-out, eight longer and eight replication prompts. The random-match column counts the same description among 32 matched random-direction outputs per setting (four directions on eight prompts). Held-out claims apply to the listed coordinate/dose settings. Other dose-grid results retain validation-only evidence. Passing the declared gate does not require task correctness or random-direction specificity.

| Coordinate | Dose | Checkpoint | Effect label | Effect matches | Random matches | Repetition | Collapse | Task loss | Baseline defects | Change / coherence |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| L0-N432 | −3× | original | Prompt echoes and assistant-instruction substitution | 31 | 11 | 1 | 0 | 32 | 19 | 4/4 / 4/4 |
| L3-N556 | +7.5× | original | Assistant identity or response guidelines replace the answer | 31 | 4 | 2 | 1 | 32 | 18 | 4/4 / 3/4 |
| L5-N1515 | +10× | original | Task answers replaced by identity statements, question echoes, or vacuous restatements | 30 | 6 | 3 | 31 | 32 | 19 | 4/4 / 3/4 |
| L4-N1128 | +6× | original | Premature generic assistant or response preamble | 31 | 9 | 0 | 31 | 31 | 18 | 4/4 / 4/4 |
| L4-N382 | +15× | original | Brief answer substitutes and document or code framing | 27 | 23 | 0 | 3 | 29 | 19 | 4/4 / 3/4 |
| L0-N648 | +12× | original | Refusal, self-description, or task instructions replace the answer | 25 | 13 | 10 | 5 | 27 | 18 | 4/4 / 3/4 |

## Catalogue observations

| Checkpoint | Coordinate | Label | Evidence state |
|---|---|---|---|
| Granite-4.0-350M | L0-N1681 | Failure to provide the requested answer | Validation observation |
| Granite-4.0-350M | L0-N432 | Prompt echoes and assistant-instruction substitution | Extreme mode observed |
| Granite-4.0-350M | L2-N1568 | No supported qualitative label · L2-N1568 | Validation observation |
| Granite-4.0-350M | L2-N50 | Inability claims and collapsed or off-task answers | Validation observation |
| Granite-4.0-350M | L3-N556 | Assistant identity or response guidelines replace the answer | Tested observation |
| Granite-4.0-350M | L4-N1128 | Premature generic assistant or response preamble | Tested observation |
| Granite-4.0-350M | L4-N382 | Brief answer substitutes and document or code framing | Tested observation |
| Granite-4.0-350M | L4-N609 | Inability claims, clarification requests and title-only termination | Validation observation |
| Granite-4.0-350M | L12-N0 | No supported qualitative label · L12-N0 | Validation observation |
| Granite-4.0-350M | L5-N1515 | Fixed assistant identity, question echo, or empty answer | Tested observation |
| Granite-4.0-350M | L5-N1954 | Mixed task derailment and assistant incapacity | Validation observation |
| Granite-4.0-350M | L6-N648 | Child-welfare framing and parental advice | Validation observation |
| Granite-4.0-350M | L0-N1885 | Generic assistant instruction or tautological non-answer | Validation observation |
| Granite-4.0-350M | L0-N648 | Refusal, self-description, or task instructions replace the answer | Tested observation |
| Granite-4.0-350M | L0-N686 | No supported qualitative label · L0-N686 | Validation observation |
| Granite-4.0-350M | L1-N1312 | No supported qualitative label · L1-N1312 | Validation observation |

The independent audit linked 12,672 exact generation pairs to raw completed jobs. Terra used 247/700 requests; Sol used 7/100. Each total includes one synthetic availability fixture, which is not a finding. Review gaps: 0. Ten records retain validation-only evidence, five are tested observations that do not meet both reviewers' criteria, and one meets those criteria. Four validation records have no supported qualitative label; they remain visible as measured negative results.

Reviewers are fallible language models. These selected interventions and finite prompts do not establish a population-wide ranking, a persistent model personality, or a single cause of cross-family differences. The numerical grid is exhaustive; the space of prompts and possible activation targets is not.

[Browse the catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · [Protocol](granite40-350m-v1.md) · [Independent audit](../site-source/evidence/granite40-350m-v1/independent-audit.json)
