# UniOCR Design System v3 — Future Precision Intelligence
**Date** : 2026-10-28  
**Direction Artistique** : Atelier Haute Précision (Obsidian & Jade)  
**Standard** : Enterprise SaaS International Premium (WCAG AA/AAA)

---

## 1. Philosophie & Direction Artistique

UniOCR incarne l'esthétique d'un instrument de laboratoire optique moderne croisé avec la rigueur éditoriale helvétique.
* **Sobriété et Densité** : Chaque pixel sert la lisibilité documentaire et la vérification humaine. Zéro fioriture superflue, zéro effet "AI template".
* **Surfaces Stratifiées** : 3 niveaux de profondeur visuelle (`surface-1` pour les cartes, `surface-2` pour les conteneurs de formulaire, `surface-3` pour les contrôles insérés).
* **Signaux Chromatiques Intentionnels** :
  - **Émeraude / Jade Électrique** (`#10B981` / `#5EEAD4`) : Confirmation, intégrité, statut optimal.
  - **Ambre Doré** (`#F59E0B`) : Attention requise, ambiguïté, révision nécessaire.
  - **Rubis / Corail Foncier** (`#F43F5E`) : Anomalie critique, champ invalide, rejet de transmission.
  - **Indigo Impérial** (`#6366F1`) : Gradients dynamiques et surbrillances ciblées.

---

## 2. Système de Tokens CSS

### 2.1 Couleurs & Thèmes

#### Thème Sombre (Atelier Nocturne - Défaut)
```css
:root {
  /* Nuances Fondamentales */
  --obsidian:    #0B1211;  /* Noir abyssal - Fond global */
  --graphite:    #121D1B;  /* Ardoise sombre - Surface 1 (Cartes/Panels) */
  --mineral:     #1C2D2A;  /* Minéral profond - Surface 2 (Champs/Tables) */
  --mineral-sub: #253A36;  /* Minéral supérieur - Surface 3 (Badges/Pills) */
  --ivory:       #F8FAFC;  /* Craie pure - Texte principal */
  --silver:      #94A3B8;  /* Argent doux - Texte secondaire */
  --faint:       #64748B;  /* Brume - Métadonnées & indices */

  /* Bordures et Lignes */
  --line:        rgba(180, 215, 205, 0.12);
  --line-soft:   rgba(180, 215, 205, 0.07);
  --line-glow:   rgba(94, 234, 212, 0.35);

  /* Accents Primaires */
  --electric:    #5EEAD4;  /* Cyan / Jade électrique */
  --cyan:        #F59E0B;  /* Ambre / Cuivre chaleureux */
  --blue-accent: #6366F1;  /* Indigo pour gradients et highlights */

  /* Texte & Contrastes */
  --ink-dark:    #06100E;  /* Texte sur bouton contrasté */
  --ink-light:   #FFFFFF;  /* Blanc absolu */
  --ink-neutral: #0B1211;  /* Neutre sombre */

  /* Sémantique Métier */
  --ok:          #34D399;  /* Vert validation */
  --warn:        #FBBF24;  /* Jaune / Ambre avertissement */
  --err:         #F87171;  /* Rouge alerte */

  /* Ombres & Lueurs */
  --shadow-1:    0 1px 3px rgba(0, 0, 0, 0.40);
  --shadow-2:    0 12px 36px rgba(0, 0, 0, 0.50), 0 0 1px rgba(255, 255, 255, 0.08);
  --shadow-glow: 0 0 0 1px rgba(94, 234, 212, 0.30), 0 8px 28px rgba(94, 234, 212, 0.12);
}
```

#### Thème Clair (Porcelaine & Encre Slate)
```css
[data-theme="light"] {
  --bg:          #F8FAFC;  /* Alabaster soyeux */
  --bg-deep:     #EDF2F7;  /* Gris froid profond pour sidebar */
  --surface:     #FFFFFF;  /* Blanc pur pour cartes et fiches */
  --surface-2:   #F1F5F9;  /* Gris clair pour champs */
  --line:        rgba(15, 23, 42, 0.09);
  --line-soft:   rgba(15, 23, 42, 0.05);
  --text:        #0F172A;  /* Encre noire douce */
  --text-2:      #334155;  /* Anthracite */
  --muted:       #475569;  /* Gris moyen lisible */
  --faint:       #64748B;  /* Gris clair */
  --electric:    #0D9488;  /* Émeraude profond contrasté */
  --cyan:        #D97706;  /* Ambre chaud */
  --accent:      #0D9488;
  --accent-2:    #D97706;
  --ok:          #059669;
  --warn:        #D97706;
  --err:         #DC2626;
  --shadow-1:    0 1px 3px rgba(15, 23, 42, 0.05);
  --shadow-2:    0 10px 30px rgba(15, 23, 42, 0.08), 0 0 1px rgba(15, 23, 42, 0.10);
  --shadow-glow: 0 0 0 1px rgba(13, 148, 136, 0.25), 0 6px 20px rgba(13, 148, 136, 0.08);
}
```

---

## 3. Typographie

* **Display (Éditorial & Grands Chiffres)** : `Instrument Serif`, `ui-serif`, `Georgia`, serif
  - Utilisé pour la marque, les en-têtes de page avec un mot clé en italique (`<em>...</em>`), et les métriques d'impact.
* **Interface (UI Controls, Menus, Tables)** : `Inter`, `system-ui`, `-apple-system`, sans-serif
  - Poids : 500 (standard), 600 (semi-gras), 750 (boutons d'action).
* **Monospace (Données OCR, Métadonnées, Bounding Boxes)** : `JetBrains Mono`, `ui-monospace`, monospace
  - Propriété essentielle : `font-variant-numeric: tabular-nums` pour un alignement vertical parfait des montants, pourcentages et numéros de série.

---

## 4. Composants Clés

1. **Sidebar de Navigation** :
   - Fond `--bg-deep`, bordure fine droite `--line`.
   - Items avec micro-indicateur vertical animé sur l'élément actif.
   - Puce index numérotée `01` à `10` en typographie monospace discrète.
2. **Topbar & Recherche Globale** :
   - Effet de verre poli avec `backdrop-filter: blur(16px)`.
   - Barre de recherche avec badge raccourci `/` et dropdown de résultats catégorisé (Dossiers, Documents, Champs, Extraits).
   - Chips d'état temps réel avec pulsation douce (`.chip.glow .dot`).
3. **Instrument de Capture (Dropzone)** :
   - Repères de visée aux 4 angles (`.corner.tl`, `.tr`, `.bl`, `.br`).
   - Balayage laser discret (`.scanline`) lors du survol ou du traitement.
   - Bouton caméra rapide pour prise de vue directe conteneur / plaque / carte grise.
4. **Boutons & Contrôles Segmentés** :
   - Bouton principal avec gradient lumineux `--electric` vers `--blue-accent`, micro-lift de 1px au hover et ombre diffuse.
   - Segmented buttons avec fond `--surface-2` et capsule active fluide.
5. **Tableaux et Indicateurs de Confiance** :
   - Rangées zébrées douces avec survol subtil.
   - Jauge de confiance avec gradient progressif : vert (>75%), jaune (50-75%), rouge (<50%).

---

## 5. Principes d'Animation & Accessibilité

* **Transition de vue** :
  ```css
  @keyframes pageEnter {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  ```
* **Durées & Courbes** :
  - Rapide : `0.15s` pour hovers et boutons.
  - Standard : `0.25s cubic-bezier(0.16, 1, 0.3, 1)` pour fenêtres et modales.
* **Mouvement Réduit (`prefers-reduced-motion: reduce`)** :
  - Désactivation de toutes les translations, rebonds et balayages.
  - Remplacement par des fondus simples ou transitions instantanées.
