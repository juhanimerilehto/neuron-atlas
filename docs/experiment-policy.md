# Experiment policy and campaign contract

## An initial campaign

Use an instruct checkpoint of SmolLM2-135M for instrumentation and narrow format behavior. Resolve an immutable revision before running. Example proposal: two layers, 32 seeded neurons each, four signed doses and 12 discovery prompts = 3,072 candidate generations before baselines, random controls, validation and follow-ups. Start with a timed ten-job pilot and reduce scope to fit measured resources. The dose ladder is chosen after calibration; no universal safe or effective magnitude is assumed.

Every campaign contains these required sections:

```yaml
schema_version: 1
name: format-pilot
model:
  repository: HuggingFaceTB/SmolLM2-135M-Instruct
  revision: RESOLVE_IMMUTABLE_COMMIT_BEFORE_EXECUTION
  adapter: llama_mlp_reference_v1
target:
  behavior: requested-format compliance
  scorer: format_parser_v1
data:
  discovery: prompts/discovery.jsonl
  validation: prompts/validation.jsonl
  test: prompts/test.jsonl
  split_unit: template_family
search:
  layer_policy: two_registered_layers
  neurons_per_layer: 32
  seed: 1729
  operation: normalized_write_add
  dose_units: median_residual_l2
  doses: [-0.10, -0.05, 0.05, 0.10]
  token_policy: last_prompt_and_decode
controls:
  zero_dose: true
  random_directions_per_layer_dose: 16
  random_neurons: true
budgets:
  max_generations: 5000
  max_output_tokens_per_generation: 96
  max_gpu_seconds: 3600
  max_wall_seconds: 7200
  max_artifact_bytes: 2000000000
  max_analyzer_requests: 64
  max_analyzer_currency_usd: 10
analysis:
  provider: disabled_until_configured
  schema: analysis.v1
  max_followup_rounds: 2
validation:
  freeze_candidates_before_test: true
  gate_policy: REQUIRED_PREDECLARED_POLICY
```

This is a design example, not an executable configuration. Dose, control counts and budgets are initial choices. A manifest compiler must resolve layer indices, immutable dataset hashes and concrete validation thresholds, estimate all controls and follow-ups, reject placeholders and prevent dispatch until every required value is valid. It must not quietly exceed the 5,000-job cap to satisfy the search design.

## Scientific gates

Keep discovery, validation and test split access enforced at the service layer. Only the validation worker can read the locked test set. The adaptive planner sees discovery and validation reports; a final report becomes terminal for that candidate/test combination. Repeated adaptive queries require a fresh test set. Report exploratory ranks separately from confirmatory evidence.

Compare paired prompt outcomes and effect sizes with uncertainty clustered by template family. Compute exact full-vocabulary KL only from full distributions on identical prefixes; specify KL direction. Use equal layer, site, token positions and injected norms for random direction controls. Record degeneration, task accuracy and output length alongside intended behavior. Choose quality loss limits and minimum target improvement before validation, using pilot evidence and application needs rather than invented universal thresholds. Correct confirmatory tests for the selected family or explicitly describe an exploratory analysis.

Validate zero-dose equivalence, hook removal, padding, per-example isolation and cached inference first. A synthetic fixture, failed task, unsupported module or missing baseline must never receive a successful evidence state. Ablation, additive write and activation scaling receive distinct intervention IDs. Quantized/backend replication requires measured drift and tolerance. Compare against normal prompting and contrastive vectors before attributing practical value to neuron search.

## Autonomous planning

Deterministic shortlist → LLM hypotheses → bounded, typed follow-up proposals → policy compiler → cost reservation → job dispatch. Allowed proposals include resample contexts, narrow dose, ablate coordinate, test pair interaction and add counterexample prompts to discovery. The compiler rejects arbitrary code, invalid indices, unsupported operations, test-set access and spending expansion. The planner can stop with inconclusive or null outcomes. Its objective includes effect, repeatability and collateral quality rather than maximizing a vivid output.
