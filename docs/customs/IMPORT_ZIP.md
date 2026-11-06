# Préparation depuis un membre ZIP explicite — lot 19

2026-11-06. **Contrat technique, pas fichier national officiel acquis.**

## Sélection et commandes

Le sidecar de `customs-prepare` déclare `lot.source.format="zip"` et le SHA256
exact du **ZIP reçu**. Deux options sont obligatoires :

- `membre_zip` : nom relatif exact dans l’archive (sensible à la casse), sans glob ;
- `format_contenu` : `csv`, `json`, `xlsx`, `xls` ou `xml`.

Le mapping et les options s’appliquent au format du membre : `colonnes`/délimiteur
pour CSV, lignes structurées avec références déjà présentes pour JSON, feuille et
ligne d’en-tête pour XLSX, racine/ligne pour XML. Aucun format n’est déduit du nom
ou de l’extension du membre. Les options incompatibles sont refusées.

```sh
# Plan sans écriture :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.zip --metadata /chemin/metadata.json
# Archive de préparation dans un répertoire neuf exclusivement :
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.zip --metadata /chemin/metadata.json --out /chemin/lot-neuf --write
```

Un seul membre est lu par un adaptateur existant, sans extraction sur disque,
sans recherche automatique de « meilleur fichier » et sans fusion des autres
membres. Tous les contrôles de codes, parents, provenance, désignations, doublons
et fiscalité séparée demeurent inchangés. Un membre mal formé empêche la préparation.
Les options ZIP sont interdites pour une source directe non ZIP.

## Conservation et traçabilité

La sortie garde **`source_recue.zip` identique aux octets reçus**, le sidecar, le lot,
le rapport et le manifeste final. Pas de sous-répertoire extrait, d’écrasement de
sortie existante ou d’activation. `lot.source.sha256` désigne le ZIP complet ;
`perimetre_lecture.sha256_membre_lu` désigne les octets du membre effectivement lu.
Le périmètre indique aussi nom exact, format du membre, taille et membres exclus.

Les localisateurs générés CSV/XLSX/XML sont préfixés du nom du membre. Pour JSON,
les références déclarées dans les lignes sont **préservées**, sans réécriture ;
le membre lu demeure identifié dans le périmètre du rapport. Ces références ne
sont pas certifiées par le simple contrôle de l’archive.

Le chargeur central vérifie les empreintes puis rejoue le ZIP, la sélection et le
lecteur. Un lot normalisé altéré puis re-haché reste refusé s’il diverge du rejeu.
La revue API utilise les mêmes habilitations, épingles et audit local obligatoire.
Pas de route d’import HTTP ou d’accès à un chemin fourni par le navigateur ajouté.

## Contrôles ZIP et limites

- ZIP ordinaire, sans préambule auto-extractible/concaténation ambiguë ; noms sûrs,
  uniques, sans chemins absolus, traversal, backslash, deux-points ou contrôles.
- Refus des symlinks/membres spéciaux/types ambigus et des flags de chiffrement ;
  compression STORE ou DEFLATE seulement.
- ZIP reçu ≤64 Mio, 256 membres, membre ≤64 Mio, somme des tailles déclarées
  ≤128 Mio, ratio déclaré ≤200. Lecture du membre bornée et non vide.
- CRC et lecture du membre sélectionné contrôlés par `zipfile` ; SHA256 calculé.
  Pour les autres membres : contrôle des **métadonnées ZIP uniquement**, aucun
  contrôle CRC/contenu, antivirus ou certification documentaire. Ils peuvent être
  corrompus ou dangereux et ne doivent pas être ouverts sans procédure distincte.

Les tailles/ratios déclarés ne garantissent pas une consommation globale de mémoire
ou temps constante. Le ZIP original est conservé comme source non fiable, pas
assaini. Le lecteur n’est pas un antivirus, bac à sable OS, déchiffreur ou preuve
éditeur. Le XLSX sélectionné reste un paquet interne contrôlé par son adaptateur ;
aucune récursion générique ZIP→ZIP n’est permise. Le [XLS textuel BIFF8](IMPORT_XLS.md) est pris en charge au lot 20 ; le PDF
tarifaire reste non qualifié. Une archive nationale réelle pourra nécessiter un autre contrat explicite.

**Code retour 0 = préparation techniquement admissible seulement**, ni officiel,
complet, applicable ou juridiquement validé. [Qualification](RAPPORT_LOT19.md).
