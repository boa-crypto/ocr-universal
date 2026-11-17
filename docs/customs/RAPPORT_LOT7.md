# Avancement — lot 7 : sauvegarde et reprise de la quarantaine

**2026-11-06 — protection technique des octets, aucune validation réglementaire.**

## Livré

- Inclusion du registre et des lots `customs-quarantine` dans le mécanisme de
  sauvegarde UniOCR existant, avec option locale explicite
  `--include-customs-quarantine` sur `backup` et `restore`.
- Refus si la quarantaine serait omise par défaut ; les routes HTTP de sauvegarde
  legacy ne peuvent pas activer cette option. La revue stricte du lot 6 n’est
  pas contournée par une création/reprise via ces routes en mode ouvert.
- Répertoire de copies dédié `sauvegardes-quarantaine` par défaut, séparé des
  sauvegardes/purges HTTP habituelles ; permissions restreintes demandées pour
  le nouveau dossier et l’archive. Pas de chiffrement nouveau.
- Tous les fichiers de quarantaine sont copiés, y compris fichiers cachés et
  `.tmp`, pour ne pas réparer silencieusement un dossier interrompu. Symlinks
  et fichiers spéciaux refusés pour ce périmètre.
- Création exclusive des ZIP avec suffixe de collision ; vérification complète
  de l’archive avant annonce de réussite, y compris détection d’un écart entre
  les octets copiés et les empreintes relevées.
- Reprise avec vérification préalable, sans fusion ni écrasement de quarantaine
  préexistante, **même avec `--force`**, y compris depuis une archive ancienne.
  Fichiers de quarantaine recréés exclusivement, dossier demandé en mode 0700.
- PDF, transcriptions, sidecars, lots, rapports, registre et empreintes de manifestes
  conservés octet pour octet. Les lecteurs/rejeux des lots restaurés retrouvent
  leurs épingles et les marqueurs de non-validation restent inchangés.

[Commandes, procédure et limites](SAUVEGARDE_QUARANTAINE.md).
Aucun magasin réel sauvegardé/restauré lors de cette livraison : les exercices
sont effectués dans des répertoires temporaires isolés. Pas de création de compte,
registre de production, corpus fictif public ou modification des sources existantes.

## Qualification

**495 tests réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
459 cas de la sélection lot 6 + **18 nouveaux cas de quarantaine/sauvegarde** +
**18 tests de sauvegarde existants** ajoutés à la non-régression. Pas de résultat
annoncé pour la suite complète du dépôt.

```sh
python -m pytest tests/test_customs_backup.py tests/test_backup.py \
  tests/test_customs_review.py tests/test_customs_search.py \
  tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
  tests/test_customs_reference.py tests/test_customs_xlsx.py \
  tests/test_customs_comparison.py tests/test_corrections_routes.py \
  tests/test_referentiels.py tests/test_referentiels_base.py \
  tests/test_customs_connector.py tests/test_rbac.py tests/test_rbac_ecritures.py \
  tests/test_rbac_reprise.py -q
```

Nouveaux tests : reprise exacte des contenus avec relecture des épingles,
options explicites, refus de fusion même avec force, anciennes archives,
préparations incomplètes/fichiers cachés/tmp préservés, symlinks source et ZIP,
racine non répertoire, collisions de noms, modification de source induite pendant
la copie, corruption refusée avant extraction, garde HTTP et invocation CLI.
Les fixtures sont **NON OFFICIELLES** ; aucune authenticité documentaire n’est
attestée par leurs préfixes PDF minimaux.

Les comparaisons de reprise portent sur les octets, pas sur les mtime qui changent
lors de la recréation. Les instantanés des fichiers d’origine vérifient aussi leur
absence de modification. La compatibilité des anciens appels directs au CLI,
sans le nouvel attribut d’option, est conservée et retestée.
Ruff `src tests`, identité des schémas et `git diff --check` contrôlés.

Les données historiques conservent leurs SHA256 :

- `data/reglementation/base.json` :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`
- `data/referentiels.json` :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`

## Limites et complétude inchangée

Suspendre les écritures pendant la sauvegarde/reprise. Pas de transaction globale
sur le corpus, de garantie de panne électrique/fsync, d’exactly-once, de WORM ou
contre un écrivain hostile. Un échec peut laisser une archive ou une reprise
partielle à inspecter, sans effacement automatique. Reprendre vers **data/logs
neufs**, service arrêté : les autres fichiers conservent le comportement legacy.
Les ACL, mtime et propriétés système complètes ne sont pas promises identiques.
La rétention, la protection des supports et les exercices sur données réelles
restent à qualifier dans le déploiement.

Une archive peut préserver un lot incohérent comme tel : intégrité de la copie
n’est pas validation du lot. Les contrôles métier doivent être relancés après
reprise ; aucune règle applicable, date d’effet ou classification n’est choisie.

**0 nouveau document officiel acquis, 0 article/code national officiel validé,
0 publication active.** La prévisualisation a été redémarrée avec le code courant : interface `/` → 200,
revue sans compte `/api/v1/customs-review/lots` → 403. Les empreintes ont été
recontrôlées après redémarrage ; aucune sauvegarde du magasin réel n’a été créée.

Les deux calculs legacy non sourcés restent bloqués.
Le StarterPack, le corpus original/modificatif exhaustif, sa chronologie, le tarif
national courant et ses sources fiscales restent manquants. La validation humaine,
la publication, la gouvernance juridique, l’administration graphique intégrée et
les fonctions de classification non livrées restent nécessaires avant usage réel.
