# Completed exhaustive Qwen neuron campaign

All 968,330 jobs completed; all ten shards passed database and archive-only audits. The uploader synchronized all 236 catalogue observations: 76 historical records preserved unchanged and 160 new measured observations. Initial MLP coordinate coverage is 172,032/172,032, including 137,026 newly screened coordinates.

Of 2,240 candidates given generated discovery ladders, 160 received validation and 60 frozen finalists received locked tests. Eight neuron interventions passed both Terra and Sol. Three were judged new relative to the fixed prior library; eight passing neurons do not mean eight distinct behavioral modes.

## Interventions that passed both reviewers

| Coordinate | Frozen mode | Setting | Novelty vs prior | Terra matches: test / long / replication | Sol test matches | Test repetition / selected degeneration flags |
| --- | --- | --- | --- | --- | --- | --- |
| L6-N5513 | Leadership and organizational-vision takeover | n8 | related_mode | 15/16 · 8/8 · 7/8 | 15/16 | 0 / 2 |
| L7-N3729 | Switching into Romance languages | p7.5 | related_mode | 13/16 · 8/8 · 6/8 | 13/16 | 0 / 0 |
| L6-N400 | Biomimetic tissue-engineering takeover | p8 | new_mode | 16/16 · 8/8 · 8/8 | 16/16 | 0 / 1 |
| L9-N5322 | Social influence and activation-process framing | n7.5 | new_mode | 13/16 · 8/8 · 7/8 | 15/16 | 0 / 2 |
| L14-N4183 | Romance-language switching | n8 | related_mode | 12/16 · 7/8 · 6/8 | 12/16 | 0 / 1 |
| L17-N1341 | Romance-language switching | n12 | related_mode | 13/16 · 8/8 · 7/8 | 13/16 | 1 / 1 |
| L8-N4135 | Environmental and social-values reinterpretation | n12 | related_mode | 16/16 · 8/8 · 5/8 | 16/16 | 0 / 0 |
| L6-N1218 | Camera settings and photography takeover | p3 | new_mode | 14/16 · 8/8 · 7/8 | 14/16 | 1 / 2 |

Settings `pX` and `nX` clamp the coordinate at plus or minus X times its calibration absolute maximum at all unpadded prompt/decode positions. These are strong inference-time interventions, not natural activation ranges or unique concept assignments.

The three new hypotheses are tissue-engineering exposition (L6 N400), social-influence/activation-process framing (L9 N5322), and photography/camera-settings exposition (L6 N1218). Each can displace the requested task, and its generated claims need not be correct. A pass permits limited repetition and degeneration. Their paired outputs and counterexamples remain in the catalogue.

## Reviewer usage

| Requested model, medium reasoning | Accepted reviews | Completed attempts | Reported input tokens | Reported output tokens |
| --- | --- | --- | --- | --- |
| gpt-6.1-terra | 320 | 325 | 65,069,131 | 1,529,143 |
| gpt-6.1-sol | 20 | 20 | 4,550,101 | 106,654 |

Includes completed invalid retries; excludes three historical calibration calls and unknown usage of the interrupted attempt. Cached input and reasoning are reported subcounts, not extra tokens. Codex billing is not inferred from API rates.
There were 326 Terra request records and 20 Sol request records: 340 accepted reviews, five completed invalid attempts, and one interrupted attempt without saved events. Invalid responses and retries are retained. Both explicitly requested model aliases, medium reasoning and CLI versions are recorded; immutable upstream checkpoints were unavailable.

## Audited batches

| Shard | Jobs | Passing neurons | New-mode neurons vs prior | Report |
| --- | --- | --- | --- | --- |
| 1 | 100,000 | 0 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s01.md) |
| 2 | 100,000 | 2 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s02.md) |
| 3 | 100,000 | 1 | 1 | [Evidence report](campaign-exhaust-qwen-v1-s03.md) |
| 4 | 100,000 | 0 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s04.md) |
| 5 | 100,000 | 4 | 1 | [Evidence report](campaign-exhaust-qwen-v1-s05.md) |
| 6 | 100,000 | 0 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s06.md) |
| 7 | 100,000 | 0 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s07.md) |
| 8 | 100,000 | 1 | 1 | [Evidence report](campaign-exhaust-qwen-v1-s08.md) |
| 9 | 100,000 | 0 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s09.md) |
| 10 | 68,330 | 0 | 0 | [Evidence report](campaign-exhaust-qwen-v1-s10.md) |

Initial coordinate coverage is not exhaustive prompt/dose coverage. Eight selected neurons passed a permissive exploratory gate; three were rated new only against the fixed 54-observation prior library. Shared prompts, adaptive selection, one checkpoint and fallible reviewer judgments limit generalization.

See the [protocol](exhaust-qwen.md) and [derived machine-readable completion report](../campaigns/exhaust-qwen-v1/completion-report.json). Canonical raw evidence and original analyses remain in the ten local campaign directories and owner-private managed catalogue storage.

The original overnight services stopped; their shutdown cause is unconfirmed. The detached resumed run completed on November 6 at 20:03 Helsinki time, and final catalogue synchronization completed at 20:06. The temporary system-awake request was released automatically.
