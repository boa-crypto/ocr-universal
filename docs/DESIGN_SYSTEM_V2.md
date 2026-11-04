# Design System UniOCR

**Version** : 2.0  
**Date** : 2026-10-28  
**Fichier source** : `web/styles.css` (section `:root` et `[data-theme="light"]`)

---

## Principes Directeurs

1. **Précision visuelle** : chaque couleur a un rôle sémantique, pas décoratif
2. **Cohérence thématique** : même système pour dark et light
3. **Performance** : tokens CSS réutilisables, zéro duplication
4. **Accessibilité** : contrastes vérifiés WCAG AA minimum

---

## Tokens de Couleurs

### Dark Theme (défaut)

| Token | Valeur | Nom | Usage |
|-------|--------|-----|-------|
| `--obsidian` | `#101A19` | Noir profond | Background principal, sidebar |
| `--graphite` | `#192624` | Gris ardoise | Surfaces (cards, panels, boutons) |
| `--mineral` | `#2B3B38` | Gris minéral | Bordures principales |
| `--ivory` | `#F4F7F5` | Blanc cassé | Alias de `--text` |
| `--silver` | `#A9B8B2` | Argent | Bordures secondaires |
| `--electric` | `#83D3C3` | Cyan électrique | Accent principal |
| `--cyan` | `#E0A17D` | Cuivre | Accent secondaire |
| `--blue-accent` | `#5F78FF` | Bleu accent | Gradients, highlights, badges |
| `--ink-dark` | `#0B0E14` | Encre foncée | Texte sur fonds clairs/gradient |
| `--ink-neutral` | `#0A0C10` | Encre neutre | Texte quasi-noir (lang-btn) |
| `--bg-deep` | `#0B1413` | Noir profond | Background secondaire (sidebar) |
| `--surface-2` | `#202F2C` | Surface second | Sous-fonds, segments |
| `--text` | `#F4F7F5` | Texte principal | Corps de texte |
| `--text-2` | `#D1DDD7` | Texte secondaire | Labels, métadonnées |
| `--muted` | `#B3C1BB` | Atténué | Texte tertiaire |
| `--faint` | `#9AA9A2` | Effacé | Placeholders, hints |
| `--ok` | `#7BD1A1` | Succès | Validations, confirms |
| `--warn` | `#F0C36A` | Avertissement | Alerts, pending |
| `--err` | `#F08A7B` | Erreur | Errors, refus |

### Light Theme

| Token | Valeur | Note |
|-------|--------|------|
| `--bg` | `#F2F6F4` | Fond clair |
| `--bg-deep` | `#E8EFEB` | Fond secondaire |
| `--surface` | `#FFFFFF` | Surfaces blanches |
| `--surface-2` | `#EAF0ED` | Sous-fonds clairs |
| `--text` | `#1C2B26` | Texte principal sombre |
| `--text-2` | `#33453E` | Texte secondaire |
| `--muted` | `#52645C` | Atténué |
| `--faint` | `#5D6E66` | Effacé |
| `--electric` | `#126B61` | Cyan plus saturé |
| `--cyan` | `#B95E3C` | Cuivre plus soutenu |
| `--ok` | `#23744A` | Vert succès |
| `--warn` | `#895A08` | Orange avertissement |
| `--err` | `#A73C32` | Rouge erreur |

> **Note** : Les tokens `--ink-dark`, `--ink-light`, `--ink-neutral`, `--blue-accent` sont identiques dans les deux thèmes.

---

## Typographie

| Token | Police | Usage |
|-------|--------|-------|
| `--font-display` | `Instrument Serif` | Titres, branding, chiffres grands |
| `--font-ui` | `Inter` | Interface, corps de texte |
| `--font-mono` | `JetBrains Mono` | Code, données techniques, IDs |

### Tailles (à ajouter si manquant)

| Niveau | Valeur | Usage |
|--------|--------|-------|
| xs | 11px | Labels, badges, hints |
| sm | 12.5px | Boutons secondaires |
| base | 14px | Corps standard |
| lg | 16px | Sous-titres |
| xl | 19px | Titres de section |
| 2xl | 24px | Titres de page |
| display | 42px | Chiffres statistiques |

---

## Espacements

| Token | Valeur | Usage |
|-------|--------|-------|
| `--xs` | 4px | Micro-espacements |
| `--sm` | 8px | Espacements serrés |
| `--md` | 12px | Espacements standards |
| `--lg` | 16px | Espacements normaux |
| `--xl` | 24px | Sections |
| `--2xl` | 32px | Grands gaps |
| `--3xl` | 48px | Hero sections |
| `--4xl` | 64px | Espacements majeurs |

---

## Rayons

| Token | Valeur | Usage |
|-------|--------|-------|
| `--r-xs` | 3px | Pins, badges ronds |
| `--r-sm` | 5px | Boutons petits |
| `--r-md` | 8px | Default (cards, panels) |
| `--r-lg` | 8px | Même que md (cohérence) |
| `--r` | 8px | Alias default |

---

## Ombres

| Token | Valeur | Usage |
|-------|--------|-------|
| `--shadow-1` | `0 1px 2px rgba(0,0,0,.18)` | Élément léger |
| `--shadow-2` | `0 12px 32px rgba(0,0,0,.24)` | Carte, modal |
| `--shadow-glow` | `0 0 0 1px color-mix(accent,32%), 0 6px 22px color-mix(accent,10%)` | Accent glow |

---

## Z-Index Scale

| Niveau | Valeur | Usage |
|--------|--------|-------|
| `--z-base` | 0 | Contenu normal |
| `--z-sidebar` | 40 | Barre latérale |
| `--z-dropdown` | 1000 | Menus déroulants |
| `--z-modal-backdrop` | 1300 | Voile modal |
| `--z-modal` | 1400 | Contenu modal |
| `--z-toast` | 1700 | Notifications |

> À ajouter aux tokens si besoin de nouveaux éléments empilés.

---

## Transitions

| Token | Valeur | Usage |
|-------|--------|-------|
| `--dur` | `0.18s` | Durée standard |
| `--ease` | `cubic-bezier(.2, .7, .2, 1)` | Ease out |

---

## Composants — Usage des Tokens

### Boutons
```css
.btn {
  background: linear-gradient(135deg, var(--electric), var(--blue-accent));
  color: var(--ink-dark);
}
.btn.ghost {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--muted);
}
```

### Badges et Statuts
```css
.badge.done    { /* vert */ }
.badge.processing { /* orange */ }
.badge.error   { /* rouge */ }
.badge.validated { /* teal */ }
.badge.info    { /* bleu accent */ }
.badge.warn    { /* orange */ }
```

### Cartes et Panneaux
```css
.card, .panel {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
}
```

### Champs de saisie
```css
.inp, .edit {
  background: var(--surface-2);
  border: 1px solid var(--line);
  color: var(--text);
}
.inp:focus, .edit:focus {
  border-color: var(--accent);
  outline: none;
}
```

---

## Règles d'Utilisation

1. **Jamais de couleur hex brute** dans les sélecteurs — utiliser `var(--token)`
2. **Fallbacks autorisés** seulement pour `.var(--token, default)` quand la backward compatibilité l'exige
3. **Couleurs sémantiques** (`--ok`, `--warn`, `--err`) ne jamais être mélangées avec des couleurs décoratives
4. **Thèmes** : chaque token doit avoir une définition dans `:root` ET `[data-theme="light"]`
5. **Gradients** : utiliser `color-mix()` pour les opacités plutôt que des hex with alpha

---

## Évolution

Ce design system est vivant. Toute nouvelle couleur ajoutée doit :
1. Être justifiée par un usage métier (pas décoratif)
2. Être définie dans les deux thèmes (dark + light)
3. Être documentée ici
4. Passer les tests de contraste WCAG AA
