# Rapport lot 61 — cohérence des compteurs JUnit et reprise d'environnement

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Le bilan ciblé exige désormais que chaque compteur déclaré corresponde aux cas et
statuts XML réellement présents. Rapports incohérents, statuts contradictoires ou
compensation de compteurs négatifs refusés avant un bilan positif. Lecture bornée,
fichier régulier, UTF-8, profondeur limitée, pas DTD/entités ni symlink final.

[Contrat et limites](COHERENCE_JUNIT.md), [recette machine](RECETTE_LOT61.json).

## Qualification exécutée

- **36 nouveaux cas**, soit **54 tests du lanceur** réussis.
- Lanceur ciblé réel : **2 160 réussis, 66 fichiers, 0 ignoré, 1 avertissement,
  52,44 s** ; compteurs JUnit contrôlés sur ces cas. Ruff code 0 et **212 scénarios
  JSDOM** existants réussis. Pas nouveau scénario d'interface métier attribué.
- Les quatre ponts UI/API rejouent encore **74 exports** (62 simples dont 14 PDF,
  12 paires, dont 4 rapports de pistes) et contrôlent 4 copies PDF Code. Pas nouvelle
  qualification juridique ou nouveau corpus.
- **Nouvelle complète finale, avec aperçu actif : 3 192 réussis, 18 échecs,
  11 ignorés, 1 avertissement, 218,99 s**, soit **3 221 tests**, code **1**.
  Les 18 identifiants d'échec sont exactement ceux du lot 60, comparaison JUnit.
  Le nouveau lecteur confirme `lisible:true`, `compteurs_coherents_avec_cas:true`
  mais `selection_sans_echec_ni_ignore:false` sur ce vrai rapport non vert.
- **27/27 empreintes conformes à la recette 56** après les tests, sans restauration
  des fixtures. Journaux historiques préservés hors commit. Artefacts bruts dans
  `/home/user/recettes-unocr/lot61`.

## Environnement réellement utilisé

Le checkout reconstitué présentait les fichiers des lots précédents mais HEAD et
index au commit initial, sans `.venv`. Référence distante du lot 60 récupérée puis
réalignement **mixed** sur cette même branche, index préalablement sans staged ;
les 24 584 fichiers contrôlés ont gardé leurs empreintes. Pas changement de branche,
reset hard, écrasement de fichiers, données ou journaux. Les métadonnées egg-info
régénérées par notre installation ont été restaurées explicitement car propres
avant celle-ci ; elles ne font pas partie du lot.

Dépendances réinstallées strictement depuis pyproject/dev, puis `npm ci`. Première
collecte interrompue par **53 erreurs d'import OpenCV, libGL.so.1 absente** ; ce
résultat n'est pas caché. Dans le venv local seulement, opencv-python 5.0.0.93 a
été remplacé par **opencv-python-headless 5.0.0.93**. Aucun changement de dépendance
projet/lock, aucune bibliothèque OCR simulée ; cette substitution ne signifie pas
que le venv satisfait littéralement l'exigence pip `opencv-python` du projet.
La sélection de référence 60 a ensuite passé ses 2 124 tests avant modification.

Première complète après développement, sans serveur : **3 190 réussis, 18 échecs,
13 ignorés, 153,35 s**. Deux tests JSDOM dépendants du serveur ont été ignorés
explicitement. Après remise en service de l'aperçu **0.0.0.0:8000 / SW v70**,
recette relancée : résultat final ci-dessus avec 11 ignorés. Les deux tests ne sont
pas transformés en réussites par une modification d'assertion ou de marqueur.
Python local 3.11.2 ; Tesseract/Indra toujours absents. Aucun échec annoncé résolu.
Les durées entre environnements ne constituent pas un benchmark de performance.

## GitHub Actions

Code **`52a20009`**, run
**[42393053789](https://github.com/boa-crypto/ocr-universal/actions/runs/42393053789)**
terminé **success**, révision et statut confirmés via `gh run view`. Le job ciblé
installe ses dépendances normales sur Ubuntu 24.04 / Node 24 / Python 3.11 : la
substitution OpenCV locale n'est pas ajoutée au workflow. Chiffres détaillés de
recette mesurés localement, pas extraits d'un JUnit distant téléchargé. La suite
OCR complète reste non verte malgré ce succès ciblé.

Aucun changement du classement/recherche, API, UI, cache, publication ou corpus.
**Mission réglementaire partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
