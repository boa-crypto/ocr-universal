const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  { JSDOM } = require("jsdom");
const tick = () => new Promise((r) => setTimeout(r, 25));
function setup() {
  const dom = new JSDOM(
    '<div class="topbar"><h2 id="pageTitle">Cockpit</h2><div class="top-chips"></div></div><nav id="mainNav"><a href="#cockpit">Tableau de bord</a><div class="nav-group"><span class="nav-label">Documents</span><a href="#documents/import">Importer les pièces<span class="nav-badge">99</span></a><a href="#documents/revue">Révision humaine</a></div></nav><main class="workspace"><section id="tab-cockpit"><div class="hero"></div></section></main>',
    {
      url: "https://test.invalid/#cockpit",
      runScripts: "outside-only",
      pretendToBeVisual: true,
    },
  );
  const w = dom.window;
  w.HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  w.HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new w.Event("close"));
  };
  w.fetch = () => {
    throw Error("No new network request expected");
  };
  w.eval(fs.readFileSync("web/product-experience.js", "utf8"));
  w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
  return dom;
}
(async () => {
  const dom = setup(),
    w = dom.window,
    d = w.document;
  try {
    assert.equal(d.querySelectorAll(".action-path").length, 2);
    assert(!d.body.textContent.includes("Traiter les dossiers"));
    assert.equal(d.querySelector("#pageTitle").textContent, "Tableau de bord");
    const trigger = d.querySelector(".intent-trigger");
    trigger.focus();
    trigger.click();
    assert(d.querySelector("dialog").open);
    const input = d.querySelector(".intent-input");
    input.value = "revision";
    input.dispatchEvent(new w.Event("input"));
    assert.equal(d.querySelectorAll(".intent-result").length, 1);
    assert.equal(d.querySelector(".intent-result").hash, "#documents/revue");
    input.value = "<img src=x onerror=evil()>";
    input.dispatchEvent(new w.Event("input"));
    assert.equal(d.querySelectorAll("img").length, 0);
    assert(d.querySelector(".intent-empty"));
    input.value = "importer";
    input.dispatchEvent(new w.Event("input"));
    input.dispatchEvent(
      new w.KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }),
    );
    assert.equal(d.activeElement.hash, "#documents/import");
    input.dispatchEvent(
      new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    );
    await tick();
    assert.equal(w.location.hash, "#documents/import");
    assert(!d.querySelector("dialog").open);
    assert.equal(d.activeElement, trigger);
    assert.equal(
      d.querySelector("#pageTitle").textContent,
      "Importer les pièces",
    );
    trigger.click();
    d.querySelector("#mainNav").replaceChildren();
    await tick();
    assert.equal(d.querySelectorAll(".intent-result").length, 0);
    assert(d.querySelector(".action-paths").hidden);
    assert(d.querySelector(".intent-empty").textContent.includes("droits"));
    d.querySelector(".intent-close").click();
    d.dispatchEvent(
      new w.KeyboardEvent("keydown", {
        key: "j",
        ctrlKey: true,
        bubbles: true,
      }),
    );
    assert(d.querySelector("dialog").open);
    d.dispatchEvent(
      new w.KeyboardEvent("keydown", {
        key: "j",
        ctrlKey: true,
        bubbles: true,
      }),
    );
    assert(!d.querySelector("dialog").open);
    console.log(
      "7 scénarios produit réussis : droits, orientation, recherche, XSS, clavier, focus, révocation.",
    );
  } finally {
    w.close();
  }
  const toastDom = new JSDOM("<ocr-toast-container></ocr-toast-container>", {
    runScripts: "outside-only",
  });
  try {
    const tw = toastDom.window;
    let called = 0;
    const legacy = (tw.toast = function () {
      called++;
    });
    tw.eval(
      fs
        .readFileSync("web/components/toast/Toast.js", "utf8")
        .replace("export { ToastContainer };", ""),
    );
    const c = tw.document.querySelector("ocr-toast-container");
    c.show({
      title: "<img src=x onerror=evil()>",
      message: "<script>evil()</script>",
      type: 'bad" onclick="evil()',
      duration: "bad",
    });
    assert(!c.shadowRoot.querySelector("img,script"));
    assert(c.shadowRoot.querySelector(".toast--info"));
    assert.equal(tw.toast, legacy);
    tw.toast("test");
    assert.equal(called, 1);
    assert.equal(typeof tw.UniOCRToast.success, "function");
    c.remove(c.toasts[0].id);
    await new Promise((r) => tw.setTimeout(r, 400));
    assert.equal(c.toasts.length, 0);
    assert(!c.shadowRoot.querySelector(".toast"));
    console.log(
      "Toast natif : parsing, échappement, type, compatibilité et fermeture sans animation réussis.",
    );
  } finally {
    toastDom.window.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
