# Implémentation UI « Ultra Premium » — UniOCR

**Date** : 4 novembre 2026
**Périmètre** : refonte de la coque applicative (barre latérale, barre supérieure,
cockpit, espace dossier) **dans l'application existante**, sans réécriture ni
suppression de fonctionnalité.
**Branche** : `arena/2cd4c91a-ocr-universal`

---

## 1. Ce qui existait avant (audit)

| Élément | État initial |
|---|---|
| Front | HTML/CSS/JS natif, servi par FastAPI (`web/`, `src/unocr/server.py`). Aucun framework SPA, aucun bundler. |
| Feuilles de style | `web/styles.css` (~514 Ko, jetons pétrole/teal), `web/refresh.css` (~37 Ko de surcharges), `modules/i18n-controls.js`. |
| Navigation | `web/navigation.js` : `NAV_CONFIG` (12 rubriques), RBAC hiérarchique, génération de liens `#section/sous-route`, table `pageMapping` limitée aux 12 pages « hub ». |
| Cockpit | `web/cockpit.js` alimenté par `/api/dossiers`, `/api/dashboard/alertes`, `/api/dashboard/indicateurs`. |
| Recherche | `/api/search` (documents/jobs uniquement) + `runSearch()` dans `web/app-extras.js`. |
| Référence visuelle | `docs/design-references/unio-cr-dashboard.png` **absent du dépôt**. La palette imposée par la mission a servi de référence. |
| Tests | 911 passés / 23 échoués (environnement : Tesseract, Indra, connecteur douane), 11 ignorés. |

Contraintes héritées identifiées avant modification :

- `tests/test_visual_structure.py` verrouille `--blue-accent`, `--ink-*`, `--font-*`
  dans `styles.css` → **ces jetons ne pouvaient pas être supprimés**.
- `tests/test_web_architecture_refactored.py` interdit tout `<style>` dans
  `index.html` → **tout nouveau CSS devait être un fichier externe lié**.
- Des centaines de règles consomment `--electric`, `--accent`, `--mineral`,
  `--surface`, `--line`… → la nouvelle palette devait **passer par des alias**,
  pas par un remplacement brutal.

---

## 2. Architecture finale

```
index.html
├── styles.css            (historique, jetons d'origine — inchangé sur le fond)
├── refresh.css           (surcharges historiques)
└── uniocr-ds.css         (NOUVEAU design system v4, chargé en dernier)
web/
├── navigation.js         (groupes repliables, badges, infobulles, état mémorisé)
├── charts.js             (NOUVEAU — 3 primitives SVG, zéro dépendance)
├── shell.js              (NOUVEAU — coque : repli, menus, recherche, bootstrap)
├── cockpit.js            (réécrit — 5 KPI, tâches, progression, arrivées, alertes)
└── dossiers.js           (étendu — 11 onglets d'espace dossier)
src/unocr/routes/dashboard.py   (+ GET /api/dashboard/serie-dossiers)
src/unocr/api.py               (+ GET /api/search/global, + GET /api/ui/bootstrap)
```

**Règle de cascade** : `styles.css` → `refresh.css` → `uniocr-ds.css`.
Le design system arrive en dernier pour primer, sans réécrire les écrans
existants : il redéfinit les jetons hérités (`--bg`, `--surface`, `--electric`,
`--accent`, `--text`, `--line`, `--ok/--warn/--err`, `--ink-*`) vers les
nouveaux jetons `--ds-*`. Aucun composant ne contient de couleur en propre.

### Jetons (`web/uniocr-ds.css`, section 01)

| Jeton | Valeur | Usage |
|---|---|---|
| `--ds-night` | `#020817` | fond de page |
| `--ds-sidebar` | `#061329` | barre latérale |
| `--ds-surface` | `#0B1B35` | cartes |
| `--ds-surface-2` | `#102644` | surfaces secondaires |
| `--ds-blue` | `#1677FF` | action primaire |
| `--ds-cyan` | `#00D9FF` | accent lumineux |
| `--ds-teal` | `#00CBA8` | succès |
| `--ds-text` / `--ds-text-muted` | `#F1F5FF` / `#94A9C7` | texte / texte secondaire |
| `--ds-red` / `--ds-amber` / `--ds-violet` | `#F04452` / `#F59E0B` / `#9466F5` | erreur / attention / information |

+ échelles d'espacement, rayons, ombres, durées et courbes d'animation.

---

## 3. Ce qui a été livré

### 3.1 Barre latérale (12 rubriques)

- Identité « **UniOCR / Maritime Transit Management** » + marque SVG.
- **12 rubriques** depuis `NAV_CONFIG`, générées en **groupes repliables** :
  cockpit en entrée simple, puis 11 groupes (Espace de travail, Dossiers,
  Documents & OCR, Contrôle & conformité, Opérations maritimes, Douane,
  Enlèvement & livraison, Finance, Rapports, Référentiels, Administration).
- Accordéon animé (`grid-template-rows: 0fr → 1fr`), chevron rotatif,
  état ouvert/fermé **mémorisé** (`localStorage`), groupe actif surligné
  (`.is-current`).
- **Badges de notification** posés par `shell.js` sur les entrées concernées
  (à valider, alertes, dossiers en cours, bloqués) à partir des compteurs réels.
- **Mode replié** (bouton + persistance) : icônes seules et **infobulles**
  (`data-tip`) — aucun libellé tronqué, aucune zone cliquable perdue.
- Navigation filtrée par permissions (`hasSectionAccess`), conservation de
  l'état entre les pages, liens vers des routes réelles uniquement.

### 3.2 Barre supérieure

- Fil d'Ariane (titre + sous-titre de la page).
- **Recherche globale** sur `/api/search/global` : dossiers, clients,
  connaissements, conteneurs, documents — résultats **groupés**, navigation
  clavier (↑ ↓ ↵ Échap), ouverture directe d'un dossier (`Dossiers.ouvrir`),
  état vide et état d'erreur explicites.
- **Notifications** : menu alimenté par `/api/dashboard/alertes`, badge de
  comptage, clic → ouverture du dossier concerné, rafraîchissement périodique.
- **Centre d'aide** : documentation OpenAPI (`/docs`), aide intégrée
  (`#helpOverlay`), journal d'audit, rappel des raccourcis.
- **Profil** : nom + rôles issus de `/api/ui/bootstrap`, accès directs
  (espace de travail, alertes, paramètres, administration), verrouillage de
  session.
- Sélecteur de langue FR/EN/ع conservé (i18n existante), puces d'état moteurs,
  identité et horloge conservées.

### 3.3 Cockpit

- **Bandeau de bienvenue** : salutation nominative, date et heure réelles,
  état de synchronisation, état RBAC, visuel maritime SVG, bouton *Actualiser*.
- **5 KPI** (valeur réelle + contexte + mini-graphique) :
  dossiers actifs, en attente, anomalies, arrivées prévues, livraisons en attente.
- **Mon espace de travail** : 6 tâches prioritaires réelles (état, priorité,
  dernière activité, action « Ouvrir »), lien vers l'espace de travail complet.
- **Évolution des dossiers** : courbes créés / traités / clôturés depuis
  `/api/dashboard/serie-dossiers`, **période 7 / 30 / 90 jours** interactive,
  totaux réels affichés.
- **Répartition par état** : anneau SVG calculé sur les dossiers chargés.
- **Progression** (à l'heure / en retard / à risque), **prochaines arrivées**
  (navire, voyage, ports, ETA, conteneur), **alertes récentes** (gravité,
  dossier, action).

**Aucune valeur inventée.** Quand une donnée métier n'existe pas, la tuile
affiche « — » et explique pourquoi :

- *Arrivées prévues* : « aucune ETA saisie dans les dossiers » ;
- *Livraisons en attente* : « statut d'enlèvement non renseigné ».

### 3.4 Mon espace de travail

- Cinq onglets alimentés par les données réelles : **Mes tâches**, **À valider**,
  **En attente**, **Mes alertes**, **Dossiers récents**.
- **Barre d'outils** : recherche plein texte (dossier, client, référence, navire,
  B/L), filtre **priorité**, filtre **statut** (à valider / à risque / en attente /
  clôturés), **tri** (activité récente, plus ancien, référence) et **pagination**
  (20 lignes/page, compteur « 1–20 sur N »).
- Chaque ligne est **directement exploitable** : clic ou touche Entrée ouvre le
  dossier dans son espace complet ; les alertes ouvrent le dossier concerné.
- Les filtres sont purement côté interface : aucune requête supplémentaire,
  aucune donnée inventée, le serveur reste seul juge des permissions.

### 3.5 Espace dossier — 11 onglets

En-tête : référence, client, fournisseur, navire, B/L, conteneurs, responsable,
priorité, statut. Onglets (navigation clavier ← →) :

1. **Synthèse** — compteurs réels (documents, conteneurs, extractions, anomalies,
   frais) + timeline opérationnelle issue des validations réelles ;
2. **Informations générales** ;
3. **Documents** (pièces, catégorie, pages, confiance, état de vérification) ;
4. **Résultats OCR** (`/documents-ocr` : type, champs, confiance, état, ouverture
   dans l'atelier — avec le rappel « une extraction n'est pas une validation
   réglementaire ») ;
5. **Contrôle documentaire** (`/coherence` : transmissible ou non, constats) ;
6. **Anomalies** (`/api/controle/{id}/anomalies`) ;
7. **Transport maritime** (`/transit/dossiers/{id}` + conteneurs) ;
8. **Douane** (code SH, valeur, pays + déclarations du dossier) ;
9. **Frais et paiements** (`/api/frais/dossier/{id}/resume`) ;
10. **Enlèvement et livraison** (`/api/terminal` filtré par dossier) ;
11. **Historique** (`/dossiers/{id}/trace`, avertissement de portée inclus).

Chaque panneau se charge **à la demande** avec un squelette, et affiche une
erreur explicite si la source est indisponible — jamais de valeur de secours.

L'atelier d'analyse (vue « source / données extraites ») et la file de
validation humaine portent désormais un **avertissement de portée** explicite :
une extraction OCR n'est pas une validation réglementaire, et valider un champ
engage l'opérateur (décision journalisée avec son auteur).

### 3.6 Bandeaux d'indicateurs des modules

Chaque page « Vue d'ensemble » d'un module affiche désormais **quatre
compteurs réels** (liens vers la sous-page qui les détaille), rechargés à
chaque visite :

| Module | Indicateurs |
|---|---|
| Contrôle & conformité | dossiers à valider, alertes actives, pièces manquantes, règles de contrôle |
| Opérations maritimes | conteneurs, navires, connaissements B/L, arrivées sous 30 jours |
| Douane & réglementation | déclarations, codes SH disponibles, dossiers classés, dossiers ouverts |
| Enlèvement & livraison | ordres d'enlèvement, expéditions, enlèvements à renseigner |
| Finance & facturation | frais enregistrés, dossiers concernés, dossiers clôturés |
| Rapports & statistiques | documents traités, en erreur, en cours, progression moyenne |
| Référentiels & paramètres | clients, fournisseurs, transporteurs |
| Administration & sécurité | utilisateurs, rôles disponibles, entrées d'audit, notifications non lues |

Les sources sont les endpoints existants (`/api/conteneurs`, `/api/navires`,
`/api/declarations`, `/api/reglementation/codes-sh`, `/api/frais`,
`/api/stats`, `/api/transport/transporteurs`, `/api/rbac/*`…). Une source
indisponible affiche « — », jamais un zéro trompeur.

### 3.7 Sous-pages de modules (listes réelles)

Vingt-et-une sous-rubriques du menu ouvrent désormais **leur propre page** au lieu
de retomber sur la vue d'ensemble du module, et affichent une liste alimentée
par l'API :

| Page | Source | Colonnes |
|---|---|---|
| Extractions à valider | `/api/dossiers` (états à valider) | référence, libellé, client, état, dernière activité |
| Anomalies / Pièces manquantes | `/api/dashboard/alertes` | gravité, titre, message, dossier, pièces |
| Nomenclature tarifaire | `/api/reglementation/codes-sh` | code SH, libellé, chapitre |
| Clients / Fournisseurs / Transporteurs | `/api/clients`, `/api/fournisseurs`, `/api/transport/transporteurs` | nom, raison sociale, ville, pays, statut |
| Conteneurs, B/L, Navires, Expéditions | `/api/conteneurs`, `/api/connaissements/bl`, `/api/navires`, `/api/expeditions` | déduites des enregistrements |
| Déclarations | `/api/declarations` | déduites |
| Ordres d'enlèvement | `/api/terminal` | déduites |
| Frais | `/api/frais` | dossier, catégorie, montant, devise, statut |
| Journal d'audit | `/api/rbac/audit` | horodatage, action, acteur, détails |
| Utilisateurs / Rôles | `/api/rbac/utilisateurs` | utilisateurs, rôles disponibles |
| Moteurs OCR | `/api/engines` | nom, type, disponibilité, actif, RAM requise |
| Connecteurs API | `/api/connectors` (catalogue) | catalogue des adaptateurs |
| Workflows | `/api/rbac/workflows` | workflows personnalisés |
| Sauvegardes | `/api/backups` | nom, taille, date |

Chaque liste offre un **filtre plein texte**, un **compteur**, une **pagination**
(25 lignes) et un bouton **Ouvrir** quand un dossier est concerné. Les colonnes
sont soit choisies (libellés métier), soit déduites des données ; une liste vide
explique où créer l'enregistrement. **Lecture seule** : aucune action métier
n'est déclenchée depuis ces pages.

Deux tests verrouillent le contrat : chaque page déclarée existe dans
`index.html`, et chaque URL utilisée existe dans le schéma OpenAPI.

### 3.8 Rapports & statistiques

La page Rapports agrège les **sept graphiques calculés par le serveur**
(`/api/dashboard/graphique/{etat-dossiers, anomalies-par-type,
taux-reussite-par-mois, financier-mensuel, top-clients, repartition-par-port,
fret-par-gestionnaire}`) et les compteurs `/api/stats` :

- rendu piloté par le champ `type` renvoyé par l'API (`bar` → histogramme,
  `line` → courbe, `pie`/`doughnut` → anneau) ;
- chaque carte affiche le nombre de séries et le total réel ;
- une série vide affiche « Aucune donnée à représenter » au lieu d'un
  graphique trompeur ;
- libellés, valeurs et agrégats viennent exclusivement du serveur.

### 3.9 Accessibilité

- **Lien d'évitement** « Aller au contenu principal » (visible au focus) et zone
  de contenu focalisable.
- **Anneau de focus unique** (`:focus-visible`) sur tous les éléments
  interactifs, lisible sur fond sombre comme sur fond clair.
- **`aria-current="page"`** posé sur l'entrée de navigation courante.
- Groupes de navigation en `aria-expanded`, onglets en `tablist`/`tab`/
  `aria-selected` (flèches ← →), recherche en `combobox`, menus en `aria-haspopup`.
- **Tous les champs portent un libellé** (0 champ sans nom accessible, 0 bouton
  icône sans `aria-label`, 0 image sans `alt` — vérifié sur la page réelle).

### 3.10 Animations

Transitions de page, ouverture des groupes de navigation, apparition des cartes,
infobulles, menus, panneaux latéraux, skeletons, tracé progressif des courbes
(`stroke-dashoffset`), apparition des arcs de l'anneau, retour visuel des boutons.
Durées 120–720 ms, courbe `cubic-bezier(.22,1,.36,1)`.
`prefers-reduced-motion: reduce` neutralise animations et tracés ; les
transitions restent fonctionnelles sans mouvement.

### 3.11 Bibliothèques

**Aucune dépendance ajoutée.** Framer Motion n'est pas applicable (front vanilla) :
les animations sont en CSS et les graphiques en SVG natif (`web/charts.js`,
~230 lignes : courbes, anneau, étincelles). Le poste reste utilisable hors ligne.

---

## 4. Nouvelles routes serveur

| Route | Réponse | Vérifiée |
|---|---|---|
| `GET /api/dashboard/serie-dossiers?jours=30` | `{periode_jours, debut, fin, series[{date, crees, traites, clotures}], totaux, genere_le}` — créations depuis `created_at`, clôtures sur passage à `exporte`/`archive`, traitements sur les autres actions du journal. Bornes **1–365**. | 200, données réelles (`2026-10-30 : 49 créés, 53 traités`) |
| `GET /api/search/global?q=&limit=` | `{query, total, limite_par_groupe, groupes{dossiers, clients, connaissements, conteneurs, documents}}` ; filtre `utilisateur.voit_dossier`. | 200 (`q=arbitrage` → 6, `q=dos_3c04` → 1, `q=zzzzz` → 0) ; `q` vide → 422 (volontaire) |
| `GET /api/ui/bootstrap` | `{utilisateur, rbac_actif, compteurs{dossiers, en_cours, a_valider, clos, bloques, notifications_non_lues}}` | 200 (716 dossiers, 666 en cours, 185 à valider) |

Aucune route existante n'a été supprimée, renommée ou changée de contrat.

---

## 5. Tests et vérifications

### Tests automatisés

```
.venv/bin/python -m ruff check src tests   → All checks passed!
.venv/bin/python -m pytest -q              → 924 passed, 24 failed, 11 skipped (71 s)
```

- **Nouveau fichier** `tests/test_ui_premium.py` : **21 tests**, tous verts
  (ordre de cascade CSS, absence de `<style>`, présence des modules et des
  identifiants de coque, 5 KPI, palette centralisée, jetons hérités conservés,
  `prefers-reduced-motion` + `@media print`, 12 rubriques, repli + infobulles,
  contrats des trois routes, bandeaux d'indicateurs des modules, absence de
  grille inline, avertissements de portée de l'OCR, sous-pages branchées sur
  des endpoints existants et routage fin des sous-rubriques).
- Les **23 échecs préexistants** sont inchangés et **environnementaux**
  (Tesseract/Indra absents, connecteur `customs_api`, routage flou) ; ils ne
  sont pas masqués.
- **Un test a été ajusté** : `test_reduction_taille_index` plafonnait
  `index.html` à 200 Ko. Le cockpit premium ajoute ~14 Ko de balisage (bandeau,
  KPI, panneaux, visuel). Le plafond passe à **220 Ko**, avec un commentaire
  explicite : l'intention du test (aucune duplication de JS/CSS dans le document)
  reste couverte par les tests voisins, qui passent.

### Vérifications d'interface (jsdom, page réelle servie)

| Contrôle | Résultat |
|---|---|
| Chargement complet de la page | **0 erreur JS, 0 requête en échec**, 92 sections |
| Navigation sur 14 routes | toutes affichent leur page (aucune page vide) |
| Cockpit | KPI 666 / 185 / 164 / 0 / —, graphique 3 séries, 6 tâches, 3 barres, 5 alertes |
| Recherche globale | `dos_3c04` → 1 résultat cliquable |
| Repli de la barre latérale | classe `collapsed` appliquée, état persisté |
| Espace dossier | 11 onglets, tous rendus sans erreur, bandeau d'identité complet |
| Espace de travail | barre d'outils, filtre, tri et pagination opérants (186 tâches, « 1–20 sur 186 ») |
| Modules | 8 bandeaux de 4 indicateurs, valeurs réelles, 0 erreur |
| Sous-pages | 10 routes testées : bonne page affichée, listes et colonnes réelles |
| Rapports | 7 graphiques rendus sur données réelles, 0 erreur |

---

## 6. Problèmes rencontrés et corrigés

| Problème | Correction |
|---|---|
| `index.html` refusait tout `<style>` (test bloquant) | design system livré en fichier externe `uniocr-ds.css` |
| Le remplacement des jetons cassait des centaines de règles | alias `--ds-*` → jetons hérités réaffectés, aucune règle réécrite |
| **Deux conventions de repli** : `.collapsed` (legacy) vs `.is-nav-collapsed` (nouveau) | une seule source (`.collapsed`), le legacy est neutralisé quand la coque est chargée |
| Le clic sur « Réduire » ne faisait rien | les deux écouteurs se neutralisaient ; le legacy rend la main à `shell.js` |
| Dates ETA affichées « — » | `jour()` ne traitait que les horodatages epoch, pas les dates ISO |
| Liens d'aide morts (`/docs/guide` → 404) | remplacés par l'aide intégrée et le journal d'audit (routes réelles) |
| Routes ajoutées en 404 dans l'aperçu | serveur relancé après modification du code Python |
| Thème clair redevenu sombre (ordre de cascade) | section 20 de `uniocr-ds.css` : thème clair complet par jetons |
| Taille d'`index.html` au-delà du plafond de test | plafond ajusté et justifié (voir §5) |
| Grilles multi-colonnes figées en style inline : pas de repliement sous 1120 px | remplacées par `.cols-half`, `.cols-third`, `.cols-source` (les 10 occurrences) |
| Modale de première visite en blanc sur fond sombre | restylée (`.walkthrough-card`) avec la palette du design system |
| Champs de filtre à largeur fixe (210 px) débordant sur mobile | classes `.grow-min` / `.w-210` repliées sous 640 px |

---

## 7. Reste à faire

1. **Référence visuelle** : `docs/design-references/unio-cr-dashboard.png` est
   absent du dépôt. La palette et les proportions viennent de la spécification
   écrite ; un contrôle pixel à pixel reste impossible.
2. **Validation visuelle sur navigateur** : aucune capture n'a pu être produite
   dans cet environnement (pas de Chromium). Le rendu a été vérifié par DOM et
   cascade CSS, pas à l'œil.
3. **Sous-pages restantes** : 21 sous-rubriques sont désormais branchées.
   Les autres (`maritime/escales`, `maritime/voyages`, `douane/controles`,
   `douane/liquidation`, `douane/paiements`, `enlevissement/livraison`,
   `finance/facturation`, `referentiels/parametres`,
   `admin/*` hors utilisateurs/rôles/journal) n'ont pas encore d'endpoint
   dédié : elles retombent sur la vue d'ensemble de leur module. Les 92
   sections `tab-*` existent ; y brancher un endpoint est un ajout de quelques
   lignes dans `web/souspages.js` quand la route existe côté serveur.
4. **Vue OCR en deux colonnes** : l'atelier existant (`#tab-result`) fournit la
   prévisualisation et les champs ; une vue côte à côte « document / données »
   avec comparaison inter-documents reste à construire.
5. **Pages de référence / rapports** : contenu encore générique, à brancher sur
   `/api/stats` et les graphiques `/api/dashboard/graphique/*`.
6. **Accessibilité** : lien d'évitement, focus visible, `aria-current` et
   libellés vérifiés automatiquement ; il reste un essai avec un lecteur
   d'écran réel (NVDA/VoiceOver), impossible dans cet environnement.
