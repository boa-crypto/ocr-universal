# Mesures autonomes XLSX — contrat technique du lot 40

Extension des préparations [JSON](MESURES_AUTONOMES.md) et
[CSV](MESURES_AUTONOMES_CSV.md), sans rattachement fiscal ou activation.

## Entrées explicites, cellules textuelles

```sh
unocr customs-fiscal-prepare MESURES.xlsx --metadata METADATA.json
unocr customs-fiscal-prepare MESURES.xlsx --metadata METADATA.json --out DOSSIER_NEUF --write
unocr customs-fiscal-check DOSSIER_NEUF
```

Sidecar `ConfigurationMesuresAutonomes` : source et SHA256 exact du fichier reçu,
`source.format: "xlsx"`, mapping `colonnes` identique au CSV, `feuille` explicite
et non blanche, `ligne_entete` entière entre 1 et 50 (défaut 1). `delimiteur`
interdit même explicitement égal au défaut. Options de feuille refusées sur JSON
et CSV ; options CSV toujours interdites sur JSON. Fragment non officiel :

```json
{
  "feuille": "Mesures déclarées",
  "ligne_entete": 2,
  "colonnes": {
    "id": "ID",
    "code_tarifaire_10": "Code",
    "type_mesure": "Type",
    "description": "Libellé",
    "taux": "Taux",
    "unite_taux": "Unité",
    "date_entree_vigueur": "Début",
    "date_fin_validite": "Fin"
  }
}
```

Il faut compléter par les véritables métadonnées et l'empreinte de sa propre
source. Les quatre premiers mappings sont requis, les autres facultatifs ; aucun
champ inconnu, partage de colonne ou mapping `reference`. Les en-têtes doivent
être textuels, non blancs, uniques et contenir tous les noms mappés exacts.

Chaque cellule mappée non vide doit déjà être **textuelle** : aucun nombre,
booléen ou objet date Excel converti. Un code numérique avec format d'affichage
`0000000000` reste refusé, comme un taux numérique, même zéro. Pas de lecture de
valeur de formule en cache ou d'évaluation ; pas de `str`, float, zfill, conversion
d'unité, arrondi, normalisation de description ou interprétation de style.

Valeurs absentes ou chaînes vides → null uniquement pour taux, unité et dates ;
les champs obligatoires restent obligatoires. Taux, code10, type, unité et dates
respectent ensuite le modèle `Mesure` existant (dont zéro ≠ null, code10 ASCII
exact, période cohérente). Référence générée : source du sidecar et
`XLSX, feuille NOM, ligne N`, ligne réelle du classeur, pas page ou article légal.

## Périmètre de lecture et bornes

Réutilisation du lecteur `tabular.lire_xlsx`, sans deuxième moteur XLSX :

- Une feuille visible explicitement choisie, autres noms listés dans
  `feuilles_non_importees` ; pas d'import automatique de toutes les feuilles.
- Enregistrements après l'en-tête ; lignes entièrement vides ignorées et comptées.
  Ligne d'en-tête seule admise, zéro mesure reçue n'établit aucune exonération.
  Préambule avant l'en-tête non importé ; pas de validation de sa signification.
- Cellules au-delà des en-têtes refusées ; dimensions déclarées réinitialisées
  pour ne pas perdre silencieusement des données hors rectangle annoncé.
- Formules refusées dans la feuille sélectionnée **à partir de l'en-tête**, y
  compris dans les colonnes non importées. Les autres feuilles et le préambule
  ne sont pas parcourus comme données métier ; leur absence de formule n'est
  pas attestée. Aucune formule n'est exécutée nulle part par cet import.
- Colonnes non mappées signalées et non importées. Leurs valeurs numériques
  ordinaires peuvent exister sans être converties en données fiscales.
- Garde ZIP/XML existante : 4 096 membres maximum, 128 Mio décompressés déclarés,
  ratio 200, chemins dangereux/membres dupliqués/chiffrement refusés, garde
  DTD/ENTITY, macros/liens de classeur externes/objets actifs identifiés refusés.
- Bornes lecteur : 200 000 lignes physiques, 256 colonnes, 2 000 000 cellules ;
  borne autonome supplémentaire : 100 000 mesures. 64 Mio par fichier reçu ou
  artefact archivé. Lecture et normalisation en mémoire, pas streaming ni quota
  global/processus, antivirus ou garantie d'innocuité universelle du classeur.

## Archive, rejeu et revue

Cinq fichiers : source `source_mesures_recue.xlsx`, sidecar original exact,
`lot_mesures.json`, `rapport.json`, `manifest.json`. Une seule source JSON/CSV/XLSX
cohérente avec son format ; octets source/sidecar préservés, SHA et rejeu complets.
Mapping et options restent dans le sidecar, pas dans le lot normalisé. Même
quarantaine, dossier neuf, aucune publication ou réécriture d'anciens lots.

Sorties JSON historiques et CSV 39 conservées ; tests à empreintes figées du code
antérieur sur fixtures NON OFFICIELLES. Les messages de périmètre historiques de
leurs rapports sont également conservés, sans déclarer que ce lecteur XLSX a été
appliqué à ces anciennes sources. Type/version de manifeste inchangés.

Inscription explicite au registre comme `mesures` avec empreinte du manifeste,
recherche FR/AR, sources, couverture et consultation séparée avec un tarif
réutilisées. Sauvegarde avec quarantaine/reprise dans un magasin neuf et rejeu
vérifiés. Aucun upload administratif, calcul ou publication ajouté.

## Limites juridiques et qualification

Tests exclusivement NON OFFICIELS, pas d'original fiscal national acquis ou
qualifié. Ni style Excel, date reçue, SHA ou égalité de code ne prouvent
rattachement, authenticité, exhaustivité ou applicabilité. Pas de choix de taux,
consolidation à date, validation humaine, extraction fiscale PDF automatique,
WORM ou transaction multi-dossiers. La recette technique ne remplace pas la
qualification de fichiers fiscaux officiels et la recette nationale.

Lot 41 : [XLS OLE/BIFF8 autonome restreint](MESURES_AUTONOMES_XLS.md) également
disponible. Ce n’est pas un lecteur XLS universel ; les contraintes diffèrent de XLSX.

Lot 42 : [PDF opaque et transcription JSON déclarée](MESURES_AUTONOMES_PDF.md)
archivables séparément, sans extraction ou fidélité au document vérifiée.
