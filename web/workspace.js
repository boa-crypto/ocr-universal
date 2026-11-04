/* ============================================================================
   UniOCR — Mon espace de travail
   ----------------------------------------------------------------------------
   Centre opérationnel personnalisé : chaque ligne est un dossier réel, que
   l'on peut ouvrir, filtrer, trier et rechercher. Aucune entrée n'est
   fabriquée : la source est `/api/dossiers` (et `/api/dashboard/alertes`
   pour l'onglet alertes).
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
  var A_RISQUE = { revision_requise: true, incomplet: true, erreur_traitement: true };

  var cache = { dossiers: null, alertes: null };

  /* État de la vue (filtres, tri, pagination) — purement côté interface. */
  var vue = {
    onglet: "taches",
    recherche: "",
    priorite: "",
    statut: "",
    tri: "recent",
    page: 1,
    parPage: 20
  };

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

  function ouvert(id) {
    if (window.UniOCRShell && window.UniOCRShell.ouvrirDossier) {
      window.UniOCRShell.ouvrirDossier(id);
    } else {
      window.location.hash = "#dossiers/tous";
    }
  }

  /* ── Barre d'outils ───────────────────────────────────────────────── */

  function champSelect(id, libelle, options) {
    var boite = el("div", "ws-filter");
    var label = el("label", "ws-filter__lbl", libelle);
    label.setAttribute("for", id);
    var select = el("select", "ws-filter__input");
    select.id = id;
    options.forEach(function (opt) {
      var option = el("option", null, opt[1]);
      option.value = opt[0];
      select.appendChild(option);
    });
    boite.appendChild(label);
    boite.appendChild(select);
    return { boite: boite, select: select };
  }

  function construireBarre() {
    if ($("workspace-toolbar")) return;
    var conteneur = $("workspace-content");
    if (!conteneur) return;

    var barre = el("div", "ws-toolbar");
    barre.id = "workspace-toolbar";

    var recherche = el("div", "ws-search");
    var icone = el("span", "ws-search__ic");
    icone.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>';
    var input = el("input", "ws-search__input");
    input.type = "search";
    input.id = "workspace-search";
    input.placeholder = "Rechercher un dossier, un client, une référence…";
    input.setAttribute("aria-label", "Rechercher dans l'espace de travail");
    recherche.appendChild(icone);
    recherche.appendChild(input);
    barre.appendChild(recherche);

    var priorite = champSelect("workspace-priorite", "Priorité", [
      ["", "Toutes"], ["haute", "Haute"], ["normale", "Normale"], ["basse", "Basse"]
    ]);
    barre.appendChild(priorite.boite);

    var statut = champSelect("workspace-statut", "Statut", [
      ["", "Tous"],
      ["a-valider", "À valider"],
      ["a-risque", "À risque"],
      ["en-attente", "En attente"],
      ["clos", "Clôturés"]
    ]);
    barre.appendChild(statut.boite);

    var tri = champSelect("workspace-tri", "Trier par", [
      ["recent", "Activité récente"],
      ["ancien", "Plus ancien d'abord"],
      ["reference", "Référence (A→Z)"]
    ]);
    barre.appendChild(tri.boite);

    var compteur = el("span", "ws-toolbar__count");
    compteur.id = "workspace-count";
    barre.appendChild(compteur);

    conteneur.parentNode.insertBefore(barre, conteneur);

    var rafraichir = function () { vue.page = 1; rendre(vue.onglet); };
    input.addEventListener("input", function () { vue.recherche = input.value; rafraichir(); });
    priorite.select.addEventListener("change", function () { vue.priorite = priorite.select.value; rafraichir(); });
    statut.select.addEventListener("change", function () { vue.statut = statut.select.value; rafraichir(); });
    tri.select.addEventListener("change", function () { vue.tri = tri.select.value; rafraichir(); });
  }

  /* ── Sélection et filtrage ────────────────────────────────────────── */

  function source(onglet) {
    var dossiers = cache.dossiers || [];
    if (onglet === "recents") {
      return dossiers.slice().sort(function (a, b) {
        return (b.updated_at || b.date_ouverture || 0) - (a.updated_at || a.date_ouverture || 0);
      }).slice(0, 60);
    }
    if (onglet === "taches") {
      return dossiers.filter(function (d) { return A_VALIDER[d.state] || d.priorite === "haute"; });
    }
    if (onglet === "valider") {
      return dossiers.filter(function (d) { return A_VALIDER[d.state]; });
    }
    if (onglet === "attente") {
      return dossiers.filter(function (d) { return EN_ATTENTE[d.state]; });
    }
    return dossiers;
  }

  function correspond(d) {
    if (!vue.recherche) return true;
    var terme = vue.recherche.trim().toLowerCase();
    return [d.id, d.label, d.reference, d.client_importateur, d.fournisseur,
            d.navire, d.reference_bl, d.state_label, d.state].some(function (v) {
      return v && String(v).toLowerCase().indexOf(terme) !== -1;
    });
  }

  function passeStatut(d) {
    if (!vue.statut) return true;
    if (vue.statut === "a-valider") return !!A_VALIDER[d.state];
    if (vue.statut === "a-risque") return !!A_RISQUE[d.state];
    if (vue.statut === "en-attente") return !!EN_ATTENTE[d.state];
    if (vue.statut === "clos") return !!CLOS[d.state];
    return true;
  }

  function filtrer(liste) {
    return liste.filter(function (d) {
      if (!correspond(d) || !passeStatut(d)) return false;
      if (vue.priorite && (d.priorite || "normale") !== vue.priorite) return false;
      return true;
    });
  }

  function trier(liste) {
    var copie = liste.slice();
    if (vue.tri === "reference") {
      copie.sort(function (a, b) { return String(identifiant(a)).localeCompare(String(identifiant(b))); });
    } else if (vue.tri === "ancien") {
      copie.sort(function (a, b) {
        return (a.updated_at || a.date_ouverture || 0) - (b.updated_at || b.date_ouverture || 0);
      });
    } else {
      copie.sort(function (a, b) {
        return (b.updated_at || b.date_ouverture || 0) - (a.updated_at || a.date_ouverture || 0);
      });
    }
    return copie;
  }

  /* ── Rendu ────────────────────────────────────────────────────────── */

  function pastille(d) {
    var classe = "status-pill status-pill--muted";
    if (d.state === "revision_requise") classe = "status-pill status-pill--warn";
    else if (d.state === "incomplet" || d.state === "erreur_traitement") classe = "status-pill status-pill--danger";
    else if (d.state === "en_validation") classe = "status-pill status-pill--info";
    else if (d.state === "traitement_en_cours") classe = "status-pill status-pill--info";
    else if (d.state === "exporte" || d.state === "archive") classe = "status-pill status-pill--ok";
    return el("span", classe, d.state_label || d.state || "—");
  }

  function ligneDossier(d) {
    var ligne = el("div", "ws-list__row ws-list__row--action");
    ligne.tabIndex = 0;
    ligne.setAttribute("role", "button");
    ligne.setAttribute("aria-label", "Ouvrir le dossier " + identifiant(d));

    var principal = el("div", "ws-list__main");
    principal.appendChild(el("span", "ws-list__titre", identifiant(d)));
    principal.appendChild(el("span", "ws-list__meta",
      [d.client_importateur || "Client non renseigné",
       d.navire, d.reference_bl,
       dateCourte(d.updated_at || d.date_ouverture)].filter(Boolean).join(" · ")));
    ligne.appendChild(principal);

    var meta = el("div", "ws-list__meta-right");
    meta.appendChild(pastille(d));
    if (d.priorite && d.priorite !== "normale") {
      meta.appendChild(el("span", "badge " + (d.priorite === "haute" ? "badge--danger" : "badge--neutral"),
        "Priorité " + d.priorite));
    }
    ligne.appendChild(meta);

    var action = el("button", "btn ghost sm", "Ouvrir");
    action.type = "button";
    action.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ouvert(d.id);
    });
    ligne.appendChild(action);

    ligne.addEventListener("click", function () { ouvert(d.id); });
    ligne.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ouvert(d.id); }
    });
    return ligne;
  }

  function ligneAlerte(a) {
    var ligne = el("div", "ws-list__row ws-list__row--action");
    var principal = el("div", "ws-list__main");
    principal.appendChild(el("span", "ws-list__titre", a.titre || a.message || a.type || "Alerte"));
    principal.appendChild(el("span", "ws-list__meta",
      [a.dossier_id, (a.pieces_manquantes || []).join(", ")].filter(Boolean).join(" · ")));
    ligne.appendChild(principal);
    var niveau = a.niveau || a.severity || "warning";
    var grave = niveau === "critical" || niveau === "error" || niveau === "danger";
    ligne.appendChild(el("span", "status-pill status-pill--" + (grave ? "danger" : "warn"), niveau));
    var action = el("button", "btn ghost sm", "Traiter");
    action.type = "button";
    action.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ouvert(a.dossier_id);
    });
    ligne.appendChild(action);
    ligne.addEventListener("click", function () { ouvert(a.dossier_id); });
    return ligne;
  }

  function paginer(liste) {
    var pages = Math.max(1, Math.ceil(liste.length / vue.parPage));
    if (vue.page > pages) vue.page = pages;
    var debut = (vue.page - 1) * vue.parPage;
    return {
      elements: liste.slice(debut, debut + vue.parPage),
      pages: pages,
      debut: liste.length ? debut + 1 : 0,
      total: liste.length
    };
  }

  function rendrePagination(conteneur, info) {
    if (info.pages <= 1) return;
    var barre = el("div", "ws-pager");
    var precedent = el("button", "btn ghost sm", "Précédent");
    precedent.type = "button";
    precedent.disabled = vue.page === 1;
    precedent.addEventListener("click", function () {
      vue.page = Math.max(1, vue.page - 1);
      rendre(vue.onglet);
    });
    var suivant = el("button", "btn ghost sm", "Suivant");
    suivant.type = "button";
    suivant.disabled = vue.page === info.pages;
    suivant.addEventListener("click", function () {
      vue.page = Math.min(info.pages, vue.page + 1);
      rendre(vue.onglet);
    });
    barre.appendChild(precedent);
    barre.appendChild(el("span", "ws-pager__info", "Page " + vue.page + " / " + info.pages));
    barre.appendChild(suivant);
    conteneur.appendChild(barre);
  }

  function majCompteur(info) {
    var compteur = $("workspace-count");
    if (!compteur) return;
    compteur.textContent = info.total
      ? info.debut + "–" + Math.min(info.debut + vue.parPage - 1, info.total) + " sur " + info.total
      : "";
  }

  function rendre(onglet) {
    var cible = $("workspace-" + onglet + "-content");
    if (!cible) return;
    cible.textContent = "";

    if (onglet === "alertes") {
      if (!cache.alertes) {
        cible.appendChild(el("p", "ws-list__vide", "Chargement des alertes…"));
        return;
      }
      var alertes = (cache.alertes.alertes || []).filter(function (a) {
        if (!vue.recherche) return true;
        var terme = vue.recherche.trim().toLowerCase();
        return [a.titre, a.message, a.type, a.dossier_id].some(function (v) {
          return v && String(v).toLowerCase().indexOf(terme) !== -1;
        });
      });
      majCompteur({ total: alertes.length, debut: alertes.length ? 1 : 0 });
      if (!alertes.length) {
        cible.appendChild(el("p", "ws-list__vide", "Aucune alerte active. Tout est en ordre."));
        return;
      }
      var listeA = el("div", "ws-list");
      alertes.slice(0, 50).forEach(function (a) { listeA.appendChild(ligneAlerte(a)); });
      cible.appendChild(listeA);
      return;
    }

    if (!cache.dossiers) {
      cible.appendChild(el("p", "ws-list__vide", "Chargement des dossiers…"));
      return;
    }

    var liste = trier(filtrer(source(onglet)));
    var info = paginer(liste);
    majCompteur(info);

    if (!info.elements.length) {
      var message = (cache.dossiers || []).length
        ? "Aucun dossier ne correspond à ces filtres."
        : "Aucun dossier enregistré pour le moment.";
      cible.appendChild(el("p", "ws-list__vide", message));
      return;
    }

    var listeEl = el("div", "ws-list");
    info.elements.forEach(function (d) { listeEl.appendChild(ligneDossier(d)); });
    cible.appendChild(listeEl);
    rendrePagination(cible, info);
  }

  /* ── Onglets ──────────────────────────────────────────────────────── */

  function activer(onglet) {
    var cle = ONGLETS[onglet] || "taches";
    vue.onglet = cle;
    vue.page = 1;

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
    construireBarre();
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

  window.EspaceTravail = { activer: activer, charger: charger, vue: vue };
})();
