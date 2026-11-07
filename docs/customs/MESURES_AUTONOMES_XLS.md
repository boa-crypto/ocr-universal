# Mesures autonomes XLS — sous-ensemble OLE/BIFF8 du lot 41

Extension de la [préparation autonome](MESURES_AUTONOMES.md), sans nomenclature
inventée, fiscalité active ou qualification d'un original officiel. Réutilise le
[lecteur XLS restreint](IMPORT_XLS.md) existant, pas un nouveau moteur Excel.

## CLI et configuration

```sh
unocr customs-fiscal-prepare MESURES.xls --metadata METADATA.json
unocr customs-fiscal-prepare MESURES.xls --metadata METADATA.json --out DOSSIER_NEUF --write
unocr customs-fiscal-check DOSSIER_NEUF
```

Plan sans écriture par défaut ; dossier neuf requis pour écrire. Sidecar suivant
`ConfigurationMesuresAutonomes` : source de format `xls`, SHA256 exact des octets
reçus, feuille explicitement nommée, en-tête entier entre 1 et 50 (défaut 1),
mapping `colonnes` explicite. Exemple de fragment NON OFFICIEL à compléter avec
les véritables métadonnées et l'empreinte de sa propre source :

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

Quatre premiers mappings requis, autres facultatifs. Noms d'en-têtes exacts,
textuels, non blancs et uniques ; champs inconnus, références réservées,
colonnes partagées et noms introuvables refusés. `delimiteur` interdit même égal
au défaut. Les options de feuille restent interdites sur JSON/CSV.

## Contrat plus restrictif que XLSX

- Vrai conteneur OLE avec flux `Workbook` et BIFF8 ; pas de HTML/CSV renommé,
  BIFF ancien, chiffrement ou récupération silencieuse d'un classeur corrompu.
- Garde OLE existante : 128 entrées maximum, flux au niveau racine limités à
  `Workbook` et aux deux flux de propriétés documentaires admis ; stockages,
  flux supplémentaires, doublons, projets VBA/objets hors contrat refusés.
- Scan BIFF du **classeur entier** avant lecture des valeurs : records de
  formules, liens, noms, objets, fusions et autres records interdits du lecteur
  existant refusés, y compris formule sur une feuille non importée. Sous-ensemble
  restrictif, pas analyse de sécurité exhaustive de tous les records BIFF.
- Une feuille tabulaire visible choisie explicitement ; autres noms listés mais
  données métier non importées. Feuille cachée/fusionnée refusée dans ce contrat.
- **Toutes les cellules lues de la feuille sélectionnée depuis l'en-tête doivent
  être textuelles ou vides**, y compris les colonnes non mappées. Contrairement
  à XLSX 40, même un nombre ordinaire dans une colonne non importée est refusé.
- Codes numériques refusés même affichés avec dix zéros ; taux numériques, zéro
  numérique, dates Excel, booléens et erreurs refusés. Aucune formule exécutée,
  valeur en cache utilisée, conversion float/str, format d'affichage ou `zfill`.
- Préambule avant l'en-tête non importé ; sa signification n'est pas validée.
  La garde binaire sur les records interdits reste globale. Lignes entièrement
  vides du parcours ignorées et comptées ; leur position ne décale pas les
  références réelles. Les vides finaux hors plage renvoyée par xlrd ne sont pas
  un inventaire physique exhaustif de tous les records du fichier.
- En-tête seul admis : zéro mesure reçue, jamais exonération. Cellules au-delà
  des en-têtes refusées ; colonnes et feuilles non importées signalées.

Taux textuels précis, zéro textuel et null restent distincts. Valeurs absentes
ou chaînes vides → null uniquement pour taux/unité/dates. Aucun ID ou code
fabriqué ; `Mesure` valide code10 ASCII exact, types/unités, taux et périodes.
Référence générée : `XLS, feuille NOM, ligne N`, source du sidecar, pas preuve
juridique, page PDF ou article officiel.

## Bornes, archive et revue

Bornes existantes : 64 Mio de fichier/flux Workbook, 500 000 records BIFF,
200 000 lignes, 256 colonnes et 2 000 000 cellules pour les contrôles du lecteur ;
les limites propres à BIFF8 s'appliquent aussi. Modèle autonome : 100 000 mesures
maximum, 64 Mio par artefact archivé. Lecture en mémoire ; pas de streaming,
quota de concurrence, bac à sable OS ou antivirus universel ajouté.

Archive à cinq fichiers : `source_mesures_recue.xls`, `metadata_original.json`,
`lot_mesures.json`, `rapport.json`, `manifest.json`. Source/sidecar exacts, une
seule source JSON/CSV/XLSX/XLS cohérente avec son format, empreintes et rejeu du
lot/rapport. Options de lecture non intégrées au lot normalisé ; manifeste écrit
en dernier comme auparavant, pas de transaction FS, signature ou WORM.

Sorties JSON/CSV historiques conservées. Empreintes du préparateur et de
l'adaptateur XLSX 40 également vérifiées : fixture NON OFFICIELLE, dates ZIP et
propriétés de date neutralisées uniquement pour rendre cette preuve de
non-régression reproductible, jamais pour réécrire un original reçu en production.
Les anciens messages de périmètre sont conservés pour rejouer leurs rapports.

Inscription explicite au registre en type `mesures` avec empreinte de manifeste ;
recherche FR/AR, sources, couverture et consultation séparée tarif/mesures
réutilisées. Sauvegarde avec quarantaine et reprise dans un magasin neuf testées.
Aucun upload administratif ou API de publication ajouté.

## Non établi

Aucun fichier fiscal officiel qualifié ou original national acquis par ces tests.
XLS universel, PDF fiscal autonome, authenticité, exhaustivité, rapprochement
juridique, droit à date, contrôle humain, publication et calcul restent hors
périmètre. Égalité de code ou SHA/rejeu ne déterminent jamais le taux applicable.
Fixtures exclusivement NON OFFICIELLES ; pas recette nationale ou de charge.
