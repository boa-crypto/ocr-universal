const assert = require("node:assert/strict"),
  fs = require("fs"),
  { JSDOM } = require("jsdom");
const html = fs.readFileSync("web/index.html", "utf8"),
  section = html.slice(
    html.indexOf('<section id="tab-dossiers"'),
    html.indexOf('<section id="tab-documents"'),
  );
const records = Array.from({ length: 45 }, (_, i) => ({
  id: "d" + i,
  label: i === 0 ? "<img src=x onerror=evil()> Électricité" : "Dossier " + i,
  state: [
    "en_preparation",
    "traitement_en_cours",
    "revision_requise",
    "archive",
    "nouvel_etat",
  ][i % 5],
  updated_at: 1700000000 - i,
  pieces: [],
  history: [],
}));
const tick = () => new Promise((r) => setTimeout(r, 35));
(async () => {
  const dom = new JSDOM(
    '<nav id="mainNav"><div class="nav-group"><a href="#dossiers/tous">Tous</a><a href="#dossiers/clients">Clients</a></div></nav><h2 id="pageTitle">Dossiers</h2><button class="context-guide">Repères</button><main class="workspace">' +
      section +
      "</main>",
    {
      url: "https://test.invalid/#dossiers/tous",
      runScripts: "outside-only",
      pretendToBeVisual: true,
    },
  );
  const w = dom.window,
    d = w.document;
  let requests = [],
    fail = false,
    opened;
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  w.HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new w.Event("close"));
  };
  w.openJob = (id) => {
    opened = id;
  };
  w.fetch = async (url, options) => {
    requests.push({ url, method: options?.method || "GET" });
    if (fail && url === "/api/dossiers") return { ok: false, status: 503 };
    let body =
      url === "/api/dossiers"
        ? records
        : url === "/api/dossiers/d0"
          ? {
              ...records[0],
              pieces: [{ job_id: "job-real-fixture", filename: "source.pdf" }],
            }
          : url.endsWith("/documents-ocr")
            ? [
                {
                  type_document: "Facture",
                  champs_extraits: [{ nom: "Référence", valeur_raw: "ABC" }],
                },
              ]
            : url.endsWith("/anomalies")
              ? { anomalies: [] }
              : url.endsWith("/historique")
                ? []
                : { total_frais: 0 };
    return { ok: true, json: async () => body };
  };
  try {
    w.eval(fs.readFileSync("web/dossiers.js", "utf8"));
    w.eval(fs.readFileSync("web/operations-studio.js", "utf8"));
    d.dispatchEvent(new w.Event("DOMContentLoaded"));
    await tick();
    assert.equal(d.querySelectorAll(".dos-row").length, 40);
    d.querySelector('[data-case-view="board"]').click();
    assert.equal(d.querySelectorAll(".case-lane").length, 5);
    assert.equal(d.querySelectorAll(".dos-row").length, 40);
    assert(d.querySelector(".case-lane--autres").textContent.includes("8 / 9"));
    d.querySelector("#dos-more").click();
    assert.equal(d.querySelectorAll(".dos-row").length, 45);
    const search = d.querySelector("#dos-search");
    search.value = "electricite";
    search.dispatchEvent(new w.Event("input"));
    assert.equal(d.querySelectorAll(".dos-row").length, 1);
    assert(!d.querySelector("#dos-list img"));
    d.querySelector(".dos-row").click();
    await tick();
    assert.equal(d.querySelectorAll(".case-next .case-next__action").length, 4);
    d.querySelectorAll(".case-next .case-next__action")[1].click();
    await tick();
    assert(
      d.querySelector('[role="tabpanel"]').textContent.includes("Non fournie"),
    );
    const tab = d.querySelector('[aria-selected="true"]');
    assert.equal(
      d
        .getElementById(tab.getAttribute("aria-controls"))
        .getAttribute("aria-labelledby"),
      tab.id,
    );
    tab.dispatchEvent(
      new w.KeyboardEvent("keydown", { key: "End", bubbles: true }),
    );
    assert.equal(
      d.querySelector('[aria-selected="true"]').dataset.tab,
      "historique",
    );
    tab.dispatchEvent(
      new w.KeyboardEvent("keydown", { key: "Home", bubbles: true }),
    );
    assert.equal(
      d.querySelector('[aria-selected="true"]').dataset.tab,
      "synthese",
    );
    d.querySelectorAll(".case-next .case-next__action")[0].click();
    d.querySelector(".dos-doc button").click();
    await new Promise((r) => setTimeout(r, 150));
    assert.equal(opened, "job-real-fixture");
    w.location.hash = "#dossiers/tous";
    await tick();
    d.querySelector(".context-guide").click();
    assert(d.querySelector(".studio-guide").open);
    assert(
      d.querySelector(".studio-guide__routes a").hash === "#dossiers/clients",
    );
    d.querySelector("#mainNav").replaceChildren();
    await tick();
    assert.equal(d.querySelectorAll(".studio-guide__route").length, 0);
    d.querySelector(".studio-guide__close").click();
    const form = d.querySelector("#dos-create-form");
    assert(!form.checkValidity());
    await tick();
    assert(!d.querySelector(".studio-form-errors").hidden);
    form.elements.label.value = "Libellé";
    form.elements.label.dispatchEvent(new w.Event("input", { bubbles: true }));
    assert(
      d.querySelector(".studio-form-progress").textContent.startsWith("1 / 1"),
    );
    assert(d.querySelector(".studio-form-errors").hidden);
    fail = true;
    await w.Dossiers.charger();
    assert.equal(d.querySelector("#dos-count-tous").textContent, "—");
    assert(d.querySelector("#dos-list").textContent.includes("Impossible"));
    assert(requests.every((r) => r.method === "GET"));
    console.log(
      "Studio: 45 real-fixture cases, unknown states, pagination, accent search/XSS, source inspector, tabs/Home/End, permission revocation, native form guidance and honest API failure passed.",
    );
  } finally {
    w.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
