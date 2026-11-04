# Mission référentiels douaniers — lot 1 : audit, sûreté et préparation

**État : socle technique, pas source de vérité réglementaire en production.**
Lire [l'audit](AUDIT_INITIAL.md), [l'avancement et les résultats](RAPPORT_AVANCEMENT.md)
et [le registre documentaire](SOURCES_RECHERCHE.json).

## Livré

- Blocage des anciens taux hypothétiques : fonctions Python refusées explicitement,
  routes `/api/reglementation/droits/calculer` et `/droits/complets` → 503 avec
  `reference_douaniere_non_verifiee` pour une requête précédemment calculable.
  Aucun remplacement par un taux supposé, même nul.
- Contrats Pydantic stricts et [JSON Schema](schemas/) : lot tarifaire, version
  individuelle d'article et mesure sourcée. Zéros initiaux conservés ; codes
  numériques, zfill et pseudo-clé de contrôle exclus du nouveau domaine.
- Hiérarchie déclarée indépendamment : sections, chapitres, positions et SH6
  doivent exister et être cohérents avant admission d'une ligne nationale.
- Mesures distinctes de la nomenclature ; champs inconnus = null, pas zéro ni
  absence certaine de restriction. Références/localisateurs requis, mais leur
  existence syntaxique ne prouve pas leur authenticité réglementaire.
- Préparation locale CSV UTF-8/JSON, plan sans écriture par défaut ; archive des
  octets **reçus**, du sidecar, du lot normalisé et de leurs empreintes dans un
  répertoire neuf. Ce n'est pas encore l'archivage certifié d'un fichier éditeur.
- Aucune activation, migration, taux applicable ou décision juridique automatique.

## Commandes

```sh
# Vérifier la structure, la provenance déclarée et les liens, sans écrire :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.csv --metadata /chemin/metadata.json

# Préparer explicitement un lot en quarantaine, dans un répertoire neuf :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.csv --metadata /chemin/metadata.json --out /chemin/lot-neuf --write
```

La sortie est JSON ; codes 0 = préparation techniquement valide, 2 = refus.
**Code 0 ne signifie ni officiel, ni complet, ni juridiquement applicable.**
`--out` seul ne crée rien. `--write` exige `--out`. Le parent de sortie doit
exister ; aucun répertoire existant n'est remplacé. Pas de nettoyage automatique
en cas d'interruption : un dossier partiel sans manifest final doit être examiné,
jamais activé. Pas de garantie de coupure électrique ou de protection WORM.

### Contrat du sidecar

Objet JSON avec :

- `lot` : structure `TariffBatch.schema.json` **sans** `lignes` ; source déclarée,
  sections, chapitres, positions, sous_positions et éventuelles mesures issues
  de la même source. Une autre source fiscale nécessite un lot/document distinct,
  pas une fusion implicite de dates ou de références.
- `colonnes` : pour CSV, dictionnaire explicite `champ_canonique -> en-tête_source`.
  Les champs sont ceux de `LigneTarifaire` dans le schéma. Pas de partage de colonne.
  Le lecteur produit `reference` avec le numéro de ligne physique et, si absent,
  un identifiant technique `source_id:code10`. Il n'invente pas de code ou libellé.
- `delimiteur` : CSV seulement, un caractère, `;` par défaut.

La source CSV doit fournir les codes 10/6/4/2, le lien de section, la désignation
FR et/ou AR (sans traduction automatique). Les cellules code doivent déjà être
exactes ; pas de nettoyage silencieux d'espaces ou ponctuations. Les colonnes non
mappées sont signalées dans le rapport, pas interprétées fiscalement.

Pour JSON : tableau de lignes conforme au schéma ; aucune ligne dans le sidecar.
La source déclare son format, sa version et son SHA256 exact. Taille de chaque
fichier ≤64 Mio. Les URL HTTPS sont limitées aux domaines documentaires prévus,
**mais ce contrôle ne certifie pas l'origine des octets remis**.

Fichiers de sortie : `source_recue.csv` ou `.json`, `metadata_original.json`,
`lot.json`, `rapport.json`, puis `manifest.json` en dernier, avec date d'import UTC
et empreintes de chaque fichier. Les sources d'origine de l'éditeur qui auraient
servi à une conversion externe doivent aussi être acquises et liées avant toute
validation : le fichier converti ne peut pas se substituer à cet original.

### Correspondance des champs réglementaires

La provenance est centralisée : `ligne.reference.source_id -> lot.source` donne
URL, organisme et version_source ; date_importation vient du manifest. Les taux
et restrictions inline restent null ; les données déclarées sourcées vont dans
`mesures`, non validées. L'unité fiscale actuellement modélisée est le pourcentage
ad valorem : pas d'inférence de taxes spécifiques, bases composites ou formules.
La date de validation reste null. Les dates d'effet inconnues restent null.

Pour les articles, `nature_version` distingue original, disposition modificative
et consolidation provisoire. `validation_juridique=non_validee` est obligatoire,
même si `statut_juridique_declare` contient « applicable ». Ce dernier est une
assertion à contrôler, pas une autorisation d'usage. Les notes non officielles
sont stockées séparément du texte. **Aucun consolidateur ni sélecteur à date
juridiquement validé n'est encore livré.**

## Intégration future, sans double source de vérité

Le module `customs_reference` ne consomme pas CODES_SH_ALGERIE et ne publie pas ses
lots via le CRUD générique des grilles de frais. Publication future conditionnée à
l'archivage des originaux, aux rapprochements de versions et à une validation
humaine habilitée et tracée. Les modules marchandise/transit devront référencer
une version publiée ; l'IA ne pourra proposer que des candidats sourcés et devra
s'abstenir lorsqu'aucune version validée n'est disponible.

Les API v1, l'import administrateur sécurisé, la recherche multilingue, la
classification tarifaire et l'extension du DS seront développés sur ce domaine,
pas sur les exemples legacy. Aucun endpoint de validation ne doit être ouvert
simplement parce que le RBAC historique est désactivé.
