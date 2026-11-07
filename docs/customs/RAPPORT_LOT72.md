# Rapport lot 72 — cloisonnement des corrections et annulations

7 novembre 2026 ; branche `arena/2cd4c91a-ocr-universal`.

Les deux routes de correction humaine et d'annulation vérifient maintenant le
rôle **et la visibilité du document**, avant lecture du résultat. Avec RBAC actif,
un opérateur hors périmètre ne peut plus utiliser ces handlers alors que la lecture
du même résultat lui est refusée.

[Politique et limites](CLOISONNEMENT_CORRECTIONS_CHAMPS.md),
[recette machine](RECETTE_LOT72.json).

## Réalisation

- Garde `_exige_job` après le contrôle opérateur et avant `store.load_result`
  dans PATCH champ et POST annulation. Pas nouveau rôle ou nouvelle permission.
- Hors périmètre : **403**, champ présent ou absent, résultat inchangé ; pas
  événement de correction/annulation réussie, pas de valeurs du champ dans le refus.
  Le refus documentaire reste audité avec ses métadonnées (acteur, route, IDs).
- Politique existante conservée : un dossier visible suffit pour un document
  partagé ; non classé régi par le rôle seul ; administrateur et jeton global
  préservent leurs accès. Lecteur/inconnu restent refusés par rôle/authentification.
- **Sans RBAC actif et sans jeton, accès ouvert historique conservé.** Ce correctif
  n'active pas la protection d'un poste non configuré et ne crée pas de propriété.
- Valeurs, statuts et historique des opérations autorisées inchangés. Pas recalcul
  qualité ajouté aux éditions, transaction générale ou refonte des annulations.

## Vérifications mesurées

- **44 nouveaux cas**, sélection cloisonnement/RBAC **120 réussis**, zéro
  échec/ignoré, 1 avertissement, **4,45 s console**, JUnit 3,579 s.
- Dossiers et rattachements temporaires réels, registre synthétique et TestClient :
  confirmations/corrections/statuts/annulations, visibilité exclusive/partagée/
  non classée, contrôles de rôle, administrateur, jeton global et mode sans RBAC.
- Garde avant lecture éprouvée en rendant `load_result` interdit dans le test ;
  empreinte du résultat conservée lors des refus. Une vraie correction autorisée
  préalable crée l'événement nécessaire pour tester l'annulation.
- Contre-épreuve : corps exacts des deux handlers du lot 71 réinjectés **en mémoire**
  dans les mêmes callables de l'application de test, sans décorateurs, pour garder
  les stores des fixtures et ne pas doubler les routes : **12 échecs attendus,
  32 réussis**, 44 cas, code 1, **6,23 s console**, JUnit 6,141 s. Aucun fichier du
  checkout ou processus de l'aperçu remplacé par le témoin.
- Documentaire historique : **2 160 réussis**, zéro échec/ignoré, 1 avertissement,
  **60,03 s**, 66 fichiers ; Ruff et **212 scénarios JSDOM documentaires** réussis.
  Quatre ponts et 74 exports existants, pas nouveau scénario métier attribué.
- **Complète : 3 540 réussis, 2 échecs, 1 ignoré, 1 avertissement, 351,22 s**,
  soit **3 543 cas**, JUnit 351,137 s, code **1**. Compteurs cohérents avec les
  vrais cas. Mêmes échecs Indra `test_indra_engine_availability` et
  `test_selection_prefers_native_when_present`, même ignoré
  `test_indra_engine_recognize` qu'au lot 71. **Suite complète non verte.**

Code **`1b0bf76768d40f9fbdb4c15652f6fcaa57828330`** poussé ;
[CI 42409835955](https://github.com/boa-crypto/ocr-universal/actions/runs/42409835955)
terminée **success**, révision et étapes confirmées via `gh` : **nouvelle étape
120 cloisonnement/RBAC**, puis 241 qualité/Baidu, 24 ingestion/PDF, 10 UI et
recette documentaire. Ces sélections se recouvrent ; pas total unique déduit de
leur addition. Pas suite OCR complète en CI ni JUnit distant téléchargé ; chiffres
locaux dans `/home/user/recettes-unocr/lot72` hors dépôt.

Aucune dépendance nouvelle. Aperçu redémarré sur `0.0.0.0:8000` avec le correctif ;
son registre RBAC reste absent, comme avant, sans nouvelle fermeture implicite.

## Limites et réception

Alignement de deux handlers, **pas audit exhaustif de tous les chemins d'accès
ou de rattachement**, politique nouvelle de propriété ou garantie en concurrence.
Documents non classés et documents partagés suivent la politique permissive décrite.
Pas protection automatique sans RBAC ni réduction du jeton d'environnement.

Pas preuve d'identité du champ `user` fourni au corps, journal WORM/signé,
transaction atomique audit/résultat, garantie générale anti-énumération ou refonte
du contenu des corrections. Les IDs de dossiers/jobs restent dans le journal de
refus. Pas validation humaine/fiscale, qualification de charge ou navigateur réel.
Limites qualité/Baidu précédentes inchangées ; Indra non réparé.

**26/27 empreintes historiques conformes**, même écart qu'aux lots 64–71 :
`data/referentiels.json` observé
`b4f12a1fb9873c191e6a120db2715b605f61864a6b7034ce8816150572533a7d`, attendu
`b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
Référentiels, quatre dossiers partagés modifiés, autres données exploratoires et
journaux préservés hors commit, sans restauration ou attribution certaine.

**0 nouvel original officiel, 0 article/code officiellement validé, 0 publication
active. Mission globale partielle, non recevable pour production fiscale.**
