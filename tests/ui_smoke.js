/* Vérifications navigateur de l'interface UniOCR (jsdom).
 *
 * Usage (serveur démarré) :
 *   npm install
 *   npm run ui:smoke -- http://127.0.0.1:8000
 *
 * Ce script répond à une question simple : **quand on clique, que se passe-t-il
 * vraiment ?** Il charge l'application comme un navigateur, parcourt les écrans
 * critiques, déclenche quelques interactions et échoue si un écran est vide, si
 * une requête tombe en erreur serveur, ou si une action n'ouvre rien.
 *
 * Trois garanties de méthode :
 *   - **aucune écriture** : si une requête non-GET est émise, le script échoue.
 *     Il observe, il ne modifie pas les données de l'utilisateur ;
 *   - **les écrans vides sont une erreur** : un écran sans contenu doit être une
 *     absence assumée (message explicite), pas une page blanche ;
 *   - **code de sortie** : 0 = tout passe, 1 = au moins une vérification tombe,
 *     2 = environnement (serveur injoignable).
 */
const { JSDOM, VirtualConsole } = require("jsdom");
const realFetch = global.fetch;
const base = (process.argv[2] || process.env.UNIOCR_UI_URL || "http://127.0.0.1:8000")
  .replace(/\/$/, "");

const attendre = (ms) => new Promise((r) => setTimeout(r, ms));

const requetesEcriture = [];
const erreursServeur = [];
const erreursJs = [];

function suivre(w) {
  w.fetch = (u, o) => {
    const brut = String(u);
    const url = brut.startsWith("http") ? brut : base + (brut.startsWith("/") ? brut : "/" + brut);
    const methode = String((o && o.method) || "GET").toUpperCase();
    if (methode !== "GET") requetesEcriture.push(methode + " " + url.slice(base.length));
    // Ne pas réutiliser un socket que le serveur de recette a déjà fermé.
    const options = { ...(o || {}), headers: { ...((o && o.headers) || {}), connection: "close" } };
    return realFetch(url, options).then((r) => {
      if (r.status >= 500) erreursServeur.push(r.status + " " + url.slice(base.length));
      return r;
    });
  };
  w.scrollTo = () => {};
  w.confirm = () => true;
  w.matchMedia = w.matchMedia || (() => ({
    matches: false, addEventListener() {}, removeEventListener() {},
    addListener() {}, removeListener() {},
  }));
}

function pageVisible(doc, w) {
  const sections = [...doc.querySelectorAll("section.page")];
  return sections.find((s) => w.getComputedStyle(s).display !== "none" &&
    !s.classList.contains("hidden") && !s.hasAttribute("hidden"));
}

const resultats = [];
function noter(nom, ok, detail) {
  resultats.push({ nom, ok, detail });
  console.log((ok ? "  ✓ " : "  ✗ ") + nom + (detail ? " — " + detail : ""));
}

async function ouvrirRoute(w, doc, route, delai) {
  w.location.hash = route;
  await attendre(delai || 2400);
  const ecran = w.UniOCREcrans && w.UniOCREcrans.ecrans[route.slice(1)];
  if (ecran) {
    const echeance = Date.now() + 15000;
    while ((!w.__ecranCourant || w.__ecranCourant.ecran !== ecran) &&
      Date.now() < echeance) {
      await attendre(50);
    }
  }
  return pageVisible(doc, w);
}

(async () => {
  let dom;
  try {
    const reponse = await realFetch(base + "/api/health").catch(() => null);
    if (!reponse || !reponse.ok) throw new Error("santé indisponible");
  } catch (e) {
    console.error("Serveur injoignable sur " + base + " (" + e.message + ")");
    process.exit(2);
  }

  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => erreursJs.push(String(e.message).slice(0, 160)));

  dom = await JSDOM.fromURL(base + "/", {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse: suivre,
  });
  const w = dom.window;
  const doc = w.document;
  await attendre(5000);

  /* ── 1. Écrans critiques : contenu réel, pas de page blanche ── */
  const ECRANS = [
    ["#cockpit", "tab-cockpit", 400],
    ["#dossiers/tous", "tab-dossiers", 400],
    ["#documents/ocr", "tab-ecran", 300],
    ["#referentiels/parametres", "tab-ecran", 200],
    ["#admin/utilisateurs", "tab-ecran", 200],
    ["#rapports/graphes", "tab-graphiques", 300],
    ["#finance/cloture", "tab-ecran", 200],
    ["#douane/paiements", "tab-ecran", 100],
  ];

  console.log("Écrans :");
  for (const [route, attendu, minimum] of ECRANS) {
    const page = await ouvrirRoute(w, doc, route);
    if (!page) {
      noter(route, false, "aucune section visible");
      continue;
    }
    const texte = (page.textContent || "").replace(/\s+/g, " ").trim();
    const okPage = page.id === attendu;
    const okTexte = texte.length >= minimum;
    noter(route + " (" + page.id + ")", okPage && okTexte,
      okPage ? texte.length + " caractères" : "section " + page.id + " au lieu de " + attendu);
  }

  /* ── 2. Interaction : chronologie d'un document ── */
  console.log("Interactions :");
  {
    const page = await ouvrirRoute(w, doc, "#documents/ocr");
    const lignes = page ? [...page.querySelectorAll("tbody tr")] : [];
    const bouton = lignes[0] && [...lignes[0].querySelectorAll("button")]
      .find((b) => /historique/i.test(b.textContent));
    if (!bouton) {
      noter("Historique d'un document", false, "bouton absent : " + lignes.length + " ligne(s)");
    } else {
      bouton.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
      await attendre(1800);
      const items = doc.querySelectorAll(".chrono-item").length;
      const bloc = doc.querySelector(".ecran__resultat");
      /* Un historique vide est acceptable — à condition qu'il s'explique. */
      const explique = Boolean(doc.querySelector(".chrono-vide")) &&
        (doc.querySelector(".chrono-vide").textContent || "").trim().length > 20;
      noter("Historique d'un document", Boolean(bloc) && (items > 0 || explique),
        items + " événement(s)" + (explique ? " (vide expliqué)" : ""));
    }
  }

  /* ── 3. Graphiques : séries dessinées, états vides expliqués ── */
  {
    const page = await ouvrirRoute(w, doc, "#rapports/graphes", 2600);
    const cartes = page ? [...page.querySelectorAll(".graph__carte")] : [];
    const dessinees = cartes.filter((c) => c.querySelector("svg")).length;
    const expliquees = cartes.filter((c) => {
      const vide = c.querySelector(".graph__vide");
      return vide && !vide.hidden && vide.textContent.trim().length > 20;
    }).length;
    noter("Graphiques", cartes.length === 6 && dessinees + expliquees === 6,
      cartes.length + " cartes : " + dessinees + " dessinée(s), " + expliquees + " expliquée(s)");
  }

  /* ── 4. Paramètres : le formulaire s'ouvre (sans écrire) ── */
  {
    const page = await ouvrirRoute(w, doc, "#referentiels/parametres", 2400);
    const lignes = page ? [...page.querySelectorAll("tbody tr")] : [];
    const cible = lignes[0];
    const modifier = cible && [...cible.querySelectorAll("button")]
      .find((b) => /modifier/i.test(b.textContent));
    if (!modifier) {
      noter("Paramètres : formulaire", false, lignes.length + " ligne(s), aucun bouton");
    } else {
      modifier.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
      await attendre(900);
      const boite = doc.querySelector(".ecran__voile");
      const champ = boite && boite.querySelector('input[name="valeur"]');
      noter("Paramètres : formulaire", Boolean(champ),
        lignes.length + " réglage(s), champ " + (champ ? champ.name : "absent"));
      if (boite) boite.remove();          /* on ferme : aucune écriture */
    }
  }

  /* ── 5. Création de dossier : le dialogue s'ouvre, rien n'est envoyé ── */
  {
    await ouvrirRoute(w, doc, "#dossiers/nouveau", 2200);
    const dlg = doc.getElementById("dos-create");
    const ouvert = dlg && (dlg.open || dlg.hasAttribute("open"));
    const champs = dlg ? dlg.querySelectorAll("input[name], select[name]").length : 0;
    const ports = doc.querySelectorAll("#dos-ports-chargement option").length;
    noter("Création de dossier", Boolean(ouvert) && champs >= 4,
      champs + " champ(s), " + ports + " port(s) proposé(s)");
  }

  /* ── 6. Bilan : aucune écriture, aucune erreur serveur ── */
  noter("Aucune écriture émise", requetesEcriture.length === 0,
    requetesEcriture.length ? requetesEcriture.slice(0, 3).join(", ") : "lecture seule");
  noter("Aucune erreur serveur", erreursServeur.length === 0,
    erreursServeur.slice(0, 3).join(", ") || "0 × 5xx");
  noter("Aucune erreur JavaScript", erreursJs.length === 0,
    erreursJs.slice(0, 2).join(" | ") || "0 erreur");

  const echecs = resultats.filter((r) => !r.ok);
  console.log("");
  console.log(resultats.length - echecs.length + "/" + resultats.length +
    " vérifications passées" + (echecs.length ? " — ÉCHECS : " +
      echecs.map((e) => e.nom).join(", ") : ""));

  w.close();
  process.exit(echecs.length ? 1 : 0);
})().catch((e) => {
  console.error("Vérification impossible : " + e.message);
  process.exit(1);
});
