# Avancement — lot 15 : audit obligatoire des succès de revue

**2026-11-06 — reprise et qualification du travail interrompu, aucun corpus publié.**

## Reprise et périmètre

À la reprise, le dépôt contenait une implémentation non commitée de l’audit
obligatoire, ses tests et sa documentation. Ces modifications ont été conservées,
relues et qualifiées avant toute nouvelle fonction d’export. L’export JSON annoncé
au début de la reprise n’est **pas livré dans ce lot**.

Inspection de `logging_setup`, du raccordement API et du routeur de revue :
l’audit legacy avale les erreurs d’écriture. Ce comportement reste inchangé pour
ses autres utilisateurs ; un writer strict distinct protège désormais la remise
des succès documentaires de `/api/v1/customs-review`.

## Livré

- Événement JSONL écrit et `fsync` local réussi avant toute réponse métier réussie
  du routeur ; réponse sérialisée avant enregistrement du succès.
- Échec d’écriture/synchronisation : **503 `audit_revue_indisponible`**, sans
  résultat documentaire, avec `Cache-Control: no-store` et erreur générique.
- Succès : acteur, opération, IDs des lots et manifestes épinglés utilisés, sans
  jeton, requête de recherche, ID/numéro d’article, code tarifaire ou texte métier.
- Ajout sans troncature ; fichier régulier, absence de symlink direct/lien multiple,
  fin de journal complète, taille d’événement bornée et écriture contrôlée.
  Permissions restrictives demandées pour les créations ; aucune modification
  automatique des permissions ou réparation d’un journal existant.
- Refus d’accès/lot/paramètres préservés même si leur audit échoue. Authentification,
  refus et middleware ne sont pas annoncés exhaustivement tracés.
- Message UI 503 adapté au registre ou à l’audit indisponible, avec effacement
  des données/actions ; coque service worker version 47.

[Guide, procédure opérateur et limites](AUDIT_REVUE.md).
Pas de changement du corpus ou d’habilitation de validation juridique.

## Qualification

**781 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
754 cas du lot 14 + **27 nouveaux cas** d’audit obligatoire.
Pas de suite complète du dépôt annoncée.

```sh
python -m pytest tests/test_customs_audit_required.py tests/test_customs_article_detail.py \
 tests/test_customs_tariff_tree.py tests/test_customs_coverage.py tests/test_customs_tariff_detail.py \
 tests/test_customs_history.py tests/test_customs_backup.py tests/test_backup.py \
 tests/test_customs_review.py tests/test_customs_review_ui.py tests/test_customs_search.py \
 tests/test_customs_legal_comparison.py tests/test_customs_legal.py tests/test_customs_reference.py \
 tests/test_customs_xlsx.py tests/test_customs_comparison.py tests/test_corrections_routes.py \
 tests/test_referentiels.py tests/test_referentiels_base.py tests/test_customs_connector.py \
 tests/test_rbac.py tests/test_rbac_ecritures.py tests/test_rbac_reprise.py \
 tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

Cas nouveaux : préfixe du journal conservé et fsync appelé, concurrence locale,
permissions de création, refus de symlinks/liens physiques/FIFO/répertoire/fin
partielle, pannes open/write/fsync, écriture partielle conservée et refusée ensuite,
événements invalides/trop volumineux refusés sans création. Les neuf lectures de
revue refusent un succès si l’audit échoue ; les épingles et exclusions de données
sensibles sont testées, les refus conservent leur statut, une réponse non
sérialisable n’enregistre pas un succès. Instantanés des lots inchangés.

**37 scénarios UI JSDOM réussis** : 36 précédents + panne d’audit 503 qui efface
texte/actions avec message générique. Le parcours HTTP/API réel isolé existant
passe aussi avec le writer strict. Fixtures et comptes NON OFFICIELS temporaires,
aucun compte/registre/lot de production créé.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation redémarrée :
coque/module/service worker 200 avec hôte de prévisualisation ; revue anonyme 403.
Aucun exercice de panne ou d’écriture stricte sur le journal réel. Empreintes
historiques inchangées après redémarrage :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Le verrou ne couvre que le writer strict du processus, pas les writers legacy,
autres processus ou rotations. Lire la fin exige les droits de lecture et d’ajout.
Pas de validation rétroactive du JSONL, WORM, signature, horodatage de confiance,
transaction lot/journal/réseau, exactly-once ou accusé de livraison. Un échec tardif
peut laisser une entrée déjà écrite ; ne pas tronquer ou réparer automatiquement.
Aucun export JSON documentaire n’a été ajouté par cette reprise.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, corpus original/modificatif exhaustif,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués. L’audit technique ne constitue
ni validation humaine ni autorisation d’usage réglementaire réel.
