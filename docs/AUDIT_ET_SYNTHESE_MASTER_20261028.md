# Synthèse d'Audit et Protection du Projet — Mission Master
**Date** : 2026-10-28  
**Rôles** : Principal UI/UX Designer, Creative Director, Senior Frontend Architect, QA & Security Engineer  
**Projet** : UniOCR (Universal Document Intelligence)

---

## 1. Cartographie Technique et Architecture

### 1.1 Stack et Langages
* **Backend** : Python 3.12, FastAPI 0.110+, Pydantic v2, Uvicorn, OpenCV 4.10, PyTesseract 0.3.10, PDFMiner.six, PyPDFium2, ReportLab, openpyxl, pandas, Striprtf, rapidfuzz, zxing-cpp.
* **Frontend** : Architecture Web standard sans bundler lourd, Vanilla JavaScript modulaire ES6 (`connectors.js`, `dossier.js`, `formulaire.js`, `tracabilite.js`, `transmission.js`, `i18n-controls.js`), CSS3 avec Design System natif (`web/styles.css`), HTML5 sémantique (`web/index.html`), Service Worker PWA hors-ligne (`web/sw.js`).
* **Typographie embarquée (100% offline)** : `Instrument Serif` (titres éditoriaux), `Inter` (UI / navigation / formulaires), `JetBrains Mono` (données techniques / code / métadonnées).

### 1.2 Routes et Espaces Utilisateur (10 Ateliers)
1. **01 — Atelier / Importer** (`#tab-import`) : Glisser-déposer, caméra directe, réglages OCR, modes de prétraitement, sélection des langues, filtres avancés, traitement unitaire et par lots.
2. **02 — Atelier / Documents** (`#tab-docs`) : Explorateur de jobs, filtres par statut, recherche plein texte, actions rapides.
3. **03 — Analyse / Résultat** (`#tab-result`) : Visualiseur de pages avec calque SVG de zones surlignées, inspecteur de champs avec provenance, tableaux reconstruits, codes-barres.
4. **04 — Maîtrise / Qualité** (`#tab-quality`) : Double score (moteur vs système), détecteur d'anomalies, désaccords multi-moteurs.
5. **05 — Maîtrise / Configuration** (`#tab-config`) : Moteurs installés, modèles linguistiques réels, profils métier disponibles.
6. **06 — Maîtrise / Tableau de bord** (`#tab-dashboard`) : Métriques système en direct (RAM, CPU, jobs), sauvegarde/restauration du magasin, journal d'audit JSONL.
7. **07 — File de validation / Révision** (`#tab-review`) : Navigation clavier (`j`/`k`, `Entrée`, `o`), validation humaine ciblée.
8. **08 — Maîtrise / Profils métier** (`#tab-profiles`) : Éditeur et testeur de profils JSON à blanc.
9. **09 — Intégration / Connecteur Hub** (`#tab-connectors`) : 12 sous-volets d'intégration vers systèmes cibles (simulateur, export assisté, API douane réelle).
10. **10 — Parcours / Dossier documentaire** (`#tab-dossier`) : Regroupement de pièces, contrôles de cohérence interdocumentaire, génération de paquets (ZIP/XLSX/JSON).

### 1.3 Rôles et Règles Métier (RBAC)
* 4 rôles hiérarchiques : `Lecteur` < `Opérateur` < `Superviseur` < `Administrateur`.
* Cloisonnement strict des documents par dossier dans `data/rbac.json`.
* Intégrité des données : aucune donnée n'est inventée, les champs absents restent explicitement absents (`not_detected`).

---

## 2. Défauts Visuels, Incohérences et Dettes UX Identifiés

1. **Hiérarchie visuelle et contraste** :
   * La barre latérale et la topbar manquent de profondeur et de séparation raffinée ; l'indicateur d'onglet actif peut être sublimé.
   * La palette de couleurs dark/light présentait des valeurs hexadécimales en dur isolées qui ont été unifiées lors du premier passage, mais l'élévation par couches (`surface-1`, `surface-2`, `surface-3`) et la subtilité des micro-bordures peuvent être grandement perfectionnées.
2. **Instrument de capture (Dropzone)** :
   * L'aspect "instrument de précision" peut être accentué avec des repères de cadrage plus fins, des angles métalliques subtils, et un effet de scanline fluide lors des chargements.
3. **Indicateurs de confiance et badges** :
   * Les jauges de confiance méritent une graduation chromatique plus nette et des micro-animations de progression.
4. **Micro-interactions et transitions** :
   * Absence de transition soignée lors du passage d'un onglet à l'autre (effet de reveal fluide).
   * Les boutons méritent un retour tactile plus affirmé avec un micro-lift et des ombres diffuses.
5. **Accessibilité & Préférences système** :
   * Respect strict de `prefers-reduced-motion` pour les utilisateurs sensibles.
   * Rapprochement des contrastes aux normes WCAG 2.1 AA/AAA.

---

## 3. Commandes et Environnement

* **Lancement Serveur** : `PYTHONPATH=src python -m uvicorn unocr.api:app --reload --host 127.0.0.1 --port 8000`
* **Tests de non-régression** : `python -m pytest tests/test_visual_structure.py tests/test_web_architecture_refactored.py tests/test_xss_frontend.py`
* **Vérification CLI** : `PYTHONPATH=src python -m unocr.cli diagnose`
* **Node / npm** : Node.js `v24.22.1`, npm `11.19.1`

---

## 4. Protection de l'Intégrité du Projet

* **Préservation absolue** : Tous les identifiants d'éléments DOM (`id`, classes fonctionnelles, `data-tab`, `data-field`), les appels d'API `/api/*`, et les liaisons JavaScript sont 100% préservés.
* **Aucune régression autorisée** : La suite de tests existante (`tests/test_xss_frontend.py`, `tests/test_web_architecture_refactored.py`, `tests/test_visual_structure.py`) doit demeurer verte à 100%.
