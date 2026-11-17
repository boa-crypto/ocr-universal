# Rapprochement littéral d’un fragment d’article avec sa page PDF source

Lot 27 — 7 novembre 2026. Constat documentaire en lecture seule, pas validation.

## Périmètre

Sélection explicite d’un ID de version, d’un champ, d’un décalage, d’une limite et
d’une **page physique** à partir de 1. Le PDF est obligatoirement celui de
`article.reference.source_id` dans le lot contrôlé. Aucun document alternatif,
localisateur libre, numéro d’article ou URL n’est utilisé pour choisir la page.
Le numéro imprimé d’un JO ne permet pas de déduire la page physique.

Le fragment transcrit est recherché tel quel dans **le texte natif entier de cette
seule page**, dans la borne de 200 000 caractères. Les paramètres de fragmentation
portent sur l’article, pas sur la page PDF. Le service renvoie la première occurrence
seulement, sans compter les répétitions ni déterminer son emplacement juridique.
Pas de normalisation Unicode, d’espaces, de césures ou de retours ligne ; pas de
traduction, rapprochement flou, OCR, rendu graphique ou correction de transcription.

## CLI et API

```sh
unocr customs-code-article-pdf-match CHEMIN_LOT \
  --id ID_VERSION_EXACT --page 1 --field texte_integral --limit 4000 --offset 0
```

```text
GET /api/v1/customs-review/lots/{lot_id}/article-pdf-match
    ?article_id=ID_VERSION_EXACT&page=1&field=texte_integral&limit=4000&offset=0
```

`page` est obligatoire en CLI/API. Champs : `texte_integral`, `texte_francais`,
`texte_arabe`, `texte_origine`, `texte_modificatif`. Limite 1–16 000 ; décalage
0–67 108 864 ; page 1–10 000. ID exact non blanc de 256 points de code maximum,
sans contrôle/substitut Unicode isolé. Les paramètres sont validés avant lecture.

Même autorisation nominative, registre épinglé, audit obligatoire et `no-store`
que la revue. Tarif/paramètres invalides : 422 ; PDF illisible, chiffré, page absente
ou extraction hors limites : 409 ; audit indisponible : 503 sans résultat.
Un constat négatif ou indisponible dans un lot cohérent reste une réponse 200 :
ce n’est pas un succès juridique. CLI : code 0 pour un constat restitué, même
négatif/indéterminé ; code 2 pour un refus. La CLI n’est pas auditée comme HTTP.

## Interprétation des résultats

| `constat` | `fragment_present_litteralement` | Interprétation limitée |
|---|---|---|
| `correspondance_litterale_trouvee` | `true` | Ce fragment exact apparaît dans le texte natif de cette page. |
| `correspondance_litterale_non_trouvee` | `false` | Pas de correspondance exacte ; ce n’est pas une preuve d’erreur. |
| `texte_natif_absent` | `null` | Extraction effectuée mais texte vide/blanc ; aucun OCR. |
| `article_absent_du_lot` | `null` | ID inconnu du seul lot reçu. |
| `champ_absent` | `null` | Aucun repli sur une autre langue. |
| `fragment_vide` | `null` | Décalage hors fin ou champ vide ; pas de correspondance vide positive. |
| `fragment_sans_caractere_non_blanc` | `null` | Aucun rapprochement positif déduit d’un fragment blanc. |

Les quatre derniers cas ne déclenchent **aucune extraction** : l’existence de la
page demandée n’est alors pas vérifiée. `extraction_effectuee=false`, empreinte
PDF lue et nombre de pages restent `null`. La référence documentaire déclarée
peut être présente sans qu’un PDF ait été extrait.

`position_debut_pdf` et `position_fin_pdf_exclusive` encadrent la première occurrence
dans le texte extrait, pas une zone graphique du PDF. Les positions et décalages
sont en points de code Unicode Python, pas en octets/UTF-16/graphèmes.
`fragment_article`, provenance, empreinte du PDF effectivement lu et pagination
restent dans le rapport. `decalage_suivant` permet de demander un autre fragment
sur la même page ; cela ne localise pas automatiquement la suite dans le PDF.

## Interface et export

Dans la revue UniOCR, remplir le formulaire de lecture d’article, puis choisir la
page dans « Rapprochement littéral article / PDF » et lancer le rapprochement.
Le champ ID du lecteur PDF indépendant ne modifie jamais la source imposée.
Les boutons permettent de rapprocher le fragment suivant sur cette même page et,
après extraction, de lire la page PDF rapprochée au premier emplacement trouvé
(ou au début en l’absence de correspondance). Les anciennes actions deviennent
inertes après remplacement/changement de lot ou de compte. Tarif désactivé.

Export JSON partiel existant : relecture autorisée/auditée, route admise dans la
whitelist et le schéma d’enveloppe version 1. Contrôle hors ligne uniquement
structurel/déclaratif, pas preuve d’authenticité. Anciens contrôleurs stricts
susceptibles de refuser cette nouvelle route. Textes affichés sans HTML exécuté.

## Extraction et limites

L’extraction commune au lecteur PDF est réutilisée : un seul rejeu du lot pour ce
rapprochement, puis recontrôle SHA des octets réellement remis au worker. Limites
inchangées : PDF 64 Mio, 10 000 pages, 200 000 caractères/page, processus 15 s ;
gardes Unix mémoire/CPU best-effort. Ni antivirus, sandbox OS/réseau, quota global
de concurrence ou mémoire constante. Aucun PDF distant téléchargé ou brut exporté.

Présence ne prouve ni fidélité du reste de l’article, unicité, bonne localisation
juridique ou authenticité de la source. L’ordre natif, les glyphes et les retours
peuvent différer du document visible. Même après correspondance, les marqueurs
restent `transcription_verification=non_verifiee`, `validation_juridique=non_validee`,
`publication_active=false`. Aucune attestation humaine ou donnée applicable à un
calcul douanier réel n’est créée ; aucun lot ou registre n’est modifié.
