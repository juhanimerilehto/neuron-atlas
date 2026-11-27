# Neuron Atlas

Explore what changes when a single MLP neuron in a small language model is clamped. The public atlas shows exact before-and-after responses to ordinary prompts, selected matched random-direction controls, and evidence from the original discovery, validation and held-out phases.

[Open the interactive atlas](https://juhanimerilehto.github.io/neuron-atlas/) · [Campaign report](docs/campaign-exhaust-qwen-v1.md) · [Re-review protocol](docs/extremity-rereview-protocol.md)

## Browse locally

With Node.js 20 or later, run `node serve.mjs` and open `http://127.0.0.1:8792`. `node scripts/check_public_snapshot.mjs` checks the evidence links and explorer under the GitHub Pages project path.

The public catalogue contains 356 observations across 9 model checkpoints. The paired Qwen 0.6B experiment produced 38 model-specific records across 19 shared coordinates after 914,288 measured configurations, including numerical screening and 34,544 paired generations. Both checkpoints showed language switches and support-oriented reframing. The abliterated checkpoint was more repetitive at several matched settings, with counterexamples where it improved. No primary setting met all prespecified stability criteria under both reviewers; this does not mean the interventions had no behavioral effect. [Qwen model comparison, results and limitations](docs/campaign-paired-qwen06-late-v1.md) · [Protocol and recorded deviations](docs/paired-qwen06-late-v1.md)

The completed Llama comparison screened all 131,072 coordinates in each checkpoint and finished 1,339,424 configurations. It adds 34 observations across 17 shared coordinates, with seven coordinates receiving held-out tests and independent Terra/Sol review. Three model-specific records meet the declared stability criteria: first-person statements in both checkpoints and denial/nonanswer responses in the derivative. These modes frequently abandon the requested task. Unlike the Qwen pair, Llama shows no consistent increase in repetition after abliteration across the eight matched settings. [Llama results and checkpoint differences](docs/campaign-paired-llama32-1b-v1.md) · [Protocol](docs/paired-llama32-1b-v1.md)

The completed LFM2.5-350M comparison screened all 73,728 coordinates in each checkpoint, finished 764,900 configurations and added 30 observations. Group-facilitation framing (L3 N2589, +9x) and abstract progress/collaboration discourse (L5 N4206, +15x) met the declared stability criteria in both checkpoints. Those are four frozen model/coordinate/dose conditions, represented by three passing preferred cards plus an additional qualified setting on one card. The modes frequently abandon the requested task. Diplomatic/military and agricultural takeovers also appear, with quality-limit failures retained. Eight of 15 validation coordinates came through delayed-effect ranking without an early nomination. [LFM results, examples and checkpoint differences](docs/campaign-paired-lfm25-350m-v1.md) · [Protocol](docs/paired-lfm25-350m-v1.md)

The completed dense Granite 4.0-350M survey screened all 57,344 coordinates, finished 307,008 configurations and added 16 observations. L0 N432 at −3x met both reviewers' stability criteria, replacing answers with prompt echoes or assistant instructions. Similar effects also appeared in 11/32 random-direction controls, and baseline defects were common. Other settings produced template-like preambles and document framing but missed quality limits. These are task failures, not evidence of a new personality; Granite has no abliterated comparison in this survey. [Granite results and exact same-prompt examples](docs/campaign-granite40-350m-v1.md) · [Protocol](docs/granite40-350m-v1.md) · [Campaign operations and cross-session handoff](docs/family-campaign-operations.md)

Eight featured Qwen3-1.7B effects have deeper evidence drawers. That earlier sweep screened 172,032 coordinates numerically and advanced 2,240 candidates to behavioral generation in the final sweep. The candidate index publishes one assessed setting per shortlisted coordinate. [Earlier campaign audit](site-source/evidence/extremity-rereview-v1/audit.json)

The LFM depth programme's first prospective study confirms diplomatic/military reframing at L2 N3420, +9x in both checkpoints. Terra and Sol each matched 29/32 fresh responses per checkpoint, with zero collapse flags and no matching random controls; task loss was frequent. The catalogue adds two separately identified confirmation records, preserving the older dose-specific findings. Bounded dose, sampling, timing and neuron-combination inquiries follow. [Confirmation results and exact examples](docs/campaign-lfm-depth-20261127-v1-01-confirm-p9.md) · [Frozen plan and research limits](docs/lfm-depth-20261127-v1.md) · [Cross-session operations](docs/lfm-followup-operations.md)

A supplementary [weight comparison](docs/lfm-weight-geometry.md) found 19 changed named tensors out of 148 in the LFM pair. L2 N3420's MLP weights are exactly shared; changes affect later MLP output matrices and attention/convolution output projections. Static vocabulary readouts align with some measured topic shifts, with their limits and full token lists retained. The unstarted timing and pair designs reserve edited-matrix regions as well as the confirmed early coordinate; this adaptation preserves their original sizes and ceilings.

## Run the reference worker

The reference campaign uses Windows and Python 3.10, with a compatible CPU or CUDA PyTorch build. Install PyTorch for your hardware, then run the commands below in that environment. The first test exercises intervention and journal semantics using a tiny randomly initialized model. The measured campaign downloads SmolLM2-135M-Instruct, runs a bounded bracket-onset experiment, and writes evidence under `campaigns/` and `dist/`.

```powershell

python -m pip install -r requirements-worker.txt psutil

python worker/test_reference.py

python worker/prepare_model.py

python worker/campaign.py

python scripts/audit_campaign.py

```

[Worker setup and measurement scope](docs/worker.md) · [Codex evidence contract](docs/llm-analysis.md) · [Qwen sweep protocol](docs/exhaust-qwen.md)

`worker/` and `engine/` contain the reference worker, batched inference and Codex analysis adapter. `extreme/`, `wide/`, `deep/`, `exhaust/` and `rereview/` include research implementations from the larger runs. Reproducing those runs requires their full campaign inputs and a separate CUDA and Codex setup. The public snapshot includes selected measurements and audit metadata.

## Catalogue updates

Run experiments off-site. Review each proposed snapshot, keep the exact model revision, intervention, stage, prompt, paired texts and controls, and retain the original case IDs. Keep evidence and its index in the same commit. The Pages workflow validates the snapshot and deploys the static explorer on updates to `main`.

The MIT license covers the project code and documentation. Model checkpoints are obtained separately under their upstream terms. The checked-in examples are experimental model outputs, including some violent language, factual errors and repetition.

