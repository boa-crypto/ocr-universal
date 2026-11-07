# Rapport lot 66 — suppression de la confiance Baidu inventée

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

La constante **0,95** n'est plus attribuée aux mots Baidu sans score fournisseur.
Une valeur numérique finie de `probability.average` entre 0 et 1 est conservée
comme **score déclaré non calibré**. Sans valeur exploitable : zéro conservateur,
pas probabilité nulle mesurée. Texte conservé et revue humaine non neutralisée.

[Politique, provenance et limites](SCORES_BAIDU_SANS_VALEUR_INVENTEE.md),
[recette machine](RECETTE_LOT66.json).

## Réalisations et vérifications

- Pas coercition des chaînes/booléens, NaN/Inf ou valeurs hors bornes. Une valeur
  explicitement déclarée 0,95 reste possible ; c'est la constante inventée qui
  disparaît. La moyenne inclut tous les éléments, même absents/invalides à zéro.
- Compteurs `reported` / `missing` / `invalid` et politique non calibrée dans
  `EngineOutput.raw`. Pas corps fournisseur, texte ou secret dans ces compteurs.
- Un score inconnu ne fait plus passer Baidu devant un concurrent noté dans le
  cas testé. Le pipeline conserve le zéro dans mots/run/qualité et signale la
  page à revoir. Pas nouvelle validation automatique des valeurs ou du classement.
- **30 nouveaux cas**, sélection Baidu **90 réussis, 0 échec, 0 ignoré, 2,64 s**.
  Les 60 tests de confidentialité/transport existants restent réussis. Réponses
  HTTP et mots synthétiques uniquement, pas reconnaissance distante réelle.
- Contre-épreuve : adaptateur exact du lot 65 chargé dans un processus séparé,
  sans remplacer les fichiers du checkout : **30/30 cas échouent**, code 1
  attendu, 4,63 s. Le témoin négatif ne fait pas partie du bilan positif de CI.
- Sélection documentaire historique : **2 160 réussis, 0 échec, 0 ignoré,
  1 avertissement, 56,15 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM** réussis.
  Quatre ponts et 74 exports existants, pas nouveau scénario métier attribué.
- **Complète : 3 343 réussis, 2 échecs, 1 ignoré, 1 avertissement, 353,43 s**,
  soit **3 346 tests**, code **1**. Durée JUnit 353,346 s. Compteurs cohérents
  avec les cas réels, suite complète non verte. Deux échecs exactement identiques
  au lot 65, liés à Indra absent ; seul ignoré : `test_indra_engine_recognize`.

## CI et environnement

Code **`13303354`**, run
**[42400091694](https://github.com/boa-crypto/ocr-universal/actions/runs/42400091694)**
terminé **success**, révision et étapes confirmées via `gh` : 90 Baidu hors réseau,
24 ingestion/PDF, 8 UI, puis sélection documentaire. Ubuntu 24.04 / Python 3.11 /
Node 24. **Pas suite OCR complète en CI**, pas JUnit distant téléchargé ; détails
chiffrés mesurés localement.

Aucune nouvelle dépendance, endpoint, option fournisseur ou configuration de clés.
Transport du lot 65 conservé ; Tesseract local, OpenCV headless et verrou PDFium
inchangés. Aperçu redémarré avec le correctif sur `0.0.0.0:8000`.
Artefacts : `/home/user/recettes-unocr/lot66`.

## Limites explicites

Le `Word` existant exige un nombre : **le zéro de repli ne distingue pas un score
absent d'un score réellement nul dans les résultats persistés**. Les compteurs
`raw` sont disponibles sur la sortie de l'adaptateur mais **ne sont pas persistés
par le pipeline actuel**. Pas nouvelle UI de provenance ou schéma optionnel.
Le signalement de faible confiance est conservateur, pas une mesure d'erreur.

Un score déclaré par le fournisseur n'est ni une probabilité calibrée, ni une
validation humaine ou juridique. Les scores des différents moteurs ne deviennent
pas automatiquement comparables. Pas mesure FR/AR réelle, test de charge ou
connexion fournisseur qualifiée. La présence/sémantique du champ de score chez
un compte réel n'a pas été vérifiée. La géométrie approximative préexistante en
absence de `location` reste inchangée et non qualifiée.

L'exposition résiduelle des paramètres OAuth en query et les risques de traces
externes du lot 65 restent présents. Aucun appel Baidu réel ni contournement de
l'allowlist réseau. Indra reste absent, sans moteur substitué ou test assoupli.

## Intégrité et mission

**26/27 empreintes historiques conformes**, même écart partagé qu'aux lots 64/65 :
`data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, référence
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiel, quatre dossiers historiques déjà modifiés, journaux et données
exploratoires préservés hors commit, sans restauration pour forcer la conformité.
Pas certification d'intégrité complète du magasin.

**Mission réglementaire toujours partielle : 0 nouvel original officiel acquis,
0 article/code national officiellement validé, 0 publication active.**
