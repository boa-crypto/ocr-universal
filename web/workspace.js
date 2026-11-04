/* ============================================================================
   UniOCR — Mon espace de travail
   ----------------------------------------------------------------------------
   Alimente les onglets « Mes tâches », « À valider », « En attente »,
   « Mes alertes » et « Dossiers récents » avec les données réelles, et relie
   les sous-routes du menu (#workspace/…) aux onglets correspondants.
   ========================================================================== */
(function () {
  "use strict";

  var ONGLETS = {
    taches: "taches",
    valider: "valider",
    "en-attente": "attente",
    attente: "attente",
    alertes: "alertes",
    recents: "recents"
  };

  var A_VALIDER = { en_validation: true, revision_requise: true, incomplet: true };
  var EN_ATTENTE = { en_preparation: true, traitement_en_cours: true };
  var CLOS = { exporte: true, archive: true };

  var cache = { dossiers: null, alertes: null };

  function $(id) { return document.getElementById(id); }

  function jeton() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }

  function getJSON(chemin) {
    var entetes = { Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(chemin, { headers: entetes, credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function el(tag, classe, texte) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texte !== undefined && texte !== null) n.textContent = String(texte);
    return n;
  }

  function identifiant(d) { return d.reference || d.label || d.id; }

  function dateCourte(ts) {
    if (!ts) return "";
    var d = new Date(Number(ts) * 1000);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  }

  function rendreListe(conteneur, entrees, messageVide) {
    conteneur.textContent = "";
    if (!entrees.length) {
      conteneur.appendChild(el("p", "ws-list__vide", messageVide));
      return;
    }
    var liste = el("div", "ws-list");
    entrees.forEach(function (e) {
      var ligne = el("div", "ws-list__row");
      var principal = el("div", "ws-list__main");
      principal.appendChild(el("span", "ws-list__titre", e.titre));
      if (e.meta) principal.appendChild(el("span", "ws-list__meta", e.meta));
      ligne.appendChild(principal);
      if (e.pill) {
        ligne.appendChild(el("span", "status-pill status-pill--" + e.pill[1], e.pill[0]));
      }
      liste.appendChild(ligne);
    });
    conteneur.appendChild(liste);
  }

  function entreesDossiers(filtre) {
    var source = cache.dossiers || [];
    return source.filter(filtre).slice(0, 25).map(function (d) {
      return {
        titre: identifiant(d),
        meta: [d.client_importateur || "Client non renseigné",
               d.state_label || d.state,
               dateCourte(d.updated_at || d.date_ouverture)].filter(Boolean).join(" · ")
      };
    });
  }

  function rendre(onglet) {
    var cible = $("workspace-" + onglet + "-content");
    if (!cible) return;

    if (onglet === "alertes") {
      if (!cache.alertes) {
        cible.textContent = "";
        cible.appendChild(el("p", "ws-list__vide", "Chargement des alertes…"));
        return;
      }
      var alertes = (cache.alertes.alertes || []).slice(0, 25).map(function (a) {
        return {
          titre: a.message || a.type || "Alerte",
          meta: [a.dossier_id, a.type].filter(Boolean).join(" · "),
          pill: [a.severity === "error" ? "Erreur" : "Attention",
                 a.severity === "error" ? "danger" : "warn"]
        };
      });
      rendreListe(cible, alertes, "Aucune alerte active. Tout est en ordre.");
      return;
    }

    if (!cache.dossiers) {
      cible.textContent = "";
      cible.appendChild(el("p", "ws-list__vide", "Chargement des dossiers…"));
      return;
    }

    if (onglet === "taches") {
      rendreListe(cible,
        entreesDossiers(function (d) { return A_VALIDER[d.state] || d.priorite === "haute"; }),
        "Aucune tâche ne vous est assignée pour le moment.");
    } else if (onglet === "valider") {
      rendreListe(cible,
        entreesDossiers(function (d) { return A_VALIDER[d.state]; }),
        "Aucun document en attente de validation.");
    } else if (onglet === "attente") {
      rendreListe(cible,
        entreesDossiers(function (d) { return EN_ATTENTE[d.state]; }),
        "Aucun dossier en attente de traitement.");
    } else if (onglet === "recents") {
      var recents = (cache.dossiers || []).slice().sort(function (a, b) {
        return (b.updated_at || b.date_ouverture || 0) - (a.updated_at || a.date_ouverture || 0);
      }).slice(0, 20);
      rendreListe(cible, recents.map(function (d) {
        return {
          titre: identifiant(d),
          meta: [d.client_importateur || "Client non renseigné",
                 dateCourte(d.updated_at || d.date_ouverture)].filter(Boolean).join(" · ")
        };
      }), "Aucun dossier pour le moment.");
    }
  }

  function activer(onglet) {
    var cle = ONGLETS[onglet] || "taches";
    var barre = $("workspace-tabs");
    if (barre) {
      Array.prototype.forEach.call(barre.querySelectorAll("[data-tab]"), function (b) {
        var on = b.getAttribute("data-tab") === cle;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
    }
    ["taches", "valider", "attente", "alertes", "recents"].forEach(function (id) {
      var panneau = $("workspace-" + id);
      if (panneau) panneau.style.display = id === cle ? "" : "none";
    });
    rendre(cle);
  }

  function appliquerRoute() {
    var hash = (window.location.hash || "").replace(/^#/, "");
    if (hash.indexOf("workspace") !== 0) return;
    var sous = hash.split("/")[1] || "taches";
    activer(sous);
  }

  function charger() {
    if (!cache.dossiers) {
      getJSON("/api/dossiers").then(function (d) {
        cache.dossiers = Array.isArray(d) ? d : [];
        appliquerRoute();
      }).catch(function () {
        var cible = $("workspace-taches-content");
        if (cible) {
          cible.textContent = "";
          cible.appendChild(el("p", "ws-list__vide",
            "Impossible de charger les dossiers. Actualisez la page."));
        }
      });
    }
    if (!cache.alertes) {
      getJSON("/api/dashboard/alertes").then(function (a) {
        cache.alertes = a || { alertes: [] };
        appliquerRoute();
      }).catch(function () {
        cache.alertes = { alertes: [] };
        appliquerRoute();
      });
    }
  }

  function demarrer() {
    var barre = $("workspace-tabs");
    if (!barre) return;
    barre.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-tab]");
      if (!btn) return;
      var cle = btn.getAttribute("data-tab");
      if (window.location.hash.indexOf("#workspace") === 0) {
        window.location.hash = "#workspace/" + (cle === "attente" ? "en-attente" : cle);
      } else {
        activer(cle);
      }
    });
    window.addEventListener("hashchange", appliquerRoute);
    charger();
    activer("taches");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.EspaceTravail = { activer: activer, charger: charger };
})();
