# Exhaustive remaining-coordinate campaign

Requested 2026-11-05. Parent: `exhaust-qwen-v1`. Pinned local checkpoint: Qwen/Qwen3-1.7B revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`, BF16, SDPA, thinking disabled, greedy decoding.

## Coverage and fixed budget

Earlier pools contain 35,006 distinct coordinates. A fixed seeded partition assigns all other **137,026** coordinates exactly once across ten shards, without overlap with prior pools. The first nine shards contain 14,336 coordinates each; the final shard contains 8,002. Every layer is represented in every shard. Full coverage means initial coordinate screening, not exhaustive testing of each coordinate over all prompts and doses.

The budget is **968,330 stored measured jobs**: nine 100,000-job shards and one 68,330-job tail. All ten numerical screens and fine grids finish before full behavioral generation begins. Each shard then advances 224 neurons, validates sixteen, and freezes six finalists. Planned totals: 2,240 generated candidates, 160 validation observations and 60 locked-test finalists.

| Stage | Parent jobs |
| --- | ---: |
| Calibration | 160 |
| Broad numerical screen | 685,130 |
| Fine numerical screen | 76,160 |
| Discovery generation | 116,480 |
| Fine-dose validation | 6,400 |
| Locked tests | 2,880 |
| Longer continuations | 1,440 |
| Random-direction generation controls | 1,920 |
| Ordinary answer probes | 480 |
| Replication | 480 |
| Distribution controls | 76,800 |

Additional untouched anchor rows are recorded inside physical batches. Numerical preflight, post-run conformance and the three historical reviewer-calibration calls are separate diagnostics. There are 130,080 generation jobs and 838,090 distribution jobs.

## Prompts, doses and selection

The same fixed bank of 71 ordinary prompt strings is used across all ten shards for comparable coordinate coverage. Its calibration, broad/fine screen, discovery, validation, test, long, answer-probe and replication splits are distinct within each shard and absent from earlier campaign datasets. Shared prompts across shards are not claimed to be independent fresh datasets.

Each row clamps one pre-down-projection MLP coordinate at every unpadded prompt/decode position. Broad doses: off and ±4/±12 calibration maxima. Three moderate-dose divergence leaders, three distinct extreme-dose leaders and two random candidates per layer advance. All 224 receive off and ±0.5/1/2/3/4/6/8/12 on two fine-screen prompts. Each candidate then generates at off plus both signs of the six magnitudes nearest its largest fine-proxy divergence, on four normal discovery prompts. Validation tests the proposed signed dose at ×0.75/1/1.25, off and its original opposite; off proposals receive off and ±0.5/±1.

The prior-library snapshot is fixed at 54 Qwen observations from earlier campaigns. Newness is a fallible comparison with that finite snapshot. Cross-shard duplicates can occur; a new neuron observation is not necessarily a new distinct behavioral mode. Selection prefers strong non-length-only new hypotheses, then related modes, with no more than two candidates per layer. The six final hypotheses, settings and novelty judgments are frozen before tests.

## Explicit reviewers and independent confirmation

- Primary discovery, validation and final reviewer: **`gpt-6.1-terra`**, medium reasoning.
- Independent final-hypothesis confirmation: **`gpt-6.1-sol`**, medium reasoning.

Every CLI request explicitly supplies the model and reasoning effort. Model aliases, CLI version, schema, original responses, wire bundles and reference maps are retained. Resolved immutable upstream checkpoint identifiers are unavailable; selecting an explicit alias does not prevent upstream alias changes. Primary review hashes include the model and reasoning effort, so cached judgments cannot be reused across models accidentally.

Terra calibration on six historical finalists reproduced all six earlier pass/fail decisions. Sol independently matched its three sampled cases. These are small, non-independent checks, not general reviewer accuracy measurements. Earlier published judgments remain unchanged.

Two calls may run concurrently. Each shard admits at most forty Terra requests and four Sol requests, including invalid retries: **400 Terra and 40 Sol attempts maximum** for the parent, plus the three separate calibration calls. Invalid judgments stop the affected shard instead of becoming invented no-effect results. Codex-plan usage is not inferred from API dollar prices.

Both models must support the frozen mode for the new catalogue state “Extreme mode observed.” Requirements: named non-length-only Terra validation/test hypotheses rated at least 3/4; ≥4/8 validation, ≥8/16 locked-test, ≥4/8 long and ≥4/8 replication sustained matches; at most two heuristic test repetition flags; and at most two selected-condition degeneration flags. Sol independently applies the same held-out match, rating and degeneration requirements. Disagreements are retained. Two model judgments are not independent data replication or statistical confidence.

## Checkpoints and publication

`scripts/run_exhaust.py` owns a parent lock and invokes locked shard workers. Frozen source and plan hashes are checked before each child operation. SQLite admission limits and content-addressed IDs support resume. Audits independently reconstruct the entire partition, check job and archive identities, verify both models' explicit commands and evidence references, reproduce selection and both gate decisions, and check paired anchors and decoded tokens. Full logits are not retained for independent divergence recomputation.

Every shard must pass database and archive-only audits before export. `export-complete.json` is written last. The uploader transfers completed evidence before replacing the catalogue snapshot, preserves the original 76 records, checks byte hashes, and keeps credentials only in process memory. Evidence objects are immutable in managed storage; only the catalogue and progress snapshots are replaceable. The Site remains owner-private, using its existing supported service credential.

Web source and local evidence snapshots are in `site-source/`; canonical measurement journals and original analysis artifacts remain under `campaigns/`. Worker build output in `dist/` is generated. New large shard artifacts are stored locally and in managed Site storage rather than bundled into the static Git deployment. The frozen bootstrap catalogue keeps the existing 76 observations accessible while initial storage transfer runs.

The current run uses a temporary Windows system-use request through `scripts/keep_campaign_awake.py`, tied to its runner PID and bounded to twenty hours. It releases when that runner ends or reports completion/failure. It does not change the power plan or require the display to stay on. The implementation uses Microsoft's documented [SetThreadExecutionState API](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).

On 2026-11-06, inspection found the previous runner, uploader and sleep guard absent. Their last saved campaign progress was around 21:14 Helsinki time on November 5; the shutdown cause is unconfirmed. All initial numerical screens and 18 accepted Terra reviews remained intact. The first journal contained 87,416 completed rows and eight pending rows. No behavioral shard had finished its audits, and the catalogue still contained the original 76 observations.

The campaign resumed through `scripts/launch_exhaust_services.py`, which launches the existing runner, a console-independent Python sleep guard and the uploader as detached Windows processes with explicit breakaway from the interactive executor job. The existing Site credential is supplied through hidden stdin and forwarded only through the uploader's anonymous pipe. PID and log metadata are saved in the ignored `.cache/exhaust-services.json`; no credential is saved. The launcher refuses to duplicate live recorded services. After the launcher exited, all three services were independently checked alive and fresh generation jobs completed. Worker sources, partition, journals and request ceilings remain unchanged. A restart can replay status messages from cached stages; it does not regenerate completed measurements.

Initial live-storage verification on 2026-11-05 checked all 76 original catalogue values, four representative evidence byte hashes, the 172,032-coordinate progress total, and anonymous HTTP 401 access denial. The uploader acknowledged 1,445 objects before ongoing campaign exports. This verifies initial transfer and access behavior, not completion of the behavioral campaign. `scripts/verify_site_evidence.mjs` can repeat read-only live checks with the existing Site credential supplied through hidden stdin.

```powershell
.venv-qwen\Scripts\python.exe scripts/run_exhaust.py
node scripts/exhaust_progress.mjs --brief
node check-ui.mjs
.venv-qwen\Scripts\python.exe scripts/build_evidence_worker.py
node scripts/test_evidence_worker.mjs
```

Per-shard elapsed time includes time waiting between the numerical pass and its behavioral pass. Use parent wall-clock time for total duration. Single checkpoint, mostly English prompts, greedy decoding, adaptive shortlisting, token ceilings and subjective judgments limit generalization. A pass establishes an observed sampled mode change, not a useful improvement, unique neuron function or intent.
