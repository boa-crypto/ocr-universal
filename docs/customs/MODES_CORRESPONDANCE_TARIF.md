# Modes littéraux des critères tarifaires — lot 48

Complément de la [recherche multicritère](RECHERCHE_TARIF_CRITERES.md) et de ses
[positions Unicode](EXTRAITS_TARIF_CRITERES.md). Pas nouvelle recherche juridique
ou sémantique : même lot en quarantaine, seuls ses libellés FR/AR sont interrogés.

## Contrat

`match_mode` facultatif, strictement `sous_chaine` (défaut historique) ou
`mots_entiers`. Type/valeur inconnus refusés avant lecture du lot par le service.
API : enum HTTP 422. Interface : liste fermée, aucun HTTP si mode invalide.

```sh
unocr customs-tariff-criteria LOT --matiere acier --match-mode mots_entiers
```

API inchangée :
`GET /api/v1/customs-review/lots/ID/tariff-criteria?matiere=acier&match_mode=mots_entiers`.
Exemple de requête, pas proposition de classement ou propriété matière certifiée.

- `sous_chaine` : tout terme normalisé peut apparaître à l'intérieur d'un mot.
  « acier » correspond à « glacier ». Ce comportement existant reste le défaut.
- `mots_entiers` : chaque terme doit être une unité entière dans le libellé
  **après normalisation existante**. « acier » correspond à « acier inox », pas
  « glacier » ou « aciers ». « معدات » ne correspond pas à « المعدات » ou « معداتهم ».
- Tous les termes de tous les critères restent conjoints sur **la même ligne**,
  FR/AR pouvant contribuer. Plusieurs mots dans une requête ne deviennent pas une
  phrase ordonnée/contiguë : ils sont toujours des termes indépendants en ET.
- Ponctuation, tirets, underscores et espaces sont des séparateurs après
  normalisation ; accents, marques arabes et tatweel sont neutralisés pour recherche.
  Pas flexion, stemming, suppression d'article arabe, segmentation linguistique,
  synonyme ou traduction. Ce sont des unités normalisées, pas une grammaire FR/AR.
- NFKD peut créer des unités à l'intérieur d'un caractère source : « ¼ » se normalise
  en « 1 4 » et peut correspondre au terme « 4 ». Le span original encadre alors le
  caractère entier, sans prétendre qu'il contient littéralement le chiffre seul.
- Préfixe de code seul : même résultat pour les deux modes, sans terme/extrait créé.

## Positions, restitution et export

`filtres.match_mode` conserve le choix exact. `mode` vaut
`conjonction_criteres_sous_chaines` ou `conjonction_criteres_mots_entiers`.
Les avertissements ne qualifient plus le mode mots entiers de sous-chaînes.

Même mode pour chercher et localiser : dans « glacier acier », la première
correspondance entière d'« acier » commence à **8**, pas à 2. Projection Unicode
originelle, première occurrence **admissible selon le mode**, bornes et troncature
du lot 47 conservées. Les unités ne deviennent pas des indices du texte normalisé.

Suite de page : réapplication du mode du rapport, même si le brouillon a changé.
Un ancien rapport sans `filtres.match_mode` utilise le défaut historique ; un
rapport portant un mode inconnu ne propose pas de suite. Export partiel JSON
conserve le filtre et les positions, même contrôleur hors ligne et limite 10 Mio.
Pas changement de schéma, d'audit (`recherche_tarif_criteres`) ou d'autorisation.

## Correctif d'effacement de l'interface

Le sélecteur ajouté a exposé un défaut préexistant : les fieldsets multicritère,
PDF fiscal et rapprochement de description PDF étaient rattachés hors du conteneur
vidé lors d'un refus d'accès/audit. Leurs inputs pouvaient donc rester visibles.
Les trois sont désormais dans le conteneur des outils : **401, 403 ou 503 les
retirent tous**, ainsi que les résultats/extraits. Aucun droit serveur modifié.
Les tests contrôlent désormais l'absence de tout fieldset, pas seulement d'un select.

Cache : `v68-whole-word-criteria`. Ni attribut certifié, score, IA, classement,
notes/exclusions juridiques, taux calculé ou validation ajoutés. Le parcours complet
avant pagination et les autres limites de quarantaine restent inchangés.
