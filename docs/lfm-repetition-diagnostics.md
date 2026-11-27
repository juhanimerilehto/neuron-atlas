# LFM repetition: literal tokens and reviewer judgments

This supplementary analysis measures repetition in already saved generated tokens. It makes no new model calls, changes no acceptance threshold and does not adjudicate the reviewers. It covers the final catalogue conditions in the first three depth studies: 18 checkpoint/settings, each with 32 neuron responses and 32 random-direction controls. Auxiliary single-neuron arms of later pair studies are outside this summary.

For a sequence with at least four tokens, the **duplicate fourgram fraction** is `1 - distinct contiguous token fourgrams / total contiguous token fourgrams`. Overlapping fourgrams count. A sequence of eight identical tokens scores 0.8; a sequence with no repeated fourgram scores zero. Sequences shorter than four tokens have a null value. Separate fields retain the same statistic on the last at most 64 tokens, the longest consecutive run of one token ID, lengths, termination states and the original reviewer flags.

The table shows medians over all 32 neuron responses per condition, not only successful examples. Percentages express the duplicate fourgram fraction. The first study uses a different prompt partition from the dose study; comparisons across those studies are descriptive.

| Study / coordinate / clamp | Checkpoint | Median baseline tokens | Median steered tokens | Baseline duplicate fourgrams | Steered duplicate fourgrams |
|---|---|---:|---:|---:|---:|
| Confirmation / L2 N3420 +9x | Original | 256 | 207 | 0.20% | 0.20% |
| Confirmation / L2 N3420 +9x | Edited | 256 | 121 | 0.00% | 0.00% |
| Dose / L2 N3420 +10.5x | Original | 197 | 178 | 0.40% | 1.16% |
| Dose / L2 N3420 +10.5x | Edited | 173.5 | 103 | 0.00% | 0.00% |
| Dose / L2 N3420 +15x | Original | 197 | 74 | 0.40% | 12.14% |
| Dose / L2 N3420 +15x | Edited | 173.5 | 50.5 | 0.00% | 2.07% |
| Dose / L2 N3030 -15x | Original | 197 | 123 | 0.40% | 0.40% |
| Dose / L2 N3030 -15x | Edited | 173.5 | 132.5 | 0.00% | 0.00% |
| Broader candidates / L13 N4194 +6x | Original | 233.5 | 209 | 0.00% | 0.79% |
| Broader candidates / L13 N4194 +6x | Edited | 176 | 188.5 | 0.00% | 0.57% |

In the matched dose-study prompts, +15x at L2 N3420 has a higher median duplicate fraction than +10.5x in each checkpoint. That agrees descriptively with a quality deterioration, but it is not a new significance test or an independent confirmation: these are the same outputs the reviewers read.

Low literal repetition does not establish good behavior. Agricultural takeover at L2 N3030 -15x has low median duplicate fractions despite Sol flagging collapse in 28/32 responses in each checkpoint. The L13 N4194 question/fragment setting also has a low median fourgram score despite many repetition flags. Recurrent meanings, grammatical fragments and task abandonment need not repeat identical four-token strings. Conversely, ordinary lists and formatting can repeat strings without collapsing. Medians can also conceal a minority of severe loops.

Lengths, tokenization, special tokens and termination caps affect these statistics. The 32 neuron responses mix held-out, longer and replication partitions, with different caps. A shorter output can have fewer opportunities for repeated phrases while still failing its task. Baselines and random directions are reused; rows are not independent samples from a population. No healthy/unhealthy threshold is introduced.

The immutable outputs include per-case measurements and flags, not just these medians:

- [Prospective +9x confirmation](../site-source/evidence/lfm-depth-20261127-v1/01-confirm-p9/posthoc-repetition-v1.json)
- [Fine doses](../site-source/evidence/lfm-depth-20261127-v1/02-dose-response/posthoc-repetition-v1.json)
- [Broader candidates](../site-source/evidence/lfm-depth-20261127-v1/03-missed-candidates/posthoc-repetition-v1.json)

Each file binds its analysis source, raw paired-output file, reviewer analyses and numerical audit by SHA-256. The [read-only implementation](../scripts/lfm_repetition_diagnostics_v1.py) never invokes a generator or reviewer. Existing frozen verdicts and reviewer disagreements remain visible in the study reports.
