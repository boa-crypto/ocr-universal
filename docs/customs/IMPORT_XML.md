# Préparation tarifaire XML tabulaire — lot 18

2026-11-06. **Adaptateur de contrat explicite, aucun tarif national importé.**

## Structure acceptée

Le lecteur accepte uniquement un XML 1.0 UTF-8 tabulaire plat : un élément racine,
contenant exclusivement des éléments de ligne ; chaque ligne contient des champs
texte simples. Le sidecar habituel fournit le lot sans ses lignes, le SHA256 exact
des octets source et le mapping `colonnes` entre champs canoniques et noms XML.
Il doit aussi fournir **`racine_xml`** et **`ligne_xml`** : noms simples ASCII,
1 à 64 caractères, sans XPath, préfixe ou espace de noms.

Les colonnes sont les noms des champs enfants, pas des attributs. Tous les champs
d’une ligne doivent être uniques et toutes les lignes doivent avoir le même jeu
de noms ; l’ordre peut varier. Les champs non mappés sont signalés dans
`colonnes_non_importees`, jamais interprétés comme des taux ou mesures. Une racine
sans ligne ou une ligne vide est refusée. Aucun autre élément racine/ligne annexe
n’est silencieusement ignoré. Les espaces d’indentation seuls sont permis hors champs.

Le mapping et les contrôles métier existants restent centraux : codes10 ASCII en
chaînes, zéros initiaux, parents 2/4/6 et sections déclarés, références, doublons,
désignations, dates et interdiction de fiscalité non sourcée. Aucun code n’est
complété par des zéros ou déduit d’un format d’affichage ; aucun taux n’est inventé.
Un champ XML vide devient une chaîne vide, puis suit les règles existantes du
mapping (null pour certains champs facultatifs, refus pour un code obligatoire).

## Limites de format et sécurité

- DTD, entités **déclarées**, références externes, commentaires et instructions de
  traitement refusés ; aucune résolution réseau ou lecture d’une cible externe.
- Attributs, espaces de noms, champs imbriqués, contenu mixte et autre encodage
  refusés. Options CSV/XLSX interdites pour XML ; options XML interdites hors XML.
- Entités XML prédéfinies (`&amp;`, etc.), références numériques et CDATA sont
  interprétées comme texte par XML 1.0. Les fins de ligne suivent la normalisation
  XML : les valeurs ne prétendent donc pas être des sous-chaînes octet à octet.
  Les octets originaux reçus, eux, sont intégralement conservés et empreintés.
- Bornes : source 64 Mio, 200 000 lignes, 256 champs/ligne, 2 000 000 cellules,
  1 048 576 caractères Python par champ. Structure de trois niveaux seulement.
  Pas de garantie globale de mémoire/temps pour des fichiers arbitraires hostiles.

L’adaptateur est volontairement **non générique** : pas de XSD officiel, XPath,
XML hiérarchique national, transformation XSLT ou archive ZIP. Un document officiel
hors contrat devra faire l’objet d’un adaptateur explicite et de tests sur ce format,
pas d’une conversion silencieuse. XLS, PDF tarifaire et ZIP restent non qualifiés.

## Commandes et conservation

```sh
# Plan sans écriture :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.xml --metadata /chemin/metadata.json
# Préparation explicite dans un répertoire neuf :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.xml --metadata /chemin/metadata.json --out /chemin/lot-neuf --write
```

Le sidecar déclare `lot.source.format="xml"`, `racine_xml`, `ligne_xml` et `colonnes`.
Le nom du fichier remis n’est pas une preuve de format ; source et métadonnées sont
vérifiées avant écriture. Résultat 0 = préparation techniquement admissible, pas
publication ou validation juridique. Une sortie existante n’est jamais écrasée.

La préparation garde `source_recue.xml`, `metadata_original.json`, `lot.json`,
`rapport.json` puis le manifeste final. La provenance d’une ligne indique l’élément
et sa ligne physique d’ouverture dans le XML ; l’encodage, les noms racine/ligne et
la normalisation sont rappelés dans `perimetre_lecture`.

Le chargeur central vérifie les empreintes et **rejoue le XML et le mapping** avant
consultation/comparaison. Un lot normalisé altéré puis re-haché reste refusé s’il
diverge de ce rejeu. La revue API réutilise ce chargeur, l’habilitation nominative,
l’épingle du manifeste et l’audit obligatoire. Aucun import HTTP ou activation
n’est ajouté ; l’enregistrement d’un lot reste une opération administrative séparée.
La sauvegarde/reprise opt-in du lot 7 conserve aussi les octets XML.

[Rapport de qualification](RAPPORT_LOT18.md). L’intégrité locale ne démontre ni
l’authenticité éditeur, ni la complétude nationale, ni le droit applicable.
