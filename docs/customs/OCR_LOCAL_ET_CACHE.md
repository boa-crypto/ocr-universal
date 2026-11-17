# Lot 62 — OCR local réel et suspension du cache non contextuel

7 novembre 2026. Ce document ne qualifie ni un corpus officiel ni une installation
OCR de production. [Versions, commits, empreintes et options exactes](PROVISIONNEMENT_OCR_LOT62.json).

## Correction de comportement

`Pipeline._process_page` consultait SQLite sur le seul SHA-256 de l'image PNG,
avant de considérer les options. Une page déjà traitée en natif pouvait donc
répondre à une demande Tesseract forcée ; le prétraitement, les variantes,
les langues, les moteurs disponibles et la pagination pouvaient aussi être
incorrectement recyclés. Trois tests d'options échouaient après installation
réelle de Tesseract, dont un prétraitement standard remplacé par un ancien « off ».

**Lecture et écriture de ce cache suspendues dans le pipeline.** Ce choix
conservateur privilégie la justesse, au prix de nouveaux calculs OCR sur des
pages répétées. Le module `PageCache` reste compatible mais n'est plus appelé ;
aucune purge ni migration des bases existantes. Pas nouveau cache prétendument
exhaustif : avant toute réactivation, qualifier l'identité du calcul (options,
configuration, couche native, moteurs/modèles/calibration, page, versions, etc.),
son invalidation et les erreurs de stockage. Les temps tracés correspondent à
nouveau aux moteurs exécutés, pas à une ancienne exécution mise en cache.

Douze tests unitaires avec doubles explicitement synthétiques couvrent les
entrées historiques, demandes différentes, résultat moteur modifié,
indisponibilité, numéros de page et passage natif → raster forcé. Ils ne sont
pas présentés comme une preuve de reconnaissance réelle. Les tests OCR existants
sont exécutés séparément avec le vrai binaire et ses modèles.

Le test de secours de capture, auparavant ignoré sans Tesseract, régénérait
16 PNG suivis dans `benchmarks/field_samples`. Le générateur accepte désormais
une destination explicite ; pytest utilise `tmp_path` et `tmp_cfg`. Deux tests
vérifient cette destination et le défaut manuel historique, sans réécrire Git.
La première complète a régénéré ces PNG : restauration explicite de nos seules
modifications avant la complète finale. Les journaux existants sont préservés.

## Provisionnement effectué

Binaire compilé depuis `madler/zlib`, `pnggroup/libpng`,
`DanBloomberg/leptonica`, `tesseract-ocr/tesseract`, archives codeload GitHub
référencées par commits dans le manifeste. Compilateur GCC/G++, make, CMake
**4.4.4** installé dans le venv via PyPI public ; compilation à deux tâches,
Release, bibliothèques partagées. Pas installation système, wrapper WASM,
moteur simulé, substitution de reconnaissance ou modification des assertions.
Modèles `eng`, `fra`, `ara` provenant du dépôt `tesseract-ocr/tessdata_fast`,
commit et blobs épinglés dans le manifeste. Pas modèle Indra installé : les poids
annoncés sur Hugging Face restent hors des hôtes réseau autorisés.

**Limite volontaire de cette compilation : PNG/PNM**, sans codecs JPEG/TIFF/GIF/
WebP/OpenJPEG. Leptonica émet des avertissements TIFF lors de l'initialisation de
polices internes ; ils figurent dans le journal de compilation. La présence des
modèles arabes n'est pas une qualification exhaustive de l'OCR arabe. Aucune
couverture de formats générale ou performance terrain n'est déduite des tests.
Les sources, modèles et bibliothèques sont hors Git, dans les caches locaux et
`.venv/ocr-native`. Les licences amont restent applicables (notamment Apache-2.0
Tesseract/tessdata, zlib, libpng et Leptonica) ; pas redistribution binaire livrée.
Les empreintes attestent les octets observés, pas une signature éditeur ni un
build bit-à-bit reproductible.

### Refaire cette compilation

Le manifeste permet de reconstruire avec les mêmes sources, sans rechercher
« latest ». Prérequis : Python, GCC/G++, make, CMake 4.4.4, `gh` connecté à GitHub.
Choisir un préfixe et des répertoires de travail **vides hors du corpus suivi**.
Pour chaque entrée `sources`, dans l'ordre du manifeste :

1. Télécharger `https://codeload.github.com/{repo}/tar.gz/{commit}`.
2. Vérifier le SHA-256 contre `archive_sha256`, refuser tout écart. Extraire dans
   un répertoire propre après contrôle des chemins (pas absolus/`..` sortants,
   ni liens/fichiers spéciaux). Nos archives ont été contrôlées ainsi avant usage.
3. Configurer le répertoire source extrait :

```sh
cmake -S "$source" -B "$build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" \
  -DCMAKE_INSTALL_LIBDIR=lib -DCMAKE_PREFIX_PATH="$prefix" \
  -DCMAKE_INSTALL_RPATH="$prefix/lib" -DBUILD_SHARED_LIBS=ON \
  "${options[@]}"
cmake --build "$build" --parallel 2
cmake --install "$build"
```

`options` est le tableau exact de chaque entrée, pas un argument JSON littéral.
Pour chaque modèle du manifeste, `gh api repos/tesseract-ocr/tessdata_fast/git/blobs/{git_blob_sha1}`
retourne un contenu base64. Décoder, vérifier sa taille et son SHA-256 avant
installation sous `$prefix/share/tessdata/{nom}`. Conserver les licences des
sources téléchargées ; ce descriptif n'est pas un installateur/sandbox de production.

Activation locale réellement utilisée (à refaire dans chaque nouveau shell) :

```sh
prefix="$PWD/.venv/ocr-native"
export PATH="$prefix/bin:$PATH"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TESSDATA_PREFIX="$prefix/share/tessdata"
tesseract --version
tesseract --list-langs
.venv/bin/python -m pytest -q --junitxml=/chemin/hors-du-depot/pytest.xml
```

L'aperçu a été redémarré avec ces variables et écoute `0.0.0.0:8000`. Elles ne
sont pas injectées dans les profils utilisateur ou le workflow CI. La substitution
OpenCV headless locale du lot 61 reste inchangée ; ni pyproject ni lock modifiés.
