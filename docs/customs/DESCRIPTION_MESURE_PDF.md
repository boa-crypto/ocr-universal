# Présence littérale d'un fragment de description dans sa page PDF — lot 44

Une description transcrite, un fragment et une page **choisie explicitement** de
sa source PDF déclarée. Aucun OCR, normalisation, traduction ou localisation
automatique à partir de la référence libre. Réutilise le constat littéral du Code
et la chaîne de contrôle PDF des mesures 43, sans moteur fiscal supplémentaire.

```sh
unocr customs-measure-pdf-match LOT --measure ID_LOCAL --page 1 --limit 4000 --offset 0
```

API : `GET /api/v1/customs-review/lots/ID/measure-pdf-match?mesure_id=M&page=1&limit=4000&offset=0`.
Opération `rapprochement_mesure_pdf`, archives `mesures` de source PDF uniquement.
Types Code/tarif refusés 422, archive non PDF ou page illisible/absente 409 ; règles
d'autorisation, épingle de provenance, audit obligatoire et no-store conservées.
ID non blanc sans contrôles/surrogates, maximum 256 caractères ; page 1–10 000,
limite 1–16 000, offset 0–67 108 864, entiers stricts dans le service local.
Paramètres vérifiés avant lecture du magasin.

Interface : fieldset distinct, ID local de mesure, page physique, taille et offset
du fragment ; bouton de présence et suite de description gardant la même page.
Pas de page calculée depuis « article… » ou « page… » du localisateur. Le fragment
est affiché comme texte, pas HTML ; changements de lot et erreurs d'audit effacent
l'ancien constat. Export JSON partiel à provenance simple admis par le contrôleur
hors ligne et son schéma. Cache v65-measure-pdf-match.

Le rapport `rapprochement_litteral_description_mesure_pdf` distingue :

- mesure absente, fragment vide ou blanc : pas d'extraction, correspondance null ;
- page sans texte natif : constat indéterminé, correspondance null ;
- fragment présent/non présent : recherche exacte avec `find`, première occurrence
  seulement et offsets Unicode Python, aucun dénombrement ou preuve d'unicité.

La description seule est comparée. Les métadonnées de mesure restituées incluent
ID, code, type et référence déclarés, **pas de taux restitué comme preuve**.
`taux_et_periodes_verifies`, `rattachement_juridique_etabli` et
`utilisable_pour_calcul_douanier` restent false ; transcription non vérifiée.
Présence du texte ne valide ni code, taux, unité, période, contexte ou portée
juridique. Absence ne prouve pas erreur : glyphes, ordre et espaces peuvent différer
du rendu. Le reste de la description et les autres pages ne sont pas attestés.

Archive PDF/sidecar/transcription rejouée, relecture SHA avant worker, mêmes bornes
et limites que [lecture PDF 43](LECTURE_PDF_MESURES.md). Pas publication, décision
humaine, calcul, antivirus, mémoire constante ou transaction filesystem ajoutés.
Tests exclusivement sur fixtures NON OFFICIELLES ; aucun original fiscal qualifié.
