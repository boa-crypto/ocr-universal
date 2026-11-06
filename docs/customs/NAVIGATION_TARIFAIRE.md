# Navigation tarifaire documentaire — lot 12

2026-11-06. **Hiérarchie reçue en quarantaine, sans classement ou tarif applicable.**

## Périmètre

`customs_reference.tariff_tree.parcourir_tarif` contrôle/rejoue un lot tarifaire
complet avant de présenter ses enfants directs. Ni index parallèle ni exploration
de fichiers à partir d’un identifiant de parent. Les références et libellés reçus
sont conservés ; aucun parent ou désignation n’est reconstruit depuis un préfixe.

| Niveau demandé | Parent exact requis | Enfants présentés |
|---|---|---|
| `sections` | aucun ; tout parent fourni est refusé | sections déclarées |
| `chapitres` | ID de section, y compris Unicode | chapitres de cette section |
| `positions` | code chapitre, 2 chiffres ASCII | positions de ce chapitre |
| `sh6` | code position, 4 chiffres ASCII | sous-positions SH6 de cette position |
| `codes` | SH6, 6 chiffres ASCII | lignes code10 de ce SH6 |

La transition SH6 → code10 reflète le contrat existant : aucune subdivision
nationale intermédiaire à huit chiffres n’est inventée. Les lignes code10 conservent
leurs champs fiscaux inconnus ; les mesures ne sont pas jointes à cette navigation.
Consulter la [fiche documentaire](FICHE_TARIFAIRE.md) pour les mesures déclarées.
Aucun taux applicable, calcul ou candidat de classement n’est choisi.

## Correspondance et pagination

Les parents sont des chaînes exactes, sans trim, conversion des chiffres Unicode,
zfill ou recherche par préfixe. Un parent non racine doit être non blanc, sans
caractère de contrôle, de 256 caractères maximum. Les IDs de section ne sont pas
convertis en numéros : le classement est lexicographique par ID/code reçu, pas
une chronologie ou une conversion des numéros romains.

`limit` : entier 1–100 (défaut 20), `offset` : entier 0–1000000 (défaut 0).
Chaque réponse comporte le niveau, le parent exact et son objet déclaré s’il
existe, la source et l’empreinte du manifeste, `total_enfants_declares`,
`enfants_declares`, `decalage_suivant` (null en fin) et `niveau_suivant` (null aux
feuilles code10). Les références de page/feuille/ligne sont celles des objets reçus.

- Racine : `parent_trouve=null`, car il n’y a pas de parent à rechercher.
- Parent existant sans enfant : `parent_trouve=true`, total zéro.
- Parent non trouvé : `parent_trouve=false`, parent déclaré null et enfants vides.
- Page hors limites : total réel du lot conservé, liste vide ; le parent reste
  indiqué présent s’il existe.

Ces absences ne prouvent ni inexistence nationale, ni abrogation, ni erreur de la
hiérarchie : la source peut contenir une hiérarchie plus large que ses lignes reçues.
Aucune complétude nationale ne découle du nombre d’enfants.

## Accès local, HTTP et écran

```sh
PYTHONPATH=src python -m unocr.cli customs-tariff-tree /chemin/lot
PYTHONPATH=src python -m unocr.cli customs-tariff-tree /chemin/lot \
  --level codes --parent "$SH6_EXACT" --limit 20 --offset 0
```

JSON en lecture seule : code retour 0 pour une lecture réussie (y compris parent
absent/vide), 2 pour un refus. Aucun fichier résultat ou archive n’est écrit par
cette commande ; les habilitations d’accès au disque restent nécessaires.

GET `/api/v1/customs-review/lots/{lot_id}/tree` avec `level`, `parent`, `limit`,
`offset`. Droits nominatifs et registre épinglé de revue habituels, audit
`navigation_tarif` avec IDs de lots, réponse `no-store`. Type juridique Code refusé
422 ; parent absent annoncé en 200 avec son statut explicite ; lot inconnu 404 ;
paramètres invalides 422. Les contrôles de manifeste comparent l’épingle avant
lecture au manifeste effectivement utilisé. Aucun choix de chemin ou URL HTTP.
Ce n’est pas l’API publique future d’une nomenclature officiellement validée.

Dans **Administration → Revue douanière · quarantaine** : choisir un lot tarifaire,
un niveau et, hors racine, un ID/code parent exact puis **Parcourir la hiérarchie
tarifaire**. Le champ parent est désactivé à la racine et n’est pas transmis ;
le groupe est désactivé pour les lots Code juridiques. Limite/décalage indépendants
de ceux des autres consultations. Les enfants sont présentés en JSON lisible :
copier l’ID/code choisi puis sélectionner le niveau suivant, ou utiliser les
boutons « Enfants de… » ajoutés au [lot 14](NAVIGATION_ASSISTEE.md). Il ne s’agit pas encore
d’un arbre graphique dépliable. Mêmes protections de rendu texte/réponses tardives
que le reste de la revue. Coque service worker v44 ; API toujours hors cache.

## Limites

Un seul lot, pas de données officielles acquises par cette navigation, de
reconstruction normative, de rapprochement fiscal, de classification IA, de
validation humaine, de publication ou de calcul. Source et transcriptions restent
non vérifiées ; SHA/rejeu ne prouvent pas authenticité/exactitude/exhaustivité.
Les limites de taille, de charge et de concurrence des lecteurs s’appliquent.
Qualification JSDOM/backend isolé, pas homologation visuelle/accessibilité complète
ou benchmark sur tarif national réel. [Rapport](RAPPORT_LOT12.md).

Lot 23 : cette navigation reste une projection SH6→code10. Les [subdivisions
intermédiaires explicitement déclarées](SUBDIVISIONS_NATIONALES.md) sont restituées
dans la fiche, sans nouveau niveau de navigation ajouté ici.

[Lot 24 : niveau subdivisions et enfants directs mixtes](NAVIGATION_SUBDIVISIONS.md).
La projection historique reste disponible ; la vue détaillée préserve les liens
explicitement déclarés, sans déduire de parent par préfixe.
