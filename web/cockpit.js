/**
 * UniOCR — Cockpit (page d'accueil)
 * ---------------------------------------------------------------------------
 * Alimente le cockpit avec des données strictement réelles :
 *   - dossiers            → GET /api/dossiers
 *   - alertes             → GET /api/dashboard/alertes
 *   - série temporelle    → GET /api/dashboard/serie-dossiers?jours=N
 *
 * Aucun chiffre n'est inventé : quand une information n'est pas renseignée
 * côté métier (ETA, statut d'enlèvement), la tuile affiche « — » et explique
 * pourquoi. L'interface ne comble jamais un trou par une valeur plausible.
 */
(function () {
  "use strict";

  var ETATS_CLOS = { exporte: true, archive: true };
  var ETATS_EN_ATTENTE = { en_validation: true, revision_requise: true };
  var ETATS_A_RISQUE = { revision_requise: true, incomplet: true, erreur_traitement: true };
  var PRIORITES = { urgente: 0, haute: 1, normale: 2, basse: 3 };

  var COULEURS_ETATS = {
    en_preparation: "#1677FF",
    traitement_en_cours: "#00D9FF",
    en_validation: "#9466F5",
    revision_requise: "#F59E0B",
    incomplet: "#F04452",
    erreur_traitement: "#F04452",
    exporte: "#00CBA8",
    archive: "#4B6485"
  };

  var etat = {
    dossiers: [],
    alertes: [],
    periode: 30,
    chargement: 0
  };

  function $(id) { return document.getElementById(id); }

  function apiBase() {
    return (typeof window.__apiBase === "string" ? window.__apiBase : "");
  }

  function entetes() {
    var jeton = "";
    try { jeton = sessionStorage.getItem("uniocr_token") || ""; } catch (e) { jeton = ""; }
    return jeton ? { Authorization: "Bearer " + jeton } : {};
  }

  function api(chemin) {
    return fetch(apiBase() + chemin, { headers: entetes() }).then(function (reponse) {
      if (!reponse.ok) throw new Error(chemin + " → HTTP " + reponse.status);
      return reponse.json();
    });
  }

  function elt(nom, classe, texte) {
    var noeud = document.createElement(nom);
    if (classe) noeud.className = classe;
    if (texte !== undefined && texte !== null) noeud.textContent = String(texte);
    return noeud;
  }

  function nombre(valeur) {
    var n = Number(valeur);
    return isFinite(n) ? n : 0;
  }

  function jour(valeur) {
    if (!valeur) return null;
    // Les horodatages du store sont en secondes ; les ETA sont des dates ISO.
    if (typeof valeur === "string" && isNaN(Number(valeur))) {
      var iso = new Date(valeur);
      return isNaN(iso.getTime()) ? null : iso;
    }
    var n = Number(valeur);
    if (!isFinite(n) || n === 0) return null;
    var d = new Date(n < 1e12 ? n * 1000 : n);
    return isNaN(d.getTime()) ? null : d;
  }

  function dateCourte(valeur) {
    var d = jour(valeur);
    if (!d) return "—";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  }

  function dateLongue(valeur) {
    var d = jour(valeur);
    if (!d) return "—";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
  }

  function joursDepuis(valeur) {
    var d = jour(valeur);
    if (!d) return null;
    return Math.floor((Date.now() - d.getTime()) / 86400000);
  }

  function texteEtat(dossier) {
    return dossier.state_label || (dossier.state || "").replace(/_/g, " ");
  }

  function pastilleEtat(dossier) {
    var classe = "badge badge--neutral";
    if (dossier.state === "revision_requise") classe = "badge badge--warn";
    else if (dossier.state === "incomplet" || dossier.state === "erreur_traitement") classe = "badge badge--danger";
    else if (dossier.state === "en_validation") classe = "badge badge--info";
    else if (ETATS_CLOS[dossier.state]) classe = "badge badge--ok";
    else if (dossier.state === "traitement_en_cours") classe = "badge badge--info";
    return elt("span", classe, texteEtat(dossier));
  }

  /* ── KPI ─────────────────────────────────────────────────────────── */
  function renseigner(id, valeur, texte) {
    var cible = $(id);
    if (!cible) return;
    cible.textContent = valeur === null || valeur === undefined ? "—" : String(valeur);
    if (texte) {
      var sub = $(id + "-sub");
      if (sub) sub.textContent = texte;
    }
  }

  function rendKpis(serie) {
    var dossiers = etat.dossiers;
    var actifs = dossiers.filter(function (d) { return !ETATS_CLOS[d.state]; }).length;
    var attente = dossiers.filter(function (d) { return ETATS_EN_ATTENTE[d.state]; }).length;

    renseigner("kpi-actifs", actifs, "hors circuit clôturé (export / archive)");
    renseigner("kpi-attente", attente, "validation ou révision humaine");
    renseigner("kpi-anomalies", etat.alertes.length, "alertes documentaires actives");

    var limite = Date.now() + 30 * 86400000;
    var avecEta = dossiers.filter(function (d) { return d.eta; });
    var arrivees = avecEta.filter(function (d) {
      var echeance = new Date(d.eta);
      return !isNaN(echeance.getTime()) && echeance.getTime() <= limite &&
        !ETATS_CLOS[d.state];
    }).length;
    renseigner("kpi-arrivees", avecEta.length ? arrivees : null,
      avecEta.length ? "ETA renseignée sous 30 jours" : "aucune ETA saisie dans les dossiers");

    var avecEnlevement = dossiers.filter(function (d) {
      return d.statut_enlevement || d["statut_enlèvement"];
    });
    var enAttenteLivraison = avecEnlevement.filter(function (d) {
      var s = String(d.statut_enlevement || d["statut_enlèvement"] || "").toLowerCase();
      return s !== "livre" && s !== "livré" && s !== "confirme" && !ETATS_CLOS[d.state];
    }).length;
    renseigner("kpi-livraisons", avecEnlevement.length ? enAttenteLivraison : null,
      avecEnlevement.length ? "enlèvement non encore confirmé" : "statut d'enlèvement non renseigné");

    // Étincelles : uniquement si la série réelle contient des données.
    if (serie && serie.series && serie.series.length > 1) {
      var crees = serie.series.map(function (l) { return l.crees; });
      var traites = serie.series.map(function (l) { return l.traites; });
      var clos = serie.series.map(function (l) { return l.clotures; });
      if (window.UniOCRCharts) {
        window.UniOCRCharts.sparkline($("spark-actifs"), crees, { color: "#1677FF" });
        window.UniOCRCharts.sparkline($("spark-attente"), traites, { color: "#F59E0B" });
        window.UniOCRCharts.sparkline($("spark-anomalies"), traites, { color: "#F04452" });
        window.UniOCRCharts.sparkline($("spark-arrivees"), crees, { color: "#00D9FF" });
        window.UniOCRCharts.sparkline($("spark-livraisons"), clos, { color: "#9466F5" });
      }
    }
  }

  /* ── Mes tâches ──────────────────────────────────────────────────── */
  function descriptionTache(dossier) {
    if (dossier.state === "revision_requise") return "Révision documentaire demandée";
    if (dossier.state === "incomplet") return "Pièces obligatoires manquantes";
    if (dossier.state === "en_validation") return "Contrôle en attente de validation";
    if (dossier.state === "en_preparation") return "Compléter les pièces du dossier";
    if (dossier.state === "traitement_en_cours") return "Extraction OCR en cours";
    return "Suivre l'avancement du dossier";
  }

  function niveauPriorite(dossier) {
    if (dossier.state === "incomplet" || dossier.state === "revision_requise") return "haute";
    return (dossier.priorite || "normale").toLowerCase();
  }

  function classePriorite(priorite) {
    if (priorite === "urgente") return "badge badge--danger";
    if (priorite === "haute") return "badge badge--warn";
    if (priorite === "basse") return "badge badge--neutral";
    return "badge badge--info";
  }

  function ligneTache(dossier) {
    var ligne = elt("div", "task-row");

    var icone = elt("span", "row-ic");
    if (dossier.state === "incomplet" || dossier.state === "erreur_traitement") icone.className += " row-ic--danger";
    else if (dossier.state === "revision_requise") icone.className += " row-ic--warn";
    else if (dossier.state === "en_validation") icone.className += " row-ic--ok";
    icone.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' +
      '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 9h6M9 13h6M9 17h4"/></svg>';
    ligne.appendChild(icone);

    var principal = elt("span", "row-main");
    var titre = elt("span", "row-title", dossier.label || dossier.id);
    var sous = elt("span", "row-sub",
      descriptionTache(dossier) +
      (dossier.client_importateur ? " · " + dossier.client_importateur : "") +
      " · maj " + dateCourte(dossier.updated_at));
    principal.appendChild(titre);
    principal.appendChild(sous);
    ligne.appendChild(principal);

    var meta = elt("span", "row-meta");
    meta.appendChild(pastilleEtat(dossier));
    meta.appendChild(elt("span", classePriorite(niveauPriorite(dossier)), niveauPriorite(dossier)));
    ligne.appendChild(meta);

    var action = elt("button", "row-action", "Ouvrir");
    action.type = "button";
    action.addEventListener("click", function () {
      if (window.UniOCRShell && window.UniOCRShell.ouvrirDossier) {
        window.UniOCRShell.ouvrirDossier(dossier.id);
      } else {
        window.location.hash = "#dossiers/tous";
      }
    });
    ligne.appendChild(action);
    return ligne;
  }

  function rendTaches() {
    var cible = $("cockpit-tasks");
    if (!cible) return;
    cible.textContent = "";

    var ouverts = etat.dossiers.filter(function (d) { return !ETATS_CLOS[d.state]; });
    ouverts.sort(function (a, b) {
      var pa = PRIORITES[niveauPriorite(a)];
      var pb = PRIORITES[niveauPriorite(b)];
      pa = pa === undefined ? 2 : pa;
      pb = pb === undefined ? 2 : pb;
      if (pa !== pb) return pa - pb;
      return nombre(a.updated_at) - nombre(b.updated_at);
    });

    var selection = ouverts.slice(0, 6);
    if (!selection.length) {
      cible.appendChild(elt("p", "ws-empty", "Aucune tâche ouverte : tous les dossiers sont traités."));
      return;
    }
    selection.forEach(function (dossier) { cible.appendChild(ligneTache(dossier)); });
  }

  /* ── Progression ─────────────────────────────────────────────────── */
  function rendProgression() {
    var cible = $("cockpit-progression");
    if (!cible) return;
    cible.textContent = "";

    var ouverts = etat.dossiers.filter(function (d) { return !ETATS_CLOS[d.state]; });
    var aRisque = ouverts.filter(function (d) { return ETATS_A_RISQUE[d.state]; });
    var enRetard = ouverts.filter(function (d) {
      var age = joursDepuis(d.updated_at);
      return age !== null && age > 7 && !ETATS_A_RISQUE[d.state];
    });
    var aLHeure = Math.max(0, ouverts.length - aRisque.length - enRetard.length);
    var total = Math.max(1, ouverts.length);

    var lignes = [
      { libelle: "À l'heure", valeur: aLHeure, classe: "ok", hint: "activité dans les 7 derniers jours" },
      { libelle: "En retard", valeur: enRetard.length, classe: "warn", hint: "aucun mouvement depuis plus de 7 jours" },
      { libelle: "À risque", valeur: aRisque.length, classe: "danger", hint: "révision requise ou pièces manquantes" }
    ];

    lignes.forEach(function (ligne) {
      var bloc = elt("div");
      bloc.style.padding = "10px 2px";
      var tete = elt("div");
      tete.style.display = "flex";
      tete.style.justifyContent = "space-between";
      tete.style.marginBottom = "6px";
      tete.appendChild(elt("span", "row-title", ligne.libelle));
      var valeurs = elt("span", "row-meta");
      valeurs.appendChild(elt("span", "row-sub", Math.round((ligne.valeur / total) * 100) + " %"));
      valeurs.appendChild(elt("strong", null, ligne.valeur));
      tete.appendChild(valeurs);
      bloc.appendChild(tete);

      var barre = elt("div", "progress progress--" + ligne.classe);
      var remplissage = elt("span");
      remplissage.style.width = Math.round((ligne.valeur / total) * 100) + "%";
      barre.appendChild(remplissage);
      bloc.appendChild(barre);
      bloc.appendChild(elt("div", "row-sub", ligne.hint));
      cible.appendChild(bloc);
    });
  }

  /* ── Prochaines arrivées ─────────────────────────────────────────── */
  function rendArrivees() {
    var cible = $("cockpit-arrivals");
    if (!cible) return;
    cible.textContent = "";

    var avecEta = etat.dossiers.filter(function (d) {
      if (!d.eta) return false;
      var date = new Date(d.eta);
      return !isNaN(date.getTime());
    });
    avecEta.sort(function (a, b) { return new Date(a.eta) - new Date(b.eta); });

    if (!avecEta.length) {
      cible.appendChild(elt("p", "ws-empty",
        "Aucune ETA saisie. Renseignez l'ETA d'un dossier (onglet Transport maritime) pour alimenter ce panneau."));
      return;
    }

    avecEta.slice(0, 5).forEach(function (dossier) {
      var ligne = elt("div", "arrival-row");
      var icone = elt("span", "row-ic");
      icone.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' +
        '<path d="M3 17h18l-3-7H6z"/><path d="M12 10V4"/></svg>';
      ligne.appendChild(icone);

      var principal = elt("span", "row-main");
      principal.appendChild(elt("span", "row-title",
        (dossier.navire || "Navire non renseigné") +
        (dossier.numero_voyage ? " · " + dossier.numero_voyage : "")));
      var ports = [dossier.port_chargement, dossier.port_destination].filter(Boolean).join(" → ");
      principal.appendChild(elt("span", "row-sub",
        (ports || "ports non renseignés") +
        (dossier.numero_conteneur ? " · " + dossier.numero_conteneur : "")));
      ligne.appendChild(principal);

      var meta = elt("span", "row-meta");
      meta.appendChild(elt("span", "badge badge--info", "ETA " + dateCourte(dossier.eta)));
      ligne.appendChild(meta);

      var action = elt("button", "row-action", "Dossier");
      action.type = "button";
      action.addEventListener("click", function () {
        if (window.UniOCRShell && window.UniOCRShell.ouvrirDossier) {
          window.UniOCRShell.ouvrirDossier(dossier.id);
        }
      });
      ligne.appendChild(action);
      cible.appendChild(ligne);
    });
  }

  /* ── Alertes récentes ────────────────────────────────────────────── */
  function rendAlertes() {
    var cible = $("cockpit-alerts");
    if (!cible) return;
    cible.textContent = "";

    if (!etat.alertes.length) {
      cible.appendChild(elt("p", "ws-empty", "Aucune alerte active."));
      return;
    }

    etat.alertes.slice(0, 5).forEach(function (alerte) {
      var ligne = elt("div", "alert-row");
      var gravite = alerte.niveau === "critical" || alerte.niveau === "error" ? "danger"
        : alerte.niveau === "warning" ? "warn" : "";
      var icone = elt("span", "row-ic" + (gravite ? " row-ic--" + gravite : ""));
      icone.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">' +
        '<path d="M10.3 4.3 2.6 18a1.7 1.7 0 0 0 1.5 2.5h15.8a1.7 1.7 0 0 0 1.5-2.5L13.7 4.3a1.7 1.7 0 0 0-3.4 0z"/>' +
        '<path d="M12 9v4m0 3h.01"/></svg>';
      ligne.appendChild(icone);

      var principal = elt("span", "row-main");
      principal.appendChild(elt("span", "row-title", alerte.titre || alerte.type));
      var pieces = (alerte.pieces_manquantes || []).join(", ");
      principal.appendChild(elt("span", "row-sub",
        (alerte.dossier_id || "dossier non précisé") + (pieces ? " · " + pieces : "")));
      ligne.appendChild(principal);

      var meta = elt("span", "row-meta");
      var classe = gravite === "danger" ? "badge badge--danger"
        : gravite === "warn" ? "badge badge--warn" : "badge badge--info";
      meta.appendChild(elt("span", classe, alerte.niveau || "info"));
      ligne.appendChild(meta);

      var action = elt("button", "row-action", "Traiter");
      action.type = "button";
      action.addEventListener("click", function () {
        if (window.UniOCRShell && window.UniOCRShell.ouvrirDossier) {
          window.UniOCRShell.ouvrirDossier(alerte.dossier_id);
        }
      });
      ligne.appendChild(action);
      cible.appendChild(ligne);
    });
  }

  /* ── Graphiques ──────────────────────────────────────────────────── */
  function rendGraphique(serie) {
    var hote = $("cockpit-chart");
    if (!hote || !window.UniOCRCharts) return;
    if (!serie || !serie.series || !serie.series.length) {
      hote.textContent = "";
      hote.appendChild(elt("p", "ws-empty", "Aucune donnée sur la période."));
      return;
    }
    var labels = serie.series.map(function (l) { return l.date; });
    window.UniOCRCharts.line(hote, {
      labels: labels,
      series: [
        { key: "crees", label: "Créés", values: serie.series.map(function (l) { return l.crees; }), color: "#1677FF", fill: true },
        { key: "traites", label: "Traités", values: serie.series.map(function (l) { return l.traites; }), color: "#00D9FF" },
        { key: "clotures", label: "Clôturés", values: serie.series.map(function (l) { return l.clotures; }), color: "#00CBA8" }
      ],
      height: 236,
      label: "Évolution des dossiers sur " + serie.periode_jours + " jours"
    });
    var etiq = $("chart-period-label");
    if (etiq) {
      etiq.textContent = serie.periode_jours + " derniers jours · " +
        serie.totaux.crees + " créés, " + serie.totaux.traites + " traités";
    }
  }

  function rendDonut() {
    var hote = $("cockpit-donut");
    if (!hote || !window.UniOCRCharts) return;
    var compte = {};
    etat.dossiers.forEach(function (d) {
      compte[d.state_label || d.state] = (compte[d.state_label || d.state] || 0) + 1;
    });
    var items = Object.keys(compte).map(function (cle) {
      var brut = null;
      Object.keys(COULEURS_ETATS).forEach(function (code) {
        var dossier = etat.dossiers.find(function (d) { return (d.state_label || d.state) === cle; });
        if (dossier && dossier.state === code) brut = COULEURS_ETATS[code];
      });
      return { label: cle, value: compte[cle], color: brut || "#4B6485" };
    }).sort(function (a, b) { return b.value - a.value; });

    window.UniOCRCharts.donut(hote, {
      items: items,
      size: 168,
      centre: "dossiers",
      label: "Répartition des dossiers par état"
    });
  }

  /* ── Chargement ──────────────────────────────────────────────────── */
  function chargerSerie() {
    return api("/api/dashboard/serie-dossiers?jours=" + etat.periode)
      .catch(function () { return null; });
  }

  function charger() {
    var jeton = ++etat.chargement;
    var bouton = $("cockpit-refresh");
    if (bouton) bouton.classList.add("is-busy");

    return Promise.all([
      api("/api/dossiers").catch(function () { return []; }),
      api("/api/dashboard/alertes").catch(function () { return { alertes: [] }; }),
      chargerSerie()
    ]).then(function (resultats) {
      if (jeton !== etat.chargement) return;
      etat.dossiers = Array.isArray(resultats[0]) ? resultats[0]
        : (resultats[0] && resultats[0].dossiers) || [];
      etat.alertes = (resultats[1] && resultats[1].alertes) || [];
      var serie = resultats[2];

      rendKpis(serie);
      rendTaches();
      rendProgression();
      rendArrivees();
      rendAlertes();
      rendGraphique(serie);
      rendDonut();

      var synchro = $("hero-sync");
      if (synchro) {
        synchro.textContent = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      }
      var systeme = $("hero-system");
      if (systeme) {
        systeme.textContent = resultats[1] && resultats[1].alertes
          ? "Système opérationnel — " + etat.alertes.length + " alerte(s)"
          : "Système opérationnel";
      }
    }).catch(function (erreur) {
      var taches = $("cockpit-tasks");
      if (taches) {
        taches.textContent = "";
        taches.appendChild(elt("p", "ws-empty",
          "Cockpit indisponible : " + (erreur && erreur.message ? erreur.message : "API non jointe") + "."));
      }
    }).then(function () {
      if (bouton) bouton.classList.remove("is-busy");
    });
  }

  function initPeriode() {
    var groupe = $("chart-period");
    if (!groupe) return;
    groupe.addEventListener("click", function (ev) {
      var bouton = ev.target.closest ? ev.target.closest("button[data-period]") : null;
      if (!bouton) return;
      var periode = Number(bouton.dataset.period);
      if (!periode || periode === etat.periode) return;
      etat.periode = periode;
      groupe.querySelectorAll("button").forEach(function (b) {
        var actif = Number(b.dataset.period) === periode;
        b.classList.toggle("is-active", actif);
        b.setAttribute("aria-pressed", actif ? "true" : "false");
      });
      chargerSerie().then(rendGraphique);
    });
  }

  function demarrer() {
    if (!$("tab-cockpit")) return;
    var bouton = $("cockpit-refresh");
    if (bouton) {
      bouton.addEventListener("click", function () {
        charger().then(function () {
          if (typeof window.toast === "function") window.toast("Cockpit actualisé", "success");
        });
      });
    }
    window.addEventListener("uniocr:refresh", charger);
    document.addEventListener("click", function (ev) {
      var lien = ev.target.closest ? ev.target.closest('[data-nav="cockpit"]') : null;
      if (lien) charger();
    });
    // Premier chargement dès que la page est visible : le cockpit est la vue
    // d'accueil, il ne doit pas attendre un clic.
    charger();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.Cockpit = { charger: charger, etat: etat };
})();
