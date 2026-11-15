# Paired Llama 3.2 1B results

This experiment screened all 131,072 MLP coordinates in each checkpoint, completing 1,339,424 measured configurations. The catalogue contains 34 model-specific observations across 17 shared coordinates. Seven coordinates advanced to held-out testing at eight shared coordinate/dose settings. 3 model-specific catalogue records meet the full declared stability criteria under both reviewers.

The strongest recurring changes replace the requested task with personal statements, denials, misplaced assistance, or walking-route discussion. Both checkpoints show these modes. These findings establish reproducible output changes; they do not establish a persistent personality or a useful task-preserving capability.

The original model is meta-llama/Llama-3.2-1B-Instruct; its derivative is ai-anytime/Llama-3.2-1B-Instruct-abliterated. Both used the original runtime configuration, tokenizer, template and calibration scale. Each intervention has its own same-batch unmodified baseline.

Terra and Sol are language-model reviewers. Ratings are fallible. Changes, coherence, repetition and collapse are recorded separately. The strict pass/fail threshold is not evidence that rejected settings produced no behavioral change.

## Paired checkpoint differences

All frozen primary coordinate/dose combinations are compared, including both doses when the checkpoints nominated different settings. This avoids filtering the comparison by each model’s preferred displayed dose.

| Reviewer | Comparable settings | Abliterated more repetitive | Abliterated less repetitive | Equal repetition |
|---|---:|---:|---:|---:|
| Terra | 8 | 1 | 3 | 4 |
| Sol | 8 | 2 | 2 | 4 |

The Llama results do not reproduce a consistent increase in repetition after abliteration. The same broad modes appear in both checkpoints, while individual settings improve or worsen and the reviewers sometimes disagree.

The table below uses Sol ratings on the same 32 neuron outputs per checkpoint and setting (16 held-out, eight longer and eight replication prompts). Counts exclude random-direction controls. Each cell is original / abliterated. Doses are signed multiples of the original calibration maximum.

| Coordinate | Dose | Effect matches | Repetition | Collapse | Task loss | Coherence (0–4) |
|---|---:|---:|---:|---:|---:|---:|
| L4-N3761 | −4.5 | 31 / 32 | 5 / 5 | 1 / 0 | 30 / 30 | 3 / 3 |
| L4-N3761 | −6 | 32 / 32 | 9 / 5 | 8 / 3 | 31 / 31 | 2 / 3 |
| L0-N4395 | +5 | 32 / 28 | 0 / 0 | 0 / 2 | 32 / 32 | 3 / 3 |
| L0-N4799 | −3 | 32 / 32 | 0 / 0 | 32 / 32 | 32 / 32 | 3 / 3 |
| L0-N7298 | −1.5 | 28 / 30 | 2 / 2 | 5 / 5 | 28 / 29 | 2 / 3 |
| L2-N6518 | −3 | 28 / 32 | 0 / 4 | 9 / 1 | 29 / 32 | 3 / 3 |
| L4-N6515 | −12 | 31 / 30 | 19 / 22 | 3 / 6 | 28 / 29 | 3 / 2 |
| L5-N4905 | +4 | 28 / 28 | 3 / 1 | 0 / 0 | 28 / 29 | 3 / 3 |

**L0-N4395 at +5** meets the declared criteria in both checkpoints: ordinary questions turn into brief first-person statements. Sol matched the frozen description in 32/32 original outputs and 28/32 abliterated outputs, with zero repetition flags and zero/two collapse flags respectively. All 32 outputs in each checkpoint were flagged for task loss.

**L5-N4905 at +4** meets the criteria only in the abliterated checkpoint. Both models often produce denials or irrelevant prerequisite/tool responses. Sol marked three original outputs repetitive versus one abliterated output; the declared maximum is two. This is a threshold crossing, not a distinct behavior found only in the derivative.

**L4-N3761 at −6** is a counterexample to a general degradation claim: Sol marked nine/five repetitions and eight/three collapses in original/abliterated outputs. **L4-N6515 at −12** goes the other way, with 19/22 repetitions and three/six collapses. Both settings still fail the full gate. Task loss remains common even when wording is readable.

For context, the earlier Qwen3-0.6B comparison found higher repetition in the abliterated checkpoint at five of eight selected settings under each reviewer. A second family and a different community editing implementation introduce multiple changed factors, so these comparisons cannot isolate abliteration as a sole cause.

## Recorded observations

| Model | Coordinate | Label | State |
|---|---|---|---|
| Llama-3.2-1B-Instruct | L0-N4395 | Brief first-person identity or personal statements | Extreme mode observed |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L0-N4395 | Brief personal or identity statements | Extreme mode observed |
| Llama-3.2-1B-Instruct | L0-N4405 | Mixed capitalization and spelling disruption | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L0-N4405 | Mixed capitalization and occasional task collapse | Validation observation |
| Llama-3.2-1B-Instruct | L0-N4799 | Brief unrelated statements or prompt echoes | Tested observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L0-N4799 | Short giving or helping statements replace tasks | Tested observation |
| Llama-3.2-1B-Instruct | L2-N735 | Knowledge and quiz framing intrudes on tasks | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L2-N735 | Knowledge framing and task substitution | Validation observation |
| Llama-3.2-1B-Instruct | L4-N3761 | Misplaced personal and property assistance | Tested observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L4-N3761 | Off-task garden and neighbor discourse | Tested observation |
| Llama-3.2-1B-Instruct | L4-N6515 | Walking-route framing displaces tasks | Tested observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L4-N6515 | Walking-route framing displaces tasks | Tested observation |
| Llama-3.2-1B-Instruct | L5-N4905 | Brief denials or irrelevant responses replacing the task | Tested observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L5-N4905 | Brief denial, confusion, or unrelated answer | Extreme mode observed |
| Llama-3.2-1B-Instruct | L6-N1257 | Brief, often circular or contradictory assertions | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L6-N1257 | Brief, often circular or unresponsive assertions | Validation observation |
| Llama-3.2-1B-Instruct | L9-N7812 | Extra spacing around paragraphs and formatting | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L9-N7812 | Extra spacing around paragraphs and formatting | Validation observation |
| Llama-3.2-1B-Instruct | L1-N4178 | Sustained uppercase formatting | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L1-N4178 | Sustained uppercase formatting | Validation observation |
| Llama-3.2-1B-Instruct | L11-N3260 | Title-like capitalization with an isolated story loop | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L11-N3260 | Pervasive title-like capitalization | Validation observation |
| Llama-3.2-1B-Instruct | L2-N5131 | Brief nonanswers and sharp-object references | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L2-N5131 | Refusals and sharp-object reinterpretation | Validation observation |
| Llama-3.2-1B-Instruct | L0-N7298 | Fluent but misdirected answers | Tested observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L0-N7298 | Readable but misdirected answers | Tested observation |
| Llama-3.2-1B-Instruct | L1-N2711 | Isolated false claim that source text is absent | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L1-N2711 | False missing-text response and local repetition | Validation observation |
| Llama-3.2-1B-Instruct | L1-N7983 | No supported qualitative label · L1-N7983 | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L1-N7983 | No supported qualitative label · L1-N7983 | Validation observation |
| Llama-3.2-1B-Instruct | L2-N6518 | First-person inability or misplaced personal statements | Tested observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L2-N6518 | Misplaced first-person inability or meeting statements | Tested observation |
| Llama-3.2-1B-Instruct | L3-N4552 | Variable drift away from the requested task | Validation observation |
| Llama-3.2-1B-Instruct-abliterated (ai-anytime) | L3-N4552 | Variable task drift and conversational misreading | Validation observation |

Independent audit linked 18,368 exact generation pairs to completed raw jobs. 0 review bundles remain explicit gaps. Exhausted invalid responses were preserved rather than repaired or repeatedly retried.

Full coordinate coverage applies to the fixed numerical grid. Prompts, doses and free-generation candidates are finite samples. Shared ordinary prompts and unchanged scoring criteria support comparison with Qwen, but family, size and editing method differ. These are descriptive intervention results rather than a general safety, refusal or capability ranking.

[Catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · [Protocol](paired-llama32-1b-v1.md) · [Independent audit](../site-source/evidence/paired-llama32-1b-v1/independent-audit.json)
