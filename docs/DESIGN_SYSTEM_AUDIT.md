# UniOCR Design System - Audit Complet
**Date**: 2026-10-23  
**Version actuelle**: CSS embarqué (styles.css, 490KB)  
**Statut**: Analyse terminée

---

## 📊 ÉTAT ACTUEL

### ✅ Fondations solides découvertes

#### Tokens CSS existants (`:root`)

**Couleurs nommées** (palette de base):
```css
--obsidian: #101A19   /* Noir profond */
--graphite: #192624   /* Gris foncé */
--mineral:  #2B3B38   /* Gris moyen */
--ivory:    #F4F7F5   /* Blanc cassé */
--silver:   #A9B8B2   /* Gris clair */
--electric: #83D3C3   /* Cyan/Turquoise (accent) */
--cyan:     #E0A17D   /* Cuivre/Orange */
```

**Couleurs sémantiques**:
```css
--bg:        #101A19   /* Background principal */
--bg-deep:   #0B1413   /* Background profond */
--surface:   #192624   /* Surfaces (cards, panels) */
--line:      rgba(190, 207, 199, .17)  /* Bordures */
--line-soft: rgba(190, 207, 199, .10)  /* Bordures légères */
--text:      #F4F7F5   /* Texte principal */
--muted:     #B3C1BB   /* Texte secondaire */
--faint:     #9AA9A2   /* Texte tertiaire */

--ok:   #7BD1A1  /* Succès (vert) */
--warn: #F0C36A  /* Warning (jaune) */
--err:  #F08A7B  /* Erreur (rouge) */

--accent: var(--electric)  /* Accent = electric cyan */
```

**Typographie**:
```css
--font-display: "Instrument Serif", ui-serif, Georgia, serif
  /* Pour les titres élégants, éditorial */

--font-ui: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif
  /* Pour l'interface, corps de texte */

--font-mono: "JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Code", monospace
  /* Pour le code, données techniques */
```

**Spacing** (échelle cohérente):
```css
--xs: 4px
--sm: 8px
--md: 12px
--lg: 16px
--xl: 24px
```

**Border radius**:
```css
--r-xs: 3px
--r-sm: 5px
--r-md: 8px
--r-lg: 8px  /* Note: même valeur que md */
--r: 8px     /* Default */
```

**Layout**:
```css
--sidebar-w: 248px
--topbar-h: 68px
```

**Shadow** (effet glow sur accent):
```css
--shadow-glow: 0 0 0 1px color-mix(in srgb, var(--accent) 32%, transparent), 
               0 6px 22px color-mix(in srgb, var(--accent) 10%, transparent)
```

---

## ⚠️ PROBLÈMES IDENTIFIÉS

### 1. Prolifération de couleurs (Critique)

**76 couleurs hex uniques** dans le CSS au lieu d'utiliser les tokens.

**Exemples de duplication**:
- `#101A19` (obsidian) réutilisé directement au lieu de `var(--obsidian)`
- `#192624` (graphite) en dur au lieu de `var(--graphite)`
- Dizaines de variations de gris sans token correspondant

**Impact**:
- ❌ Incohérence visuelle
- ❌ Maintenance difficile
- ❌ Impossible de themer facilement
- ❌ Pas de garantie de cohérence dark/light

### 2. Light theme incomplet

**Trouvé**: Uniquement le dark theme est défini  
**Manque**: Section `[data-theme="light"]` complète

**Conséquence**: Le light mode n'utilise probablement pas les tokens sémantiques optimaux.

### 3. Tokens manquants

**Spacing**:
- ✅ xs, sm, md, lg, xl définis
- ❌ Manque: 2xl, 3xl pour grands espaces
- ❌ Pas de scale négative pour overlap

**Radius**:
- ❌ `--r-md` et `--r-lg` ont la même valeur (8px)
- ❌ Manque: radius xl (16px+) pour grands panels
- ❌ Manque: radius full (9999px) pour pills/avatars

**Shadows**:
- ✅ `--shadow-glow` défini
- ❌ Manque: shadow-sm, shadow-md, shadow-lg (élévation)
- ❌ Pas de shadow tokens pour dark mode distinct

**Transitions**:
- ❌ Aucun token de durée/easing
- ❌ Transitions définies inline partout

**Z-index**:
- ❌ Pas de scale z-index documentée
- ❌ Risque de conflits d'empilement

### 4. Inconsistances

**Nommage**:
- `--cyan` contient du orange/cuivre (`#E0A17D`) 🤔
- `--electric` est le vrai cyan (`#83D3C3`)
- Confusion potentielle

**Hiérarchie**:
- Pas de tokens pour tailles de texte (font-size)
- Pas de tokens pour hauteurs de ligne (line-height)
- Pas de tokens pour poids (font-weight)

**Sémantique**:
- `--fg`, `--dim` définis mais peu utilisés
- Couleurs sémantiques (`--ok`, `--warn`, `--err`) pas de variantes (light/dark)

---

## 🎯 PLAN D'OPTIMISATION

### Phase 2A.1 - Consolidation des couleurs (Priorité 1)

**Objectif**: 76 couleurs → 25 couleurs max

**Actions**:
1. Identifier les couleurs "core" (les 20 plus utilisées)
2. Créer des tokens pour chaque couleur core manquante
3. Remplacer TOUS les hex directs par `var(--token)`
4. Supprimer les couleurs one-off

**Stratégie de remplacement**:
```css
/* Avant */
background: #101A19;
color: #F4F7F5;

/* Après */
background: var(--obsidian);
color: var(--ivory);
```

**Script Python**: Automatiser le remplacement

### Phase 2A.2 - Complétion des tokens (Priorité 1)

**Ajouter**:

**Spacing étendu**:
```css
--space-2xs: 2px   /* Micro-spacing */
--space-xs: 4px    /* Existant */
--space-sm: 8px    /* Existant */
--space-md: 12px   /* Existant */
--space-lg: 16px   /* Existant */
--space-xl: 24px   /* Existant */
--space-2xl: 32px  /* Grands gaps */
--space-3xl: 48px  /* Hero sections */
--space-4xl: 64px  /* Espacements majeurs */
```

**Radius corrigés**:
```css
--radius-sm: 4px      /* Petits éléments */
--radius-md: 8px      /* Default (existant --r) */
--radius-lg: 12px     /* Cards, panels */
--radius-xl: 16px     /* Modals, grandes surfaces */
--radius-2xl: 24px    /* Hero, images */
--radius-full: 9999px /* Pills, avatars, badges ronds */
```

**Shadows élévation**:
```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05)
--shadow-md: 0 4px 6px rgba(0,0,0,0.07)
--shadow-lg: 0 10px 15px rgba(0,0,0,0.1)
--shadow-xl: 0 20px 25px rgba(0,0,0,0.15)
--shadow-2xl: 0 25px 50px rgba(0,0,0,0.25)
```

**Transitions**:
```css
--duration-fast: 150ms
--duration-base: 250ms
--duration-slow: 350ms
--duration-slower: 500ms
--easing-default: cubic-bezier(0.4, 0, 0.2, 1)  /* ease-out */
--easing-in: cubic-bezier(0.4, 0, 1, 1)
--easing-out: cubic-bezier(0, 0, 0.2, 1)
--easing-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55)
```

**Z-index scale**:
```css
--z-base: 0
--z-dropdown: 1000
--z-sticky: 1100
--z-fixed: 1200
--z-modal-backdrop: 1300
--z-modal: 1400
--z-popover: 1500
--z-tooltip: 1600
--z-toast: 1700
```

**Typography scale**:
```css
/* Sizes */
--text-xs: 0.75rem   /* 12px */
--text-sm: 0.875rem  /* 14px */
--text-base: 1rem    /* 16px */
--text-lg: 1.125rem  /* 18px */
--text-xl: 1.25rem   /* 20px */
--text-2xl: 1.5rem   /* 24px */
--text-3xl: 1.875rem /* 30px */
--text-4xl: 2.25rem  /* 36px */
--text-5xl: 3rem     /* 48px */

/* Line heights */
--leading-none: 1
--leading-tight: 1.25
--leading-snug: 1.375
--leading-normal: 1.5
--leading-relaxed: 1.625
--leading-loose: 2

/* Weights */
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

### Phase 2A.3 - Light theme complet (Priorité 1)

**Créer une section `[data-theme="light"]`** cohérente:

```css
[data-theme="light"] {
  /* Backgrounds */
  --bg: #FFFFFF;
  --bg-deep: #F8F9FA;
  --surface: #FFFFFF;
  
  /* Borders */
  --line: rgba(0, 0, 0, 0.1);
  --line-soft: rgba(0, 0, 0, 0.05);
  
  /* Text */
  --text: #1A1A1A;
  --muted: #6B6B6B;
  --faint: #9B9B9B;
  
  /* Semantic colors (ajustés pour light) */
  --ok: #0A8754;
  --warn: #D97706;
  --err: #DC2626;
  
  /* Accent conservé mais possiblement ajusté */
  --accent: #14B8A6;  /* Turquoise plus saturé pour light */
  
  /* Shadows plus visibles en light */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
}
```

### Phase 2A.4 - Renommage cohérent (Priorité 2)

**Problème**: `--cyan` contient du orange

**Solution**: Renommer pour clarté
```css
/* Avant */
--electric: #83D3C3  /* cyan/turquoise */
--cyan: #E0A17D      /* cuivre/orange (!!) */

/* Après */
--primary: #83D3C3   /* Cyan principal */
--copper: #E0A17D    /* Cuivre/accent chaud */
--accent: var(--primary)  /* Par défaut = primary */
```

Ou garder les noms actuels mais documenter clairement.

### Phase 2A.5 - Documentation (Priorité 2)

**Créer**: `docs/DESIGN_SYSTEM.md`

**Contenu**:
1. Vue d'ensemble
2. Palette de couleurs (avec preview)
3. Typographie (échelle + exemples)
4. Spacing (scale + usage)
5. Composants (documentation + exemples)
6. Guidelines (do's and don'ts)
7. Accessibilité (contrastes WCAG)

---

## 📈 MÉTRIQUES D'AMÉLIORATION

### Avant optimisation
- **Couleurs**: 76 uniques (non contrôlées)
- **Tokens utilisés**: ~30% du CSS
- **Light theme**: Incomplet
- **Documentation**: Aucune
- **Cohérence**: Moyenne

### Après optimisation (cibles)
- **Couleurs**: ≤25 (100% via tokens)
- **Tokens utilisés**: 95% du CSS
- **Light theme**: Complet et optimisé
- **Documentation**: DESIGN_SYSTEM.md complet
- **Cohérence**: Élevée

---

## 🚀 PROCHAINES ACTIONS

### Immédiat (aujourd'hui)
1. ✅ Analyser fréquence d'usage des couleurs
2. ⏳ Créer tokens pour top 20 couleurs
3. ⏳ Script de remplacement automatique
4. ⏳ Compléter les tokens manquants

### Demain
5. ⏳ Implémenter light theme complet
6. ⏳ Moderniser composants prioritaires
7. ⏳ Raffiner animations
8. ⏳ Documenter le système

---

**Mise à jour**: 2026-10-23 23:24 UTC  
**Progression**: Audit terminé, implémentation commencée
