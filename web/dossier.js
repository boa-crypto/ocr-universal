/* ═══ Parcours documentaire — module d'interface (source unique) ═══
   Chargé directement par web/index.html
   (<script src="dossier.js" defer>). Depuis la refactorisation Phase 1, ce
   module n'est plus injecté dans index.html : il n'existe plus de copie.

   Ce que fait ce module : il rend visibles les étapes 4 (classification),
   8 (cohérence interdocumentaire), 11 (dossier documentaire) et 13 (paquet
   de données) du parcours. Aucune donnée n'est inventée : tout ce qui
   s'affiche vient d'un appel API réel, et un constat sans réponse humaine
   reste affiché comme tel.

   Aucune ressource externe : pas de police, pas d'image, pas de CDN.        */

const DossierUI = (function () {
  "use strict";

  /* état local — jamais une source de vérité, seulement ce que l'utilisateur
     regarde. Le serveur reste seul détenteur de l'état des dossiers. */
  let dossierActif = null;
  let profilsDispo = {};
  let etatsDispo = {};
  let occupation = false;   // évite les doubles clics sur les actions

  /* ─────────────────────────── helpers ─────────────────────────── */

  function el(id) { return document.getElementById(id); }

  /* gravité → classe de badge et libellé lisible.
     Les libellés sont ceux du moteur, pas une interprétation. */
  const GRAVITES = {
    information:   { cls: "info",    label: "Information" },
    avertissement: { cls: "warning", label: "Avertissement" },
    anomalie:      { cls: "err",     label: "Anomalie" },
    blocage:       { cls: "err",     label: "Blocage" },
  };

  const ETATS_LISIBLES = {
    en_preparation:    "En préparation",
    traitement_en_cours: "Traitement en cours",
    revision_requise:  "Révision requise",
    incomplet:         "Incomplet",
    en_validation:     "En validation",
    valide:            "Validé",
    pret_a_exporter:   "Prêt à exporter",
    exporte:           "Exporté",
    archive:           "Archivé",
    erreur_traitement: "Erreur de traitement",
  };

  function etatBadge(etat) {
    const classe = {
      valide: "ok", pret_a_exporter: "ok", exporte: "ok", archive: "ok",
      erreur_traitement: "err", revision_requise: "warning",
      incomplet: "warning", traitement_en_cours: "warning",
    }[etat] || "info";
    const label = ETATS_LISIBLES[etat] || etat;
    return '<span class="badge ' + classe + '">' + esc(label) + "</span>";
  }

  function graviteBadge(gravite) {
    const g = GRAVITES[gravite] || { cls: "info", label: gravite };
    return '<span class="badge ' + g.cls + '">' + esc(g.label) + "</span>";
  }

  function octets(n) {
    if (n === null || n === undefined) return "—";
    if (n < 1024) return n + " o.";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " Ko";
    return (n / (1024 * 1024)).toFixed(2) + " Mo";
  }

  function confianceBadge(c) {
    if (c === null || c === undefined) return '<span class="badge info">inconnue</span>';
    const pct = Math.round(c * 100);
    const cls = c >= 0.8 ? "ok" : (c >= 0.6 ? "warning" : "err");
    return '<span class="badge ' + cls + '">' + pct + " %</span>";
  }

  /* ─────────────────────── chargement des données ─────────────────────── */

  async function chargeReferences() {
    try {
      const [profils, types] = await Promise.all([
        api("/api/dossier-profiles"),
        api("/api/document-types"),
      ]);
      profilsDispo = {};
      (profils.profiles || []).forEach(p => { profilsDispo[p.id] = p; });
      etatsDispo = {};
      (profils.states || []).forEach(s => { etatsDispo[s.id] = s.label; });
      remplitSelectProfil(profilsDispo);
      afficheTypes(types);
    } catch (e) {
      toast("Références indisponibles : " + e.message, "error");
    }
  }

  function remplitSelectProfil(profils) {
    const sel = el("dossierProfile");
    if (!sel) return;
    const actuel = sel.value;
    sel.innerHTML = "";
    Object.keys(profils).forEach(id => {
      const p = profils[id];
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = p.label || id;
      sel.appendChild(opt);
    });
    if (actuel && profils[actuel]) sel.value = actuel;
  }

  function afficheTypes(types) {
    const box = el("dossierTypes");
    if (!box) return;
    const cats = types.categories || [];
    const sans = cats.filter(c => !c.active);
    let html = '<div class="card-sub">' +
      "Classifieur v" + esc(types.classifier_version || "?") +
      " — " + cats.length + " catégories connues</div>";
    html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">';
    cats.slice(0, 14).forEach(c => {
      const cls = c.active ? "pill lang" : "pill";
      html += '<span class="' + cls + '" title="' + esc(c.label) +
        (c.profile ? " — profil " + esc(c.profile) : " — sans profil d'extraction") +
        '">' + esc(c.label) + "</span>";
    });
    html += "</div>";
    if (sans.length) {
      html += '<div class="card-sub" style="margin-top:8px">' +
        sans.length + " catégorie(s) reconnue(s) mais sans indice distinctif : " +
        "un document de ce type sera classé « inconnu » plutôt que deviné.</div>";
    }
    box.innerHTML = html;
  }

  async function chargeDossiers() {
    const box = el("dossierListe");
    if (!box) return;
    box.innerHTML = '<div class="card-sub">Chargement…</div>';
    try {
      const dossiers = await api("/api/dossiers");
      if (!dossiers.length) {
        box.innerHTML = '<div class="card-sub">Aucun dossier. ' +
          "Créez-en un ci-dessus pour regrouper les documents d'un même envoi.</div>";
        return;
      }
      let html = '<table class="tbl"><thead><tr>' +
        "<th>Libellé</th><th>Profil</th><th>Pièces</th><th>État</th><th>Activité</th>" +
        "</tr></thead><tbody>";
      dossiers.forEach(d => {
        const prof = profilsDispo[d.profile];
        const actif = dossierActif && dossierActif.id === d.id;
        html += '<tr data-dossier="' + esc(d.id) + '"' +
          (actif ? ' style="background:var(--surface-2)"' : "") + ">" +
          '<td><button class="btn ghost sm" data-ouvre="' + esc(d.id) + '">' +
          esc(d.label) + "</button></td>" +
          "<td>" + esc((prof && prof.label) || d.profile) + "</td>" +
          "<td>" + (d.pieces ? d.pieces.length : 0) + "</td>" +
          "<td>" + etatBadge(d.state) + "</td>" +
          '<td class="mono dim">' + esc(d.updated_at || d.created_at || "—") + "</td>" +
          "</tr>";
      });
      html += "</tbody></table>";
      box.innerHTML = html;
      box.querySelectorAll("[data-ouvre]").forEach(b => {
        b.addEventListener("click", () => ouvreDossier(b.getAttribute("data-ouvre")));
      });
    } catch (e) {
      box.innerHTML = '<div class="card-sub">Erreur : ' + esc(e.message) + "</div>";
    }
  }

  /* ─────────────────────── dossier sélectionné ─────────────────────── */

  async function ouvreDossier(id) {
    dossierActif = null;
    const box = el("dossierDetail");
    if (!box) return;
    box.innerHTML = '<div class="card-sub">Chargement du dossier…</div>';
    try {
      const d = await api("/api/dossiers/" + encodeURIComponent(id));
      dossierActif = d;
      dessineDossier(d);
      chargeDossiers();
      // le formulaire du dossier se charge en même temps (étape 12). Il n'est
      // pas attendu volontairement : son échec ne doit pas casser l'ouverture
      // du dossier, et il n'y a rien à afficher si le module n'est pas là.
      if (typeof FormulaireUI !== "undefined") FormulaireUI.charge(d.id);
      // la trace se charge avec le dossier : elle porte l'avertissement sur
      // ce que le journal est, et doit être vue en même temps que le dossier.
      if (typeof TracabiliteUI !== "undefined") TracabiliteUI.charge(d.id);
      // l'aperçu de transmission se charge avec le dossier, comme le
      // formulaire et la trace. Il n'envoie jamais rien : l'envoi est un
      // POST déclenché par l'utilisateur, avec confirmation.
      if (typeof TransmissionUI !== "undefined") TransmissionUI.charge(d.id);
    } catch (e) {
      box.innerHTML = '<div class="card-sub">Erreur : ' + esc(e.message) + "</div>";
    }
  }

  function dessineDossier(d) {
    const box = el("dossierDetail");
    if (!box) return;
    const prof = profilsDispo[d.profile] || {};

    let html = "";

    /* en-tête : libellé, profil, état déduit */
    html += '<div class="page-head"><div>' +
      '<div class="ph-kicker">Dossier</div>' +
      '<h3 class="ph-title">' + esc(d.label) + "</h3>" +
      '<p class="ph-sub">' + esc(prof.description || "Profil personnalisé") +
      " — conventions de rangement, aucune obligation réglementaire.</p>" +
      "</div>" +
      '<div class="ph-actions">' + etatBadge(d.state) +
      '<span class="pill">' + (d.pieces || []).length + " pièce(s)</span>" +
      '<span class="pill">v' + esc(String(d.version || 1)) + "</span>" +
      '<button class="btn ghost sm" id="dosRafraichir">↻ Actualiser</button>' +
      "</div></div>";

    /* pièces : classification réelle de chaque document */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Pièces du dossier</div>' +
      '<div class="card-sub" id="dosPiecesSub">—</div></div>';
    if (!(d.pieces || []).length) {
      html += '<div class="card-sub">Dossier vide. Ajoutez des documents depuis ' +
        "l'onglet Documents, ou avec le bouton ci-dessous.</div>";
    } else {
      html += '<table class="tbl"><thead><tr><th>Fichier</th><th>Catégorie</th>' +
        "<th>Confiance</th><th>Empreinte</th><th></th></tr></thead><tbody>";
      d.pieces.forEach(p => {
        html += "<tr>" +
          "<td>" + esc(p.filename) + "</td>" +
          "<td>" + esc(p.category || "non classé") + "</td>" +
          "<td>" + confianceBadge(p.confidence) + "</td>" +
          '<td class="mono dim" title="' + esc(p.sha256 || "") + '">' +
          esc((p.sha256 || "").slice(0, 12)) + "</td>" +
          '<td><button class="btn ghost sm" data-retire="' + esc(p.job_id) +
          '" title="Retirer du dossier (le document n’est pas supprimé)">✕</button></td>' +
          "</tr>";
      });
      html += "</tbody></table>";
    }
    html += '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">' +
      '<input class="inp" id="dosJobId" placeholder="job_id à ajouter" ' +
      'style="flex:1;min-width:220px">' +
      '<button class="btn ghost sm" id="dosAjouter">+ Ajouter une pièce</button>' +
      "</div></div>";

    /* pièces attendues par le profil — rappel, pas une obligation */
    if (prof.pieces && prof.pieces.length) {
      const presentes = {};
      (d.pieces || []).forEach(p => { presentes[p.category] = (presentes[p.category] || 0) + 1; });
      html += '<div class="card"><div class="card-head">' +
        '<div class="card-title">Pièces attendues par le profil</div>' +
        '<div class="card-sub">Ce que le profil décrit comme usage courant</div></div>';
      html += '<table class="tbl"><thead><tr><th>Catégorie</th><th>Attendu</th>' +
        "<th>Présent</th></tr></thead><tbody>";
      prof.pieces.forEach(pc => {
        const n = presentes[pc.category] || 0;
        const ok = n >= (pc.min_count || (pc.required ? 1 : 0));
        html += "<tr><td>" + esc(pc.label || pc.category) + "</td>" +
          "<td>" + (pc.required ? "requis" : "optionnel") + "</td>" +
          "<td>" + (ok ? "✓ " : "") + n + "</td></tr>";
      });
      html += "</tbody></table></div>";
    }

    /* cohérence interdocumentaire */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Cohérence entre les documents</div>' +
      '<div class="card-sub" id="dosCohSub">—</div>' +
      '<div class="ph-actions"><button class="btn ghost sm" id="dosCohLancer">' +
      "Analyser</button></div></div>" +
      '<div id="dosCoh">Cliquez sur « Analyser » pour comparer les documents ' +
      "entre eux.</div></div>";

    /* paquet de données */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Paquet de données</div>' +
      '<div class="card-sub">Export structuré, séparé de tout envoi</div></div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">' +
      '<button class="btn sm" id="dosXlsx">Excel (.xlsx)</button>' +
      '<button class="btn ghost sm" id="dosJson">JSON</button>' +
      '<button class="btn ghost sm" id="dosZip">ZIP</button>' +
      '<label class="ph-check" for="dosDocs"><input type="checkbox" id="dosDocs">' +
      "<span>inclure les documents originaux dans le ZIP</span></label>" +
      "</div>" +
      '<div id="dosPaquet" class="card-sub" style="margin-top:10px">' +
      "Aucun paquet généré pour l'instant.</div></div>";

    /* Zones des modules frères : formulaire (étape 12) et traçabilité
       (étape 15). Elles sont créées ici parce que dessineDossier réécrit
       tout le contenu de dossierDetail à chaque ouverture — sans ces
       conteneurs, les modules frères n'ont nulle part où s'écrire et
       restent muets sans que rien ne le signale. */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Formulaire du dossier</div>' +
      '<div class="card-sub">Ce que le dossier décrit, champ par champ</div>' +
      '</div><div id="dossierForm"></div></div>';
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Traçabilité et archivage</div>' +
      '<div class="card-sub">Ce qui s\'est passé sur ce dossier, et son ' +
      'archivage</div>' +
      '</div><div id="dossierTrace"></div></div>';
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Transmission du dossier</div>' +
      '<div class="card-sub">Envoyer les valeurs du dossier vers un ' +
      'connecteur — les documents ne partent pas</div>' +
      '</div><div id="dossierTransmission"></div></div>';

    box.innerHTML = html;

    /* câblage */
    el("dosRafraichir").addEventListener("click", () => ouvreDossier(d.id));
    const btnAdd = el("dosAjouter");
    if (btnAdd) {
      btnAdd.addEventListener("click", () => ajoutePiece(d.id));
    }
    el("dosCohLancer").addEventListener("click", () => analyseCoherence(d.id));
    el("dosXlsx").addEventListener("click", () => generePaquet(d.id, "xlsx"));
    el("dosJson").addEventListener("click", () => generePaquet(d.id, "json"));
    el("dosZip").addEventListener("click", () => generePaquet(d.id, "zip"));
    box.querySelectorAll("[data-retire]").forEach(b => {
      b.addEventListener("click", () => retirePiece(d.id, b.getAttribute("data-retire")));
    });
  }

  /* ─────────────────────── actions ─────────────────────── */

  async function creeDossier() {
    const label = (el("dossierLabel").value || "").trim();
    const profile = el("dossierProfile").value;
    if (!label) { toast("Donnez un libellé au dossier.", "error"); return; }
    if (occupation) return;
    occupation = true;
    try {
      const d = await api("/api/dossiers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: label, profile: profile }),
      });
      el("dossierLabel").value = "";
      toast("Dossier créé : " + d.label, "success");
      dossierActif = d;
      dessineDossier(d);
      chargeDossiers();
    } catch (e) {
      toast("Création refusée : " + e.message, "error");
    } finally {
      occupation = false;
    }
  }

  async function ajoutePiece(dossierId) {
    const jobId = (el("dosJobId").value || "").trim();
    if (!jobId) { toast("Indiquez un identifiant de document (job_id).", "error"); return; }
    try {
      const d = await api("/api/dossiers/" + encodeURIComponent(dossierId) + "/pieces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, filename: jobId }),
      });
      el("dosJobId").value = "";
      toast("Pièce ajoutée.", "success");
      dossierActif = d;
      dessineDossier(d);
      chargeDossiers();
    } catch (e) {
      toast("Ajout refusé : " + e.message, "error");
    }
  }

  async function retirePiece(dossierId, jobId) {
    try {
      const d = await api("/api/dossiers/" + encodeURIComponent(dossierId) +
        "/pieces/" + encodeURIComponent(jobId), { method: "DELETE" });
      toast("Pièce retirée du dossier. Le document n'est pas supprimé.", "info");
      dossierActif = d;
      dessineDossier(d);
      chargeDossiers();
    } catch (e) {
      toast("Retrait refusé : " + e.message, "error");
    }
  }

  async function analyseCoherence(dossierId) {
    const box = el("dosCoh");
    const sub = el("dosCohSub");
    if (!box) return;
    box.innerHTML = '<div class="card-sub">Comparaison des documents…</div>';
    try {
      const r = await api("/api/dossiers/" + encodeURIComponent(dossierId) + "/coherence");
      const constats = r.constats || [];
      if (sub) {
        sub.textContent = constats.length + " constat(s) sur " +
          (r.documents_analyses || 0) + " document(s) analysé(s) — " +
          (r.transmissible ? "transmission autorisée" : "transmission bloquée");
      }
      if (!constats.length) {
        box.innerHTML = '<div class="card-sub">Aucune divergence détectée entre ' +
          "les documents comparés.</div>";
        return;
      }
      let html = "";
      constats.forEach(c => {
        const sev = c.severity === "anomalie" ? "err" : "warning";
        html += '<div class="anom">' +
          '<div style="flex:1">' +
          '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">' +
          graviteBadge(c.severity) +
          '<span class="mono dim">' + esc(c.rule) + "</span>" +
          '<span class="pill">' + esc(c.status || "a_trancher") + "</span>" +
          "</div>" +
          '<div style="margin-top:6px">' + esc(c.explication || "") + "</div>";
        if (c.valeurs && c.valeurs.length) {
          html += '<div class="mono dim" style="margin-top:6px">Valeurs relevées : ' +
            esc(c.valeurs.join(" · ")) + "</div>";
        }
        if (c.documents && c.documents.length) {
          html += '<div class="dim" style="margin-top:4px">Documents : ' +
            esc(c.documents.join(", ")) + "</div>";
        }
        html += "</div></div>";
      });
      box.innerHTML = html;
      if (!r.transmissible) {
        toast("Un constat bloquant reste à trancher.", "error");
      }
    } catch (e) {
      box.innerHTML = '<div class="card-sub">Erreur : ' + esc(e.message) + "</div>";
    }
  }

  async function generePaquet(dossierId, fmt) {
    const box = el("dosPaquet");
    if (!box) return;
    const avecDocs = !!(el("dosDocs") && el("dosDocs").checked);
    box.textContent = "Génération du paquet " + fmt + "…";
    try {
      const r = await api("/api/dossiers/" + encodeURIComponent(dossierId) + "/package", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: fmt, include_documents: avecDocs }),
      });
      let html = '<div class="stat-row">';
      html += statCarte("Fichier", r.fichier);
      html += statCarte("Taille", octets(r.taille));
      html += statCarte("Documents", String(r.documents));
      html += statCarte("Anomalies", String(r.anomalies));
      html += statCarte("Pièces manquantes", String(r.pieces_manquantes));
      html += "</div>";
      html += '<div class="card-sub" style="margin-top:8px">' +
        "Paquet généré et enregistré côté serveur. Il n'est ni validé ni " +
        "envoyé : ce sont des décisions humaines séparées.</div>";
      box.innerHTML = html;
      toast("Paquet " + r.fichier + " généré (" + octets(r.taille) + ")", "success");
    } catch (e) {
      box.textContent = "Erreur : " + e.message;
      toast("Génération échouée : " + e.message, "error");
    }
  }

  function statCarte(label, valeur) {
    return '<div class="stat"><div class="stat-k">' + esc(label) +
      '</div><div class="stat-v">' + esc(valeur) + "</div></div>";
  }

  /* ─────────────────────── cycle de vie ─────────────────────── */

  async function loadAll() {
    await chargeReferences();
    await chargeDossiers();
    const box = el("dossierDetail");
    if (box && !dossierActif) {
      box.innerHTML = '<div class="card-sub">Sélectionnez un dossier, ou ' +
        "créez-en un, pour voir ses pièces, les contrôles de cohérence et " +
        "générer un paquet de données.</div>";
    }
  }

  function init() {
    const btn = el("dossierCreer");
    if (btn) btn.addEventListener("click", creeDossier);
    const champ = el("dossierLabel");
    if (champ) {
      champ.addEventListener("keydown", e => {
        if (e.key === "Enter") { e.preventDefault(); creeDossier(); }
      });
    }
  }

  return {
    init: init,
    loadAll: loadAll,
    ouvreDossier: ouvreDossier,
    analyseCoherence: analyseCoherence,
    generePaquet: generePaquet,
    creeDossier: creeDossier,
  };
})();

if (typeof document !== "undefined" && document.getElementById("dossierCreer")) {
  DossierUI.init();
}
