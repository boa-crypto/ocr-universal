const { JSDOM } = require("jsdom"),
  fs = require("node:fs"),
  assert = require("node:assert/strict");
const dom = new JSDOM("<!doctype html><body></body>", {
    runScripts: "outside-only",
  }),
  w = dom.window;
w.eval(
  fs
    .readFileSync("web/components/forms/Form.js", "utf8")
    .replace(/export\s*\{[^}]+\};?\s*$/, ""),
);
const host = w.document.createElement("form-input");
host.setAttribute("type", "password");
w.document.body.append(host);
let input = host.shadowRoot.querySelector("input");
assert.equal(input.type, "password");
host.value = 0;
assert.equal(input.value, "0");
input.focus();
input.value = "Saisie continue";
input.dispatchEvent(new w.Event("input", { bubbles: true }));
assert.equal(host.value, "Saisie continue");
assert.equal(host.shadowRoot.querySelector("input"), input);
assert.equal(host.shadowRoot.activeElement, input);
host.error = "Valeur <img src=x> à vérifier";
assert.equal(host.shadowRoot.querySelector("input"), input);
assert.equal(input.getAttribute("aria-invalid"), "true");
assert.equal(host.shadowRoot.querySelector(".form-error img"), null);
host.clearError();
assert.equal(host.shadowRoot.querySelector("input"), input);
host.setAttribute("readonly", "");
assert(host.shadowRoot.querySelector("input").readOnly);
host.removeAttribute("readonly");
input = host.shadowRoot.querySelector("input");
input.value = "Après mise à jour";
input.dispatchEvent(new w.Event("input", { bubbles: true }));
assert.equal(host.value, "Après mise à jour");
const select = w.document.createElement("form-select");
select.innerHTML =
  '<option value="a">Algérie</option><option value="o">Oran</option>';
w.document.body.append(select);
let changes = 0;
select.addEventListener("form-input-change", () => changes++);
const native = select.shadowRoot.querySelector("select");
native.value = "o";
native.dispatchEvent(new w.Event("input", { bubbles: true }));
native.dispatchEvent(new w.Event("change", { bubbles: true }));
assert.equal(select.value, "o");
assert.equal(changes, 1);
const textarea = w.document.createElement("form-textarea");
w.document.body.append(textarea);
assert(textarea.shadowRoot.querySelector("textarea"));
dom.window.close();
console.log(
  "Shadow components: native types, continuous input/focus, zero, safe error message, readonly rebinding, select single-change and textarea passed.",
);
