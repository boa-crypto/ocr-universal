# CSV groupé indépendant du fichier horodaté — lot 93

Route : `GET /api/batches/export/csv?ids=...`.

## Contrat

La branche CSV prépare désormais son texte avec `StringIO(newline="")`, le
writer CSV existant, puis les octets UTF-8 BOM en mémoire. Réponse créée avant
l'audit, sans création/lecture/réouverture du répertoire ou du fichier groupé.
Les sorties préexistantes sont laissées intactes.

Changements HTTP explicites : **`text/csv; charset=utf-8`**, nom fixe **`lot.csv`**,
`Cache-Control: no-store`, sans ETag/Last-Modified de fichier ; ancien octet-stream
et nom horodaté remplacés. BOM, séparateur/quoting/newlines CSV, huit colonnes92,
priorité humaine non None et neutraliseur existant conservés. JSON groupé reste
sur sa réponse mémoire91 ; TXT/XLSX/archives restent fichiers partagés.

Ordre/doublons, limite200, contrôle par job et erreurs de liste inchangés.
Séquence de lectures par document, **pas snapshot atomique du lot**. Réponse liée
à ces lectures, pas dernier état garanti en fin transfert. Audit `batch_exported`
CSV et nombre de documents conservé après préparation, pas preuve de livraison
ou attribution nouvelle de personne.

## Recette

18 nouveaux cas : contrat HTTP/BOM/colonnes, chemin piégé, anciens fichiers
intacts, ordre/doublons, Unicode/virgules/guillemets/multiligne, trois refus,
job absent, résultat absent, deux listes invalides/trop longues, contrôles
JSON/TXT, deux changements humains HTTP, limite200 et course HTTP.
Les 41 cas92 restent inclus pour valeurs retenues/neutraliseur.

Course : nom horodaté fixé pour reproduire la même seconde ; premier CSV arrêté
à l'audit après préparation, PATCH de confirmation, second téléchargement fini,
puis premier libéré. Comparaison des CSV relus **avant en-têtes** : ancien handler
livre au premier la valeur AFTER93 du second ; nouveau code conserve deux clichés.
Véritables TestClient/stores/jobs/audits temporaires et barrières maîtrisées,
pas navigateur, tableur réel, fournisseur OCR ou qualification de charge.

Contre-épreuve : seul ancien export_batch réinjecté en mémoire, autres handlers/
fixtures conservés, checkout/aperçu non remplacés. Échec de contenu concurrent
vérifié dans JUnit, pas simplement changement de média/nom/no-store.
[Rapport](RAPPORT_LOT93.md), [recette](RECETTE_LOT93.json).

## Limites

CSV groupé HTTP seulement. TXT/XLSX/archives groupés, formats unitaires ou
sélectionnés non JSON restent hors périmètre et peuvent garder des chemins
partagés/obsolètes. Aucun ancien fichier réparé ou purgé. no-store ne purge pas
les caches clients/proxies/offline déjà présents.

Tableau/texte/octet-réponse matérialisés en mémoire ; limite200 pas borne
d'octets/CPU/mémoire, pas streaming ou test de charge. Pas validation universelle
structurelle/numérique/qualité, ni redaction des données. Limites92 du neutraliseur
et de l'origine déclarée conservées, pas qualification Excel/LibreOffice.
Audit best-effort après préparation, pas transaction ou livraison attestée.
Droits, révision processus/ABA et autres écrivains inchangés.

Aperçu backend76 maintenu : code77–93 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements. RBAC non activé
implicitement ; mission réglementaire toujours partielle.
