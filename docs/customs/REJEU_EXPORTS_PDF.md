# Rejeu PDF sur autorisation locale explicite — lot 53

Extension du [rejeu typé](REJEU_EXPORTS_TYPES.md), après la
[provenance documentaire](REJEU_PROVENANCE.md). Un export ne suffit pas à autoriser
une extraction : l'opérateur doit fournir l'option locale **`--allow-pdf`**.

```sh
unocr customs-review-export-replay rapport.json --lot DOSSIER --lot-id ID --type-lot code --allow-pdf
```

Python : `verifier_rejeu_export(..., type_lot, autoriser_pdf=True)`. Argument nommé
facultatif, défaut **false**, type booléen strict (ni 1, ni chaîne "true"). Valeur
non booléenne refusée avant lecture de l'export. Aucune permission extraite du JSON,
aucun nouveau droit serveur, endpoint de chemins locaux ou consentement implicite.
Le contrôleur historique des seuls critères ne gagne pas cette option.

## Matrice ajoutée

Routes sous `/api/v1/customs-review/lots/ID/` :

| Route | Type | ID requis | Page |
|---|---|---|---|
| `pdf` | code | `document_id` | défaut 1 |
| `article-pdf-match` | code | `article_id` | requise |
| `relation-pdf-match` | code | `relation_id` | requise |
| `fiscal-pdf` | mesures | `document_id` | défaut 1 |
| `measure-pdf-match` | mesures | `mesure_id` | défaut 1 |

Toutes acceptent `page`, `limit`, `offset` ; `article-pdf-match` accepte aussi
`field`. Pas autre clé ni sélection de document substituée pour les rapprochements :
la source reste imposée par la référence déclarée de l'article/relation/mesure.
Type incompatible, identifiant/page requis manquants, doublons, encodages,
paramètres inconnus ou pagination non décimale refusés. `allow_pdf` dans la requête
est un paramètre inconnu, jamais une permission.

Sans autorisation, **toutes** ces routes sont refusées avant appel d'un lecteur,
même si le rapport affirme une absence d'article/fragment qui n'exigerait pas
d'extraction. Il n'y a pas d'exception déduite du contenu non fiable du rapport.
Les contrôles d'intégrité des autres routes peuvent toujours lire/hacher les PDF
d'une archive Code ; l'option régit le rejeu des extractions/rapprochements natifs,
pas toute lecture d'octets PDF.

## Extraction et comparaison

Services publics existants uniquement, avec leurs validations et contrôles :
archive rejouée, octets PDF revérifiés, page physique 1–10 000, fragment 1–16 000
points de code, offset 0–67 108 864 ; page native limitée à 200 000 caractères.
Worker PDFium séparé, délai parent 15 s, bornes Unix de CPU/mémoire best effort.
Ces limites ne constituent pas antivirus, bac à sable OS, quota global ou garantie
matérielle. Pas OCR, rendu, recherche de page automatique ou URL distante suivie.

Page sans texte, fragment absent ou version/mesure inconnue : même constat que le
service initial, sans inventer de fidélité ou de droit. L'absence d'objet peut
éviter l'extraction, mais exige quand même l'autorisation de cette route.
`rejeu_pdf_autorise` décrit la **permission effective**, pas le nombre ou la réalité
des extractions. True peut aussi accompagner un contrôle non PDF sans extraction.

Le rapport complet est comparé : texte natif, fragment, page/offset, positions,
constats, source/empreintes et tous les drapeaux de non-validation. Pas champ
ignoré pour obtenir une égalité. Une version différente de moteur/logiciel peut
produire un rejeu différent ; ce n'est pas une preuve de fraude.
PDF altéré/illisible, échec du lecteur ou bornes dépassées : refus générique, pas
rapport identique ni erreur de moteur recopiée. Codes CLI 0/1/2 inchangés.

## Limites

Ni authenticité officielle, signature, audit serveur, registre, validation humaine
ou droit applicable attestés. Présence littérale ≠ fidélité de l'article,
justification juridique ou vérification d'un taux/période/rattachement fiscal.
Pas transaction filesystem ni protection contre modification concurrente.

Copies PDF brutes (`pdf-source`) et comparaisons multi-archives toujours exclues
du rejeu JSON. Interface, cache v69 et droits HTTP inchangés ; aucune nouvelle
fonction de rejeu navigateur revendiquée. Les tests UI/API alimentent un contrôle
local hors ligne sur archives temporaires NON OFFICIELLES.

## Extension lot 54

[Comparaisons à deux archives](REJEU_DEUX_ARCHIVES.md) prises en charge par une
commande distincte à dossiers/IDs/types ordonnés. Cette commande ne lance pas de
worker PDF ; la permission locale PDF décrite ci-dessus reste propre au rejeu simple.
