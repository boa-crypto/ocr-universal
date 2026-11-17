#!/usr/bin/env node
/*
 * Contrôle statique de l'interface — remplace le test navigateur qui n'est pas
 * possible dans cet environnement (aucun headless disponible).
 *
 * Il vérifie, sans navigateur :
 *   1. la syntaxe du script (<script> de web/index.html) — node --check
 *   2. son chargement sur un DOM simulé, SANS ReferenceError
 *      (c'est ce contrôle qui a révélé que api() était appelée sans être définie)
 *   3. la cohérence entre les identifiants du HTML et ceux que le script utilise
 *
 * Usage :  node tests/ui_stub_check.js
 * Sortie : code 0 si tout passe, 1 sinon.
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const HTML = path.join(ROOT, "web", "index.html");

let failures = 0;
const ok = m => console.log("  [OK]   " + m);
const ko = m => { console.log("  [FAIL] " + m); failures++; };

// ── extraction ──────────────────────────────────────────────────────────────
const html = fs.readFileSync(HTML, "utf8");
// TOUS les blocs <script>, pas seulement le premier : un module ajouté en fin
// de fichier (ex. Connecteur Hub) échappait au contrôle et une erreur de
// syntaxe y passait inaperçue, rendant la page muette.
const blocks = [];
for (const m of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) blocks.push(m[1]);
if (!blocks.length) { console.error("bloc <script> introuvable"); process.exit(1); }
const tempDir = fs.mkdtempSync(path.join(require("os").tmpdir(), "unocr-ui-"));
const jsPath = path.join(tempDir, "_ui_extracted.js");
fs.writeFileSync(jsPath, blocks.join("\n;\n"));

// ── 1. syntaxe ──────────────────────────────────────────────────────────────
for (let i = 0; i < blocks.length; i++) {
  const one = path.join(tempDir, `_ui_bloc_${i}.js`);
  fs.writeFileSync(one, blocks[i]);
  try {
    execFileSync(process.execPath, ["--check", one], { stdio: "pipe" });
    ok(`syntaxe du script (bloc ${i}, ${blocks[i].length} car.)`);
  } catch (e) {
    ko(`syntaxe du script (bloc ${i}) :\n` + e.stderr.toString());
  }
}

// ── 2. DOM simulé ───────────────────────────────────────────────────────────
function el(tag) {
  return {
    tagName: (tag || "div").toUpperCase(), id: "", style: {}, dataset: {},
    classList: {
      _s: new Set(),
      add(...c) { c.forEach(x => this._s.add(x)); },
      remove(...c) { c.forEach(x => this._s.delete(x)); },
      toggle(c) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); },
      contains(c) { return this._s.has(c); }
    },
    children: [], attrs: {},
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; },
    addEventListener() {}, removeEventListener() {},
    appendChild(c) { this.children.push(c); return c; },
    append(...c) { this.children.push(...c); },
    remove() {}, removeChild() {}, insertAdjacentHTML() {},
    closest() { return null; }, matches() { return false; },
    querySelector() { return el("div"); },
    querySelectorAll() { return []; },
    focus() {}, blur() {}, select() {}, click() {}, scrollIntoView() {},
    setSelectionRange() {},
    getBoundingClientRect() {
      return { left: 0, top: 0, right: 100, bottom: 100, width: 100, height: 100 };
    },
    getContext() {
      return { drawImage() {}, clearRect() {}, fillRect() {},
               getImageData() { return { data: [] }; }, putImageData() {} };
    },
    toBlob(cb) { if (cb) cb(null); },
    files: [], disabled: false, value: "", textContent: "", innerHTML: "",
    offsetWidth: 0, offsetHeight: 0
  };
}

const byId = {};
for (const id of html.match(/id="([^"]+)"/g).map(s => s.slice(4, -1))) {
  byId[id] = el("div");
  byId[id].id = id;
}

global.document = {
  documentElement: el("html"), body: el("body"), head: el("head"),
  getElementById: id => byId[id] || null,
  querySelector: () => el("div"), querySelectorAll: () => [],
  createElement: t => el(t), addEventListener() {}, removeEventListener() {}
};
global.window = {
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  addEventListener() {},
  location: { hostname: "localhost", origin: "http://localhost:8000",
              href: "http://localhost:8000/", host: "localhost:8000" }
};
global.location = global.window.location;
global.navigator = {
  mediaDevices: { getUserMedia: async () => { throw new Error("stub"); } },
  userAgent: "stub", language: "fr"
};
const store = { _d: {} };
global.localStorage = {
  getItem(k) { return k in store._d ? store._d[k] : null; },
  setItem(k, v) { store._d[k] = String(v); },
  removeItem(k) { delete store._d[k]; }
};
global.fetch = async () => ({ ok: true, status: 200,
  json: async () => [], text: async () => "", blob: async () => ({ size: 0 }) });
global.requestAnimationFrame = cb => cb(0);
global.setInterval = () => 0;
global.setTimeout = (cb) => { if (typeof cb === "function") { try { cb(0); } catch (_) {} } return 0; };
global.clearInterval = () => {};
global.clearTimeout = () => {};
global.Event = class { constructor(t) { this.type = t; } };
global.CustomEvent = class extends global.Event {};
global.FormData = class { append() {} };
global.File = class {};
global.Blob = class {};
global.URL = { createObjectURL: () => "", revokeObjectURL() {} };
global.HTMLElement = class {};
global.Node = class {};
global.Element = class {};
global.MutationObserver = class { observe() {} disconnect() {} };
global.IntersectionObserver = class { observe() {} disconnect() {} };
global.ResizeObserver = class { observe() {} disconnect() {} };
global.alert = () => {};
global.confirm = () => true;
global.prompt = () => null;
global.structuredClone = o => JSON.parse(JSON.stringify(o));
global.performance = { now: () => 0 };

try {
  require(jsPath);
  ok("chargement sur DOM simulé sans ReferenceError");
} catch (e) {
  ko("chargement du script : " + e.constructor.name + " — " + e.message);
}

// ── 3. cohérence des identifiants ───────────────────────────────────────────
const htmlIds = new Set([...html.matchAll(/id="([^"]+)"/g)].map(x => x[1]));
const used = new Set();
for (const b of blocks) {
  for (const x of b.matchAll(/getElementById\("([^"]+)"\)/g)) used.add(x[1]);
  for (const x of b.matchAll(/\$\(\s*["']([\w-]+)["']\s*\)/g)) used.add(x[1]);
}
const missing = [...used].filter(i => !htmlIds.has(i) && i !== "overlaySvg");
if (missing.length) ko("identifiants absents du HTML : " + missing.join(", "));
else ok(`${used.size} identifiants utilisés par le script, tous présents`);

// ── 3ter. taille du fichier unique (garde-fou) ───────────────────────────────
// La page est volontairement un fichier unique hors ligne. Sans plafond, rien
// n'empêche qu'elle double silencieusement. 800 Ko = ~20 % de marge.
const PLAFOND_KO = 800;
const tailleKo = Math.round(html.length / 1024);
if (tailleKo > PLAFOND_KO) {
  ko(`web/index.html fait ${tailleKo} Ko, au-delà du plafond de ${PLAFOND_KO} Ko : ` +
     `découper le module ou supprimer ce qui est mort.`);
} else {
  ok(`taille du fichier unique : ${tailleKo} Ko (plafond ${PLAFOND_KO} Ko)`);
}

// Les erreurs de rendu sont des échecs ; seul ECONNREFUSED est facultatif.
async function checkRenders() {
  if (process.argv.includes("--static")) return;
  const {readLocal} = require("./served_modules");
  const port = process.env.PORT || "8000";
  try { await readLocal(port, "/api/health"); }
  catch (error) {
    if (error.code === "ECONNREFUSED" && !process.argv.includes("--require-render")) {
      console.log("  [--]   serveur absent : rendu non exécuté"); return;
    }
    ko("serveur de rendu : " + error.message); return;
  }
  for (const [name, script, expected] of [
    ["Connecteur Hub", "_hub_render_src.js", 21],
    ["Parcours documentaire", "_dossier_render_src.js", 55],
  ]) {
    try {
      const out = execFileSync(process.execPath,
        [path.join(__dirname, script), String(port)],
        {encoding: "utf8", timeout: 180000, env: {...process.env, PORT: String(port)}});
      const {validateRenderOutput} = require("./render_output");
      const count = validateRenderOutput(out, expected);
      ok(`${name} : ${count} controles de rendu executes`);
    } catch (error) {
      ko(name + " : échec du harnais\n" + (error.stdout || "") + (error.stderr || error.message));
    }
  }
}

// ── 4. aucune ressource réseau externe ──────────────────────────────────────
// On n'interdit que ce qui quitte la machine : URL absolue, autre hôte, CDN.
// Les fichiers du même origine (/manifest.webmanifest, /icon.svg) sont servis
// par l'API locale : ils ne cassent pas le fonctionnement hors ligne.
const links = [...html.matchAll(/<link[^>]*href="([^"]+)"/g)].map(x => x[1]);
const externes = links.filter(h => /^(https?:)?\/\//i.test(h));
if (externes.length) ko("balises <link> externes : " + externes.join(", "));
else ok(`aucune ressource externe (${links.length} lien(s) local/locale)`);

fs.unlinkSync(jsPath);
console.log("");
if (failures) console.log(failures + " contrôle(s) statiques en échec.");
else console.log("Tous les contrôles statiques de l'interface passent.");

// Le statut final attend tous les contrôles asynchrones.
fs.rmSync(tempDir, {recursive: true, force: true});
checkRenders().then(() => { process.exitCode = failures ? 1 : 0; })
  .catch(error => { console.error(error); process.exitCode = 1; });
