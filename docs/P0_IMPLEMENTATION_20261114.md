# P0 — implémentation et revalidation (2026-11-14)

Branche `arena/a4e8bc76-ocr-universal`, base `1ea71dad`.
Cette note fait suite au bilan `docs/BILAN_RESTE_A_FAIRE_20261114.md` ; elle ne réécrit pas le bilan, elle constate ce qui a été codé et vérifié après la demande « continues ».

## 1. Cloisonnement RBAC (P0.1)

Les routes métier suivantes appliquent désormais le périmètre dossier avant lecture, écriture, suppression et changement de dossier :

- frais, factures, justificatifs ;
- déclarations, liquidations ;
- enlèvements terminal et actions de workflow terminal ;
- expéditions ;
- livraisons, conteneurs, connaissements BL/BAD ;
- workflow opérationnel ;
- contrôle documentaire et résolutions.

Helpers partagés dans `src/unocr/routes/dependencies.py` : `_exige_dossier`, `_exige_objet_dossier`, `_filtre_dossiers`. Les listes sont filtrées par dossier visible ; les créations et déplacements vers un dossier hors périmètre renvoient 403. La recherche globale (`/api/search/global`) lit les BL/conteneurs depuis le magasin métier et filtre aussi par périmètre.

## 2. Workflow opérationnel persistant (P0.2)

Nouveau moteur `src/unocr/workflow.py`, stocké dans `BusinessStore` (`metier.sqlite3`, collection `workflow_operationnel`), à raison d'un workflow par dossier.

- étapes : `creation → scan → ocr → verification → douane → port → transport → cloture`, plus `bloque` ;
- création idempotente, template unique `default` ;
- transitions avant/arrière contrôlées, rôle requis, motif obligatoire pour blocage/déblocage/retour arrière/clôture ;
- version optimiste (`expected_version`) : une version obsolète renvoie 409 ;
- historique append-only et audits `workflow_cree`, `workflow_transition`, `workflow_transition_refusee` ;
- `cloture` est terminale.

Routes réécrites dans `src/unocr/routes/workflow.py` : `/api/workflow/template`, `/create`, `/{dossier_id}`, `/{dossier_id}/transition`, `/{dossier_id}/historique`. Les anciens chemins `/api/workflow/workflow/...` restent servis en alias hors schéma pour compatibilité.

Divergence assumée : ce moteur n'utilise pas les modèles déclaratifs `WorkflowStage.etape_N_*` / `WorkflowInstance` de `models.py`, qui ne sont pas branchés à un magasin persistant. Il ne remplace pas non plus les workflows RBAC personnalisés (`/api/rbac/workflows`).

## 3. Résolutions du contrôle documentaire (P0.3)

Nouveau module `src/unocr/controle_resolutions.py` :

- acceptation de risque persistante, liée à une empreinte SHA-256 canonique du constat (type, règle, champ, gravité, documents triés, valeurs) ;
- si la source change, l'empreinte change : l'ancienne acceptation ne s'applique plus et l'anomalie redevient active ;
- `corriger` ne marque pas résolue une anomalie encore détectée ; il confirme seulement sa disparition après nouveau contrôle ;
- révocation tracée ;
- `analyser_dossier_complet` réapplique les résolutions et expose `total_detectees`, `total_anomalies` (actives), `anomalies_acceptees`, `anomalies_bloquantes`, `peut_continuer`.

Routes `src/unocr/routes/controle_doc.py` : analyse, règles, anomalies, résolution/révocation, statut. L'acteur vient de la session, pas du corps de requête. Alias de présentation `niveau`, `document`, `resolue` ajoutés pour l'interface ; le compteur d'anomalies du dossier ne compte plus les acceptations de risque.

## 4. Persistance maritime et préconditions

Les modules autrefois stockés dans `request.app.state` sont migrés vers `BusinessStore` :

- `transport` : transporteurs, camions, livraisons ;
- `conteneurs` ;
- `connaissements` : BL et BAD.

Préconditions ajoutées (409/422) :

- un BAD référence un BL existant du même dossier ;
- suppression/changement d'un BL référencé par BAD, expédition ou terminal refusée ;
- suppression/changement d'un conteneur utilisé par un enlèvement terminal refusée ;
- camion rattaché à un transporteur existant ; suppression d'un transporteur/camion utilisé refusée ;
- workflow livraison : `demarrer`, `arriver`, `confirmer` avec transitions contrôlées, preuve signée obligatoire, champs de workflow non contournables par PUT ; après confirmation, seules les observations restent modifiables.

## 5. Tests et validation

Nouveaux tests :

- `tests/test_p0_securite_metier.py` : cloisonnement inter-dossiers, listes filtrées, déplacements refusés, workflow persistant/rôles/motif/version/clôture, acceptation de risque persistante et invalidée si la source change ;
- `tests/test_maritime_persistence.py` : persistance conteneurs/BL/BAD/livraisons/transporteurs/camions et préconditions.

`tests/conftest.py` inclut désormais les routeurs maritime/workflow/contrôle dans `client_factory`.

Résultats du 2026-11-14 :

```text
ruff check src tests benchmarks   → All checks passed!
pytest -q                         → 4492 passed, 15 failed, 13 skipped (258 s)
tests ciblés métier/RBAC          → 73 passed
npm run ui:product (Chromium)     → 408 routes, 4 viewports, 32 captures, 0 erreur JS, 0 mutation
```

Les 15 échecs pytest sont les mêmes échecs environnementaux que le bilan initial : Tesseract/Poppler absents, modèles Indra non téléchargés en mode hors ligne. Ils ne concernent pas les modules métier modifiés.

## 6. Ce qui reste

Le P0 traité ici ne rend pas le produit « production ready » au sens fiscal/douanier. Restent notamment les chantiers P1/P2 du bilan : import bancaire réel, conversion multi-devises, mesure OCR terrain, intégrations douane effectives, corpus/quarantaine/publication habilitée, CI OCR avec binaires/modèles épinglés, Docker/config, verrou de dépendances et nettoyage des arteaux suivis.
