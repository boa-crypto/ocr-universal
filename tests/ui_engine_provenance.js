"use strict";
const assert = require("node:assert/strict");
const {JSDOM} = require("jsdom");
const {readLocal} = require("./served_modules");
const port = process.argv[2];
let scenarios = 0;
const cp = {policy: "provider_average_else_zero", calibrated: false, reported: 1, missing: 1, invalid: 1};
const run = changes => ({engine: "baidu", page_num: 1, ok: true, word_count: 3, mean_confidence: 0, confidence_provenance: {...cp}, ...changes});
const pages = r => [{page_num: 1, engine_runs: [r]}];
const scenario = (name, action) => {action(); scenarios++; console.log("OK " + name);};
async function main() {
  const html = await readLocal(port, "/");
  const parsed = new JSDOM(html);
  const scripts = [...parsed.window.document.querySelectorAll("script[src]")].map(s => s.getAttribute("src"));
  const sources = {};
  for (const path of ["/web/engine-provenance.js", "/web/app-legacy.js", "/web/app-extras.js"]) {
    assert.equal(scripts.filter(p => p === path).length, 1, "référence HTTP unique " + path);
    sources[path] = await readLocal(port, path);
  }
  assert.ok(scripts.indexOf("/web/engine-provenance.js") < scripts.indexOf("/web/app-extras.js"));
  parsed.window.close();
  const dom = new JSDOM('<div id="host"></div>', {runScripts: "outside-only"});
  const w = dom.window, host = w.document.getElementById("host");
  w.eval(sources["/web/engine-provenance.js"]);
  function render(input) {host.innerHTML = w.UniOCREngineRuns.render(input); return host.textContent;}
  scenario("un seul moteur visible, zéro déclaré et absences distincts", () => {
    const text = render(pages(run()));
    assert.match(text, /1 déclaré\(s\) · 1 absent\(s\) · 1 invalide\(s\)/);
    assert.match(text, /non calibré/); assert.match(text, /0 %/);
    assert.equal(host.querySelectorAll(".engine-run").length, 1);
    assert.equal(host.querySelectorAll(".meter.hi, .stat.up").length, 0);
  });
  scenario("ancien score élevé jamais requalifié", () => {
    const text = render(pages(run({confidence_provenance: undefined, mean_confidence: 0.95})));
    assert.match(text, /95 %/); assert.match(text, /Provenance indisponible/);
    assert.equal(host.querySelectorAll(".engine-confidence-counts").length, 0);
  });
  const invalid = [null, [], "PRIVATE68", {}, {...cp, policy: "other"}, {...cp, calibrated: true},
    {...cp, calibrated: 0}, {...cp, missing: "1"}, {...cp, missing: true}, {...cp, invalid: -1},
    {...cp, reported: 1.0 / 2}, {...cp, reported: 10001}, {...cp, invalid: NaN},
    {...cp, invalid: Infinity}, {...cp, private: "PRIVATE68"}, {...cp, reported: 2}];
  invalid.forEach((value, i) => scenario("provenance incohérente " + i, () => {
    const text = render(pages(run({confidence_provenance: value})));
    assert.match(text, /Provenance indisponible/); assert.doesNotMatch(text, /PRIVATE68/);
    assert.equal(host.querySelectorAll(".engine-confidence-counts").length, 0);
  }));
  for (const changes of [{word_count: "3"}, {mean_confidence: "0"}, {mean_confidence: NaN},
    {mean_confidence: Infinity}, {mean_confidence: false}, {mean_confidence: -0.1}, {mean_confidence: 0.7}, {ok: false},
    {ok: undefined}, {page_num: 2}, {word_count: 2}]) {
    scenario("association au run refusée " + JSON.stringify(changes), () => {
      assert.match(render(pages(run(changes))), /Provenance indisponible/);
      assert.equal(host.querySelectorAll(".engine-confidence-counts").length, 0);
    });
  }
  scenario("run vide", () => {
    const text = render(pages(run({word_count: 0, confidence_provenance: {...cp, reported: 0, missing: 0, invalid: 0}})));
    assert.match(text, /Run vide/); assert.match(text, /0 déclaré/);
  });
  for (const [name, input, valid] of [
    ["plafond exact", pages(run({mean_confidence: 1 / 3})), true],
    ["10000 éléments déclarés", pages(run({word_count: 10000, mean_confidence: 1,
      confidence_provenance: {...cp, reported: 10000, missing: 0, invalid: 0}})), true],
    ["total excessif", pages(run({word_count: 30000,
      confidence_provenance: {...cp, reported: 10000, missing: 10000, invalid: 10000}})), false],
    ["vide avec moyenne positive", pages(run({word_count: 0, mean_confidence: 0.1,
      confidence_provenance: {...cp, reported: 0, missing: 0, invalid: 0}})), false],
    ["page parent inconnue", [{engine_runs: [run()]}], false],
  ]) {
    scenario(name, () => {
      render(input);
      assert.equal(host.querySelectorAll(".engine-confidence-counts").length, valid ? 1 : 0);
      assert.equal(host.querySelectorAll(".engine-confidence-unavailable").length, valid ? 0 : 1);
    });
  }
  scenario("pas de somme de runs ni de variantes", () => {
    const input = [{page_num: 1, engine_runs: [run(), run()]}, {page_num: 2, engine_runs: [run({page_num: 2})]}];
    const before = JSON.stringify(input); render(input);
    assert.equal(host.querySelectorAll(".engine-run").length, 3);
    assert.equal(host.querySelectorAll(".engine-confidence-counts").length, 3);
    assert.match(host.textContent, /page 1 · run 2/); assert.match(host.textContent, /page 2 · run 1/);
    assert.equal(JSON.stringify(input), before);
  });
  scenario("autre moteur sans provenance Baidu, y compris prototype", () => {
    render(pages(run({engine: "__proto__"})));
    assert.equal(host.querySelectorAll(".engine-confidence-counts, .engine-confidence-unavailable").length, 0);
    assert.match(host.textContent, /non fournie pour ce moteur/);
  });
  scenario("échappement nom moteur, pas erreur fournisseur affichée", () => {
    render(pages(run({engine: '<img src=x onerror="alert(1)">', error: "PRIVATE68", duration_ms: "PRIVATE68", word_count: "PRIVATE68"})));
    assert.equal(host.querySelectorAll("img, script").length, 0);
    assert.match(host.textContent, /<img/); assert.doesNotMatch(host.textContent, /PRIVATE68/);
  });
  scenario("nouveau rendu efface les anciens compteurs", () => {
    render(pages(run())); render(pages(run({confidence_provenance: null})));
    assert.equal(host.querySelectorAll(".engine-confidence-counts").length, 0);
    assert.equal(host.querySelectorAll(".engine-confidence-unavailable").length, 1);
  });
  for (const input of [[], null, {}, [{page_num: 1}], [{engine_runs: "wrong"}]]) {
    scenario("aucun run ne devient moteur actif", () => assert.match(render(input), /Aucune trace/));
  }
  scenario("trace illisible et page inconnue assumées", () => {
    render([{engine_runs: [null]}]); assert.match(host.textContent, /Moteur inconnu/);
    assert.match(host.textContent, /Statut non confirmé/); assert.match(host.textContent, /page \?/);
  });
  dom.window.close();

  // Exécution des modules complets réellement servis, pas extraction de fonction.
  const full = new JSDOM(html, {url: "https://preview.invalid/#documents/resultat", runScripts: "outside-only"});
  const fw = full.window;
  fw.setInterval = fw.setTimeout = () => 0;
  fw.Navigation = {init() {}};
  fw.requestAnimationFrame = callback => callback();
  fw.fetch = async (url, opts) => {
    assert.equal((opts && opts.method) || "GET", "GET", "aucune écriture UI");
    return {ok: false, status: 503, text: async () => "indisponible", json: async () => ({})};
  };
  // Un seul contexte lexical : JSDOM eval ne partage pas les let entre eval.
  fw.eval(sources["/web/app-legacy.js"] + "\n" + sources["/web/engine-provenance.js"] +
    "\n" + sources["/web/app-extras.js"] + '\ncurrentResult = ' +
    JSON.stringify({pages: [{page_num: 1, width: 10, height: 10, words: [], text: "", engine_runs: [run()]}]}) + '; renderResult();');
  scenario("renderResult complet utilise la provenance servie", () => {
    assert.match(fw.document.getElementById("enginesView").textContent, /1 déclaré/);
  });
  fw.eval('delete window.UniOCREngineRuns; renderResult();');
  scenario("module absent : état explicite, anciens compteurs effacés", () => {
    const view = fw.document.getElementById("enginesView");
    assert.match(view.textContent, /module de provenance non chargé/);
    assert.equal(view.querySelectorAll(".engine-confidence-counts").length, 0);
  });
  await new Promise(resolve => setImmediate(resolve));
  full.window.close();
  console.log(`${scenarios} scénarios provenance réussis (DOM simulé, aucune qualification Baidu).`);
}
main().catch(error => {console.error(error); process.exitCode = 1;});
