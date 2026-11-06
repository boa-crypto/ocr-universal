# Mission référentiels douaniers — lots 1–17 : audit, préparation et comparaison

**État : socle technique, pas source de vérité réglementaire en production.**
Lire [l'audit](AUDIT_INITIAL.md), [l'avancement du lot 1](RAPPORT_AVANCEMENT.md),
[le lot 2](RAPPORT_LOT2.md), [le lot 3](RAPPORT_LOT3.md),
[le lot 4](RAPPORT_LOT4.md), [le lot 5](RAPPORT_LOT5.md),
[le lot 6](RAPPORT_LOT6.md), [le lot 7 du 6 novembre 2026](RAPPORT_LOT7.md) et [le registre documentaire](SOURCES_RECHERCHE.json).

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
- Préparation locale CSV UTF-8/JSON/XLSX, plan sans écriture par défaut ; archive des
  octets **reçus**, du sidecar, du lot normalisé et de leurs empreintes dans un
  répertoire neuf. Ce n'est pas encore l'archivage certifié d'un fichier éditeur.
- Comparaison de lots en quarantaine : empreintes, rejeu de la source et du mapping,
  écarts de nomenclature/hiérarchie/mesures, provenance séparée. Aucune différence
  n’est automatiquement interprétée comme un nouveau droit ou une abrogation.
- Aucune activation, migration, taux applicable ou décision juridique automatique.

## Commandes

```sh
# Vérifier la structure, la provenance déclarée et les liens, sans écrire :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.csv --metadata /chemin/metadata.json

# Préparer explicitement un lot en quarantaine, dans un répertoire neuf :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.csv --metadata /chemin/metadata.json --out /chemin/lot-neuf --write

# Comparer deux préparations archivées, sans modifier les lots ni les stores :
PYTHONPATH=src python -m unocr.cli customs-diff /chemin/lot-avant /chemin/lot-apres
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
- `colonnes` : pour CSV/XLSX, dictionnaire explicite `champ_canonique -> en-tête_source`.
  Les champs sont ceux de `LigneTarifaire` dans le schéma. Pas de partage de colonne.
  Le lecteur produit `reference` avec le numéro de ligne physique et, si absent,
  un identifiant technique `source_id:code10`. Il n'invente pas de code ou libellé.
- `delimiteur` : CSV seulement, un caractère, `;` par défaut.
- `feuille` : XLSX seulement, nom explicite d’une feuille visible.
- `ligne_entete` : XLSX seulement, entier de 1 à 50, 1 par défaut.
  Les options de feuille sont interdites pour CSV/JSON.

La source tabulaire doit fournir les codes 10/6/4/2, le lien de section, la désignation
FR et/ou AR (sans traduction automatique). Les cellules code doivent déjà être
exactes ; pas de nettoyage silencieux d'espaces ou ponctuations. Les colonnes non
mappées sont signalées dans le rapport, pas interprétées fiscalement.

Pour JSON : tableau de lignes conforme au schéma ; aucune ligne dans le sidecar.
La source déclare son format, sa version et son SHA256 exact. Taille de chaque
fichier ≤64 Mio. Les URL HTTPS sont limitées aux domaines documentaires prévus,
**mais ce contrôle ne certifie pas l'origine des octets remis**.

Fichiers de sortie : `source_recue.csv`, `.json` ou `.xlsx`, `metadata_original.json`,
`lot.json`, `rapport.json`, puis `manifest.json` en dernier, avec date d'import UTC
et empreintes de chaque fichier. Les sources d'origine de l'éditeur qui auraient
servi à une conversion externe doivent aussi être acquises et liées avant toute
validation : le fichier converti ne peut pas se substituer à cet original.

### XLSX : lecture littérale, périmètre explicite

Les codes doivent être des cellules **texte**. Un nombre Excel affiché avec le
format `0000000000` n’est pas converti en code ; aucune reconstitution des zéros.
Les en-têtes sont textuels, non vides et uniques. Les formules sont refusées à
partir de l’en-tête sur la feuille sélectionnée, sans utiliser leurs caches.
Les valeurs de date attendues dans les colonnes mappées doivent être des chaînes
ISO conformes au schéma ; aucune conversion automatique d’une date Excel.

Les lignes cachées sont lues ; les dimensions déclarées du classeur ne limitent
pas la lecture. Les lignes vides et les autres feuilles sont indiquées dans
`perimetre_lecture`. Les lignes avant l’en-tête sont hors du tableau sélectionné.
**Un compteur de feuille n’est pas un compteur national.** Les autres feuilles
ne sont ni importées ni qualifiées implicitement.

Bornes : source/sidecar 64 Mio chacun ; 4 096 membres ZIP, 128 Mio décompressés,
ratio par membre ≤200 ; 200 000 lignes parcourues (en-tête compris), 256 colonnes,
2 millions de cellules. Les chemins dangereux, liens symboliques ZIP, membres
dupliqués, chiffrement, parties VBA/macrosheets/dialogsheets/ActiveX/objets
embarqués et liens externes de classeur identifiés sont refusés. DTD/ENTITY
refusés avant analyse XML. Lecture en mémoire sans extraction ni exécution.
Ces contrôles ne constituent pas une certification antivirus.

### Comparaison : intégrité locale, pas authenticité

`customs-diff` accepte seulement les préparations en quarantaine. Il exige les
archives source/sidecar/lot/rapport et le manifeste final, sans fichier inattendu,
vérifie les SHA256, refuse les liens symboliques, rejoue l’analyse **des octets
vérifiés** et contrôle le rapport. Une altération du seul lot, même re-haché, est
refusée si le résultat ne se reproduit pas. Le rapport du lot 1 sans
`perimetre_lecture` reste accepté si les autres champs sont cohérents.

La sortie JSON présente `lignes`, `hierarchie`, `mesures_modifiees`,
`provenances_modifiees`, `sources`, `archives`, `perimetres` et `avertissements`.
Les taux sont comparés exactement, sans arrondi ; `19.0` et `19.00` sont
équivalents. Les mesures affichées gardent leurs identifiants et références.
Les déplacements de localisateur et changements d’identifiant technique sont
séparés des changements de contenu. Une même version déclarée avec des octets
différents et des périmètres de lecture différents déclenchent un avertissement.

Code 0 = comparaison techniquement effectuée ; code 2 = refus intégral, sans
résultat partiel présenté comme valide. Aucun lot ni store n’est modifié. Le
manifeste restitue un horodatage UTC **déclaré par la machine**, non un horodatage
certifié. Une personne pouvant réécrire toutes les sources et empreintes peut
constituer un nouveau lot cohérent : **pas d’authenticité prouvée ni de WORM**.
Ces écarts ne prouvent ni abrogation, ni date d’effet, ni validité juridique.

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

## Code des douanes : archivage documentaire en quarantaine (lot 3)

[Guide du format et des commandes](CODE_DOCUMENTAIRE.md), schémas
[CodeDocumentaireBatch](schemas/CodeDocumentaireBatch.schema.json) et
[MetadataCode](schemas/MetadataCode.schema.json).

`customs-code-prepare` archive des PDF reçus et une transcription JSON explicite,
avec versions originales, modificatives et compilations provisoires séparées.
Aucun OCR, téléchargement, consolidation ni rapprochement transcription/PDF
n’est effectué. Les relations doivent être justifiées et sourcées ; aucun lien
n’est inféré à partir d’une ressemblance ou d’un numéro d’article identique.
L’archivage seul, avec zéro article transcrit, est possible et signalé comme tel.
`customs-code-check` vérifie et rejoue un lot archivé ; `customs-code-diff`
compare ses articles, documents et relations avec un second lot vérifié, sans
modifier les archives. L’appariement est fondé sur les IDs déclarés, pas sur
les numéros ni une similarité de texte. Une absence ne signifie pas abrogation.
**Les octets reçus ne sont pas certifiés originaux de l’éditeur.** Le résultat
n’est pas une source de vérité applicable et n’est exposé par aucune API métier.

## Recherche locale FR/AR en quarantaine (lot 5)

[Guide de la recherche](RECHERCHE_LOCALE.md) et [résultats/limites](RAPPORT_LOT5.md).
`customs-tariff-search` retrouve des désignations déclarées ou préfixes ASCII ;
`customs-code-search` retrouve des textes et filtre des numéros/sources/natures
exacts, sans fusionner les versions. Contrôle complet du lot, pagination bornée,
références, champs correspondants et textes reçus conservés. Aucune IA, synonymie
inventée, interprétation juridique ou suggestion de classement officiel.

## API de revue administrative (lot 6)

[Contrat, habilitations et configuration](API_REVUE.md),
[rapport de qualification](RAPPORT_LOT6.md). GET sous `/api/v1/customs-review` :
liste des lots inscrits côté serveur, contrôle, recherche et diff. Administrateur
RBAC nominatif **et** habilitation explicite dans le registre local ; mode ouvert
et passe-partout d’environnement refusés. Aucun chemin choisi par HTTP ; manifeste
épinglé avant et après le traitement. Audit existant, pas de nouvel index métier.
**Aucune écriture, validation juridique ou publication.** Interface de lecture
ajoutée au lot 8, historique documentaire au lot 9.
Aucun compte ni registre n’est créé automatiquement sur le poste.

## Sauvegarde et reprise locale (lot 7)

[Guide](SAUVEGARDE_QUARANTAINE.md) et [qualification](RAPPORT_LOT7.md).
`backup` et `restore` couvrent le registre/les lots avec
`--include-customs-quarantine`, via le CLI seulement. Sans cette option, une
quarantaine présente n’est pas omise silencieusement : l’opération est refusée.
Destination de copies dédiée ; reprise sans quarantaine préexistante, même avec
`--force`. Les octets et épingles sont conservés, pas une validité réglementaire.

## Interface de revue (lot 8)

Dans Administration → Revue douanière · quarantaine : liste, contrôle, recherche
et comparaison via l’API stricte existante. Lecture seule ; aucune habilitation
accordée par le menu. [Guide](INTERFACE_REVUE.md), [rapport](RAPPORT_LOT8.md).
Rapports JSON sûrs, pas de corpus de démonstration ou d’édition réglementaire.

## Historique documentaire (lot 9)

[Guide](HISTORIQUE_DOCUMENTAIRE.md), [rapport](RAPPORT_LOT9.md).
`customs-code-history`, route de revue `/lots/{id}/history` et bouton intégré :
versions du numéro exact, sources/dates déclarées et relations justifiées à un
saut, paginées indépendamment. Pas de succession juridique ou droit à date inféré.

## Fiche tarifaire documentaire (lot 10)

[Guide](FICHE_TARIFAIRE.md), [rapport](RAPPORT_LOT10.md).
`customs-tariff-show`, route de revue `/lots/{id}/tariff/{code10}` et bouton
intégré : code exact dix chiffres ASCII, parents reçus, source et mesures
paginées. Taux inconnus conservés ; aucun taux applicable ou calcul inféré.

## Diagnostic de couverture documentaire (lot 11)

[Guide](COUVERTURE_DOCUMENTAIRE.md), [rapport](RAPPORT_LOT11.md).
`customs-coverage`, route de revue `/lots/{id}/coverage` et bouton intégré :
compteurs du lot, champs non renseignés et sources/limites explicites. Aucun
pourcentage de complétude réglementaire ou autorisation de publication/calcul.

## Navigation tarifaire documentaire (lot 12)

[Guide](NAVIGATION_TARIFAIRE.md), [rapport](RAPPORT_LOT12.md).
`customs-tariff-tree`, route de revue `/lots/{id}/tree` et contrôles intégrés :
sections → chapitres → positions → SH6 → codes10 reçus, parents exacts et
pagination. Parent absent et parent présent sans enfant distingués, sans
complétude nationale ou subdivision intermédiaire inventée.

## Lecture individuelle d’article (lot 13)

[Guide](LECTURE_ARTICLE.md), [rapport](RAPPORT_LOT13.md).
`customs-code-read`, route de revue `/lots/{id}/article` et groupe intégré :
version par ID exact, source/métadonnées et texte reçu par fragments. Champs
FR/AR absents conservés ; aucune traduction, consolidation ou applicabilité inférée.

## Navigation assistée des résultats (lot 14)

[Guide](NAVIGATION_ASSISTEE.md), [rapport](RAPPORT_LOT14.md).
Boutons de consultation depuis recherche/historique/arbre, descente par enfant
reçu, page suivante et fragment suivant. Même API de revue et droits, aucune
URL source suivie ou validation implicite. Pas de corpus de démonstration installé.

## Audit obligatoire des succès de revue (lot 15)

[Guide](AUDIT_REVUE.md), [rapport](RAPPORT_LOT15.md).
Un résultat HTTP réussi exige l’écriture/synchronisation locale de son événement
et de ses épingles ; sinon 503 sans contenu métier. Refus/middleware toujours
best-effort. Ni WORM, ni exactly-once ou validation juridique.

## Export de rapport non validé (lot 16)

[Guide](EXPORT_REVUE.md), [rapport](RAPPORT_LOT16.md).
Export JSON du rapport/page courant après relecture par l’API et audit obligatoire.
Aucun export complet du corpus, original PDF, validation ou publication implicite.

## Contrôle hors ligne des exports (lot 17)

[Guide CLI](CONTROLE_EXPORT_REVUE.md), [rapport](RAPPORT_LOT17.md),
[schéma d’enveloppe](schemas/ExportRevue.schema.json).
`customs-review-export-check FICHIER` : structure compatible ou refus, sans import,
authentification du document ou validation juridique.

## Intégration future, sans double source de vérité

Le module `customs_reference` ne consomme pas CODES_SH_ALGERIE et ne publie pas ses
lots via le CRUD générique des grilles de frais. Publication future conditionnée à
l'archivage des originaux, aux rapprochements de versions et à une validation
humaine habilitée et tracée. Les modules marchandise/transit devront référencer
une version publiée ; l'IA ne pourra proposer que des candidats sourcés et devra
s'abstenir lorsqu'aucune version validée n'est disponible.

Les API v1 de référentiels publiés, l'import administrateur sécurisé, la recherche
sur versions publiées, la
classification tarifaire et l'extension du DS seront développés sur ce domaine,
pas sur les exemples legacy. Aucun endpoint de validation ne doit être ouvert
simplement parce que le RBAC historique est désactivé.
