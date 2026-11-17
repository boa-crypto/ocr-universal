# Avancement — lot 6 : API de revue administrative, lecture seule

**2026-11-06 — revue de quarantaine, pas validation juridique ou publication.**

**Suite :** [lot 7 — sauvegarde/reprise locale explicite](RAPPORT_LOT7.md).
Les résultats ci-dessous conservent l’état historique du lot 6.

## Livré

- Routes GET intégrées à l’API FastAPI UniOCR existante, sous
  `/api/v1/customs-review` : liste de lots inscrits, contrôle/rejeu, recherche FR/AR,
  comparaison de deux lots de même type. Réutilisation des services lots 1–5.
- Autorisation renforcée : RBAC actif, administrateur nominatif (pas le jeton
  d’environnement) et nom explicitement habilité dans le registre serveur.
  Le mode ouvert legacy ne donne aucun accès à ces routes.
- Registre déclaratif côté serveur avec IDs/dossiers simples, type de lot et
  SHA256 attendu du manifeste. Aucun chemin fourni par l’appel HTTP ; pas de
  découverte automatique de dossiers. Contrôle de l’épingle avant traitement et
  contre le manifeste effectivement consommé par le lecteur/rejeu.
- Schéma `RegistreRevue` ; validation stricte, limite de 1 Mio/64 lots/64 réviseurs,
  doublons, traversées et liens symboliques directs refusés.
- Audit existant pour opérations/refus, sans jetons, requêtes de recherche ou
  textes dans les événements spécifiques de revue. Réponses métier non cachables,
  erreurs génériques sans chemins internes.

[Configuration et contrat HTTP détaillés](API_REVUE.md).
Aucune dépendance, application autonome ou UI dupliquée ajoutée. Aucun POST/PUT/
PATCH/DELETE de revue, aucun import HTTP, endpoint `validate`, PDF brut ou écriture
sur les lots. Aucun compte ni registre de production créé automatiquement.

## Limites de sécurité et réglementaires

L’habilitation est un droit de lecture, pas une capacité à attester la loi.
Le RBAC local reste fondé sur des jetons porteurs et sa gouvernance doit être
sécurisée. La liste explicite de réviseurs ne protège pas d’un administrateur
système ou d’un compte habilité compromis. Les routes legacy ne sont pas
prétendues globalement durcies par ce lot.

Le registre ancre un instantané local, pas une authenticité officielle ni un
horodatage certifié. L’audit existant est best-effort, non WORM ; la présente
API n’est pas un workflow de validation humaine avec historique inviolable.
Les sources et transcriptions restent non vérifiées ; aucune date d’effet,
abrogation ou classification applicable n’est déduite.

**0 document officiel nouvellement acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, corpus original/modificatif exhaustif,
chronologie et export national courant avec fiscalité restent manquants.
Le dossier `customs-quarantine` n’est pas inclus dans la liste actuelle de
`backup.py` : sa sauvegarde/reprise reste à intégrer/qualifier, avec copie protégée
indépendante en attendant. Les tests de reprise RBAC ne valident pas cette couverture.
Les API publiques de référentiels publiés, l’administration graphique intégrée,
la validation/publication habilitée, la classification IA et les autres fonctions
réglementaires non livrées précédemment restent à construire.

## Qualification technique

**459 tests réussis, 1 avertissement Starlette/httpx**, sous data/logs isolés :
341 cas de la sélection lot 5 + **42 nouveaux cas de revue** + **76 cas RBAC**
existants ajoutés à la sélection de non-régression. Pas de suite complète annoncée.

```sh
python -m pytest tests/test_customs_review.py tests/test_customs_search.py \
  tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
  tests/test_customs_reference.py tests/test_customs_xlsx.py \
  tests/test_customs_comparison.py tests/test_corrections_routes.py \
  tests/test_referentiels.py tests/test_referentiels_base.py \
  tests/test_customs_connector.py tests/test_rbac.py tests/test_rbac_ecritures.py \
  tests/test_rbac_reprise.py -q
```

Les tests de revue utilisent **le vrai middleware de l’application**, pas une
substitution de la dépendance d’authentification. Cas : succès administrateur
habilité, refus en mode ouvert, jeton inconnu/absent, lecteur, faux en-têtes de
rôle, passe-partout environnement, administrateur non habilité, recherche/diff,
registres absents/incohérents/symboliques, épingle différente, sources corrompues,
changement induit de manifeste entre précontrôle et rejeu, paramètres invalides,
types incompatibles, absence d’écritures et audit sans secret ni texte recherché.
Les fixtures sont temporaires et **NON OFFICIELLES** ; pas de corpus fictif publié.

Un premier passage de la sélection élargie a révélé trois échecs d’isolation dans
`test_rbac_reprise.py` : sa fixture écrivait sous `tmp_path`, mais `Config.data_dir`
utilisait le `UNOCR_DATA_DIR` isolé hérité du processus. La fixture fixe désormais
ses propres variables data/logs par test. Les trois cas passent ensuite ; pas de
modification du code de sauvegarde pour masquer l’écart. Le répertoire concerné
était temporaire, pas le magasin réel.

Ruff `src tests`, identité des schémas et `git diff --check` contrôlés. Empreintes
historiques conservées :

- `data/reglementation/base.json` :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`
- `data/referentiels.json` :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`

La prévisualisation a été redémarrée avec le code courant : GET `/` → 200 et
GET `/api/v1/customs-review/lots` sans compte → **403**, garde réellement chargée.
Aucun RBAC ou registre de revue n’a été créé ; les empreintes ci-dessus ont été
recontrôlées après redémarrage.

Les deux calculs legacy non sourcés restent bloqués. Les fonctions de revue ne
sont branchées sur aucun calcul douanier réel, activation de version ou décision
marchandise/transit/facturation. La prochaine intégration devra conserver ces
frontières et réutiliser les composants/permissions existants, sans simuler une
validation réglementaire en l’absence des sources et de la revue humaine.
