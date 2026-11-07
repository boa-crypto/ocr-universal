# Rapport lot 64 — ingestion PDF concurrente et fermeture native

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

[Contrat technique et limites](CONCURRENCE_INGESTION_PDF.md),
[recette machine](RECETTE_LOT64.json).

## Défaut reproduit et correction

Quatre threads chargeant des PDF synthétiques distincts dans un processus isolé
ont reproduit un arrêt natif avant correction : `corrupted size vs. prev_size`,
`Fatal Python error: Aborted`, code shell **134**. Le même programme termine ses
**20 chargements**, code **0**, après correction. Cela reproduit un défaut natif
concurrent ; pas preuve rétrospective de la cause exacte de la perte du serveur
signalée au lot 63. L'amont pypdfium2 documente l'absence de thread-safety de PDFium.

Un **RLock par processus** protège désormais toute l'ingestion PDF : création,
comptage, extraction native, rendu et fermeture. Les documents, pages et bitmaps
sont fermés explicitement, même sur refus du nombre de pages et erreurs de lecture
ou conversion. Les pixels sont copiés avant fermeture ; seuls des objets Python
et images détachées sortent de la section. Les jobs ne sont pas tous réduits à une
seule exécution : OCR et étapes suivantes restent hors de ce verrou.

## Vérifications exécutées

- **16 nouveaux tests Python** : 12 cas unitaires de verrou/fermeture, 3 stress
  PDFium réel en processus enfants, 1 parcours HTTP de dépôts concurrents.
- Les stress font **60 chargements / 90 pages**, quatre threads à 72/100/144 DPI,
  documents natifs, scannés et multipages synthétiques. Pas reconnaissance OCR
  prétendue pour les scans, seulement chargement et rendu réels.
- **Quatre requêtes de dépôt simultanées**, quatre jobs distincts `done`, une
  tentative chacun, SHA-256 et nombres de pages correspondants, textes natifs
  présents, API health toujours joignable. Serveur et données temporaires ; aucune
  dépendance au magasin de l'aperçu ni à Tesseract/Indra pour cette sélection.
- Sélection PDF/ingestion/UI finale : **32 réussis, 0 échec, 0 ignoré, 44,69 s**
  (16 nouveaux, 8 tests d'ingestion existants et 8 tests UI existants).
- Sélection documentaire inchangée : **2 160 réussis, 0 échec, 0 ignoré,
  1 avertissement, 55,19 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM** réussis.
  Quatre ponts et 74 exports existants conservés, pas nouvelle recette métier.
- **Complète finale : 3 254 réussis, 2 échecs, 1 ignoré, 1 avertissement,
  333,52 s**, soit **3 257 tests**, code **1**. Durée JUnit 332,356 s, distincte
  de la durée console. Compteurs JUnit cohérents avec les cas réels, pas bilan
  complet vert. Deux échecs exactement identiques au lot 63, liés à Indra absent ;
  seul ignoré : `test_indra_engine_recognize`.

La première complète donnait **3 253 réussis, 3 échecs, 1 ignoré, 340,86 s**.
L'échec supplémentaire était le double historique du test de limite de pages,
sans protocole de contexte. Adapté au contrat réel : refus avant extraction/rendu
conservé, assertion de fermeture ajoutée. Ce test et les sept autres tests
existants d'ingestion sont désormais également exécutés dans l'étape PDF de CI.
Aucune assertion de moteur assouplie, aucun nouveau marqueur d'ignoré.

## Intégrité — écart constaté, non masqué

Après la première complète, **27/27 empreintes historiques** correspondaient
encore à la recette 56. Après la finale : **26/27** seulement. Le fichier partagé
`data/referentiels.json` a changé :

- attendu : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b` ;
- observé : `b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`.

Quatre dossiers historiques suivis ont également changé dans l'espace partagé :
`dos_85b0f264dc36`, `dos_bc3ee32380d9`, `dos_c43ad60245d4`, `dos_f76099842795`.
Provenance de ces changements **non attribuée avec certitude**. Ils sont
**préservés hors commit**, comme les journaux et données exploratoires ; aucune
restauration pour forcer une empreinte conforme. Empreintes ponctuelles avant/
après consignées dans les artefacts locaux, pas certification de l'intégrité
complète du magasin. Les PNG de benchmark, fixtures de tests et cache suivis
n'ont pas été régénérés/restaurés par cette correction. Les 16 nouveaux tests
utilisent des répertoires temporaires.

## CI vérifiée

Code final **`4028202a`**, run
**[42398432474](https://github.com/boa-crypto/ocr-universal/actions/runs/42398432474)**
terminé **success**, révision et étapes confirmées via `gh` : 24 tests PDF/
ingestion, 8 tests UI, puis sélection documentaire. Le premier run du code natif,
[42398005189](https://github.com/boa-crypto/ocr-universal/actions/runs/42398005189),
était également réussi, mais n'incluait pas encore les huit anciens tests
d'ingestion. Les annotations diagnostiques couvrent désormais PDF et rendu.
Cette CI ne lance **pas** la suite OCR complète. Chiffres détaillés mesurés
localement, pas issus d'un JUnit distant téléchargé.

Artefacts bruts : `/home/user/recettes-unocr/lot64`. Python 3.11.2,
pypdfium2 5.15.0, pdfminer.six 20260107, Pillow 13.0.0 localement. Aperçu redémarré
avec le correctif sur `0.0.0.0:8000` et activation OCR locale du lot 62.

## Limites

L'ingestion PDF est sérialisée par processus : coût possible en débit, pas de
FIFO, de timeout natif principal ou de nouvelle sandbox OS. Une extension qui
appelle directement PDFium ailleurs, ou un fork pendant un verrou détenu, n'est
pas couvert. Essais synthétiques limités, pas preuve d'absence de tous les défauts
natifs, sécurité de PDF hostiles, charge nationale ou garantie « zéro crash ».
Le worker documentaire jetable séparé est inchangé. Aucun modèle/codec ajouté,
cache OCR toujours suspendu. Indra reste absent, sans contournement réseau.

**Mission réglementaire partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
