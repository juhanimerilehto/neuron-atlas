# Reference worker and first real campaign

Implemented 2026-11-03. The first campaign uses SmolLM2-135M-Instruct on CUDA in float32. Hardware probing found 128 GB system RAM, about 90 GB available, 16 CPU cores / 32 logical processors and an RTX 4070 with 12 GB VRAM. The desktop GPU had other activity, so available VRAM varied. A 135M model leaves substantial headroom for a correctness-first pilot.

## Reproduce

The reference environment is Windows, Python 3.10.9, torch 2.0.0+cu118, Transformers 4.44.2, NumPy 1.23.5. The local virtual environment inherits the host CUDA torch installation and installs model tooling locally. A different host must install a suitable CUDA or CPU PyTorch build explicitly; the worker selects CPU if CUDA is unavailable. The campaign lock currently uses Windows `msvcrt`; portability is future work.

```powershell
python -m venv --system-site-packages .venv
.venv\Scripts\python.exe -m pip install -r requirements-worker.txt
.venv\Scripts\python.exe worker/prepare_model.py
.venv\Scripts\python.exe worker/test_reference.py
.venv\Scripts\python.exe worker/campaign.py
.venv\Scripts\python.exe scripts/audit_campaign.py
node check-ui.mjs
node serve.mjs
```

`prepare_model.py` resolves the upstream revision and downloads only model/tokenizer data, including safetensors; remote model code is disabled. The first run is pinned to `12fd25f77366fa6b3b4b768ec3050bf629380bac`. For exact offline replay, retain the existing `campaigns/bracket-pilot-v1/model.json` and project cache. Do not rerun acquisition against a changed upstream revision in the same campaign: identity checks reject changed manifests. New model or code versions require a new campaign implementation/version. Source data and exact settings are in the exported manifest.

## What the worker does

- Registers the actual Llama-family MLP down projections and normalizes their output columns.
- Calibrates layer-output residual L2 norms at the last prompt token over eight fixed contexts. Records per-coordinate natural activation summaries.
- Checks zero-dose equivalence, hook removal, additive pre/post-projection equivalence, per-example batch masking and cached-decode replay against full recomputation at matched positions.
- Executes one unpadded example at a time, adding a signed fraction of the median calibrated residual norm to the last prompt position and each decode input. General padded batches are intentionally unsupported.
- Journals deterministic job identities in SQLite and writes results atomically before marking completion. A single-process file lock excludes another campaign owner. Failed or interrupted jobs can rerun; completed jobs return cached artifacts.
- Enforces at most 2,500 unique jobs and a 1,200-second dispatch deadline per invocation. Generation length is capped at 48 new tokens. The time budget prevents new dispatch after expiry; it cannot preempt an already running model call. A cumulative GPU-time or currency reservation scheduler is not implemented.

This is a bounded reference campaign, not the full distributed scheduler described in the architecture. No autonomous planner, remote control service, API analyzer or Codex subprocess is connected.

## Experimental scope

48 seeded neurons, 24 each from zero-based layers 15 and 22; doses −0.30, −0.15, +0.15, +0.30. Screening uses six discovery prompts. The target is the summed probability of token IDs 75 and 933 (the single tokens for `[` and ` [`), at the first response token. This excludes other possible bracket-prefixed tokens; it does not measure JSON validity or all list forms.

Two distinct neuron/dose candidates per layer are frozen before eight validation prompts are scored. Each is compared with sixteen deterministic random unit directions at the same layer, norm, dose and positions. The same controls can be reused for candidates sharing those settings. Three validation prompts receive greedy baseline, selected-dose and opposite-dose generations. Token IDs and termination status are saved. Full-vocabulary KL is computed on the shared first-token distribution; generation-time per-token logits are not retained in this pilot.

The catalogue shows absolute probability changes in percentage points, mean log-probability changes, positive-context counts, descriptive bootstrap intervals and coarse smoothed random-control exceedance. It keeps all selected observations, even when random controls compare favorably. No confirmatory significance, capability preservation, broad neuron function or independent replication is claimed. All generated outputs are escaped before display.

## Evidence and checks

`campaigns/bracket-pilot-v1/` contains the manifest, calibration, conformance, screen, frozen shortlist, random controls, job artifacts and summary. The SQLite journal and machine-local model path are ignored by Git; the committed JSON artifacts preserve the evidence. Published catalogue records link to their JSON evidence and the shared manifest/conformance report.

`scripts/audit_campaign.py` independently recomputes exported aggregates from saved measurements, checks job identity, verifies cache hits without executing inference, counts generated tokens and checks split separation. This is an artifact audit, not a second inference campaign. The automated UI harness checks logic and escaping; browser rendering remains unverified because browser automation is disabled in this workspace.
