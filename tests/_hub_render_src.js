
const {loadServedModules} = require("./served_modules");
const PORT = process.env.PORT || "8000";
(async function servedHarness() {
const {html, sources} = await loadServedModules(PORT, ["/connectors.js"]);
const hub = sources["/connectors.js"];

function mkEl(tag) {
  return {
    tagName: (tag || "div").toUpperCase(), id: "", _html: "", style: {},
    dataset: {},
    classList: { _s: new Set(),
      add(...c){c.forEach(x=>this._s.add(x));}, remove(...c){c.forEach(x=>this._s.delete(x));},
      toggle(c){this._s.has(c)?this._s.delete(c):this._s.add(c);}, contains(c){return this._s.has(c);} },
    children: [], attrs: {}, value: "", textContent: "",
    set innerHTML(v){ this._html = String(v); this.children = []; },
    get innerHTML(){ return this._html; },
    setAttribute(k,v){this.attrs[k]=v;}, getAttribute(k){return this.attrs[k];},
    _ls: {},
    addEventListener(t, f){ (this._ls[t] = this._ls[t] || []).push(f); },
    removeEventListener(t, f){ this._ls[t] = (this._ls[t]||[]).filter(x => x !== f); },
    click(){ (this._ls.click || []).forEach(f => {
      try { const p = f({ preventDefault(){}, target: this });
            if (p && p.catch) p.catch(e => console.log("  [REJET] " + flat(e))); }
      catch (e) { console.log("  [THROW] " + flat(e)); } }); },
    appendChild(c){this.children.push(c);return c;},
    append(...c){this.children.push(...c);}, remove(){}, removeChild(){},
    querySelector(){ return mkEl("div"); }, querySelectorAll(){ return []; },
    focus(){}, offsetWidth: 0,
  };
}
function flat(e) {
  const st = (e && e.stack) ? e.stack.split("\n").slice(0,5).join(" << ") : String(e);
  return st.slice(0, 300);
}

const ids = {};
for (const id of html.match(/id="([^"]+)"/g).map(s => s.slice(4, -1))) {
  const e = mkEl("div"); e.id = id; ids[id] = e;
}
const panes = {};
for (const m of html.matchAll(/data-cnx="([a-z]+)"/g)) {
  const e = mkEl("div"); e.dataset.cnx = m[1]; panes[m[1]] = e;
}
const CONTENT = {
  overview:"cnxOverview", catalog:"cnxCatalog", active:"cnxActive",
  add:"cnxWizard", config:"cnxConfig", mapping:"cnxMapping", forms:"cnxForms",
  flow:"cnxModes", history:"cnxHistory", errors:"cnxErrors",
  security:"cnxSecurity", audit:"cnxAudit",
};

function getEl(id) {
  if (!ids[id]) { const e = mkEl("div"); e.id = id; ids[id] = e; }
  return ids[id] || null;
}
global.document = {
  getElementById: id => getEl(id),
  querySelector: () => mkEl("div"),
  querySelectorAll: sel => (sel === ".cnx-pane" ? Object.values(panes) : []),
  createElement: t => mkEl(t),
  addEventListener(){},
};
global.window = { addEventListener(){}, location: { hostname: "localhost" } };
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
const _fetch = globalThis.fetch.bind(globalThis);
global.fetch = async (path, opts) => {
  const r = await _fetch("http://127.0.0.1:" + PORT + path, opts);
  const t = await r.text();
  return { ok: r.ok, status: r.status, text: async () => t,
           json: async () => JSON.parse(t) };
};
global.esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
global.api = async (path, opts) => {
  const r = await fetch(path, opts);
  const t = await r.text();
  if (!r.ok) { let d = t; try { d = JSON.parse(t).detail || t; } catch (_) {}
               throw new Error(d || ("HTTP " + r.status)); }
  return JSON.parse(t);
};
global.CustomEvent = class { constructor(t,d){ this.type=t; this.detail=d; } };
global.Event = class { constructor(t){ this.type=t; } };

(async () => {
  eval(hub + "\n;globalThis.CnxHub = CnxHub;");
  if (typeof CnxHub === "undefined") { console.log("ERREUR: CnxHub non defini"); process.exit(1); }
  process.on("unhandledRejection", e => console.log("  [NON GERE] " + flat(e)));

  // ── 12 sous-menus ──
  console.log("=== rendu des 12 sous-menus (JS reel, API reelle) ===");
  await CnxHub.loadAll();
  let ko = 0;
  const SECTIONS = ["overview","catalog","active","add","config","mapping",
                    "forms","flow","history","errors","security","audit"];
  for (const s of SECTIONS) {
    CnxHub.show(s);
    await new Promise(r => setTimeout(r, 900));
    const pane = ids[CONTENT[s]] || panes[s];
    const html_ = (pane && pane.innerHTML) || "";
    const tags = html_.match(/<(div|table|button|select|h4|span|input)\b/g) || [];
    // un état vide explicite (« cnx-empty » avec consigne) est un rendu valide
    const etatVide = html_.indexOf("cnx-empty") !== -1 && html_.length > 40;
    const ok = (html_.length > 200 && tags.length >= 3) || etatVide;
    console.log("  " + (ok ? "[OK]" : "[KO]") + " " + s.padEnd(10)
      + String(html_.length).padStart(6) + " car., " + String(tags.length).padStart(3) + " elements");
    if (!ok) { ko++; console.log("        " + html_.slice(0, 200)); }
  }
  console.log("  sous-menus generes : "
    + ((ids["cnxSubnav"] || {}).innerHTML || "").match(/cnx-sub/g || []).length);

  // ── assistant 9 etapes ──
  console.log("\n=== assistant de creation : 9 etapes ===");
  let ko2 = 0;
  for (let step = 0; step < 9; step++) {
    for (const id of Object.keys(ids)) if (ids[id]) ids[id]._ls = {};
    CnxHub.show("add");
    await new Promise(r => setTimeout(r, 500));
    const h = (ids["cnxWizard"] || {}).innerHTML || "";
    const title = (h.match(/<h4>([^<]*)<\/h4>/) || [])[1] || "(vide)";
    const puces = ((ids["cnxSteps"] || {}).innerHTML || "").match(/<li/g) || [];
    const champs = (h.match(/<(input|select|textarea)\b/g) || []).length;
    const n = step + 1;
    const ok = h.indexOf("Étape " + n + "/9") !== -1 && puces.length === 9;
    console.log("  " + (ok ? "[OK]" : "[KO]") + " etape " + n + "/9 : "
      + title.trim().slice(0,44) + " | " + champs + " champ(s) | " + puces.length + " puces");
    if (!ok) { ko2++; console.log("        " + h.slice(0, 160)); }
    if (h.indexOf('id="wzNext"') === -1) {
      console.log("        derniere etape — bouton « Creer le connecteur » present : "
        + (h.indexOf('id="wzDone"') !== -1));
      break;
    }
    ids["wzNext"].click();
    await new Promise(r => setTimeout(r, 900));
  }
  console.log("\n" + ((ko || ko2) ? "ECHEC" : "TOUS LES CONTROLES PASSENT"));
  process.exit((ko || ko2) ? 1 : 0);
})();

})().catch(error => { console.error(error); process.exitCode = 2; });
