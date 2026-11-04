/**
 * UniOCR — Espace de travail (Cockpit)
 * ---------------------------------------------------------------------------
 * Alimente la page d'accueil avec des données réelles :
 *   - indicateurs de dossiers (GET /api/dossiers)
 *   - alertes actives (GET /api/dashboard/alertes)
 *   - synthèse des traitements (GET /api/dashboard/indicateurs)
 *
 * Aucune valeur n'est inventée : si une source ne répond pas, le bloc affiche
 * un état vide explicite. Les données de l'API sont posées via textContent /
 * createElement, jamais concaténées dans du HTML.
 */
(function () {
  "use strict";

  var ETATS_EN_COURS = {
    en_preparation: true,
    traitement_en_cours: true,
    revision_requise: true,
    incomplet: true,
    en_validation: true
  };
  var ETATS_A_VALIDER = { en_validation: true, revision_requise: true };
  var ETATS_CLOS = { exporte: true, archive: true };
  var PRIORITES = { urgente: 0, haute: 1, normale: 2, basse: 3 };

  function $(id) { return document.getElementById(id); }

  function base() {
    return (typeof window.__apiBase === "string" ? window.__apiBase : "");
  }

  function entetes() {
    var jeton = "";
    try { jeton = sessionStorage.getItem("uniocr_token") || ""; } catch (e) { jeton = ""; }
    return jeton ? { Authorization: "Bearer " + jeton } : {};
  }

  function getJSON(chemin) {
    return fetch(base() + chemin, { headers: entetes() }).then(function (r) {
      if (!r.ok) throw new Error(chemin + " → HTTP " + r.status);
      return r.json();
    });
  }

  function texte(el, valeur) {
    if (el) el.textContent = valeur;
  }

  function formateDate(ts) {
    if (!ts) return "—";
    var d = new Date(Number(ts) * 1000);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  }

  function classeEtat(etat) {
    if (etat === "erreur_traitement" || etat === "incomplet") return "status-pill--danger";
    if (etat === "revision_requise") return "status-pill--warn";
    if (etat === "en_validation") return "status-pill--info";
    if (etat === "valide" || etat === "pret_a_exporter") return "status-pill--ok";
    if (ETATS_CLOS[etat]) return "status-pill--muted";
    return "status-pill--info";
  }

  function pastille(etat, libelle) {
    var span = document.createElement("span");
    span.className = "status-pill " + classeEtat(etat);
    span.textContent = libelle || etat || "—";
    return span;
  }

  /* ── Tableau des tâches prioritaires ─────────────────────────────────── */
  function rendTaches(dossiers) {
    var cible = $("cockpit-tasks");
    if (!cible) return;

    var ouverts = (dossiers || []).filter(function (d) {
      return d && !ETATS_CLOS[d.state];
    });
    ouverts.sort(function (a, b) {
      var pa = PRIORITES[(a.priorite || "").toLowerCase()];
      var pb = PRIORITES[(b.priorite || "").toLowerCase()];
      pa = pa === undefined ? 2 : pa;
      pb = pb === undefined ? 2 : pb;
      if (pa !== pb) return pa - pb;
      return Number(b.updated_at || 0) - Number(a.updated_at || 0);
    });
    ouverts = ouverts.slice(0, 6);

    cible.textContent = "";
    if (!ouverts.length) {
      var vide = document.createElement("p");
      vide.className = "ws-empty";
      vide.textContent = "Aucune tâche ouverte. Tout est à jour.";
      cible.appendChild(vide);
      return;
    }

    var table = document.createElement("table");
    table.className = "ws-table";
    var thead = document.createElement("thead");
    var trh = document.createElement("tr");
    ["Dossier", "État", "Priorité", "Modifié", ""].forEach(function (titre) {
      var th = document.createElement("th");
      th.textContent = titre;
      trh.appendChild(th);
    });
    thead.appendChild(trh);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    ouverts.forEach(function (d) {
      var tr = document.createElement("tr");

      var tdRef = document.createElement("td");
      var ref = document.createElement("span");
      ref.className = "ws-ref";
      ref.textContent = d.label || d.id || "Dossier";
      var meta = document.createElement("span");
      meta.className = "ws-meta";
      meta.textContent = d.client_importateur || d.reference || "Client non renseigné";
      tdRef.appendChild(ref);
      tdRef.appendChild(meta);
      tr.appendChild(tdRef);

      var tdEtat = document.createElement("td");
      tdEtat.appendChild(pastille(d.state, d.state_label));
      tr.appendChild(tdEtat);

      var tdPrio = document.createElement("td");
      tdPrio.textContent = d.priorite || "normale";
      tr.appendChild(tdPrio);

      var tdDate = document.createElement("td");
      tdDate.textContent = formateDate(d.updated_at);
      tr.appendChild(tdDate);

      var tdAction = document.createElement("td");
      var lien = document.createElement("a");
      lien.className = "ws-link";
      lien.href = "#dossiers/tous";
      lien.textContent = "Ouvrir";
      tdAction.appendChild(lien);
      tr.appendChild(tdAction);

      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    cible.appendChild(table);
  }

  /* ── « Ma journée en un coup d'œil » ─────────────────────────────────── */
  function ligneJour(icone, libelle, indice, valeur, variante) {
    var ligne = document.createElement("div");
    ligne.className = "day-item";

    var ic = document.createElement("span");
    ic.className = "day-ic";
    ic.setAttribute("aria-hidden", "true");
    ic.textContent = icone;
    ligne.appendChild(ic);

    var corps = document.createElement("span");
    corps.className = "day-main";
    var lbl = document.createElement("span");
    lbl.className = "day-lbl";
    lbl.textContent = libelle;
    var hint = document.createElement("span");
    hint.className = "day-hint";
    hint.textContent = indice;
    corps.appendChild(lbl);
    corps.appendChild(hint);
    ligne.appendChild(corps);

    var compte = document.createElement("span");
    compte.className = "day-count" + (variante ? " day-count--" + variante : "");
    compte.textContent = String(valeur);
    ligne.appendChild(compte);

    return ligne;
  }

  function rendJour(stats) {
    var cible = $("cockpit-day");
    if (!cible) return;
    cible.textContent = "";
    cible.appendChild(ligneJour("✓", "Tâches à traiter", "dossiers à faire avancer",
      stats.taches, stats.taches ? "warn" : ""));
    cible.appendChild(ligneJour("◔", "Dossiers en cours",
      "préparation, traitement, validation", stats.enCours));
    cible.appendChild(ligneJour("⚠", "Alertes actives", "anomalies et pièces manquantes",
      stats.alertes, stats.alertes ? "danger" : ""));
    cible.appendChild(ligneJour("🗓", "Échéances 7 jours", "à traiter cette semaine",
      stats.echeances));
  }

  /* ── Échéances ───────────────────────────────────────────────────────── */
  function rendEcheances(dossiers) {
    var cible = $("cockpit-deadlines");
    if (!cible) return;
    cible.textContent = "";

    var prochaines = [];
    (dossiers || []).forEach(function (d) {
      (d.echeances || []).forEach(function (e) {
        if (!e || typeof e !== "object") return;
        var quand = e.date || e.echeance || e.due || e.ts;
        var ms = quand ? Date.parse(String(quand).length > 10 ? quand : quand + "T00:00:00") : NaN;
        if (!isNaN(ms)) {
          prochaines.push({ ms: ms, label: e.libelle || e.label || e.titre || "Échéance",
            dossier: d.label || d.id });
        }
      });
    });
    prochaines.sort(function (a, b) { return a.ms - b.ms; });

    if (!prochaines.length) {
      var vide = document.createElement("p");
      vide.className = "ws-empty";
      vide.textContent = "Aucune échéance enregistrée pour le moment.";
      cible.appendChild(vide);
      return;
    }

    prochaines.slice(0, 4).forEach(function (e) {
      var ligne = document.createElement("div");
      ligne.className = "day-item";
      var ic = document.createElement("span");
      ic.className = "day-ic";
      ic.setAttribute("aria-hidden", "true");
      ic.textContent = "🗓";
      ligne.appendChild(ic);
      var corps = document.createElement("span");
      corps.className = "day-main";
      var lbl = document.createElement("span");
      lbl.className = "day-lbl";
      lbl.textContent = e.label;
      var hint = document.createElement("span");
      hint.className = "day-hint";
      hint.textContent = e.dossier;
      corps.appendChild(lbl);
      corps.appendChild(hint);
      ligne.appendChild(corps);
      var quand = document.createElement("span");
      quand.className = "day-count";
      quand.textContent = new Date(e.ms).toLocaleDateString("fr-FR",
        { day: "2-digit", month: "short" });
      ligne.appendChild(quand);
      cible.appendChild(ligne);
    });
  }

  /* ── Chargement ──────────────────────────────────────────────────────── */
  function charge() {
    var date = $("cockpit-date");
    if (date) {
      date.textContent = new Date().toLocaleDateString("fr-FR",
        { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    }

    var dossiersP = getJSON("/api/dossiers").catch(function () { return []; });
    var alertesP = getJSON("/api/dashboard/alertes").catch(function () { return null; });
    var indicsP = getJSON("/api/dashboard/indicateurs").catch(function () { return null; });

    Promise.all([dossiersP, alertesP, indicsP]).then(function (res) {
      var dossiers = Array.isArray(res[0]) ? res[0] : (res[0] && res[0].dossiers) || [];
      var alertes = res[1] || {};
      var indics = res[2] || {};

      var enCours = 0;
      var aValider = 0;
      var taches = 0;
      dossiers.forEach(function (d) {
        if (!d || ETATS_CLOS[d.state]) return;
        taches++;
        if (ETATS_EN_COURS[d.state]) enCours++;
        if (ETATS_A_VALIDER[d.state]) aValider++;
      });

      var nbAlertes = typeof alertes.nb_total === "number"
        ? alertes.nb_total
        : (alertes.alertes || []).length;

      var echeances = 0;
      var limite = Date.now() + 7 * 86400000;
      dossiers.forEach(function (d) {
        (d.echeances || []).forEach(function (e) {
          var quand = e && (e.date || e.echeance || e.due || e.ts);
          var ms = quand ? Date.parse(String(quand).length > 10 ? quand : quand + "T00:00:00") : NaN;
          if (!isNaN(ms) && ms >= Date.now() && ms <= limite) echeances++;
        });
      });

      texte($("cockpit-total"), dossiers.length || (indics.total_dossiers || 0));
      texte($("cockpit-en-cours"), enCours);
      texte($("cockpit-a-valider"), aValider);
      texte($("cockpit-alertes"), nbAlertes);
      texte($("cockpit-echeances"), echeances);

      rendTaches(dossiers);
      rendJour({
        taches: taches, enCours: enCours, alertes: nbAlertes, echeances: echeances
      });
      rendEcheances(dossiers);

      // Si l'API est muette, on le dit plutôt que d'afficher des zéros trompeurs.
      if (!dossiers.length) texte($("cockpit-total"), "—");
    });
  }

  function init() {
    var bouton = $("cockpit-refresh");
    if (bouton) bouton.addEventListener("click", charge);
    charge();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
