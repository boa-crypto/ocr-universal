# Navigation détaillée des subdivisions déclarées — lot 24

2026-11-06. **Lecture seule d’un lot non validé, aucune hiérarchie nationale reconstruite.**

## Deux vues complémentaires

La vue historique `codes` conserve son sens : projection de **tous les codes10 du
SH6**, même s’ils ont une subdivision intermédiaire déclarée. Les anciens clients
peuvent continuer à l’utiliser. Elle ne doit pas être interprétée comme une liste
d’enfants directs sans intermédiaire.

Le nouveau niveau **`subdivisions`** accepte un parent exact SH6 ou subdivision
(6 à 9 chiffres ASCII). Il retourne ses seuls enfants directement déclarés :

- subdivision avec `code_parent` égal au parent demandé ;
- code10 avec `code_subdivision_nationale` égal au parent intermédiaire ;
- sous un SH6 seulement, code10 de ce SH6 dont le lien intermédiaire est null.

Un code10 dont le préfixe ressemble à une subdivision mais dont le lien est null
reste directement sous le SH6. **Aucun parent n’est inféré**. Le même rapport peut
contenir subdivisions et codes10 : pagination commune, ordre lexicographique par
code, sans perdre les lignes non rattachées à un intermédiaire.

## CLI, API et interface

```sh
PYTHONPATH=src python -m unocr.cli customs-tariff-tree /chemin/lot --level subdivisions --parent CODE_PARENT_EXACT --limit 20 --offset 0
```

API existante :
`GET /api/v1/customs-review/lots/{lot_id}/tree?level=subdivisions&parent=CODE_PARENT_EXACT`.
Mêmes habilitations nominatives, épingles, contrôles/rejeu, no-store et audit.
Aucune nouvelle route ou écriture métier.

Le rapport utilise `mode_navigation=enfants_directs_declares_mixtes` et
`type_noeud=subdivision_nationale|code10` pour chaque enfant. Les métadonnées,
liens explicites et références reçus sont conservés. Parent inconnu :
`parent_trouve=false`, page vide ; pas de preuve d’absence nationale.

Dans la coque de revue, le menu conserve **Codes dix chiffres projetés** et ajoute
**Enfants directs (parent : SH6 / subdivision)**. Depuis un SH6, « Enfants de… »
utilise la vue détaillée lorsque le serveur la propose ; une subdivision ouvre
ses enfants, un code10 ouvre sa fiche. Les boutons et la pagination reprennent les
gardes de requête/lot/session ; les types, liens, préfixes et bornes sont contrôlés.
Ce contrôle d’affichage ne remplace pas l’autorisation serveur.

Le champ historique `niveau_suivant=codes` d’une page SH6 reste présent ;
`niveau_suivant_detaille=subdivisions` propose la nouvelle vue. Un ancien client
ignorant ce champ continue vers la projection. Coque **v50-subdivisions**.

## Limites

Pas d’arbre graphique dépliable, fil d’Ariane complet, niveau national inventé,
classification tarifaire ou validation juridique. Une source/localisation et un
préfixe cohérents ne démontrent pas l’existence officielle ou l’applicabilité des
nœuds. Les limites de pagination et lecture de lot restent celles du service.
Aucun nouveau fichier officiel ; complétude nationale non établie.
[Qualification](RAPPORT_LOT24.md).
