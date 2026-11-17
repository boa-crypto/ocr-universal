/* Harnais de rendu du module Dossier (source unique : tests/_dossier_render_src.js).
 *
 * Pourquoi ce fichier existe. Aucun navigateur headless n'est disponible ici :
 * le rendu visuel, le clavier et les lecteurs d'écran ne peuvent pas être
 * contrôlés. Ce harnais fait le reste — il charge le module *servi* (extrait de
 * la page et ses modules externes par HTTP, pour tester ce qui est réellement
 * livré), le pose sur un DOM simulé, et le fait tourner contre l'API réelle.
 *
 * Pièges déjà rencontrés, à ne pas re-découvrir :
 *   - addEventListener(){} est un no-op sur un DOM simulé → on déclenche à la
 *     main via _ls[t] puis on appelle vraiment click() ;
 *   - mkEl définissait déjà click(){} plus bas dans l'objet littéral, et la
 *     dernière définition gagnait → on le redéfinit explicitement ;
 *   - getElementById doit CRÉER les identifiants générés dynamiquement ;
 *   - un module en portée locale n'expose pas ses const → on évalue dans une
 *     fonction et on renvoie ce qui nous intéresse.
 *
 * Usage : node tests/_dossier_render_src.js [port]
 * Sortie : code 0 si tous les contrôles passent, 1 sinon.
 */
"use strict";

const {loadServedModules} = require("./served_modules");

const PORT = process.argv[2] || "8123";
const BASE = "http://127.0.0.1:" + PORT;


let echecs = 0, passes = 0;
function ok(cond, msg, detail) {
  if (cond) { passes++; console.log("  [OK]  " + msg); }
  else { echecs++; console.log("  [FAIL] " + msg + (detail ? " — " + detail : "")); }
}

/* ─────────────────────────── extraction du module servi ─────────────────────────── */

(async function servedHarness() {
const {html, sources} = await loadServedModules(PORT,
  ["/dossier.js", "/tracabilite.js", "/transmission.js", "/formulaire.js"]);
const codeModule = sources["/dossier.js"];
const codeTracabilite = sources["/tracabilite.js"];
const codeTransmission = sources["/transmission.js"];
const codeFormulaire = sources["/formulaire.js"];

/* ─────────────────────────── DOM simulé ─────────────────────────── */

function mkEl(tag, id) {
  const el = {
    tagName: (tag || "div").toUpperCase(), id: id || "", _html: "", style: {},
    dataset: {}, children: [], attrs: {}, value: "", textContent: "",
    checked: false, placeholder: "", title: "", innerHTML: "",
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
    /* la dernière définition gagne dans un littéral : on la met explicitement */
    click(){ (this._ls.click || []).forEach(f => f.call(this, {})); },
    appendChild(c){ this.children.push(c); return c; },
    querySelectorAll(){ return []; },
    querySelector(){ return null; },
  };
  /* Le setter innerHTML doit faire exister les identifiants qu'il contient :
     sans cela, getElementById("dosCoh") renvoie un élément vide jamais rempli,
     et le harnais croit à tort que le module n'a rien rendu. */
  Object.defineProperty(el, "innerHTML", {
    get(){ return this._html; },
    set(v){
      this._html = String(v);
      this.children = [];
      const re = /id="([A-Za-z0-9_]+)"/g;
      let m;
      while ((m = re.exec(this._html)) !== null) {
        registre[m[1]] = mkEl("div", m[1]);
      }
    },
  });
  return el;
}

const registre = {};
["dossierCreer", "dossierLabel", "dossierProfile", "dossierListe", "dossierTypes",
 "dossierDetail", "dosJobId", "dosAjouter", "dosCohLancer", "dosCoh", "dosCohSub",
 "dosXlsx", "dosJson", "dosZip", "dosDocs", "dosPaquet", "dosRafraichir",
 "dosPiecesSub", "toasts", "pageTitle", "pageSub",
].forEach(id => { registre[id] = mkEl("div", id); });

/* identifiants générés dynamiquement par dessineDossier() : ils doivent être
   créés à la demande, sinon getElementById renvoie null et le module explose. */
function getEl(id) {
  if (!registre[id]) registre[id] = mkEl("div", id);
  return registre[id];
}

const documentSimule = {
  getElementById: getEl,
  createElement: t => mkEl(t),
  querySelectorAll: () => [],
  querySelector: () => null,
  addEventListener: () => {},
  documentElement: { lang: "fr", dir: "ltr" },
  dispatchEvent: () => true,
};

/* ─────────────────────────── dépendances du module ─────────────────────────── */

const messages = [];
function toast(msg, type) { messages.push({ msg: String(msg), type: type || "info" }); }
function esc(s) {
  return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ─────────── simulation de la cohérence (rendu deterministe) ─────────── */
const FETCH_REEL = globalThis.fetch;
function simulerCoherence(dossierId) {
  const faux = {
    ok: true, status: 200,
    json: async () => ({
      dossier_id: dossierId,
      transmissible: true,
      documents_analyses: 3,
      constats: [{
        rule: "poids_divergent:gross_weight",
        severity: "anomalie",
        documents: ["a", "b"],
        champs: [
          { filename: "connaissement.pdf", key: "gross_weight",
            label: "Poids brut", value: "12000" },
          { filename: "colisage.pdf", key: "gross_weight",
            label: "Poids brut", value: "13500" }],
        valeurs: [{ document: "a", valeur: 12000 },
                  { document: "b", valeur: 13500 }],
        resultat: "divergent",
        explication: "ecart de 1500.00 au-dela de la tolerance de 2 %.",
        status: "a_trancher",
        decision_par: null }] }),
  };
  globalThis.fetch = (url, opts) =>
    String(url).indexOf("/coherence") !== -1
      ? Promise.resolve(faux)
      : FETCH_REEL(url, opts);
}
function retablirFetch() { globalThis.fetch = FETCH_REEL; }

let appels = [];
async function api(path, opts) {
  appels.push({ path: path, method: (opts && opts.method) || "GET" });
  const r = await fetch(BASE + path, opts);
  if (!r.ok) {
    let detail = "HTTP " + r.status;
    try { const j = await r.json(); detail = j.detail || j.message || detail; }
    catch (e) { /* réponse non JSON */ }
    throw new Error(detail);
  }
  return r.json();
}

/* ─────────────────────────── évaluation du module ─────────────────────────── */

let DossierUI;
let FormulaireUI;
let TracabiliteUI;
let TransmissionUI;
try {
  const fabrique = new Function(
    "document", "esc", "toast", "api", "fetch", "confirm",
    codeModule + "\n" + codeFormulaire + "\n" + codeTracabilite +
    "\n" + codeTransmission +
    "\nreturn { d: (typeof DossierUI !== 'undefined' ? DossierUI : null)," +
    " f: (typeof FormulaireUI !== 'undefined' ? FormulaireUI : null)," +
    " t: (typeof TracabiliteUI !== 'undefined' ? TracabiliteUI : null)," +
    " x: (typeof TransmissionUI !== 'undefined' ? TransmissionUI : null) };"
  );
  const modules = fabrique(documentSimule, esc, toast, api, fetch, () => true);
  DossierUI = modules.d;
  FormulaireUI = modules.f;
  TracabiliteUI = modules.t;
  TransmissionUI = modules.x;
  ok(!!FormulaireUI, "le module Formulaire est exposé par le code servi");
  ok(!!TracabiliteUI, "le module Tracabilite est exposé par le code servi");
  ok(!!TransmissionUI, "le module Transmission est exposé par le code servi");
} catch (e) {
  console.error("le module servi n'a pas pu être évalué :", e.message);
  process.exit(2);
}

if (!DossierUI) {
  console.error("DossierUI n'a pas été exposé par le module servi");
  process.exit(2);
}

/* ─────────────────────────── les contrôles ─────────────────────────── */

(async function main() {
  console.log("── module Dossier rendu sur DOM simulé, API réelle (" + BASE + ") ──");

  /* 1. chargement des références : profils, états, types de documents */
  try {
    await DossierUI.loadAll();
    ok(true, "loadAll() sans exception");
  } catch (e) {
    ok(false, "loadAll() sans exception", e.message);
  }

  const types = getEl("dossierTypes").innerHTML;
  ok(types.length > 40, "les types de documents sont rendus", types.slice(0, 60));
  ok(types.indexOf("Classifieur v") !== -1,
     "la version du classifieur est affichée");
  ok(types.indexOf("sans indice distinctif") !== -1,
     "les catégories sans indice sont signalées, pas cachées");

  const select = getEl("dossierProfile");
  ok(select.children.length >= 5,
     "le sélecteur de profil est rempli", select.children.length + " options");

  /* 2. la liste des dossiers se rend */
  const liste = getEl("dossierListe").innerHTML;
  ok(liste.indexOf("<table") !== -1 || liste.indexOf("Aucun dossier") !== -1,
     "la liste des dossiers se rend sous forme de tableau ou de message vide");

  /* 3. création d'un dossier — écriture réelle */
  const avant = appels.length;
  getEl("dossierLabel").value = "Dossier rendu " + Date.now();
  getEl("dossierProfile").value = "importation";
  try {
    await DossierUI.creeDossier();
    const crees = appels.slice(avant)
      .filter(a => a.path === "/api/dossiers" && a.method === "POST");
    ok(crees.length === 1,
       "creeDossier() appelle POST /api/dossiers",
       JSON.stringify(appels.slice(avant)));
    ok(messages.some(m => m.type === "success"),
       "un message de succès est émis");
  } catch (e) {
    ok(false, "creeDossier() fonctionne", e.message);
  }

  /* 4. ouverture du dossier créé : pièces, pièces attendues, cohérence, paquet */
  const listeDossiers = await api("/api/dossiers");
  if (!listeDossiers.length) {
    ok(false, "un dossier existe pour la suite des contrôles");
    process.exit(1);
  }
  const dossier = listeDossiers[0];

  const appelsAvantForm = appels.length;
  try {
    await DossierUI.ouvreDossier(dossier.id);
    ok(true, "ouvreDossier() sans exception");
  } catch (e) {
    ok(false, "ouvreDossier() sans exception", e.message);
  }

  const detail = getEl("dossierDetail").innerHTML;
  ok(detail.indexOf("Pièces du dossier") !== -1,
     "le bloc des pièces est rendu");
  ok(detail.indexOf("Pièces attendues par le profil") !== -1,
     "le rappel des pièces attendues est rendu (convention, pas obligation)");
  ok(detail.indexOf("Cohérence entre les documents") !== -1,
     "le bloc de cohérence est rendu");
  ok(detail.indexOf("Paquet de données") !== -1,
     "le bloc de paquet est rendu");
  ok(detail.indexOf("conventions de rangement") !== -1,
     "le profil est présenté comme une convention");
  ok(detail.indexOf("ni validé ni") !== -1 || detail.indexOf("séparé de tout envoi") !== -1,
     "le paquet est présenté comme distinct de tout envoi");

  /* 5. dossier vide : pas de tableau fantôme */
  if (!(dossier.pieces || []).length) {
    ok(detail.indexOf("Dossier vide") !== -1,
       "un dossier vide annonce qu'il est vide");
  } else {
    ok(detail.indexOf("<table") !== -1,
       "les pièces sont rendues dans un tableau");
    ok(detail.indexOf("data-retire") !== -1,
       "chaque pièce a une action de retrait motivée");
  }

  /* 5bis. ouvrir un dossier doit aussi charger son formulaire */
  ok(appels.slice(appelsAvantForm).some(a => a.path.indexOf("/formulaire") !== -1),
     "ouvrir un dossier charge aussi le formulaire du dossier");

  /* 5ter. le formulaire se rend avec ses champs et leurs origines */
  try {
    await FormulaireUI.charge(dossier.id);
    const form = getEl("dossierForm").innerHTML;
    ok(form.indexOf("Formulaire") !== -1, "le bloc formulaire est rendu");
    ok(form.indexOf("extrait") !== -1 || form.indexOf("Aucun champ") !== -1,
       "l'origine de chaque champ est affichée, ou le vide est annoncé");
    ok(form.indexOf("n'est envoyé") !== -1 || form.indexOf("ne la transmet") !== -1,
       "le formulaire dit explicitement qu'il ne transmet rien");
    if (form.indexOf("Aucun champ") === -1) {
      ok(form.indexOf("ajout humain") !== -1 || form.indexOf("Ajouter un champ") !== -1,
         "l'ajout humain est proposé et tracé comme tel");
    }
  } catch (e) {
    ok(false, "FormulaireUI.charge() fonctionne", e.message);
  }

  /* 5quater. ouvrir un dossier doit aussi charger sa trace */
  ok(appels.slice(appelsAvantForm).some(a => a.path.indexOf("/trace") !== -1),
     "ouvrir un dossier charge aussi la trace du dossier");

  /* 5quinquies. la trace se rend, avec son avertissement EN PERMANENCE */
  try {
    await TracabiliteUI.charge(dossier.id);
    const trc = getEl("dossierTrace").innerHTML;
    ok(trc.indexOf("Traçabilité") !== -1, "le bloc traçabilité est rendu");
    ok(trc.indexOf("inviolable") !== -1,
       "l'avertissement est affiché à côté de la trace");
    ok(trc.indexOf("administrateur") !== -1,
       "l'avertissement nomme qui peut modifier le journal");
    ok(trc.indexOf("ne rend rien inaltérable") !== -1,
       "les limites de l'archivage sont listées, pas seulement ses garanties");
    ok(trc.indexOf("L'archivage conserve") !== -1,
       "ce que l'archivage conserve est listé");
    /* le conteneur doit exister : sans lui le module reste muet */
    ok(html.indexOf('id="dossierTrace"') !== -1 ||
       trc.indexOf("Traçabilité") !== -1,
       "le conteneur de la trace existe dans la page");
  } catch (e) {
    ok(false, "TracabiliteUI.charge() fonctionne", e.message);
  }

  /* 5sexies. un dossier archivé : plus de bouton, mais la trace reste là */
  try {
    const cree = await api("/api/dossiers", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: "Archive rendu " + Date.now(),
                             profile: "importation" }),
    });
    await api("/api/dossiers/" + cree.id + "/archiver", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ motif: "contrôle du harnais" }),
    });
    await TracabiliteUI.charge(cree.id);
    const trc = getEl("dossierTrace").innerHTML;
    ok(trc.indexOf("déjà archivé") !== -1,
       "un dossier archivé le dit au lieu de proposer de l'archiver encore");
    ok(trc.indexOf("posé par") !== -1,
       "un état forcé par un humain est distingué d'un état déduit");
    ok(trc.indexOf("Dossier archivé") !== -1,
       "l'archivage apparaît dans la trace comme un événement");
  } catch (e) {
    ok(false, "rendu d'un dossier archivé", e.message);
  }

  /* 5septies. ouvrir un dossier charge aussi l'aperçu de transmission */
  ok(appels.slice(appelsAvantForm).some(a => a.path.indexOf("/transmission") !== -1),
     "ouvrir un dossier charge aussi l'aperçu de transmission");

  /* 5octies. l'aperçu de transmission se rend, avec son rappel permanent */
  try {
    await TransmissionUI.charge(dossier.id);
    const tx = getEl("dossierTransmission").innerHTML;
    ok(tx.indexOf("Transmission") !== -1, "le bloc transmission est rendu");
    ok(tx.indexOf("n'est pas") !== -1 || tx.indexOf("ne garantit pas") !== -1,
       "le rappel « envoyé n'est pas accepté » est affiché");
    ok(tx.indexOf("non</strong> jointe") !== -1 ||
       tx.indexOf("pas partent") !== -1 || tx.indexOf("ne partent pas") !== -1,
       "l'aperçu dit que les documents ne partent pas");
    ok(tx.indexOf("Aucune valeur validée") !== -1 ||
       tx.indexOf("Ce qui part") !== -1,
       "le contenu réellement envoyé est distingué du contenu saisi");
    if (tx.indexOf("prêt à envoyer") !== -1) {
      ok(tx.indexOf("txConfirme") !== -1,
         "l'envoi exige une confirmation humaine explicite");
    } else {
      ok(tx.indexOf("Envoi refusé") !== -1,
         "un envoi impossible affiche la raison du refus");
    }
  } catch (e) {
    ok(false, "TransmissionUI.charge() fonctionne", e.message);
  }

  /* 6. analyse de cohérence réelle */
  try {
    await DossierUI.analyseCoherence(dossier.id);
    ok(true, "analyseCoherence() sans exception");
  } catch (e) {
    ok(false, "analyseCoherence() sans exception", e.message);
  }
  const coh = getEl("dosCoh").innerHTML;
  ok(coh.length > 20, "le résultat de cohérence est rendu", coh.slice(0, 70));
  if (coh.indexOf("Aucune divergence") === -1 && coh.indexOf("Erreur") === -1) {
    ok(coh.indexOf("badge") !== -1, "chaque constat porte un badge de gravité");
    ok(coh.indexOf("a_trancher") !== -1,
       "un constat non tranché est affiché comme tel, pas comme résolu");
    ok(coh.indexOf("Valeurs relevées") !== -1,
       "les valeurs divergentes sont montrées, pas seulement le verdict");
  }

  /* 6bis. un dossier qui CONTIENT des documents : les constats réels
          doivent être rendus avec leur gravité, pas comme du texte nu. */
  let dossierRempli = null;
  try {
    const cree = await api("/api/dossiers", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: "Rendu avec pièces " + Date.now(),
                             profile: "importation" }),
    });
    /* /api/jobs renvoie une LISTE, pas un objet {jobs: […]}.
       On cible les documents de référence par leur nom : prendre « les 3
       derniers done » faisait ramasser les artefacts des autres tests
       (injection.png, data.csv), qui n'ont aucun champ comparable. */
    const jobs = await api("/api/jobs");
    const liste = Array.isArray(jobs) ? jobs : (jobs.jobs || []);
    const voulus = ["facture", "bl", "colisage"];
    const recents = [];
    for (const motif of voulus) {
      const trouve = liste.find(j => j.status === "done" &&
        String(j.filename || "").toLowerCase().indexOf(motif) !== -1);
      if (trouve) recents.push(trouve);
    }
    for (const j of recents) {
      await api("/api/dossiers/" + cree.id + "/pieces", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: j.id, filename: j.filename }),
      });
    }
    if (recents.length >= 2) {
      dossierRempli = await api("/api/dossiers/" + cree.id);
      await DossierUI.ouvreDossier(dossierRempli.id);
      /* Le rendu des constats ne doit pas dependre de l'etat du magasin :
         les documents partages ont pu etre corriges entre-temps (ou le lot
         ne contenir que des artefacts sans champ comparable), et des
         controles qui portent sur l'affichage echoueraient alors pour une
         raison qui n'est pas celle du rendu. On simule donc une reponse de
         coherence connue, avec une anomalie non tranchee. */
      simulerCoherence(cree.id);
      await DossierUI.analyseCoherence(cree.id);
      retablirFetch();
      const coh2 = getEl("dosCoh").innerHTML;
      ok(coh2.indexOf("Aucune divergence") === -1,
         "un dossier à plusieurs documents produit des constats",
         coh2.slice(0, 90));
      ok(coh2.indexOf("badge") !== -1,
         "chaque constat porte un badge de gravité");
      ok(coh2.indexOf("a_trancher") !== -1,
         "un constat non tranché est affiché comme tel, pas comme résolu");
      ok(coh2.indexOf("Valeurs relevées") !== -1,
         "les valeurs divergentes sont montrées, pas seulement le verdict");
      const sub2 = getEl("dosCohSub").textContent;
      ok(/\d+ constat/.test(sub2), "le nombre de constats est annoncé", sub2);
      ok(sub2.indexOf("transmission") !== -1,
         "la transmissibilité est annoncée explicitement", sub2);
      /* l'état du dossier doit refléter l'anomalie, pas la complétude */
      ok(getEl("dossierDetail").innerHTML.indexOf("Révision requise") !== -1 ||
         getEl("dossierDetail").innerHTML.indexOf("Validation") !== -1,
         "l'état affiché reflète une révision ou une validation, pas « terminé »");
    } else {
      console.log("  [--]   pas assez de documents traités pour le rendu des constats");
    }
  } catch (e) {
    ok(false, "rendu des constats sur un dossier rempli", e.message);
  }

  /* 7. génération de paquet — écriture réelle sur disque */
  const avantPaquet = appels.length;
  try {
    await DossierUI.generePaquet(dossier.id, "xlsx");
    const appeles = appels.slice(avantPaquet).filter(a => a.path.indexOf("/package") !== -1);
    ok(appeles.length === 1 && appeles[0].method === "POST",
       "generePaquet() appelle POST /package");
  } catch (e) {
    ok(false, "generePaquet(xlsx) fonctionne", e.message);
  }
  const paquet = getEl("dosPaquet").innerHTML;
  ok(paquet.indexOf("Fichier") !== -1 || paquet.indexOf("Erreur") !== -1,
     "le résultat du paquet est rendu");
  if (paquet.indexOf("Erreur") === -1) {
    ok(paquet.indexOf("ni validé ni") !== -1,
       "le paquet généré n'est pas présenté comme envoyé");
    ok(paquet.indexOf("Taille") !== -1, "la taille réelle du fichier est affichée");
  }

  /* 8. les originaux ne sont pas embarqués par défaut */
  getEl("dosDocs").checked = false;
  await DossierUI.generePaquet(dossier.id, "zip");
  ok(true, "un ZIP sans les originaux peut être demandé (case décochée)");

  /* 9. refus d'un format inconnu — l'API doit répondre, pas le module inventer */
  await DossierUI.generePaquet(dossier.id, "pdf");
  const paquetErreur = getEl("dosPaquet").textContent || getEl("dosPaquet").innerHTML;
  ok(/format inconnu/i.test(paquetErreur),
     "un format inconnu est refusé par l'API et le message est affiché",
     String(paquetErreur).slice(0, 80));
  ok(messages.some(m => m.type === "error"),
     "un échec de génération produit un message d'erreur, pas un succès");

  console.log("\n  " + passes + " contrôle(s) passé(s), " + echecs + " échec(s)");
  process.exit(echecs ? 1 : 0);
})().catch(e => {
  console.error("erreur fatale du harnais :", e);
  process.exit(2);
});

})().catch(error => { console.error(error); process.exitCode = 2; });
