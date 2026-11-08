/* The public atlas uses the existing paired evidence drawer for curated cards. */
{
  const inspectFull = inspect;
  inspect = async id => {
    const evidence = records.find(record => record.id === id)?.public_review;
    if (evidence) return window.rereviewExplorer.open(evidence.detail_ref, evidence.phase, evidence.dose);
    return inspectFull(id);
  };

  const drawFullMap = drawModelMap;
  drawModelMap = list => {
    drawFullMap(list);
    $('#mapCount').textContent = `${list.length} OBSERVATIONS IN THIS PUBLIC SNAPSHOT`;
  };

  const nav = navigate;
  navigate = next => {
    nav(next);
    if (next === 'atlas') $('#intro').textContent = 'A curated public catalogue. Explore exact before-and-after responses, matched controls, and how each effect was tested.';
    if (next === 'rereview') $('#intro').textContent = 'Selected cases from the full retrospective audit. Change and coherence are assessed separately.';
  };

  window.catalogueReady.then(() => {
    const filter = $('#model');
    filter.replaceChildren(new Option('All models', 'all'));
    for (const model of new Set(records.map(record => record.model))) filter.add(new Option(model));
    $('#state').add(new Option('Discovery observation'));
    $('#runProgress').textContent = 'Qwen3-1.7B · audited campaign';
  });
}
