# Rapport lot 62 — Tesseract réel et cache OCR non contextuel

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

## Réalisations

- Compilation locale de **Tesseract 5.5.4 / Leptonica 1.87.0**, zlib 1.4,
  libpng 1.6.59, depuis les dépôts amont GitHub ; modèles **eng/fra/ara** de
  tessdata_fast. Reconnaissance réelle exécutée, pas seulement `--version`.
- **Cache SQLite par pixels suspendu dans le pipeline**, sans purge : un résultat
  antérieur pouvait ignorer moteur forcé, prétraitement, variantes ou pagination.
  Pas prétention d'avoir construit une nouvelle clé exhaustive. Coût assumé :
  les pages répétées sont recalculées.
- Génération du benchmark de capture déplacée sous répertoire temporaire pour
  pytest ; défaut du générateur manuel conservé. Le test auparavant ignoré faute
  de moteur ne doit plus réécrire les PNG suivis.
- **14 nouveaux tests** : 12 régressions de cache avec doubles explicitement
  unitaires, 2 destinations du générateur synthétique. Contre-épreuve avec le
  pipeline exact du lot 61 chargé dans un processus séparé : **12/12 échouent**,
  code 1 attendu ; avec la correction, sélection de régression **88/88 réussis**,
  1 avertissement, 15,92 s. Aucun fichier source remplacé pour cette contre-épreuve.

[Contrat, limites et reconstruction](OCR_LOCAL_ET_CACHE.md),
[versions/commits/empreintes](PROVISIONNEMENT_OCR_LOT62.json),
[recette machine](RECETTE_LOT62.json).

## Recettes exécutées

- Sélection documentaire inchangée : **2 160 réussis, 0 échec, 0 ignoré,
  1 avertissement, 59,22 s, 66 fichiers** ; Ruff et **212 scénarios JSDOM**
  réussis. Quatre ponts réels et 74 exports existants, pas nouveau scénario
  d'interface métier ou nouvelle validation juridique attribués.
- Première complète, avant isolation du benchmark : **3 229 réussis, 2 échecs,
  2 ignorés, 1 avertissement, 305,79 s**. Les 16 PNG de benchmark régénérés et
  notre ancienne écriture du cache (essais initiaux avant correction) ont été
  restaurés explicitement : ils étaient propres avant nos essais.
- **Complète finale : 3 231 réussis, 2 échecs, 2 ignorés, 1 avertissement,
  313,01 s, 3 235 tests, code 1.** Compteurs JUnit cohérents avec les cas réels.
  **16 des 18 identifiants d'échec du lot 61 passent désormais**, aucun nouvel
  identifiant d'échec dans cette complète. Ne pas attribuer tous ces gains au
  code : l'installation réelle du moteur est une condition majeure du résultat.
- **27/27 empreintes historiques conformes**, sans restauration après finale ;
  les 16 PNG de benchmark et la base de cache suivis restent propres également.
  Les journaux historiques et les dossiers temporaires de jobs sont laissés
  hors commit. Artefacts bruts : `/home/user/recettes-unocr/lot62`.

### Restes connus, sans les masquer

Les deux échecs de la complète sont :

- `tests/test_indra_ocr.py::test_indra_engine_availability` ;
- `tests/test_ocr.py::test_selection_prefers_native_when_present` (attend Indra).

Indra et ses poids ne sont pas installés ; pas activation fictive par simple
import, moteur de remplacement ou contournement de l'allowlist réseau.

Les deux tests ignorés sont la reconnaissance Indra et le rendu documentaire
qui cherche par défaut un serveur **8123**. L'aperçu réel est sur **8000**.
Ce dernier test a ensuite été exécuté séparément avec `UNIOCR_TEST_PORT=8000` :
**1 échec, 0 ignoré, 0,32 s**. Il révèle une dette supplémentaire du contrôleur
historique : `_dossier_render_src.js` cherche encore une région DOSSIER inline
alors que le module est servi séparément via `/dossier.js` ; `_hub_render.js`
signale aussi `CnxHub is not defined`. Ces erreurs sont conservées dans
`ui-dossier.log`, pas corrigées ni transformées en succès dans ce lot.
**Le bilan connu n'est donc pas « seuls deux défauts subsistent »** : deux
échecs OCR dans la complète et un contrôle UI optionnel supplémentaire en échec.
Le résultat isolé n'est pas fusionné artificiellement avec les totaux JUnit.

## CI et environnement

Code **`db864999`**, CI ciblée
**[42395442147](https://github.com/boa-crypto/ocr-universal/actions/runs/42395442147)**
terminée **success**, révision/statut vérifiés via `gh`. Cette CI ne compile pas
notre Tesseract local, ne lance pas la suite OCR complète ni les 14 nouveaux tests
hors sélection documentaire. Chiffres détaillés mesurés localement, pas issus
 d'un JUnit distant téléchargé.

Compilation locale limitée PNG/PNM, sans JPEG/TIFF/GIF/WebP/OpenJPEG ; les
avertissements TIFF de Leptonica sont consignés. Pas qualification générale des
formats ni benchmark terrain/FR-AR exhaustif. Activation PATH/LD_LIBRARY_PATH/
TESSDATA_PREFIX nécessaire dans chaque shell. OpenCV headless local du lot 61
inchangé, sans modification des dépendances projet ou du lock. Binaries, modèles,
sources et logs de compilation non ajoutés à Git. Aperçu redémarré avec le vrai
moteur sur `0.0.0.0:8000`, pas nouveau service de production.

**Mission réglementaire toujours partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
