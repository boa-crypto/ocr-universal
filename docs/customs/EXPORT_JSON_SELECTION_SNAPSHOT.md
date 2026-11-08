# JSON sélectionné indépendant du fichier partagé — lot 90

Route : `GET /api/jobs/{job_id}/export/json/selected?fields=...`.

## Changement ciblé

Le JSON sélectionné était régénéré, mais un chemin partagé
`exports/selected/selection_<champs>.json` était écrit puis rouvert par
`FileResponse`. Deux requêtes pouvaient donc se remplacer leur contenu avant
livraison, y compris après une correction du résultat entre les deux.

La route prépare désormais le modèle filtré et sa **réponse JSON en mémoire**
avant l'audit et la livraison. Pas création/lecture/écriture de chemin d'export
pour JSON. Fichiers préexistants laissés inchangés. Les noms de champs ne servent
plus de nom de chemin ou de pièce jointe pour cette branche.

Contrat HTTP JSON : `application/json`, **nom fixe `selection.json`** (changement
explicite par rapport à `selection_<champs>.json`), `Cache-Control: no-store`,
sans ETag/Last-Modified issus d'un fichier. Indentation compacte, contenu
sémantique modèle conservé. Le type retour Python devient `Response`, base des
réponses JSON et fichier ; pas nouveau modèle de réponse API.

Politique de sélection conservée : espaces retirés dans les tokens, doublons
sans effet, champs inconnus ignorés si au moins un champ existe, sélection
sans champ reconnu400, paramètre vide422. Filtrage uniquement de `fields` :
**autres sections (classification, pages/texte, tableaux, etc.) conservées**.
Ce n'est pas un export de confidentialité ni une suppression des autres données.
Audit `export_selected`, job/fmt/liste triée, conservé après construction de la
réponse ; pas preuve de livraison ou nouvel acteur attribué.

## Recette

26 nouveaux cas : trois sélections valides/doublons/espaces, quatre refus de
sélection, une conservation des autres sections, quatre noms particuliers dont
FR/AR/slash/ponctuation, un fichier existant intact, une primitive de chemin
piégée, quatre changements entre exports, trois refus d'accès, un job absent,
un résultat absent, un format interdit, un TXT fichier conservé,
un **entrelacement HTTP de deux exports et d'un PATCH**.

Entrelacement : premier export suspendu au point d'audit après préparation,
PATCH de confirmation, second export terminé, puis premier libéré. Chaque
réponse doit conserver son cliché. Avec l'ancien handler, le premier reçoit la
valeur du second ; assertion des corps avant vérification des en-têtes.
Stores/jobs/audits temporaires réels, ThreadPool/Event et véritable TestClient ;
pas navigateur, fournisseur OCR ou qualification de charge.

Contre-épreuve : seul ancien `export_selected` réinjecté en mémoire, autres
handlers/fixtures conservés, checkout/aperçu non remplacés. Le JUnit témoin
atteste l'échec de contenu du premier export concurrent, pas seulement le
nouveau nom ou no-store. [Rapport](RAPPORT_LOT90.md), [recette](RECETTE_LOT90.json).

## Limites

JSON sélectionné seulement. CSV/TXT/XML/XLSX/PDF sélectionnés conservent les
chemins partagés, avec risques de collision/concurrence non corrigés ici.
Autres formats complets, batch/archives et helpers disque inchangés ; JSON
complet relève du lot89. Aucun ancien fichier supprimé ou réparé.

Snapshot lu, pas état dernier garanti à fin transfert. Modèle et réponse
matérialisés en mémoire, pas nouvelles bornes de taille/mémoire/CPU/débit,
streaming ou test de charge. no-store ne purge pas les caches déjà présents
côté client/proxy/offline. Pas redaction des sections conservées, détails des
erreurs ou audit. Validation modèle existante, pas validation universelle qualité.
Erreurs de génération/dossier prises dans le bloc existant ; validation modèle
reste avant ce bloc. Audit best-effort, pas transaction ou garantie de livraison.

Droits, identité, révision processus/ABA et autres écrivains inchangés.
Aperçu backend76 maintenu : code77–90 poussé/testé mais non chargé avant
redémarrage maîtrisé pour préserver les traitements. RBAC non activé
implicitement ; mission réglementaire toujours partielle.
