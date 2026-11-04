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

    corps.appendChild(onglets(d));
  }

  function onglets(d) {
    var enveloppe = el("div", "dos-tabs");
    var barre = el("div", "dos-tabs__bar");
    barre.setAttribute("role", "tablist");

    var panneaux = el("div", "dos-tabs__panels");
    var pieces = Array.isArray(d.pieces) ? d.pieces : [];

    var definitions = [
      { cle: "documents", titre: "Documents (" + pieces.length + ")", rendu: panneauDocuments },
      { cle: "informations", titre: "Informations", rendu: panneauInformations },
      { cle: "suivi", titre: "Suivi", rendu: panneauSuivi }
    ];

    function activer(cle) {
      Array.prototype.forEach.call(barre.children, function (b) {
        var on = b.getAttribute("data-tab") === cle;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
      panneaux.textContent = "";
      var def = definitions.filter(function (x) { return x.cle === cle; })[0];
      if (def) panneaux.appendChild(def.rendu(d));
    }

    definitions.forEach(function (def) {
      var b = el("button", "dos-tab", def.titre);
      b.type = "button";
      b.setAttribute("role", "tab");
      b.setAttribute("data-tab", def.cle);
      b.addEventListener("click", function () { activer(def.cle); });
      barre.appendChild(b);
    });

    enveloppe.appendChild(barre);
    enveloppe.appendChild(panneaux);
    activer("documents");
    return enveloppe;
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

  function ouvrirCreation() {
    var dlg = $("dos-create");
    if (!dlg) return;
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

  window.Dossiers = { charger: charger, etat: etat };
})();
