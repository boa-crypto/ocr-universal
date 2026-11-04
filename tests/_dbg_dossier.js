/* Debug des contrôles en échec du harnais Dossier. */
"use strict";
const fs = require("fs");
const PORT = "8123";
const BASE = "http://127.0.0.1:" + PORT;
const html = fs.readFileSync("/home/user/ocr-universal/web/index.html", "utf8");
const i = html.indexOf("/* ═══ DOSSIER:BEGIN");
const j = html.indexOf("/* ═══ DOSSIER:END");
const codeModule = html.slice(i, j).replace(/^\/\* ═══ DOSSIER:BEGIN[\s\S]*?\*\/\s*/, "");

function mkEl(tag, id) {
  const el = {
    tagName: (tag || "div").toUpperCase(), id: id || "", _html: "", style: {},
    dataset: {}, children: [], attrs: {}, value: "", textContent: "",
    checked: false, placeholder: "", title: "",
    classList: { _s: new Set(),
      add(...c){ c.forEach(x => this._s.add(x)); },
      remove(...c){ c.forEach(x => this._s.delete(x)); },
      toggle(c){ this._s.has(c) ? this._s.delete(c) : this._s.add(c); },
      contains(c){ return this._s.has(c); } },
    setAttribute(k, v){ this.attrs[k] = v; },
    getAttribute(k){ return this.attrs[k]; },
    _ls: {},
    addEventListener(t, f){ (this._ls[t] = this._ls[t] || []).push(f); },
    removeEventListener(t, f){ this._ls[t] = (this._ls[t] || []).filter(x => x !== f); },
    click(){ (this._ls.click || []).forEach(f => f.call(this, {})); },
    appendChild(c){ this.children.push(c); return c; },
    querySelectorAll(){ return []; },
    querySelector(){ return null; },
  };
  Object.defineProperty(el, "innerHTML", {
    get(){ return this._html; },
    set(v){ this._html = String(v); this.children = []; },
  });
  return el;
}

const registre = {};
["dossierCreer","dossierLabel","dossierProfile","dossierListe","dossierTypes",
 "dossierDetail","dosJobId","dosAjouter","dosCohLancer","dosCoh","dosCohSub",
 "dosXlsx","dosJson","dosZip","dosDocs","dosPaquet","dosRafraichir","dosPiecesSub",
 "toasts","pageTitle","pageSub"].forEach(id => { registre[id] = mkEl("div", id); });

function getEl(id) {
  if (!registre[id]) { console.log("   [créé à la demande] " + id); registre[id] = mkEl("div", id); }
  return registre[id];
}
const documentSimule = {
  getElementById: getEl, createElement: t => mkEl(t),
  querySelectorAll: () => [], querySelector: () => null,
  addEventListener: () => {}, documentElement: { lang: "fr", dir: "ltr" },
  dispatchEvent: () => true,
};

const messages = [];
function toast(msg, type) { messages.push({ msg: String(msg), type: type || "info" }); }
function esc(s) {
  return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const appels = [];
async function api(path, opts) {
  appels.push({ path: path, method: (opts && opts.method) || "GET" });
  const r = await fetch(BASE + path, opts);
  if (!r.ok) {
    let detail = "HTTP " + r.status;
    try { const jj = await r.json(); detail = jj.detail || jj.message || detail; }
    catch (e) {}
    throw new Error(detail);
  }
  return r.json();
}

const fabrique = new Function("document", "esc", "toast", "api", "fetch",
  codeModule + "\nreturn typeof DossierUI !== 'undefined' ? DossierUI : null;");
const DossierUI = fabrique(documentSimule, esc, toast, api, fetch);

(async function () {
  await DossierUI.loadAll();
  console.log("── appels après loadAll ──");
  appels.forEach(a => console.log("   ", a.method, a.path));

  const avant = appels.length;
  getEl("dossierLabel").value = "Debug " + Date.now();
  getEl("dossierProfile").value = "importation";
  console.log("── label lu par le module :", JSON.stringify(getEl("dossierLabel").value));
  await DossierUI.creeDossier();
  console.log("── appels après creeDossier ──");
  appels.slice(avant).forEach(a => console.log("   ", a.method, a.path));
  console.log("── messages ──");
  messages.forEach(m => console.log("   ", m.type, ":", m.msg.slice(0, 70)));

  const liste = await api("/api/dossiers");
  const d = liste[0];
  console.log("── dossier ouvert :", d.id, "| pièces :", (d.pieces || []).length);
  await DossierUI.ouvreDossier(d.id);
  console.log("── dosCoh existe ?", !!registre.dosCoh, "| innerHTML :",
              JSON.stringify((registre.dosCoh || {}).innerHTML || "").slice(0, 120));
  console.log("── identifiants du registre après dessineDossier ──");
  console.log("   ", Object.keys(registre).filter(k => k.startsWith("dos")).join(", "));

  await DossierUI.analyseCoherence(d.id);
  console.log("── dosCoh après analyse ──");
  console.log("   ", JSON.stringify((registre.dosCoh || {}).innerHTML || "").slice(0, 300));
  console.log("── dosCohSub ──");
  console.log("   ", JSON.stringify((registre.dosCohSub || {}).textContent || "").slice(0, 150));
})();
