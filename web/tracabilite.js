/* ═══ Traçabilité du dossier — module d'interface (source unique) ═══
   Chargé directement par web/index.html (<script src="tracabilite.js" defer>).

   Étape 15 du parcours. Ce module montre ce qui s'est passé sur un dossier :
   création, ajout de pièces, changements d'état, archivage. Et il permet de
   l'archiver.

   Contrainte structurante, à ne jamais contourner : **le journal applicatif
   n'est pas une preuve inviolable.** Il est écrit par l'application dans un
   fichier texte sur cette machine ; quiconque a un accès administrateur peut
   le modifier. L'avertissement ci-dessous est donc affiché EN PERMANENCE à
   côté de la trace, jamais une fois pour toutes dans une page d'aide, jamais
   caché dans un repli. Si un jour quelqu'un veut le déplacer « pour faire
   plus propre », c'est que la contrainte a été oubliée.

   L'archivage est un état, pas une suppression : rien n'est effacé, et les
   pièces manquantes ne sont pas créées. Aucune ressource externe.            */

const TracabiliteUI = (function () {
  "use strict";

  let traceActive = null;
  let occupation = false;

  function el(id) { return document.getElementById(id); }

  /* libellés lisibles des événements réellement écrits par le journal */
  const LIBELLES = {
    dossier_created: "Dossier créé",
    dossier_piece_added: "Pièce ajoutée",
    dossier_piece_removed: "Pièce retirée",
    dossier_piece_recategorized: "Pièce reclassée",
    dossier_deleted: "Dossier supprimé",
    dossier_state_changed: "État recalculé",
    dossier_state_forced: "État forcé par un humain",
    dossier_archived: "Dossier archivé",
    dossier_form_saved: "Formulaire enregistré",
    dossier_form_deleted: "Formulaire supprimé",
    data_package_generated: "Paquet de données généré",
    job_created: "Document reçu",
    job_done: "Document traité",
    job_error: "Document en erreur",
    job_deduped: "Document déjà connu",
    document_classified: "Document classé",
    field_validated: "Valeur validée par un humain",
    field_decisions_restored: "Décisions humaines réappliquées",
  };

  /* l'acteur distingue l'état déduit de l'état posé à la main : c'est la
     seule façon de voir qu'un état a été forcé malgré ce que montraient
     les pièces réellement présentes. */
  function acteurBadge(detail) {
    const acteur = (detail && detail.acteur) || "systeme";
    if (acteur === "systeme") {
      return '<span class="badge info" title="État déduit des pièces ' +
        'réellement présentes">déduit</span>';
    }
    return '<span class="badge warning" title="État posé par ' +
      esc(acteur) + ', pas déduit des pièces">posé par ' +
      esc(acteur) + "</span>";
  }

  function libelleEvent(event) {
    return LIBELLES[event] || event;
  }

  function horodatage(ts) {
    if (typeof ts !== "number" || !ts) return "—";
    const d = new Date(ts * 1000);
    const pad = n => String(n).padStart(2, "0");
    return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" +
      d.getFullYear() + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) +
      ":" + pad(d.getSeconds());
  }

  function resumeDetail(detail) {
    if (!detail) return "";
    const morceaux = [];
    if (detail.from && detail.to) morceaux.push(detail.from + " → " + detail.to);
    if (detail.filename) morceaux.push(esc(detail.filename));
    if (detail.category) morceaux.push(esc(detail.category));
    if (detail.motif) morceaux.push("motif : " + esc(detail.motif));
    if (detail.avertissements) {
      morceaux.push(detail.avertissements + " avertissement(s)");
    }
    if (!morceaux.length) {
      /* on montre le détail brut plutôt que de le taire : une clé qu'on ne
         sait pas résumer vaut mieux qu'une ligne vide. */
      Object.keys(detail).forEach(k => {
        if (k === "acteur") return;
        morceaux.push(k + "=" + esc(String(detail[k])));
      });
    }
    return morceaux.join(" · ");
  }

  /* ─────────────────────── avertissement permanent ─────────────────────── */

  function blocAvertissement(avertissement, garanties, limites) {
    /* Volontairement hors d'un repli : ce texte doit être vu à chaque fois
       qu'on regarde une trace. */
    return '<div class="card" style="border-left:3px solid var(--warn,#c77700)">' +
      '<div class="card-title" style="margin-bottom:6px">Ce que cette trace ' +
      "est — et ce qu'elle n'est pas</div>" +
      '<div class="card-sub" style="margin-bottom:8px">' +
      esc(avertissement || "") + "</div>" +
      '<div style="display:flex;gap:18px;flex-wrap:wrap">' +
      '<div style="flex:1;min-width:220px">' +
      '<div class="card-sub" style="font-weight:600;margin-bottom:4px">' +
      "L'archivage conserve :</div><ul style=\"margin:0;padding-left:18px\">" +
      (garanties || []).map(g => "<li>" + esc(g) + "</li>").join("") +
      "</ul></div>" +
      '<div style="flex:1;min-width:220px">' +
      '<div class="card-sub" style="font-weight:600;margin-bottom:4px">' +
      "L'archivage ne fait pas :</div><ul style=\"margin:0;padding-left:18px\">" +
      (limites || []).map(l => "<li>" + esc(l) + "</li>").join("") +
      "</ul></div></div></div>";
  }

  /* ─────────────────────────── chargement ─────────────────────────── */

  async function charge(dossierId) {
    const box = el("dossierTrace");
    if (!box) return;
    if (!dossierId) {
      box.innerHTML = '<div class="card-sub">Ouvrez d\'abord un dossier.</div>';
      return;
    }
    box.innerHTML = '<div class="card-sub">Lecture du journal…</div>';
    try {
      const t = await api("/api/dossiers/" + encodeURIComponent(dossierId) +
        "/trace");
      traceActive = t;
      dessine(t);
    } catch (e) {
      box.innerHTML = '<div class="card-sub">Erreur : ' + esc(e.message) + "</div>";
    }
  }

  async function chargeAvertissement() {
    try {
      return await api("/api/tracabilite/avertissement");
    } catch (e) {
      /* Même sans cet appel, l'avertissement minimal reste affiché : on ne
         laisse jamais une trace sans son correctif. */
      return {
        avertissement: "Journal applicatif, pas preuve inviolable : il est " +
          "écrit par l'application dans un fichier texte sur cette machine.",
        garanties: [],
        limites: [],
      };
    }
  }

  function dessine(t) {
    const box = el("dossierTrace");
    if (!box) return;
    const entrees = t.entrees || [];

    let html = '<div class="page-head"><div>' +
      '<div class="ph-kicker">Traçabilité</div>' +
      '<h3 class="ph-title">Ce qui s\'est passé sur ce dossier</h3>' +
      '<p class="ph-sub">' + (t.total || 0) + " événement(s) au journal, du " +
      "plus ancien au plus récent.</p></div>" +
      '<div class="ph-actions">' +
      '<span class="pill">' + esc(t.etat || "?") + "</span>" +
      '<button class="btn ghost sm" id="trcRafraichir">↻ Relire le journal</button>' +
      "</div></div>";

    /* l'avertissement est rendu en premier : il cadre la lecture de tout ce
       qui suit, il n'est pas une note de bas de page. */
    html += blocAvertissement(t.avertissement, t.garanties, t.limites);

    /* ── archivage ── */
    const dejaArchive = t.etat === "archive";
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Archiver ce dossier</div>' +
      '<div class="card-sub">L\'archivage est un état, pas une suppression ' +
      ": rien n'est effacé — et aucune pièce manquante n'est créée.</div></div>";
    if (dejaArchive) {
      html += '<div class="card-sub">Ce dossier est déjà archivé. ' +
        "Le rester n'ajoute rien.</div>";
    } else {
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap;' +
        'align-items:flex-end">' +
        '<input class="inp" id="trcMotif" placeholder="Motif (optionnel)" ' +
        'style="flex:1;min-width:200px">' +
        '<button class="btn" id="trcArchiver">Archiver</button></div>';
    }
    html += "</div>";

    /* ── la trace ── */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Journal</div>' +
      '<div class="card-sub">Les événements marqués « déduit » ont été ' +
      "calculés par l'application ; ceux marqués « posé par » viennent " +
      "d'une action humaine.</div></div>";

    if (!entrees.length) {
      html += '<div class="card-sub">Aucun événement pour ce dossier. Un ' +
        "journal vide est affiché comme tel.</div>";
    } else {
      html += '<table class="tbl"><thead><tr><th>Quand</th><th>Quoi</th>' +
        "<th>Détail</th><th>Acteur</th><th>Document</th></tr></thead><tbody>";
      entrees.forEach(e => {
        const evenementDoc = e.event && e.event.indexOf("job_") === 0 ||
          e.event === "document_classified" ||
          e.event === "field_validated" ||
          e.event === "field_decisions_restored";
        html += "<tr" + (evenementDoc ? ' class="dim"' : "") + ">" +
          '<td class="mono">' + horodatage(e.ts) + "</td>" +
          "<td>" + esc(libelleEvent(e.event)) +
          (evenementDoc
            ? ' <span class="pill" title="Événement du document, pas du dossier">document</span>'
            : "") + "</td>" +
          "<td>" + resumeDetail(e.detail) + "</td>" +
          "<td>" + acteurBadge(e.detail) + "</td>" +
          '<td class="mono">' + (e.job_id ? esc(e.job_id) : "—") + "</td>" +
          "</tr>";
      });
      html += "</tbody></table>";
    }
    html += "</div>";

    box.innerHTML = html;

    const r = el("trcRafraichir");
    if (r) r.addEventListener("click", () => charge(t.dossier_id));
    const a = el("trcArchiver");
    if (a) a.addEventListener("click", () => archiver(t.dossier_id));
  }

  /* ─────────────────────────── archivage ─────────────────────────── */

  async function archiver(dossierId) {
    const motif = (el("trcMotif") ? el("trcMotif").value : "") || "";
    if (occupation) return;
    /* Confirmation explicite : archiver change l'état du dossier de façon
       visible par tous, même si rien n'est supprimé. */
    if (!confirm("Archiver ce dossier ?\n\n" +
      "· aucun document n'est supprimé\n" +
      "· les valeurs extraites et les corrections restent en place\n" +
      "· les pièces manquantes ne sont PAS créées\n" +
      "· le dossier reste consultable et peut repasser en préparation\n\n" +
      "L'archivage ne rend rien inaltérable : le journal reste un fichier " +
      "modifiable sur cette machine.")) {
      return;
    }
    occupation = true;
    try {
      await api("/api/dossiers/" + encodeURIComponent(dossierId) + "/archiver", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ motif: motif.trim() }),
      });
      toast("Dossier archivé. Rien n'a été supprimé.", "success");
      await charge(dossierId);
      /* le reste de l'interface doit refléter le nouvel état */
      if (typeof DossierUI !== "undefined") {
        DossierUI.loadAll();
        DossierUI.ouvreDossier(dossierId);
      }
    } catch (e) {
      toast("Archivage refusé : " + e.message, "error");
    } finally {
      occupation = false;
    }
  }

  return {
    charge: charge,
    dessine: dessine,
    archiver: archiver,
    chargeAvertissement: chargeAvertissement,
    libelleEvent: libelleEvent,
    blocAvertissement: blocAvertissement,
    get actif() { return traceActive; },
  };
})();
