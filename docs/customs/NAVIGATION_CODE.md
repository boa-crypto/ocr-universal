# Navigation hiérarchique documentaire du Code

Lot 26 — 6 novembre 2026. Lecture seule de lots Code en quarantaine.

## Identité et périmètre

La racine liste les documents déclarés, y compris ceux sans article transcrit.
Choisir une source puis descendre les chemins `hierarchie` effectivement reçus.
L’identité d’un nœud est **source ID + chemin complet des couples
`niveau`/`identifiant`**, et non le numéro d’article, l’intitulé ou le préfixe d’un ID.
Deux documents ne sont jamais fusionnés, même pour un chemin identique.

Les enfants sont les prochains éléments du chemin transcrit : si un livre, titre
ou chapitre n’est pas fourni, il n’est pas reconstitué. Le contrat d’import existant
continue à exiger `texte_legislatif` initial et un niveau `article` cohérent avec le
numéro ; aucun assouplissement des archives ni du schéma métier n’a été introduit.
Une version devient lisible au terme de son chemin, après ses éventuels paragraphes,
alinéas ou annexes déclarés. Aucun découpage textuel en alinéas n’est effectué.

Les intitulés divergents d’un même nœud sont conservés dans `intitules_declares`,
y compris `null` lorsqu’absent : aucune correction ou qualification juridique.
Le compteur `nombre_versions_transcrites` compte des versions du lot, pas des
articles distincts du Code national ni un taux de complétude.

## CLI

```sh
unocr customs-code-tree CHEMIN_LOT
unocr customs-code-tree CHEMIN_LOT --source ID_SOURCE
unocr customs-code-tree CHEMIN_LOT --source ID_SOURCE \
  --path '[{"niveau":"texte_legislatif","identifiant":"ID_TEXTE_RECU"}]' \
  --limit 20 --offset 0
```

Les IDs ci-dessus sont des paramètres à remplacer, pas des données réglementaires.
Le chemin JSON ne contient que `niveau` et `identifiant`, pas `intitule`.
Les clés dupliquées, niveaux inconnus/désordonnés/dupliqués et sélecteurs mal formés
sont refusés avant lecture. Source requise pour un chemin non vide. Racine par
défaut : source absente et chemin `[]`.

Bornes : source ID non blanc, sans caractères de contrôle, 256 points de code
maximum ; chemin JSON 8 192 caractères, 10 niveaux maximum ; identifiant de niveau
256 points de code maximum, sans substitut Unicode isolé. Limite 1–100, décalage
0–1 000 000. Les anciens identifiants dépassant ces bornes ne sont pas navigables
par cette interface : ils ne sont ni tronqués ni réécrits. Les contraintes JSON
s’ajoutent à celles des lots, elles ne garantissent pas leur authenticité.

## API, interface et export

```text
GET /api/v1/customs-review/lots/{lot_id}/code-tree
    ?source_id=ID_SOURCE&path=JSON_CHEMIN&limit=20&offset=0
```

Encoder les paramètres avec le client HTTP ; aucun chemin de système de fichiers
n’est accepté. La réponse inclut `archive`, `document_declare`, `source_id_exact`,
`chemin_exact`, `parent_trouve`, `total_enfants_declares`, `enfants_declares` et
`decalage_suivant`. À la racine globale, `parent_trouve=null`. Un document connu
sans transcription a `parent_trouve=true` et zéro enfant ; une source ou un chemin
inconnu donne `false`, pas une preuve d’absence légale.

Tri : documents par ID ; niveaux par ordre du contrat puis identifiant exact ;
versions terminales ensuite, par ID. Pagination commune de la liste d’enfants.
Les variantes d’intitulés sont triées avec `null` en premier puis ordre Unicode.
Ce tri n’est ni un ordre naturel des numéros ni une chronologie juridique.

La route reprend les droits nominatifs, le registre épinglé, le rejeu et l’audit
obligatoire de revue. Tarif ou paramètres invalides : 422 ; refus de droits selon
le contrôle existant ; audit indisponible : 503 sans résultat. `no-store` conservé.
La CLI reste hors contrat d’audit HTTP. Les URLs peuvent figurer dans les journaux
HTTP d’infrastructure ; elles ne doivent contenir aucun secret d’authentification.

Dans la revue existante : « Parcourir la hiérarchie du Code », puis boutons
« Parcourir le document… », « Parcourir le niveau… », « Lire la version… ».
« Remonter… » retire le dernier élément ou retourne à la liste des documents.
La pagination conserve source/chemin ; changement de lot/compte ou résultat
remplacé rend les anciennes actions inertes. Le formulaire est désactivé sur tarif.
Les références et libellés sont rendus comme texte, sans HTML exécuté.

L’export partiel existant relit la route avec droits et audit courants ; la whitelist
et `ExportRevue.schema.json` acceptent `code-tree`. Le contrôle hors ligne demeure
structurel et déclaratif. Les anciens contrôleurs stricts peuvent refuser cette
nouvelle route d’enveloppe version 1. Ni corpus complet ni binaire PDF exporté.

## Limites

Projection technique des transcriptions d’un seul lot, pas arbre juridique officiel,
consolidation, restitution à date, filiation ou classement tarifaire. L’arbre ne
matérialise pas des parties non transcrites. Empreintes/rejeu ne valident ni
source officielle ni fidélité au PDF. Le lot et les regroupements sont en mémoire ;
la pagination borne la réponse, pas la consommation RAM globale. Pas d’arbre
graphique dépliable ni recette visuelle/accessibilité complète de navigateur réel.
