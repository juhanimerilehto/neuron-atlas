import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
import vm from 'node:vm';

const root = new URL('../site-source/', import.meta.url);
const prefix = '/neuron-atlas/';
const server = createServer(async (request, response) => {
  const path = new URL(request.url, 'http://localhost').pathname;
  if (path.startsWith(prefix)) {
    try {
      response.end(await readFile(new URL(path.slice(prefix.length) || 'index.html', root)));
      return;
    } catch {}
  }
  response.writeHead(404).end();
});

await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  const site = new URL(prefix, `http://127.0.0.1:${server.address().port}`);
  async function get(path) {
    const url = new URL(path, site);
    assert.ok(url.href.startsWith(site.href), `Escaped project path: ${path}`);
    const result = await fetch(url);
    assert.equal(result.status, 200, path);
    return result;
  }
  const json = async path => (await get(path)).json();
  const catalogue = await json('catalogue.json');
  const snapshot = await json('snapshot.json');
  assert.equal(catalogue.synthetic, false);
  assert.equal(catalogue.records.length, snapshot.findings);
  assert.ok(catalogue.records.length > 0);
  assert.equal(new Set(catalogue.records.map(r => r.id)).size, catalogue.records.length);

  const index = await json(catalogue.rereview.index_ref);
  const auditBytes = Buffer.from(await (await get(index.audit_ref)).arrayBuffer());
  const audit = JSON.parse(auditBytes);
  assert.equal(audit.passed, true);
  assert.equal(createHash('sha256').update(auditBytes).digest('hex'), snapshot.review_audit_sha256);
  assert.equal(index.components, audit.components);
  assert.equal(index.all_condition_count, audit.conditions_assessed);
  assert.equal(index.public_components, snapshot.featured.length);
  const {candidates} = await json('candidate-index.json');
  const followup = await json('campaign-progress-lfm-depth.json');
  for (const stage of followup.stages) {
    if (!stage.assessments_ref) continue;
    const assessed = await json(stage.assessments_ref);
    assert.equal(assessed.stage, stage.id);
    assert.equal(assessed.assessments.length, stage.assessed_condition_reviews);
    assert.ok(assessed.assessments.every(row => ['Terra', 'Sol'].includes(row.reviewer)
      && ['original', 'abliterated'].includes(row.checkpoint) && row.matches <= row.n
      && [row.repetition, row.collapse, row.task_loss, row.baseline_defects].every(n => n >= 0 && n <= row.n)
      && /^[a-f0-9]{64}$/.test(row.review_input_sha256)));
  }
  assert.equal(candidates.length, snapshot.candidates);
  assert.equal(candidates.length, audit.components);
  assert.equal(new Set(candidates.map(row => row.id)).size, candidates.length);
  assert.ok(candidates.every(row => row.hits <= row.n && ['discovery', 'validation', 'locked_test'].includes(row.phase)));
  const findings = new Map();
  const conditionOutcomes = new Map();
  let examples = 0;
  for (const record of catalogue.records) {
    assert.equal(record.synthetic, false);
    const path = record.public_finding_ref;
    assert.match(path, /^evidence\/findings\/[a-z0-9-]+\.json$/);
    if (!findings.has(path)) findings.set(path, await json(path));
    const pairs = findings.get(path)[record.id];
    assert.ok(Array.isArray(pairs));
    assert.ok(pairs.every(pair => typeof pair.prompt === 'string' && typeof pair.baseline === 'string' && typeof pair.steered === 'string'));
    if (record.condition_record) {
      assert.match(record.campaign_id, /^lfm-depth-20261127-v1-0[2-5]-[a-z-]+-(original|abliterated)$/);
      assert.ok(record.intervention_description?.length > 0);
      assert.ok(record.intervention_sites?.length > 0);
      assert.ok(record.intervention_sites.every(site => Number.isInteger(site.layer) && Number.isInteger(site.neuron)));
      assert.equal((record.additional_frozen_settings || []).length, 0);
      const base = record.campaign_id.replace(/-(original|abliterated)$/, '');
      const outcomeRef = `evidence/${base}/outcomes.json`;
      if (!conditionOutcomes.has(outcomeRef)) conditionOutcomes.set(outcomeRef, await json(outcomeRef));
      const outcomes = conditionOutcomes.get(outcomeRef);
      const profile = outcomes.profiles.find(row => row.record_id === record.id);
      assert.ok(profile, `Missing measured profile for ${record.id}`);
      assert.equal(profile.condition, record.hypothesis.best_condition);
      assert.deepEqual(profile.variant.sites, record.intervention_sites);
      assert.equal(profile.variant.timing, record.timing);
      assert.equal(profile.passed, !!record.paired_gate?.passed);
      if (record.primary_test_settings.length) {
        assert.ok(outcomes.condition_gates.some(row => row.record_id === record.id && row.condition === profile.condition));
      }
      if (profile.passed) {
        const example = pairs.find(pair => pair.id === profile.example_id);
        assert.ok(example, `Missing qualified-profile example for ${record.id}`);
        assert.equal(example.condition, profile.condition);
        assert.notEqual(example.baseline, example.steered);
      }
      if (record.factorial_examples_ref) {
        const factorial = (await json(record.factorial_examples_ref))[record.id];
        assert.deepEqual(factorial.map(row => row.arm), ['A', 'B', 'AB']);
        assert.equal(new Set(factorial.map(row => row.prompt)).size, 1);
        assert.equal(new Set(factorial.map(row => row.phase)).size, 1);
        assert.ok(factorial.every(row => /^[a-f0-9]{64}$/.test(row.id) && typeof row.baseline === 'string' && typeof row.steered === 'string'));
      }
    }
    for (const setting of record.additional_frozen_settings || []) {
      assert.equal(setting.passed, true);
      assert.equal(setting.preferred_on_card, false);
      assert.equal(setting.validation.passed, true);
      assert.equal(setting.primary.passed, true);
      assert.equal(setting.independent.passed, true);
      assert.ok(record.primary_test_settings.includes(setting.condition));
      assert.notEqual(setting.condition, record.hypothesis.best_condition);
      const example = pairs.find(pair => pair.id === setting.example_id);
      assert.ok(example, `Missing additional-setting example for ${record.id}`);
      assert.equal(example.phase, 'locked_test');
      assert.equal(example.condition, setting.condition);
      assert.notEqual(example.baseline, example.steered);
      if (!conditionOutcomes.has(record.additional_settings_ref)) conditionOutcomes.set(record.additional_settings_ref, await json(record.additional_settings_ref));
    }
    if (pairs.length) examples++;
  }
  for (const outcomes of conditionOutcomes.values()) {
    const rows = catalogue.records.filter(record => (record.campaign_id || '').startsWith(outcomes.campaign_id + '-'));
    const displayed = rows.filter(record => record.paired_gate?.passed).length + rows.reduce((n, record) => n + (record.additional_frozen_settings || []).length, 0);
    assert.equal(displayed, outcomes.qualified_frozen_condition_count);
    assert.equal(outcomes.condition_gates.filter(setting => setting.passed).length, displayed);
  }
  assert.equal(examples, snapshot.findings_with_examples);
  const components = new Map();
  for (const {id, detail_ref, phase, dose} of snapshot.featured) {
    const component = await json(detail_ref);
    assert.equal(component.id, id);
    assert.ok(component.public_excerpt);
    assert.ok(component.assessments.some(a => a.phase === phase && a.condition_effects.some(e => e.condition === dose)));
    assert.ok(component.pairs.some(p => p.stage === phase && p.condition === dose && p.kind === 'neuron'));
    assert.ok(component.pairs.every(p => /^[a-f0-9]{64}$/.test(p.id) && typeof p.baseline === 'string' && typeof p.steered === 'string'));
    components.set(detail_ref, component);
  }
  for (const row of [...index.entries, ...index.readable, ...index.mixed, ...index.nominations]) {
    assert.equal(components.get(row.detail_ref)?.id, row.id);
  }
  const report = await (await get(index.report_ref)).text();
  for (const [, link] of report.matchAll(/\]\((?!https:\/\/)([^)]+)\)/g)) {
    await get(new URL(link, new URL(index.report_ref, site)).href);
  }

  const nodes = new Map();
  function element(id) {
    if (!nodes.has(id)) nodes.set(id, {
      value: ['#model', '#state', '#campaign', '#candidatePhase'].includes(id) ? 'all' : '',
      innerHTML: '', textContent: '', hidden: false, open: false,
      classList: {toggle() {}, add() {}, remove() {}},
      setAttribute(key, value) { this[key] = value; },
      addEventListener() {}, showModal() { this.open = true; }, close() { this.open = false; },
      focus() {}, setSelectionRange() {}, add() {}, replaceChildren() {},
    });
    return nodes.get(id);
  }
  const map = element('#map');
  Object.assign(map, {clientWidth: 1000, clientHeight: 420});
  let resizeMap;
  const context = vm.createContext({
    fetch: get, document: {querySelector: element, querySelectorAll: () => [], addEventListener() {}},
    localStorage: {getItem: () => null}, window: {}, setInterval() {}, Option: class {}, console,
    ResizeObserver: class { constructor(callback) { resizeMap = callback; } observe() {} },
  });
  const run = code => vm.runInContext(code, context);
  const html = await (await get('')).text();
  assert.doesNotMatch(html, /behavior re-review|<small>new<\/small>/i);
  assert.doesNotMatch(html, /id="(?:llamaCampaign|pairedCampaign)"/);
  for (const [, asset] of html.matchAll(/(?:src|href)="([^"#]+)"/g)) {
    const result = await get(asset);
    if (asset.endsWith('.js')) run(await result.text());
  }
  await context.window.catalogueReady;
  await context.window.rereviewExplorer.load();
  for (let attempt = 0; attempt < 30 && !element('#pageTitle').innerHTML.includes('A different answer'); attempt++) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.equal(run('records.length'), catalogue.records.length);
  assert.equal(map.viewBox, '0 0 1000 420');
  assert.equal([...map.innerHTML.matchAll(/class="map-dot"/g)].length, catalogue.records.length);
  assert.match(map.innerHTML, /class="map-annotation"[^>]+L17-N668/);
  assert.match(map.innerHTML, />Language switch<\/text>/);
  function checkAnnotations(width, height, axisLabels) {
    const boxes = [...map.innerHTML.matchAll(/<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="4"/g)]
      .map(match => match.slice(1).map(Number));
    assert.ok(boxes.length > 0 && boxes.length <= 7);
    assert.equal([...map.innerHTML.matchAll(/<text /g)].length, axisLabels + boxes.length);
    boxes.forEach(([x, y, w, h], i) => {
      assert.ok(x >= 0 && y >= 0 && x + w <= width && y + h <= height);
      for (const [ax, ay, aw, ah] of boxes.slice(0, i)) assert.ok(x >= ax + aw || x + w <= ax || y >= ay + ah || y + h <= ay);
    });
  }
  checkAnnotations(1000, 420, 11);
  Object.assign(map, {clientWidth: 350, clientHeight: 330});
  resizeMap();
  assert.equal(map.viewBox, '0 0 350 330');
  checkAnnotations(350, 330, 7);
  assert.equal([...map.innerHTML.matchAll(/class="map-dot"/g)].length, catalogue.records.length);
  element('#search').value = 'L15 N1366';
  run('render()');
  assert.match(map.innerHTML, /class="map-annotation"[^>]+L15-N1366/);
  element('#search').value = '';
  run('render()');
  assert.match(element('#pageTitle').innerHTML, /A different answer/);
  assert.doesNotMatch(element('#intro').textContent, /172,032|Qwen3-1.7B/);
  assert.equal(element('#statFamilyLabel').textContent, 'MODEL CHECKPOINTS');
  assert.match(element('#publicFeatured').innerHTML, /SELECTED FROM ACROSS THE ATLAS/);
  assert.match(element('#publicFeatured').innerHTML, /paired-llama32-1b-v1-original-L0-N4395/);
  assert.match(element('#publicFeatured').innerHTML, /paired-qwen06-late-v1-original-L7-N2500/);
  assert.match(element('#publicFeatured').innerHTML, /lfm-depth-20261127-v1-01-confirm-p9-original-L2-N3420/);
  assert.equal(element('#publicFeatured').hidden, false);
  run("navigate('pipeline')");
  await context.window.researchReady;
  assert.equal(element('#publicFeatured').hidden, true);
  assert.match(element('#alternate').innerHTML, /Original and abliterated models/);
  assert.match(element('#llamaCampaign').innerHTML, /Llama 3.2 1B/);
  assert.match(element('#pairedCampaign').innerHTML, /Qwen3-0.6B/);
  assert.match(element('#lfmFollowup').innerHTML, /Study status and assessed profiles/);
  for (const stage of followup.stages) if (stage.assessments_ref) assert.ok(element('#lfmFollowup').innerHTML.includes(stage.assessments_ref));
  run("navigate('candidates')");
  for (let attempt = 0; attempt < 30 && !element('#candidateResults').innerHTML; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  assert.match(element('#candidateResults').innerHTML, /2,240 matches/);
  element('#candidateSearch').value = 'L17 N668';
  element('#candidateSearch').oninput();
  assert.match(element('#candidateResults').innerHTML, /1 match ·/);
  run("navigate('atlas')");
  for (const record of catalogue.records) {
    context.recordId = record.id;
    await run('inspect(recordId)');
    assert.match(element('#detail').innerHTML, /Selected paired example/);
    if (record.measurement_type === 'open_ended_neuron_pair') {
      const heading = element('#detail').innerHTML.split('</div>')[0];
      for (const site of record.intervention_sites) assert.ok(heading.includes(`L${site.layer} N${site.neuron}`), 'Pair heading must identify both neurons');
    }
    if (record.factorial_examples_ref) assert.match(element('#detail').innerHTML, /data-factorial-examples/);
    if (record.condition_record) {
      context.compareFixtureId = record.id;
      run('compare = new Set([compareFixtureId]); navigate("compare")');
      assert.match(element('#alternate').innerHTML, /Compare exact intervention profiles/);
      assert.ok(element('#alternate').innerHTML.includes(run('esc(records.find(r=>r.id===compareFixtureId).intervention_description.split("; constellation")[0])')));
      if (record.measurement_type === 'open_ended_neuron_pair') {
        assert.equal(run('isExtreme(records.find(r=>r.id===compareFixtureId))'), true);
        assert.match(run('card(records.find(r=>r.id===compareFixtureId))'), /NEURON PAIR/);
      }
      run('navigate("atlas")');
      if (record.measurement_type === 'open_ended_neuron_pair') {
        const otherSite = record.intervention_sites[1];
        element('#search').value = `L${otherSite.layer} N${otherSite.neuron}`;
        assert.equal(run('selected().some(row=>row.id===compareFixtureId)'), true, 'Pair must be searchable by its second neuron');
        element('#search').value = '';
      }
    }
    if (record.paired_gate) {
      const detail = element('#detail').innerHTML;
      assert.match(detail, /data-gate-summary/);
      if (record.paired_gate.review_status === 'incomplete') assert.ok(detail.includes(`Missing validated assessment: ${record.paired_gate.missing_reviewers.join(', ')}`));
      else {
        context.inspectedDose = record.hypothesis.best_condition;
        assert.ok(detail.includes(`Stability gate at ${run('esc(conditionLabel(inspectedDose))')}: ${record.paired_gate.passed ? 'passed' : 'not passed'}`));
        assert.match(detail, /Terra/);
        assert.match(detail, /Sol/);
        assert.match(detail, /Description supported/);
      }
    }
    for (const setting of record.additional_frozen_settings || []) {
      const detail = element('#detail').innerHTML;
      context.inspectedDose = setting.condition;
      context.settingLabel = setting.label;
      assert.match(detail, /data-additional-setting/);
      assert.ok(detail.includes(run('esc(settingLabel)')));
      assert.ok(detail.includes(`Stability gate at ${run('esc(conditionLabel(inspectedDose))')}: passed`));
    }
    const pairs = findings.get(record.public_finding_ref)[record.id];
    if (pairs.length) {
      context.sample = pairs[0].steered;
      assert.ok(element('#detail').innerHTML.includes(run('esc(sample)')));
    }
  }
  for (const {detail_ref, phase, dose} of snapshot.featured) {
    Object.assign(context, {detail_ref, phase, dose});
    await run('window.rereviewExplorer.open(detail_ref,phase,dose)');
    assert.match(element('#reviewDetail').innerHTML, /selected exact pairs/);
    assert.match(element('#reviewPairOutput').innerHTML, /BEFORE · UNMODIFIED/);
    const pair = components.get(detail_ref).pairs.find(p => p.stage === phase && p.condition === dose);
    context.sample = pair.steered;
    assert.ok(element('#reviewPairOutput').innerHTML.includes(run('esc(sample)')));
  }
  console.log(`Verified ${snapshot.findings} findings, ${snapshot.featured.length} featured effects, ${candidates.length} candidates, and relative assets at ${prefix}.`);
} finally {
  server.closeAllConnections();
  server.close();
}
