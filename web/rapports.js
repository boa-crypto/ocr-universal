/**
 * UniOCR — Rapports & statistiques
 * ---------------------------------------------------------------------------
 * La page « Rapports » agrège les graphiques déjà calculés par le serveur
 * (`/api/dashboard/graphique/*`) et les compteurs de `/api/stats`. Rien n'est
 * recalculé côté client et rien n'est inventé : une série vide reste vide.
 *
 * Le type de rendu suit le champ `type` renvoyé par l'API :
 *   bar → histogramme, line → courbe, pie/doughnut → anneau.
 */
(function () {
  "use strict";

  var GRAPHIQUES = [
    { cle: "etat-dossiers", titre: "Dossiers par état" },
    { cle: "anomalies-par-type", titre: "Anomalies par type" },
    { cle: "taux-reussite-par-mois", titre: "Taux de réussite par mois" },
    { cle: "financier-mensuel", titre: "Évolution financière mensuelle" },
    { cle: "top-clients", titre: "Top clients" },
    { cle: "repartition-par-port", titre: "Répartition par port" },
    { cle: "fret-par-gestionnaire", titre: "Frais par gestionnaire" }
  ];

  var COULEURS = ["#1677FF", "#00D9FF", "#00CBA8", "#9466F5", "#F59E0B", "#F04452", "#4B6485"];

  function $(id) { return document.getElementById(id); }

  function jeton() {
    try { return sessionStorage.getItem("uniocr_token") || ""; } catch (e) { return ""; }
  }

  function lire(url) {
    var entetes = { Accept: "application/json" };
    var t = jeton();
    if (t) entetes.Authorization = "Bearer " + t;
    return fetch(url, { headers: entetes, credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function elt(nom, classe, texte) {
    var n = document.createElement(nom);
    if (classe) n.className = classe;
    if (texte !== undefined && texte !== null) n.textContent = String(texte);
    return n;
  }

  function construire(section) {
    if (section.querySelector("[data-rapports]")) return;
    var entete = section.querySelector("header");
    if (!entete) return;

    var hote = elt("div", "rapports");
    hote.setAttribute("data-rapports", "1");
    entete.parentNode.insertBefore(hote, entete.nextSibling);

    var grille = elt("div", "rapports__grid");
    hote.appendChild(grille);

    var cartes = {};
    GRAPHIQUES.forEach(function (definition) {
      var carte = elt("div", "ws-card chart-card");
      var tete = elt("div", "chart-head");
      var bloc = elt("div");
      bloc.appendChild(elt("div", "ws-card-title", definition.titre));
      var sous = elt("div", "row-sub", "Chargement…");
      bloc.appendChild(sous);
      tete.appendChild(bloc);
      carte.appendChild(tete);

      var zone = elt("div", "chart-host");
      carte.appendChild(zone);
      grille.appendChild(carte);
      cartes[definition.cle] = { zone: zone, sous: sous, carte: carte };
    });

    GRAPHIQUES.forEach(function (definition) {
      var cible = cartes[definition.cle];
      lire("/api/dashboard/graphique/" + definition.cle).then(function (donnees) {
        var series = (donnees && donnees.series) || [];
        var total = series.reduce(function (somme, point) {
          return somme + (Number(point.y) || 0);
        }, 0);
        cible.sous.textContent = series.length
          ? series.length + " série(s) · total " + total.toLocaleString("fr-FR")
          : "Aucune donnée";

        if (!series.length) {
          cible.zone.textContent = "";
          cible.zone.appendChild(elt("p", "ws-empty", "Aucune donnée à représenter pour le moment."));
          return;
        }

        var labels = series.map(function (p) { return p.name; });
        var valeurs = series.map(function (p) { return Number(p.y) || 0; });
        var type = donnees.type || "bar";

        if (type === "pie" || type === "doughnut") {
          window.UniOCRCharts.donut(cible.zone, {
            items: series.map(function (p, i) {
              return { label: p.name, value: Number(p.y) || 0, color: COULEURS[i % COULEURS.length] };
            }),
            size: 168,
            centre: "total",
            label: definition.titre
          });
        } else if (type === "line") {
          window.UniOCRCharts.line(cible.zone, {
            labels: labels,
            series: [{ key: definition.cle, label: definition.titre, values: valeurs, color: "#1677FF", fill: true }],
            height: 200,
            dots: false,
            label: definition.titre
          });
        } else {
          window.UniOCRCharts.bars(cible.zone, {
            labels: labels,
            values: valeurs,
            colors: series.map(function (_, i) { return COULEURS[i % COULEURS.length]; }),
            height: 200,
            label: definition.titre
          });
        }
      }).catch(function () {
        cible.sous.textContent = "Indisponible";
        cible.zone.textContent = "";
        cible.zone.appendChild(elt("p", "ws-empty", "Graphique indisponible pour le moment."));
      });
    });
  }

  function demarrer() {
    var section = $("tab-reports");
    if (!section) return;

    var chargerSiVisible = function () {
      if (section.classList.contains("hidden")) return;
      construire(section);
    };
    window.addEventListener("hashchange", function () { setTimeout(chargerSiVisible, 60); });
    setTimeout(chargerSiVisible, 600);

  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }

  window.UniOCRRapports = { graphiques: GRAPHIQUES };
})();
