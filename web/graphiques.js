/**
 * UniOCR — Graphiques (écran dédié)
 * ---------------------------------------------------------------------------
 * L'entrée de menu « Graphiques » renvoyait vers la page « Rapports » : un
 * titre, deux boutons, aucune courbe. Cet écran dessine les six séries que le
 * serveur calcule déjà (`/api/dashboard/graphique/*` et `serie-dossiers`).
 *
 * Règles tenues :
 *   - aucun chiffre inventé : les séries viennent du serveur, telles quelles ;
 *   - une série vide n'affiche pas un cadre muet : elle dit ce qui manque
 *     (aucun dossier sur la période, port non renseigné, etc.) ;
 *   - si le serveur ne répond pas, l'écran le dit au lieu de rester vide.
 */
(function () {
  "use strict";

  var chargement = null;
  var dejaCharge = false;

  function $(id) { return document.getElementById(id); }

  function sectionVisible() {
    var section = $("tab-graphiques");
    if (!section) return false;
    if (section.classList.contains("hidden")) return false;
    return window.getComputedStyle(section).display !== "none";
  }

  function lire(url) {
    return fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      });
  }

  function couleur(nom) {
    return window.UniOCRPalette ? window.UniOCRPalette.couleur(nom, "#00d9ff") : "#00d9ff";
  }

  /* Message d'absence : la carte dit *pourquoi* elle est vide. */
  function vide(idCanvas, idVide, message) {
    var canvas = $(idCanvas), note = $(idVide);
    if (canvas) canvas.textContent = "";
    if (note) {
      note.textContent = message;
      note.hidden = false;
    }
  }

  function rempli(idCanvas, idVide) {
    var note = $(idVide);
    if (note) { note.hidden = true; note.textContent = ""; }
    return $(idCanvas);
  }

  /* Une série « bar » du serveur : {series: [{name, y}]}. */
  function dessineBarres(idCanvas, idVide, donnees, messageVide) {
    var series = (donnees && donnees.series) || [];
    var positives = series.filter(function (s) { return Number(s.y) > 0; });
    if (!positives.length) {
      vide(idCanvas, idVide, messageVide);
      return;
    }
    var hote = rempli(idCanvas, idVide);
    if (!hote || !window.UniOCRCharts) return;
    hote.textContent = "";
    window.UniOCRCharts.bars(hote, {
      labels: positives.map(function (s) { return s.name; }),
      values: positives.map(function (s) { return Number(s.y); }),
      height: 200
    });
  }

  /* Valeurs de repli du serveur : elles disent qu'un champ n'est pas renseigné. */
  var NON_RENSEIGNE = /^(non défini|non defini|inconnu|sans port|sans client|-|n\/a)$/i;

  /* Une série « pie »/« doughnut » : {series: [{name, y}]} → anneau. */
  function dessineAnneau(idCanvas, idVide, donnees, messageVide) {
    var series = (donnees && donnees.series) || [];
    var positives = series.filter(function (s) { return Number(s.y) > 0; });
    if (!positives.length) {
      vide(idCanvas, idVide, messageVide);
      return;
    }
    /* Un anneau à une seule part « non défini » ne montre rien : autant dire
       que le champ n'est pas renseigné, et combien de dossiers sont concernés. */
    if (positives.length === 1 && NON_RENSEIGNE.test(String(positives[0].name).trim())) {
      vide(idCanvas, idVide,
        messageVide + " (" + positives[0].y + " dossier" +
        (Number(positives[0].y) > 1 ? "s" : "") + ")");
      return;
    }
    var hote = rempli(idCanvas, idVide);
    if (!hote || !window.UniOCRCharts) return;
    hote.textContent = "";
    var teintes = ["cyan", "blue", "violet", "teal", "amber", "red"];
    window.UniOCRCharts.donut(hote, {
      items: positives.map(function (s, i) {
        return { label: s.name, value: Number(s.y), color: couleur(teintes[i % teintes.length]) };
      }),
      size: 168
    });
    var legende = document.createElement("ul");
    legende.className = "graph__legende";
    positives.forEach(function (s, i) {
      var li = document.createElement("li");
      var pastille = document.createElement("span");
      pastille.className = "graph__pastille";
      pastille.style.background = couleur(teintes[i % teintes.length]);
      li.appendChild(pastille);
      li.appendChild(document.createTextNode(s.name + " — " + s.y));
      legende.appendChild(li);
    });
    hote.appendChild(legende);
  }

  /* Série temporelle : {series: [{date, crees, traites, clotures}]}. */
  function dessineActivite(donnees) {
    var serie = (donnees && donnees.series) || [];
    var total = serie.reduce(function (n, j) {
      return n + Number(j.crees || 0) + Number(j.traites || 0) + Number(j.clotures || 0);
    }, 0);
    if (!serie.length || total === 0) {
      vide("graph-serie", "graph-serie-vide",
        serie.length
          ? "Aucun mouvement sur la période (" + serie.length + " jours observés) : " +
            "ni création, ni traitement, ni clôture."
          : "Le serveur n'a renvoyé aucune journée : la série est vide.");
      return;
    }
    var hote = rempli("graph-serie", "graph-serie-vide");
    if (!hote || !window.UniOCRCharts) return;
    hote.textContent = "";
    window.UniOCRCharts.line(hote, {
      labels: serie.map(function (j) { return (j.date || "").slice(5); }),
      series: [
        { label: "Créés", values: serie.map(function (j) { return Number(j.crees || 0); }),
          color: couleur("blue") },
        { label: "Traités", values: serie.map(function (j) { return Number(j.traites || 0); }),
          color: couleur("cyan") },
        { label: "Clôturés", values: serie.map(function (j) { return Number(j.clotures || 0); }),
          color: couleur("teal") }
      ],
      height: 200
    });
  }

  function majEntete(etat) {
    var chip = $("graph-sync");
    if (!chip) return;
    chip.textContent = etat;
  }

  function charger(force) {
    if (chargement) return chargement;
    if (dejaCharge && !force) return Promise.resolve();
    majEntete("Chargement…");
    chargement = Promise.all([
      lire("/api/dashboard/graphique/etat-dossiers").catch(function () { return null; }),
      lire("/api/dashboard/serie-dossiers?jours=30").catch(function () { return null; }),
      lire("/api/dashboard/graphique/repartition-par-port").catch(function () { return null; }),
      lire("/api/dashboard/graphique/top-clients").catch(function () { return null; }),
      lire("/api/dashboard/graphique/anomalies-par-type").catch(function () { return null; }),
      lire("/api/dashboard/graphique/fret-par-gestionnaire").catch(function () { return null; })
    ]).then(function (reponses) {
      var etats = reponses[0], serie = reponses[1], ports = reponses[2];
      var clients = reponses[3], anomalies = reponses[4], frais = reponses[5];
      var indisponibles = reponses.filter(function (r) { return r === null; }).length;

      dessineBarres("graph-etats", "graph-etats-vide", etats,
        "Aucun dossier par état : la base est vide.");
      dessineActivite(serie);
      dessineAnneau("graph-ports", "graph-ports-vide", ports,
        "Tous les dossiers sont sans port renseigné : il n'y a rien à répartir.");
      dessineAnneau("graph-clients", "graph-clients-vide", clients,
        "Aucun client rattaché : renseignez le client importateur des dossiers.");
      dessineBarres("graph-anomalies", "graph-anomalies-vide", anomalies,
        "Aucune anomalie enregistrée sur les documents traités.");
      dessineBarres("graph-frais", "graph-frais-vide", frais,
        "Aucun frais imputé : les montants par gestionnaire restent à zéro.");

      var maintenant = new Date();
      majEntete(indisponibles
        ? indisponibles + " série(s) indisponible(s) — " + maintenant.toLocaleTimeString()
        : "Séries à jour — " + maintenant.toLocaleTimeString());
      dejaCharge = true;
    }).catch(function (erreur) {
      majEntete("Serveur injoignable : " + erreur.message);
    }).then(function () {
      chargement = null;
    });
    return chargement;
  }

  function brancher() {
    var bouton = $("graph-refresh");
    if (bouton && !bouton.__lie) {
      bouton.__lie = true;
      bouton.addEventListener("click", function () { charger(true); });
    }
  }

  function verifier() {
    if (!sectionVisible()) return;
    brancher();
    charger(false);
  }

  window.addEventListener("hashchange", function () { setTimeout(verifier, 80); });
  window.addEventListener("load", function () { setTimeout(verifier, 200); });
  setTimeout(verifier, 600);
})();
