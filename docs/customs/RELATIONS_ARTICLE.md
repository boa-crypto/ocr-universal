# Relations documentaires d’une version exacte d’article

Lot 29 — 7 novembre 2026. Lecture seule, relations déclarées non validées.

## Périmètre

Choisir **l’ID exact d’une version** dans un seul lot Code. Seules les relations
de `lot.relations` dont `origine_id` ou `cible_id` égale cet ID sont retenues.
Il n’y a ni recherche par numéro, élargissement aux versions de même numéro,
parcours transitif, reconstruction depuis `articles_lies` ou inférence de similarité.

`sortante` signifie que la version sélectionnée est `origine_id` ; `entrante`
qu’elle est `cible_id`. Ce sens est technique, pas une chronologie juridique.
Les cinq types déclarés sont `modifie`, `complete`, `abroge`, `rectifie`,
`renvoie_a`. Leur lecture ne valide ni leur qualification juridique ni leur preuve.

Cette vue complète l’historique existant : celui-ci part d’un numéro d’article et
inclut les liens de toutes les versions reçues de ce numéro ; la nouvelle vue
part d’une seule version et permet de filtrer le sens/type sans fusionner ces
périmètres. Les deux lectures réutilisent le même modèle et le même rejeu du lot.

## CLI et API

```sh
unocr customs-code-article-relations CHEMIN_LOT --id ID_VERSION_EXACT \
  --direction entrantes --relation-type modifie --limit 20 --offset 0
```

```text
GET /api/v1/customs-review/lots/{lot_id}/article-relations
    ?article_id=ID_VERSION_EXACT&direction=entrantes&relation_type=modifie
    &limit=20&offset=0
```

Sens : `tous` par défaut, `entrantes`, `sortantes`. Type absent = tous les types
reçus, pas une chaîne vide. Les filtres sont combinés par ET, puis la liste est
triée par ID de relation (ordre Unicode, pas chronologique), puis paginée.

ID exact non blanc de 256 points de code maximum, sans contrôle/substitut Unicode
isolé ; limite entière 1–100 ; décalage entier 0–1 000 000. Les paramètres invalides
sont refusés avant lecture. Aucun chemin de fichiers ou URL n’est reçu par HTTP.

Même accès nominatif/habilitation de revue, registre épinglé, rejeu, audit obligatoire
et `no-store`. Tarif ou paramètres invalides : 422 ; lot incohérent/empreinte changée :
409 ; audit indisponible : 503 sans résultat. CLI hors contrat d’audit HTTP.
Les URLs peuvent apparaître dans les journaux HTTP d’infrastructure ; les événements
métier de cette lecture n’enregistrent pas les IDs d’article ou justifications.

## Réponse

- `article_trouve` et `version_declaree` distinguent ID inconnu et version connue
  sans lien ; absence de relation reçue ne prouve ni absence de droit ni modification.
- `total_relations_incidentes` et `totaux_incidents_par_sens` décrivent les liens
  avant filtres ; `total_relations_filtrees` compte ceux satisfaisant les filtres.
- `relations_declarees` contient la page : chaque entrée conserve
  `relation_declaree` (origine/cible/type/justification/référence), le sens relatif et
  `autre_version_declaree` (métadonnées sans texte intégral).
- `documents_declares_page` contient la source de la version sélectionnée, celles
  des versions voisines et les sources de preuve des seules relations de cette page.
  Aucun document d’un autre lot ou URL distante n’est ajouté.
- `decalage_suivant=null` indique la fin ; hors fin : page vide. Les sources de
  preuve/voisins d’une page précédente ne sont pas conservées dans cette page.
- `relation_juridique_etablie=false`, `preuve_rapprochee_pdf=false`,
  `transcription_verification=non_verifiee`, `publication_active=false`.

Le contrat d’import existant vérifie déjà les extrémités, la référence à la source
originaire et les contrôles documentaires de cycles/dates. Cela ne certifie pas
l’authenticité du document ou le contenu juridique du lien. Les renvois réciproques
peuvent exister sans entraîner de parcours automatique.

## Interface et export

La revue contient « Relations déclarées d’une version exacte ». Saisir l’ID, choisir
sens/type/pagination puis « Inspecter les relations déclarées ». La lecture d’article
propose aussi « Inspecter les relations de cette version ».

Les actions permettent d’ouvrir les autres versions de cette page, sans doublonner
les mêmes IDs, et de lire les PDF déclarés comme preuves. Le bouton PDF indique
explicitement **page 1** : aucun localisateur libre ou numéro de page imprimée
n’est interprété. L’opérateur peut ensuite choisir une autre page physique dans le
lecteur PDF existant. Lire un PDF ne rapproche pas automatiquement la justification
et ne change pas son statut. Pas d’ouverture d’URL distante ou de PDF brut.

Les suites conservent version/sens/type/limite ; changements de lot/compte, réponses
remplacées et navigation invalident les anciennes actions. Tarif désactivé.
Justifications/localisateurs sont rendus comme texte, jamais comme HTML exécuté.

L’export partiel existant relit la route avec les droits/audit courants. Whitelist
et schéma d’enveloppe version 1 mis à jour ; contrôle hors ligne structurel et
déclaratif seulement. Les anciens contrôleurs stricts peuvent refuser cette route.
Ce n’est ni un graphe juridique complet ni un certificat d’authenticité.

## Limites

Le lot et les liens incidents sont chargés/triés en mémoire. La pagination borne
le nombre de relations renvoyées, pas la taille de chaque justification ou la RAM
globale. Export navigateur limité à 10 Mio selon les règles existantes. Pas de
relations inter-lots ou articles↔tarif/taxes/régimes, de création/édition de liens,
validation humaine signée, consolidation ou restitution de droit applicable à date.
Aucune référence non vérifiée autorisée pour un calcul douanier réel.

## Extension lot 30

Un fragment de justification peut désormais être recherché littéralement dans une
page explicitement choisie de sa source, sans que l’inspection seule ne déclenche
ce contrôle ou ne valide le lien : [RAPPROCHEMENT_JUSTIFICATION_PDF.md](RAPPROCHEMENT_JUSTIFICATION_PDF.md).
