# UniOCR — Refonte produit opérationnelle

## Résultat livré

L’entrée dans UniOCR devient un **poste de travail orienté actions**, et non uniquement un catalogue de menus : **importer les pièces → vérifier l’extraction → traiter les dossiers**. Ces raccourcis ouvrent les fonctions existantes ; aucune démonstration fictive, donnée métier inventée ou API de remplacement n’est introduite.

La transformation est implémentée. L’amélioration de l’adoption est un objectif UX, **pas un gain « 100× » mesuré**, ni une augmentation de conversion démontrée.

## Constats et décisions

L’exploration a porté sur la navigation complète et ses **102 destinations**, les composants partagés, les données du cockpit, l’atelier OCR, les dossiers, les contrôles, les écrans douaniers et financiers, l’administration et les vues documentaires. Les contrats d’habilitation, le routage hash, les composants existants et le service worker ont été examinés avant les modifications.

| Observation concrète | Transformation implémentée |
|---|---|
| Navigation riche, mais parcours initial peu explicite | Trois actions métier au premier plan, conditionnées par les liens réellement disponibles dans la navigation |
| Multiples vues « Vue d’ensemble » difficiles à distinguer | Titres contextualisés et fil d’Ariane synchronisés au changement de route |
| Recherche de données distincte de la recherche d’un écran | Palette **Aller à…**, **Ctrl/⌘ J**, recherche sans accents, groupes, compteur et état vide ; recherche métier **Ctrl K conservée** |
| Impossible de distinguer certaines erreurs réseau d’une absence de dossiers | Erreur de synchronisation et panneaux indisponibles explicites ; suppression des replis trompeurs vers des listes vides |
| Création de dossier restant modale après changement d’écran | Fermeture effective du dialogue natif à la sortie de sa route, suppression du blocage global des clics ; titre resynchronisé à l’annulation |
| Module de notification inutilisable puis incompatible avec l’API historique | Correction du doublon de déclaration, échappement des messages, normalisation du type/délai, API `UniOCRToast` et préservation de la fonction `toast` existante |
| Fermeture des notifications dépendante d’une animation | Repli de fermeture indépendant de `animationend`, testé sans animation |
| Débordements mobiles réels dans les résultats OCR et la configuration des moteurs | Grilles adaptatives, tableaux défilants, panneaux et boutons repliables ; recherche globale conservée en seconde ligne |
| Fontes base64 bloquées par la CSP existante | Extraction à l’identique de quatre fichiers WOFF2 dédupliqués, servis en same-origin et intégrés au cache hors ligne, avec textes OFL |

## Expérience et composants

- **Coque commune** : navigation vert profond, espace de travail clair, hiérarchie des titres, boutons et tableaux harmonisés, thème sombre conservé et préférence persistante protégée contre les erreurs de stockage.
- **Cockpit** : proposition de valeur explicite, trois accès immédiats, actualisation réelle, statut et fraîcheur de synchronisation, indicateurs conservant leurs sources et leurs valeurs manquantes explicites.
- **Navigation par intention** : dialogue natif accessible au clavier, flèches, Entrée, Échap et restitution du focus. Les destinations proviennent du menu existant, sans nouveau modèle de permissions. Une révocation de liens est répercutée pendant que la palette est ouverte.
- **Catalogue juridique** : présentation en cartes, extraits lisibles et détails de provenance consultables ; identifiants, données sources et avertissements juridiques maintenus.
- **Responsive** : barre latérale complète sur ordinateur, rail et tiroir sur tablette, tiroir et recherche sur deux lignes sur mobile ; les trois actions restent visibles dans la première vue mobile du cockpit.
- **Compatibilité** : routes, formulaires, fonctions métier, API, données et mécanismes d’autorisation existants maintenus. Pas de nouveau framework ni de dépendance JavaScript tierce à charger à l’exécution ; outils Chromium uniquement en dépendances de développement.

L’effet recherché est de réduire l’effort d’orientation et de rendre la prochaine action évidente, sans retirer la navigation experte. Aucun suivi analytique supplémentaire ni transmission de documents à un service tiers n’a été ajouté.

## Performances et sécurité

`web/styles.css` passe de **514 597 à 74 091 octets**, soit **−85,6 % sur ce fichier non compressé**, après externalisation des fontes. Les quatre fichiers WOFF2 représentent ensemble **122 848 octets**. Cela ne signifie pas que le site entier est 85,6 % plus rapide : aucun benchmark global de chargement ou Core Web Vitals n’est revendiqué.

La CSP n’a pas été assouplie. Le chargement effectif d’Inter est vérifié dans Chromium. La palette produit ne crée aucune requête métier, écriture de stockage ou injection HTML. Les messages de notification malveillants sont affichés comme du texte.

**27 empreintes sur 27 identiques aux valeurs observées à la livraison du lot 101**. L’écart historique de `data/referentiels.json` par rapport au référentiel attendu reste inchangé. Les deux PDF en quarantaine gardent leurs SHA-256 :

- `d0f2c3089769ae42949477fdb9b854c83f56eb403fb28dc81eecb125d5f866c6`
- `37c8bc3f614ffb127e2104dd70205ed279160d2ca522b9b523505fca7015b09a`

Les fichiers de données, travaux et journaux déjà présents dans l’arbre de travail n’ont pas été ajoutés aux commits de refonte.

## Recette et résultats

| Vérification | Résultat |
|---|---|
| Chromium, ordinateur **1440 × 1000**, tablette **834 × 1112**, mobile **390 × 844** | **306 passages de routes**, aucune exception JavaScript, aucun débordement horizontal de page, aucune tentative d’écriture HTTP |
| Captures navigateur | **24 captures de vues métier + 3 états sombres** ; captures de viewport, pas de pages complètes ; rendu du cockpit relu aux trois tailles |
| Interactions navigateur | Palette, recherche, clavier, Échap, thème, ouverture du menu responsive, annulation de création, notification échappée et fonte locale |
| Menus et panne API, contrôle complémentaire | Notifications, aide et profil ouverts/fermés ; erreur HTTP 503 simulée uniquement dans le navigateur, correctement signalée par le cockpit |
| Pytest ciblé produit/architecture/provenance/PDF | **121 réussis**, 1 avertissement |
| Scénarios JSDOM produit | **7 groupes de scénarios** + notifications : droits, orientation, accents, XSS, clavier, focus, révocation et fermeture sans animation |
| JSDOM catalogue juridique | **23 scénarios réussis** |
| Recette documentaire | **2 332 tests réussis**, Ruff réussi et **212 scénarios UI réussis** |
| Suite Python complète | **4 487 réussis, 2 échecs préexistants, 1 ignoré**, 1 avertissement ; **525,65 s** |
| CI GitHub du code final `1a5880e6` | **Réussie**, [exécution 42484994144](https://github.com/boa-crypto/ocr-universal/actions/runs/42484994144) |
| Analyse statique | Ruff `src`, `tests` et script de recette réussi ; `git diff --check` réussi |

Les deux échecs de la suite complète sont les mêmes qu’au lot 101 :

- `tests/test_indra_ocr.py::test_indra_engine_availability`
- `tests/test_ocr.py::test_selection_prefers_native_when_present`

Ils concernent la disponibilité du moteur optionnel Indra dans cet environnement, pas les modifications d’interface. La suite complète **n’est donc pas entièrement verte**. Le formatage et les derniers ajustements visuels ont été revérifiés par les tests UI ciblés et la recette navigateur ; ils ne constituent pas une seconde exécution de toute la suite Python.

Les premiers essais de la recette navigateur ont révélé des limites de l’outil : fermeture de Chromium monoprocessus après fermeture d’un contexte, et capture bloquée lors de l’annulation synthétique des animations. Le runner lance désormais un navigateur par taille et attend la fin naturelle de la transition de page. Aucun clic forcé ni désactivation de la CSP n’a servi à masquer un problème de l’application.

## Fichiers principaux

- `web/product-experience.js`, `web/product-experience.css` : couche produit, palette, orientation, cockpit et adaptations responsive.
- `web/index.html`, `web/app-extras.js`, `web/manifest.webmanifest`, `web/sw.js` : intégration, thème et cache.
- `web/cockpit.js`, `web/dossiers.js`, `web/components/toast/Toast.js` : états réseau, cycle de vie modal, notifications sûres et compatibles.
- `web/customs-legal-pages.js` : catalogue et provenance lisibles.
- `web/styles.css`, `web/fonts/` : fontes locales, déduplication et licences.
- `tests/ui_product_browser.cjs`, `tests/ui_product_experience.js`, `tests/test_ui_product_experience.py` : nouvelles recettes ; tests de thème et d’architecture adaptés aux contrats réellement modifiés.
- `package.json`, `package-lock.json`, `scripts/customs_review_recipe.py` : outils navigateur et intégration de la validation produit à la recette existante.

## Preuves et reproduction

Les preuves détaillées sont conservées hors Git sous `/home/user/recettes-unocr/product-redesign/` :

- `verified/browser-report.json`, `verified/*.png`, `browser.log`
- `cibles.xml`, `cibles.log`, `product-final.log`
- `complete.xml`, `complete.log`
- `documentaire/recette-5mj4iiox/recette.json` et journaux associés
- `quality.json`, `fonts.json`, `empreintes.json`, `ci.json`

Commandes principales, depuis la racine du dépôt :

```sh
npm run ui:product -- http://127.0.0.1:8000 /home/user/recettes-unocr/product-redesign/verified
node tests/ui_product_experience.js
.venv/bin/python -m pytest tests/test_ui_product_experience.py -q
.venv/bin/python scripts/customs_review_recipe.py --artifacts /home/user/recettes-unocr/product-redesign/documentaire
source .venv/ocr-native/activate.sh
.venv/bin/python -m pytest -q
```

## Limites et suite éventuelle — non implémentée

- Aucune mesure A/B, conversion, rétention ou gain « 100× » ; une future étude d’usage demanderait un protocole et des données consenties.
- Recette visuelle dans Chromium aux trois tailles, pas certification WCAG exhaustive ni certification Safari/Firefox ou terminaux physiques. Aucun faux comparatif avant/après : la capture visuelle initiale n’a pas été conservée.
- Les transactions métier destructrices ou persistantes ne sont pas exécutées contre les données locales par la recette navigateur. Les fonctions correspondantes restent couvertes par leurs tests existants.
- Serveur local existant conservé, backend version 76 non redéployé : les évolutions juridiques du lot 101 ne sont pas annoncées comme disponibles sur ce backend ancien.
- La quarantaine juridique reste non validée/non publiée ; cette refonte ne confère aucune authenticité aux textes ni recevabilité fiscale.
- Aucun déploiement de production, migration de données ou changement d’habilitation. Une mise en production et l’installation/validation d’Indra restent des opérations distinctes, non exécutées ici.
