/* ═══ Transmission du dossier — module d'interface (source unique) ═══
   Chargé directement par web/index.html (<script src="transmission.js" defer>).

   Étape 14 du parcours. Ce module envoie le contenu d'un dossier vers un
   connecteur opérationnel — la même discipline que le Connecteur Hub, mais
   la source est le formulaire du dossier (étape 12) et non un document
   isolé.

   Contrainte structurante, à ne jamais contourner : **« envoyé » n'est pas
   « accepté ».** Tant qu'aucune preuve d'acceptation n'est revenue du
   système cible, le dossier n'est pas enregistré. Le rappel est donc rendu
   EN PERMANENCE à côté de tout envoi, jamais une fois pour toutes dans une
   page d'aide. Si un jour quelqu'un veut le déplacer « pour faire plus
   propre », c'est que la contrainte a été oubliée.

   L'envoi exige une confirmation humaine explicite quand le niveau de risque
   l'exige, et le refus vient du serveur — pas de ce module.

   Aucune ressource externe.                                                        */

const TransmissionUI = (function () {
  "use strict";

  let occupation = false;

  function el(id) { return document.getElementById(id); }

  const LIBELLES_ISSUE = {
    missing_required: "manquant",
    unknown_field: "sans correspondance",
    unvalidated_suggestion: "non validé par un humain",
    contradiction: "anomalie non tranchée",
    bad_format: "format douteux",
    ambiguous: "ambigu",
  };

  function severiteBadge(sev) {
    const cls = { error: "warning", warning: "info", info: "info" }[sev] || "info";
    const texte = { error: "bloquant", warning: "à signaler",
                    info: "information" }[sev] || sev;
    return '<span class="badge ' + cls + '">' + esc(texte) + "</span>";
  }

  /* ─────────────────── le rappel permanent, hors de tout repli ─────────────────── */

  function blocNeGarantitPas(neGarantitPas) {
    return '<div class="card" style="border-left:3px solid var(--warn,#c77700)">' +
      '<div class="card-title" style="margin-bottom:6px">Ce que l\'envoi ne ' +
      "garantit pas</div>" +
      '<div class="card-sub" style="margin-bottom:8px">' +
      "Un envoi est une intention. Tant qu'aucune preuve d'acceptation " +
      "n'est revenue du système cible, ce dossier n'est <strong>pas</strong> " +
      "enregistré chez lui.</div>" +
      '<ul style="margin:0;padding-left:18px">' +
      (neGarantitPas || []).map(g => "<li>" + esc(g) + "</li>").join("") +
      "</ul></div>";
  }

  /* ─────────────────────────── aperçu ─────────────────────────── */

  async function charge(dossierId, formId) {
    const box = el("dossierTransmission");
    if (!box) return;
    if (!dossierId) {
      box.innerHTML = '<div class="card-sub">Ouvrez d\'abord un dossier.</div>';
      return;
    }
    box.innerHTML = '<div class="card-sub">Préparation de l\'aperçu…</div>';
    try {
      const url = "/api/dossiers/" + encodeURIComponent(dossierId) +
        "/transmission" + (formId ? "?form_id=" + encodeURIComponent(formId) : "");
      const ap = await api(url);
      apercuActif = ap;
      dessine(ap);
    } catch (e) {
      box.innerHTML = '<div class="card-sub">Erreur : ' + esc(e.message) + "</div>";
    }
  }

  let apercuActif = null;

  function dessine(ap) {
    const box = el("dossierTransmission");
    if (!box) return;

    let html = '<div class="page-head"><div>' +
      '<div class="ph-kicker">Transmission</div>' +
      '<h3 class="ph-title">Envoyer ce dossier</h3>' +
      '<p class="ph-sub">Les valeurs du formulaire, mappées vers le ' +
      "formulaire cible. Les documents eux-mêmes ne partent pas.</p></div>" +
      '<div class="ph-actions">' +
      (ap.transmissible
        ? '<span class="badge ok">prêt à envoyer</span>'
        : '<span class="badge warning">envoi refusé</span>') +
      '<span class="pill">' + (ap.form_id || "aucun formulaire cible") + "</span>" +
      '<button class="btn ghost sm" id="txRafraichir">↻ Recalculer</button>' +
      "</div></div>";

    html += blocNeGarantitPas(ap.ne_garantit_pas);

    /* ce qui part réellement */
    const contenu = ap.contenu || {};
    const champs = contenu.champs || {};
    const cles = Object.keys(champs);
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Ce qui part</div>' +
      '<div class="card-sub">' + cles.length + " valeur(s), et " +
      (ap.pieces || 0) + " pièce(s) <strong>non</strong> jointe(s)</div></div>";
    if (!cles.length) {
      html += '<div class="card-sub">Rien à envoyer pour l\'instant : ' +
        "aucune valeur validée n'est prête.</div>";
    } else {
      html += '<table class="tbl"><thead><tr><th>Champ cible</th>' +
        "<th>Valeur</th></tr></thead><tbody>";
      cles.forEach(k => {
        html += "<tr><td>" + esc(k) + "</td>" +
          '<td class="mono">' + esc(String(champs[k])) + "</td></tr>";
      });
      html += "</tbody></table>";
    }
    html += "</div>";

    /* les points de contrôle */
    if ((ap.issues || []).length) {
      html += '<div class="card"><div class="card-head">' +
        '<div class="card-title">Points de contrôle</div>' +
        '<div class="card-sub">Ce qui bloque, et ce qui mérite d\'être ' +
        "signalé avant l'envoi</div></div>" +
        '<table class="tbl"><thead><tr><th>Quoi</th><th>Champ</th>' +
        "<th>Détail</th><th>Portée</th></tr></thead><tbody>";
      ap.issues.forEach(i => {
        html += "<tr><td>" +
          esc(LIBELLES_ISSUE[i.kind] || i.kind) + "</td>" +
          '<td class="mono">' + esc(i.field || "—") + "</td>" +
          "<td>" + esc(i.message) + "</td>" +
          "<td>" + severiteBadge(i.severity) + "</td></tr>";
      });
      html += "</tbody></table></div>";
    }

    /* suggestions de correspondance — jamais appliquées seules */
    if ((ap.suggestions_mapping || []).length) {
      html += '<div class="card"><div class="card-head">' +
        '<div class="card-title">Correspondances suggérées</div>' +
        '<div class="card-sub">Proposées par similarité de nom. ' +
        "Une suggestion ne remplit rien : à valider avant l'envoi." +
        "</div></div>" +
        '<table class="tbl"><thead><tr><th>Champ du dossier</th>' +
        "<th>Champ cible</th><th>Score</th></tr></thead><tbody>";
      ap.suggestions_mapping.forEach(s => {
        html += "<tr><td>" + esc(s.source_field || "") + "</td>" +
          "<td>" + esc(s.target_field || "") + "</td>" +
          "<td>" + esc(String(s.score != null ? s.score : "—")) + "</td></tr>";
      });
      html += "</tbody></table></div>";
    }

    /* l'envoi, ou la raison du refus */
    html += '<div class="card"><div class="card-head">' +
      '<div class="card-title">Envoyer</div>' +
      '<div class="card-sub">L\'envoi part vers le connecteur ' +
      "opérationnel configuré. Rien n'est envoyé sans votre confirmation." +
      "</div></div>";
    if (!ap.transmissible) {
      const bloquants = (ap.issues || []).filter(i => i.severity === "error");
      html += '<div class="card-sub">Envoi refusé : ' +
        esc(bloquants.map(b => b.message).join(" ; ") ||
            "le dossier n'est pas transmissible") + "</div>";
    } else {
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap;' +
        'align-items:flex-end">' +
        '<label class="ph-field" for="txRisque">Niveau de risque</label>' +
        '<select class="inp" id="txRisque" style="width:180px">' +
        '<option value="low">faible</option>' +
        '<option value="medium" selected>moyen</option>' +
        '<option value="high">élevé</option>' +
        "</select>" +
        '<label class="ph-check" for="txConfirme">' +
        '<input type="checkbox" id="txConfirme"><span>je confirme ' +
        "l'envoi de ces valeurs</span></label>" +
        '<button class="btn" id="txEnvoyer">Envoyer</button></div>' +
        '<div class="card-sub" style="margin-top:6px">Un niveau ' +
        "moyen ou élevé exige la case cochée. Le refus vient du " +
        "serveur, pas de cette page.</div>";
    }
    html += "</div>";

    box.innerHTML = html;

    const r = el("txRafraichir");
    if (r) r.addEventListener("click", () => charge(ap.dossier_id, ap.form_id));
    const e = el("txEnvoyer");
    if (e) e.addEventListener("click", () => envoie(ap));
  }

  /* ─────────────────────────── envoi ─────────────────────────── */

  async function envoie(ap) {
    if (occupation) return;
    if (!el("txConfirme").checked) {
      toast("Cochez la confirmation : l'envoi exige une décision humaine.",
            "error");
      return;
    }
    if (!confirm("Envoyer ce dossier ?\n\n" +
      "· " + Object.keys((ap.contenu || {}).champs || {}).length +
      " valeur(s) partent vers le connecteur\n" +
      "· les documents originaux ne sont PAS joints\n" +
      "· « envoyé » ne veut pas dire « accepté » : sans preuve du système " +
      "cible, ce dossier n'est pas enregistré chez lui\n" +
      "· un second envoi du même contenu ne sera pas renvoyé\n\n" +
      "Confirmer l'envoi ?")) {
      return;
    }
    occupation = true;
    try {
      const regles = (ap.suggestions_mapping || [])
        .filter(s => s.source_field && s.target_field)
        .map(s => ({ source_field: s.source_field,
                     target_field: s.target_field, transform: "none" }));
      const res = await api("/api/dossiers/" +
        encodeURIComponent(ap.dossier_id) + "/transmission", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          form_id: ap.form_id || "",
          rules: regles,
          risk: el("txRisque").value,
          confirmed: true,
          confirmed_by: "utilisateur",
        }),
      });
      const statut = res.transmission.status;
      if (statut === "accepted") {
        toast("Accepté par le système cible — référence " +
              (res.transmission.reference || "?"), "success");
      } else if (statut === "sent") {
        toast("Envoyé. En attente d'une preuve d'acceptation : ce dossier " +
              "n'est pas encore enregistré chez le cible.", "info");
      } else if (statut === "pending_confirmation") {
        toast("Issue inconnue après l'envoi : à rapprocher, jamais supposé " +
              "enregistré.", "warning");
      } else {
        toast("Envoi non abouti (" + statut + ") : " +
              (res.transmission.errors || []).join(" ; "), "error");
      }
      await charge(ap.dossier_id, ap.form_id);
      if (typeof DossierUI !== "undefined") DossierUI.loadAll();
    } catch (e) {
      toast("Envoi refusé : " + e.message, "error");
    } finally {
      occupation = false;
    }
  }

  return {
    charge: charge,
    dessine: dessine,
    envoie: envoie,
    blocNeGarantitPas: blocNeGarantitPas,
    get actif() { return apercuActif; },
  };
})();
