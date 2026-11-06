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
      outils.append(bouton("Diagnostiquer la couverture documentaire", function () {
        lire("/lots/" + encodeURIComponent(lot.value) + "/coverage", afficher);
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
        histoire.disabled = filtres.disabled;
        fiche.disabled = !filtres.disabled;
        ++requete; resultat.textContent = "";
      }
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
      var histoire = element("fieldset");
      histoire.append(element("legend", "Historique documentaire — Code seulement"));
      histoire.append(element("p", "Utilise le numéro d’article exact et les paginations ; texte recherché, source et nature ignorés. " +
        "Même numéro ne prouve pas une succession juridique. Aucune restitution à date."));
      var relationLimit = champ(histoire, "Relations par page (1–100)", "input", "number");
      relationLimit.min = 1; relationLimit.max = 100; relationLimit.value = 20; relationLimit.required = true;
      var relationOffset = champ(histoire, "Décalage relations (0–1000000)", "input", "number");
      relationOffset.min = 0; relationOffset.max = 1000000; relationOffset.value = 0; relationOffset.required = true;
      histoire.append(bouton("Afficher l’historique documentaire", function () {
        if (histoire.disabled || !form.reportValidity()) return;
        if (!article.value.trim()) {
          ++requete; resultat.textContent = "";
          statut.textContent = "Numéro d’article exact requis pour l’historique."; return;
        }
        var params = new URLSearchParams({article: article.value, limit: limit.value, offset: offset.value,
          relations_limit: relationLimit.value, relations_offset: relationOffset.value});
        lire("/lots/" + encodeURIComponent(lot.value) + "/history?" + params, afficher);
      }));
      form.append(histoire);
      var fiche = element("fieldset");
      fiche.append(element("legend", "Fiche tarifaire documentaire — tarif seulement"));
      fiche.append(element("p", "Code exact à dix chiffres ASCII. Parents et mesures déclarés, sans taux applicable ou calcul. " +
        "Aucune mesure ne signifie pas exonération."));
      var code10 = champ(fiche, "Code tarifaire exact (10 chiffres)");
      code10.inputMode = "numeric"; code10.maxLength = 10; code10.pattern = "[0-9]{10}";
      code10.setAttribute("data-code10", "");
      var measureLimit = champ(fiche, "Mesures par page (1–100)", "input", "number");
      measureLimit.min = 1; measureLimit.max = 100; measureLimit.value = 20; measureLimit.required = true;
      var measureOffset = champ(fiche, "Décalage mesures (0–1000000)", "input", "number");
      measureOffset.min = 0; measureOffset.max = 1000000; measureOffset.value = 0; measureOffset.required = true;
      fiche.append(bouton("Consulter la fiche tarifaire", function () {
        if (fiche.disabled) return;
        if (!/^[0-9]{10}$/.test(code10.value)) {
          ++requete; resultat.textContent = "";
          statut.textContent = "Code exact de dix chiffres ASCII requis, sans conversion."; return;
        }
        if (!measureLimit.reportValidity() || !measureOffset.reportValidity()) return;
        var params = new URLSearchParams({measures_limit: measureLimit.value, measures_offset: measureOffset.value});
        lire("/lots/" + encodeURIComponent(lot.value) + "/tariff/" + encodeURIComponent(code10.value) + "?" + params, afficher);
      }));
      lot.addEventListener("change", adapter); adapter();
      outils.append(form, fiche);
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
