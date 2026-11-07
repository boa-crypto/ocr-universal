# Rapport lot 70 — pages sans sortie incluses dans la qualité et la revue

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

La limite constatée au lot 69 est corrigée : une page sans mots, non déclarée
vide et sans texte après `str.strip()` contribue désormais **zéro** aux moyennes
moteur/globale et figure dans `pages_low_confidence`, même au seuil de revue zéro.
L'anomalie `OCR_FAILED` reste présente. Ce zéro est une convention conservatrice,
pas un score fournisseur ou une probabilité mesurée.

[Contrat et limites](PAGES_SANS_SORTIE_DANS_QUALITE.md),
[recette machine](RECETTE_LOT70.json).

## Réalisation

- Les pages sans sortie ne disparaissent plus du dénominateur d'un document mixte.
  Une page reconnue à 1,0 + une page échouée + une page déclarée vide donnent 0,5,
  pas 1,0. La page déclarée vide reste exclue, selon le drapeau existant.
- Une contribution par page, pas par run : plusieurs moteurs échoués ne multiplient
  pas le poids d'une même page. Aucun mot ou run n'est inventé pour le signalement.
- Un texte constitué seulement d'espaces reconnus par `str.strip()` ne reçoit plus
  le repli historique 0,95. Pas analyse sémantique du texte ou de la langue.
- Rapport conservé dans stockage, API et export JSON existants. Pas nouveau schéma,
  file visuelle, règle d'autorisation ou validation juridique automatique.
- Test d'intégration géométrique du lot 69 renforcé : la page Baidu échouée sans
  sortie figure maintenant dans la liste, en conservant l'anomalie d'erreur.

## Vérifications mesurées

- **27 nouveaux tests**, sélection qualité/Baidu **214 réussis**, zéro
  échec/ignoré, 1 avertissement, **3,51 s console**, JUnit 2,358 s.
- Pages isolées/mixtes, espaces Unicode, blancs, seuils 0/0,7/1, runs multiples,
  non-mutation et chemins reconnus préexistants. Une vraie image PNG passe par le
  pipeline avec un registre volontairement vide dans le harnais : aucune fausse
  reconnaissance, aucune absence générale de Tesseract revendiquée.
- Stockage temporaire et GET résultat/export via TestClient, relecture modèle et
  export JSON réels : moyennes et liste corrigées sont conservées.
- Contre-épreuve sur le calcul qualité exact du lot 69, chargé dans un processus
  séparé et substitué aussi au point d'appel du pipeline : **24 échecs attendus,
  3 réussis**, 27 cas, code 1, **4,44 s console**, JUnit 3,052 s. Checkout non
  remplacé. Les trois cas inchangés couvrent blanc seul, document vide et non-mutation.
- Documentaire historique : **2 160 réussis**, zéro échec/ignoré, 1 avertissement,
  **72,07 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM documentaires** réussis.
  Quatre ponts et 74 exports existants, pas nouveau scénario métier attribué.
- **Complète : 3 469 réussis, 2 échecs, 1 ignoré, 1 avertissement, 429,96 s**,
  soit **3 472 cas**, JUnit 429,861 s, code **1**. Compteurs cohérents avec les
  vrais cas. Mêmes échecs Indra `test_indra_engine_availability` et
  `test_selection_prefers_native_when_present`, même ignoré
  `test_indra_engine_recognize` qu'au lot 69. **Suite complète non verte.**

Code **`2f9805be7ebdd01080639dbeefd989e3919d0360`** poussé ;
[CI 42403664023](https://github.com/boa-crypto/ocr-universal/actions/runs/42403664023)
terminée **success**, révision et étapes confirmées via `gh` : 214 qualité/Baidu,
24 ingestion/PDF, 10 UI dont les 47 scénarios de provenance du lot 68, puis documentaire.
Pas suite OCR complète en CI ni JUnit distant téléchargé ; chiffres détaillés locaux
conservés dans `/home/user/recettes-unocr/lot70` hors dépôt.

Aucune dépendance nouvelle. Aperçu redémarré sur `0.0.0.0:8000` avec le correctif.

## Limites et réception

Les moyennes restent des conventions par page, pas une précision OCR mesurée.
Mots présents, facteur de qualité, champs, statuts et repli historique **0,95 pour
texte non blanc sans mots** restent inchangés, sans requalification en score mesuré.
Le contrôle ne traite pas toutes les incohérences texte/mots/drapeaux ni les champs
de confiance nulle. Le drapeau `blank` n'est pas une attestation de page vide.

Aucune migration/requalification des anciens résultats ou exports ; un ancien
rapport réutilisé par dédoublonnage n'est pas automatiquement recalculé. La liste
signale la revue, sans prouver son exécution ni constituer un verrou fiscal.
Pas modification des états de job ou garantie générale du processus humain.

Localisation Baidu absente toujours approximative, risques OAuth query et autres
limites de transport inchangés. Pas appel fournisseur, précision FR/AR, charge ou
navigateur réel qualifiés. Indra n'est ni substitué ni annoncé réparé.

**26/27 empreintes historiques conformes**, même écart qu'aux lots 64–69 :
`data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiels, quatre dossiers partagés modifiés, autres données exploratoires et
journaux préservés hors commit, sans restauration ou attribution certaine.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
