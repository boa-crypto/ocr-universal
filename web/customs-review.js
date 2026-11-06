/* Revue de quarantaine : GET uniquement, mêmes services et jeton que la coque.
 * Aucune donnée documentaire en stockage navigateur ; aucun HTML de document.
 */
(function () {
  "use strict";
  var ROUTE = "#admin/revue-douaniere", BASE = "/api/v1/customs-review";
  var generation = 0;
  function token() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }
  function element(tag, texte, classe) {
    var node = document.createElement(tag);
    if (texte !== undefined) node.textContent = texte;
    if (classe) node.className = classe;
    return node;
  }
  function ouvrir() {
    var host = document.getElementById("customs-review-host");
    if (!host) return;
    var tour = ++generation;
    host.replaceChildren();
    if (window.location.hash !== ROUTE) return;
    var courant = token();
    var statut = element("p", "", "sp-empty");
    statut.setAttribute("role", "status");
    statut.setAttribute("aria-live", "polite");
    var resultat = element("pre", "", "customs-review-result");
    resultat.setAttribute("dir", "auto");
    resultat.tabIndex = 0;
    var outils = element("div", undefined, "ecran__formulaire");
    var recharger = bouton("Actualiser les lots", ouvrir);
    host.append(recharger, statut, outils, resultat);
    function actuel() { return tour === generation && window.location.hash === ROUTE; }
    function effacer() { outils.replaceChildren(); resultat.textContent = ""; }
    function bouton(texte, action) {
      var b = element("button", texte, "btn ghost sm");
      b.type = "button";
      b.addEventListener("click", action);
      return b;
    }
    var erreurs = {
      401: "Authentification requise ou jeton expiré. Utilisez votre compte personnel UniOCR.",
      403: "Accès refusé : administrateur nominatif et habilitation de revue requis.",
      404: "Lot non inscrit dans le registre courant. Actualisez les lots.",
      409: "Lot incohérent ou empreinte modifiée. Aucune exploitation autorisée.",
      422: "Paramètres invalides ou types de lots incompatibles.",
      503: "Registre de revue absent ou invalide. Configuration serveur requise."
    };
    var requete = 0;
    async function lire(chemin, recevoir) {
      var numero = ++requete;
      resultat.textContent = "";
      statut.textContent = "Chargement…";
      try {
        if (courant !== token()) { effacer(); throw new Error("Compte modifié : actualisez les lots."); }
        var headers = {Accept: "application/json"};
        if (courant) headers.Authorization = "Bearer " + courant;
        var r = await fetch(BASE + chemin, {method: "GET", headers: headers,
          credentials: "same-origin", cache: "no-store"});
        if (!r.ok) {
          var erreur = new Error(erreurs[r.status] || "Service de revue indisponible.");
          erreur.acces = r.status === 401 || r.status === 403 || r.status === 503;
          throw erreur;
        }
        var donnees = await r.json();
        if (!actuel() || numero !== requete) return;
        if (courant !== token()) { effacer(); throw new Error("Compte modifié : actualisez les lots."); }
        if (donnees.lecture_seule !== true || donnees.publication_active !== false ||
            donnees.validation_juridique !== "non_validee" ||
            donnees.perimetre !== "revue_administrative_quarantaine" || !donnees.resultat) {
          throw new Error("Réponse de revue inattendue, non affichée.");
        }
        recevoir(donnees.resultat);
      } catch (e) {
        if (!actuel() || numero !== requete) return;
        if (e.acces) effacer();
        statut.textContent = e instanceof SyntaxError ? "Réponse illisible, non affichée." :
          (e.message && !/fetch|network/i.test(e.message) ? e.message : "Service de revue inaccessible.");
      }
    }
    function champ(parent, nom, tag, type) {
      var label = element("label", nom, "ecran__label");
      var input = element(tag || "input");
      if (type) input.type = type;
      label.append(input); parent.append(label);
      return input;
    }
    function afficher(rep) {
      resultat.textContent = JSON.stringify(rep, null, 2);
      statut.textContent = "Résultat technique — non validé juridiquement, non publié.";
    }
    lire("/lots", function (rep) {
      if (!Array.isArray(rep.lots)) throw new Error("Liste de lots illisible.");
      if (!rep.lots.length) {
        statut.textContent = "Aucun lot inscrit dans ce registre. Cela ne prouve pas un corpus vide ou complet.";
        return;
      }
      statut.textContent = rep.lots.length + " lot(s) inscrit(s). Intégrité non contrôlée par cette liste.";
      var liste = element("ul");
      rep.lots.forEach(function (lot) {
        if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(lot.id) ||
            !["code", "tarif"].includes(lot.type_lot) || !/^[a-f0-9]{64}$/.test(lot.manifest_sha256_attendu)) {
          effacer(); throw new Error("Entrée de registre inattendue.");
        }
        liste.append(element("li", lot.id + " · " + lot.type_lot + " · SHA256 attendu : " + lot.manifest_sha256_attendu));
      });
      outils.append(liste);
      var lot = champ(outils, "Lot à contrôler / rechercher", "select");
      var apres = champ(outils, "Lot après (comparaison de même type)", "select");
      rep.lots.forEach(function (item) {
        [lot, apres].forEach(function (select) {
          var option = element("option", item.id + " · " + item.type_lot);
          option.value = item.id; select.append(option);
        });
      });
      outils.append(bouton("Contrôler l’intégrité / rejouer", function () {
        lire("/lots/" + encodeURIComponent(lot.value) + "/check", afficher);
      }));
      outils.append(bouton("Comparer avant / après", function () {
        var a = rep.lots.find(function (v) { return v.id === lot.value; });
        var b = rep.lots.find(function (v) { return v.id === apres.value; });
        if (!a || !b || a.type_lot !== b.type_lot) {
          ++requete; resultat.textContent = "";
          statut.textContent = "Comparaison refusée : choisissez deux lots de même type."; return;
        }
        lire("/diff?" + new URLSearchParams({avant: lot.value, apres: apres.value}), afficher);
      }));
      var form = element("form");
      var q = champ(form, "Recherche FR / AR / code"); q.maxLength = 256; q.dir = "auto";
      var filtres = element("fieldset");
      filtres.append(element("legend", "Filtres Code documentaire seulement"));
      var article = champ(filtres, "Article"); article.maxLength = 256;
      var source = champ(filtres, "Source déclarée"); source.maxLength = 256;
      var nature = champ(filtres, "Nature", "select");
      ["", "originale", "modificative", "consolidee_provisoire"].forEach(function (v) {
        var option = element("option", v || "Toutes"); option.value = v; nature.append(option);
      });
      form.append(filtres);
      function adapter() {
        filtres.disabled = rep.lots.find(function (v) { return v.id === lot.value; }).type_lot !== "code";
        ++requete; resultat.textContent = "";
      }
      lot.addEventListener("change", adapter); adapter();
      var limit = champ(form, "Limite (1–100)", "input", "number");
      limit.min = 1; limit.max = 100; limit.value = 20; limit.required = true;
      var offset = champ(form, "Décalage (0–1000000)", "input", "number");
      offset.min = 0; offset.max = 1000000; offset.value = 0; offset.required = true;
      var chercher = element("button", "Rechercher", "btn primary sm"); chercher.type = "submit"; form.append(chercher);
      form.addEventListener("submit", function (event) {
        event.preventDefault(); if (!form.reportValidity()) return;
        var params = new URLSearchParams({q: q.value, limit: limit.value, offset: offset.value});
        if (!filtres.disabled) {
          [["article", article], ["source", source], ["nature", nature]].forEach(function (paire) {
            if (paire[1].value) params.set(paire[0], paire[1].value);
          });
        }
        lire("/lots/" + encodeURIComponent(lot.value) + "/search?" + params, afficher);
      });
      outils.append(form);
    });
  }
  function demarrer() {
    window.addEventListener("hashchange", ouvrir);
    window.addEventListener("pagehide", function () {
      ++generation;
      var host = document.getElementById("customs-review-host"); if (host) host.replaceChildren();
    });
    window.addEventListener("pageshow", function (event) { if (event.persisted) ouvrir(); });
    ouvrir();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
})();
