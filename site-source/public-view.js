/* Public catalogue and candidate index. Featured examples share the paired evidence drawer. */
{
  const number = n => Number(n).toLocaleString('en-US');
  const originalIsExtreme = isExtreme;
  isExtreme = record => record.measurement_type === 'open_ended_neuron_pair' || originalIsExtreme(record);
  const pairSites = record => record.intervention_sites.map(site => `L${site.layer} N${site.neuron}`).join(' + ');
  const originalExtremeCard = extremeCard;
  extremeCard = record => {
    const html = originalExtremeCard(record);
    return record.measurement_type === 'open_ended_neuron_pair'
      ? html.replace('SINGLE NEURON · NORMAL PROMPTS', 'NEURON PAIR · NORMAL PROMPTS')
        .replace(`L${record.layer} / N${record.neuron}`, esc(pairSites(record))) : html;
  };
  const originalMixedCompare = renderMixedCompare;
  renderMixedCompare = rows => {
    if (!rows.some(row => row.condition_record)) return originalMixedCompare(rows);
    $('#alternate').innerHTML = `<div class="notice">Compare exact intervention profiles. Ratings are ordinal judgments; paired-neuron effects do not by themselves establish synergy.</div>
      <div style="overflow:auto"><table><thead><tr><th>COMPONENT / MODEL</th><th>INTERVENTION</th><th>REPORTED EFFECT</th><th>EVIDENCE</th><th>STATE</th><th></th></tr></thead><tbody>
      ${rows.map(record => `<tr><td><button class="card-title" data-open="${esc(record.id)}">${esc(record.measurement_type === 'open_ended_neuron_pair' ? pairSites(record) : `L${record.layer} N${record.neuron}`)} ↗</button><br>${esc(record.model)}</td>
        <td>${esc(record.intervention_description?.split('; constellation')[0] || (isExtreme(record) ? conditionLabel(record.hypothesis.best_condition) + ' coordinate clamp' : signed(record.dose) + ' residual norms'))}</td>
        <td>${isExtreme(record) ? `${record.hypothesis.extremity}/4 Codex rubric` : `${signed(record.effect)} pp`}</td>
        <td>${isExtreme(record) ? 'Open paired outputs and controls' : fmt(record.random_control_exceedance)}</td><td>${esc(record.state)}</td>
        <td><button class="icon" data-remove="${esc(record.id)}">×</button></td></tr>`).join('')}</tbody></table></div>`;
  };
  const originalCampaignLabel = campaignLabel;
  const originalConditionLabel = conditionLabel;
  conditionLabel = value => {
    if ((value || '').includes('__')) {
      const parts = value.split('__');
      if (parts[0] === 'pair') return `Pair arm ${parts[1]} · ${originalConditionLabel(parts[2])} target multiplier`;
      const timings = {all: 'prompt and response', prompt: 'prompt only', decode: 'from response token 2',
        window_8_24: 'response tokens 9–24', pulse_16: 'response token 17'};
      return `${parts[0]} · ${timings[parts[1]] || parts[1].replaceAll('_', ' ')} · ${originalConditionLabel(parts[2])}`;
    }
    return originalConditionLabel(value);
  };
  const studyLabels = {
    'paired-qwen06-late-v1-original': 'Qwen3-0.6B · original',
    'paired-qwen06-late-v1-abliterated': 'Qwen3-0.6B · abliterated',
    'paired-llama32-1b-v1-original': 'Llama 3.2 1B · original',
    'paired-llama32-1b-v1-abliterated': 'Llama 3.2 1B · abliterated',
    'paired-lfm25-350m-v1-original': 'LFM2.5-350M · original',
    'paired-lfm25-350m-v1-abliterated': 'LFM2.5-350M · abliterated',
    'granite40-350m-v1-original': 'Granite 4.0-350M · survey',
  };
  const followupStageNames = {'01-confirm-p9': '+9× confirmation', '02-dose-response': 'Dose response',
    '03-missed-candidates': 'Missed candidates', '04-timing-operators': 'Timing and operators', '05-neuron-pairs': 'Neuron pairs'};
  campaignLabel = id => {
    if ((id || '').startsWith('lfm-depth-20261127-v1-')) {
      const stage = id.slice('lfm-depth-20261127-v1-'.length).replace(/-(original|abliterated)$/, '');
      return `LFM follow-up · ${followupStageNames[stage] || stage} · ${id.endsWith('-abliterated') ? 'abliterated' : 'original'}`;
    }
    return studyLabels[id] || originalCampaignLabel(id);
  };
  const phaseName = phase => ({discovery: 'Discovery', validation: 'Validation',
    locked_test: 'Held-out test', random_control: 'Matched random direction'})[phase] || phase;
  const readJson = async path => {
    const response = await fetch(path);
    if (!response.ok) throw Error('Evidence unavailable');
    return response.json();
  };
  const snapshotReady = readJson('snapshot.json');
  const loadCampaign = (path, selector, title, protocol) => readJson(path).then(progress => {
    const target = $(selector);
    if (!target) return;
    const names = {original: 'Original', abliterated: 'Abliterated'};
    const paired = Object.keys(progress.models).length > 1;
    target.hidden = false;
    target.innerHTML = `<div class="coverage-title"><span class="eyebrow">${paired ? 'ORIGINAL AND ABLITERATED CHECKPOINTS' : 'SINGLE-MODEL NEURON SURVEY'}</span><span>${esc(progress.stage.replaceAll('_', ' '))}</span></div>
      <h3>${esc(title)}</h3><p>${number(progress.published_findings)} model-specific observations. ${paired ? 'Both checkpoints receive the same coordinates, prompts and activation targets.' : 'Individual neurons are tested across ordinary prompts and activation targets.'}</p>
      <p><a href="${esc(progress.outcome?.report_url || protocol)}">${progress.outcome ? (paired ? 'Results and model differences' : 'Results and measured effects') : 'Experiment protocol'} ↗</a></p>
      <details><summary>Screening and audit details</summary>
      <p>Numerical screening checks answer positions ${progress.checkpoints.join(', ')} before full-response generation on a shared shortlist.</p>
      <div class="coverage-metrics">${Object.entries(progress.models).map(([name, model]) => `<span>${names[name]} <b>${number(model.coordinates_screened)} / ${number(progress.coordinates_per_model)}</b> coordinates screened · ${number(model.completed_jobs)} measured configurations</span>`).join('')}</div>
      ${progress.outcome ? `<p>${number(progress.outcome.stable_gate_passes)} preferred catalogue records meet the declared stability criteria under both reviewers. ${progress.outcome.qualified_frozen_conditions !== undefined ? `${number(progress.outcome.qualified_frozen_conditions)} frozen checkpoint/coordinate/dose conditions meet those criteria across all tested settings. ` : ''}${number(progress.outcome.final_review_incomplete_records)} records have an incomplete final review. <a href="${esc(progress.outcome.audit_ref)}">Audit ↗</a></p>` : ''}
      <p>Snapshot ${esc(progress.timestamp_utc.replace('T', ' ').slice(0, 19))} UTC. <a href="${esc(protocol)}">Full protocol ↗</a></p></details>`;
  }).catch(() => {});
  const evidenceCache = new Map();
  const loadFollowup = () => readJson('campaign-progress-lfm-depth.json').then(progress => {
    const target = $('#lfmFollowup');
    if (!target) return;
    target.hidden = false;
    const finished = progress.stages.filter(stage => stage.audit_passed).length;
    target.innerHTML = `<div class="coverage-title"><span class="eyebrow">FOCUSED PAIRED STUDIES</span><span>${finished}/${progress.stages.length} stages audited</span></div>
      <h3>LFM: deeper experiments</h3><p>${number(progress.published_findings)} assessed observations from prospective confirmation, dose response, sampling, timing and bounded combinations. Each record states its tested intervention and evidence status.</p>
      <div class="coverage-metrics">${Object.entries(progress.counts).map(([name, count]) => `<span>${name === 'original' ? 'Original' : 'Abliterated'} <b>${number(count)}</b> new measured configurations</span>`).join('')}</div>
      <details><summary>Study status and assessed profiles</summary><div style="overflow:auto"><table><thead><tr><th>Study</th><th>Status</th><th>Qualified settings</th><th>Review gaps</th><th>Assessments</th></tr></thead><tbody>
        ${progress.stages.map(stage => `<tr><td>${stage.report_ref ? `<a href="${esc(stage.report_ref)}">${esc(followupStageNames[stage.id] || stage.id)} ↗</a>` : esc(followupStageNames[stage.id] || stage.id)}</td><td>${stage.audit_passed ? 'Audited' : stage.stage === 'not_started' ? 'Queued' : ['failed','needs_attention'].includes(stage.stage) ? 'Needs attention' : stage.stage.startsWith('codex') ? 'Reviewing' : 'In progress'}</td><td>${stage.qualified_conditions ?? '—'}</td><td>${stage.review_diagnostics_ref ? `<a href="${esc(stage.review_diagnostics_ref)}">${stage.review_gap_count ?? 'Pending'} ↗</a>` : stage.review_gap_count ?? '—'}</td><td>${stage.assessments_ref ? `<a href="${esc(stage.assessments_ref)}">${number(stage.assessed_condition_reviews)} condition reviews ↗</a>` : '—'}</td></tr>`).join('')}
      </tbody></table></div><p>Condition-review downloads include exploratory and failed settings. They are broader than the selected catalogue records; missing reviews are gaps, not negative findings.</p></details>
      <p><a href="https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/lfm-depth-20261127-v1.md">Study plans and limits ↗</a> · <a href="https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/lfm-weight-geometry.md">Checkpoint edits ↗</a> · <a href="https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/lfm-output-prefixes.md">Shared response openings ↗</a></p>
      ${progress.timestamp_utc ? `<p class="tiny">Snapshot ${esc(progress.timestamp_utc.replace('T',' ').slice(0,19))} UTC. Counts update with reviewed public releases.</p>` : ''}`;
  }).catch(() => {});
  const finalReview = record => {
    const gate = record.paired_gate;
    if (!gate) return '';
    if (gate.review_status === 'incomplete') return `<section data-gate-summary><h3>Final review incomplete</h3><p>Missing validated assessment: ${esc(gate.missing_reviewers.join(', '))}. No final extreme-mode verdict is assigned.</p></section>`;
    return `<section data-gate-summary><h3>Stability gate at ${esc(conditionLabel(record.hypothesis.best_condition))}: ${gate.passed ? 'passed' : 'not passed'}</h3>
      ${gate.primary_selection_eligible === false ? '<p>This setting was tested as an exploratory observation.</p>' : ''}
      <div style="overflow:auto"><table><thead><tr><th>Reviewer</th><th>Change / coherence</th><th>Held-out</th><th>Longer</th><th>Replication</th><th>Repetition</th><th>Collapse</th><th>Description supported</th></tr></thead><tbody>
      ${[['Terra', gate.primary], ['Sol', gate.independent]].map(([name, value]) => `<tr><td>${name}</td><td>${value.change}/4 · ${value.coherence}/4</td><td>${value.matches.locked_test}/16</td><td>${value.matches.long}/8</td><td>${value.matches.replication}/8</td><td>${value.repetition_flags}/32</td><td>${value.collapse_flags}/32</td><td>${value.hypothesis_supported ? 'Yes' : 'No'}</td></tr>`).join('')}</tbody></table></div>
      ${[gate.primary, gate.independent].every(value => Number.isInteger(value.task_loss) && Number.isInteger(value.random_matches)) ? `<div style="overflow:auto"><table><thead><tr><th>Reviewer</th><th>Task loss</th><th>Baseline defects</th><th>Matching random controls</th></tr></thead><tbody>
        ${[['Terra', gate.primary], ['Sol', gate.independent]].map(([name,value]) => `<tr><td>${name}</td><td>${value.task_loss}/32</td><td>${value.baseline_defects}/32</td><td>${value.random_matches}/32</td></tr>`).join('')}</tbody></table></div>
        <p class="tiny">Task loss and random-control matches are separate from this stability criterion. These 32 controls reuse four seeded directions on eight prompts.</p>` : ''}
      <p class="tiny">Both reviewers must pass. The gate permits at most two repetition flags and two collapse flags across the 32 selected-condition responses. Change and coherence are separate ratings.</p></section>`;
  };
  const additionalSettings = record => (record.additional_frozen_settings || []).map(setting =>
    `<section data-additional-setting><h3>Additional frozen setting: ${esc(conditionLabel(setting.condition))}</h3>
    <p>${esc(setting.label)}. Validation matches: ${setting.validation.matches}/${setting.validation.n}. This setting was frozen before held-out generation. The card's preferred setting is assessed above.</p>
    ${finalReview({...record, hypothesis: {...record.hypothesis, best_condition: setting.condition},
      paired_gate: {passed: true, primary: setting.primary, independent: setting.independent}})}
    <p><a href="${esc(record.additional_settings_ref)}">All frozen-setting results ↗</a></p></section>`).join('');
  let findingVersion = 0;
  const inspectFull = inspect;
  inspect = async id => {
    const record = records.find(row => row.id === id);
    const path = record?.public_finding_ref;
    if (!path) return inspectFull(id);
    if (!/^evidence\/findings\/[a-z0-9-]+\.json$/.test(path)) return;
    const version = ++findingVersion;
    const dialog = $('#inspector');
    if (!dialog.open) dialog.showModal();
    $('#detail').innerHTML = '<p>Loading paired evidence…</p>';
    try {
      if (!evidenceCache.has(path)) evidenceCache.set(path, readJson(path));
      const pairs = (await evidenceCache.get(path))[id];
      if (!Array.isArray(pairs)) throw Error('Missing evidence record');
      let factorial = [];
      if (record.factorial_examples_ref) {
        const ref = record.factorial_examples_ref;
        if (!/^evidence\/lfm-depth-20261127-v1-05-neuron-pairs\/factorial-examples\.json$/.test(ref)) throw Error('Invalid factorial evidence path');
        if (!evidenceCache.has(ref)) evidenceCache.set(ref, readJson(ref));
        factorial = (await evidenceCache.get(ref))[id];
        if (!Array.isArray(factorial) || factorial.length !== 3) throw Error('Missing factorial evidence');
      }
      if (version !== findingVersion || !dialog.open) return;
      $('#detail').innerHTML = `<div class="eyebrow">${esc(record.model)} · L${record.layer} N${record.neuron}</div>
        <h2>${esc(record.label)}</h2><p><b>${esc(record.state)}</b> · ${esc(campaignLabel(recordCampaign(record)))}</p>
        <p>${esc(record.summary)}</p>${record.intervention_description ? `<p>${esc(record.intervention_description)}</p>` : ''}${finalReview(record)}${additionalSettings(record)}<h3>Selected paired examples</h3>
        <p>These examples illustrate the intervention. The evidence status describes the campaign’s broader results.</p>
        ${pairs.length ? pairs.map(pair => `<section class="public-pair">
          <p class="tiny">${esc(phaseName(pair.phase))} · ${esc(typeof pair.condition === 'number' ? signed(pair.condition) : conditionLabel(pair.condition))}</p>
          <p class="review-prompt">${esc(pair.prompt)}</p><div class="review-pair">
          <article><span class="tiny">BEFORE · UNMODIFIED</span><pre>${esc(pair.baseline)}</pre></article>
          <article><span class="tiny">${pair.kind === 'random_direction' ? 'AFTER · RANDOM DIRECTION' : 'AFTER · NEURON INTERVENTION'}</span><pre>${esc(pair.steered)}</pre></article></div>
          ${pair.termination === 'max_tokens' ? '<p class="tiny">The intervention response reached its token cap.</p>' : ''}</section>`).join('') : '<p>This record is published with its summary and evidence status.</p>'}
        ${factorial.length ? `<details data-factorial-examples><summary>The two neurons separately and together</summary>
          <p>The same ordinary prompt is shown for A, B and AB. Each response has its own measured baseline. This illustration alone does not establish synergy.</p>
          <p class="review-prompt">${esc(factorial[0].prompt)}</p>
          ${factorial.map(pair => `<section><h3>Arm ${esc(pair.arm)}</h3><p class="tiny">${esc(pair.sites.map(s => `L${s.layer} N${s.neuron}: clamp at ${s.value}× original calibration maximum`).join(' · '))}</p>
            <div class="review-pair"><article><span class="tiny">BEFORE · UNMODIFIED</span><pre>${esc(pair.baseline)}</pre></article>
            <article><span class="tiny">AFTER · ARM ${esc(pair.arm)}</span><pre>${esc(pair.steered)}</pre></article></div>
            ${pair.termination === 'max_tokens' ? '<p class="tiny">The intervention response reached its token cap.</p>' : ''}</section>`).join('')}</details>` : ''}
        <details><summary>Provenance</summary><p>Checkpoint revision <code>${esc(record.revision)}</code></p>
        ${record.manifest_sha256 ? `<p>Campaign manifest SHA-256 <code>${esc(record.manifest_sha256)}</code></p>` : ''}
        <a href="${esc(path)}">Download paired evidence for this campaign ↗</a></details>`;
    } catch {
      evidenceCache.delete(path);
      if (version === findingVersion && dialog.open) $('#detail').textContent = 'Paired evidence could not be loaded. Reopen this finding to retry.';
    }
  };

  const drawFullMap = drawModelMap;
  const mapHighlights = {
    'exhaust-qwen-v1-s03-L17-N668': 'Language switch',
    'exhaust-qwen-v1-s04-L7-N3649': 'Assault framing',
    'exhaust-qwen-v1-s03-L10-N3451': 'Business paperwork',
    'exhaust-qwen-v1-s01-L6-N5464': 'Constitutional law',
    'exhaust-qwen-v1-s03-L6-N400': 'Tissue engineering',
    'exhaust-qwen-v1-s08-L6-N1218': 'Photography',
    'exhaust-qwen-v1-s05-L9-N5322': 'Influence framing',
  };
  const mobileHighlights = {'Language switch': 'Language', 'Assault framing': 'Assault', 'Business paperwork': 'Paperwork'};
  const shortLabel = label => label.length <= 25 ? label : `${label.slice(0, 24).replace(/\s+\S*$/, '')}…`;
  drawModelMap = list => {
    const compact = $('#map').clientWidth < 480;
    drawFullMap(list, record => {
      const highlight = mapHighlights[record.id];
      if (list.length <= 12) return highlight || shortLabel(record.label);
      return compact ? mobileHighlights[highlight] : highlight;
    });
    $('#mapCount').textContent = `${number(list.length)} MATCHING FINDINGS`;
  };
  if (typeof ResizeObserver !== 'undefined') {
    const map = $('#map');
    new ResizeObserver(() => {
      if (map.clientWidth && map.clientHeight && (view === 'atlas' || view === 'saved')) drawModelMap(selected());
    }).observe(map);
  }
  const renderFull = render;
  render = () => {
    renderFull();
    if (view === 'atlas') $('#listTitle').innerHTML = `All findings <sup>${number(selected().length)}</sup>`;
  };

  const featuredTitles = {
    'L17-N668': 'English prompts, multilingual replies', 'L7-N3649': 'Everyday questions turn into assault scenes',
    'L10-N3451': 'A short story becomes a business letter', 'L24-N1387': 'A river answer dissolves into digits',
    'L6-N5464': 'A baking question becomes constitutional law', 'L6-N400': 'Ordinary questions turn into tissue engineering',
    'L6-N1218': 'The model sees photography in ordinary tasks', 'L9-N5322': 'Tasks become stories about influence',
  };
  const featuredSection = $('#publicFeatured');
  Promise.all([window.catalogueReady, snapshotReady]).then(([, snapshot]) => {
    const deepHighlights = snapshot.featured.filter(item => ['L17-N668', 'L10-N3451', 'L24-N1387'].includes(item.component_id));
    const catalogueHighlights = [
      ['paired-llama32-1b-v1-original-L0-N4395', 'Ordinary questions become personal statements'],
      ['paired-qwen06-late-v1-original-L7-N2500', 'Requested answers become offers of support'],
      ['paired-llama32-1b-v1-abliterated-L4-N6515', 'Unrelated tasks become walking-route advice'],
    ].map(([id, title]) => ({record: records.find(row => row.id === id), title})).filter(item => item.record);
    const deepCards = deepHighlights.map(item => `<article class="card public-featured-card">
      <div class="card-top"><span class="tag">QWEN3-1.7B</span><span class="tiny">${esc(item.component_id)}</span></div>
      <h3><button class="card-title" data-review-open="${esc(item.detail_ref)}" data-review-phase="${esc(item.phase)}" data-review-dose="${esc(item.dose)}">${esc(featuredTitles[item.component_id] || item.label)} ↗</button></h3>
      <div class="review-evidence"><b>${item.hits}/${item.n} matching cases</b><span>${esc(phaseName(item.phase))}</span></div></article>`);
    const findingCards = catalogueHighlights.map(({record, title}) => `<article class="card public-featured-card">
      <div class="card-top"><span class="tag">${esc(record.model)}</span><span class="tiny">L${record.layer}-N${record.neuron}</span></div>
      <h3><button class="card-title" data-open="${esc(record.id)}">${esc(title)} ↗</button></h3>
      <div class="review-evidence"><b>${esc(record.state)}</b><span>Paired responses</span></div></article>`);
    featuredSection.innerHTML = `<div class="section-title public-featured-heading"><div><p class="eyebrow">SELECTED FROM ACROSS THE ATLAS</p>
      <h2 id="featuredTitle">Small interventions. Striking changes.</h2><p>Open a finding to compare the same prompt before and after. Some effects also disrupt the task or produce repetition.</p></div>
      <a class="button" href="#listTitle">Browse all findings ↓</a></div>
      <div class="cards public-featured-grid">${deepCards.flatMap((card, i) => [card, findingCards[i]]).filter(Boolean).join('')}</div>`;
    featuredSection.hidden = view !== 'atlas';
  }).catch(() => {});

  let candidateRequest;
  async function showCandidates() {
    $('#alternate').innerHTML = '<p>Loading the candidate index…</p>';
    try {
      candidateRequest ??= readJson('candidate-index.json');
      const {candidates} = await candidateRequest;
      if (view !== 'candidates') return;
      $('#alternate').innerHTML = `<div class="notice">${number(candidates.length)} Qwen3-1.7B coordinates received full generations in the final sweep. This index summarizes one assessed setting per coordinate. Change and coherence are scored separately.</div>
        <div class="toolbar review-toolbar"><label class="search"><span>⌕</span><input id="candidateSearch" placeholder="Search by behavior or coordinate…" aria-label="Search candidates"></label>
        <select id="candidatePhase" aria-label="Filter candidates by evidence phase"><option value="all">All phases</option><option value="discovery">Discovery</option><option value="validation">Validation</option><option value="locked_test">Held-out test</option></select>
        <a class="button" href="candidate-index.json" download>Download index ↗</a></div><div id="candidateResults"></div>`;
      let limit = 24;
      const search = $('#candidateSearch');
      const phase = $('#candidatePhase');
      const update = () => {
        const query = search.value.trim().toLowerCase();
        const rows = candidates.filter(row => (phase.value === 'all' || row.phase === phase.value)
          && `${row.component_id} ${row.component_id.replace('-', ' ')} ${row.label || ''} ${row.condition}`.toLowerCase().includes(query));
        $('#candidateResults').innerHTML = `<p class="tiny">${number(rows.length)} ${rows.length === 1 ? 'match' : 'matches'} · showing ${number(Math.min(limit, rows.length))}</p>
          <div class="cards">${rows.slice(0, limit).map(row => `<article class="card"><div class="card-top"><span class="tag">${esc(row.component_id)}</span><span class="tiny">${esc(conditionLabel(row.condition))}</span></div>
          <h3>${esc(row.label || 'No supported qualitative label')}</h3><p>${esc(phaseName(row.phase))} · ${row.hits}/${row.n} matches</p>
          <p class="tiny">Change ${row.change_strength}/4 · coherence ${row.coherence}/4 · ${row.repetition_flags} repetition · ${row.collapse_flags} collapse</p>
          ${records.some(record => record.id === row.id) ? `<button class="card-title" data-open="${esc(row.id)}">Open finding ↗</button>` : ''}</article>`).join('')}</div>
          ${rows.length > limit ? '<button class="button review-more" id="candidateMore">Show 24 more ↓</button>' : ''}`;
        if (rows.length > limit) $('#candidateMore').onclick = () => { limit += 24; update(); };
      };
      search.oninput = phase.onchange = () => { limit = 24; update(); };
      update();
    } catch {
      candidateRequest = null;
      if (view === 'candidates') $('#alternate').textContent = 'The candidate index could not be loaded. Reopen the tab to retry.';
    }
  }

  const nav = navigate;
  navigate = next => {
    featuredSection.hidden = next !== 'atlas' || !featuredSection.innerHTML;
    if (next === 'candidates') {
      view = next;
      document.querySelectorAll('.nav').forEach(button => button.classList.toggle('active', button.dataset.view === next));
      $('#browse').hidden = true;
      $('#alternate').hidden = false;
      $('#pageTitle').innerHTML = 'From the sweep<br><em>to 2,240 candidates.</em>';
      $('#intro').textContent = 'See the shortlisted settings, including weak, repetitive, and collapsed outputs.';
      $('#crumb').textContent = 'CANDIDATE INDEX';
      $('#export').hidden = true;
      showCandidates();
      return;
    }
    $('#export').hidden = false;
    nav(next);
    if (next === 'atlas') {
      const hasPairs = records.some(record => record.measurement_type === 'open_ended_neuron_pair');
      $('#pageTitle').innerHTML = `${hasPairs ? 'Small changes.' : 'One neuron.'}<br><em>A different answer.</em>`;
      $('#intro').textContent = `A growing field guide to what changes when we intervene on individual neurons${hasPairs ? ' and selected neuron pairs' : ''} in small language models. Explore measured effects, compare the same prompt before and after, and follow the evidence across models.`;
      if (hasPairs) {
        document.querySelector('.map-bottom > span').innerHTML = '● <b>Each point, a tested setting.</b> Position shows the first site of a pair, not semantic similarity. Open its record for both sites.';
        $('#map').setAttribute('aria-label', 'Layer and coordinate map. Pairs are plotted at their first site; select a record for both sites.');
      }
    }
    if (next === 'pipeline') {
      $('#pageTitle').innerHTML = 'How we tested<br><em>the interventions.</em>';
      $('#intro').textContent = 'From a numerical screen to ordinary prompts, matched controls, and held-out tests.';
      $('#alternate').innerHTML = `<div class="pipeline">
        <article class="stage"><span class="num">01 ─────</span><h3>Define the intervention</h3><p>Use a pinned model checkpoint. Start with one MLP coordinate, testing ablation, clamping or other recorded activation changes. Selected pair studies compare both individual neurons and their combination. Model weights stay unchanged, and each study records its exact settings.</p></article>
        <article class="stage"><span class="num">02 ─────</span><h3>Compare ordinary prompts</h3><p>Screen for changes in token probabilities, then generate full responses for shortlisted settings. Compare each response with the unmodified model on the same prompt. Later-token screening is included in the paired model studies.</p></article>
        <article class="stage"><span class="num">03 ─────</span><h3>Challenge the effects</h3><p>Use fresh prompts, longer responses, repeat tests and matched random directions to check how broadly a pattern persists. Each record states which tests it reached.</p></article>
        <article class="stage"><span class="num">04 ─────</span><h3>Review and retain the evidence</h3><p>Codex reviews paired outputs and names the changes. Strength, coherence, task loss, repetition and collapse are assessed separately. LLM judgments are fallible; the response examples and evidence status remain visible.</p></article>
        </div><div class="section-title"><h2>Original and abliterated models</h2></div>
        <p class="research-intro">These paired studies test the same interventions in an original checkpoint and its edited derivative. The reports include similarities, differences and counterexamples.</p>
        <div class="research-studies"><section id="llamaCampaign" class="campaign-progress" hidden aria-label="Paired Llama study"></section><section id="pairedCampaign" class="campaign-progress" hidden aria-label="Paired Qwen study"></section></div>
        <div class="section-title"><h2>More model families</h2></div>
        <div class="research-studies"><section id="lfmCampaign" class="campaign-progress" hidden aria-label="Paired LFM study"></section><section id="graniteCampaign" class="campaign-progress" hidden aria-label="Granite neuron survey"></section></div>
        <div class="section-title"><h2>Deeper experiments</h2></div><section id="lfmFollowup" class="campaign-progress" hidden aria-label="Focused LFM follow-up studies"></section>
        <p><a href="evidence/extremity-rereview-v1/report.md">Qwen3-1.7B findings and audit ↗</a> · <a href="https://github.com/juhanimerilehto/neuron-atlas">Source and study protocols ↗</a></p>`;
      window.researchReady = Promise.all([
        loadFollowup(),
        loadCampaign('campaign-progress-llama.json', '#llamaCampaign', 'Llama 3.2 1B', 'https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/paired-llama32-1b-v1.md'),
        loadCampaign('campaign-progress.json', '#pairedCampaign', 'Qwen3-0.6B', 'https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/paired-qwen06-late-v1.md'),
        loadCampaign('campaign-progress-lfm.json', '#lfmCampaign', 'LFM2.5-350M', 'https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/paired-lfm25-350m-v1.md'),
        loadCampaign('campaign-progress-granite.json', '#graniteCampaign', 'Granite 4.0-350M', 'https://github.com/juhanimerilehto/neuron-atlas/blob/main/docs/granite40-350m-v1.md'),
      ]);
    }
  };

  Promise.all([window.catalogueReady, snapshotReady]).then(([, snapshot]) => {
    const filter = $('#model');
    filter.replaceChildren(new Option('All models', 'all'));
    for (const model of new Set(records.map(record => record.model))) filter.add(new Option(model));
    const campaigns = $('#campaign');
    campaigns.replaceChildren(new Option('All campaigns', 'all'));
    for (const id of new Set(records.map(recordCampaign))) campaigns.add(new Option(campaignLabel(id), id));
    const states = $('#state');
    states.replaceChildren(new Option('All evidence states', 'all'));
    for (const state of new Set(records.map(record => record.state))) states.add(new Option(state));
    $('#statCount').innerHTML = `${number(snapshot.findings)}<small> measured observations</small>`;
    $('#statFamilies').innerHTML = `${new Set(records.map(row => row.model)).size}<small> original and edited models</small>`;
    $('#statFamilyLabel').textContent = 'MODEL CHECKPOINTS';
    $('#modeStatLabel').textContent = 'WITH BEFORE & AFTER';
    $('#stabilityStat').innerHTML = `${number(snapshot.findings_with_examples)}<small> observations with paired examples</small>`;
    $('#runStatLabel').textContent = 'PAIRED MODEL STUDIES';
    $('#runState').textContent = number(new Set(records.filter(row => row.paired_checkpoint).map(row => row.campaign_id.replace(/-(original|abliterated)$/, ''))).size);
    $('#runProgress').textContent = 'original and abliterated comparisons';
    if (view === 'atlas') navigate('atlas');
  }).catch(() => {});
}
