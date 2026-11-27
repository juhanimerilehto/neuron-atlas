# LFM broader candidates: intermittent French and late repetitive drift

The broader search found **no new setting that met all frozen stability criteria**. L1 N4341 at -12x switched some English responses into French in both checkpoints. L13 N4194 at +6x, sampled from a previously ungenerated coordinate, produced repeated questions and fragments but failed quality limits. L3 N2550 at -8x produced abstract task drift that also appeared frequently under random-direction controls. These are useful counterexamples and leads, not reliable new modes.

The study measured **10,096 configurations**, 5,048 per checkpoint: 4,784 discovery generations, 72 validation generations and 192 held-out/longer/replication/control generations. It adds **18 assessed profile records**: six final-tested observations that did not qualify and twelve validation-only observations. Earlier records and verdicts remain unchanged.

## What the broader sample covered

The frozen plan contained 42 unique coordinates: ten with rare effects in the parent study, sixteen seeded uniform draws (one per layer) from coordinates without parent discovery generation, and sixteen deliberately selected low-proxy coordinates. The latter minimize the worst early/late numerical impact across the two checkpoints, excluding the uniform draw and previously generated coordinates. The parent had generated responses for 147 coordinates and validated 15; parent validation coordinates were excluded from the rare-effect pool.

Each coordinate received zero and +/-3, +/-6 and +/-12 clamps, with earlier rare settings retained where outside that grid: **299 profiles** on 16 ordinary discovery prompts. Nine profiles advanced to eight fresh validation prompts. Three were frozen for 16 held-out, eight longer and eight replication prompts, with four seeded random directions on eight prompts per final profile and checkpoint. L1 N4341 and L3 N2550 came from the prior-rare pool; L13 N4194 was a uniform draw.

This is a conditional sample, not an estimate of how many effects exist among all coordinates. The low-proxy draws are intentionally nonrandom. Parent numerical screening used one original-checkpoint continuation prefix at five positions; this study changed both prompts and some doses and generated free continuations. Finding a change here does not isolate why the parent ranking missed it or establish a population false-negative rate. The [frozen manifest](../site-source/evidence/lfm-depth-20261127-v1/03-missed-candidates/manifest.json) records the sampling frame, seed and source hashes.

## Fresh tests and failures

| Checkpoint | Profile | Validation | Terra / Sol final matches | Terra / Sol repetition | Terra / Sol collapse | Terra / Sol random matches | Stability criteria |
|---|---|---:|---:|---:|---:|---:|---|
| original | clamp; all; L2-N926; value 12 | 1/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L2-N926; value 12 | 1/8 | — | — | — | — | Validation only |
| original | clamp; all; L13-N4194; value 6 | 5/8 | 16 / 21 | 15 / 17 | 5 / 9 | 0 / 0 | Not met |
| abliterated | clamp; all; L13-N4194; value 6 | 5/8 | 22 / 22 | 21 / 21 | 6 / 7 | 0 / 0 | Not met |
| original | clamp; all; L3-N2550; value -8 | 6/8 | 14 / 22 | 4 / 3 | 0 / 1 | 11 / 12 | Not met |
| abliterated | clamp; all; L3-N2550; value -8 | 5/8 | 14 / 22 | 3 / 2 | 0 / 1 | 10 / 12 | Not met |
| original | clamp; all; L4-N385; value -8 | 2/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L4-N385; value -8 | 3/8 | — | — | — | — | Validation only |
| original | clamp; all; L11-N1359; value 2 | 6/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L11-N1359; value 2 | 7/8 | — | — | — | — | Validation only |
| original | clamp; all; L1-N4341; value -12 | 3/8 | 9 / 10 | 3 / 7 | 0 / 0 | 0 / 0 | Not met |
| abliterated | clamp; all; L1-N4341; value -12 | 3/8 | 9 / 10 | 4 / 7 | 0 / 0 | 0 / 0 | Not met |
| original | clamp; all; L9-N3559; value 6 | 2/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L9-N3559; value 6 | 2/8 | — | — | — | — | Validation only |
| original | clamp; all; L4-N385; value 3 | 4/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L4-N385; value 3 | 3/8 | — | — | — | — | Validation only |
| original | clamp; all; L0-N3336; value 6 | 3/8 | — | — | — | — | Validation only |
| abliterated | clamp; all; L0-N3336; value 6 | 3/8 | — | — | — | — | Validation only |

All final-match, repetition and collapse totals have denominator 32; slashes separate Terra and Sol. Random matches also have denominator 32, from four directions reused on eight prompts. These are separate reviewer assessments, not averaged judgments.

- **Intermittent French, L1 N4341 -12x:** Terra matched the same 9/32 prompts in both checkpoints. Sol matched 10/32 in each, with nine shared matches. Validation was only 3/8 in each checkpoint, and final phase coverage and repetition also missed limits. Both reviewers supported the description, but neither checkpoint qualified. This is not a reliable French switch, nor evidence of an abliteration advantage.
- **Questions and fragments, L13 N4194 +6x:** the original matched 16/21 and the edited checkpoint 22/22 responses (Terra/Sol), but repetition affected 15/17 original and 21/21 edited outputs. Collapse and coherence limits also failed. Checkpoint-specific frozen descriptions differ, so match totals are not a common-target efficacy comparison. A post hoc saved-token check found the first greedy token unchanged in 31/32 original and 29/32 edited outputs. Many matched changes appeared after shared opening tokens, but those late changes were frequently degenerate.
- **Abstract task drift, L3 N2550 -8x:** final matches were 14/22 in each checkpoint. Terra missed phase-coverage and repetition criteria; Sol passed its final criterion only in the edited checkpoint. Both reviewers are required. Similar effects appeared in 10-12/32 random-control outputs per checkpoint/reviewer, weakening any claim that this description is specific to this neuron.

Baseline defects were common and reviewer-dependent: 7-22 of 32 baselines were flagged across these conditions. Task-loss flags remain separate. Passing stability would not establish task correctness or specificity. [Complete outcomes](../site-source/evidence/lfm-depth-20261127-v1-03-missed-candidates/outcomes.json) and the [prompt-matched checkpoint comparison](../site-source/evidence/lfm-depth-20261127-v1/03-missed-candidates/paired-checkpoint-comparison.json) retain all counts.

## One ordinary prompt, English before and French after

Prompt: **Why do some birds migrate each year?** Both checkpoints were clamped at L1 N4341 -12x. The following are exact opening excerpts, not complete responses.

Original baseline:

> Birds migrate each year for a variety of reasons, including:

Original steered:

> Certains oiseaux migrentent chaque année pour profiter des conditions climatiques plus favorables dans leurs régions d’origine.

Edited baseline:

> Birds migrate each year for a variety of reasons, including:

Edited steered:

> Les oiseaux migrentent chaque année pour plusieurs raisons, principalement liées à la recherche de nourriture, à l'évitement des conditions météorologiques défavorables et à l'exploration de nouvelles zones pour des habitats adaptés.

Both reviewers matched French switching and flagged neither steered example for repetition or collapse. Sol flagged the edited baseline as defective. The outputs include grammatical and factual problems; this illustration demonstrates a language change, not preserved factual accuracy. Full responses, termination states, case IDs and flags are in the [exact example file](../site-source/evidence/lfm-depth-20261127-v1/03-missed-candidates/report-examples.json). A selected example does not change the failed aggregate verdict.

## Audit, missing reviews and limits

The independent audit linked all **10,096 exact pairs** to completed raw jobs and replayed accepted review evidence. Discovery group L6 N461 part 0 exhausted two attempts: each claimed a behavioral change in an identical baseline/steered text. Its seven doses in both checkpoints remain unassessed, not negative findings. Original attempts are preserved locally; the [safe diagnosis](../site-source/evidence/lfm-depth-20261127-v1/03-missed-candidates/review-diagnostics-latest.json) records hashes and offending references. All validation and final review groups are complete.

This adaptive study was frozen locally before its measurements; it was not the programme's publicly preregistered +9x confirmation. Prompt strings are disjoint across partitions but share task templates. Generation is greedy in the pinned BF16 runtime. Replication uses another prompt partition, not a claim of robustness across sampling temperatures or model revisions. A/B aliases conceal checkpoint identity, and final reviewers see frozen descriptions without earlier scores, notes or each other's judgment. LLM assessments remain fallible. [Programme protocol](lfm-depth-20261127-v1.md).
