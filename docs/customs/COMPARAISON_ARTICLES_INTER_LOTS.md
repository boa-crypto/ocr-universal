# Comparaison littérale de versions d’article entre deux lots

Lot 28 — 7 novembre 2026. Lecture seule de deux archives Code explicitement choisies.

## Sélection et identité

Choisir un lot avant, un lot après et un ID exact de version dans chacun. Les IDs
sont **locaux à leur lot** : deux chaînes identiques ne prouvent ni identité de
source, même article juridique ou succession. Les deux sélections peuvent même
viser explicitement le même lot ; le rapport conserve la paire de provenances.
Aucun appariement par numéro, titre, date, langue ou ressemblance.

Le même moteur que la comparaison du lot 25 retire le préfixe puis le suffixe
strictement communs, sans chevauchement, et restitue les deux blocs centraux
indépendamment paginés. Unicode Python sans normalisation, pas diff minimal,
traduction, alignement mot à mot, correction ou consolidation.

## CLI

```sh
unocr customs-code-article-diff LOT_AVANT --after-lot LOT_APRES \
  --before-id ID_VERSION_AVANT --after-id ID_VERSION_APRES \
  --field texte_integral --limit 4000 --before-offset 0 --after-offset 0
```

Sans `--after-lot`, le contrat existant de comparaison dans un seul lot est
conservé, avec `archive` simple. Avec l’option, les deux archives sont contrôlées
et rejouées ; les sources de chaque côté restent celles de leur propre lot.
Les paramètres d’ID/champ/pagination sont validés avant les deux chargements.

Bornes inchangées : IDs exacts non blancs, sans contrôle, 256 points de code
maximum ; cinq champs transcrits du lecteur d’article ; limite 1–16 000,
décalages indépendants 0–67 108 864 relatifs aux **blocs différents**. Positions
en points de code Unicode Python, pas octets, UTF-16 ou graphèmes.
Un champ ou ID absent rend la comparaison indisponible et `textes_identiques=null`,
sans substitution d’une langue. Hors fin : fragment vide, pas de suite.

## API et provenance double

```text
GET /api/v1/customs-review/article-diff
    ?avant=ID_LOT_AVANT&apres=ID_LOT_APRES
    &avant_id=ID_VERSION_AVANT&apres_id=ID_VERSION_APRES
    &field=texte_integral&limit=4000&offset_avant=0&offset_apres=0
```

La route de comparaison intra-lot `/lots/{lot_id}/article-diff` reste inchangée.
La nouvelle route ne reçoit aucun chemin de fichiers. Les deux lots doivent être
inscrits et de type Code ; les deux manifestes sont épinglés avant lecture puis
rapprochés des empreintes réellement retournées. Le succès d’audit contient les
identités et empreintes des lots, pas les IDs d’article ni les textes. Les URLs
peuvent toutefois apparaître dans les journaux HTTP d’infrastructure.

Réponse : `type_rapport=comparaison_litterale_versions_article_inter_lots`,
`lots_exacts={avant,apres}`, `archives={avant,apres}`, sans `archive` simple.
Chaque côté possède ses propres métadonnées, référence et document source.
L’ordre demandé n’établit aucune chronologie ou succession juridique.

`relations_directes_declarees=[]` dans ce mode : les relations internes des lots
**ne sont pas transposées** entre deux espaces d’IDs. Cela ne signifie pas absence
de relation juridique réelle ; aucune relation inter-lots n’est recherchée ou
établie. `relations_inter_lots_etablies=false` et
`relation_juridique_etablie=false`. Les relations locales restent consultables
par les lectures documentaires existantes dans chaque lot.

Même autorisation nominative et `no-store`. Types/paramètres invalides : 422 ;
lot inconnu : 404 ; incohérence/empreinte différente d’un côté : 409 ; audit
indisponible : 503 sans résultat. La CLI reste hors contrat d’audit HTTP.

## Interface et export

Dans la revue existante, sélectionner « Lot à contrôler / rechercher » et « Lot
après », saisir les deux IDs dans le formulaire de comparaison d’articles, puis
« Comparer les versions entre deux lots Code ». Le champ et la limite restent
ceux du formulaire de lecture. Le bouton intra-lot conserve son comportement.
Les suites indépendantes conservent la paire de lots et les paramètres retournés.

« Lire la version avant/apres du lot… » bascule vers le bon lot et lit l’ID exact
correspondant. Changer le lot après invalide les requêtes en cours et efface les
anciennes actions, tout comme les gardes existantes de lot/session/navigation.
Un tarif après est refusé côté interface avant requête ; le serveur recontrôle.

L’export JSON partiel relit la nouvelle route sous les droits/audit courants.
La whitelist, le schéma et le contrôle hors ligne exigent une provenance double
sur cette route ; une provenance simple ou ambiguë est refusée. Le contrôle reste
structurel/déclaratif, jamais preuve d’authenticité. Les anciens contrôleurs stricts
peuvent refuser cette nouvelle route de l’enveloppe version 1.

## Limites

Deux lots peuvent être entièrement chargés/rejoués et les blocs copiés en mémoire.
La pagination ne borne pas la RAM globale. Les contrôles ne constituent pas une
transaction de lecture multi-dossiers ; l’épingle et le rejeu vérifient la cohérence
locale des données consommées, pas une immutabilité WORM ou une authenticité éditeur.

Pas de filiation juridique, consolidation, restitution à date, rapprochement au PDF,
validation humaine ou publication. Statuts conservés : non vérifié/non validé,
publication inactive. Aucune référence utilisable pour un calcul douanier réel.
