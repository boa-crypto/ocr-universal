# Lecture native d'une page PDF fiscal reçu — lot 43

Lecture seule d'une archive [PDF + transcription 42](MESURES_AUTONOMES_PDF.md)
contrôlée. Réutilise le worker PDFium du Code, sans OCR, rendu, URL distante,
extraction de taux ou vérification de fidélité des mesures transcrites.

## CLI, API et interface

```sh
unocr customs-fiscal-pdf-read LOT --document SOURCE_ID --page 1 --limit 4000 --offset 0
```

API autorisée :
`GET /api/v1/customs-review/lots/ID/fiscal-pdf?document_id=SOURCE_ID&page=1&limit=4000&offset=0`.
Opération d'audit `lecture_pdf_mesures`, type de lot `mesures` uniquement ; source
exacte de format PDF requise. Code/tarif refusés 422 ; lot de mesures sans PDF,
source absente, page absente, PDF illisible/chiffré ou worker indisponible : refus
409. Paramètres HTTP invalides 422, autorisations et audit obligatoire inchangés.
Les anciennes routes `/pdf` et `/pdf-source` restent réservées au Code et refusées
sur les mesures. Pas d'exception pour comparaison mixte ajoutée.

Interface : fieldset fiscal distinct du lecteur Code, activé seulement pour le
type `mesures`. Le registre ne décrit pas le format : une demande manuelle dans
un lot non PDF est donc possible mais refusée par le backend, jamais devinée.
Inventaire des sources : action dédiée sur la source PDF, aucune action d'article
Code ou téléchargement binaire proposée. Fragments et pages suivants indépendants ;
changement de lot invalide les anciens boutons. Texte en `textContent`, pas HTML.
Cache shell v64-fiscal-pdf.

## Chaîne de contrôle et résultat

Paramètres validés avant accès au magasin pour le service local : ID non blanc
sans contrôle de 256 caractères maximum, page entière 1–10 000, limite entière
1–16 000, offset entier 0–67 108 864. Rejeu intégral des six fichiers, source PDF
exacte, puis relecture des octets et SHA comparé à source et manifeste avant worker.
Épingle de manifeste vérifiée à l'entrée de la revue et dans la provenance retournée ;
audit obligatoire avant réponse. Pas de transaction/verrou global des fichiers ni
promesse d'absence de course après le contrôle. Corpus et rapport d'import inchangés.

Rapport `lecture_page_pdf_mesures_recu` : provenance du lot, source, SHA du PDF et
de la transcription archivée, page physique/nombre de pages, fragment de texte,
limite/offset et suites. Unité d'offset : points de code Unicode Python, pas octets
ou unités UTF-16. Limite au-delà du texte : fragment vide admis. Page physique à
partir de 1, pas page imprimée ou référence juridique automatiquement localisée.

`lecture_pdf_effectuee: true` décrit cette consultation ; le rapport d'import 42
reste `lecture_pdf_effectuee: false`, puisqu'il n'avait pas lu le document.
`mesures_transcrites_comparees: false`, `transcription_verification: non_verifiee`,
validation juridique non validée et calcul douanier false restent explicites.
Extraire une page ne valide pas la structure entière ou l'innocuité du PDF.

Export partiel JSON déjà audité côté lecture et contrôlable hors ligne : route
dédiée admise par la whitelist et le schéma `ExportRevue`. Provenance simple requise,
jamais double, aucune authenticité ou certification de l'heure client ajoutée.

## Worker et limites réutilisées

Processus jetable : délai parent 15 secondes, sortie 3 Mio maximum, 10 000 pages,
200 000 caractères par page, 64 Mio d'entrée. Gardes Unix mémoire 512 Mio et CPU
10 secondes au mieux selon environnement. Erreurs de parseur génériques sans
recopier contenu sensible. Lecture du texte natif seulement : PDF scanné sans texte
ou page blanche peut donner chaîne vide ; aucun OCR déclenché et aucune absence
de droit déduite. Ordre et caractères peuvent différer du rendu visuel.

Pas bac à sable OS/réseau, antivirus, quota global ou de concurrence, mémoire
constante, Range ou qualification de charge nationale. Lecture et rejeu complets
avant pagination ; le fragment ne rend pas le coût proportionnel à sa longueur.
Aucun original officiel acquis/qualifié, mesure rapprochée, fidélité attestée,
consolidation à date, décision humaine, publication ou taux applicable établi.

Lot 44 : [constat littéral de description](DESCRIPTION_MESURE_PDF.md) disponible
séparément ; aucune validation des taux, périodes ou rattachements déduite.
