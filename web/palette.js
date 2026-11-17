/**
 * UniOCR — passerelle de palette pour les rendus non-CSS
 * ---------------------------------------------------------------------------
 * Les graphiques SVG écrivent des attributs de présentation (`fill`,
 * `stop-color`, `stroke`…) où `var(--ds-blue)` n'est pas résolu de façon
 * fiable. Ce module lit donc les jetons du design system **une seule fois**
 * dans `getComputedStyle` : les valeurs restent définies dans `uniocr-ds.css`,
 * aucun composant JavaScript ne connaît de code couleur.
 *
 * Si un jeton manque (feuille non chargée), on renvoie un secours neutre
 * (`currentColor`) plutôt qu'une valeur inventée ; la lecture n'est alors pas
 * mise en cache, pour reprendre la bonne valeur dès que le CSS est disponible.
 *
 * `couleur("blue")`     → valeur de `--ds-blue`
 * `couleur("--ds-blue")` → idem, par nom de jeton brut
 */
(function () {
  "use strict";

  var JETONS = {
    night: "--ds-night",
    sidebar: "--ds-sidebar",
    surface: "--ds-surface",
    surface2: "--ds-surface-2",
    blue: "--ds-blue",
    cyan: "--ds-cyan",
    teal: "--ds-teal",
    violet: "--ds-violet",
    amber: "--ds-amber",
    red: "--ds-red",
    green: "--ds-green",
    neutral: "--ds-neutral",
    text: "--ds-text",
    text2: "--ds-text-2",
    muted: "--ds-text-muted",
    faint: "--ds-text-faint",
    line: "--ds-line",
    lineStrong: "--ds-line-strong"
  };

  var cache = {};

  function couleur(nom, secours) {
    var jeton = JETONS[nom] || nom;
    if (typeof jeton !== "string" || jeton.charAt(0) !== "-") {
      return secours || "currentColor";
    }
    if (Object.prototype.hasOwnProperty.call(cache, jeton)) return cache[jeton];
    var valeur = "";
    try {
      valeur = window.getComputedStyle(document.documentElement)
        .getPropertyValue(jeton).trim();
    } catch (e) {
      valeur = "";
    }
    if (!valeur) return secours || "currentColor";
    cache[jeton] = valeur;
    return valeur;
  }

  /** Série ordinale stable (graphiques multi-catégories). */
  function serie() {
    return ["blue", "cyan", "teal", "violet", "amber", "red", "neutral"].map(function (nom) {
      return couleur(nom);
    });
  }

  window.UniOCRPalette = { couleur: couleur, serie: serie, jetons: JETONS };
})();
