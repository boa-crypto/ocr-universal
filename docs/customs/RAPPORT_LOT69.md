# Rapport lot 69 — refus des localisations Baidu fournies incohérentes

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Les coordonnées Baidu **fournies** sont désormais contrôlées avant création des
mots : pas coercition de chaînes/booléens, valeur non finie, champ requis manquant,
boîte hors image, dimension nulle/négative ou aire calculée nulle.
**L'absence de `location` reste compatible avec la boîte pleine image historique,
approximative et non mesurée.** Pas correction générale de toute la géométrie OCR.

[Contrat, refus et limites](LOCALISATIONS_BAIDU_DECLAREES.md),
[recette machine](RECETTE_LOT69.json).

## Réalisation

- `location` présent doit être un objet avec quatre valeurs numériques finies et
  compatibles avec les dimensions de l'image envoyée. Une valeur présente mais
  vide/falsy n'est plus assimilée à une absence ; aucun champ omis n'est inventé.
- Bornes vérifiées avant conversion des entiers ; contrôle des extrémités et de
  l'aire effective après calcul flottant. Pas clipping ou réparation silencieuse.
- Champs supplémentaires ignorés sans copie dans les mots ou le résultat.
- Refus de toute cette sortie Baidu, sans mots/texte/provenance partiels, avec
  message constant `Baidu : localisation invalide`. Pas donnée distante interpolée.
- Coordonnées valides, bords exacts et fractions conservés ; politique des scores
  et provenance des sorties réussies inchangées. Autres moteurs et `BBox` général
  inchangés. Aucun nouveau paramètre ou endpoint fournisseur.

## Vérifications mesurées

- **54 nouveaux tests**, sélection Baidu/provenance **187 réussis**, zéro
  échec/ignoré, 1 avertissement, **2,86 s console**, JUnit 1,835 s.
  Entrées et réponses synthétiques, jamais localisation Baidu réelle mesurée.
- Contre-épreuve : adaptateur exact du lot 68 importé séparément, checkout non
  remplacé ; **47 cas exécutés, 41 échecs attendus, 6 réussis, 7 désélectionnés**,
  code 1, 1,67 s. Les 7 tests directs du nouveau helper sont exclus. Les écarts
  couvrent les refus et le diagnostic constant, pas 41 fuites de données alléguées.
- Intégration pipeline : run échoué conservé, aucun mot/texte partiel ni compteur
  de confiance inventé ; anomalie `OCR_FAILED` et moyenne globale nulle dans le
  cas isolé testé. **La liste `pages_low_confidence` reste vide pour cette page
  sans mots/texte** : couverture préexistante non corrigée, pas faux succès de revue.
- Documentaire historique : **2 160 réussis**, zéro échec/ignoré, 1 avertissement,
  **56,15 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM documentaires** réussis.
  Quatre ponts et 74 exports existants, aucun nouveau scénario métier attribué.
- **Complète : 3 442 réussis, 2 échecs, 1 ignoré, 1 avertissement, 363,12 s**,
  soit **3 445 cas**, JUnit 363,044 s, code **1**. Compteurs cohérents avec les
  cas réels. Mêmes échecs Indra `test_indra_engine_availability` et
  `test_selection_prefers_native_when_present`, même ignoré
  `test_indra_engine_recognize` qu'au lot 68. **Suite complète non verte.**

Code **`09045399c1a028a09463f142a4fddea26d068de4`** poussé ;
[CI 42402932739](https://github.com/boa-crypto/ocr-universal/actions/runs/42402932739)
terminée **success**, révision et étapes confirmées via `gh` : 187 Baidu/provenance,
24 ingestion/PDF, 10 UI dont les 47 scénarios provenance du lot 68, puis documentaire.
Pas suite OCR complète en CI ni JUnit distant téléchargé ; chiffres détaillés locaux
conservés dans `/home/user/recettes-unocr/lot69` hors dépôt.

Aucune dépendance nouvelle. Aperçu redémarré sur `0.0.0.0:8000` avec le correctif.

## Limites et réception

Validation dans les pixels de l'image envoyée, éventuellement prétraitée, pas
reprojection PDF d'origine, correction de rotation, fidélité ou précision de
localisation attestée. Aucun nouvel indicateur de provenance géométrique persisté.
Sans `location`, les boîtes restent approximatives. Aucun ancien résultat migré.
Pas verrou global sur `BBox`, calibration ou validation humaine ajoutée.

Les pages échouées sans mots/texte peuvent encore être exclues des moyennes d'un
document mixte et de `pages_low_confidence`, même avec une anomalie d'erreur :
ce lot ne qualifie pas cette agrégation ou un processus de revue basé sur cette
seule liste. Risques OAuth query et limites du transport inchangés. Aucun appel
Baidu réel, qualification FR/AR, navigateur réel ou test de charge revendiqué.
Indra n'est ni installé artificiellement ni annoncé réparé.

**26/27 empreintes historiques conformes**, même écart qu'aux lots 64–68 :
`data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiels, quatre dossiers partagés modifiés, autres données exploratoires et
journaux préservés hors commit, sans restauration ou attribution certaine.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
