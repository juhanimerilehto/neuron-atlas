# Extremity-first retrospective re-review

The completed exhaustive campaign advanced only six finalists per shard, sorting novelty before most measures of strength. This excluded L7 N3649 at −8× despite seven of eight validation cases matching a violence-related change. The user requested a re-review centered on striking behavior.

The new `extremity-rereview-v1` protocol preserves every original measurement, judgment and gate result. It runs fresh evidence-only Codex interpretation over all 2,240 generated discovery candidates, all 160 validation records and the existing held-out evidence for 60 finalists. It performs no new Qwen generation. Review order is validation first, discovery second, existing held-out evidence last. The validation bundles containing the user-discussed violence and document candidates run first.

## New interpretation contract

Every supplied dose gets an assessment, including the opposite sign. There are 30,100 condition assessments over 129,600 paired generations, including the saved random controls. Two independent ordinal axes replace the old combined prioritization: behavioral change strength (0–4) and coherence (0–4). A dramatic numeric loop can receive high change and low coherence; it remains visible rather than being presented as a stable coherent mode or discarded. Task loss, repetition, collapse, baseline defects and matching random controls have separate evidence references. Factual errors and task displacement are disclosed rather than automatically suppressing the observation.

Earlier labels, ratings, novelty categories and selection outcomes are omitted from primary reviewer inputs. Repeated baseline text is deduplicated in the model's wire representation, with a lossless lookup and reference map. Exact full continuation strings, ordinary prompts, termination flags and original job IDs are preserved. Structural checks require coverage of every supplied case and condition, reject references to other conditions, and prevent identical baseline/steered strings from serving as evidence of change.

Rank order is change strength, matching fraction, evidence count and coherence. Novelty, topic and layer have no preference. Readable changes (coherence ≥3) and mixed/collapsed changes have separate queues, with all coordinates searchable. Other assessments at the same dose remain visible to expose contradictory phases rather than hiding them behind one favorable rating.

## Reviewers and bounds

The primary reviewer explicitly requests `gpt-6.1-terra`, medium reasoning: 320 planned batches, at most 400 attempts including retries. Two calls can run concurrently. `gpt-6.1-sol`, medium, independently checks the two user-interest nominations plus up to 24 readable and 24 mixed/collapsed nominations, deduplicated by coordinate and dose: up to 50 nominations, 13 batches, and 26 attempts. Both requested aliases and CLI versions are saved; immutable resolved upstream checkpoints are unavailable.

Sol receives all available saved pairs at the nominated coordinate/dose and any saved random controls at that setting. This independent interpretation does not create independent experimental data. User-interest nominations are explicit and separate from score-based ranking. The violence candidate remains without locked tests; the document candidate retains its original quality-gate failure. Neither can become a new original campaign pass through retrospective relabeling.

## Provenance and publication

The source-hashed manifest binds all original review bundles, original audit files, original findings, original worker sources, the new reviewer code, schema and instruction. Raw CLI responses, commands, schemas, canonical/wire bundles, reference maps, errors, retries and usage remain under `campaigns/extremity-rereview-v1/`. The final audit reconstructs all primary bundles, checks all 129,600 original case references, all condition coverage, explicit models and raw-to-derived linkage. Scores are subjective interpretations, not independent ground truth.

The catalogue keeps its original 236 record values. A separate re-review sidecar adds rankings, per-dose detail, paired outputs and proposed unexecuted tests. Progress is published while reviews run. Complete sidecar evidence uploads with byte-hash acknowledgments before its index is linked from the catalogue. New evidence objects are immutable; the owner-private access policy is preserved.

The runner and publisher launch detached from the interactive terminal, using the already tested Windows process-lifetime method. They hold temporary system-awake requests and release them when work ends. The publisher's guard is bounded to 48 hours to cover the full review and evidence transfer. Credentials stay in hidden input, anonymous pipes and process memory. A failed review or failed upload stops the affected service and preserves prior catalogue evidence.

## Initial real checks

The first two accepted reviews cover 16 validation candidates and 80 condition assessments. Their raw responses, schema references, explicit commands and original evidence linkage passed the independent checker. Fresh Terra interpretation of L7 N3649 gives −8× change 4/4, coherence 3/4 and seven matching validation cases; −10× also gives change 4/4, but coherence 2/4 with more looping. The document candidate at +15× receives change 4/4, coherence 3/4 and eight matching validation cases. These are preliminary retrospective judgments; Sol confirmation and the full corpus review are pending.

Five contract checks passed, including independent axes, cross-condition reference rejection, omitted settings, identical-output rejection and lossless baseline deduplication. Catalogue logic checks use the actual first accepted review outputs and cover original-record preservation, paired text, dose switching, score/path rejection and HTML escaping. Browser layout remains unverified because local browser use is disabled in Work settings; no browser-control workaround is used.

Run or resume with `.venv-qwen\Scripts\python.exe scripts/launch_rereview.py`. Inspect `campaigns/extremity-rereview-v1/status.json` and the ignored `.cache/rereview-services.json`. Launching refuses to duplicate a recorded live runner. The publisher uses the existing Site service credential through hidden stdin, never arguments or files.
