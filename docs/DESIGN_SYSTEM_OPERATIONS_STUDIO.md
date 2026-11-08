# UniOCR — Operations Studio : système et contrats

## Direction

**Un atelier documentaire, pas une galerie de widgets.** Le cockpit explique le parcours ; les écrans opérationnels privilégient l’information exacte et l’action contextualisée. Les index de modules sont des répertoires fonctionnels plutôt que des cartes promotionnelles répétées.

- Typographie éditoriale **Instrument Serif** pour le récit du cockpit et les repères ; **Inter** pour les opérations ; **JetBrains Mono** pour identifiants et métadonnées.
- Papier/sauge et encre verte pour la coque ; accent ardoise pour contrôle/douane, accent laiton pour finance. Ces accents ne changent jamais les couleurs sémantiques des statuts.
- Réduction de la concurrence visuelle : métadonnées secondaires repliables, actions du dossier groupées, tableaux sobres, légendes explicites.
- Sur mobile, le fil d’Ariane conserve la destination courante et l’accès aux repères, sans répéter toute la hiérarchie.

## Sources de vérité et cascade

Le système adapte l’application vanilla existante, sans introduire de framework ni réécrire les API :

1. `styles.css`, `refresh.css`, `uniocr-ds.css` : structure et contrats historiques.
2. `product-experience.css` : surfaces et typographie de coque via `--pe-*`, correspondance avec les tokens `--ds-*`.
3. `visual-motion.css` : mouvement et illustration de parcours.
4. `operations-studio.css` : composants opérationnels et variations de rubrique.

Tokens principaux :

| Domaine | Variables |
|---|---|
| Surfaces | `--pe-paper`, `--pe-white`, `--pe-green-soft` |
| Texte | `--pe-ink`, `--pe-muted` |
| Navigation | `--pe-nav`, `--pe-nav-text`, `--pe-gold` |
| Séparateurs | `--pe-line` |
| Accent opérationnel | `--studio-accent`, `--studio-soft` |
| Conteneurs opérationnels | `--studio-r-sm`, `--studio-r-md`, `--studio-focus` |
| Statuts métier | Tokens sémantiques existants `--ds-red`, `--ds-amber`, etc. |

Le thème sombre conserve des textes contrastés et les mêmes significations métier. Des sélecteurs ciblés neutralisent les anciens `!important` qui rendaient les sous-menus actifs illisibles ; ils ne changent pas les liens marqués indisponibles. Les contrôles primaires sont harmonisés sans recolorer les actions destructrices.

Ce n’est pas une prétention à avoir supprimé tout le CSS historique : la cascade d’adaptation est explicite pour préserver les composants existants.

## Composants réutilisables

### Pilotage par état

`[data-case-view]` bascule entre `liste` et `board` via `Dossiers.etat.vue`. La recherche, les filtres, la sélection, l’ordre et la pagination restent partagés. Aucune écriture API ni mémorisation métier.

| Colonne | États réels |
|---|---|
| Préparer | `en_preparation` |
| Traiter | `traitement_en_cours` |
| Examiner | `revision_requise`, `incomplet`, `erreur_traitement`, `en_validation` |
| Clôturés | `exporte`, `archive` |
| Autres états | Tout état non reconnu — jamais éliminé ni classé arbitrairement |

Le compteur d’une colonne signifie **affichés / total après filtres** ; il ne représente pas une progression ou un taux de conformité. La limite initiale de 40 dossiers et « Afficher plus » sont conservées. Aucun glisser-déposer : une transition métier exige les actions et validations existantes.

### Dossier contextualisé

- `.case-next` : boutons vers les vrais onglets pièces, OCR, anomalies et historique.
- `.case-return` : retour au dossier sélectionné dans le pilotage, avec restitution du focus.
- `.case-identity` : `details/summary` natif ; toutes les références restent accessibles, sans ellipses permanentes.
- Onglets : boutons natifs, `aria-selected`, `aria-controls`, identifiants de panneaux stables, un seul panneau visible. Navigation flèches, Début et Fin.
- `.dos-doc` : nom complet et icône selon l’extension connue (sans prétendre valider le contenu du format), métadonnées, inspection et export rattachés au job. Aucun lien vers un identifiant absent.

### Inspecteur de source

L’inspection réutilise l’atelier OCR et les vrais résultats. `loadResult` possède un numéro de génération : une réponse ancienne ne peut plus remplacer une demande plus récente. Pendant l’ouverture, les anciens résultats ne sont pas présentés comme ceux de la nouvelle pièce ; après un échec, `currentResult` est vidé, une erreur explicite et un bouton de réessai GET apparaissent. Le marqueur `data-result-source` n’est posé qu’après réception du résultat demandé.

Une confiance absente ou invalide n’est pas convertie en 0 %. Une confiance réellement égale à zéro reste 0 %. Une valeur extraite réellement égale à zéro est préservée. Les horodatages nuls du magasin historique restent « — », et ne deviennent pas une date d’ouverture au 1er janvier 1970.

### Repères contextuels

`.context-guide` ouvre un dialogue natif `.studio-guide`. Le titre reprend l’écran courant, sans les compteurs des badges de navigation. L’introduction réutilise la description native quand elle existe. Le contenu explique ensuite le périmètre de la rubrique, les précautions de lecture et les écrans voisins **présents dans la navigation autorisée**. Le guide suit une révocation de liens pendant son ouverture, se ferme à la navigation et restitue le focus à la fermeture clavier.

Le guide ne définit aucun nouveau droit et n’effectue aucune requête métier.

### Formulaires

Les formulaires natifs possédant des champs obligatoires reçoivent :

- un état de complétude issu de la validité native ;
- un récapitulatif des erreurs avec accès au champ concerné ;
- une mise à jour pendant la saisie et après réinitialisation.

Aucune interception de soumission, autosauvegarde, persistance des saisies ou validation métier automatique. Le nombre de champs remplis ne signifie pas qu’un dossier est réglementairement validé.

## Mouvement, accessibilité et contrôle

Réutiliser les transitions CSS et la Web Animations API existantes. Éviter une deuxième animation concurrente sur la même surface. La préférence de réduction des mouvements reste prioritaire, y compris après changement en cours de session.

Les états `hidden` des composants opérationnels doivent rester réellement invisibles malgré les règles `display` héritées. Ne pas confondre contenu repliable accessible et texte définitivement tronqué.

Recettes :

```sh
npm run ui:studio
npm run ui:studio:browser
UI_ALLSHOTS=1 npm run ui:product -- http://127.0.0.1:8000 /chemin/preuves
UI_STUDIO_BROWSER=1 UI_STUDIO_ARTIFACTS=/chemin/preuves-natives .venv/bin/python -m pytest tests/test_ui_studio_visual_pipeline.py -q
```

Le dernier test utilise deux PDF réellement traités en OCR natif et un dossier dans un magasin temporaire isolé. Il ne prépare pas une démonstration fictive dans le magasin utilisateur. Les parcours navigateur restent GET/HEAD uniquement ; seuls les préparatifs de la fixture isolée créent leurs documents de test.
