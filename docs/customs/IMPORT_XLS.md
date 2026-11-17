# Préparation XLS historique : sous-ensemble OLE/BIFF8 textuel — lot 20

2026-11-06. **Contrat restreint, pas qualification universelle Excel ou tarif national.**

## Pourquoi un contrôle binaire

`xlrd`, déjà dépendance de production, peut restituer la valeur en cache d’une
formule sans l’exposer comme formule via l’API cellule. Lire uniquement ces valeurs
risquerait de traiter un résultat calculé comme un code littéral. Le lecteur
contrôle donc le répertoire OLE et parcourt les records du flux Workbook **avant**
la lecture des cellules. Aucune formule n’est évaluée ; son cache n’est pas admis.

## Périmètre admis

- Conteneur OLE avec flux `Workbook`, version BIFF8 seulement, globales puis feuilles
  tabulaires ; pas de BIFF antérieur, HTML/CSV renommé `.xls`, XLSB ou paquet XLSX.
- Feuille sélectionnée explicitement par `feuille`, visible, avec `ligne_entete`
  entière de 1 à 50. Mapping `colonnes` habituel ; préambule avant en-tête exclu.
- En-têtes textuels uniques/non vides. Après l’en-tête, cellules texte ou vides
  uniquement, **y compris les colonnes non mappées**. Nombres, dates Excel, booléens,
  erreurs et codes rendus sur dix chiffres par format d’affichage sont refusés.
- Réutilisation des codes chaîne ASCII, parents, doublons, désignations, périodes,
  provenance et mesures séparées ; aucune conversion de nombre, zfill ou taux inventé.

La politique est volontairement restrictive : records de formule/tableau, noms
définis, liens externes, objets, dessins, liens hypertextes, fusions et chiffrement
reconnus sont refusés dans **tout le flux Workbook**, pas seulement la feuille
sélectionnée. Les autres feuilles ne fournissent aucune ligne mais peuvent donc
faire refuser le fichier. Les flux/stockages OLE supplémentaires sont refusés, sauf
les deux flux de résumé usuels à la racine, dont le contenu n’est pas validé.
Les macrosheets/sections non tabulaires et projets VBA ne sont pas admis au contrat.
Ce n’est pas une détection exhaustive de toute menace ou record inconnu.

## Commande et conservation

```sh
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.xls --metadata /chemin/metadata.json
PYTHONPATH=src python -m unocr.cli customs-prepare /chemin/source.xls --metadata /chemin/metadata.json --out /chemin/lot-neuf --write
```

Sidecar : `lot.source.format="xls"`, SHA256 exact, `feuille`, éventuellement
`ligne_entete`, `colonnes` et hiérarchie/source habituelles. Une cellule date doit
être transcrite explicitement en texte ISO par une procédure source documentée si
elle doit être importée ; ce lecteur ne fait pas cette conversion. Ne pas écraser
un original pour le rendre compatible : conserver toute transformation séparément.

Plan sans écriture par défaut ; sortie neuve sur option explicite, fichier
`source_recue.xls` identique aux octets reçus, sidecar, normalisé, rapport et
manifeste. Le localisateur donne feuille/ligne ; périmètre avec contrat BIFF8 et
feuilles non importées. Le chargeur vérifie les empreintes et rejoue le lecteur.
Le même sous-ensemble est accepté comme membre `format_contenu="xls"` dans le
[ZIP explicite](IMPORT_ZIP.md). Aucune extraction ou activation n’est ajoutée.

## Bornes, dépendances et limites

Source 64 Mio, 128 entrées OLE, 500 000 records BIFF ; bornes lignes/colonnes/cellules
partagées avec le lecteur XLSX (200 000 / 256 / 2 000 000), dimensions déclarées
contrôlées avant lecture et rectangle réel après chargement. Le format XLS a aussi
ses propres limites historiques. Pas de garantie de mémoire/temps constants,
notamment si des dimensions sont mensongères. Pas de bac à sable OS, antivirus,
réparation, déchiffrement, signature, WORM ou certification d’authenticité.
Les diagnostics internes de xlrd ne sont pas recopiés dans la sortie CLI.

`xlwt==1.3.0` sert **uniquement à générer les fixtures de tests** ; ajouté au groupe
`dev` et au verrou de l’environnement de qualification, pas aux dépendances runtime.
Le lecteur de production utilise `xlrd`, déjà présent. Installer les dépendances
`dev` pour exercer les fixtures BIFF8 ; sans xlwt, ces cas sont explicitement sautés,
jamais comptés comme réussites.

Code 0 : préparation techniquement admissible seulement, **pas** valeur applicable,
complétude nationale ou validation juridique. [Rapport](RAPPORT_LOT20.md).
