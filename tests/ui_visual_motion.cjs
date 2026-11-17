const assert = require("node:assert/strict"),
  fs = require("fs"),
  { JSDOM } = require("jsdom");
(async () => {
  let dom = new JSDOM(
    '<main class="workspace"><section class="page"><a class="action-path" href="#cockpit">Import</a><div id="cockpit-kpis"><b class="kpi-val">17</b></div></section><div class="action-paths"></div></main>',
    {
      url: "https://test.invalid",
      runScripts: "outside-only",
      pretendToBeVisual: true,
    },
  );
  let w = dom.window,
    calls = [],
    cancelled = 0,
    preference = {
      matches: false,
      addEventListener(_, fn) {
        this.changed = fn;
      },
    };
  w.matchMedia = () => preference;
  w.fetch = () => {
    throw Error("No network permitted");
  };
  w.Element.prototype.animate = function (frames, options) {
    calls.push({ node: this, frames, options });
    return {
      cancel() {
        cancelled++;
      },
    };
  };
  w.IntersectionObserver = class {
    constructor(fn) {
      this.fn = fn;
    }
    observe(target) {
      this.fn([{ target, isIntersecting: true }]);
    }
    unobserve() {}
  };
  try {
    w.eval(fs.readFileSync("web/visual-motion.js", "utf8"));
    w.document.dispatchEvent(new w.Event("DOMContentLoaded"));
    assert.equal(w.document.querySelectorAll(".mobile-document-art").length, 1);
    assert.equal(w.document.querySelector(".kpi-val").textContent, "17");
    w.document.querySelector(".action-path").click();
    assert(calls.length >= 2);
    let n = w.document.querySelector(".kpi-val");
    n.textContent = "29";
    await new Promise((r) => w.setTimeout(r, 30));
    assert.equal(n.textContent, "29");
    assert(calls.some((c) => c.node === n));
    preference.matches = true;
    preference.changed();
    assert(cancelled > 0);
    let count = calls.length;
    n.textContent = "30";
    w.document.querySelector(".action-path").click();
    await new Promise((r) => w.setTimeout(r, 30));
    assert.equal(calls.length, count);
    assert.equal(n.textContent, "30");
    assert(calls.every((c) => c.options.duration <= 380));
    assert.equal(w.document.querySelectorAll(".mobile-document-art").length, 1);
    console.log(
      "Motion: progressive reveal, bounded feedback, data integrity, dynamic reduced-motion cancellation, idempotency passed.",
    );
  } finally {
    w.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
