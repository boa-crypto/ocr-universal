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
    var extrait = element("pre", "", "customs-review-result");
    extrait.setAttribute("dir", "auto"); extrait.setAttribute("data-article-fragment", "");
    extrait.tabIndex = 0; extrait.hidden = true;
    var actions = element("div"); actions.setAttribute("data-review-actions", "");
    actions.setAttribute("role", "group"); actions.setAttribute("aria-label", "Navigation documentaire des résultats");
    var rendreActions = function () {};
    var outils = element("div", undefined, "ecran__formulaire");
    var recharger = bouton("Actualiser les lots", ouvrir);
    host.append(recharger, statut, outils, actions, resultat, extrait);
    function viderResultat() { actions.replaceChildren(); resultat.textContent = ""; extrait.textContent = ""; extrait.hidden = true; }
    function actuel() { return tour === generation && window.location.hash === ROUTE; }
    function effacer() { outils.replaceChildren(); viderResultat(); }
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
      viderResultat();
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
      if (rep.type_rapport === "lecture_article_documentaire" && typeof rep.fragment === "string") {
        extrait.textContent = rep.fragment; extrait.hidden = false;
      }
      rendreActions(rep);
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
          ++requete; viderResultat();
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
        arbre.disabled = !filtres.disabled;
        lecture.disabled = filtres.disabled;
        ++requete; viderResultat();
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
          ++requete; viderResultat();
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
      function chargerFiche() {
        if (fiche.disabled) return;
        if (!/^[0-9]{10}$/.test(code10.value)) {
          ++requete; viderResultat();
          statut.textContent = "Code exact de dix chiffres ASCII requis, sans conversion."; return;
        }
        if (!measureLimit.reportValidity() || !measureOffset.reportValidity()) return;
        var params = new URLSearchParams({measures_limit: measureLimit.value, measures_offset: measureOffset.value});
        lire("/lots/" + encodeURIComponent(lot.value) + "/tariff/" + encodeURIComponent(code10.value) + "?" + params, afficher);
      }
      fiche.append(bouton("Consulter la fiche tarifaire", chargerFiche));
      var arbre = element("fieldset");
      arbre.append(element("legend", "Navigation hiérarchique — tarif seulement"));
      arbre.append(element("p", "Parcourir les enfants directs reçus. Copier l’ID/code parent exact depuis le rapport. " +
        "Ni nomenclature exhaustive ni subdivision nationale intermédiaire inventée."));
      var level = champ(arbre, "Niveau à consulter", "select"); level.setAttribute("data-tree-level", "");
      [["sections", "Sections / racine"], ["chapitres", "Chapitres (parent : section)"],
        ["positions", "Positions (parent : chapitre)"], ["sh6", "SH6 (parent : position)"],
        ["codes", "Codes dix chiffres (parent : SH6)"]].forEach(function (paire) {
        var option = element("option", paire[1]); option.value = paire[0]; level.append(option);
      });
      var treeParent = champ(arbre, "ID / code parent exact"); treeParent.maxLength = 256; treeParent.dir = "auto";
      treeParent.setAttribute("data-tree-parent", "");
      function adapterNiveau() {
        treeParent.disabled = level.value === "sections";
        ++requete; viderResultat();
      }
      level.addEventListener("change", adapterNiveau); adapterNiveau();
      var treeLimit = champ(arbre, "Enfants par page (1–100)", "input", "number");
      treeLimit.min = 1; treeLimit.max = 100; treeLimit.value = 20; treeLimit.required = true;
      var treeOffset = champ(arbre, "Décalage enfants (0–1000000)", "input", "number");
      treeOffset.min = 0; treeOffset.max = 1000000; treeOffset.value = 0; treeOffset.required = true;
      function chargerArbre() {
        if (arbre.disabled || !treeLimit.reportValidity() || !treeOffset.reportValidity()) return;
        if (level.value !== "sections" && !treeParent.value.trim()) {
          ++requete; viderResultat();
          statut.textContent = "ID ou code parent exact requis pour ce niveau."; return;
        }
        var params = new URLSearchParams({level: level.value, limit: treeLimit.value, offset: treeOffset.value});
        if (level.value !== "sections") params.set("parent", treeParent.value);
        lire("/lots/" + encodeURIComponent(lot.value) + "/tree?" + params, afficher);
      }
      arbre.append(bouton("Parcourir la hiérarchie tarifaire", chargerArbre));
      var lecture = element("fieldset");
      lecture.append(element("legend", "Lire une version d’article — Code seulement"));
      lecture.append(element("p", "ID exact de version issu de la recherche/histoire, pas numéro d’article. " +
        "Un champ de langue absent reste absent. Utiliser le décalage suivant retourné, sans compter en unités UTF-16."));
      var readId = champ(lecture, "Identifiant exact de version"); readId.maxLength = 256; readId.setAttribute("data-read-id", "");
      var readField = champ(lecture, "Champ transcrit", "select"); readField.setAttribute("data-read-field", "");
      ["texte_integral", "texte_francais", "texte_arabe", "texte_origine", "texte_modificatif"].forEach(function (v) {
        var option = element("option", v); option.value = v; readField.append(option);
      });
      var readLimit = champ(lecture, "Caractères par fragment (1–16000)", "input", "number");
      readLimit.min = 1; readLimit.max = 16000; readLimit.value = 4000; readLimit.required = true;
      var readOffset = champ(lecture, "Décalage du texte (0–67108864)", "input", "number");
      readOffset.min = 0; readOffset.max = 67108864; readOffset.value = 0; readOffset.required = true;
      function chargerArticle() {
        if (lecture.disabled || !readLimit.reportValidity() || !readOffset.reportValidity()) return;
        if (!readId.value.trim()) {
          ++requete; viderResultat(); statut.textContent = "Identifiant exact de version requis."; return;
        }
        var params = new URLSearchParams({article_id: readId.value, field: readField.value,
          limit: readLimit.value, offset: readOffset.value});
        lire("/lots/" + encodeURIComponent(lot.value) + "/article?" + params, afficher);
      }
      lecture.append(bouton("Lire le fragment d’article", chargerArticle));
      function idValide(id) {
        return typeof id === "string" && id.trim() && Array.from(id).length <= 256 && !/[\u0000-\u001f\u007f-\u009f]/.test(id);
      }
      function entier(v, min, max) { return Number.isInteger(v) && v >= min && v <= max; }
      function actionDocumentaire(titre, action) {
        var sequence = requete, selectionLot = lot.value;
        return bouton(titre, function () {
          if (!actuel() || sequence !== requete || selectionLot !== lot.value) return;
          if (courant !== token()) {
            ++requete; effacer(); statut.textContent = "Compte modifié : actualisez les lots."; return;
          }
          action();
        });
      }
      function proposerVersion(id) {
        if (!idValide(id) || lecture.disabled) return;
        actions.append(actionDocumentaire("Lire la version " + id, function () {
          readId.value = id; readField.value = "texte_integral"; readLimit.value = 4000; readOffset.value = 0;
          chargerArticle();
        }));
      }
      function proposerCode(code) {
        if (typeof code !== "string" || !/^[0-9]{10}$/.test(code) || fiche.disabled) return;
        actions.append(actionDocumentaire("Fiche documentaire " + code, function () {
          code10.value = code; measureLimit.value = 20; measureOffset.value = 0; chargerFiche();
        }));
      }
      rendreActions = function (rapport) {
        // Les boutons ne reprennent aucune URL source. Seuls des IDs/codes déclarés
        // alimentent les champs des lectures déjà protégées par le serveur.
        if (rapport.type_recherche === "code_documentaire" && Array.isArray(rapport.resultats)) {
          rapport.resultats.slice(0, 100).forEach(function (v) { if (v) proposerVersion(v.id); });
        }
        if (rapport.type_recherche === "tarif_documentaire" && Array.isArray(rapport.resultats)) {
          rapport.resultats.slice(0, 100).forEach(function (v) { if (v && v.ligne) proposerCode(v.ligne.code_tarifaire_10); });
        }
        if (rapport.type_rapport === "historique_documentaire_article") {
          var vus = new Set();
          [rapport.versions_meme_numero, rapport.articles_contexte_relations].forEach(function (liste) {
            if (!Array.isArray(liste)) return;
            liste.slice(0, 200).forEach(function (v) {
              if (v && !vus.has(v.id)) { vus.add(v.id); proposerVersion(v.id); }
            });
          });
        }
        if (rapport.type_rapport === "navigation_tarifaire_documentaire" && !arbre.disabled) {
          var suites = {sections: "chapitres", chapitres: "positions", positions: "sh6", sh6: "codes", codes: null};
          if (Object.prototype.hasOwnProperty.call(suites, rapport.niveau) && rapport.niveau_suivant === suites[rapport.niveau] &&
              Array.isArray(rapport.enfants_declares)) {
            rapport.enfants_declares.slice(0, 100).forEach(function (v) {
              if (!v) return;
              if (rapport.niveau === "codes") { proposerCode(v.code_tarifaire_10); return; }
              var id = rapport.niveau === "sections" ? v.id : v.code;
              var largeur = {chapitres: 2, positions: 4, sh6: 6}[rapport.niveau];
              if (!idValide(id) || (largeur && !new RegExp("^[0-9]{" + largeur + "}$").test(id))) return;
              actions.append(actionDocumentaire("Enfants de " + id, function () {
                level.value = rapport.niveau_suivant; treeParent.value = id; adapterNiveau();
                treeLimit.value = 20; treeOffset.value = 0; chargerArbre();
              }));
            });
          }
          if (Object.prototype.hasOwnProperty.call(suites, rapport.niveau) &&
              (rapport.niveau === "sections" ? rapport.parent_exact === null : idValide(rapport.parent_exact)) &&
              entier(rapport.limite, 1, 100) && entier(rapport.decalage, 0, 1000000) &&
              entier(rapport.decalage_suivant, rapport.decalage + 1, 1000000) &&
              entier(rapport.total_enfants_declares, rapport.decalage_suivant + 1, Number.MAX_SAFE_INTEGER)) {
            actions.append(actionDocumentaire("Page suivante des enfants", function () {
              level.value = rapport.niveau; treeParent.value = rapport.parent_exact || ""; adapterNiveau();
              treeLimit.value = rapport.limite; treeOffset.value = rapport.decalage_suivant; chargerArbre();
            }));
          }
        }
        if (rapport.type_rapport === "lecture_article_documentaire" && !lecture.disabled &&
            rapport.article_trouve === true && rapport.texte_renseigne === true &&
            rapport.unite_decalage === "points_de_code_unicode_python" && idValide(rapport.article_id_exact) &&
            ["texte_integral", "texte_francais", "texte_arabe", "texte_origine", "texte_modificatif"].includes(rapport.champ_texte) &&
            entier(rapport.limite, 1, 16000) && entier(rapport.decalage, 0, 67108864) &&
            entier(rapport.decalage_suivant, rapport.decalage + 1, 67108864) &&
            entier(rapport.total_caracteres, rapport.decalage_suivant + 1, 67108864)) {
          actions.append(actionDocumentaire("Fragment suivant de l’article", function () {
            readId.value = rapport.article_id_exact; readField.value = rapport.champ_texte;
            readLimit.value = rapport.limite; readOffset.value = rapport.decalage_suivant; chargerArticle();
          }));
        }
      };
      lot.addEventListener("change", adapter); adapter();
      outils.append(form, fiche, arbre, lecture);
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
