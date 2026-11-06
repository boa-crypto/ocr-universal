# Texte natif d’une page PDF reçue — lot 21

2026-11-06. **Lecture documentaire non validée, pas import de tarif PDF.**

## Service, CLI et API

```sh
PYTHONPATH=src python -m unocr.cli customs-code-pdf-read /chemin/lot-code --document ID_EXACT --page 1 --limit 4000 --offset 0
```

API administrative existante :
`GET /api/v1/customs-review/lots/{lot_id}/pdf?document_id=ID_EXACT&page=1&limit=4000&offset=0`.
Lot Code uniquement, mêmes habilitations nominatives, registre, manifeste épinglé,
`no-store` et audit obligatoire avant restitution du succès (`lecture_pdf`).
Aucun chemin local, URL distante, mot de passe ou PDF brut n’est accepté par HTTP.
Le document est choisi par son ID exact dans le lot contrôlé, jamais par son nom
reçu. Aucune URL source ou lien du PDF n’est suivi par le service.

Le chargeur central contrôle/rejoue d’abord le lot ; les octets sélectionnés sont
relus et leur SHA256 comparé au document et au rapport avant remise à l’extracteur.
Aucune modification du lot, du texte transcrit ou de son statut de vérification.
La CLI retourne 0 pour une lecture techniquement réussie, 2 pour refus. L’API
retourne 422 pour paramètres/types de lot incompatibles, 409 pour PDF non lisible,
page/document absent ou limites atteintes, 503 si audit indisponible. Authentification
et incohérence du lot conservent leurs refus habituels.

## Résultat et sens des pages

Rapport `lecture_page_pdf_recu` : document déclaré, manifeste du lot, SHA256 des
octets PDF lus, page physique/total/suivante, fragment, longueur et décalage suivant.
Pages physiques à partir de **1**, sans déduction du numéro imprimé du JO. Fragment
par points de code Unicode Python, sans traduction, correction ou choix d’article.

Extraction `texte_natif_pdfium_sans_ocr` : une page blanche ou scannée peut produire
un fragment vide, avec `texte_natif_non_vide=false`. Cela ne prouve pas qu’elle ne
contient rien ni qu’aucun droit n’existe. Aucun OCR, rendu graphique, découpage en
articles ou rapprochement automatique avec une transcription n’est effectué.
Ordre des caractères/colonnes/retours à la ligne et glyphes extraits peuvent différer
de la lecture visuelle ; une vérification humaine du document est nécessaire.

Toujours `validation_juridique=non_validee`, `transcription_verification=non_verifiee`
et authenticité/complétude non établies. Une lecture réussie ne certifie ni le PDF,
son éditeur, les dates ou statuts déclarés, ni le droit applicable.

## Processus et limites

L’extraction utilise `pypdfium2`, déjà dépendance, dans un **processus jetable** :
pas de nouveau partage concurrent de PDFium avec les threads OCR du serveur.
Octets par entrée standard, réponse JSON, diagnostics internes jamais retournés.
Le chemin du worker provient du paquet installé, pas du document, du cwd ou d’un
paramètre client. Aucun fichier de résultat n’est créé par le worker.

- PDF reçu ≤64 Mio (contrôle existant), 10 000 pages maximum.
- 200 000 caractères internes PDFium/page et caractères Unicode extraits maximum.
- Fragment 1–16 000, offset 0–67 108 864 ; extraction de la page avant découpage.
- Délai parent 15 secondes ; protections Unix supplémentaires tentées : espace
  d’adressage 512 Mio et temps CPU 10 secondes, selon disponibilité de `resource`.

Pas de garantie globale de mémoire/temps côté serveur, de limite au nombre de
requêtes concurrentes, d’antivirus ou de bac à sable OS/réseau complet. Les autres
parties du serveur et son chargeur de lots ont leurs limites propres. Le processus
séparé réduit le partage d’état ; il n’établit pas l’innocuité du parseur C.
Un PDF chiffré nécessitant un mot de passe est refusé, sans tentative de déchiffrement.

**Pas de nouveau bouton PDF, lecteur visuel ou export PDF dans l’interface à ce lot.**
L’export JSON UI/contrôle hors ligne existant conserve son périmètre antérieur ;
ne pas présenter cet ajout API comme un parcours graphique déjà livré.

[Rapport et qualification](RAPPORT_LOT21.md).
