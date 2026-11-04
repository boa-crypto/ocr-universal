/**
 * UniOCR — micro-bibliothèque de graphiques SVG (sans dépendance)
 * ---------------------------------------------------------------------------
 * Trois visualisations suffisent au cockpit : courbes (évolution), anneau
 * (répartition) et étincelle (KPI). Aucune bibliothèque externe n'est
 * chargée : le poste fonctionne hors ligne et le rendu reste net à toute
 * résolution.
 *
 * Les animations sont neutralisées quand `prefers-reduced-motion` est actif.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";

  function reduit() {
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) {
      return false;
    }
  }

  function el(nom, attrs) {
    var noeud = document.createElementNS(NS, nom);
    if (attrs) {
      Object.keys(attrs).forEach(function (cle) {
        noeud.setAttribute(cle, String(attrs[cle]));
      });
    }
    return noeud;
  }

  function nombre(valeur) {
    var n = Number(valeur);
    return isFinite(n) ? n : 0;
  }

  function formatCourt(valeur) {
    var n = nombre(valeur);
    if (Math.abs(n) >= 1000) return (n / 1000).toFixed(n % 1000 === 0 ? 0 : 1) + "k";
    return String(Math.round(n));
  }

  function animerTrait(chemin, duree) {
    if (!chemin || reduit()) return;
    var longueur = 0;
    try { longueur = chemin.getTotalLength(); } catch (e) { longueur = 0; }
    if (!longueur) return;
    chemin.style.strokeDasharray = String(longueur);
    chemin.style.strokeDashoffset = String(longueur);
    chemin.getBoundingClientRect();
    chemin.style.transition = "stroke-dashoffset " + duree + "ms cubic-bezier(.22,1,.36,1)";
    chemin.style.strokeDashoffset = "0";
  }

  /* ── Courbes multi-séries ─────────────────────────────────────────── */
  function line(hote, options) {
    if (!hote) return null;
    var opts = options || {};
    var labels = opts.labels || [];
    var series = (opts.series || []).filter(function (s) { return s && s.values; });
    var largeur = opts.width || Math.max(320, hote.clientWidth || 560);
    var hauteur = opts.height || 220;
    var marge = { haut: 14, droite: 12, bas: 26, gauche: 38 };
    var zoneL = largeur - marge.gauche - marge.droite;
    var zoneH = hauteur - marge.haut - marge.bas;

    var maxi = 1;
    series.forEach(function (s) {
      s.values.forEach(function (v) { maxi = Math.max(maxi, nombre(v)); });
    });
    maxi = Math.ceil(maxi / 5) * 5 || 5;

    var svg = el("svg", {
      class: "chart-svg",
      viewBox: "0 0 " + largeur + " " + hauteur,
      role: "img",
      "aria-label": opts.label || "Graphique"
    });

    var defs = el("defs");
    var grad = el("linearGradient", { id: "dsAreaGradient", x1: "0", y1: "0", x2: "0", y2: "1" });
    grad.appendChild(el("stop", { offset: "0", "stop-color": "#1677FF", "stop-opacity": "0.38" }));
    grad.appendChild(el("stop", { offset: "1", "stop-color": "#1677FF", "stop-opacity": "0" }));
    defs.appendChild(grad);
    svg.appendChild(defs);

    var grille = el("g", { class: "chart-grid" });
    for (var i = 0; i <= 4; i += 1) {
      var y = marge.haut + (zoneH * i) / 4;
      grille.appendChild(el("line", { x1: marge.gauche, y1: y, x2: largeur - marge.droite, y2: y }));
    }
    svg.appendChild(grille);

    var axe = el("g", { class: "chart-axis" });
    for (var j = 0; j <= 4; j += 1) {
      var yy = marge.haut + (zoneH * j) / 4;
      var txt = el("text", { x: marge.gauche - 8, y: yy + 3.5, "text-anchor": "end" });
      txt.textContent = formatCourt(maxi - (maxi * j) / 4);
      axe.appendChild(txt);
    }
    var pas = Math.max(1, Math.ceil(labels.length / 6));
    labels.forEach(function (libelle, index) {
      if (index % pas !== 0 && index !== labels.length - 1) return;
      var x = marge.gauche + (labels.length === 1 ? zoneL / 2 : (zoneL * index) / (labels.length - 1));
      var t = el("text", { x: x, y: hauteur - 8, "text-anchor": "middle" });
      t.textContent = String(libelle).slice(5);
      axe.appendChild(t);
    });
    svg.appendChild(axe);

    series.forEach(function (serie) {
      var points = serie.values.map(function (valeur, index) {
        var x = marge.gauche + (serie.values.length === 1
          ? zoneL / 2
          : (zoneL * index) / (serie.values.length - 1));
        var y = marge.haut + zoneH - (nombre(valeur) / maxi) * zoneH;
        return [x, y];
      });
      if (!points.length) return;

      var chemin = points.map(function (p, index) {
        return (index === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1);
      }).join(" ");

      if (serie.fill) {
        var aire = chemin + " L" + points[points.length - 1][0].toFixed(1) + " " +
          (marge.haut + zoneH) + " L" + points[0][0].toFixed(1) + " " + (marge.haut + zoneH) + " Z";
        svg.appendChild(el("path", { d: aire, class: "chart-area" }));
      }

      var trait = el("path", {
        d: chemin,
        class: "chart-line" + (serie.variant ? " chart-line--" + serie.variant : "")
      });
      if (serie.color) trait.style.stroke = serie.color;
      svg.appendChild(trait);
      animerTrait(trait, opts.duration || 720);

      if (opts.dots !== false && points.length <= 40) {
        points.forEach(function (p) {
          var dot = el("circle", { cx: p[0], cy: p[1], r: 2.6, class: "chart-dot" });
          if (serie.color) dot.style.stroke = serie.color;
          dot.appendChild(el("title")).textContent = "";
          svg.appendChild(dot);
        });
      }
    });

    hote.textContent = "";
    hote.appendChild(svg);
    return svg;
  }

  /* ── Barres verticales ───────────────────────────────────────────── */
  function bars(hote, options) {
    if (!hote) return null;
    var opts = options || {};
    var labels = opts.labels || [];
    var valeurs = (opts.values || []).map(nombre);
    if (!labels.length || !valeurs.length) {
      hote.textContent = "";
      return null;
    }
    var largeur = opts.width || Math.max(320, hote.clientWidth || 520);
    var hauteur = opts.height || 210;
    var marge = { haut: 12, droite: 10, bas: 30, gauche: 34 };
    var zoneL = largeur - marge.gauche - marge.droite;
    var zoneH = hauteur - marge.haut - marge.bas;
    var maxi = Math.max.apply(null, valeurs.concat([1]));
    var pas = zoneL / valeurs.length;
    var largeurBarre = Math.max(6, Math.min(38, pas * 0.55));

    var svg = el("svg", {
      class: "chart-svg",
      viewBox: "0 0 " + largeur + " " + hauteur,
      role: "img",
      "aria-label": opts.label || "Histogramme"
    });

    var grille = el("g", { class: "chart-grid" });
    for (var i = 0; i <= 3; i += 1) {
      var y = marge.haut + (zoneH * i) / 3;
      grille.appendChild(el("line", { x1: marge.gauche, y1: y, x2: largeur - marge.droite, y2: y }));
    }
    svg.appendChild(grille);

    var axe = el("g", { class: "chart-axis" });
    for (var j = 0; j <= 3; j += 1) {
      var yy = marge.haut + (zoneH * j) / 3;
      var txt = el("text", { x: marge.gauche - 8, y: yy + 3.5, "text-anchor": "end" });
      txt.textContent = formatCourt(maxi - (maxi * j) / 3);
      axe.appendChild(txt);
    }
    svg.appendChild(axe);

    valeurs.forEach(function (valeur, index) {
      var h = (valeur / maxi) * zoneH;
      var x = marge.gauche + pas * index + (pas - largeurBarre) / 2;
      var rect = el("rect", {
        x: x, y: marge.haut + zoneH - h, width: largeurBarre, height: Math.max(2, h),
        rx: 4, class: "chart-bar"
      });
      if (opts.colors && opts.colors[index]) rect.style.fill = opts.colors[index];
      var titre = el("title");
      titre.textContent = labels[index] + " : " + formatCourt(valeur);
      rect.appendChild(titre);
      if (!reduit()) {
        rect.style.transformOrigin = (x + largeurBarre / 2) + "px " + (marge.haut + zoneH) + "px";
        rect.style.transform = "scaleY(0.02)";
        rect.style.transition = "transform 620ms cubic-bezier(.22,1,.36,1) " + (index * 40) + "ms";
        requestAnimationFrame(function () { rect.style.transform = "scaleY(1)"; });
      }
      svg.appendChild(rect);
    });

    var labelsG = el("g", { class: "chart-axis" });
    var saut = Math.max(1, Math.ceil(labels.length / 7));
    labels.forEach(function (libelle, index) {
      if (index % saut !== 0 && index !== labels.length - 1) return;
      var t = el("text", {
        x: marge.gauche + pas * index + pas / 2,
        y: hauteur - 9,
        "text-anchor": "middle"
      });
      t.textContent = String(libelle).length > 14 ? String(libelle).slice(0, 13) + "…" : String(libelle);
      labelsG.appendChild(t);
    });
    svg.appendChild(labelsG);

    hote.textContent = "";
    hote.appendChild(svg);
    return svg;
  }

  /* ── Étincelle (KPI) ──────────────────────────────────────────────── */
  function sparkline(hote, valeurs, options) {
    if (!hote) return null;
    var opts = options || {};
    var data = (valeurs || []).map(nombre);
    if (data.length < 2) {
      hote.textContent = "";
      return null;
    }
    var l = opts.width || 64;
    var h = opts.height || 28;
    var maxi = Math.max.apply(null, data) || 1;
    var mini = Math.min.apply(null, data);
    var etendue = Math.max(1, maxi - mini);

    var svg = el("svg", { class: "chart-svg", width: l, height: h, viewBox: "0 0 " + l + " " + h, "aria-hidden": "true" });
    var points = data.map(function (v, i) {
      var x = (l * i) / (data.length - 1);
      var y = h - 3 - ((v - mini) / etendue) * (h - 6);
      return [x, y];
    });
    var d = points.map(function (p, i) {
      return (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1);
    }).join(" ");
    var trait = el("path", { d: d, class: "chart-line", style: "stroke-width:1.8" });
    if (opts.color) trait.style.stroke = opts.color;
    svg.appendChild(trait);
    animerTrait(trait, 520);
    hote.textContent = "";
    hote.appendChild(svg);
    return svg;
  }

  /* ── Anneau ───────────────────────────────────────────────────────── */
  function donut(hote, options) {
    if (!hote) return null;
    var opts = options || {};
    var items = (opts.items || []).filter(function (i) { return nombre(i.value) > 0; });
    var taille = opts.size || 176;
    var rayon = taille / 2 - 12;
    var circonference = 2 * Math.PI * rayon;

    var svg = el("svg", {
      class: "chart-svg",
      viewBox: "0 0 " + taille + " " + taille,
      width: taille,
      height: taille,
      role: "img",
      "aria-label": opts.label || "Répartition"
    });

    svg.appendChild(el("circle", {
      cx: taille / 2, cy: taille / 2, r: rayon, fill: "none",
      stroke: "rgba(122,168,255,.12)", "stroke-width": 14
    }));

    var total = items.reduce(function (somme, i) { return somme + nombre(i.value); }, 0) || 1;
    var offset = 0;
    items.forEach(function (item) {
      var part = nombre(item.value) / total;
      var arc = el("circle", {
        cx: taille / 2, cy: taille / 2, r: rayon, fill: "none",
        stroke: item.color || "#1677FF", "stroke-width": 14,
        "stroke-dasharray": (circonference * part).toFixed(2) + " " + circonference.toFixed(2),
        "stroke-dashoffset": (-circonference * offset).toFixed(2),
        "stroke-linecap": "butt",
        transform: "rotate(-90 " + taille / 2 + " " + taille / 2 + ")"
      });
      if (!reduit()) {
        arc.style.opacity = "0";
        arc.style.transition = "opacity 420ms cubic-bezier(.22,1,.36,1) " + (offset * 420) + "ms";
        requestAnimationFrame(function () { arc.style.opacity = "1"; });
      }
      svg.appendChild(arc);
      offset += part;
    });

    var centreNombre = el("text", {
      x: taille / 2, y: taille / 2 + 2, "text-anchor": "middle",
      fill: "#F1F5FF", "font-size": 24, "font-weight": 700,
      "font-family": "Inter, system-ui, sans-serif"
    });
    centreNombre.textContent = String(total);
    svg.appendChild(centreNombre);
    var centreLabel = el("text", {
      x: taille / 2, y: taille / 2 + 22, "text-anchor": "middle",
      fill: "#94A9C7", "font-size": 10.5, "font-family": "Inter, system-ui, sans-serif"
    });
    centreLabel.textContent = opts.centre || "dossiers";
    svg.appendChild(centreLabel);

    hote.textContent = "";
    hote.appendChild(svg);

    if (opts.legend !== false) {
      var legende = document.createElement("div");
      legende.className = "chart-legend";
      legende.style.marginTop = "10px";
      items.forEach(function (item) {
        var span = document.createElement("span");
        var puce = document.createElement("i");
        puce.style.background = item.color || "#1677FF";
        span.appendChild(puce);
        span.appendChild(document.createTextNode(item.label + " · " + nombre(item.value)));
        legende.appendChild(span);
      });
      hote.appendChild(legende);
    }
    return svg;
  }

  window.UniOCRCharts = { line: line, donut: donut, bars: bars, sparkline: sparkline, reduit: reduit };
})();
