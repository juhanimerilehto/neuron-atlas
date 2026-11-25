# LFM then Granite: durable campaign handoff

The finite sequence configured on 25 November 2026 completes LFM, verifies public publication, then completes and publishes Granite. Run commands from the repository root.

## Durable state

- Queue service PID and log: `.cache/family-queue-service.json`.
- Current queue stage: `.cache/family-queue-state.json`; append-only transitions: `.cache/family-queue-events.jsonl`.
- Campaigns: `campaigns/paired-lfm25-350m-v1` then `campaigns/granite40-350m-v1`.
- Each campaign retains `manifest.json`, `selection.json`, `preflight.json`, original/native calibration, numerical prefix bank, per-layer summaries, raw paired generations, SQLite journals, raw reviewer attempts, reviewed analyses, failures and final independent audit.
- The queue state records the current worker PID and its `logs/*-campaign.log`. Numerical progress is saved after each layer/prompt; SQLite job counts are authoritative between status updates.

The detached queue and its worker do not depend on a chat response remaining open. They do require the local Windows machine and the existing Codex reviewer authentication to remain available. Completed jobs are reused after restart. Historical Qwen and Llama sources and environments are preserved.

## Inspect and recover

Run `.venv-qwen/Scripts/python.exe scripts/family_status.py` for a read-only JSON summary of both campaigns, including live journal counts, reviewer request totals, audit results and publication receipts. It uses only the Python standard library and does not load a model. Journal counts can be ahead of the per-prompt status file.

Check the recorded PID outside the restricted sandbox process view; sandboxed process checks can falsely report detached workers missing. Preserve the unrelated GPU workload. Read actual journal counts using SQLite `mode=ro` and count `codex/*.attempt-*.request.json` and `codex-confirm/*.attempt-*.request.json`. Primary ceilings are 700/100 per campaign, including one synthetic transport-availability fixture for each reviewer. Synthetic fixtures are never model findings.

Resume a dead queue with `.venv-qwen/Scripts/python.exe scripts/launch_family_queue.py` using normal approved local execution. It rejects a duplicate live queue. The queue tries the same frozen campaign process at most three times, reusing completed jobs and accepted reviews. A persistent failure becomes `needs_attention`. Numerical source fixes require a new versioned recovery; never overwrite the frozen sources or reset attempts.

The runtime entry point is `.venv-qwen/Scripts/python.exe scripts/run_family.py <lfm|granite> <module>`. Modules include `campaign`, `audit`, `report` and `tests`. It prepends the isolated `.cache/family-runtime` dependencies, preserving `.venv-qwen`'s old packages. `family-runtime-lock.json` and `requirements-family-lock.txt` record versions; critical inference sources are checked before work and during audit.

## Publication barrier and completion

The queue deliberately waits at `awaiting_verified_publication` after each passed independent audit. Publish through the connected GitHub tools using `.cache/publication-state.json`, an actual current main-head check and `scripts/prepare_public_update.py`. Run the generated release's `node scripts/check_public_snapshot.mjs`. Preserve external changes and all earlier observations. Require expected blob/tree hashes and use a non-forced expected-head lease. Verify Pages bytes with `scripts/verify_public_deployment.py <payload-directory> <commit-sha>`.

Standalone Git authentication was not available at setup, so the detached numerical process must not invent credentials or claim that local export equals publication. A connected assistant can resume this handoff from disk in any later session. A connected assistant or authenticated publisher handles each publication barrier. If that connection disappears, the queue safely retains its outbox state; after twelve hours waiting it exits with `publication_pending`, remaining resumable. Do not start Granite until LFM's public publication is verified.

After readback, write `campaigns/<id>/publication-receipt.json` with `campaign_id`, `pages_verified: true`, `commit_sha`, `independent_audit_sha256`, publication timestamp and the verified publication baseline. The queue validates that receipt before advancing. Also save `completion.json` with counts, request totals, evidence hashes, report path and review gaps. After Granite's receipt, the queue records `complete` and exits. The finite queue exits after both verified receipts.

Before claiming scientific completion, read the final report and `site-source/evidence/<id>/outcomes.json`. Compare all frozen settings, report task loss and both improvements and regressions, and preserve missing reviews. Counts passing the declared gate are model-specific observations and do not prove task correctness, a personality, or a general model ranking.
