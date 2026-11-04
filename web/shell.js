/**
 * UniOCR — coque applicative (barre latérale, barre supérieure, recherche)
 * ---------------------------------------------------------------------------
 * Ce module ne contient aucune règle métier : il lit les endpoints réels
 * (`/api/ui/bootstrap`, `/api/search/global`, `/api/dashboard/alertes`) et
 * pilote l'interface. Toute donnée affichée vient du serveur ; quand une
 * source est vide, l'interface le dit au lieu de fabriquer une valeur.
 */
(function () {
  "use strict";

  var ETAT = {
    bootstrap: null,
    alertes: [],
    rechercheEnCours: 0,
    menus: {}
  };

  var ICONES = {
    dossier: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    client: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3.4"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
    bl: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
    conteneur: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 8h11v9H3z"/><path d="M14 11h4l3 3v3h-7z"/></svg>',
    document: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>'
  };

  var GROUPES = {
    dossiers: "Dossiers",
    clients: "Clients",
    connaissements: "Connaissements B/L",
    conteneurs: "Conteneurs",
    documents: "Documents OCR"
  };

  function $(id) { return document.getElementById(id); }

  function apiBase() {
    return (typeof window.__apiBase === "string" ? window.__apiBase : "");
  }

  function entetes() {
    var jeton = "";
    try { jeton = sessionStorage.getItem("uniocr_token") || ""; } catch (e) { jeton = ""; }
    var h = { Accept: "application/json" };
    if (jeton) h.Authorization = "Bearer " + jeton;
    return h;
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

  function reduit() {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }

  function toast(message, type) {
    if (typeof window.toast === "function") window.toast(message, type || "info");
  }

  /* ── État replié de la barre latérale ─────────────────────────────── */
  function appliquerRepli(replie) {
    var app = $("app");
    if (!app) return;
    app.classList.toggle("collapsed", !!replie);
    app.classList.toggle("is-nav-collapsed", !!replie);
    var bouton = $("sidebarCollapse");
    if (bouton) {
      bouton.setAttribute("aria-label", replie ? "Déployer la barre latérale" : "Réduire la barre latérale");
      var libelle = bouton.querySelector(".foot-label");
      if (libelle) libelle.textContent = replie ? "Déployer" : "Réduire";
    }
    try { localStorage.setItem("unocr_sidebar", replie ? "1" : "0"); } catch (e) { /* stockage indisponible */ }
  }

  function initRepli() {
    var memorise = "0";
    try { memorise = localStorage.getItem("unocr_sidebar") || "0"; } catch (e) { memorise = "0"; }
    appliquerRepli(memorise === "1");

    var bouton = $("sidebarCollapse");
    if (bouton) {
      bouton.addEventListener("click", function () {
        var app = $("app");
        appliquerRepli(!(app && app.classList.contains("collapsed")));
      });
    }

    var burger = $("navBurger");
    if (burger) {
      burger.addEventListener("click", function () {
        var app = $("app");
        if (!app) return;
        app.classList.toggle("nav-open");
        burger.setAttribute("aria-expanded", app.classList.contains("nav-open") ? "true" : "false");
      });
    }

    document.addEventListener("click", function (ev) {
      var app = $("app");
      if (!app || !app.classList.contains("nav-open")) return;
      if (ev.target.closest && (ev.target.closest(".sidebar") || ev.target.closest("#navBurger"))) return;
      app.classList.remove("nav-open");
    });
  }

  /* ── Menus de la barre supérieure ─────────────────────────────────── */
  function fermerMenus(sauf) {
    ["notifMenu", "helpMenu", "profileMenu"].forEach(function (id) {
      if (sauf === id) return;
      var menu = $(id);
      if (menu) menu.classList.add("hidden");
      var bouton = { notifMenu: "notifBtn", helpMenu: "helpBtn", profileMenu: "profileBtn" }[id];
      var declencheur = bouton ? $(bouton) : null;
      if (declencheur) declencheur.setAttribute("aria-expanded", "false");
    });
  }

  function basculerMenu(id) {
    var menu = $(id);
    if (!menu) return;
    var ouvert = !menu.classList.contains("hidden");
    fermerMenus(null);
    if (ouvert) return;
    menu.classList.remove("hidden");
    var declencheur = { notifMenu: "notifBtn", helpMenu: "helpBtn", profileMenu: "profileBtn" }[id];
    var bouton = declencheur ? $(declencheur) : null;
    if (bouton) bouton.setAttribute("aria-expanded", "true");
  }

  function initMenus() {
    var map = { notifBtn: "notifMenu", helpBtn: "helpMenu", profileBtn: "profileMenu" };
    Object.keys(map).forEach(function (idBouton) {
      var bouton = $(idBouton);
      if (!bouton) return;
      bouton.addEventListener("click", function (ev) {
        ev.stopPropagation();
        basculerMenu(map[idBouton]);
      });
    });

    document.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest(".menu")) return;
      if (ev.target.closest && ev.target.closest(".icon-btn, .profile-btn")) return;
      fermerMenus(null);
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        fermerMenus(null);
        fermerRecherche();
      }
    });
  }

  /* ── Aide ─────────────────────────────────────────────────────────── */
  function construireAide() {
    var menu = $("helpMenu");
    if (!menu) return;
    menu.textContent = "";
    var tete = elt("div", "menu-head", "Centre d'aide");
    menu.appendChild(tete);
    var liste = elt("div", "menu-list");

    var liens = [
      { titre: "Documentation de l'API", meta: "/docs — contrat OpenAPI", href: "/docs", externe: true },
      { titre: "Aide intégrée", meta: "Raccourcis clavier et navigation", overlay: true },
      { titre: "Journal d'audit", meta: "Traçabilité des actions", route: "admin/journal" },
      { titre: "Recherche globale", meta: "Ctrl K · dossiers, clients, B/L, conteneurs", info: true }
    ];

    liens.forEach(function (lien) {
      var item;
      if (lien.href) {
        item = elt("a", "menu-item");
        item.href = lien.href;
        if (lien.externe) { item.target = "_blank"; item.rel = "noopener noreferrer"; }
      } else {
        item = elt("button", "menu-item");
        item.type = "button";
        if (lien.route) {
          item.addEventListener("click", function () {
            window.location.hash = "#" + lien.route;
            fermerMenus(null);
          });
        }
        if (lien.info) {
          item.addEventListener("click", function () {
            toast("Ctrl K : recherche globale · / : recherche · Échap : fermer les menus", "info");
          });
        }
        if (lien.overlay) {
          item.addEventListener("click", function () {
            var overlay = $("helpOverlay");
            if (overlay) overlay.classList.remove("hidden");
            fermerMenus(null);
          });
        }
      }
      var texte = elt("span");
      texte.appendChild(elt("span", "mi-title", lien.titre));
      texte.appendChild(document.createElement("br"));
      texte.appendChild(elt("span", "mi-meta", lien.meta));
      item.appendChild(texte);
      liste.appendChild(item);
    });

    menu.appendChild(liste);
  }

  /* ── Profil ───────────────────────────────────────────────────────── */
  function construireProfil() {
    var menu = $("profileMenu");
    if (!menu) return;
    menu.textContent = "";
    menu.appendChild(elt("div", "menu-head", "Mon profil"));

    var utilisateur = ETAT.bootstrap && ETAT.bootstrap.utilisateur;
    var liste = elt("div", "menu-list");

    var identite = elt("div", "menu-item");
    var bloc = elt("span");
    bloc.appendChild(elt("span", "mi-title", utilisateur ? utilisateur.nom : "Poste local"));
    bloc.appendChild(document.createElement("br"));
    var roles = utilisateur && utilisateur.roles ? utilisateur.roles.join(", ") : "RBAC inactif — accès complet";
    bloc.appendChild(elt("span", "mi-meta", roles));
    identite.appendChild(bloc);
    liste.appendChild(identite);

    var actions = [
      { titre: "Mon espace de travail", route: "workspace/taches" },
      { titre: "Mes alertes", route: "workspace/alertes" },
      { titre: "Paramètres généraux", route: "referentiels/parametres" },
      { titre: "Administration & sécurité", route: "admin/utilisateurs" }
    ];
    actions.forEach(function (action) {
      var bouton = elt("button", "menu-item");
      bouton.type = "button";
      bouton.appendChild(elt("span", "mi-title", action.titre));
      bouton.addEventListener("click", function () {
        window.location.hash = "#" + action.route;
        fermerMenus(null);
      });
      liste.appendChild(bouton);
    });

    var sortie = elt("button", "menu-item");
    sortie.type = "button";
    sortie.appendChild(elt("span", "mi-title", "Verrouiller la session"));
    sortie.addEventListener("click", function () {
      try { sessionStorage.removeItem("uniocr_token"); } catch (e) { /* ignore */ }
      window.location.reload();
    });
    liste.appendChild(sortie);

    menu.appendChild(liste);
  }

  /* ── Notifications (alertes réelles) ──────────────────────────────── */
  function niveauClasse(niveau) {
    if (niveau === "critical" || niveau === "error") return "row-ic--danger";
    if (niveau === "warning") return "row-ic--warn";
    return "";
  }

  function niveauPastille(niveau) {
    if (niveau === "critical" || niveau === "error") return "badge--danger";
    if (niveau === "warning") return "badge--warn";
    return "badge--info";
  }

  function construireNotifications() {
    var menu = $("notifMenu");
    if (!menu) return;
    menu.textContent = "";
    var tete = elt("div", "menu-head");
    tete.appendChild(elt("span", null, "Notifications"));
    tete.appendChild(elt("span", "badge badge--neutral", ETAT.alertes.length + " alerte(s)"));
    menu.appendChild(tete);

    var liste = elt("div", "menu-list");
    if (!ETAT.alertes.length) {
      liste.appendChild(elt("div", "menu-empty", "Aucune alerte active. Tout est à jour."));
    } else {
      ETAT.alertes.slice(0, 12).forEach(function (alerte) {
        var bouton = elt("button", "menu-item");
        bouton.type = "button";
        var texte = elt("span");
        var titre = elt("span", "mi-title", alerte.titre || alerte.type);
        var meta = elt("span", "mi-meta",
          (alerte.message || "") + (alerte.dossier_id ? " · " + alerte.dossier_id : ""));
        texte.appendChild(titre);
        texte.appendChild(document.createElement("br"));
        texte.appendChild(meta);
        bouton.appendChild(texte);
        bouton.addEventListener("click", function () {
          fermerMenus(null);
          ouvrirDossier(alerte.dossier_id);
        });
        liste.appendChild(bouton);
      });
    }
    menu.appendChild(liste);

    var badge = $("notifBadge");
    if (badge) {
      if (!ETAT.alertes.length) {
        badge.classList.add("hidden");
      } else {
        badge.classList.remove("hidden");
        badge.textContent = ETAT.alertes.length > 99 ? "99+" : String(ETAT.alertes.length);
      }
    }
    var boutonNotif = $("notifBtn");
    if (boutonNotif) {
      boutonNotif.setAttribute("aria-label",
        ETAT.alertes.length ? ETAT.alertes.length + " alertes actives" : "Aucune alerte");
    }
  }

  function chargerAlertes() {
    return api("/api/dashboard/alertes").then(function (donnees) {
      ETAT.alertes = (donnees && donnees.alertes) || [];
      construireNotifications();
      return ETAT.alertes;
    }).catch(function () {
      ETAT.alertes = [];
      construireNotifications();
      return [];
    });
  }

  /* ── Amorçage : identité, compteurs, badges ───────────────────────── */
  function appliquerBootstrap(donnees) {
    ETAT.bootstrap = donnees || null;
    var utilisateur = donnees && donnees.utilisateur;
    var nom = utilisateur ? utilisateur.nom : "Poste local";
    var roles = utilisateur && utilisateur.roles && utilisateur.roles.length
      ? utilisateur.roles.join(", ")
      : "Accès complet (RBAC inactif)";

    var nomEl = $("profileName");
    if (nomEl) nomEl.textContent = nom;
    var roleEl = $("profileRole");
    if (roleEl) roleEl.textContent = roles;
    var avatar = $("profileAvatar");
    if (avatar) avatar.textContent = (nom || "U").trim().charAt(0).toUpperCase();

    var rbac = $("hero-rbac");
    if (rbac) {
      rbac.textContent = donnees && donnees.rbac_actif ? "RBAC actif" : "RBAC inactif";
      rbac.className = "badge " + (donnees && donnees.rbac_actif ? "badge--ok" : "badge--neutral");
    }
    var utilisateurHero = $("cockpit-user");
    if (utilisateurHero) utilisateurHero.textContent = nom;

    appliquerBadgesNavigation(donnees && donnees.compteurs ? donnees.compteurs : {});
    construireProfil();
  }

  function appliquerBadgesNavigation(compteurs) {
    var cibles = {
      "workspace/valider": compteurs.dossiers_a_valider,
      "workspace/alertes": ETAT.alertes.length,
      "dossiers/en-cours": compteurs.dossiers_en_cours,
      "dossiers/bloques": compteurs.dossiers_bloques,
      "controle/anomalies": ETAT.alertes.length,
      "documents/verification": compteurs.dossiers_a_valider
    };
    Object.keys(cibles).forEach(function (route) {
      var lien = document.querySelector('.nav-subitem[href="#' + route + '"]');
      if (!lien) return;
      var valeur = Number(cibles[route] || 0);
      var badge = lien.querySelector(".nav-badge");
      if (!valeur) {
        if (badge) badge.remove();
        return;
      }
      if (!badge) {
        badge = elt("span", "nav-badge");
        lien.appendChild(badge);
      }
      badge.textContent = valeur > 999 ? "999+" : String(valeur);
    });
  }

  function chargerAmorcage() {
    return api("/api/ui/bootstrap").then(function (donnees) {
      appliquerBootstrap(donnees);
      return donnees;
    }).catch(function () {
      appliquerBootstrap(null);
      return null;
    });
  }

  /* ── Navigation vers un dossier précis ────────────────────────────── */
  function ouvrirDossier(dossierId) {
    if (!dossierId) return;
    window.location.hash = "#dossiers/tous";
    var essais = 0;
    function tenter() {
      if (window.Dossiers && typeof window.Dossiers.ouvrir === "function") {
        window.Dossiers.ouvrir(dossierId);
        return;
      }
      essais += 1;
      if (essais < 12) setTimeout(tenter, 120);
    }
    setTimeout(tenter, 60);
  }

  /* ── Recherche globale ────────────────────────────────────────────── */
  var recherche = { timer: null, hits: [], index: -1 };

  function fermerRecherche() {
    var resultats = $("searchResults");
    var champ = $("globalSearch");
    if (resultats) resultats.classList.add("hidden");
    if (champ) champ.setAttribute("aria-expanded", "false");
    recherche.index = -1;
  }

  function naviguerVers(hit) {
    fermerRecherche();
    if (!hit) return;
    if (hit.kind === "dossier") {
      ouvrirDossier(hit.id);
      return;
    }
    if (hit.kind === "document" && window.openJob) {
      window.location.hash = "#documents/ocr";
      setTimeout(function () { window.openJob(hit.id); }, 80);
      return;
    }
    window.location.hash = "#" + (hit.route || "cockpit");
  }

  function rendreRecherche(donnees, requete) {
    var resultats = $("searchResults");
    if (!resultats) return;
    resultats.textContent = "";
    resultats.classList.remove("hidden");
    var champ = $("globalSearch");
    if (champ) champ.setAttribute("aria-expanded", "true");

    recherche.hits = [];
    var groupes = (donnees && donnees.groupes) || {};
    var total = 0;

    Object.keys(GROUPES).forEach(function (cle) {
      var hits = groupes[cle] || [];
      if (!hits.length) return;
      total += hits.length;
      var section = elt("div", "search-group");
      section.appendChild(elt("div", "search-group-title", GROUPES[cle] + " · " + hits.length));
      hits.forEach(function (hit) {
        recherche.hits.push(hit);
        var bouton = elt("button", "search-hit");
        bouton.type = "button";
        bouton.setAttribute("role", "option");
        var ic = elt("span", "hit-ic");
        ic.innerHTML = ICONES[hit.kind] || ICONES.document;
        bouton.appendChild(ic);
        var texte = elt("span");
        texte.appendChild(elt("span", "hit-title", hit.label || hit.id));
        texte.appendChild(document.createElement("br"));
        var meta = hit.meta ? hit.meta : "";
        if (hit.reference && hit.reference !== hit.label) meta = hit.reference + (meta ? " · " + meta : "");
        texte.appendChild(elt("span", "hit-meta", meta || hit.id));
        bouton.appendChild(texte);
        bouton.addEventListener("click", function () { naviguerVers(hit); });
        section.appendChild(bouton);
      });
      resultats.appendChild(section);
    });

    if (!total) {
      resultats.appendChild(elt("div", "search-empty",
        "Aucun résultat pour « " + requete + " ». Essayez une référence, un client ou un conteneur."));
    }
  }

  function lancerRecherche(requete) {
    var q = (requete || "").trim();
    if (q.length < 2) { fermerRecherche(); return; }
    var jeton = ++ETAT.rechercheEnCours;
    var resultats = $("searchResults");
    if (resultats) {
      resultats.classList.remove("hidden");
      resultats.textContent = "";
      resultats.appendChild(elt("div", "search-empty", "Recherche…"));
    }
    api("/api/search/global?q=" + encodeURIComponent(q) + "&limit=5")
      .then(function (donnees) {
        if (jeton !== ETAT.rechercheEnCours) return;
        rendreRecherche(donnees, q);
      })
      .catch(function () {
        if (jeton !== ETAT.rechercheEnCours) return;
        var zone = $("searchResults");
        if (zone) {
          zone.textContent = "";
          zone.appendChild(elt("div", "search-empty", "Recherche indisponible — API non jointe."));
        }
      });
  }

  function initRecherche() {
    var champ = $("globalSearch");
    if (!champ) return;
    champ.addEventListener("input", function () {
      clearTimeout(recherche.timer);
      recherche.timer = setTimeout(function () { lancerRecherche(champ.value); }, 220);
    });

    champ.addEventListener("keydown", function (ev) {
      var hits = document.querySelectorAll("#searchResults .search-hit");
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault();
        if (!hits.length) return;
        recherche.index += ev.key === "ArrowDown" ? 1 : -1;
        if (recherche.index < 0) recherche.index = hits.length - 1;
        if (recherche.index >= hits.length) recherche.index = 0;
        hits.forEach(function (h, i) { h.classList.toggle("is-active", i === recherche.index); });
        hits[recherche.index].scrollIntoView({ block: "nearest" });
      } else if (ev.key === "Enter") {
        ev.preventDefault();
        var actif = document.querySelector("#searchResults .search-hit.is-active") ||
          document.querySelector("#searchResults .search-hit");
        if (actif) actif.click();
      } else if (ev.key === "Escape") {
        champ.blur();
        fermerRecherche();
      }
    });

    document.addEventListener("click", function (ev) {
      if (ev.target.closest && ev.target.closest(".top-search")) return;
      fermerRecherche();
    });

    document.addEventListener("keydown", function (ev) {
      var ctrlK = (ev.ctrlKey || ev.metaKey) && (ev.key === "k" || ev.key === "K");
      if (ctrlK) {
        ev.preventDefault();
        champ.focus();
        champ.select();
      }
    });
  }

  /* ── Horloge et date du bandeau ───────────────────────────────────── */
  function initHorloge() {
    var heure = $("cockpit-clock");
    var date = $("cockpit-date");
    function rafraichir() {
      var maintenant = new Date();
      if (heure) {
        heure.textContent = maintenant.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      }
      if (date) {
        date.textContent = maintenant.toLocaleDateString("fr-FR", {
          weekday: "long", day: "2-digit", month: "long", year: "numeric"
        });
      }
    }
    rafraichir();
    setInterval(rafraichir, 30000);
  }

  /* ── Transitions de page ──────────────────────────────────────────── */
  function initTransitions() {
    var workspace = document.querySelector("main.workspace");
    if (!workspace) return;
    workspace.addEventListener("click", function (ev) {
      var lien = ev.target.closest ? ev.target.closest("[data-nav]") : null;
      if (!lien) return;
      if (reduit()) return;
      var page = document.querySelector("section.page:not(.hidden)");
      if (page) {
        page.style.opacity = "0";
        page.style.transform = "translateY(6px)";
        setTimeout(function () {
          page.style.opacity = "";
          page.style.transform = "";
        }, 120);
      }
    });
  }

  /* ── Synchronisation périodique des alertes ───────────────────────── */
  function initRafraichissement() {
    setInterval(function () {
      if (document.hidden) return;
      chargerAlertes().then(function (alertes) {
        var compteurs = (ETAT.bootstrap && ETAT.bootstrap.compteurs) || {};
        compteurs.alertes = alertes.length;
        appliquerBadgesNavigation(compteurs);
      });
    }, 120000);
  }

  function demarrer() {
    initRepli();
    initMenus();
    construireAide();
    initRecherche();
    initHorloge();
    initTransitions();
    chargerAlertes().then(chargerAmorcage).then(function () { construireProfil(); });
    initRafraichissement();

    window.addEventListener("uniocr:refresh", function () {
      chargerAlertes().then(chargerAmorcage);
    });
  }

  window.UniOCRShell = {
    demarrer: demarrer,
    rafraichir: function () { return chargerAlertes().then(chargerAmorcage); },
    ouvrirDossier: ouvrirDossier,
    etat: ETAT
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
