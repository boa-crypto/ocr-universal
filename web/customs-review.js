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
      503: "Revue indisponible : registre ou journal d’audit. Intervention serveur requise."
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
        if (chemin !== "/lots") {
          actions.append(bouton("Exporter ce rapport JSON non validé", function () {
            if (!actuel() || numero !== requete) return;
            lire(chemin, function (rep) {
              afficher(rep);
              var contenu = JSON.stringify({schema_version: "1", type_export: "rapport_revue_documentaire_non_valide",
                lecture_seule: true, publication_active: false, validation_juridique: "non_validee",
                perimetre: "rapport_ou_page_uniquement_pas_corpus_complet", horodatage_client_non_certifie: new Date().toISOString(),
                requete_relative: BASE + chemin, resultat: rep}, null, 2);
              var blob = new Blob([contenu], {type: "application/json;charset=utf-8"});
              if (blob.size > 10 * 1024 * 1024) throw new Error("Rapport trop volumineux pour cet export (10 Mio maximum).");
              var url = URL.createObjectURL(blob);
              try {
                var lien = element("a"); lien.href = url; lien.download = "uniocr-revue-non-validee.json";
                host.append(lien); try { lien.click(); } finally { lien.remove(); }
              } finally { window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000); }
              statut.textContent = "Téléchargement demandé — rapport non validé, non publié, pas corpus complet.";
            });
          }));
        }
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
      if (["lecture_article_documentaire", "lecture_page_pdf_recu"].includes(rep.type_rapport) && typeof rep.fragment === "string") {
        extrait.textContent = rep.fragment; extrait.hidden = false;
      }
      rendreActions(rep);
      statut.textContent = rep.type_rapport === "lecture_page_pdf_recu" && rep.texte_natif_non_vide === false ?
        "Aucun texte natif sélectionnable : aucun OCR effectué. Cela ne prouve pas une page vide ou l’absence de droit." :
        "Résultat technique — non validé juridiquement, non publié.";
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
      apres.setAttribute("data-comparison-after-lot", "");
      apres.addEventListener("change", function () { ++requete; viderResultat(); });
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
        histoire.disabled = filtres.disabled; sourcesNature.disabled = filtres.disabled;
        fiche.disabled = !filtres.disabled; paireTarif.disabled = fiche.disabled; mesuresRecherche.disabled = fiche.disabled;
        arbre.disabled = !filtres.disabled;
        justificationLecture.disabled = filtres.disabled; relationsLecture.disabled = filtres.disabled; matchLecture.disabled = filtres.disabled; codeArbre.disabled = filtres.disabled; lecture.disabled = filtres.disabled; diffArticle.disabled = filtres.disabled; pdfLecture.disabled = filtres.disabled;
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
      measureLimit.setAttribute("data-measures-limit", "");
      measureLimit.min = 1; measureLimit.max = 100; measureLimit.value = 20; measureLimit.required = true;
      var measureOffset = champ(fiche, "Décalage mesures (0–1000000)", "input", "number");
      measureOffset.setAttribute("data-measures-offset", "");
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
        ["codes", "Codes dix chiffres projetés (parent : SH6)"],
        ["subdivisions", "Enfants directs (parent : SH6 / subdivision)"]].forEach(function (paire) {
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
      var codeArbre = element("fieldset");
      codeArbre.append(element("legend", "Navigation hiérarchique déclarée — Code seulement"));
      codeArbre.append(element("p", "Racine : documents séparés. Chemin JSON exact des couples niveau/identifiant ; aucun niveau manquant reconstitué."));
      var codeSource = champ(codeArbre, "ID source exact (vide à la racine)"); codeSource.maxLength = 256;
      codeSource.setAttribute("data-code-tree-source", "");
      var codePath = champ(codeArbre, "Chemin JSON déclaré"); codePath.value = "[]"; codePath.maxLength = 8192;
      codePath.setAttribute("data-code-tree-path", "");
      var codeTreeLimit = champ(codeArbre, "Enfants Code par page (1–100)", "input", "number");
      codeTreeLimit.min = 1; codeTreeLimit.max = 100; codeTreeLimit.value = 20; codeTreeLimit.required = true;
      var codeTreeOffset = champ(codeArbre, "Décalage enfants Code (0–1000000)", "input", "number");
      codeTreeOffset.min = 0; codeTreeOffset.max = 1000000; codeTreeOffset.value = 0; codeTreeOffset.required = true;
      var niveauxCode = ["texte_legislatif", "livre", "titre", "chapitre", "section", "sous_section", "article", "paragraphe", "alinea", "annexe"];
      function cheminCodeValide(v) {
        return Array.isArray(v) && v.length <= 10 && v.every(function (n, i) {
          return n && Object.keys(n).length === 2 && niveauxCode.includes(n.niveau) &&
            typeof n.identifiant === "string" && Array.from(n.identifiant).length <= 256 &&
            (i === 0 || niveauxCode.indexOf(n.niveau) > niveauxCode.indexOf(v[i - 1].niveau));
        });
      }
      function cleCheminCode(v) { return JSON.stringify(v.map(function (n) { return [n.niveau, n.identifiant]; })); }
      function chargerCodeArbre() {
        if (codeArbre.disabled || !codeTreeLimit.reportValidity() || !codeTreeOffset.reportValidity()) return;
        var chemin;
        try { chemin = JSON.parse(codePath.value); } catch (_) { chemin = null; }
        if (!cheminCodeValide(chemin) || (!codeSource.value && chemin.length) || (codeSource.value && !idValide(codeSource.value))) {
          ++requete; viderResultat(); statut.textContent = "Source et chemin JSON déclaré valides requis."; return;
        }
        var params = new URLSearchParams({path: codePath.value, limit: codeTreeLimit.value, offset: codeTreeOffset.value});
        if (codeSource.value) params.set("source_id", codeSource.value);
        lire("/lots/" + encodeURIComponent(lot.value) + "/code-tree?" + params, afficher);
      }
      codeArbre.append(bouton("Parcourir la hiérarchie du Code", chargerCodeArbre));
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
      readLimit.setAttribute("data-read-limit", "");
      readLimit.min = 1; readLimit.max = 16000; readLimit.value = 4000; readLimit.required = true;
      var readOffset = champ(lecture, "Décalage du texte (0–67108864)", "input", "number");
      readOffset.setAttribute("data-read-offset", "");
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
      var pdfLecture = element("fieldset");
      pdfLecture.append(element("legend", "Texte natif PDF reçu — Code seulement"));
      pdfLecture.append(element("p", "Page physique, pas numéro imprimé du JO. Sans OCR ni transcription vérifiée. Aucun PDF brut ou lien distant ouvert."));
      var pdfId = champ(pdfLecture, "ID exact du document PDF"); pdfId.maxLength = 256; pdfId.setAttribute("data-pdf-id", "");
      var pdfPage = champ(pdfLecture, "Page physique PDF (1–10000)", "input", "number");
      pdfPage.min = 1; pdfPage.max = 10000; pdfPage.value = 1; pdfPage.required = true; pdfPage.setAttribute("data-pdf-page", "");
      var pdfLimit = champ(pdfLecture, "Caractères du fragment PDF (1–16000)", "input", "number");
      pdfLimit.min = 1; pdfLimit.max = 16000; pdfLimit.value = 4000; pdfLimit.required = true; pdfLimit.setAttribute("data-pdf-limit", "");
      var pdfOffset = champ(pdfLecture, "Décalage du texte PDF (0–67108864)", "input", "number");
      pdfOffset.min = 0; pdfOffset.max = 67108864; pdfOffset.value = 0; pdfOffset.required = true; pdfOffset.setAttribute("data-pdf-offset", "");
      function chargerPDF() {
        if (pdfLecture.disabled) return;
        if (!idValide(pdfId.value) || !entier(Number(pdfPage.value), 1, 10000) ||
            !entier(Number(pdfLimit.value), 1, 16000) || !entier(Number(pdfOffset.value), 0, 67108864) ||
            !pdfPage.reportValidity() || !pdfLimit.reportValidity() || !pdfOffset.reportValidity()) {
          ++requete; viderResultat(); statut.textContent = "Document exact, page et plage PDF valides requis."; return;
        }
        lire("/lots/" + encodeURIComponent(lot.value) + "/pdf?" + new URLSearchParams({document_id: pdfId.value,
          page: pdfPage.value, limit: pdfLimit.value, offset: pdfOffset.value}), afficher);
      }
      pdfLecture.append(bouton("Lire le texte natif PDF", chargerPDF));
      var diffArticle = element("fieldset");
      diffArticle.append(element("legend", "Comparer deux versions transcrites — Code seulement"));
      diffArticle.append(element("p", "Ordre avant/après choisi, pas succession juridique. Champ/limite de lecture d’article utilisés. Aucun alignement par similarité."));
      var diffAvant = champ(diffArticle, "ID exact avant"); diffAvant.maxLength = 256; diffAvant.setAttribute("data-diff-before", "");
      var diffApres = champ(diffArticle, "ID exact après"); diffApres.maxLength = 256; diffApres.setAttribute("data-diff-after", "");
      var diffOffsetAvant = champ(diffArticle, "Décalage bloc avant", "input", "number");
      var diffOffsetApres = champ(diffArticle, "Décalage bloc après", "input", "number");
      [diffOffsetAvant, diffOffsetApres].forEach(function (v) { v.min = 0; v.max = 67108864; v.value = 0; v.required = true; });
      diffOffsetAvant.setAttribute("data-diff-offset-before", ""); diffOffsetApres.setAttribute("data-diff-offset-after", "");
      function chargerDiffArticle(interLots) {
        interLots = interLots === true;
        if (diffArticle.disabled) return;
        if (interLots && !rep.lots.some(function (v) { return v.id === apres.value && v.type_lot === "code"; })) {
          ++requete; viderResultat(); statut.textContent = "Deux lots Code explicitement choisis requis."; return;
        }
        if (!idValide(diffAvant.value) || !idValide(diffApres.value) || !readLimit.reportValidity() || !diffOffsetAvant.reportValidity() || !diffOffsetApres.reportValidity()) {
          ++requete; viderResultat(); statut.textContent = "Deux identifiants exacts et une limite valides requis."; return;
        }
        var paramDiff = new URLSearchParams({avant_id: diffAvant.value, apres_id: diffApres.value,
          field: readField.value, limit: readLimit.value, offset_avant: diffOffsetAvant.value, offset_apres: diffOffsetApres.value});
        if (interLots) { paramDiff.set("avant", lot.value); paramDiff.set("apres", apres.value); }
        lire(interLots ? "/article-diff?" + paramDiff : "/lots/" + encodeURIComponent(lot.value) + "/article-diff?" + paramDiff, afficher);
      }
      diffArticle.append(bouton("Comparer les deux versions exactes", chargerDiffArticle));
      diffArticle.append(element("p", "Pour comparer entre archives, choisir aussi le lot après en haut. IDs locaux à chaque lot ; aucune identité ou relation juridique déduite."));
      diffArticle.append(bouton("Comparer les versions entre deux lots Code", function () { chargerDiffArticle(true); }));
      var matchLecture = element("fieldset");
      matchLecture.append(element("legend", "Rapprochement littéral article / PDF — Code seulement"));
      matchLecture.append(element("p", "Utilise l’ID, le champ, la limite et le décalage du formulaire de lecture d’article. " +
        "Source PDF imposée par la référence de l’article. Présence ≠ validation ; absence ≠ erreur de transcription. Sans OCR."));
      var matchPage = champ(matchLecture, "Page physique source choisie (1–10000)", "input", "number");
      matchPage.min = 1; matchPage.max = 10000; matchPage.value = 1; matchPage.required = true;
      matchPage.setAttribute("data-match-page", "");
      function chargerRapprochement() {
        if (matchLecture.disabled) return;
        if (!idValide(readId.value) || !readLimit.reportValidity() || !readOffset.reportValidity() ||
            !entier(Number(matchPage.value), 1, 10000) || !matchPage.reportValidity()) {
          ++requete; viderResultat(); statut.textContent = "ID, fragment d’article et page physique source valides requis."; return;
        }
        lire("/lots/" + encodeURIComponent(lot.value) + "/article-pdf-match?" + new URLSearchParams({article_id: readId.value,
          field: readField.value, page: matchPage.value, limit: readLimit.value, offset: readOffset.value}), afficher);
      }
      matchLecture.append(bouton("Rapprocher le fragment avec sa page PDF", chargerRapprochement));
      var relationsLecture = element("fieldset");
      relationsLecture.append(element("legend", "Relations déclarées d’une version exacte — Code seulement"));
      relationsLecture.append(element("p", "Un seul saut, pas toutes les versions du même numéro. Sens et types déclarés, justification non vérifiée contre le PDF."));
      var relationsId = champ(relationsLecture, "ID exact de version à inspecter"); relationsId.maxLength = 256;
      relationsId.setAttribute("data-relations-id", "");
      var relationsSens = champ(relationsLecture, "Sens des liens", "select"); relationsSens.setAttribute("data-relations-direction", "");
      ["tous", "entrantes", "sortantes"].forEach(function (v) { var o = element("option", v); o.value = v; relationsSens.append(o); });
      var relationsType = champ(relationsLecture, "Type déclaré", "select"); relationsType.setAttribute("data-relations-type", "");
      var typesRelations = ["modifie", "complete", "abroge", "rectifie", "renvoie_a"];
      [""].concat(typesRelations).forEach(function (v) { var o = element("option", v || "Tous"); o.value = v; relationsType.append(o); });
      var relationsLimit = champ(relationsLecture, "Relations par page (1–100)", "input", "number");
      relationsLimit.min = 1; relationsLimit.max = 100; relationsLimit.value = 20; relationsLimit.required = true;
      var relationsOffset = champ(relationsLecture, "Décalage relations (0–1000000)", "input", "number");
      relationsOffset.min = 0; relationsOffset.max = 1000000; relationsOffset.value = 0; relationsOffset.required = true;
      function chargerRelations() {
        if (relationsLecture.disabled) return;
        if (!idValide(relationsId.value) || !relationsLimit.reportValidity() || !relationsOffset.reportValidity()) {
          ++requete; viderResultat(); statut.textContent = "ID exact et pagination des relations valides requis."; return;
        }
        var p = new URLSearchParams({article_id: relationsId.value, direction: relationsSens.value, limit: relationsLimit.value, offset: relationsOffset.value});
        if (relationsType.value) p.set("relation_type", relationsType.value);
        lire("/lots/" + encodeURIComponent(lot.value) + "/article-relations?" + p, afficher);
      }
      relationsLecture.append(bouton("Inspecter les relations déclarées", chargerRelations));
      var justificationLecture = element("fieldset");
      justificationLecture.append(element("legend", "Rapprochement littéral justification / PDF — Code seulement"));
      justificationLecture.append(element("p", "Justification déclarée, pas forcément citation. Source imposée par la relation ; page physique à choisir. Présence ≠ preuve juridique, absence ≠ erreur."));
      var justificationId = champ(justificationLecture, "ID exact de relation"); justificationId.maxLength = 256; justificationId.setAttribute("data-justification-id", "");
      var justificationPage = champ(justificationLecture, "Page physique explicitement choisie (1–10000)", "input", "number");
      justificationPage.min = 1; justificationPage.max = 10000; justificationPage.value = 1; justificationPage.required = true; justificationPage.setAttribute("data-justification-page", "");
      var justificationLimit = champ(justificationLecture, "Caractères de justification (1–16000)", "input", "number");
      justificationLimit.setAttribute("data-justification-limit", "");
      justificationLimit.min = 1; justificationLimit.max = 16000; justificationLimit.value = 4000; justificationLimit.required = true;
      var justificationOffset = champ(justificationLecture, "Décalage justification (0–67108864)", "input", "number");
      justificationOffset.setAttribute("data-justification-offset", "");
      justificationOffset.min = 0; justificationOffset.max = 67108864; justificationOffset.value = 0; justificationOffset.required = true;
      function chargerJustification() {
        if (justificationLecture.disabled) return;
        if (!idValide(justificationId.value) || !justificationPage.reportValidity() || !justificationLimit.reportValidity() || !justificationOffset.reportValidity()) {
          ++requete; viderResultat(); statut.textContent = "Relation exacte, page et fragment de justification valides requis."; return;
        }
        lire("/lots/" + encodeURIComponent(lot.value) + "/relation-pdf-match?" + new URLSearchParams({relation_id: justificationId.value,
          page: justificationPage.value, limit: justificationLimit.value, offset: justificationOffset.value}), afficher);
      }
      justificationLecture.append(bouton("Rapprocher la justification avec sa page PDF", chargerJustification));
      var paireTarif = element("fieldset");
      paireTarif.append(element("legend", "Deux fiches tarifaires séparées — tarif seulement"));
      paireTarif.append(element("p", "Utilise les lots avant/après en haut et le code exact de la fiche. Pagination avant = formulaire de fiche. Aucune fusion de taux, succession juridique ou fiscalité applicable déduite."));
      var paireLimit = champ(paireTarif, "Mesures après par page (1–100)", "input", "number");
      paireLimit.min = 1; paireLimit.max = 100; paireLimit.value = 20; paireLimit.required = true; paireLimit.setAttribute("data-pair-after-limit", "");
      var paireOffset = champ(paireTarif, "Décalage mesures après (0–1000000)", "input", "number");
      paireOffset.min = 0; paireOffset.max = 1000000; paireOffset.value = 0; paireOffset.required = true; paireOffset.setAttribute("data-pair-after-offset", "");
      function chargerPaireTarif() {
        if (paireTarif.disabled) return;
        if (!/^[0-9]{10}$/.test(code10.value) || !rep.lots.some(function (v) { return v.id === apres.value && v.type_lot === "tarif"; })) {
          ++requete; viderResultat(); statut.textContent = "Deux lots tarifaires et un code exact à dix chiffres ASCII requis."; return;
        }
        if (!measureLimit.reportValidity() || !measureOffset.reportValidity() || !paireLimit.reportValidity() || !paireOffset.reportValidity()) return;
        lire("/tariff-compare?" + new URLSearchParams({avant: lot.value, apres: apres.value, code10: code10.value,
          before_limit: measureLimit.value, before_offset: measureOffset.value, after_limit: paireLimit.value, after_offset: paireOffset.value}), afficher);
      }
      paireTarif.append(bouton("Consulter les deux fiches tarifaires séparées", chargerPaireTarif));
      var mesuresRecherche = element("fieldset");
      mesuresRecherche.append(element("legend", "Rechercher les descriptions de mesures — tarif seulement"));
      mesuresRecherche.append(element("p", "Descriptions déclarées uniquement, pas désignations ou taux. Sans synonymes/traduction/IA ni droit applicable. Requête ou filtre exact requis."));
      var mesuresQuery = champ(mesuresRecherche, "Texte FR / AR de description"); mesuresQuery.maxLength = 256; mesuresQuery.dir = "auto"; mesuresQuery.setAttribute("data-measure-query", "");
      var mesuresCode = champ(mesuresRecherche, "Code10 exact facultatif"); mesuresCode.maxLength = 10; mesuresCode.setAttribute("data-measure-code", "");
      var mesuresType = champ(mesuresRecherche, "Type déclaré facultatif", "select"); mesuresType.setAttribute("data-measure-type", "");
      ["", "droit", "tva", "autre_taxe", "restriction", "autorisation", "regime"].forEach(function (v) { var o = element("option", v || "Tous"); o.value = v; mesuresType.append(o); });
      var mesuresLimit = champ(mesuresRecherche, "Mesures trouvées par page (1–100)", "input", "number");
      mesuresLimit.min = 1; mesuresLimit.max = 100; mesuresLimit.value = 20; mesuresLimit.required = true;
      var mesuresOffset = champ(mesuresRecherche, "Décalage résultats mesures (0–1000000)", "input", "number");
      mesuresOffset.min = 0; mesuresOffset.max = 1000000; mesuresOffset.value = 0; mesuresOffset.required = true;
      function chargerRechercheMesures() {
        if (mesuresRecherche.disabled) return;
        if ((!mesuresQuery.value.trim() && !mesuresCode.value && !mesuresType.value) ||
            (mesuresCode.value && !/^[0-9]{10}$/.test(mesuresCode.value))) {
          ++requete; viderResultat(); statut.textContent = "Requête ou filtre exact requis ; code facultatif à dix chiffres ASCII."; return;
        }
        if (!mesuresLimit.reportValidity() || !mesuresOffset.reportValidity()) return;
        var p = new URLSearchParams({q: mesuresQuery.value, limit: mesuresLimit.value, offset: mesuresOffset.value});
        if (mesuresCode.value) p.set("code10", mesuresCode.value);
        if (mesuresType.value) p.set("measure_type", mesuresType.value);
        lire("/lots/" + encodeURIComponent(lot.value) + "/measure-search?" + p, afficher);
      }
      mesuresRecherche.append(bouton("Rechercher dans les mesures déclarées", chargerRechercheMesures));
      var sourcesLecture = element("fieldset");
      sourcesLecture.append(element("legend", "Inventaire des sources déclarées du lot"));
      sourcesLecture.append(element("p", "Métadonnées reçues seulement : titre, organisme, version. Aucun accès réseau, authenticité ou corpus exhaustif attesté. Requête vide = toutes les sources du lot."));
      var sourcesQuery = champ(sourcesLecture, "Recherche FR / AR des métadonnées"); sourcesQuery.maxLength = 256; sourcesQuery.dir = "auto"; sourcesQuery.setAttribute("data-sources-query", "");
      var sourcesId = champ(sourcesLecture, "ID source exact facultatif"); sourcesId.maxLength = 256; sourcesId.setAttribute("data-sources-id", "");
      var sourcesNature = champ(sourcesLecture, "Nature déclarée — Code seulement", "select"); sourcesNature.setAttribute("data-sources-nature", "");
      ["", "code_original", "acte_modificatif", "compilation"].forEach(function (v) { var o = element("option", v || "Toutes"); o.value = v; sourcesNature.append(o); });
      var sourcesLimit = champ(sourcesLecture, "Sources par page (1–100)", "input", "number"); sourcesLimit.min = 1; sourcesLimit.max = 100; sourcesLimit.value = 20; sourcesLimit.required = true;
      var sourcesOffset = champ(sourcesLecture, "Décalage sources (0–1000000)", "input", "number"); sourcesOffset.min = 0; sourcesOffset.max = 1000000; sourcesOffset.value = 0; sourcesOffset.required = true;
      function chargerSources() {
        if (!sourcesLimit.reportValidity() || !sourcesOffset.reportValidity()) return;
        if (sourcesId.value && !idValide(sourcesId.value)) { ++requete; viderResultat(); statut.textContent = "ID source exact invalide."; return; }
        var p = new URLSearchParams({q: sourcesQuery.value, limit: sourcesLimit.value, offset: sourcesOffset.value});
        if (sourcesId.value) p.set("source_id", sourcesId.value);
        if (!sourcesNature.disabled && sourcesNature.value) p.set("nature_document", sourcesNature.value);
        lire("/lots/" + encodeURIComponent(lot.value) + "/sources?" + p, afficher);
      }
      sourcesLecture.append(bouton("Inventorier les sources déclarées", chargerSources));
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
        if (rapport.type_recherche === "sources_documentaires" && rapport.type_lot === (filtres.disabled ? "tarif" : "code")) {
          var fs = rapport.filtres, naturesSources = ["code_original", "acte_modificatif", "compilation"];
          if (fs && (fs.source_id_exact === null || idValide(fs.source_id_exact)) &&
              (fs.nature_document === null || (rapport.type_lot === "code" && naturesSources.includes(fs.nature_document)))) {
            var sourcesVues = new Set();
            if (Array.isArray(rapport.resultats)) rapport.resultats.slice(0, 100).forEach(function (r) {
              var d = r && r.source_declaree;
              if (!d || !idValide(d.id) || typeof d.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(d.sha256) || sourcesVues.has(d.id) ||
                  (fs.source_id_exact !== null && fs.source_id_exact !== d.id) || rapport.type_lot !== "code" ||
                  !naturesSources.includes(d.nature_document) || (fs.nature_document !== null && fs.nature_document !== d.nature_document)) return;
              sourcesVues.add(d.id);
              actions.append(actionDocumentaire("Articles de la source " + d.id, function () {
                codeSource.value = d.id; codePath.value = "[]"; codeTreeLimit.value = 20; codeTreeOffset.value = 0; chargerCodeArbre();
              }));
              if (d.format === "pdf") actions.append(actionDocumentaire("Lire la source PDF " + d.id + " — page 1", function () {
                pdfId.value = d.id; pdfPage.value = 1; pdfLimit.value = 4000; pdfOffset.value = 0; chargerPDF();
              }));
            });
            if (typeof rapport.requete === "string" && Array.from(rapport.requete).length <= 256 &&
                entier(rapport.limite, 1, 100) && entier(rapport.decalage, 0, 1000000) &&
                entier(rapport.decalage_suivant, rapport.decalage + 1, 1000000) &&
                entier(rapport.total_correspondances, rapport.decalage_suivant + 1, Number.MAX_SAFE_INTEGER)) {
              actions.append(actionDocumentaire("Page suivante des sources déclarées", function () {
                sourcesQuery.value = rapport.requete; sourcesId.value = fs.source_id_exact || ""; sourcesNature.value = fs.nature_document || "";
                sourcesLimit.value = rapport.limite; sourcesOffset.value = rapport.decalage_suivant; chargerSources();
              }));
            }
          }
        }
        if (rapport.type_recherche === "mesures_tarifaires_documentaires" && !mesuresRecherche.disabled) {
          var codesMesures = new Set();
          if (Array.isArray(rapport.resultats)) rapport.resultats.slice(0, 100).forEach(function (r) {
            if (!r || !r.mesure_declaree || !r.ligne_declaree) return;
            var code = r.mesure_declaree.code_tarifaire_10;
            if (typeof code !== "string" || !/^[0-9]{10}$/.test(code) || r.ligne_declaree.code_tarifaire_10 !== code || codesMesures.has(code)) return;
            codesMesures.add(code); proposerCode(code);
          });
          var fm = rapport.filtres;
          if (fm && typeof rapport.requete === "string" && Array.from(rapport.requete).length <= 256 &&
              (fm.code10_exact === null || (typeof fm.code10_exact === "string" && /^[0-9]{10}$/.test(fm.code10_exact))) &&
              (fm.type_mesure === null || ["droit", "tva", "autre_taxe", "restriction", "autorisation", "regime"].includes(fm.type_mesure)) &&
              entier(rapport.limite, 1, 100) && entier(rapport.decalage, 0, 1000000) &&
              entier(rapport.decalage_suivant, rapport.decalage + 1, 1000000) &&
              entier(rapport.total_correspondances, rapport.decalage_suivant + 1, Number.MAX_SAFE_INTEGER)) {
            actions.append(actionDocumentaire("Page suivante des mesures trouvées", function () {
              mesuresQuery.value = rapport.requete; mesuresCode.value = fm.code10_exact || ""; mesuresType.value = fm.type_mesure || "";
              mesuresLimit.value = rapport.limite; mesuresOffset.value = rapport.decalage_suivant; chargerRechercheMesures();
            }));
          }
        }
        if (rapport.type_rapport === "juxtaposition_documentaire_fiches_tarifaires" && !paireTarif.disabled &&
            typeof rapport.code_tarifaire_10_exact === "string" && /^[0-9]{10}$/.test(rapport.code_tarifaire_10_exact) && rapport.lots_exacts && rapport.lots_exacts.avant === lot.value &&
            [rapport.lots_exacts.avant, rapport.lots_exacts.apres].every(function (id) {
              return rep.lots.some(function (v) { return v.id === id && v.type_lot === "tarif"; });
            }) && rapport.avant && rapport.apres) {
          ["avant", "apres"].forEach(function (cote) {
            var f = rapport[cote];
            if (f.ligne_trouvee === true && f.ligne_declaree && f.ligne_declaree.code_tarifaire_10 === rapport.code_tarifaire_10_exact) {
              actions.append(actionDocumentaire("Fiche " + cote + " du lot " + rapport.lots_exacts[cote], function () {
                lot.value = rapport.lots_exacts[cote]; adapter();
                code10.value = rapport.code_tarifaire_10_exact; measureLimit.value = 20; measureOffset.value = 0; chargerFiche();
              }));
            }
            if (!entier(f.limite_mesures, 1, 100) || !entier(f.decalage_mesures, 0, 1000000) ||
                !entier(f.decalage_mesures_suivant, f.decalage_mesures + 1, 1000000) ||
                !entier(f.total_mesures_declarees, f.decalage_mesures_suivant + 1, Number.MAX_SAFE_INTEGER)) return;
            var autre = rapport[cote === "avant" ? "apres" : "avant"];
            if (!entier(autre.limite_mesures, 1, 100) || !entier(autre.decalage_mesures, 0, 1000000)) return;
            actions.append(actionDocumentaire("Mesures suivantes côté " + cote, function () {
              code10.value = rapport.code_tarifaire_10_exact; apres.value = rapport.lots_exacts.apres;
              measureLimit.value = rapport.avant.limite_mesures; paireLimit.value = rapport.apres.limite_mesures;
              measureOffset.value = cote === "avant" ? f.decalage_mesures_suivant : rapport.avant.decalage_mesures;
              paireOffset.value = cote === "apres" ? f.decalage_mesures_suivant : rapport.apres.decalage_mesures;
              chargerPaireTarif();
            }));
          });
        }
        // Les boutons ne reprennent aucune URL source. Seuls des IDs/codes déclarés
        // alimentent les champs des lectures déjà protégées par le serveur.
        if (rapport.type_recherche === "code_documentaire" && Array.isArray(rapport.resultats)) {
          rapport.resultats.slice(0, 100).forEach(function (v) {
            if (!v) return;
            proposerVersion(v.id);
            if (!idValide(v.id) || lecture.disabled || !Array.isArray(v.extraits_correspondants) || !Array.isArray(rapport.termes_normalises)) return;
            var champsVus = new Set();
            v.extraits_correspondants.slice(0, 4).forEach(function (ex) {
              if (!ex || !["intitule", "texte_integral", "texte_francais", "texte_arabe"].includes(ex.champ_texte) || champsVus.has(ex.champ_texte) ||
                  ex.unite_decalage !== "points_de_code_unicode_python" || typeof ex.fragment !== "string" ||
                  !rapport.termes_normalises.includes(ex.terme_normalise) || typeof ex.terme_normalise !== "string" || !ex.terme_normalise ||
                  !entier(ex.decalage, 0, 67108864) || !entier(ex.total_caracteres, 1, 67108864)) return;
              var longueur = Array.from(ex.fragment).length;
              if (longueur < 1 || longueur > 384 || ex.decalage + longueur > ex.total_caracteres ||
                  !entier(ex.correspondance_debut, ex.decalage, ex.decalage + longueur - 1) ||
                  !entier(ex.correspondance_fin, ex.correspondance_debut + 1, ex.total_caracteres) ||
                  ex.correspondance_entierement_visible !== (ex.correspondance_fin <= ex.decalage + longueur)) return;
              champsVus.add(ex.champ_texte);
              var contexte = element("blockquote", ex.fragment); contexte.dir = "auto";
              actions.append(element("p", "Extrait non validé — " + v.id + " — " + ex.champ_texte), contexte);
              if (ex.champ_texte === "intitule") return;
              actions.append(actionDocumentaire("Lire le passage " + v.id + " — " + ex.champ_texte, function () {
                readId.value = v.id; readField.value = ex.champ_texte; readLimit.value = longueur; readOffset.value = ex.decalage; chargerArticle();
              }));
            });
          });
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
          var suites = {sections: "chapitres", chapitres: "positions", positions: "sh6", sh6: "codes", codes: null, subdivisions: "subdivisions"};
          if (Object.prototype.hasOwnProperty.call(suites, rapport.niveau) && rapport.niveau_suivant === suites[rapport.niveau] &&
              Array.isArray(rapport.enfants_declares)) {
            rapport.enfants_declares.slice(0, 100).forEach(function (v) {
              if (!v) return;
              if (rapport.niveau === "codes") { proposerCode(v.code_tarifaire_10); return; }
              if (rapport.niveau === "subdivisions") {
                var parentDirect = rapport.parent_exact;
                if (typeof parentDirect !== "string" || !/^[0-9]{6,9}$/.test(parentDirect)) return;
                if (v.type_noeud === "code10" && typeof v.code_tarifaire_10 === "string" && /^[0-9]{10}$/.test(v.code_tarifaire_10) &&
                    v.code_tarifaire_10.startsWith(parentDirect) && v.code_sh_6 === parentDirect.slice(0, 6) &&
                    ((parentDirect.length > 6 && v.code_subdivision_nationale === parentDirect) ||
                    (parentDirect.length === 6 && v.code_sh_6 === parentDirect && v.code_subdivision_nationale === null))) {
                  proposerCode(v.code_tarifaire_10); return;
                }
                if (v.type_noeud !== "subdivision_nationale" || typeof v.code !== "string" || !/^[0-9]{7,9}$/.test(v.code) ||
                    v.code_parent !== parentDirect || v.code.length <= parentDirect.length || !v.code.startsWith(parentDirect)) return;
                actions.append(actionDocumentaire("Enfants de " + v.code, function () {
                  level.value = "subdivisions"; treeParent.value = v.code; adapterNiveau();
                  treeLimit.value = 20; treeOffset.value = 0; chargerArbre();
                }));
                return;
              }
              var id = rapport.niveau === "sections" ? v.id : v.code;
              var largeur = {chapitres: 2, positions: 4, sh6: 6}[rapport.niveau];
              if (!idValide(id) || (largeur && !new RegExp("^[0-9]{" + largeur + "}$").test(id))) return;
              actions.append(actionDocumentaire("Enfants de " + id, function () {
                level.value = rapport.niveau === "sh6" && rapport.niveau_suivant_detaille === "subdivisions" ? "subdivisions" : rapport.niveau_suivant;
                treeParent.value = id; adapterNiveau();
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
        if (rapport.type_rapport === "navigation_code_documentaire" && !codeArbre.disabled &&
            cheminCodeValide(rapport.chemin_exact) && (rapport.source_id_exact === null ? rapport.chemin_exact.length === 0 : idValide(rapport.source_id_exact))) {
          var pathCode = rapport.chemin_exact, sourceCode = rapport.source_id_exact;
          function ouvrirCode(source, chemin, limite, decalage) {
            codeSource.value = source || ""; codePath.value = JSON.stringify(chemin);
            codeTreeLimit.value = limite; codeTreeOffset.value = decalage; chargerCodeArbre();
          }
          if (sourceCode !== null) actions.append(actionDocumentaire("Remonter la hiérarchie du Code", function () {
            ouvrirCode(pathCode.length ? sourceCode : null, pathCode.slice(0, -1), 20, 0);
          }));
          if (Array.isArray(rapport.enfants_declares)) rapport.enfants_declares.slice(0, 100).forEach(function (v) {
            if (!v) return;
            if (sourceCode === null && v.type_noeud === "document" && idValide(v.source_id)) {
              actions.append(actionDocumentaire("Parcourir le document " + v.source_id, function () { ouvrirCode(v.source_id, [], 20, 0); }));
            } else if (sourceCode !== null && rapport.parent_trouve === true && v.type_noeud === "niveau_declare" &&
                       cheminCodeValide(v.chemin) && v.chemin.length === pathCode.length + 1 &&
                       cleCheminCode(v.chemin.slice(0, -1)) === cleCheminCode(pathCode)) {
              actions.append(actionDocumentaire("Parcourir le niveau " + v.chemin.at(-1).identifiant, function () { ouvrirCode(sourceCode, v.chemin, 20, 0); }));
            } else if (sourceCode !== null && rapport.parent_trouve === true && v.type_noeud === "version_article" &&
                       v.version_declaree && v.version_declaree.reference && v.version_declaree.reference.source_id === sourceCode) {
              proposerVersion(v.version_declaree.id);
            }
          });
          if (entier(rapport.limite, 1, 100) && entier(rapport.decalage, 0, 1000000) &&
              entier(rapport.decalage_suivant, rapport.decalage + 1, 1000000) &&
              entier(rapport.total_enfants_declares, rapport.decalage_suivant + 1, Number.MAX_SAFE_INTEGER)) {
            actions.append(actionDocumentaire("Page suivante des enfants Code", function () { ouvrirCode(sourceCode, pathCode, rapport.limite, rapport.decalage_suivant); }));
          }
        }
        var interDiff = rapport.type_rapport === "comparaison_litterale_versions_article_inter_lots";
        var lotsDiffValides = !interDiff || (rapport.lots_exacts && rapport.lots_exacts.avant === lot.value &&
          [rapport.lots_exacts.avant, rapport.lots_exacts.apres].every(function (id) {
            return rep.lots.some(function (v) { return v.id === id && v.type_lot === "code"; });
          }));
        if (interDiff && lotsDiffValides && !lecture.disabled) {
          ["avant", "apres"].forEach(function (cote) {
            var version = rapport[cote] && rapport[cote].version_declaree;
            if (!version || version.id !== rapport[cote + "_id_exact"] || !idValide(version.id)) return;
            actions.append(actionDocumentaire("Lire la version " + cote + " du lot " + rapport.lots_exacts[cote], function () {
              lot.value = rapport.lots_exacts[cote]; adapter();
              readId.value = version.id; readField.value = "texte_integral"; readLimit.value = 4000; readOffset.value = 0;
              chargerArticle();
            }));
          });
        }
        if ((rapport.type_rapport === "comparaison_litterale_versions_article" || interDiff) && lotsDiffValides && !diffArticle.disabled &&
            rapport.champs_comparables === true && rapport.unite_decalage === "points_de_code_unicode_python" &&
            idValide(rapport.avant_id_exact) && idValide(rapport.apres_id_exact) &&
            ["texte_integral", "texte_francais", "texte_arabe", "texte_origine", "texte_modificatif"].includes(rapport.champ_texte) &&
            entier(rapport.limite, 1, 16000) && rapport.avant && rapport.apres &&
            entier(rapport.avant.decalage_dans_bloc, 0, 67108864) && entier(rapport.apres.decalage_dans_bloc, 0, 67108864)) {
          ["avant", "apres"].forEach(function (cote) {
            var bloc = rapport[cote];
            if (typeof bloc.fragment_bloc_different !== "string" || Array.from(bloc.fragment_bloc_different).length > rapport.limite ||
                !entier(bloc.total_caracteres_bloc_different, 0, 67108864) ||
                bloc.decalage_suivant !== bloc.decalage_dans_bloc + Array.from(bloc.fragment_bloc_different).length ||
                !entier(bloc.decalage_suivant, bloc.decalage_dans_bloc + 1, bloc.total_caracteres_bloc_different - 1)) return;
            actions.append(actionDocumentaire("Suite du bloc " + cote, function () {
              diffAvant.value = rapport.avant_id_exact; diffApres.value = rapport.apres_id_exact;
              readField.value = rapport.champ_texte; readLimit.value = rapport.limite;
              diffOffsetAvant.value = cote === "avant" ? bloc.decalage_suivant : rapport.avant.decalage_dans_bloc;
              diffOffsetApres.value = cote === "apres" ? bloc.decalage_suivant : rapport.apres.decalage_dans_bloc;
              if (interDiff) apres.value = rapport.lots_exacts.apres;
              chargerDiffArticle(interDiff);
            }));
          });
        }
        if (rapport.type_rapport === "rapprochement_litteral_fragment_article_pdf" && !matchLecture.disabled &&
            rapport.article_trouve === true && rapport.texte_renseigne === true && idValide(rapport.article_id_exact) &&
            rapport.unite_decalage === "points_de_code_unicode_python" && entier(rapport.page_physique_demandee, 1, 10000) &&
            ["texte_integral", "texte_francais", "texte_arabe", "texte_origine", "texte_modificatif"].includes(rapport.champ_texte) &&
            entier(rapport.limite, 1, 16000) && entier(rapport.decalage, 0, 67108864) &&
            typeof rapport.fragment_article === "string" && Array.from(rapport.fragment_article).length <= rapport.limite &&
            rapport.decalage_suivant === rapport.decalage + Array.from(rapport.fragment_article).length &&
            entier(rapport.decalage_suivant, rapport.decalage + 1, 67108864) &&
            entier(rapport.total_caracteres_article, rapport.decalage_suivant + 1, 67108864)) {
          actions.append(actionDocumentaire("Fragment suivant à rapprocher", function () {
            readId.value = rapport.article_id_exact; readField.value = rapport.champ_texte;
            readLimit.value = rapport.limite; readOffset.value = rapport.decalage_suivant;
            matchPage.value = rapport.page_physique_demandee; chargerRapprochement();
          }));
        }
        if (rapport.type_rapport === "lecture_article_documentaire" && rapport.article_trouve === true &&
            !relationsLecture.disabled && idValide(rapport.article_id_exact)) {
          actions.append(actionDocumentaire("Inspecter les relations de cette version", function () {
            relationsId.value = rapport.article_id_exact; relationsSens.value = "tous"; relationsType.value = "";
            relationsLimit.value = 20; relationsOffset.value = 0; chargerRelations();
          }));
        }
        if (rapport.type_rapport === "relations_documentaires_version_article" && !relationsLecture.disabled &&
            rapport.article_trouve === true && idValide(rapport.article_id_exact) && ["tous", "entrantes", "sortantes"].includes(rapport.sens) &&
            (rapport.type_relation_filtre === null || typesRelations.includes(rapport.type_relation_filtre))) {
          var versionsVues = new Set(), preuvesVues = new Set();
          if (Array.isArray(rapport.relations_declarees)) rapport.relations_declarees.slice(0, 100).forEach(function (v) {
            if (!v || !v.relation_declaree || !v.autre_version_declaree) return;
            var r = v.relation_declaree, autre = v.autre_version_declaree;
            var sortante = r.origine_id === rapport.article_id_exact, entrante = r.cible_id === rapport.article_id_exact;
            if (sortante === entrante || !idValide(r.id) || !typesRelations.includes(r.type_relation) ||
                (rapport.sens === "sortantes" && !sortante) || (rapport.sens === "entrantes" && !entrante) ||
                (rapport.type_relation_filtre !== null && rapport.type_relation_filtre !== r.type_relation) ||
                v.sens_par_rapport_a_version !== (sortante ? "sortante" : "entrante") ||
                autre.id !== (sortante ? r.cible_id : r.origine_id) || !idValide(autre.id)) return;
            if (!versionsVues.has(autre.id)) { versionsVues.add(autre.id); proposerVersion(autre.id); }
            actions.append(actionDocumentaire("Préparer le rapprochement de justification " + r.id, function () {
              justificationId.value = r.id; justificationPage.value = 1; justificationLimit.value = 4000; justificationOffset.value = 0;
              statut.textContent = "Relation préparée : choisissez explicitement la page physique puis lancez le rapprochement.";
            }));
            var origine = sortante ? rapport.version_declaree : autre;
            if (!r.reference || !origine || !origine.reference || r.reference.source_id !== origine.reference.source_id ||
                !Array.isArray(rapport.documents_declares_page)) return;
            var preuve = rapport.documents_declares_page.find(function (d) { return d && d.id === r.reference.source_id; });
            if (!preuve || !idValide(preuve.id) || typeof preuve.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(preuve.sha256) || preuvesVues.has(preuve.id)) return;
            preuvesVues.add(preuve.id);
            actions.append(actionDocumentaire("Lire le PDF de preuve " + preuve.id + " — page 1", function () {
              pdfId.value = preuve.id; pdfPage.value = 1; pdfLimit.value = 4000; pdfOffset.value = 0; chargerPDF();
            }));
          });
          if (entier(rapport.limite, 1, 100) && entier(rapport.decalage, 0, 1000000) &&
              entier(rapport.decalage_suivant, rapport.decalage + 1, 1000000) &&
              entier(rapport.total_relations_filtrees, rapport.decalage_suivant + 1, Number.MAX_SAFE_INTEGER)) {
            actions.append(actionDocumentaire("Page suivante des relations déclarées", function () {
              relationsId.value = rapport.article_id_exact; relationsSens.value = rapport.sens;
              relationsType.value = rapport.type_relation_filtre || ""; relationsLimit.value = rapport.limite;
              relationsOffset.value = rapport.decalage_suivant; chargerRelations();
            }));
          }
        }
        if (rapport.type_rapport === "rapprochement_litteral_justification_relation_pdf" && !justificationLecture.disabled &&
            rapport.relation_trouvee === true && idValide(rapport.relation_id_exact) &&
            rapport.unite_decalage === "points_de_code_unicode_python" && entier(rapport.page_physique_demandee, 1, 10000) &&
            entier(rapport.limite, 1, 16000) && entier(rapport.decalage, 0, 67108864) &&
            typeof rapport.fragment_justification === "string" && Array.from(rapport.fragment_justification).length <= rapport.limite &&
            rapport.decalage_suivant === rapport.decalage + Array.from(rapport.fragment_justification).length &&
            entier(rapport.decalage_suivant, rapport.decalage + 1, 67108864) &&
            entier(rapport.total_caracteres_justification, rapport.decalage_suivant + 1, 67108864)) {
          actions.append(actionDocumentaire("Justification suivante à rapprocher", function () {
            justificationId.value = rapport.relation_id_exact; justificationPage.value = rapport.page_physique_demandee;
            justificationLimit.value = rapport.limite; justificationOffset.value = rapport.decalage_suivant; chargerJustification();
          }));
        }
        var docPDF = rapport.document_declare;
        if (!pdfLecture.disabled && ["rapprochement_litteral_fragment_article_pdf", "rapprochement_litteral_justification_relation_pdf"].includes(rapport.type_rapport) &&
            rapport.extraction_effectuee === true && docPDF && idValide(docPDF.id) &&
            typeof docPDF.sha256 === "string" && /^[a-f0-9]{64}$/.test(docPDF.sha256) && rapport.sha256_pdf_lu === docPDF.sha256 &&
            entier(rapport.page_physique_demandee, 1, 10000)) {
          actions.append(actionDocumentaire("Lire la page PDF rapprochée", function () {
            pdfId.value = docPDF.id; pdfPage.value = rapport.page_physique_demandee; pdfLimit.value = 4000;
            pdfOffset.value = entier(rapport.position_debut_pdf, 0, 199999) ? rapport.position_debut_pdf : 0; chargerPDF();
          }));
        }
        if (!pdfLecture.disabled && docPDF && idValide(docPDF.id) && typeof docPDF.sha256 === "string" && /^[a-f0-9]{64}$/.test(docPDF.sha256)) {
          actions.append(actionDocumentaire("Lire le PDF reçu " + docPDF.id + " — page 1", function () {
            pdfId.value = docPDF.id; pdfPage.value = 1; pdfLimit.value = 4000; pdfOffset.value = 0; chargerPDF();
          }));
        }
        if (!pdfLecture.disabled && rapport.type_rapport === "lecture_page_pdf_recu" && docPDF && idValide(docPDF.id) &&
            typeof docPDF.sha256 === "string" && /^[a-f0-9]{64}$/.test(docPDF.sha256) && rapport.sha256_pdf_lu === docPDF.sha256 &&
            rapport.methode === "texte_natif_pdfium_sans_ocr" && rapport.unite_decalage === "points_de_code_unicode_python" &&
            entier(rapport.page_physique, 1, 10000) && entier(rapport.nombre_pages_pdf, rapport.page_physique, 10000) &&
            entier(rapport.limite, 1, 16000) && entier(rapport.decalage, 0, 67108864) &&
            entier(rapport.total_caracteres, 0, 200000)) {
          if (typeof rapport.fragment === "string" && Array.from(rapport.fragment).length <= rapport.limite &&
              rapport.decalage_suivant === rapport.decalage + Array.from(rapport.fragment).length &&
              entier(rapport.decalage_suivant, rapport.decalage + 1, rapport.total_caracteres - 1)) {
            actions.append(actionDocumentaire("Fragment suivant de la page PDF", function () {
              pdfId.value = docPDF.id; pdfPage.value = rapport.page_physique;
              pdfLimit.value = rapport.limite; pdfOffset.value = rapport.decalage_suivant; chargerPDF();
            }));
          }
          if (rapport.page_physique_suivante === rapport.page_physique + 1 && rapport.page_physique_suivante <= rapport.nombre_pages_pdf) {
            actions.append(actionDocumentaire("Page physique PDF suivante", function () {
              pdfId.value = docPDF.id; pdfPage.value = rapport.page_physique_suivante;
              pdfLimit.value = rapport.limite; pdfOffset.value = 0; chargerPDF();
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
      outils.append(form, fiche, arbre, codeArbre, lecture, pdfLecture, diffArticle, matchLecture, relationsLecture, justificationLecture, paireTarif, mesuresRecherche, sourcesLecture);
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
