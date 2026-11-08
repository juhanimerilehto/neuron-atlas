/* Public catalogue and candidate index. Featured examples share the paired evidence drawer. */
{
  const number = n => Number(n).toLocaleString('en-US');
  const phaseName = phase => ({discovery: 'Discovery', validation: 'Validation',
    locked_test: 'Held-out test', random_control: 'Matched random direction'})[phase] || phase;
  const readJson = async path => {
    const response = await fetch(path);
    if (!response.ok) throw Error('Evidence unavailable');
    return response.json();
  };
  const snapshotReady = readJson('snapshot.json');
  const evidenceCache = new Map();
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
      if (version !== findingVersion || !dialog.open) return;
      $('#detail').innerHTML = `<div class="eyebrow">${esc(record.model)} · L${record.layer} N${record.neuron}</div>
        <h2>${esc(record.label)}</h2><p><b>${esc(record.state)}</b> · ${esc(campaignLabel(recordCampaign(record)))}</p>
        <p>${esc(record.summary)}</p><h3>Selected paired example</h3>
        <p>These examples illustrate the intervention. The evidence status describes the campaign’s broader results.</p>
        ${pairs.length ? pairs.map(pair => `<section class="public-pair">
          <p class="tiny">${esc(phaseName(pair.phase))} · ${esc(typeof pair.condition === 'number' ? signed(pair.condition) : conditionLabel(pair.condition))}</p>
          <p class="review-prompt">${esc(pair.prompt)}</p><div class="review-pair">
          <article><span class="tiny">BEFORE · UNMODIFIED</span><pre>${esc(pair.baseline)}</pre></article>
          <article><span class="tiny">${pair.kind === 'random_direction' ? 'AFTER · RANDOM DIRECTION' : 'AFTER · NEURON INTERVENTION'}</span><pre>${esc(pair.steered)}</pre></article></div>
          ${pair.termination === 'max_tokens' ? '<p class="tiny">The intervention response reached its token cap.</p>' : ''}</section>`).join('') : '<p>This record is published with its summary and evidence status.</p>'}
        <details><summary>Provenance</summary><p>Checkpoint revision <code>${esc(record.revision)}</code></p>
        ${record.manifest_sha256 ? `<p>Campaign manifest SHA-256 <code>${esc(record.manifest_sha256)}</code></p>` : ''}
        <a href="${esc(path)}">Download paired evidence for this campaign ↗</a></details>`;
    } catch {
      evidenceCache.delete(path);
      if (version === findingVersion && dialog.open) $('#detail').textContent = 'Paired evidence could not be loaded. Reopen this finding to retry.';
    }
  };

  const drawFullMap = drawModelMap;
  drawModelMap = list => {
    drawFullMap(list, true);
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
  snapshotReady.then(snapshot => {
    featuredSection.innerHTML = `<div class="section-title public-featured-heading"><div><p class="eyebrow">QWEN3-1.7B · ONE NEURON AT A TIME</p>
      <h2 id="featuredTitle">Eight standout changes</h2><p>Every example pairs the same ordinary prompt with and without the intervention.</p></div>
      <a class="button" href="#listTitle">Browse all findings ↓</a></div>
      <div class="cards public-featured-grid">${snapshot.featured.map(item => `<article class="card public-featured-card">
      <div class="card-top"><span class="tag">${esc(item.component_id.replace('-', ' / '))}</span><span class="tiny">${esc(conditionLabel(item.dose))}</span></div>
      <h3><button class="card-title" data-review-open="${esc(item.detail_ref)}" data-review-phase="${esc(item.phase)}" data-review-dose="${esc(item.dose)}">${esc(featuredTitles[item.component_id] || item.label)} ↗</button></h3>
      <div class="review-evidence"><b>${item.hits}/${item.n} matching cases</b><span>${esc(phaseName(item.phase))}</span></div></article>`).join('')}</div>`;
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
      $('#pageTitle').innerHTML = 'We screened every neuron.<br><em>Here’s what changed.</em>';
      $('#intro').textContent = 'We screened all 172,032 MLP coordinates in Qwen3-1.7B, intervening on one neuron at a time. Explore how the same ordinary prompts changed, from language switches to business letters and digit loops.';
    }
    if (next === 'pipeline') {
      $('#pageTitle').innerHTML = 'How we tested<br><em>one neuron at a time.</em>';
      $('#intro').textContent = 'From a numerical screen to ordinary prompts, matched controls, and held-out tests.';
      $('#alternate').innerHTML = `<div class="pipeline">
        <article class="stage"><span class="num">01 ─────</span><h3>Screen the model</h3><p>Screen all 172,032 MLP coordinates in the pinned Qwen3-1.7B checkpoint. Clamp one coordinate at a time, including turning it off.</p></article>
        <article class="stage"><span class="num">02 ─────</span><h3>Generate paired responses</h3><p>Generate responses across doses for 2,240 shortlisted candidates in the final sweep. Compare each with the unchanged model on the same prompt.</p></article>
        <article class="stage"><span class="num">03 ─────</span><h3>Challenge the effects</h3><p>Advance 160 candidates to validation and 60 finalists to held-out testing. Use longer generations and matched random directions to test whether changes persist.</p></article>
        <article class="stage"><span class="num">04 ─────</span><h3>Score change and coherence</h3><p>Codex labeled changes from the paired outputs. A later scoring pass separated strength of change from readability and kept the original test decisions visible.</p></article>
        </div><p><a href="evidence/exhaust-qwen-v1/manifest.json">Campaign manifest ↗</a> · <a href="evidence/extremity-rereview-v1/report.md">Results and audit ↗</a> · <a href="https://github.com/juhanimerilehto/neuron-atlas">Source repository ↗</a></p>`;
    }
  };

  Promise.all([window.catalogueReady, snapshotReady]).then(([, snapshot]) => {
    const filter = $('#model');
    filter.replaceChildren(new Option('All models', 'all'));
    for (const model of new Set(records.map(record => record.model))) filter.add(new Option(model));
    $('#statCount').innerHTML = `${number(snapshot.findings)}<small> across ${new Set(records.map(row => row.model)).size} models</small>`;
    $('#statFamilies').innerHTML = `${number(snapshot.screened_coordinates)}<small> Qwen3-1.7B MLP coordinates</small>`;
    $('#statFamilyLabel').textContent = 'COORDINATES SCREENED';
    $('#modeStatLabel').textContent = 'QWEN CANDIDATES';
    $('#stabilityStat').innerHTML = `${number(snapshot.candidates)}<small> with paired generations in the final sweep</small>`;
    $('#runStatLabel').textContent = 'FINAL SWEEP';
    $('#runState').textContent = number(snapshot.jobs);
    $('#runProgress').textContent = 'measured jobs across 10 shards';
    if (view === 'atlas') navigate('atlas');
  }).catch(() => {});
}
