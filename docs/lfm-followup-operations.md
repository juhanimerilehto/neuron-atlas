# LFM depth: durable execution and publication

Run commands from the Neuron Atlas repository root. The finite programme directory is `campaigns/lfm-depth-20261127-v1`. `programme.json` records the authorized stages, cumulative ceilings and recovery policy. Each `stages/<id>` retains its immutable manifest, exact prompt plan, native preflight, per-checkpoint SQLite journal, response pairs, accepted reviews, independent audit and append-only `events.jsonl`.

The first study is `stages/01-confirm-p9`. Its source is `lfmfollow/confirmation_v1.py`; its shared foundation is `core_v1.py`. Do not modify these frozen numerical sources after jobs begin. Use a separately versioned recovery with a documented reason if a correction is required.

## Start and inspect

The existing `.venv-qwen` interpreter enters the isolated native runtime through `scripts/run_lfm_followup.py`. First run `preflight_v1`, then `freeze_v1`. Publish the frozen plan and verify it before writing the first stage's `preregistration-receipt.json`. The receipt binds the manifest identity and verified commit. `confirmation_v1` refuses to create measured jobs without that receipt.

`scripts/launch_lfm_followup.py confirmation_v1` detaches the first finite worker. `.cache/lfm-followup-service.json` records its PID and log. Verify that PID outside the restricted sandbox process view before recovery; a sandboxed process lookup can falsely report a detached worker missing. A duplicate live process is rejected. Preserve unrelated GPU workloads.

Read real counts from the stage's `<checkpoint>/jobs.sqlite` using SQLite `mode=ro`. Status files update after prompt batches, so journal counts can be ahead. Cumulative budgets include all stage journals and all requests under the programme's shared `codex` and `codex-confirm` directories. Never reset those directories or attempt counters.

After the first audit, `scripts/launch_lfm_followup.py programme_v1` runs the remaining finite sequence. Programme state is `campaigns/lfm-depth-20261127-v1/status.json`; its `events.jsonl` is append-only. Per-process logs are under the programme's `logs/` folder and the detached service log recorded in `.cache/lfm-followup-service.json`. The queue retries a failed stage process at most three times without resetting numerical jobs or reviewer attempts. Pending reviewed publications are recorded in `pending-publications.json`. After measurement and export it waits up to twelve hours for verified stage receipts, then exits resumably if publication is still pending.

The timing prototype's first full-prefix replay check failed before any timing-stage jobs. That failure is retained in `diagnostics/timing-preflight-v1-failure.json`. The separately versioned `preflight_timing_v2` requires exact agreement with an independently coded cached manual hook, while retaining full-prefix BF16 drift as a diagnostic. Timing and pair jobs cannot start before the versioned preflight passes; this change does not alter the first confirmation's worker or evidence.

## Recovery and publication

Read the log, manifest, current status and raw failures first. Restart the same frozen entry point to reuse completed jobs and accepted reviews. Process recovery is bounded; persistent source or reviewer errors require an explicit versioned diagnosis. Preserve incomplete evidence instead of fabricating an assessment. A passed numerical audit does not turn failed semantic criteria into a positive finding.

After a stage audit, export new observations with unique programme/stage IDs; preserve all older records, even for the same coordinate. Prepare the static release with `scripts/prepare_public_update.py`, run the release's `node scripts/check_public_snapshot.mjs`, inspect the actual remote main head, require expected blob/tree hashes and update the branch without force using an expected-head lease. Verify Pages with `scripts/verify_public_deployment.py` and retain the publication receipt. Pending changes and uncertain mutations belong in the publication outbox; inspect the remote head before retrying a ref update.

The numerical worker does not have independent GitHub credentials. A connected publisher handles public deployment; a future session can resume from these files. Later locally frozen exploratory stages may finish and queue reviewed exports while publication is unavailable. Their public reports must distinguish local freezing from the first study's public preregistration.
