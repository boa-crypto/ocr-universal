# Inventaire documentaire des sources déclarées — lot 34

Inventaire local des sources d'un seul lot contrôlé en quarantaine : aucun accès
réseau, acquisition, fusion, dédoublonnage automatique ou validation juridique.

```text
customs-sources DOSSIER_LOT --type code [--query TEXTE] [--source ID] [--nature code_original] [--limit 20] [--offset 0]
GET /api/v1/customs-review/lots/{lot_id}/sources?q=TEXTE&source_id=ID&nature_document=code_original&limit=20&offset=0
```

CLI : type explicite `code` ou `tarif`. API : type du registre autorisé, pas choisi
par le client. Requête vide admise : inventaire de toutes les sources du lot.
Recherche FR/AR normalisée existante dans **titre, organisme et version_source**
seulement, tous termes en sous-chaînes, éventuellement répartis entre ces champs.
Pas de recherche dans URL, SHA, IDs, articles ou localisateurs. Pas de traduction,
synonymes, IA ou score. La requête n'est pas un filtre d'ID exact.

Filtres cumulatifs : `source_id` exact non blanc, maximum 256 points de code,
sans contrôle ni substitut Unicode isolé ; `nature_document` réservé au Code,
parmi `code_original`, `acte_modificatif`, `compilation`. Un filtre nature reçu
sur tarif est refusé, jamais ignoré par le service/API. Requête maximum 256
points de code et 16 termes ; limite entière 1–100, offset 0–1000000, booléens
refusés par le service. Paramètres du service vérifiés avant chargement du lot.

## Rapport

`type_recherche=sources_documentaires`, provenance simple `archive`, `type_lot`,
`total_sources_lot`, filtres, compteurs paginés et `resultats` triés par ID source
Unicode croissant, sans classement chronologique ou juridique. Chaque résultat :

- `source_declaree` complète : URL, organisme, titre, version, format, empreinte,
  date de publication reçue, vérification non vérifiée ; nature reçue sur Code
  seulement, aucune nature de document Code inventée sur tarif ;
- `champs_correspondants` : termes normalisés → métadonnées correspondantes ;
- `compteurs_lot` : sur Code, nombre d'articles en référence principale, nombre
  d'articles citant la source dans leur historique (une fois par article même
  si répétée), nombre de relations dont elle est la référence de preuve ; sur
  tarif, effectifs des sections/chapitres/positions/SH6/subdivisions/lignes/mesures ;
- `autres_sources_meme_sha256_dans_lot` : autres IDs déclarant le même SHA dans
  ce lot, même hors page/filtres, sans inclure la source elle-même.

Un zéro ne prouve ni document vide ni absence de modification. Une égalité de
SHA décrit les octets reçus, pas l'identité juridique de documents ou langues,
leur rôle, leur authenticité ou leur applicabilité. Aucun dénominateur national.
L'inventaire ne complète pas les sources manquantes.

## Interface, API et export

Formulaire intégré aux outils existants de revue, pagination indépendante.
Sur Code, ouverture de la hiérarchie de la source exacte avec chemin `[]` ;
lecture du PDF reçu à la page physique 1, sans suivre l'URL déclarée ni prétendre
avoir localisé une disposition. Pas d'action PDF sur tarif. Nature désactivée
sur tarif et non envoyée par l'interface ; les autres filtres restent utilisables.
Gardes de sélection/compte/réponse et refus de métadonnées d'action incohérentes.

Mêmes autorisations administrateur nominatif + allowlist de réviseurs, registre
et manifeste épinglés, rejeu central, empreinte de résultat contrôlée. Audit de
succès obligatoire `inventaire_sources`, `no-store` ; panne audit 503 sans résultat.
Paramètres invalides 422, lot inconnu 404, intégrité refusée 409.

Export partiel relu/audité ; enveloppe 1 et whitelist/schéma mis à jour pour
`sources`. Les anciens vérificateurs à whitelist stricte peuvent refuser cette
nouvelle route. Validation hors ligne structurelle uniquement, pas authenticité.

Le lot entier est chargé/rejoué avant pagination et comptage ; aucune garantie
mémoire constante ou performance nationale. Tests sur fixtures NON OFFICIELLES,
JSDOM et API réelle isolée, pas recette visuelle/accessibilité Chrome/Firefox.

Lot 35 : [téléchargement contrôlé du PDF archivé](COPIE_PDF_SOURCE.md) via `GET /lots/{lot_id}/pdf-source?document_id=…`, audit obligatoire et SHA navigateur, pièce jointe non validée (pas antivirus).

Lot 37 : [revue intégrée des mesures autonomes](REVUE_MESURES_AUTONOMES.md), type de registre `mesures`. Contrôle/recherche de mesures/sources/couverture et exports existants, autres opérations explicitement refusées ; aucun rapprochement fiscal.
