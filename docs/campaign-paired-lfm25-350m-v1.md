# LFM2.5-350M neuron-intervention results

Two recurring modes met the declared stability criteria in both the original and abliterated checkpoints: group-discussion/facilitation framing at L3 N2589, +9x, and abstract progress/collaboration discourse at L5 N4206, +15x. These remained readable while frequently replacing the requested task. Diplomatic/military and agricultural topic takeovers also appeared, but their frozen test settings exceeded the repetition or collapse limits.

The fixed numerical grid screened all 73,728 MLP coordinates in each checkpoint. The full pipeline completed 764,900 configurations and added 30 model-specific catalogue observations. 3 preferred catalogue records meet the declared stability criteria under both reviewers. Across all frozen settings, 4 checkpoint/coordinate/dose conditions meet the same criteria.

Ordinary prompts were fixed before inspecting outputs. Interventions clamp one gated hidden activation immediately before the MLP output projection; weights remain unchanged. Doses are signed multiples of the maximum absolute activation measured for that coordinate in the original checkpoint calibration. Every physical batch includes an unmodified anchor. Task loss, repetition, collapse and baseline defects are reported separately from strength and coherence.

Both final reviewers receive the frozen validation hypotheses, including validation ratings, notes and evidence references. Sol receives a separate request without Terra's held-out verdict. The second-model assessment therefore shares nomination information with the primary review.

## What changed, and how the checkpoints differed

- **Group facilitation, L3 N2589 at +9x:** both reviewers matched the effect in 30/32 responses in each checkpoint. Sol marked two repetition cases in each, with zero collapse cases in the original and one in the derivative. Sol marked task loss in 25/32 and 24/32 respectively.
- **Progress/collaboration discourse, L5 N4206 at +15x:** Sol matched the effect in 29/32 responses in each checkpoint; Terra matched 30/32 in each. Both reviewers marked zero repetition and zero collapse. Sol marked task loss in 26/32 original and 27/32 edited responses.

The three passing preferred catalogue cards and four passing frozen conditions are different counts. The edited L3 N2589 card displays the validation-preferred -15x assessment/development setting, which misses the final repetition limit. Its separately frozen +9x group-facilitation setting passes both reviewers and is shown as an additional setting on that card.

Repetition differences varied by setting. Sol marked the derivative more repetitive at three of eight matched settings, less repetitive at two, and equal at three; Terra's counts were four, two and two. For example, Sol's repetition count fell from 7 to 3 for assessment boilerplate at L3 N2589, -15x, but rose from 5 to 7 for multilingual switching at L10 N4198, +3x. The two qualifying modes occurred in both checkpoints.

The more dramatic topic takeovers remain measured findings. At L2 N3420, +12x, Sol matched diplomatic/military reframing in 32/32 original and 31/32 edited responses, but marked 6/4 repetition and 3/2 collapse cases. At L2 N3030, -15x, agricultural takeover matched 29/32 in both, with 3/4 repetition cases. These settings miss the prespecified quality limits. The diplomatic +9x setting looked cleaner in validation: 8/8 matches in both checkpoints with no repetition or collapse flags. It was outside the frozen held-out grid, which tested -12x and +12x for that coordinate; its held-out stability remains unmeasured.

## The same ordinary question, different frames

Prompt: **What is a curious fact about ponds?** These are selected held-out illustrations jointly matched by both reviewers, with task loss flagged and no repetition/collapse flag on the displayed cases. Counts above cover the full test sets. Baseline-defect counts in the detailed table also include existing errors and truncated outputs.

**Original baseline:**

> A curious fact about ponds is that they can be home to a wide variety of aquatic life, including fish, amphibians, and even certain types of algae. Some ponds are so diverse that they can host multiple species of fish, such as carp, bass, and catfish, depending on the location and water conditions. Additionally, ponds can also be home to unique and sometimes invasive species, like the Asian carp, which can disrupt local ecosystems and outcompete native species for resources.

**Group-facilitation frame (L3-N2589, +9x):**

> A curious fact about ponds is that they often serve as a reflection of the community's values and priorities. The water level of the pond can reveal insights into the group's dynamics, as the more vocal members may dominate the conversation, while the quieter voices may contribute to a more balanced discussion. This highlights the importance of active listening and encourages empathy, ultimately leading to a deeper understanding of the group's needs and goals.

**Progress/collaboration frame (L5-N4206, +15x):**

> A curious fact about ponds is that they are not created in a vacuum. This means that scientific understanding and evidence have shifted, leading to a greater emphasis on the interconnectedness of human knowledge and the potential for new insights and solutions to complex global issues.

**Abliterated baseline:**

> A curious fact about ponds is that they can be home to a surprising number of species, including fish, amphibians, and even certain types of algae. Some ponds may also host invasive species that can disrupt local ecosystems. Additionally, the water quality in ponds can be affected by factors such as pollution, nutrient levels, and temperature, making them important indicators of environmental health.

**Group-facilitation frame (L3-N2589, +9x):**

> A curious fact about ponds is that they often serve as a metaphor for human interactions. Just as ponds can be used to model discussions, negotiate conflicts, or even simulate team-building exercises, they can also reveal underlying dynamics, emotions, and unspoken needs. This highlights the importance of active listening, empathy, and clear communication, ultimately leading to a deeper understanding of the group's dynamics and a more cohesive outcome.

**Progress/collaboration frame (L5-N4206, +15x):**

> A curious fact is that the Earth is not entirely made of water, and the concept of human ingenuity has led to the development of sustainable technologies and solutions to global challenges. This realization has sparked conversations about the importance of addressing issues like climate change, environmental degradation, and social justice, as well as the potential for innovation and progress.

Full selected [original paired examples](../site-source/evidence/findings/paired-lfm25-350m-v1-original.json) and [edited paired examples](../site-source/evidence/findings/paired-lfm25-350m-v1-abliterated.json) retain the case IDs, doses and termination flags.

## Checkpoints

- original: [LiquidAI/LFM2.5-350M](https://huggingface.co/LiquidAI/LFM2.5-350M/tree/9921cd4d82c0e3986887aa4b376f9446729ef8a3), revision `9921cd4d82c0e3986887aa4b376f9446729ef8a3`.
- abliterated: [s3nh/LFM2.5-350M-abliterated](https://huggingface.co/s3nh/LFM2.5-350M-abliterated/tree/3b5076fba033be25cb354990e7d03d883cf43b2c), revision `3b5076fba033be25cb354990e7d03d883cf43b2c`.

Exact CPU comparison found 19 changed and 129 identical tensors, with matching names, shapes and dtypes: 6 MLP, 5 attention and 8 convolution output projections changed. The derivative publisher's documented parent weights match the acquired original file hash. This inventory does not establish edit rank or independently verify the publisher's refusal benchmarks. The paired result concerns all these checkpoint edits together. [Weight inventory](../site-source/evidence/paired-lfm25-350m-v1/weight-comparison.json) · [Parent verification](../site-source/evidence/paired-lfm25-350m-v1/parent-provenance.json)

Both checkpoints use original-model tokenization, runtime settings, calibration targets and shared continuations. The following comparisons include every frozen coordinate/dose in both checkpoints, not only each preferred displayed dose.

| Reviewer | Settings | Derivative more repetitive | Less repetitive | Equal |
|---|---:|---:|---:|---:|
| Terra | 8 | 4 | 2 | 2 |
| Sol | 8 | 3 | 2 | 3 |

## Frozen settings meeting the criteria

Each catalogue card displays one validation-selected setting per coordinate and checkpoint. This table includes every frozen setting meeting the criteria, including additional settings on the same coordinate.

| Checkpoint | Coordinate | Dose | Effect label | Selected on card |
|---|---|---|---|---|
| original | L5-N4206 | p15 | Sweeping progress, collaboration and argument discourse | Yes |
| abliterated | L5-N4206 | p15 | Sweeping progress and collaboration discourse | Yes |
| original | L3-N2589 | p9 | Group discussion and facilitation framing | Yes |
| abliterated | L3-N2589 | p9 | Group discussion and facilitation framing | No |

## Later-token screening

8 of 15 validation coordinates entered the shared shortlist through delayed-effect ranking with no early-rank nomination in any checkpoint. These are selection-provenance counts under fixed per-layer quotas. [Within-layer ranks and selection paths](../site-source/evidence/paired-lfm25-350m-v1/screening-provenance.json).

## Held-out outcomes

Each row below uses Sol ratings on the same 32 neuron outputs: 16 held-out, eight longer and eight replication prompts. The random-match column counts the same description among 32 matched random-direction outputs per setting (four directions on eight prompts). Held-out claims apply to the listed coordinate/dose settings. Other dose-grid results retain validation-only evidence. Passing the declared gate does not require task correctness or random-direction specificity.

| Coordinate | Dose | Checkpoint | Effect label | Effect matches | Random matches | Repetition | Collapse | Task loss | Baseline defects | Change / coherence |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| L2-N3030 | n15 | original | Agricultural topic takeover | 29 | 0 | 3 | 2 | 29 | 18 | 4/4 / 3/4 |
| L2-N3030 | n15 | abliterated | Agricultural topic takeover | 29 | 0 | 4 | 2 | 30 | 14 | 4/4 / 3/4 |
| L2-N3420 | n12 | original | Invented historical and institutional exposition, with archival storytelling | 30 | 0 | 11 | 1 | 28 | 16 | 4/4 / 3/4 |
| L2-N3420 | n12 | abliterated | Invented historical, institutional and biographical exposition | 30 | 0 | 11 | 0 | 27 | 17 | 4/4 / 3/4 |
| L2-N3420 | p12 | original | Diplomatic and military reframing | 32 | 0 | 6 | 3 | 32 | 16 | 4/4 / 3/4 |
| L2-N3420 | p12 | abliterated | Diplomatic and military reframing | 31 | 0 | 4 | 2 | 31 | 17 | 4/4 / 3/4 |
| L5-N4206 | p15 | original | Sweeping progress, collaboration and argument discourse | 29 | 0 | 0 | 0 | 26 | 18 | 4/4 / 3/4 |
| L5-N4206 | p15 | abliterated | Sweeping progress and collaboration discourse | 29 | 0 | 0 | 0 | 27 | 16 | 4/4 / 3/4 |
| L3-N2589 | n15 | original | Individualized needs, development and assessment boilerplate substitution | 32 | 0 | 7 | 1 | 30 | 19 | 4/4 / 3/4 |
| L3-N2589 | n15 | abliterated | Professional development and individualized needs-assessment substitution | 32 | 1 | 3 | 0 | 30 | 16 | 4/4 / 3/4 |
| L3-N2589 | p9 | original | Group discussion and facilitation framing | 30 | 0 | 2 | 0 | 25 | 19 | 4/4 / 4/4 |
| L3-N2589 | p9 | abliterated | Group discussion and facilitation framing | 30 | 0 | 2 | 1 | 24 | 16 | 4/4 / 3/4 |
| L10-N4198 | p3 | original | Multilingual switching with variable semantic degradation | 30 | 0 | 5 | 1 | 7 | 17 | 4/4 / 3/4 |
| L10-N4198 | p3 | abliterated | Mixed-language responses with intermittent repetition and semantic degradation | 30 | 0 | 7 | 2 | 4 | 20 | 4/4 / 3/4 |
| L5-N3454 | n8 | original | Mixed-language responses and foreign-language switching | 30 | 0 | 5 | 0 | 5 | 19 | 4/4 / 3/4 |
| L5-N3454 | n8 | abliterated | Mixed-language responses and foreign-language switching | 30 | 0 | 6 | 0 | 6 | 17 | 4/4 / 3/4 |

## Catalogue observations

| Checkpoint | Coordinate | Label | Evidence state |
|---|---|---|---|
| LFM2.5-350M | L2-N3420 | Diplomatic and military reframing | Tested observation |
| LFM2.5-350M-abliterated (s3nh) | L2-N3420 | Diplomatic and military reframing | Tested observation |
| LFM2.5-350M | L0-N3732 | French or mixed-language, often abbreviated responses | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L0-N3732 | French or mixed-language, often abbreviated responses | Validation observation |
| LFM2.5-350M | L1-N4266 | Digressive or circular response | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L1-N4266 | Digression and repetitive advice | Validation observation |
| LFM2.5-350M | L10-N4198 | Multilingual switching | Tested observation |
| LFM2.5-350M-abliterated (s3nh) | L10-N4198 | Mixed-language responses | Tested observation |
| LFM2.5-350M | L2-N3030 | Agricultural topic takeover | Tested observation |
| LFM2.5-350M-abliterated (s3nh) | L2-N3030 | Agricultural topic takeover | Tested observation |
| LFM2.5-350M | L3-N2589 | Group discussion and facilitation framing | Extreme mode observed |
| LFM2.5-350M-abliterated (s3nh) | L3-N2589 | Professional development and assessment substitution | Tested observation |
| LFM2.5-350M | L4-N999 | Invented conditions, qualifications and physical challenges | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L4-N999 | Invented qualifications and physical-work scenarios | Validation observation |
| LFM2.5-350M | L5-N3454 | Mixed-language responses | Tested observation |
| LFM2.5-350M-abliterated (s3nh) | L5-N3454 | Mixed-language responses | Tested observation |
| LFM2.5-350M | L3-N4170 | Chinese or mixed-language response | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L3-N4170 | Chinese or mixed-language response | Validation observation |
| LFM2.5-350M | L14-N1700 | Scattered malformed words and incorrect arithmetic | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L14-N1700 | Lighting-list fixation and L-initial headings | Validation observation |
| LFM2.5-350M | L2-N451 | Layout and content-design reframing with repeated or indirect answers | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L2-N451 | Layout and presentation reframing, with story repetition | Validation observation |
| LFM2.5-350M | L1-N1466 | Emerging Japanese-English mixing | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L1-N1466 | Multilingual responses and mixing | Validation observation |
| LFM2.5-350M | L0-N3694 | Abbreviated, generic responses with loss of specificity | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L0-N3694 | Abbreviated, generic responses with loss of specificity | Validation observation |
| LFM2.5-350M | L1-N1681 | No supported qualitative label · L1-N1681 | Validation observation |
| LFM2.5-350M-abliterated (s3nh) | L1-N1681 | No supported qualitative label · L1-N1681 | Validation observation |
| LFM2.5-350M | L5-N4206 | Sweeping progress and argument discourse | Extreme mode observed |
| LFM2.5-350M-abliterated (s3nh) | L5-N4206 | Sweeping progress and collaboration discourse | Extreme mode observed |

The independent audit linked 17,624 exact generation pairs to raw completed jobs. Terra used 169/700 requests; Sol used 7/100. Review gaps: 0.

Reviewers are fallible language models. These selected interventions and finite prompts do not establish a population-wide ranking, a persistent model personality, or a single cause of cross-family differences. The numerical grid is exhaustive; the space of prompts and possible activation targets is not.

[Browse the catalogue](https://juhanimerilehto.github.io/neuron-atlas/) · [Protocol](paired-lfm25-350m-v1.md) · [Independent audit](../site-source/evidence/paired-lfm25-350m-v1/independent-audit.json)
