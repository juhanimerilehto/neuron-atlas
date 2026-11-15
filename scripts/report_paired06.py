"""Write the final public campaign report from audited measurements and review decisions."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'campaigns/paired-qwen06-late-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    audit = read(OUT / 'independent-audit.json')
    assert audit['passed']
    records = [r for r in read(ROOT / 'site-source/catalogue.json')['records']
               if r.get('campaign_id', '').startswith('paired-qwen06-late-v1')]
    primary = [r for r in records if (r.get('paired_gate') or {}).get('primary_selection_eligible')]
    passed = sum(bool((r.get('paired_gate') or {}).get('passed')) for r in records)
    jobs = sum(sum(stages.values()) for stages in audit['all_stage_counts'].values())
    shortlist = read(OUT / 'shared-shortlist.json')
    tracks = Counter(kind for row in shortlist.values() for kind in {t.split(':')[1] for t in row['tracks']})
    later_only = sum(any(t.endswith(':late') for t in row['tracks'])
                     and not any(t.endswith(':early') for t in row['tracks']) for row in shortlist.values())
    states = Counter(r['state'] for r in records)
    by_model = {(r['component_id'], 'original' if r['model'] == 'Qwen3-0.6B' else 'abliterated'): r for r in primary}
    coordinates = sorted({r['component_id'] for r in primary})
    dose_text = lambda dose: '0' if dose == 'off' else ('+' if dose.startswith('p') else '−') + dose[1:] + '×'
    higher_repetition = {reviewer: sum(by_model[(cid, 'abliterated')]['paired_gate'][reviewer]['repetition_flags'] >
                                      by_model[(cid, 'original')]['paired_gate'][reviewer]['repetition_flags'] for cid in coordinates)
                         for reviewer in ('primary', 'independent')}
    lines = ['# Single-neuron interventions: Qwen3-0.6B and its abliterated variant', '',
             'This experiment compared Qwen3-0.6B with Huihui-Qwen3-0.6B-abliterated-v2 by clamping one MLP activation at a time '
             'and asking both checkpoints the same ordinary questions. The interventions changed activations during inference; model weights were not edited.', '',
             '**The checkpoints showed similar kinds of behavioral change, but differed in how often the changed responses repeated or broke down.** '
             'The clearest shared effects were English-to-Chinese responses and generic support/help replies replacing the requested answer. '
             'The abliterated checkpoint was more repetitive at several matched settings, while some settings favored it. '
             'These findings do not establish that either model is generally better, safer, or more steerable.', '',
             f'The experiment screened all 86,016 MLP coordinates in each checkpoint and completed {jobs:,} measured configurations. '
             f'Most configurations measured token probabilities; {audit["exact_pairs_linked_to_raw_jobs"]:,} generated responses were paired with their own unmodified baselines. '
             f'The catalogue contains {len(records)} model-specific records: 19 shared coordinates, each observed in two checkpoints.', '',
             '## Differences between the checkpoints', '',
             'The following examples use the same coordinate, clamp target, prompts and generation limits in both checkpoints. '
             'Terra and Sol are language-model reviewers used through Codex to assess the saved before-and-after responses. '
             'Counts below are Sol\'s judgments on 32 neuron-intervention responses per setting '
             '(16 held-out, 8 longer and 8 replication responses). Collapse means the reviewer judged that the output had broken down, '
             'for example into malformed or unusable text. A repetition flag and a collapse flag can apply to the same response.', '',
             '| Matched intervention | Shared observed effect | Original: repetition / collapse | Abliterated: repetition / collapse | Comparison |',
             '|---|---|---|---|---|']
    examples = [('L0-N262', 'Chinese-language responses', 'More repetition and collapse in the abliterated checkpoint.'),
                ('L7-N2500', 'Generic support/help replaces requested answers', 'More repetition and collapse in the abliterated checkpoint.'),
                ('L15-N59', 'Predominantly Chinese responses', 'Less repetition and collapse in the abliterated checkpoint.'),
                ('L10-N400', 'Language switching, sometimes with malformed text', 'A smaller improvement in the abliterated checkpoint.')]
    for cid, label, interpretation in examples:
        original, abliterated = by_model[(cid, 'original')], by_model[(cid, 'abliterated')]
        assert original['hypothesis']['best_condition'] == abliterated['hypothesis']['best_condition']
        a, b = original['paired_gate']['independent'], abliterated['paired_gate']['independent']
        lines.append(f"| {cid} at {dose_text(original['hypothesis']['best_condition'])} | {label} | "
                     f"{a['repetition_flags']}/32 · {a['collapse_flags']}/32 | {b['repetition_flags']}/32 · {b['collapse_flags']}/32 | {interpretation} |")
    lines += ['',
              'At L0 N262 (+5×), both reviewers identified the language change in all 32 responses from each checkpoint. '
              'The difference was therefore in the quality of the changed output, rather than whether a language switch occurred. '
              'At L7 N2500 (+8×), Sol matched the support/help pattern in 30/32 original-model responses and 31/32 abliterated-model responses, '
              'but flagged substantially more repetition in the latter. At L15 N59 (−12×), both had 31/32 matches, '
              'and the abliterated checkpoint had fewer repetition and collapse flags.', '',
              f"Across all eight primary coordinates, Terra rated the abliterated checkpoint as more repetitive at {higher_repetition['primary']}/8 settings; "
              f"Sol did so at {higher_repetition['independent']}/8 settings. These are descriptive comparisons of a selected set of interventions. "
              'The coordinates and prompts are not independent random samples, and the reviewers can disagree about individual cases.', '',
              '**Interpretation:** the experiment found changes in the strength and reliability of shared effects. '
              'It did not establish a distinct, repeatable behavior unique to the abliterated checkpoint. '
              'Ordinary prompts were used to look for unrequested shifts; this was not a refusal or harmful-request benchmark.', '',
              '## What the stability threshold means', '',
              f'Of the eight primary coordinate/setting pairs tested in each model, {passed} satisfied all criteria under both reviewers. '
              'This does not mean that the interventions had no effect. A language shift can recur across nearly every prompt '
              'and still fail the criterion because three responses repeat: the prespecified limit was two repetition flags among 32 responses.', '',
              'Passing required change and coherence ratings of at least 3/4, enough matches on fresh prompts '
              '(4/8 validation, 8/16 held-out, 4/8 longer and 4/8 replication), no more than two repetition and two collapse flags, '
              'and support for the description selected before held-out testing. Both reviewers had to agree that the criteria were met. '
              'This is an experiment-specific decision rule, not a certification or a claim that every failed observation is incoherent.', '',
              '## How the comparison was controlled', '',
              'Both checkpoints used the original Qwen3-0.6B chat template, identical input token IDs, greedy decoding and thinking disabled. '
              'Clamp targets used the original checkpoint\'s activation calibration in both models. Every intervention response was compared '
              'with an unmodified response from the same checkpoint and physical batch. This distinguishes an intervention effect from '
              'differences already present in the models\' baseline answers.', '',
              'A dose such as +5× means clamping the coordinate to five times its original-model calibration maximum. '
              'It does not mean multiplying its naturally varying activation by five. Matching a coordinate number across the checkpoints '
              'identifies the same architectural position, but does not prove it represents an identical feature. '
              'Exact checkpoint revisions and the procedure are in the [protocol](paired-qwen06-late-v1.md).', '',
              '## Measurement coverage', '',
              'A configuration is one intervention setting on one prompt. A numerical screening configuration contains several '
              'token-position scores; it is not a full generated answer. The table separates these stages.', '',
              '| Stage | Original | Abliterated |', '|---|---:|---:|']
    for stage in ('screen', 'fine', 'discovery', 'validation', 'locked_test', 'long', 'replication', 'random_controls'):
        lines.append(f"| {stage.replace('_', ' ')} | {audit['all_stage_counts']['original'][stage]:,} | {audit['all_stage_counts']['abliterated'][stage]:,} |")
    lines += ['', f'The shared shortlist contained {len(shortlist)} coordinates: {tracks["early"]} selected for opening-token effects, '
              f'{tracks["late"]} for later-position effects and {tracks["random"]} sampled randomly (these groups can overlap). '
              f'{later_only} coordinates were selected for later-position effects without also being selected for opening-token effects. '
              'Screening measured positions 0, 8, 16, 32 and 64 along the same original-model continuation. '
              'Fine-dose probes used two additional normal continuations; free generation used four discovery prompts, eight fresh validation prompts, '
              'sixteen held-out prompts, eight longer prompts and eight replication prompts.', '',
              'The intended readable finalist set is eight shared coordinates, assessed in both checkpoints. '
              'Both reviewers assessed each of these coordinates, and their responses passed format and evidence-reference checks. A selection error also advanced exploratory settings, '
              'giving eighteen total tested coordinates. The error, the validation-only reconstruction of the primary set, and the preserved extra measurements are documented in the '
              '[protocol](paired-qwen06-late-v1.md).', '', '## Primary finalist outcomes', '',
              'Doses are signed multiples of the original checkpoint calibration maximum. T = the Terra reviewer; S = the independent Sol reviewer. '
              'Matches are held-out /16, longer /8, replication /8. Repetition and collapse are separate flags over the 32 selected-condition neuron outputs. '
              'The gate permits at most two flags of each kind and requires both reviewers, the frozen hypothesis and validation criteria to pass.', '',
              '| Coordinate | Model | Clamp target | Matches T | Matches S | Repetition (T, S) | Collapse (T, S) |',
              '|---|---|---|---|---|---|---|']
    for r in sorted(primary, key=lambda r: (r['layer'], r['neuron'], r['model'] != 'Qwen3-0.6B')):
        gate = r['paired_gate']
        t, s = gate['primary'], gate['independent']
        matches = lambda v: ' · '.join(f"{v['matches'][stage]}/{total}" for stage, total in [('locked_test', 16), ('long', 8), ('replication', 8)])
        name = 'Original' if r['model'] == 'Qwen3-0.6B' else 'Abliterated'
        lines.append(f"| {r['component_id']} | {name} | {dose_text(r['hypothesis']['best_condition'])} | {matches(t)} | {matches(s)} | "
                     f"({t['repetition_flags']}, {s['repetition_flags']}) | ({t['collapse_flags']}, {s['collapse_flags']}) |")
    lines += ['', 'The closest reviewer disagreements were:', '',
              '- Original L5 N7 at −15×: Terra passed it; Sol flagged three repetitive cases, above the two-case limit.',
              '- Abliterated L15 N59 at −12×: Terra passed it; Sol likewise flagged three repetitive cases.',
              '- Original L7 N2500 at +8×: Sol passed the support/help shift; Terra flagged three repetitive cases.', '',
              'The thresholds were not changed after seeing these results. For the Chinese-language primary settings, '
              'the reviewers usually found no matching random-direction cases among the 32 controls at that setting. '
              'For the support shift at L7 N2500, both cited 3/32 original-model controls; the abliterated counts were 1/32 (Terra) and 4/32 (Sol). '
              'These are finite rubric judgments, not significance estimates or proof that a coordinate uniquely encodes a behavior.', '',
              '## Catalogue coverage and missing assessment', '',
              f'The {len(records)} records comprise ' + ', '.join(f'{count} with status “{name}”' for name, count in states.items()) + '. '
              'Exploratory outputs included punctuation/fragment collapse, prompt echo, repeated questions, imagined correction narratives and food/storage substitutions. '
              'They remain available as measured observations rather than being described as coherent stable modes.', '',
              'Exploratory L1 N1418 has no accepted Terra final review: both replies used random-control IDs in a neuron-only diagnostic field. '
              'Both were rejected and preserved. Sol completed all eighteen bundles, but that does not substitute for the missing Terra assessment. '
              'The two checkpoint records are explicitly marked “Final review incomplete.” No extra semantic retries were granted.', '',
              '## Data provenance and limits', '',
              f"The independent audit linked {audit['exact_pairs_linked_to_raw_jobs']:,} generation pairs to completed raw jobs, checked the full coordinate grid, "
              'job identities, SQLite integrity, frozen worker hashes, unchanged recovery sources, reviewer wire/reference hashes and winning raw responses. '
              'It also checked the primary/exploratory selection correction and explicit review gaps. '
              'These checks establish evidence linkage and consistency; the language-model ratings remain fallible judgments.', '']
    for folder, values in audit['review_transport_and_raw_response_checks'].items():
        label = 'Terra' if folder == 'codex' else 'Sol'
        lines.append(f"- {label}: {values['accepted']} accepted review bundles; {values['attempts']} requests counted against a {values['ceiling']}-request ceiling.")
    lines += ['', 'Rejected over-limit requests remain counted. One separate historical transport diagnostic was used before the new campaign and is excluded from its discoveries.', '',
              'Numerical coverage is exhaustive for the declared coordinate/dose grid. Behavioral coverage is a finite sample: the broad screen used one normal prompt '
              'and a shared teacher-forced prefix, and only a shortlist received free generation. Later-position screening can expose effects missed by the first token, '
              'but cannot guarantee discovery of every trajectory-dependent mode. Token caps, greedy decoding, BF16 rounding and a small calibration set limit generalization. '
              'Both models used the original chat template and original activation scale. The comparison concerns these two pinned checkpoints; it does not isolate abliteration as the sole cause of any difference.', '',
              '[Browse the catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · '
              '[Independent audit](../site-source/evidence/paired-qwen06-late-v1/independent-audit.json) · '
              '[Paired outcomes](../site-source/evidence/paired-qwen06-late-v1/comparison.json)', '']
    target = ROOT / 'docs/campaign-paired-qwen06-late-v1.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'report': str(target.relative_to(ROOT)), 'jobs': jobs, 'observations': len(records), 'gate_passes': passed}), flush=True)


if __name__ == '__main__':
    main()
