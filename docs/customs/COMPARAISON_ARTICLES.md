# Comparaison littérale de deux versions d’article

Livré le 6 novembre 2026 — revue documentaire non validée, lecture seule.

## Périmètre et interprétation

Deux IDs exacts sont explicitement choisis dans **un même lot Code archivé**.
Les mots « avant » et « après » décrivent uniquement l’ordre demandé. Ni numéro
commun, ni ressemblance, ni dates ne permettent d’inférer une succession juridique.
Les deux IDs peuvent désigner la même version ; cela ne crée aucune relation.

Le service retire le préfixe strictement commun puis le suffixe strictement commun,
sans chevauchement. Il restitue les deux blocs centraux restants. Il ne calcule pas
un diff minimal, un alignement de lignes/mots ou une consolidation. Des passages
identiques internes peuvent donc demeurer dans les blocs différents.

Aucune normalisation, traduction, correction de transcription, traitement OCR,
comparaison visuelle PDF ou détermination du droit applicable. Espaces, retours
ligne, accents combinés et caractères arabes sont comparés tels que transcrits.
L’unité est le point de code Unicode Python, pas l’octet, UTF-16 ou le graphème.

## CLI

```sh
unocr customs-code-article-diff CHEMIN_LOT \
  --before-id ID_EXACT_AVANT --after-id ID_EXACT_APRES \
  --field texte_integral --limit 4000 --before-offset 0 --after-offset 0
```

Champs : `texte_integral`, `texte_francais`, `texte_arabe`, `texte_origine`,
`texte_modificatif`. Limite : 1 à 16 000 ; chaque décalage : 0 à 67 108 864.
Les décalages sont relatifs au **bloc différent**, pas au texte intégral. Reprendre
le `decalage_suivant` du côté voulu ; `null` indique la fin. Un décalage hors fin
produit un fragment vide. Les paramètres sont contrôlés avant chargement du lot.

## API et interface existantes

```text
GET /api/v1/customs-review/lots/{lot_id}/article-diff
    ?avant_id=ID_EXACT_AVANT&apres_id=ID_EXACT_APRES
    &field=texte_integral&limit=4000&offset_avant=0&offset_apres=0
```

Même autorisation nominative, registre épinglé/rejeu, audit obligatoire et
`Cache-Control: no-store` que les autres lectures de revue. Lot tarif refusé 422 ;
paramètres invalides 422 ; audit indisponible 503 sans résultat. La CLI ne relève
pas du contrat d’audit HTTP. Les IDs transmis dans les URLs peuvent apparaître dans
les journaux HTTP d’infrastructure ; l’événement métier n’enregistre pas les textes.

Dans la revue existante, saisir les deux IDs dans « Comparaison littérale de deux
versions exactes ». Le champ et la limite réutilisent le formulaire de lecture.
Les décalages sont indépendants et les boutons « Suite du bloc avant/après »
reprennent l’identité et les paramètres de la réponse. Les actions deviennent
inertes après remplacement, changement de lot ou de compte. Le tarif désactive
cette lecture. Les textes sont affichés sans interprétation HTML.

L’export JSON partiel existant relit cette route avec les droits et l’audit courants.
La whitelist et son schéma acceptent `/article-diff`. Le contrôle hors ligne
atteste seulement la compatibilité structurelle/déclarative, jamais l’authenticité.
Les anciens contrôleurs stricts peuvent refuser cette nouvelle route.

## Résultat et limites

`champs_comparables=false` si un ID ou un champ manque : `textes_identiques=null`,
aucun fragment substitué depuis une autre langue. Consulter `article_trouve` et
`champ_renseigne` de chaque côté ; ce résultat n’est pas une preuve d’absence légale.
Si les deux textes sont identiques, les blocs sont vides et le préfixe couvre le
texte entier, sans suffixe supplémentaire.

Chaque côté conserve les métadonnées de version, la référence documentaire et le
document source déclaré. Les relations directes entre les deux IDs sont recopiées
sans qualification ; `relation_juridique_etablie=false`, même si une relation était
déclarée dans le lot. Empreintes/rejeu ne certifient ni authenticité ni fidélité au PDF.

Le calcul préfixe/suffixe est linéaire ; le lot et les blocs centraux peuvent être
chargés/copiés en mémoire. La pagination borne le fragment retourné, **pas la RAM
globale**. Pas de comparaison inter-lots, restitution juridique à date, validation
humaine signée ou publication active. Les sources manquantes restent manquantes.
