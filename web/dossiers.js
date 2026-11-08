/* ============================================================================
   UniOCR — Espace dossiers
   ----------------------------------------------------------------------------
   Liste filtrable + panneau de détail, alimentés par l'API réelle.
   Tout le rendu passe par createElement/textContent : aucune donnée serveur
   n'est interprétée comme du HTML.
   ========================================================================== */
(function () {
  "use strict";

  var PAR_PAGE = 40;

  var FILTRES = {
    tous: function () { return true; },
    "en-cours": function (d) {
      return ["en_preparation", "traitement_en_cours", "revision_requise",
              "incomplet", "en_validation"].indexOf(d.state) !== -1;
    },
    "a-valider": function (d) {
      return ["en_validation", "revision_requise"].indexOf(d.state) !== -1;
    },
    clos: function (d) { return ["exporte", "archive"].indexOf(d.state) !== -1; }
  };

  var ETATS = {
    en_preparation:      { label: "En préparation",   ton: "info" },
    traitement_en_cours: { label: "Traitement",       ton: "info" },
    en_validation:       { label: "En validation",    ton: "warn" },
    revision_requise:    { label: "Révision requise", ton: "danger" },
    incomplet:           { label: "Incomplet",        ton: "warn" },
    exporte:             { label: "Exporté",          ton: "ok" },
    archive:             { label: "Archivé",          ton: "muted" }
  };

  var CATEGORIES = {
    invoice: "Facture",
    bill_of_lading: "Connaissement",
    packing_list: "Colisage",
    certificate_of_origin: "Certificat d'origine",
    customs_declaration: "Déclaration douanière",
    insurance: "Assurance",
    transport_document: "Document de transport"
  };

  var etat = {
    dossiers: [],
    filtre: "tous",
    recherche: "",
    visibles: PAR_PAGE,
    selection: null,
    detail: null
  };

  function $(id) { return document.getElementById(id); }
  function base() { return "/api"; }
  function jeton() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }

  function getJSON(chemin) {
    var entetes = { Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(base() + chemin, { headers: entetes, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
  }

  function envoyer(chemin, corps) {
    var entetes = { "Content-Type": "application/json", Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(base() + chemin, {
      method: "POST",
      headers: entetes,
      credentials: "same-origin",
      body: JSON.stringify(corps || {})
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  /** GET sur une URL absolue (les modules exposent des préfixes différents). */
  function getJSONUrl(url) {
    var entetes = { Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(url, { headers: entetes, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
  }

  /**
   * Affiche un squelette puis le panneau réel. Une erreur réseau est dite
   * explicitement : le panneau n'affiche jamais de valeurs inventées.
   */
  function panneauAsync(zone, url, rendu) {
    var attente = el("div", "dos-loading");
    attente.appendChild(el("span", "skeleton skeleton--title"));
    attente.appendChild(el("span", "skeleton skeleton--text"));
    attente.appendChild(el("span", "skeleton skeleton--text"));
    attente.appendChild(el("span", "skeleton skeleton--text"));
    zone.appendChild(attente);

    getJSONUrl(url).then(function (donnees) {
      if (!attente.parentNode) return;
      attente.remove();
      rendu(donnees);
    }).catch(function (erreur) {
      if (!attente.parentNode) return;
      attente.remove();
      zone.appendChild(el("p", "dos-detail__empty-txt",
        "Données indisponibles pour le moment (" + (erreur && erreur.message ? erreur.message : "erreur réseau") + ")."));
    });
    return zone;
  }

  function el(tag, classe, texte) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texte !== undefined && texte !== null) n.textContent = String(texte);
    return n;
  }

  function pill(txt, ton) {
    return el("span", "status-pill status-pill--" + (ton || "muted"), txt);
  }

  function texteOuTiret(v) {
    if (v === undefined || v === null || v === "") return "—";
    return String(v);
  }

  function dateCourte(ts) {
    if (!ts) return "—";
    var d = new Date(ts * 1000);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
  }

  function dateHeure(ts) {
    if (!ts) return "—";
    var d = new Date(ts * 1000);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }) + " · " +
      d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }

  function numero(n) {
    if (n === undefined || n === null || n === "") return "—";
    return Number(n).toLocaleString("fr-FR");
  }

  function statut(d) {
    var e = ETATS[d.state];
    return {
      label: d.state_label || (e && e.label) || d.state || "Inconnu",
      ton: (e && e.ton) || "muted"
    };
  }

  function identifiant(d) {
    return d.reference || d.label || d.id;
  }

  function correspond(d, terme) {
    if (!terme) return true;
    var champs = [d.id, d.label, d.reference, d.client_importateur, d.fournisseur,
                  d.navire, d.reference_bl, d.state_label];
    return champs.some(function (v) {
      return v && String(v).toLowerCase().indexOf(terme) !== -1;
    });
  }

  function filtrer() {
    var terme = etat.recherche.trim().toLowerCase();
    return etat.dossiers.filter(function (d) {
      return (FILTRES[etat.filtre] || FILTRES.tous)(d) && correspond(d, terme);
    });
  }

  /* ---------- Liste ---------- */

  function rendreListe() {
    var liste = $("dos-list");
    var vide = $("dos-empty");
    var plus = $("dos-more");
    if (!liste) return;

    var tous = filtrer();
    var affiches = tous.slice(0, etat.visibles);

    liste.textContent = "";
    affiches.forEach(function (d) {
      liste.appendChild(ligne(d));
    });

    if (vide) {
      vide.hidden = tous.length > 0;
      vide.textContent = etat.dossiers.length
        ? "Aucun dossier ne correspond à cette recherche."
        : "Aucun dossier enregistré pour le moment.";
    }
    if (plus) {
      plus.hidden = tous.length <= etat.visibles;
    }
    var meta = $("dos-meta");
    if (meta) {
      meta.textContent = tous.length
        ? Math.min(affiches.length, tous.length) + " sur " + tous.length + " dossier" +
          (tous.length > 1 ? "s" : "")
        : "";
    }
    actualiserCompteurs();
  }

  function ligne(d) {
    var st = statut(d);
    var b = el("button", "dos-row");
    b.type = "button";
    b.setAttribute("data-id", d.id);
    if (etat.selection === d.id) b.classList.add("is-selected");
    b.setAttribute("aria-pressed", etat.selection === d.id ? "true" : "false");

    var principal = el("div", "dos-row__main");
    principal.appendChild(el("span", "dos-row__ref", identifiant(d)));
    principal.appendChild(el("span", "dos-row__sub",
      (d.client_importateur || "Client non renseigné") +
      (d.type_operation ? " · " + d.type_operation : "")));
    b.appendChild(principal);

    var cote = el("div", "dos-row__side");
    cote.appendChild(pill(st.label, st.ton));
    var pieces = Array.isArray(d.pieces) ? d.pieces.length : 0;
    cote.appendChild(el("span", "dos-row__meta", pieces + " pièce" + (pieces > 1 ? "s" : "")));
    b.appendChild(cote);

    b.addEventListener("click", function () { selectionner(d.id); });
    return b;
  }

  function actualiserCompteurs() {
    Object.keys(FILTRES).forEach(function (cle) {
      var n = $("dos-count-" + cle);
      if (!n) return;
      n.textContent = String(etat.dossiers.filter(FILTRES[cle]).length);
    });
  }

  function marquerActif(cle) {
    var barre = $("dos-filters");
    if (!barre) return;
    Array.prototype.forEach.call(barre.querySelectorAll("[data-filter]"), function (btn) {
      var actif = btn.getAttribute("data-filter") === cle;
      btn.classList.toggle("is-active", actif);
      btn.setAttribute("aria-pressed", actif ? "true" : "false");
    });
  }

  /* ---------- Détail ---------- */

  function selectionner(id) {
    etat.selection = id;
    etat.detail = null;
    var d = etat.dossiers.filter(function (x) { return x.id === id; })[0] || null;
    rendreListe();
    rendreDetail(d, true);

    getJSON("/dossiers/" + encodeURIComponent(id)).then(function (detail) {
      if (etat.selection !== id) return;
      etat.detail = detail;
      rendreDetail(detail, false);
    }).catch(function () {
      if (etat.selection !== id) return;
      var note = $("dos-detail-note");
      if (note) note.textContent = "Détail complet indisponible — informations de la liste affichées.";
    });
  }

  function rendreDetail(d, chargement) {
    var corps = $("dos-detail-body");
    var vide = $("dos-detail-empty");
    if (!corps || !vide) return;

    if (!d) {
      corps.hidden = true;
      vide.hidden = false;
      return;
    }
    vide.hidden = true;
    corps.hidden = false;
    corps.textContent = "";

    var st = statut(d);

    var tete = el("div", "dos-detail__head");
    var titres = el("div");
    titres.appendChild(el("span", "dos-detail__eyebrow", d.id));
    titres.appendChild(el("h2", "dos-detail__title", identifiant(d)));
    titres.appendChild(el("p", "dos-detail__sub",
      (d.client_importateur || "Client non renseigné") +
      (d.profile_label ? " · " + d.profile_label : "")));
    tete.appendChild(titres);

    var actions = el("div", "dos-detail__actions");
    actions.appendChild(pill(st.label, st.ton));
    if (d.priorite && d.priorite !== "normale") {
      actions.appendChild(pill("Priorité " + d.priorite, d.priorite === "haute" ? "danger" : "warn"));
    }
    tete.appendChild(actions);
    corps.appendChild(tete);

    var note = el("p", "dos-detail__note");
    note.id = "dos-detail-note";
    note.textContent = chargement ? "Chargement du détail…" : "";
    corps.appendChild(note);

    // Bandeau d'identité : les informations qui permettent de reconnaître le
    // dossier d'un coup d'œil (référence, parties, transport, statut).
    var bandeau = el("div", "dos-detail__meta");
    [
      ["Référence", d.reference || d.id],
      ["Client", d.client_importateur],
      ["Fournisseur", d.fournisseur],
      ["Navire", d.navire],
      ["B/L", d.reference_bl],
      ["Conteneurs", (Array.isArray(d.conteneurs_associes) ? d.conteneurs_associes.length : 0) || ""],
      ["Responsable", d.gestionnaire],
      ["Priorité", d.priorite]
    ].forEach(function (paire) {
      var item = el("div", "dos-meta-item");
      item.appendChild(el("span", "dos-meta-item__key", paire[0]));
      item.appendChild(el("span", "dos-meta-item__val",
        paire[1] === 0 || paire[1] === "" || paire[1] === undefined || paire[1] === null
          ? "—" : String(paire[1])));
      bandeau.appendChild(item);
    });
    corps.appendChild(bandeau);

    corps.appendChild(onglets(d));
  }

  function onglets(d) {
    var enveloppe = el("div", "dos-tabs");
    var barre = el("div", "dos-tabs__bar");
    barre.setAttribute("role", "tablist");
    barre.setAttribute("aria-label", "Onglets du dossier");

    var panneaux = el("div", "dos-tabs__panels");
    var pieces = Array.isArray(d.pieces) ? d.pieces : [];

    var definitions = [
      { cle: "synthese", titre: "Synthèse", rendu: panneauSynthese },
      { cle: "informations", titre: "Informations générales", rendu: panneauInformations },
      { cle: "documents", titre: "Documents (" + pieces.length + ")", rendu: panneauDocuments },
      { cle: "ocr", titre: "Résultats OCR", rendu: panneauOCR },
      { cle: "controle", titre: "Contrôle documentaire", rendu: panneauControle },
      { cle: "anomalies", titre: "Anomalies", rendu: panneauAnomalies },
      { cle: "maritime", titre: "Transport maritime", rendu: panneauMaritime },
      { cle: "douane", titre: "Douane", rendu: panneauDouane },
      { cle: "frais", titre: "Frais et paiements", rendu: panneauFrais },
      { cle: "enlevement", titre: "Enlèvement et livraison", rendu: panneauEnlevement },
      { cle: "historique", titre: "Historique", rendu: panneauHistorique }
    ];

    function activer(cle) {
      Array.prototype.forEach.call(barre.children, function (b) {
        var on = b.getAttribute("data-tab") === cle;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
        b.tabIndex = on ? 0 : -1;
      });
      panneaux.textContent = "";
      var def = definitions.filter(function (x) { return x.cle === cle; })[0];
      if (def) panneaux.appendChild(def.rendu(d));
    }

    definitions.forEach(function (def, index) {
      var b = el("button", "dos-tab", def.titre);
      b.type = "button";
      b.setAttribute("role", "tab");
      b.setAttribute("data-tab", def.cle);
      b.tabIndex = index === 0 ? 0 : -1;
      b.addEventListener("click", function () { activer(def.cle); });
      barre.appendChild(b);
    });

    // Navigation clavier conforme au motif ARIA « tablist ».
    barre.addEventListener("keydown", function (ev) {
      if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return;
      ev.preventDefault();
      var index = definitions.map(function (x) { return x.cle; })
        .indexOf(barre.querySelector(".dos-tab.is-active").getAttribute("data-tab"));
      var suivant = ev.key === "ArrowRight" ? index + 1 : index - 1;
      if (suivant < 0) suivant = definitions.length - 1;
      if (suivant >= definitions.length) suivant = 0;
      activer(definitions[suivant].cle);
      barre.children[suivant].focus();
    });

    enveloppe.appendChild(barre);
    enveloppe.appendChild(panneaux);
    activer("synthese");
    return enveloppe;
  }

  /* ---------- 1. Synthèse ---------- */

  function panneauSynthese(d) {
    var zone = el("div", "dos-panel");

    var compteurs = el("div", "dos-counts");
    function tuile(libelle, valeur, ton) {
      var t = el("div", "dos-count");
      t.appendChild(el("span", "dos-count__val" + (ton ? " dos-count__val--" + ton : ""), valeur));
      t.appendChild(el("span", "dos-count__lbl", libelle));
      return t;
    }
    var pieces = Array.isArray(d.pieces) ? d.pieces : [];
    var conteneurs = Array.isArray(d.conteneurs_associes) ? d.conteneurs_associes : [];
    compteurs.appendChild(tuile("Documents", pieces.length));
    compteurs.appendChild(tuile("Conteneurs", conteneurs.length));
    compteurs.appendChild(tuile("Extractions OCR", "…"));
    compteurs.appendChild(tuile("Anomalies", "…"));
    compteurs.appendChild(tuile("Frais cumulés", "…"));
    zone.appendChild(compteurs);

    // Renseigne les compteurs par des appels réels, sans bloquer l'affichage.
    getJSONUrl("/api/dossiers/" + encodeURIComponent(d.id) + "/documents-ocr")
      .then(function (extractions) {
        compteurs.children[2].querySelector(".dos-count__val").textContent =
          Array.isArray(extractions) ? extractions.length : 0;
      }).catch(function () { compteurs.children[2].querySelector(".dos-count__val").textContent = "—"; });

    getJSONUrl("/api/controle/" + encodeURIComponent(d.id) + "/anomalies")
      .then(function (res) {
        var liste = (res && res.anomalies) || [];
        var valeur = compteurs.children[3].querySelector(".dos-count__val");
        valeur.textContent = liste.length;
        valeur.className = "dos-count__val" + (liste.length ? " dos-count__val--danger" : "");
      }).catch(function () { compteurs.children[3].querySelector(".dos-count__val").textContent = "—"; });

    getJSONUrl("/api/frais/dossier/" + encodeURIComponent(d.id) + "/resume")
      .then(function (resume) {
        compteurs.children[4].querySelector(".dos-count__val").textContent =
          numero(resume.total_frais) + " " + (d.devise || "");
      }).catch(function () { compteurs.children[4].querySelector(".dos-count__val").textContent = "—"; });

    var grille = el("div", "dos-kv");
    [
      ["Référence dossier", d.reference || d.id],
      ["Client importateur", d.client_importateur],
      ["Fournisseur", d.fournisseur],
      ["Navire / voyage", [d.navire, d.numero_voyage].filter(Boolean).join(" · ")],
      ["Connaissement B/L", d.reference_bl],
      ["Port de destination", d.port_destination],
      ["Responsable", d.gestionnaire],
      ["Priorité", d.priorite]
    ].forEach(function (paire) {
      var ligne = el("div", "dos-kv__row");
      ligne.appendChild(el("span", "dos-kv__key", paire[0]));
      ligne.appendChild(el("span", "dos-kv__val", texteOuTiret(paire[1])));
      grille.appendChild(ligne);
    });
    zone.appendChild(grille);

    var hist = Array.isArray(d.history) ? d.history : [];
    zone.appendChild(el("h3", "dos-panel__titre", "Timeline opérationnelle"));
    if (!hist.length) {
      zone.appendChild(el("p", "dos-detail__empty-txt",
        "Aucune évolution enregistrée pour ce dossier : la timeline se construit à partir des validations réelles."));
    } else {
      var tl = el("div", "timeline");
      hist.slice(-8).reverse().forEach(function (entree, index) {
        var step = el("div", "tl-step " + (index === 0 ? "tl-step--current" : "tl-step--done"));
        var dot = el("span", "tl-dot", index === 0 ? "●" : "✓");
        step.appendChild(dot);
        var corps = el("div", "tl-body");
        var action = entree.action || entree.evenement || entree.type || "Événement";
        corps.appendChild(el("div", "tl-title", String(action).replace(/_/g, " ")));
        var meta = [];
        if (entree.acteur) meta.push(entree.acteur);
        if (entree.etat) meta.push(entree.etat);
        if (entree.horodatage || entree.created_at) meta.push(dateHeure(entree.horodatage || entree.created_at));
        corps.appendChild(el("div", "tl-meta", meta.join(" · ") || "—"));
        step.appendChild(corps);
        tl.appendChild(step);
      });
      zone.appendChild(tl);
    }
    return zone;
  }

  /* ---------- 4. Résultats OCR ---------- */

  function panneauOCR(d) {
    var zone = el("div", "dos-panel");
    zone.appendChild(el("p", "dos-panel__intro",
      "Champs extraits par l'OCR. Une extraction n'est pas une validation réglementaire : chaque valeur doit être contrôlée avant transmission."));
    return panneauAsync(zone, "/api/dossiers/" + encodeURIComponent(d.id) + "/documents-ocr", function (extractions) {
      var liste = Array.isArray(extractions) ? extractions : [];
      if (!liste.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt",
          "Aucune extraction OCR rattachée à ce dossier. Importez un document puis classez-le depuis l'atelier OCR."));
        return;
      }
      liste.forEach(function (extraction) {
        var carte = el("div", "ocr-card");
        var tete = el("div", "ocr-card__head");
        tete.appendChild(el("span", "ocr-card__type", extraction.type_document || "Document"));
        var statut = extraction.statut === "validated" ? ["Validé", "ok"]
          : extraction.statut === "corrected" ? ["Corrigé", "warn"] : ["À valider", "info"];
        tete.appendChild(pill(statut[0], statut[1]));
        var confiance = Math.round(Number(extraction.confiance_globale || 0) * 100);
        tete.appendChild(el("span", "ocr-card__conf", confiance + " % de confiance"));
        carte.appendChild(tete);

        var champs = Array.isArray(extraction.champs_extraits) ? extraction.champs_extraits : [];
        if (!champs.length) {
          carte.appendChild(el("p", "dos-detail__empty-txt", "Aucun champ exploitable détecté."));
        } else {
          var table = el("table", "table table--compact");
          var thead = el("thead");
          var trh = el("tr");
          ["Champ", "Valeur", "Confiance", "État"].forEach(function (titre) {
            trh.appendChild(el("th", null, titre));
          });
          thead.appendChild(trh);
          table.appendChild(thead);
          var tbody = el("tbody");
          champs.slice(0, 8).forEach(function (champ) {
            var tr = el("tr");
            tr.appendChild(el("td", null, champ.nom || "—"));
            var valeur = champ.valeur_confirmee || champ.valeur_correctee || champ.valeur_normale || champ.valeur_raw || "—";
            tr.appendChild(el("td", null, valeur));
            tr.appendChild(el("td", null, Math.round(Number(champ.confiance || 0) * 100) + " %"));
            var etatChamp = champ.statut === "validated" ? ["Validé", "ok"]
              : champ.statut === "corrected" ? ["Corrigé", "warn"]
              : champ.statut === "rejected" ? ["Rejeté", "danger"] : ["Détecté", "info"];
            var td = el("td");
            td.appendChild(pill(etatChamp[0], etatChamp[1]));
            tr.appendChild(td);
            tbody.appendChild(tr);
          });
          table.appendChild(tbody);
          var scroll = el("div", "table-wrap");
          scroll.appendChild(table);
          carte.appendChild(scroll);
        }

        if (extraction.document_id || extraction.job_id) {
          var ouvrir = el("button", "btn ghost sm", "Ouvrir dans l'atelier OCR");
          ouvrir.type = "button";
          ouvrir.addEventListener("click", function () {
            window.location.hash = "#documents/ocr";
            var jobId = extraction.job_id || extraction.document_id;
            setTimeout(function () {
              if (window.openJob) window.openJob(jobId);
            }, 120);
          });
          carte.appendChild(ouvrir);
        }
        zone.appendChild(carte);
      });

      // Comparaison inter-documents : les mêmes champs vus par chaque
      // document. Une valeur qui diverge est signalée — l'opérateur tranche.
      zone.appendChild(comparerExtractions(d, liste));
    });
  }

  /* ---------- 4 bis. Comparaison inter-documents ---------- */

  function valeurChamp(champ) {
    return champ.valeur_confirmee || champ.valeur_correctee ||
      champ.valeur_normale || champ.valeur_raw || "";
  }

  function comparerExtractions(d, extractions) {
    var bloc = el("div", "ocr-compare");
    var tete = el("div", "dos-panel__head");
    tete.appendChild(el("h3", "dos-panel__titre", "Comparaison inter-documents"));
    bloc.appendChild(tete);

    var documents = extractions.slice(0, 4).map(function (extraction) {
      var champs = {};
      (extraction.champs_extraits || []).forEach(function (champ) {
        if (!champ || !champ.nom) return;
        champs[champ.nom] = {
          valeur: valeurChamp(champ),
          confiance: Number(champ.confiance || 0),
          statut: champ.statut || "detected"
        };
      });
      return {
        titre: extraction.type_document || "Document",
        statut: extraction.statut,
        champs: champs
      };
    });

    if (documents.length < 2) {
      bloc.appendChild(el("p", "dos-detail__empty-txt",
        "La comparaison demande au moins deux documents extraits pour ce dossier. " +
        "Ajoutez une pièce supplémentaire depuis l'atelier OCR."));
      return bloc;
    }

    var noms = [];
    documents.forEach(function (document) {
      Object.keys(document.champs).forEach(function (nom) {
        if (noms.indexOf(nom) === -1) noms.push(nom);
      });
    });

    if (!noms.length) {
      bloc.appendChild(el("p", "dos-detail__empty-txt",
        "Aucun champ comparable : les documents n'ont pas livré de valeurs structurées."));
      return bloc;
    }

    bloc.appendChild(el("p", "dos-panel__intro",
      documents.length + " documents comparés · " + noms.length + " champs. " +
      "Une divergence signale des valeurs différentes entre documents : elle est à arbitrer, pas à corriger automatiquement."));

    var table = el("table", "table table--compact ocr-matrix");
    var thead = el("thead");
    var trh = el("tr");
    trh.appendChild(el("th", null, "Champ"));
    documents.forEach(function (document) {
      trh.appendChild(el("th", null, document.titre));
    });
    trh.appendChild(el("th", null, ""));
    thead.appendChild(trh);
    table.appendChild(thead);

    var tbody = el("tbody");
    var divergences = 0;
    noms.forEach(function (nom) {
      var valeurs = documents.map(function (document) {
        return document.champs[nom] ? document.champs[nom].valeur : "";
      });
      var distinctes = valeurs.filter(function (valeur, index) {
        return valeur && valeurs.indexOf(valeur) === index;
      });
      var divergente = distinctes.length > 1;
      if (divergente) divergences += 1;

      var tr = el("tr", divergente ? "is-divergent" : "");
      tr.appendChild(el("td", "ocr-matrix__nom", nom.replace(/_/g, " ")));

      documents.forEach(function (document, index) {
        var cellule = document.champs[nom];
        var td = el("td", "ocr-matrix__cell");
        td.appendChild(el("span", "ocr-matrix__val", cellule && cellule.valeur ? cellule.valeur : "—"));
        if (cellule) {
          var confiance = Math.round(cellule.confiance * 100);
          var ton = confiance >= 85 ? "ok" : confiance >= 60 ? "warn" : "danger";
          td.appendChild(el("span", "ocr-matrix__conf ocr-matrix__conf--" + ton, confiance + " %"));
        }
        tr.appendChild(td);
      });

      var actions = el("td", "sp-td--actions");
      if (divergente) {
        actions.appendChild(pill("Divergence", "danger"));
      }
      tr.appendChild(actions);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    var scroll = el("div", "table-wrap");
    scroll.appendChild(table);
    bloc.appendChild(scroll);
    bloc.appendChild(el("p", "dos-panel__meta",
      divergences
        ? divergences + " champ(s) divergent(s) entre documents — à arbitrer avant validation."
        : "Aucune divergence détectée entre les valeurs des documents comparés."));

    // Les constats du contrôle documentaire complètent la lecture.
    getJSONUrl("/api/dossiers/" + encodeURIComponent(d.id) + "/coherence")
      .then(function (coherence) {
        var constats = (coherence && coherence.constats) || [];
        if (!constats.length) return;
        var liste = el("div", "ocr-compare__constats");
        liste.appendChild(el("h4", "dos-panel__titre", "Constats du contrôle documentaire"));
        constats.slice(0, 6).forEach(function (constat) {
          var ligne = el("div", "constat-row");
          var ic = el("span", "row-ic row-ic--warn");
          ic.textContent = "!";
          ligne.appendChild(ic);
          var corps = el("span", "row-main");
          corps.appendChild(el("span", "row-title", constat.message || "Écart détecté"));
          corps.appendChild(el("span", "row-sub",
            [constat.champ, constat.document, constat.regle].filter(Boolean).join(" · ")));
          ligne.appendChild(corps);
          liste.appendChild(ligne);
        });
        bloc.appendChild(liste);
      })
      .catch(function () {
        /* le contrôle documentaire reste consultable dans son onglet */
      });

    return bloc;
  }

  /* ---------- 5. Contrôle documentaire ---------- */

  function panneauControle(d) {
    var zone = el("div", "dos-panel");
    return panneauAsync(zone, "/api/dossiers/" + encodeURIComponent(d.id) + "/coherence", function (coherence) {
      var entete = el("div", "dos-panel__head");
      var transmissible = coherence && coherence.transmissible;
      entete.appendChild(pill(transmissible ? "Transmissible" : "Non transmissible",
        transmissible ? "ok" : "danger"));
      entete.appendChild(el("span", "dos-panel__meta",
        (coherence && coherence.documents_analyses ? coherence.documents_analyses : 0) + " document(s) analysé(s)"));
      zone.appendChild(entete);

      if (coherence && coherence.motif) {
        zone.appendChild(el("p", "dos-panel__motif", coherence.motif));
      }

      var constats = (coherence && coherence.constats) || [];
      if (!constats.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt",
          "Aucun écart relevé entre les documents analysés. Le contrôle reste déclaratif : il porte sur les pièces présentes."));
        return;
      }
      constats.forEach(function (constat) {
        var niveau = constat.niveau || constat.severite || "info";
        var ligne = el("div", "constat-row");
        var ic = el("span", "row-ic" + (niveau === "critique" || niveau === "error" ? " row-ic--danger"
          : niveau === "warning" || niveau === "avertissement" ? " row-ic--warn" : ""));
        ic.textContent = "!";
        ligne.appendChild(ic);
        var corps = el("span", "row-main");
        corps.appendChild(el("span", "row-title", constat.message || constat.libelle || "Écart détecté"));
        corps.appendChild(el("span", "row-sub",
          [constat.champ, constat.document, constat.regle].filter(Boolean).join(" · ")));
        ligne.appendChild(corps);
        zone.appendChild(ligne);
      });
    });
  }

  /* ---------- 6. Anomalies ---------- */

  function panneauAnomalies(d) {
    var zone = el("div", "dos-panel");
    return panneauAsync(zone, "/api/controle/" + encodeURIComponent(d.id) + "/anomalies", function (resultat) {
      var anomalies = (resultat && resultat.anomalies) || [];
      if (!anomalies.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt", "Aucune anomalie active sur ce dossier."));
        return;
      }
      anomalies.forEach(function (anomalie) {
        var ligne = el("div", "constat-row");
        var niveau = String(anomalie.niveau || anomalie.severite || "warning");
        var ic = el("span", "row-ic" + (niveau === "critique" || niveau === "error" || niveau === "danger"
          ? " row-ic--danger" : " row-ic--warn"));
        ic.textContent = "!";
        ligne.appendChild(ic);
        var corps = el("span", "row-main");
        corps.appendChild(el("span", "row-title", anomalie.message || anomalie.description || anomalie.type || "Anomalie"));
        corps.appendChild(el("span", "row-sub",
          [anomalie.champ, anomalie.document, anomalie.regle, anomalie.resolue ? "résolue" : "à traiter"]
            .filter(Boolean).join(" · ")));
        ligne.appendChild(corps);
        var meta = el("span", "row-meta");
        meta.appendChild(pill(niveau, niveau === "critique" || niveau === "danger" ? "danger" : "warn"));
        ligne.appendChild(meta);
        zone.appendChild(ligne);
      });
    });
  }

  /* ---------- 7. Transport maritime ---------- */

  function panneauMaritime(d) {
    var zone = el("div", "dos-panel");
    var url = "/transit/dossiers/" + encodeURIComponent(d.id);
    return panneauAsync(zone, url, function (transit) {
      var grille = el("div", "dos-kv");
      [
        ["Navire", transit.navire],
        ["Voyage", transit.numero_voyage],
        ["Port de chargement", transit.port_chargement],
        ["Port de destination", transit.port_destination],
        ["ETA", transit.eta],
        ["ETA effective", transit.eta_effective],
        ["Connaissement B/L", transit.reference_bl],
        ["Incoterm", [transit.incoterm, transit.lieu_incoterm].filter(Boolean).join(" · ")],
        ["Colis", transit.nombre_colis ? numero(transit.nombre_colis) : ""],
        ["Poids brut (kg)", transit.poids_brut ? numero(transit.poids_brut) : ""],
        ["Marchandise", transit.description_marchandise]
      ].forEach(function (paire) {
        var ligne = el("div", "dos-kv__row");
        ligne.appendChild(el("span", "dos-kv__key", paire[0]));
        ligne.appendChild(el("span", "dos-kv__val", texteOuTiret(paire[1])));
        grille.appendChild(ligne);
      });
      zone.appendChild(grille);

      zone.appendChild(el("h3", "dos-panel__titre", "Conteneurs"));
      getJSONUrl("/transit/dossiers/" + encodeURIComponent(d.id) + "/conteneurs")
        .then(function (res) {
          var liste = (res && res.conteneurs) || [];
          if (!liste.length) {
            zone.appendChild(el("p", "dos-detail__empty-txt",
              "Aucun conteneur associé. Ajoutez les numéros depuis le module Opérations maritimes."));
            return;
          }
          var table = el("table", "table table--compact");
          var thead = el("thead");
          var trh = el("tr");
          ["Conteneur", "Type", "Poids", "Statut"].forEach(function (titre) { trh.appendChild(el("th", null, titre)); });
          thead.appendChild(trh);
          table.appendChild(thead);
          var tbody = el("tbody");
          liste.forEach(function (c) {
            var tr = el("tr");
            tr.appendChild(el("td", null, c.numero || c.id || "—"));
            tr.appendChild(el("td", null, c.type_conteneur || c.type || "—"));
            tr.appendChild(el("td", null, c.poids ? numero(c.poids) + " kg" : "—"));
            tr.appendChild(el("td", null, c.statut || "—"));
            tbody.appendChild(tr);
          });
          table.appendChild(tbody);
          var scroll = el("div", "table-wrap");
          scroll.appendChild(table);
          zone.appendChild(scroll);
        })
        .catch(function () {
          zone.appendChild(el("p", "dos-detail__empty-txt", "Conteneurs indisponibles pour le moment."));
        });
    });
  }

  /* ---------- 8. Douane ---------- */

  function panneauDouane(d) {
    var zone = el("div", "dos-panel");
    var grille = el("div", "dos-kv");
    [
      ["Code SH", d.code_sh],
      ["Valeur commerciale", d.valeur_commerciale ? numero(d.valeur_commerciale) + " " + (d.devise || "") : ""],
      ["Pays d'origine", d.pays_origine],
      ["Pays d'expédition", d.pays_expedition],
      ["Type d'opération", d.type_operation],
      ["Incoterm", d.incoterm]
    ].forEach(function (paire) {
      var ligne = el("div", "dos-kv__row");
      ligne.appendChild(el("span", "dos-kv__key", paire[0]));
      ligne.appendChild(el("span", "dos-kv__val", texteOuTiret(paire[1])));
      grille.appendChild(ligne);
    });
    zone.appendChild(grille);

    zone.appendChild(el("h3", "dos-panel__titre", "Déclarations douanières"));
    getJSONUrl("/api/declarations").then(function (declarations) {
      var liste = (Array.isArray(declarations) ? declarations : []).filter(function (dec) {
        return dec.dossier_id === d.id;
      });
      if (!liste.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt",
          "Aucune déclaration enregistrée pour ce dossier. Créez-la depuis le module Douane & réglementation."));
        return;
      }
      var table = el("table", "table table--compact");
      var thead = el("thead");
      var trh = el("tr");
      ["Numéro", "Régime", "Bureau", "Statut", "Liquidation"].forEach(function (t) { trh.appendChild(el("th", null, t)); });
      thead.appendChild(trh);
      table.appendChild(thead);
      var tbody = el("tbody");
      liste.forEach(function (dec) {
        var tr = el("tr");
        tr.appendChild(el("td", null, dec.numero || dec.id || "—"));
        tr.appendChild(el("td", null, dec.regime_douanier || dec.regime || "—"));
        tr.appendChild(el("td", null, dec.bureau_douane || dec.bureau || "—"));
        tr.appendChild(el("td", null, dec.statut || "—"));
        tr.appendChild(el("td", null, dec.montant_liquidation ? numero(dec.montant_liquidation) : "—"));
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      var scroll = el("div", "table-wrap");
      scroll.appendChild(table);
      zone.appendChild(scroll);
    }).catch(function () {
      zone.appendChild(el("p", "dos-detail__empty-txt", "Déclarations indisponibles pour le moment."));
    });
    return zone;
  }

  /* ---------- 9. Frais et paiements ---------- */

  function panneauFrais(d) {
    var zone = el("div", "dos-panel");
    return panneauAsync(zone, "/api/frais/dossier/" + encodeURIComponent(d.id) + "/resume", function (resume) {
      var grille = el("div", "dos-counts");
      [
        ["Total frais", resume.total_frais, ""],
        ["Avancés", resume.total_avances, ""],
        ["Facturé client", resume.total_factures_client, ""],
        ["Solde restant", resume.solde_restant, Number(resume.solde_restant) > 0 ? "danger" : "ok"]
      ].forEach(function (paire) {
        var tuile = el("div", "dos-count");
        tuile.appendChild(el("span", "dos-count__val" + (paire[2] ? " dos-count__val--" + paire[2] : ""),
          numero(paire[1]) + " " + (d.devise || "")));
        tuile.appendChild(el("span", "dos-count__lbl", paire[0]));
        grille.appendChild(tuile);
      });
      zone.appendChild(grille);

      var categories = resume.par_categorie || {};
      var cles = Object.keys(categories);
      if (!cles.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt",
          "Aucun frais enregistré pour ce dossier. Les frais se saisissent depuis le module Finance & facturation."));
        return;
      }
      var table = el("table", "table table--compact");
      var thead = el("thead");
      var trh = el("tr");
      ["Catégorie", "Montant"].forEach(function (t) { trh.appendChild(el("th", null, t)); });
      thead.appendChild(trh);
      table.appendChild(thead);
      var tbody = el("tbody");
      cles.forEach(function (cle) {
        var tr = el("tr");
        tr.appendChild(el("td", null, cle.replace(/_/g, " ")));
        tr.appendChild(el("td", null, numero(categories[cle]) + " " + (d.devise || "")));
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      var scroll = el("div", "table-wrap");
      scroll.appendChild(table);
      zone.appendChild(scroll);
    });
  }

  /* ---------- 10. Enlèvement et livraison ---------- */

  function panneauEnlevement(d) {
    var zone = el("div", "dos-panel");
    zone.appendChild(el("p", "dos-panel__intro",
      "Le statut d'enlèvement provient du module terminal. Tant qu'aucun ordre n'est enregistré, ce dossier reste « à enlever »."));
    return panneauAsync(zone, "/api/terminal", function (ordres) {
      var liste = (Array.isArray(ordres) ? ordres : []).filter(function (o) {
        return o.dossier_id === d.id;
      });
      if (!liste.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt",
          "Aucun ordre d'enlèvement pour ce dossier."));
        var lien = el("a", "ws-link", "Ouvrir le module Enlèvement & livraison");
        lien.href = "#enlevissement";
        zone.appendChild(lien);
        return;
      }
      liste.forEach(function (ordre) {
        var ligne = el("div", "constat-row");
        var corps = el("span", "row-main");
        corps.appendChild(el("span", "row-title", ordre.numero || ordre.id || "Ordre d'enlèvement"));
        corps.appendChild(el("span", "row-sub",
          [ordre.transporteur, ordre.terminal, ordre.date_planifiee ? dateCourte(ordre.date_planifiee) : ""]
            .filter(Boolean).join(" · ")));
        ligne.appendChild(corps);
        ligne.appendChild(pill(ordre.statut || "en attente",
          ordre.statut === "sortie" || ordre.statut === "livre" ? "ok" : "warn"));
        zone.appendChild(ligne);
      });
    });
  }

  /* ---------- 11. Historique ---------- */

  function panneauHistorique(d) {
    var zone = el("div", "dos-panel");
    return panneauAsync(zone, "/api/dossiers/" + encodeURIComponent(d.id) + "/trace", function (trace) {
      if (trace && trace.avertissement) {
        zone.appendChild(el("p", "dos-panel__intro", trace.avertissement));
      }
      var entrees = (trace && trace.entrees) || [];
      if (!entrees.length) {
        zone.appendChild(el("p", "dos-detail__empty-txt",
          "Aucune entrée de journal pour ce dossier. L'historique s'alimente au fil des actions réelles."));
        return;
      }
      var tl = el("div", "timeline");
      entrees.slice(-30).reverse().forEach(function (entree, index) {
        var step = el("div", "tl-step " + (index === 0 ? "tl-step--current" : "tl-step--done"));
        step.appendChild(el("span", "tl-dot", "•"));
        var corps = el("div", "tl-body");
        corps.appendChild(el("div", "tl-title", String(entree.action || entree.evenement || "Action").replace(/_/g, " ")));
        corps.appendChild(el("div", "tl-meta",
          [entree.acteur, entree.horodatage || entree.date, entree.details]
            .filter(Boolean).join(" · ") || "—"));
        step.appendChild(corps);
        tl.appendChild(step);
      });
      zone.appendChild(tl);
    });
  }

  function panneauDocuments(d) {
    var zone = el("div", "dos-docs");
    var pieces = Array.isArray(d.pieces) ? d.pieces : [];

    if (!pieces.length) {
      zone.appendChild(el("p", "dos-detail__empty-txt",
        "Aucune pièce jointe. Ajoutez des documents depuis l'atelier OCR."));
      return zone;
    }

    pieces.forEach(function (p) {
      var lignePiece = el("div", "dos-doc");

      var icone = el("span", "dos-doc__icon");
      icone.setAttribute("aria-hidden", "true");
      icone.textContent = "PDF";
      lignePiece.appendChild(icone);

      var infos = el("div", "dos-doc__infos");
      infos.appendChild(el("span", "dos-doc__name", p.filename || p.job_id));
      var cat = CATEGORIES[p.category] || p.document_type || p.category || "Document";
      var details = [cat];
      if (p.page_count) details.push(p.page_count + " page" + (p.page_count > 1 ? "s" : ""));
      if (typeof p.ocr_confidence === "number" && p.ocr_confidence > 0) {
        details.push("confiance " + Math.round(p.ocr_confidence * 100) + " %");
      }
      infos.appendChild(el("span", "dos-doc__meta", details.join(" · ")));
      lignePiece.appendChild(infos);

      var statutPiece = p.verification_status === "validated" ? ["Validé", "ok"]
        : p.verification_status === "rejected" ? ["Rejeté", "danger"]
        : ["À vérifier", "warn"];
      lignePiece.appendChild(pill(statutPiece[0], statutPiece[1]));

      var lien = el("a", "dos-doc__link", "JSON");
      lien.href = base() + "/jobs/" + encodeURIComponent(p.job_id) + "/export/json";
      lien.rel = "noopener";
      lignePiece.appendChild(lien);

      zone.appendChild(lignePiece);
    });
    return zone;
  }

  function panneauInformations(d) {
    var zone = el("div", "dos-kv");
    var lignes = [
      ["Référence", d.reference],
      ["Type d'opération", d.type_operation],
      ["Client importateur", d.client_importateur],
      ["Fournisseur", d.fournisseur],
      ["Pays d'origine", d.pays_origine],
      ["Pays d'expédition", d.pays_expedition],
      ["Port de chargement", d.port_chargement],
      ["Port de destination", d.port_destination],
      ["Navire", d.navire],
      ["Voyage", d.numero_voyage],
      ["ETA", d.eta],
      ["Incoterm", d.incoterm],
      ["Valeur commerciale", d.valeur_commerciale ? numero(d.valeur_commerciale) + " " + (d.devise || "") : ""],
      ["Colis", d.nombre_colis ? numero(d.nombre_colis) : ""],
      ["Poids brut (kg)", d.poids_brut ? numero(d.poids_brut) : ""],
      ["Code SH", d.code_sh],
      ["Gestionnaire", d.gestionnaire]
    ];

    lignes.forEach(function (paire) {
      var ligne = el("div", "dos-kv__row");
      ligne.appendChild(el("span", "dos-kv__key", paire[0]));
      ligne.appendChild(el("span", "dos-kv__val", texteOuTiret(paire[1])));
      zone.appendChild(ligne);
    });
    return zone;
  }

  function panneauSuivi(d) {
    var zone = el("div", "dos-suivi");

    var resume = el("div", "dos-kv");
    [
      ["État courant", statut(d).label],
      ["Dernière évolution", d.dernier_etat_evolution],
      ["Ouvert le", d.date_ouverture ? dateCourte(d.date_ouverture) : (d.cree_le ? dateCourte(d.cree_le) : "")],
      ["Version", d.version]
    ].forEach(function (paire) {
      var ligne = el("div", "dos-kv__row");
      ligne.appendChild(el("span", "dos-kv__key", paire[0]));
      ligne.appendChild(el("span", "dos-kv__val", texteOuTiret(paire[1])));
      resume.appendChild(ligne);
    });
    zone.appendChild(resume);

    var ech = Array.isArray(d.echeances) ? d.echeances : [];
    zone.appendChild(el("h3", "dos-suivi__titre", "Échéances"));
    if (!ech.length) {
      zone.appendChild(el("p", "dos-detail__empty-txt", "Aucune échéance enregistrée."));
    } else {
      var liste = el("ul", "dos-echeances");
      ech.forEach(function (e) {
        var item = el("li");
        var libelle = typeof e === "object" && e ? (e.label || e.titre || e.nom || "Échéance") : String(e);
        var quand = typeof e === "object" && e ? (e.date || e.echeance || e.le) : "";
        item.appendChild(el("span", "dos-echeances__label", libelle));
        if (quand) item.appendChild(el("span", "dos-echeances__date", String(quand)));
        liste.appendChild(item);
      });
      zone.appendChild(liste);
    }

    if (d.observations) {
      zone.appendChild(el("h3", "dos-suivi__titre", "Observations"));
      var obs = el("p", "dos-observations");
      obs.textContent = d.observations;
      zone.appendChild(obs);
    }
    return zone;
  }

  /* ---------- Chargement ---------- */

  function charger() {
    var liste = $("dos-list");
    if (liste) {
      liste.textContent = "";
      liste.appendChild(el("p", "ws-empty", "Chargement des dossiers…"));
    }
    return getJSON("/dossiers").then(function (dossiers) {
      etat.dossiers = Array.isArray(dossiers) ? dossiers.slice() : [];
      etat.dossiers.sort(function (a, b) {
        var da = a.updated_at || a.date_ouverture || 0;
        var db = b.updated_at || b.date_ouverture || 0;
        return db - da;
      });
      etat.visibles = PAR_PAGE;
      rendreListe();
      if (etat.selection) {
        var d = etat.dossiers.filter(function (x) { return x.id === etat.selection; })[0];
        if (d) rendreDetail(d, false);
      }
    }).catch(function () {
      if (liste) {
        liste.textContent = "";
        liste.appendChild(el("p", "ws-empty",
          "Impossible de charger les dossiers. Vérifiez votre connexion puis actualisez."));
      }
    });
  }

  function brancher() {
    var recherche = $("dos-search");
    if (recherche) {
      recherche.addEventListener("input", function () {
        etat.recherche = recherche.value || "";
        etat.visibles = PAR_PAGE;
        rendreListe();
      });
    }

    var barre = $("dos-filters");
    if (barre) {
      barre.addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-filter]");
        if (!btn) return;
        etat.filtre = btn.getAttribute("data-filter");
        etat.visibles = PAR_PAGE;
        marquerActif(etat.filtre);
        rendreListe();
      });
    }

    var plus = $("dos-more");
    if (plus) {
      plus.addEventListener("click", function () {
        etat.visibles += PAR_PAGE;
        rendreListe();
      });
    }

    var rafraichir = $("dos-refresh");
    if (rafraichir) {
      rafraichir.addEventListener("click", charger);
    }
  }

  /* ---------- Sous-routes (#dossiers/…) ---------- */

  var ROUTES = {
    "dossiers/tous": "tous",
    "dossiers/en-cours": "en-cours",
    "dossiers/a-valider": "a-valider",
    "dossiers/bloques": "a-valider",
    "dossiers/clotures": "clos",
    "dossiers/clients": "tous"
  };

  function appliquerRoute() {
    var hash = (window.location.hash || "").replace(/^#/, "");
    // Une modale native cachée par le routeur conserve sinon le document inert.
    if (hash !== "dossiers/nouveau") fermerCreation();
    if (hash.indexOf("dossiers") !== 0) return;

    if (hash === "dossiers/nouveau") {
      ouvrirCreation();
      return;
    }
    var filtre = ROUTES[hash];
    if (filtre && filtre !== etat.filtre) {
      etat.filtre = filtre;
      etat.visibles = PAR_PAGE;
      marquerActif(filtre);
      rendreListe();
    }
  }

  /* ---------- Création d'un dossier ---------- */

  /* Ports proposés depuis le référentiel : la saisie reste libre (un port
     inconnu du référentiel ne doit pas bloquer la création), mais l'opérateur
     voit immédiatement ce qui est déjà référencé — et lit que c'est vide. */
  var portsCharges = null;

  function remplirPorts() {
    if (portsCharges) return portsCharges;
    portsCharges = fetch("/api/referentiels/ports", { headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : { entrees: [] }; })
      .then(function (corps) {
        var entrees = (corps && corps.entrees) || [];
        var valeurs = entrees.map(function (e) { return e.code || e.libelle; })
          .filter(function (v) { return v; });
        ["dos-ports-chargement", "dos-ports-destination"].forEach(function (id) {
          var liste = $(id);
          if (!liste) return;
          liste.textContent = "";
          valeurs.forEach(function (valeur) {
            var option = document.createElement("option");
            option.value = valeur;
            liste.appendChild(option);
          });
        });
        var aide = $("dos-ports-aide");
        if (aide) {
          aide.textContent = valeurs.length
            ? valeurs.length + " port" + (valeurs.length > 1 ? "s" : "") +
              " proposé" + (valeurs.length > 1 ? "s" : "") + " par le référentiel."
            : "Référentiel des ports vide : saisie libre. Ajoutez des ports dans " +
              "Référentiels pour les proposer ici.";
        }
        return valeurs;
      })
      .catch(function () { return []; });
    return portsCharges;
  }

  function ouvrirCreation() {
    var dlg = $("dos-create");
    if (!dlg) return;
    remplirPorts();
    var err = $("dos-create-erreur");
    if (err) { err.hidden = true; err.textContent = ""; }
    var premier = dlg.querySelector('input[name="label"]');
    if (typeof dlg.showModal === "function") {
      if (!dlg.open) dlg.showModal();
    } else {
      dlg.setAttribute("open", "");
    }
    if (premier) premier.focus();
  }

  function fermerCreation() {
    var dlg = $("dos-create");
    if (dlg && typeof dlg.close === "function") dlg.close();
    else if (dlg) dlg.removeAttribute("open");
    if (window.location.hash === "#dossiers/nouveau") {
      history.replaceState(null, "", "#dossiers");
          window.dispatchEvent(new Event("hashchange"));
    }
  }

  function creerDossier(ev) {
    if (ev) ev.preventDefault();
    var dlg = $("dos-create");
    var form = $("dos-create-form");
    var err = $("dos-create-erreur");
    var bouton = $("dos-create-envoyer");
    if (!dlg || !form) return;

    var donnees = {};
    Array.prototype.forEach.call(form.elements, function (champ) {
      if (!champ.name) return;
      var valeur = (champ.value || "").trim();
      if (valeur) donnees[champ.name] = valeur;
    });
    if (!donnees.label) {
      if (err) { err.textContent = "Le libellé est obligatoire."; err.hidden = false; }
      return;
    }

    if (bouton) { bouton.disabled = true; bouton.textContent = "Création…"; }
    envoyer("/dossiers", donnees).then(function (dossier) {
      fermerCreation();
      form.reset();
      if (typeof window.toast === "function") {
        window.toast("Dossier créé", "success");
      }
      return charger().then(function () {
        if (dossier && dossier.id) selectionner(dossier.id);
      });
    }).catch(function () {
      if (err) {
        err.textContent = "La création a échoué. Vérifiez les champs puis réessayez.";
        err.hidden = false;
      }
    }).then(function () {
      if (bouton) { bouton.disabled = false; bouton.textContent = "Créer le dossier"; }
    });
  }

  function demarrer() {
    if (!$("tab-dossiers")) return;
    brancher();

    var dlg = $("dos-create");
    if (dlg) {
      var form = $("dos-create-form");
      if (form) form.addEventListener("submit", creerDossier);
      var annuler = $("dos-create-annuler");
      if (annuler) annuler.addEventListener("click", fermerCreation);
      var fermer = $("dos-create-cancel");
      if (fermer) fermer.addEventListener("click", fermerCreation);
      dlg.addEventListener("close", function () {
        if (window.location.hash === "#dossiers/nouveau") {
          history.replaceState(null, "", "#dossiers");
          window.dispatchEvent(new Event("hashchange"));
        }
      });
    }

    window.addEventListener("hashchange", appliquerRoute);
    marquerActif(etat.filtre);
    appliquerRoute();
    charger();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.Dossiers = { charger: charger, etat: etat, ouvrir: selectionner };
})();
