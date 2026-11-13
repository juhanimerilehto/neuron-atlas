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
    lines = ['# Paired Qwen3-0.6B campaign results', '',
             f'The campaign completed **{jobs:,} measured jobs** across Qwen3-0.6B and its Huihui abliterated v2 variant. '
             f'All 86,016 MLP coordinates in each checkpoint were screened. The catalogue contains {len(records)} new observations '
             f'across 19 shared coordinates. **{passed} passed the full stability gate under both reviewers.**', '',
             'The clearest recurrent changes were English-to-Chinese responses and generic support/help replies displacing the requested answer. '
             'These are substantial qualitative changes. Repetition and occasional collapse prevented stable-mode certification at the tested doses. '
             'A failed gate does not erase the observed change.', '', '## Scope and evidence', '',
             '| Stage | Original | Abliterated |', '|---|---:|---:|']
    for stage in ('screen', 'fine', 'discovery', 'validation', 'locked_test', 'long', 'replication', 'random_controls'):
        lines.append(f"| {stage.replace('_', ' ')} | {audit['all_stage_counts']['original'][stage]:,} | {audit['all_stage_counts']['abliterated'][stage]:,} |")
    track_text = ', '.join(f'{count} {route}' for route, count in sorted(tracks.items()))
    lines += ['', f'The shared shortlist contained {len(shortlist)} coordinates: {track_text} route memberships '
              f'(memberships can overlap). {later_only} coordinates entered through a late-position route without an early-position route. '
              'Screening measured positions 0, 8, 16, 32 and 64 along the same original-model continuation. '
              'Fine-dose probes used two additional normal continuations; free generation used four discovery prompts, eight fresh validation prompts, '
              'sixteen held-out prompts, eight longer prompts and eight replication prompts.', '',
              'The intended readable finalist set is eight shared coordinates, assessed in both checkpoints. '
              'All received accepted Terra and independent Sol final reviews. The zero-quota selection defect also advanced exploratory settings '
              'at eighteen total tested coordinates; the validation-only reconstruction and preserved extra measurements are documented in the '
              '[protocol](paired-qwen06-late-v1.md).', '', '## Primary finalist outcomes', '',
              'Doses are signed multiples of the original checkpoint calibration maximum. T = Terra; S = Sol. '
              'Matches are held-out /16, longer /8, replication /8. Repetition and collapse are separate flags over the 32 selected-condition neuron outputs. '
              'The gate permits at most two flags of each kind and requires both reviewers, the frozen hypothesis and validation criteria to pass.', '',
              '| Coordinate | Model | Dose | Matches T | Matches S | Repetition T/S | Collapse T/S |',
              '|---|---|---|---|---|---|---|']
    for r in sorted(primary, key=lambda r: (r['layer'], r['neuron'], r['model'] != 'Qwen3-0.6B')):
        gate = r['paired_gate']
        t, s = gate['primary'], gate['independent']
        matches = lambda v: ' · '.join(f"{v['matches'][stage]}/{total}" for stage, total in [('locked_test', 16), ('long', 8), ('replication', 8)])
        name = 'Original' if r['model'] == 'Qwen3-0.6B' else 'Abliterated'
        lines.append(f"| {r['component_id']} | {name} | {r['hypothesis']['best_condition']} | {matches(t)} | {matches(s)} | "
                     f"{t['repetition_flags']}/{s['repetition_flags']} | {t['collapse_flags']}/{s['collapse_flags']} |")
    lines += ['', 'The closest reviewer disagreements were:', '',
              '- Original L5 N7 at −15×: Terra passed it; Sol flagged three repetitive cases, above the two-case limit.',
              '- Abliterated L15 N59 at −12×: Terra passed it; Sol likewise flagged three repetitive cases.',
              '- Original L7 N2500 at +8×: Sol passed the support/help shift; Terra flagged three repetitive cases.', '',
              'These decisions were retained without changing thresholds after seeing the results. For the Chinese-language primary settings, '
              'the reviewers usually found no matching random-direction cases among the 32 controls at that setting. '
              'For the support shift at L7 N2500, both cited 3/32 original-model controls; the abliterated counts were 1/32 (Terra) and 4/32 (Sol). '
              'These are finite rubric judgments, not significance estimates or proof that a coordinate uniquely encodes a behavior.', '',
              '## Other observations and review gap', '',
              f'The {len(records)} records comprise ' + ', '.join(f'{count} with status “{name}”' for name, count in states.items()) + '. '
              'Exploratory outputs included punctuation/fragment collapse, prompt echo, repeated questions, imagined correction narratives and food/storage substitutions. '
              'They remain available as measured observations rather than being described as coherent stable modes.', '',
              'Exploratory L1 N1418 has no accepted Terra final review: both replies used random-control IDs in a neuron-only diagnostic field. '
              'Both were rejected and preserved. Sol completed all eighteen bundles, but that does not substitute for the missing Terra assessment. '
              'The two checkpoint records are explicitly marked “Final review incomplete.” No extra semantic retries were granted.', '',
              '## Audit and limits', '',
              f"The independent audit linked {audit['exact_pairs_linked_to_raw_jobs']:,} generation pairs to completed raw jobs, checked the full coordinate grid, "
              'job identities, SQLite integrity, frozen worker hashes, unchanged recovery sources, reviewer wire/reference hashes and winning raw responses. '
              'It also checked the primary/exploratory selection correction and explicit review gaps.', '']
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
