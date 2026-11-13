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
  assert.equal(candidates.length, snapshot.candidates);
  assert.equal(candidates.length, audit.components);
  assert.equal(new Set(candidates.map(row => row.id)).size, candidates.length);
  assert.ok(candidates.every(row => row.hits <= row.n && ['discovery', 'validation', 'locked_test'].includes(row.phase)));
  const findings = new Map();
  let examples = 0;
  for (const record of catalogue.records) {
    assert.equal(record.synthetic, false);
    const path = record.public_finding_ref;
    assert.match(path, /^evidence\/findings\/[a-z0-9-]+\.json$/);
    if (!findings.has(path)) findings.set(path, await json(path));
    const pairs = findings.get(path)[record.id];
    assert.ok(Array.isArray(pairs));
    assert.ok(pairs.every(pair => typeof pair.prompt === 'string' && typeof pair.baseline === 'string' && typeof pair.steered === 'string'));
    if (pairs.length) examples++;
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
  for (const [, asset] of html.matchAll(/(?:src|href)="([^"#]+)"/g)) {
    const result = await get(asset);
    if (asset.endsWith('.js')) run(await result.text());
  }
  await context.window.catalogueReady;
  await context.window.rereviewExplorer.load();
  for (let attempt = 0; attempt < 30 && !element('#pageTitle').innerHTML.includes('Here’s what changed'); attempt++) {
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
  assert.match(element('#pageTitle').innerHTML, /Here’s what changed/);
  assert.match(element('#publicFeatured').innerHTML, /Eight standout changes/);
  assert.equal(element('#publicFeatured').hidden, false);
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
    if (record.paired_gate) {
      const detail = element('#detail').innerHTML;
      assert.match(detail, /data-gate-summary/);
      if (record.paired_gate.review_status === 'incomplete') assert.match(detail, /Missing validated assessment: Terra/);
      else {
        assert.ok(detail.includes(`Stability gate: ${record.paired_gate.passed ? 'passed' : 'not passed'}`));
        assert.match(detail, /Terra/);
        assert.match(detail, /Sol/);
        assert.match(detail, /Description supported/);
      }
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
