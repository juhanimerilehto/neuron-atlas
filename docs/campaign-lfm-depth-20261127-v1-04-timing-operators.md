# LFM timing: arithmetic becomes a workshop plan after prompt-only clamping

Clamping **L3 N2589 at +15x during the prompt only** frequently redirected ordinary questions into structured group-facilitation scenarios. Terra and Sol each matched **31/32** original-checkpoint responses; the edited checkpoint matched **30/32** under Terra and **29/32** under Sol. The neuron was no longer clamped during cached response generation.

Neither checkpoint met the full frozen stability criterion. Terra flagged zero collapse cases and passed its final criterion; Sol flagged **32/32 collapse cases in each checkpoint**, explicitly using collapse to mean convergence onto a narrow scenario/template family, separately from readability. Both reviewers supported the description, rated coherence at least 3/4, and flagged task loss in **32/32** responses in each checkpoint. This is a frequent genre takeover with a substantial quality-definition disagreement, not a quality-preserving arithmetic or question-answering improvement. The criteria require both reviewers; their flags remain unchanged.

The study measured **13,056 configurations**, 6,528 per checkpoint, and adds **24 assessed profile records**: six final-tested observations that did not qualify and eighteen validation-only observations. No final setting met every criterion. This extends earlier group-facilitation observations to another intervention schedule; it does not establish another exclusive semantic neuron or a distinct new personality.

## What was tested

Six coordinates received thirteen operator settings across five schedules: **390 discovery profiles**, each generated on sixteen ordinary prompts per checkpoint. The coordinates were L2 N3420, L13 N4194, L10 N4198, L2 N3030, L3 N2589 and L3 N2550. L2 N3420 +9x was forced into the pool; two sites came from layers with edited W2 matrices. Candidate choices use earlier validation, not held-out ratings. The [frozen manifest](../site-source/evidence/lfm-depth-20261127-v1/04-timing-operators/manifest.json) retains the full grid and input/source hashes.

Clamps replace an activation with a constant factor of its saved original-calibration sample maximum. Additive offsets use that same unit; scaling multiplies the current activation. These are different interventions, with different write magnitudes. [Exact definitions](lfm-depth-20261127-v1.md).

| Schedule | Intervention positions |
|---|---|
| Prompt and response | All unpadded prompt and cached decode positions |
| Prompt only | All unpadded prompt positions, including the prediction of response token 1 |
| Decode only | Starting with the prediction of human response token 2 |
| Bounded window | Predictions of human response tokens 9-24 |
| Single pulse | Prediction of human response token 17 |

Prediction indices in saved traces are zero-based. A prompt-only intervention can alter the prompt cache and generated-token history; persistence in a continuation does not by itself establish a self-sustaining internal attractor or a permanent weight change. Model weights were unchanged.

Twelve profiles advanced to eight fresh validation prompts. Three reached sixteen held-out, eight longer and eight replication prompts, plus four seeded random directions on eight prompts per setting/checkpoint. The additive candidate remained validation-only. No bounded-window or pulse profile advanced to validation under the frozen nomination rule. Their absence from the shortlist is not evidence that those schedules cannot produce an effect: all discovery assessments remain in the condition-review download. The grid is exploratory, and only selected profiles received later confirmation.

## Results, including settings that stopped after validation

| Checkpoint | Profile | Validation | Terra / Sol final matches | Terra / Sol repetition | Terra / Sol collapse | Terra / Sol random matches | Stability criteria |
|---|---|---:|---:|---:|---:|---:|---|
| original | clamp; all; L2-N3420; value 11.25 | 8/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L2-N3420; value 11.25 | 8/8 | — | — | — | — | Validation only |
| original | clamp; all; L3-N2589; value -15 | 8/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L3-N2589; value -15 | 8/8 | — | — | — | — | Validation only |
| original | clamp; prompt; L2-N3420; value 9 | 4/8 | 17 / 16 | 2 / 3 | 0 / 1 | 0 / 0 | Not met |
| abliterated | clamp; prompt; L2-N3420; value 9 | 4/8 | 15 / 15 | 2 / 4 | 0 / 0 | 0 / 0 | Not met |
| original | add; prompt; L10-N4198; value 3 | 2/8 | — | — | — | — | Validation only |
| abliterated | add; prompt; L10-N4198; value 3 | 2/8 | — | — | — | — | Validation only |
| original | scale; decode; L10-N4198; value 4 | 5/8 | 16 / 19 | 6 / 5 | 0 / 0 | 0 / 0 | Not met |
| abliterated | scale; decode; L10-N4198; value 4 | 6/8 | 18 / 19 | 5 / 5 | 1 / 0 | 0 / 0 | Not met |
| original | scale; all; L10-N4198; value 4 | 6/8 | — | — | — | — | Validation only |
| abliterated | scale; all; L10-N4198; value 4 | 6/8 | — | — | — | — | Validation only |
| original | clamp; prompt; L3-N2589; value 15 | 8/8 | 31 / 31 | 2 / 2 | 0 / 32 | 0 / 0 | Not met |
| abliterated | clamp; prompt; L3-N2589; value 15 | 8/8 | 30 / 29 | 1 / 1 | 0 / 32 | 0 / 0 | Not met |
| original | clamp; all; L2-N3030; value -15 | 8/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L2-N3030; value -15 | 7/8 | — | — | — | — | Validation only |
| original | clamp; all; L2-N3420; value 9 | 7/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L2-N3420; value 9 | 7/8 | — | — | — | — | Validation only |
| original | clamp; prompt; L2-N3030; value -18.75 | 6/8 | — | — | — | — | Validation only |
| abliterated | clamp; prompt; L2-N3030; value -18.75 | 7/8 | — | — | — | — | Validation only |
| original | clamp; all; L10-N4198; value 3 | 6/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L10-N4198; value 3 | 7/8 | — | — | — | — | Validation only |
| original | clamp; decode; L10-N4198; value 3 | 5/8 | — | — | — | — | Validation only |
| abliterated | clamp; decode; L10-N4198; value 3 | 5/8 | — | — | — | — | Validation only |

Final-match, repetition and collapse totals have denominator 32; slashes separate Terra and Sol. Random-match totals also have denominator 32, from four directions reused across eight prompts, not 32 independent directions. All six final checkpoint/settings had zero matching random-control outputs under both raters. That does not establish exclusive neuron semantics, and random specificity or task correctness is not part of the frozen stability gate.

The prompt-only L2 N3420 setting produced intermittent international-affairs framing but missed replication coverage and repetition limits; the edited checkpoint also missed held-out coverage. L10 N4198 scaling produced lexical corruption, list derailment or scattered language mixing and missed quality/coverage criteria. Its unchanged first token in all 32 cases per checkpoint follows from the decode-only schedule; it is not evidence that an already active first-token intervention went undetected.

The earlier [+9x throughout-the-response confirmation](campaign-lfm-depth-20261127-v1-01-confirm-p9.md) remains a separate result. This study used a different prompt panel, and the frozen descriptions for prompt-only reframing also differ by checkpoint. Their match totals are not a common-target, matched-prompt efficacy estimate across those studies. The all-position +9x and +11.25x settings here stopped after validation, with 7/8 and 8/8 matches in each checkpoint, respectively; they have no new held-out verdict in this study.

## Arithmetic becomes a meeting document

Prompt: **Calculate 38 plus 14.** Both unmodified checkpoints answered:

> 38 + 14 = 52

At L3 N2589 +15x, clamped only during prompt processing, the original checkpoint produced:

> **Background:**
> 
> The goal is to facilitate a productive and collaborative discussion among 38 participants, with 14 of them being facilitators. The meeting aims to generate innovative ideas and solutions for a complex project.
> 
> **Objectives:**
> 
> 1. Foster a positive and inclusive environment.
> 2. Encourage open and honest communication.
> 3. Identify key themes and priorities.
> 4. Develop actionable ideas and solutions.
> 
> **Steps:**
> 
> 1. **Introduction (10 minutes):** Begin with a brief overview of the project and its goals. Explain the importance of collaboration and the role of facilitators.
> 
> 2. **Facilitator Preparation (15 minutes):** Share insights on effective facilitation techniques, such as active listening, clear communication, and managing group dynamics.
> 
> 3. **Theme Exploration (20 minutes):** Guide participants through a series of brainstorming sessions, encouraging them to explore different themes and ideas. Use prompts like "What if?" or "How might we?" to stimulate creativity.
> 
> 4. **Idea Generation (30 minutes):** Facilitate a round-robin sharing of ideas, allowing each participant to contribute without interruption. Use a simple framework like "First, I want to discuss..." to keep the conversation flowing.
> 

The edited checkpoint at the same setting produced:

> **Background:**
> 
> The goal is to facilitate a productive and collaborative discussion among 38 participants, with the aim of generating innovative ideas or solutions.
> 
> **Objectives:**
> 
> 1. Foster a positive and inclusive environment.
> 2. Encourage open and honest communication.
> 3. Identify potential areas of interest or expertise.
> 4. Develop a shared understanding of the problem or opportunity.
> 
> **Steps:**
> 
> 1. **Introduction:** Begin with a brief overview of the discussion topic and its significance.
> 2. **Icebreaker:** Use a simple icebreaker activity to help participants get to know each other and build rapport.
> 3. **Active Listening:** Encourage participants to listen actively and respond thoughtfully to each other's contributions.
> 4. **Identify Key Points:** Guide the conversation to focus on the most important and relevant information.
> 5. **Generate Ideas:** Use a brainstorming technique to generate a wide range of ideas, without judgment or criticism.
> 6. **Reflect and Connect:** Reflect on the generated ideas and connect them to the original problem or opportunity.
> 7. **Closure:** Summarize the key takeaways and ensure everyone has had a chance to contribute.
> 
> **Example:**
> 
> *Background*: A company is facing declining sales and

These are the complete captured steered texts. Both reached their **256-token cap**, so they are unfinished documents. Both reviewers matched the facilitation description, flagged task loss, and flagged neither repetition nor a baseline defect for these cases. Terra recorded no collapse; Sol recorded collapse under its template-convergence interpretation. [Exact case IDs, texts, termination states and flags](../site-source/evidence/lfm-depth-20261127-v1/04-timing-operators/report-examples.json).

## Quality disagreement and checkpoint comparison

Sol's notes explicitly distinguish narrow scenario/template convergence from unreadable looping. Terra treats these responses as coherent but redirected tasks. Their different collapse flags coexist with high coherence scores; the report does not relabel either judgment, average them away or claim a passed gate. A future quality-codebook study could distinguish within-response degeneration from across-prompt template fixation. That proposal is separate from this frozen study.

For the same facilitation description, Terra matches the same 29 prompts in both checkpoints and Sol the same 28, with a few different exceptions. Both flag task loss on every prompt in both checkpoints. The broad similarity and small differences are descriptive, not evidence of a general abliteration benefit or a localized causal role for the edited weights. Across the final profiles, baseline defects were flagged in 8-22 of 32 cases depending on condition and reviewer. [All outcomes](../site-source/evidence/lfm-depth-20261127-v1-04-timing-operators/outcomes.json) and [paired flag contingencies](../site-source/evidence/lfm-depth-20261127-v1/04-timing-operators/paired-checkpoint-comparison.json) retain these separately.

## Independent execution checks and limits

The numerical audit linked all **13,056 pairs** to completed raw jobs and replayed accepted review evidence. All discovery, validation and final reviews passed schema/evidence checks on their first attempt; there are **no review gaps**. Schema validity does not establish semantic accuracy.

A separate post hoc [exposure-integrity check](../site-source/evidence/lfm-depth-20261127-v1/04-timing-operators/posthoc-exposure-check-v1.json) passed all 13,056 pairs with zero failures. All **624 cases with no recorded intervention** had identical baseline/steered tokens and text. All **7,024 cases with a nonempty prefix before the first recorded intervention** matched the baseline on that prefix. Recorded positions also respected their requested schedules. These counts include neuron and random-control cases across phases; they are not independent population samples or behavioral-success counts. The check complements the earlier exact cached manual-hook preflight, rather than measuring hidden activation amplitude independently.

Assigned cases stay in their denominators even if a response ends before a late schedule. The accepted-condition index includes recorded exposure counts. All three final profiles recorded exposure in 32/32 neuron cases per checkpoint. [Saved-token opening comparisons](../site-source/evidence/lfm-depth-20261127-v1/04-timing-operators/posthoc-token-prefix-v1.json) are descriptive, not semantic-onset estimates.

This adaptive study was frozen locally before measurement. Prompt strings are disjoint across partitions but share templates; replication is another prompt partition under greedy BF16 decoding, not a temperature- or model-revision robustness claim. A/B aliases conceal checkpoint identity, and final reviewers see frozen descriptions without earlier scores, notes or each other's assessments. The next pair study has its own publicly frozen plan and is a separate experiment. [Programme protocol](lfm-depth-20261127-v1.md).
