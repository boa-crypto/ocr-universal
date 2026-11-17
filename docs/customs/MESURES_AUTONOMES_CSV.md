# Mesures autonomes CSV — contrat technique du lot 39

Extension de la [préparation JSON](MESURES_AUTONOMES.md), sans nomenclature
inventée, fiscalité active ou qualification d'un original officiel.

## Entrée et mapping explicite

```sh
unocr customs-fiscal-prepare MESURES.csv --metadata METADATA.json
unocr customs-fiscal-prepare MESURES.csv --metadata METADATA.json --out DOSSIER_NEUF --write
unocr customs-fiscal-check DOSSIER_NEUF
```

Le sidecar JSON suit `schemas/ConfigurationMesuresAutonomes.schema.json` : mêmes
métadonnées de source et de quarantaine que JSON, `source.format` égal à `csv`,
SHA256 des **octets reçus**, plus `colonnes` et éventuellement `delimiteur` (`;`
par défaut). Fragment de configuration non officiel, à compléter par les vraies
métadonnées et l'empreinte de sa propre source :

```json
{
  "colonnes": {
    "id": "Identifiant",
    "code_tarifaire_10": "Code déclaré",
    "type_mesure": "Type déclaré",
    "description": "Description",
    "taux": "Taux",
    "unite_taux": "Unité",
    "date_entree_vigueur": "Début",
    "date_fin_validite": "Fin"
  },
  "delimiteur": ";"
}
```

- Quatre mappings requis : `id`, `code_tarifaire_10`, `type_mesure`, `description`.
  Les quatre autres ci-dessus sont facultatifs. Aucun autre champ, en particulier
  `reference`, n'est accepté. Chaque colonne mappée doit exister et ne peut servir
  à deux champs. Le schéma structurel ne remplace pas ces contrôles du lecteur.
- UTF-8 avec ou sans BOM initial ; aucune détection de dialecte/encodage. Un seul
  caractère délimiteur explicite ; guillemet, CR, LF, NUL et BOM interdits. Virgule,
  tabulation et barre verticale également testées. Guillemets CSV standards,
  délimiteurs dans cellules citées et cellules multilignes acceptés.
- En-têtes exacts, non blancs et uniques. Largeur de chaque enregistrement exacte ;
  syntaxe CSV malformée et encodage invalide refusés avant création du dossier.
  Le lecteur Python a aussi sa limite de taille de cellule (normalement 131 072
  caractères, configurable globalement par Python ; non relevée par cet import).
- Aucun `strip`, `zfill`, conversion float, notation scientifique de code ou
  correspondance devinée. Les codes sont exactement dix chiffres ASCII ; types
  et unités doivent déjà respecter le contrat `Mesure`, sans traduction de libellé.
  IDs locaux conservés et uniques ; descriptions FR/AR et texte exacts conservés.
- Cellules vides → null uniquement pour taux, unité et dates ; sinon aucune valeur
  obligatoire n'est fabriquée. Taux textuel décimal non négatif/fini ; zéro distinct
  de null ; unité `pourcent` requise avec taux. Pas de conversion de virgule
  décimale, formule, devise ou pourcentage. Aucune formule n'est exécutée.
- Référence générée : source du sidecar et `CSV, fin de ligne physique N`.
  C'est la **fin physique** de l'enregistrement, pas sa ligne de départ, ni un
  article, page ou fondement juridique. Les lignes entièrement vides ignorées par
  le lecteur ne créent pas de mesures et comptent dans le repérage physique.
- Colonnes non mappées : non importées, leurs noms signalés dans
  `perimetre_lecture.colonnes_non_importees`. Original conservé intégralement.
  Le rapport indique délimiteur et nombre de lignes physiques lues.
- CSV avec seulement en-têtes admis : zéro mesure reçue, jamais exonération.
  Fichier vide sans en-têtes refusé. Limites communes : 64 Mio par fichier et
  100 000 mesures ; mémoire complète, ni streaming ni qualification de charge.

## Archive et compatibilité

Cinq fichiers : `source_mesures_recue.csv`, `metadata_original.json`,
`lot_mesures.json`, `rapport.json`, `manifest.json`. Octets source/sidecar exacts,
empreintes, rejeu complet et comparaison du lot/rapport comme pour JSON. Extension
source et format déclaré doivent correspondre ; deux sources ou fichier inattendu
refusés. Le mapping reste dans le sidecar, jamais dans le lot normalisé.

Anciennes archives JSON : même type/version de manifeste et sorties historiques
conservées. Des empreintes figées du préparateur antérieur `b4142425` vérifient le
lot JSON normalisé et son rapport sur une fixture NON OFFICIELLE. Les options CSV
sur un sidecar JSON sont refusées, même si elles valent leur défaut.

Une archive CSV peut être inscrite explicitement au registre existant comme type
`mesures` avec son empreinte de manifeste. Recherche, inventaire, couverture et
[consultation séparée avec un tarif](CONSULTATION_TARIF_MESURES.md) réutilisés ;
aucune route d'upload/import administratif ou publication ajoutée. La sauvegarde
avec quarantaine et la reprise neuve conservent octets et mapping et permettent
le rejeu. Pas de réécriture des anciens dossiers.

## Limites maintenues

Aucun fichier fiscal officiel national acquis ou qualifié par ces tests.
Codes syntaxiques ≠ codes officiels existants ; égalité de code ≠ rattachement
juridique. Dates non héritées, sources non fusionnées, aucun taux applicable choisi.
Pas d’extraction fiscale PDF automatique, OCR fiscal, consolidation à date, validation humaine,
publication, signature d'authenticité, WORM ou transaction multi-dossiers.
Tests sur fixtures explicitement NON OFFICIELLES, pas recette nationale.

Lot 40 : [XLSX textuel à feuille et mapping déclarés](MESURES_AUTONOMES_XLSX.md)
également disponible ; ce contrat CSV et les sorties des archives 39 sont conservés.

Lot 42 : [PDF opaque et transcription JSON déclarée](MESURES_AUTONOMES_PDF.md)
archivables séparément, sans extraction ou fidélité au document vérifiée.
