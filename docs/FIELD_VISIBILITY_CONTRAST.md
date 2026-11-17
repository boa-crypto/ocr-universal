# Champs et listes de choix — contrat de lisibilité

## Cause et correction

Le design system historique imposait un fond bleu-noir translucide aux champs, encore plus sombre au focus. La couche produit adaptait leur **texte** au thème clair sans adapter systématiquement leur **fond** : les valeurs pouvaient devenir sombres sur sombre, particulièrement dans les modales et les listes de choix.

La correction porte sur le système, pas sur une liste de champs :

- `uniocr-ds.css` : suppression de ces fonds sombres forcés dans les primitives, recherches et filtres ; utilisation du couple de tokens partagé.
- `product-experience.css` : adoption du couple texte/fond et du curseur associé, plutôt qu’une surcharge du texte seul.
- `field-accessibility.css`, chargé après les styles historiques : contrat commun aux contrôles natifs, `.edit`, contenus éditables et combobox ; options/groupes d’options et listes de recherche personnalisées inclus.
- `components/forms/Form.js` : chargement du même contrat dans les Shadow DOM, tokens hérités du thème, typage natif correct et conservation du contrôle/curseur pendant la saisie. Les raccourcis globaux reconnaissent aussi les champs encapsulés via `composedPath()` : écrire « t » ne change plus le thème.
- `sw.js` : cache v106 et nouvelle feuille précachée. Aucune réponse métier n’est mise en cache.

Les `!important` sont confinés aux propriétés d’apparence du contrat central pour empêcher les anciens sélecteurs par identifiant et styles inline de dissocier à nouveau texte et fond. Les exclusions de types utilisent `:where()` pour ne pas augmenter la spécificité : focus, erreur, succès et surfaces lecture seule/désactivées restent réellement prioritaires. La recette vérifie leurs couleurs sémantiques exactes, pas seulement un ratio minimal. Dimensions, masquage, droits, données, événements et validation métier restent inchangés.

## Tokens

| Rôle | Clair | Sombre |
|---|---|---|
| Texte, curseur | `#192c29` | `#edf5ef` |
| Placeholder / option désactivée | `#53655e` | `#b3c5b9` |
| Fond | `#ffffff` | `#1b2e26` |
| Fond lecture seule / désactivé | `#edf2ed` | `#23392e` |
| Bordure | `#718279` | `#91a99b` |
| Focus / sélection de choix | `#176b51` | `#a0d6b1` |
| Erreur | `#a12f29` | `#ffaaa3` |
| Validation positive explicite | `#176b51` | `#a0d6b1` |

Préfixe : `--field-`. `color`, `-webkit-text-fill-color`, `caret-color`, fond et opacité sont liés. Les placeholders ne sont pas rendus semi-transparents. Les champs désactivés restent lisibles, sans redevenir interactifs. Les états positifs ne sont pas déduits arbitrairement d’un champ simplement non invalide.

Les options sélectionnées et résultats de recherche pointés ont un fond de focus contrasté et un texte inverse. `color-scheme` suit le thème : menus natifs et contrôles date/heure n’utilisent plus un schéma contradictoire. L’autofill utilise le texte et une surface intérieure explicites ; pas de transition de plusieurs milliers de secondes pour masquer son état.

Les couleurs système sont respectées en mode `forced-colors`. Ne pas désactiver l’adaptation native avec `forced-color-adjust: none`.

## Recette reproductible

```sh
.venv/bin/python -m pytest tests/test_ui_field_contrast.py -q
npm run ui:fields:browser -- /chemin/hors-depot/preuves
npm run ui:fields:forms -- /chemin/hors-depot/preuves/formulaires
npm run ui:fields:shadow -- /chemin/hors-depot/preuves/shadow
# Variante pytest opt-in :
UI_FIELD_BROWSER=1 .venv/bin/python -m pytest tests/test_ui_field_browser.py -q
```

Le navigateur utilise l’application réellement servie sur le port 8000. Il parcourt la navigation autorisée dans les deux thèmes, aux largeurs 1440, 1280, 834 et 390 px ; relève les styles calculés, attend la fin des transitions de visibilité et contrôle texte, placeholder et opacité effective. Il saisit également une valeur dans la véritable modale de création, sans la soumettre.

Un laboratoire **explicitement identifié**, ajouté uniquement dans le DOM du navigateur de test, couvre les variantes natives rares : texte, recherche, mot de passe, email, URL, téléphone, nombre, date, date/heure, heure, mois, semaine, textarea, select, fichier, éditable et combobox. Il exerce les états applicables : rempli, hover, focus, erreur, succès, lecture seule et désactivé ; vérifie aussi la bordure et le focus. L’autofill est exercé via le pseudo-état du moteur Chromium, sans utiliser ni enregistrer d’identifiants réels. Les options natives sont ouvertes au clavier et photographiées. Une recette dédiée aux véritables composants Shadow DOM vérifie aussi la saisie continue au clavier, les types email/mot de passe, les valeurs nulles versus zéro, les états, la préservation du focus et le maintien effectif du thème. Une seconde recette ouvre et annule les véritables formulaires dynamiques de création et de modification disponibles ; leurs valeurs préremplies restent issues des données réelles. Elle exerce aussi la recherche globale et ses choix personnalisés. Aucun champ factice n’est installé dans l’application livrée, aucune réponse API n’est remplacée.

Les requêtes autres que GET/HEAD sont bloquées et comptées. Les saisies du test ne sont ni soumises ni sauvegardées. Les données utilisateur et le serveur existant sont conservés.

### Portée des preuves

Le contrôle impose 4,5:1 pour texte et placeholders, y compris sur les surfaces désactivées/lecture seule ; 3:1 pour bordure et focus. Il ne constitue pas une certification WCAG complète de l’application. Le navigateur de recette est Chromium Linux ; le rendu des fenêtres de choix et gestionnaires d’identifiants externes propres à d’autres systèmes doit rester une vérification de plateforme, pas une certification déduite du CSS.
