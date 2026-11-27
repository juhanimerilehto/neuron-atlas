# Shared openings before different model responses

The paired LFM outputs often start with the same generated token even when their continuations enter a different topic. This is a post hoc comparison of saved token IDs and accepted reviewer labels, without new inference or judgments.

| Study and setting | Checkpoint | Cases jointly matched to the geopolitical mode | Same first token among those cases | Shared prefix of at least eight tokens |
|---|---|---:|---:|---:|
| Prospective +9x confirmation | Original | 29 | 16 | 5 |
| Prospective +9x confirmation | Edited | 29 | 12 | 4 |
| Dose study, +10.5x | Original | 31 | 16 | 3 |
| Dose study, +10.5x | Edited | 31 | 16 | 1 |

Each profile has 32 ordinary test responses. Jointly matched means both reviewers assigned the frozen mode; it does not mean the case is free of baseline defects or quality flags. The +9x profiles meet the declared stability criteria in both checkpoints; +10.5x meets them only in the edited checkpoint. Their test panels differ. [Confirmation token-prefix data](../site-source/evidence/lfm-depth-20261127-v1/01-confirm-p9/posthoc-token-prefix-v1.json) · [Dose-study token-prefix data](../site-source/evidence/lfm-depth-20261127-v1/02-dose-response/posthoc-token-prefix-v1.json).

For example, a jointly matched +9x original-checkpoint response shares nine tokens with its baseline, beginning **“Preparing a small balcony for spring ”**, before their texts diverge. The saved analysis retains the exact case ID, prompt, common-token count and separate baseline/quality flag indicator. Shared text prefixes are computed from the actual strings; they are not obtained by decoding a possibly incomplete Unicode token sequence.

## What this establishes

An unchanged greedy opening token is compatible with a later behavioral shift. Inspecting that token alone cannot characterize the continuation. The campaign therefore generates full continuations and reviews complete paired text, including longer responses.

An unchanged chosen token does **not** imply an unchanged next-token probability distribution or zero Jensen–Shannon divergence. The numerical screen can notice probability shifts even when the highest-probability token stays the same. These selected profiles and new prompts also do not estimate the numerical screen's population miss rate. Likewise, the first differing token is an earliest lexical divergence, not a measurement of semantic onset; ordinary wording can change before a thematic shift becomes evident.

## The planned timing test goes further

The planned timing study includes decode-only, response-window and single-pulse interventions; its inputs and sources will freeze separately before measurements begin. Decode-only starts after the first response token is selected; a later window leaves a longer opening untouched by design. The study will measure whether an intervention applied later can still change the continuation, and retain responses that ended before the scheduled intervention as unexposed assigned cases. This describes the design, not an already completed timing result. [Programme protocol](lfm-depth-20261127-v1.md).
