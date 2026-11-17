const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  { JSDOM } = require("jsdom");
(async () => {
  const dom = new JSDOM(
      '<section id="tab-result"><div id="old-content">Ancien résultat</div></section><div id="exportLinks"></div><div id="exportLinksResult"></div>',
      { runScripts: "outside-only" },
    ),
    w = dom.window;
  try {
    let pending = {},
      renders = 0;
    w.fetchJson = (url) =>
      new Promise((resolve, reject) => (pending[url] = { resolve, reject }));
    w.toast = () => {};
    w.renderResult = () => {
      renders++;
    };
    w.downloadExport = () => {};
    w.eval('var currentResult={id:"old"},currentPage=1;');
    const source = fs.readFileSync("web/app-extras.js", "utf8");
    w.eval(
      source.slice(
        source.indexOf("let resultLoadGeneration = 0;"),
        source.indexOf("/* Téléchargement robuste"),
      ),
    );
    const a = w.loadResult("a"),
      b = w.loadResult("b");
    assert(
      w.document
        .querySelector("#tab-result")
        .classList.contains("is-result-pending"),
    );
    pending["/api/jobs/b/result"].resolve({ id: "b" });
    await b;
    pending["/api/jobs/a/result"].resolve({ id: "a" });
    await a;
    assert.equal(w.currentResult.id, "b");
    assert.equal(renders, 1);
    const c = w.loadResult("c");
    pending["/api/jobs/c/result"].reject(Error("HTTP 503"));
    await c;
    assert.equal(w.currentResult, null);
    assert(
      w.document
        .querySelector("#tab-result")
        .classList.contains("is-result-pending"),
    );
    assert.equal(
      w.document.querySelector("#tab-result").getAttribute("aria-busy"),
      "false",
    );
    assert(
      w.document
        .querySelector(".result-load-state")
        .textContent.includes("Aucun résultat précédent"),
    );
    w.document.querySelector(".result-load-state button").click();
    pending["/api/jobs/c/result"].resolve({ id: "c" });
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(w.currentResult.id, "c");
    assert(
      !w.document
        .querySelector("#tab-result")
        .classList.contains("is-result-pending"),
    );
    console.log(
      "Source inspector: latest-request wins, failed sources clear stale results, GET retry restores real result.",
    );
  } finally {
    w.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
