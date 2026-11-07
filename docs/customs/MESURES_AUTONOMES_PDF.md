# Mesures autonomes : PDF opaque et transcription déclarée — lot 42

Le PDF fiscal reçu peut être archivé avec une transcription JSON **explicitement
fournie**, sans lecture native, OCR, extraction de tableaux/taux ou fidélité au
PDF déduite. Extension de la [préparation autonome](MESURES_AUTONOMES.md), pas
qualification d'un document officiel ou fiscalité applicable.

## CLI et entrées

```sh
unocr customs-fiscal-prepare SOURCE.pdf --metadata METADATA.json --transcription MESURES.json
unocr customs-fiscal-prepare SOURCE.pdf --metadata METADATA.json --transcription MESURES.json --out DOSSIER_NEUF --write
unocr customs-fiscal-check DOSSIER_NEUF
```

- Source du sidecar `MetadataMesuresAutonomes` : format `pdf`, SHA256 des octets
  reçus et métadonnées documentaires habituelles. Domaine HTTPS autorisé ne
  prouve ni téléchargement effectif, authenticité, exhaustivité ou applicabilité.
- Transcription séparée requise seulement pour PDF ; refusée sur JSON/CSV/XLSX/XLS.
  Aucun chemin de transcription recherché dans un sidecar, répertoire ou réseau.
  Le chemin est un argument local explicite ; aucun upload HTTP ajouté.
- Transcription : **tableau JSON de `Mesure`**, comme la source JSON autonome 36,
  pas objet contenant une source/nomenclature. IDs et codes10 textuels exacts,
  taux en chaînes décimales précises ou null, jamais nombre JSON même zéro.
- Référence de chaque mesure obligatoire, source identique au PDF déclaré et
  localisateur non blanc **fourni par la transcription**, jamais généré. Le texte
  peut mentionner une page/article, mais le lecteur ne vérifie ni sa grammaire,
  existence, localisation, fidélité ou portée juridique.
- Les six types de mesures, unités, périodes et IDs uniques du contrat restent
  contrôlés. Aucune date héritée de la publication ; null ≠ zéro ; aucun taux
  applicable choisi. Clés JSON dupliquées/constantes non standard refusées.
- Aucune option tabulaire (`colonnes`, `delimiteur`, `feuille`, `ligne_entete`) sur
  PDF, même explicitement à sa valeur par défaut.

Une transcription vide est admise : zéro mesure reçue, jamais absence de droit
ou exonération. Un localisateur « page 9999 » peut être conservé comme déclaration
non vérifiée même si la fixture PDF a deux pages : ce lot ne localise pas le texte.

## Ce qui est contrôlé et ce qui ne l'est pas

PDF : SHA exact et préfixe `%PDF-` seulement. **Aucun parseur PDF invoqué.**
Ce préfixe ne démontre pas une structure lisible, un document non chiffré, une
absence de contenu actif ou d'infection. Un faux PDF ayant ce préfixe peut être
archivé comme opaque ; ce comportement est testé et explicitement signalé.
Pas d'antivirus, rendu, analyse des pages ou autorisation d'ouverture externe.

Transcription : intégrité, validation structurelle et syntaxique du modèle,
références au même ID de source ; pas rapprochement du contenu avec le PDF.
Une transcription techniquement valide peut être matériellement ou juridiquement
fausse. Elle reste en quarantaine, validation humaine requise/non validée.

Le rapport rend cette séparation explicite :

- `mesures_source_lues: null` (aucune mesure extraite du PDF) ;
- `mesures_transcription_lues` et `mesures_importables` : déclarations du JSON ;
- `lecture_pdf_effectuee: false`, `structure_pdf_verifiee: false` ;
- `transcription_verification: "non_verifiee"` ;
- `transcription_sha256`, également dans le périmètre de lecture ;
- `perimetre_lecture.references: "declarees_non_generees"`.

## Archive et rejeu

Six fichiers exactement :

1. `source_mesures_recue.pdf` : PDF original exact ;
2. `transcription_mesures_recue.json` : transcription originale exacte ;
3. `metadata_original.json` : sidecar original exact ;
4. `lot_mesures.json` : mesures normalisées, source PDF et références déclarées ;
5. `rapport.json` : distinctions et limites ci-dessus ;
6. `manifest.json` : empreintes, nom reçu du PDF et date UTC de préparation.

Le nom de fichier original de la transcription n'est pas stocké séparément ; ses
**octets et son empreinte** le sont. Une seule source JSON/CSV/XLSX/XLS/PDF ; fichier
supplémentaire, transcription absente, mauvaise extension/format ou deux sources
refusés. La transcription séparée est interdite dans les archives non PDF.

Rejeu depuis PDF + sidecar + transcription, comparaison du lot normalisé **et**
du rapport. Ré-hacher la transcription seule, même après un changement d'espaces
sans effet sur les mesures, ne rend pas l'ancien rapport reproductible : son SHA
original reste contrôlé. Remplacer tous les fichiers ensemble ne devient pas une
preuve d'authenticité ; épingle de manifeste et autorisations de revue restent
nécessaires. Manifeste écrit en dernier, pas transaction FS, fsync, WORM ou signature.

Fichiers réguliers non symboliques, 64 Mio maximum par fichier ; ensemble reçu
PDF + sidecar + transcription limité à **128 Mio** ; 100 000 mesures maximum,
64 Mio par artefact normalisé. Lecture complète en mémoire, pas streaming, quota
processus/global ou benchmark de charge. Les refus de borne sont testés avec
seuils réduits, pas par qualification d'un corpus national volumineux.

## Compatibilité et revue existante

Type/version de manifeste inchangés. Anciennes archives à cinq fichiers et
sorties JSON/CSV/XLSX/XLS conservées ; empreintes figées antérieures vérifiées.
Leurs messages de périmètre historiques restent conservés pour leur rejeu.

Inscription explicite au registre comme `mesures` avec SHA du manifeste : contrôle,
recherche des **descriptions transcrites**, sources, couverture, consultation
séparée avec tarif et exports déjà autorisés. Sauvegarde avec quarantaine/reprise
neuve conserve les six fichiers et permet leur rejeu.

**Pas de nouvelle route de lecture/téléchargement du PDF fiscal** : routes PDF
Code refusées sur ces archives, sans détournement de chargeur. Pas de rapprochement
littéral PDF/transcription, validation humaine, consolidation à date, fusion
fiscale, publication ou calcul. Aucun original officiel acquis ou qualifié par les
fixtures PDF/JSON explicitement NON OFFICIELLES de la recette.
