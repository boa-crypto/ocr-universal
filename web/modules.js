/**
 * UniOCR — bandeaux d'indicateurs des modules
 * ---------------------------------------------------------------------------
 * Chaque page « Vue d'ensemble » d'un module affiche quatre compteurs réels et
 * un lien vers la sous-page qui les détaille. Les valeurs viennent des
 * endpoints existants ; quand une source est vide ou indisponible, la tuile
 * affiche « — » plutôt qu'un zéro trompeur.
 *
 * Aucune logique métier ici : uniquement des comptages et des liens.
 */
(function () {
  "use strict";

  var CLOS = { exporte: true, archive: true };
  var A_VALIDER = { en_validation: true, revision_requise: true, incomplet: true };

  /* Chaque indicateur : { label, route, charger() -> Promise<number|string> } */
  var MODULES = {
    "tab-controle": {
      titre: "Contrôle & conformité",
      indicateurs: [
        { label: "Dossiers à valider", route: "#controle/documentaire",
          charger: function () { return compterDossiers(function (d) { return A_VALIDER[d.state]; }); } },
        { label: "Alertes actives", route: "#workspace/alertes",
          charger: function () { return compterAlertes(); } },
        { label: "Pièces manquantes", route: "#controle/manquants",
          charger: function () { return compterAlertes(function (a) { return a.type === "pieces_manquantes"; }); } },
        { label: "Règles de contrôle", route: "#controle/documentaire",
          charger: function () { return longueur("/api/controle/regles", "regles"); } }
      ]
    },
    "tab-maritime": {
      titre: "Opérations maritimes",
      indicateurs: [
        { label: "Conteneurs suivis", route: "#maritime/conteneurs",
          charger: function () { return longueur("/api/conteneurs"); } },
        { label: "Navires", route: "#maritime/navires",
          charger: function () { return longueur("/api/navires"); } },
        { label: "Connaissements B/L", route: "#maritime/bl",
          charger: function () { return longueur("/api/connaissements/bl"); } },
        { label: "Arrivées sous 30 j", route: "#maritime/arrivees",
          charger: function () { return compterDossiers(function (d) {
            if (!d.eta || CLOS[d.state]) return false;
            var echeance = new Date(d.eta);
            return !isNaN(echeance.getTime()) && echeance.getTime() <= Date.now() + 30 * 86400000;
          }); } }
      ]
    },
    "tab-douane": {
      titre: "Douane & réglementation",
      indicateurs: [
        { label: "Déclarations", route: "#douane/declarations",
          charger: function () { return longueur("/api/declarations"); } },
        { label: "Codes SH disponibles", route: "#douane/tarif",
          charger: function () { return longueur("/api/reglementation/codes-sh"); } },
        { label: "Dossiers classés", route: "#douane/declarations",
          charger: function () { return compterDossiers(function (d) { return !!d.code_sh; }); } },
        { label: "Dossiers ouverts", route: "#dossiers/en-cours",
          charger: function () { return compterDossiers(function (d) { return !CLOS[d.state]; }); } }
      ]
    },
    "tab-enlevissement": {
      titre: "Enlèvement & livraison",
      indicateurs: [
        { label: "Ordres d'enlèvement", route: "#enlevissement/ordres",
          charger: function () { return longueur("/api/terminal"); } },
        { label: "Expéditions", route: "#enlevissement/planning",
          charger: function () { return longueur("/api/expeditions"); } },
        { label: "Enlèvement à renseigner", route: "#enlevissement/planning",
          charger: function () { return compterDossiers(function (d) {
            return !CLOS[d.state] && !d.statut_enlevement && !d["statut_enlèvement"];
          }); } }
      ]
    },
    "tab-finance": {
      titre: "Finance & facturation",
      indicateurs: [
        { label: "Frais enregistrés", route: "#finance/frais",
          charger: function () { return longueur("/api/frais"); } },
        { label: "Dossiers concernés", route: "#finance/frais",
          charger: function () { return distinct("/api/frais", "dossier_id"); } },
        { label: "Dossiers clôturés", route: "#dossiers/clotures",
          charger: function () { return compterDossiers(function (d) { return !!CLOS[d.state]; }); } }
      ]
    },
    "tab-reports": {
      titre: "Rapports & statistiques",
      indicateurs: [
        { label: "Documents traités", route: "#documents/ocr",
          charger: function () { return champ("/api/stats", "jobs_done"); } },
        { label: "En erreur", route: "#reports/center",
          charger: function () { return champ("/api/stats", "jobs_error"); } },
        { label: "En cours", route: "#reports/center",
          charger: function () { return champ("/api/stats", "jobs_processing"); } },
        { label: "Progression moyenne", route: "#reports/center",
          charger: function () { return pourcentage("/api/stats", "mean_progress"); } }
      ]
    },
    "tab-referentiels": {
      titre: "Référentiels & paramètres",
      indicateurs: [
        { label: "Clients", route: "#referentiels/clients",
          charger: function () { return longueur("/api/clients"); } },
        { label: "Fournisseurs", route: "#referentiels/fournisseurs",
          charger: function () { return longueur("/api/fournisseurs"); } },
        { label: "Transporteurs", route: "#enlevissement/transporteurs",
          charger: function () { return longueur("/api/transport/transporteurs"); } }
      ]
    },
    "tab-admin": {
      titre: "Administration & sécurité",
      indicateurs: [
        { label: "Utilisateurs", route: "#admin/utilisateurs",
          charger: function () { return longueur("/api/rbac/utilisateurs", "utilisateurs"); } },
        { label: "Rôles disponibles", route: "#admin/roles",
          charger: function () { return longueur("/api/rbac/utilisateurs", "roles_disponibles"); } },
        { label: "Entrées d'audit", route: "#admin/journal",
          charger: function () { return longueur("/api/rbac/audit"); } },
        { label: "Notifications non lues", route: "#admin/utilisateurs",
          charger: function () { return longueur("/api/rbac/notifications", null,
            function (n) { return !n.lue; }); } }
      ]
    }
  };

  function jeton() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }

  function lire(url) {
    var entetes = { Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(url, { headers: entetes, credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  var dossiersCache = null;
  function dossiers() {
    if (!dossiersCache) {
      dossiersCache = lire("/api/dossiers").catch(function () { return []; });
    }
    return dossiersCache;
  }

  function compterDossiers(predicat) {
    return dossiers().then(function (liste) {
      return (Array.isArray(liste) ? liste : []).filter(predicat).length;
    });
  }

  function compterAlertes(predicat) {
    return lire("/api/dashboard/alertes").then(function (donnees) {
      var liste = (donnees && donnees.alertes) || [];
      return predicat ? liste.filter(predicat).length : liste.length;
    });
  }

  function longueur(url, cle, predicat) {
    return lire(url).then(function (donnees) {
      var liste = cle && donnees && !Array.isArray(donnees) ? donnees[cle] : donnees;
      if (!Array.isArray(liste)) return "—";
      return predicat ? liste.filter(predicat).length : liste.length;
    });
  }

  function distinct(url, champ) {
    return lire(url).then(function (donnees) {
      if (!Array.isArray(donnees)) return "—";
      var vus = {};
      donnees.forEach(function (item) {
        if (item && item[champ]) vus[item[champ]] = true;
      });
      return Object.keys(vus).length;
    });
  }

  function champ(url, cle) {
    return lire(url).then(function (donnees) {
      var v = donnees ? donnees[cle] : null;
      return typeof v === "number" ? v : "—";
    });
  }

  function pourcentage(url, cle) {
    return lire(url).then(function (donnees) {
      var v = donnees ? Number(donnees[cle]) : NaN;
      return isFinite(v) ? Math.round(v * 100) + " %" : "—";
    });
  }

  /* Les valeurs sont rafraîchies à chaque visite du module : un compteur
     affiché ne doit jamais dater d'une session précédente. */
  function recharger(bandeau) {
    Array.prototype.forEach.call(bandeau.querySelectorAll(".module-kpi"), function (lien) {
      var indicateur = lien._indicateur;
      if (!indicateur) return;
      Promise.resolve()
        .then(indicateur.charger)
        .then(function (valeur) {
          var cible = lien.querySelector(".module-kpi__val");
          if (cible) cible.textContent = (valeur === undefined || valeur === null) ? "—" : String(valeur);
          lien.classList.toggle("is-vide", valeur === "—");
        })
        .catch(function () {
          var cible = lien.querySelector(".module-kpi__val");
          if (cible) cible.textContent = "—";
          lien.classList.add("is-vide");
        });
    });
  }

  function construire(section, definition) {
    if (!section) return;
    var existant = section.querySelector(".module-kpis");
    if (existant) { recharger(existant); return; }
    var entete = section.querySelector("header");
    if (!entete) return;

    var bandeau = document.createElement("div");
    bandeau.className = "module-kpis";
    bandeau.setAttribute("role", "list");

    var tuiles = definition.indicateurs.map(function (indicateur) {
      var lien = document.createElement("a");
      lien.className = "module-kpi";
      lien.href = indicateur.route;
      lien.setAttribute("role", "listitem");

      var valeur = document.createElement("span");
      valeur.className = "module-kpi__val";
      valeur.textContent = "…";
      lien.appendChild(valeur);
      lien.appendChild(document.createElement("span")).className = "module-kpi__lbl";
      lien.lastChild.textContent = indicateur.label;
      lien._indicateur = indicateur;
      bandeau.appendChild(lien);
      return { lien: lien, valeur: valeur, indicateur: indicateur };
    });

    if (entete.nextSibling) section.insertBefore(bandeau, entete.nextSibling);
    else section.appendChild(bandeau);

    tuiles.forEach(function (tuile) {
      Promise.resolve()
        .then(tuile.indicateur.charger)
        .then(function (valeur) {
          tuile.valeur.textContent = (valeur === undefined || valeur === null) ? "—" : String(valeur);
          if (valeur === "—") tuile.lien.classList.add("is-vide");
        })
        .catch(function () {
          tuile.valeur.textContent = "—";
          tuile.lien.classList.add("is-vide");
        });
    });
      }

  function chargerSectionVisible() {
    var section = document.querySelector("section.page:not(.hidden)");
    if (!section) return;
    var definition = MODULES[section.id];
    if (!definition) return;
    construire(section, definition);
  }

  function demarrer() {
    window.addEventListener("hashchange", function () { setTimeout(chargerSectionVisible, 30); });
    setTimeout(chargerSectionVisible, 400);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.UniOCRModules = { modules: MODULES, chargerSectionVisible: chargerSectionVisible };
})();
