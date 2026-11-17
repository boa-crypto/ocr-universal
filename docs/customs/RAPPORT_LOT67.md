# Rapport lot 67 — provenance des scores conservée dans les résultats

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Les compteurs Baidu du lot 66 ne s'arrêtent plus à la sortie interne du moteur :
ils sont conservés, après validation, dans les runs du résultat enregistré,
l'API de résultat et l'export JSON. Cela distingue **au niveau des compteurs du
run** un score déclaré nul d'un score absent ou invalide. Pas d'attribution de
statut individuel à chaque mot, ni de nouvelle validation automatique.

[Contrat, compatibilité et limites](PROVENANCE_SCORES_PERSISTEE.md),
[recette machine](RECETTE_LOT67.json).

## Réalisations

- Champ facultatif typé `EngineRun.confidence_provenance` : politique connue,
  `calibrated: false` et compteurs entiers stricts ; champs supplémentaires refusés.
- Association contrôlée au run Baidu réussi : nombre de mots/moyenne compatibles,
  somme des compteurs égale au nombre de mots, bornes et plafond de moyenne.
- Projection des seuls compteurs validés : **pas copie du raw fournisseur**.
  Métadonnée invalide ou indisponible : champ omis, aucune provenance inventée,
  aucune erreur de validation contenant le payload journalisée par cette projection.
- Anciens JSON lisibles, forme des runs sans provenance inchangée. Pas réécriture
  des anciens jobs/exports ni requalification rétroactive de leurs anciens scores.
- Stockage temporaire réel, relecture modèle, GET résultat et téléchargement JSON
  testés ; API via TestClient, transport fournisseur doublé, aucun Baidu réel.
- Les mots/runs de score inconnu restent à zéro et la page reste à revoir.

## Vérifications mesurées

- **43 nouveaux cas**, sélection provenance/Baidu : **133 réussis**, zéro échec
  ou ignoré, 1 avertissement, **2,69 s console** (JUnit 1,817 s).
- Contre-épreuve sur le pipeline exact du lot 66, importé séparément sans modifier
  les fichiers du checkout : les **3 tests d'intégration/persistance échouent comme
  attendu**, code 1, 40 désélectionnés, 2,03 s. Les tests du nouveau modèle ne sont
  pas inclus dans cette contre-épreuve : elle cible la perte des compteurs dans
  l'ancien pipeline, pas l'absence de classes nouvelles dans l'ancien code.
- Sélection documentaire historique : **2 160 réussis**, zéro échec/ignoré,
  1 avertissement, **59,26 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM** réussis.
  Quatre ponts et 74 exports existants, aucun nouveau scénario métier attribué.
- **Suite complète : 3 386 réussis, 2 échecs, 1 ignoré, 1 avertissement,
  354,33 s**, soit **3 389 cas**, code **1**. JUnit 354,234 s, compteurs cohérents
  avec les vrais cas. Même paire d'échecs Indra et même ignoré qu'au lot 66 :
  `test_indra_engine_availability`, `test_selection_prefers_native_when_present`,
  ignoré `test_indra_engine_recognize`. **Suite complète non verte.**

Code **`628db7ad46ddae8c8dbf566029ce8148557c3a1c`** poussé ;
[CI 42401056646](https://github.com/boa-crypto/ocr-universal/actions/runs/42401056646)
terminée **success**, révision et étapes confirmées via `gh` : sélection Baidu/
provenance, 24 ingestion/PDF, 8 UI puis recette documentaire. Pas suite OCR
complète en CI ni JUnit distant téléchargé ; chiffres détaillés mesurés localement.

Aucune dépendance ou option fournisseur nouvelle. Aperçu redémarré sur
`0.0.0.0:8000` avec le code livré. Artefacts hors dépôt :
`/home/user/recettes-unocr/lot67`.

## Limites et mission

Compteurs agrégés par run, pas provenance par mot ni certification de l'origine
fournisseur. L'absence du champ signifie **indisponible**, jamais « tout déclaré ».
Les scores déclarés restent non calibrés et pas automatiquement comparables entre
moteurs ; les scores historiques ne sont pas recalculés. Pas nouvelle UI de
provenance, acquisition officielle, précision FR/AR mesurée, API distante qualifiée,
signature, preuve d'authenticité ou modification des règles de validation humaine.
La géométrie Baidu approximative et les risques OAuth query du lot 65 restent
inchangés. Indra n'est ni remplacé artificiellement ni annoncé réparé.

**26/27 empreintes historiques conformes**, même écart partagé qu'aux lots 64–66 :
`data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiels, quatre dossiers partagés modifiés, autres données exploratoires et
journaux sont préservés hors commit, sans restauration ni attribution certaine.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
