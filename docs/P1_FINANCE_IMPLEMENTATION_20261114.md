# P1 finance + fiabilisation — implémentation (2026-11-14)

Suite de `docs/P0_IMPLEMENTATION_20261114.md`. Cette passe ferme deux chantiers
P1 réalisables sans service externe (rapprochement bancaire, cohérence
multi-devises) et deux points P2 (configuration Docker, déclenchement CI).

## 1. Rapprochement bancaire réel

Nouveau module `src/unocr/finance.py` et routes sous `/api/frais` :

- import JSON `POST /banque/import` et CSV `POST /banque/import-csv` ;
- liste `GET /banque/operations` ;
- rapprochement automatique `POST /rapprochement/auto` sur opérations importées ;
- pointage manuel `POST /rapprochement/manuel` et annulation `POST /rapprochement/annuler`.

Les opérations sont persistées dans `BusinessStore` (`operation_bancaire`),
dédupliquées par identifiant externe ou empreinte stable. Le rapprochement
automatique ne lie qu'une correspondance unique (montant au centime, devise,
sens crédit/débit, référence, fenêtre de date) ; les ambiguïtés sont signalées,
pas arbitrées silencieusement. Chaque lien/annulation est audité.

Format d'import et règles détaillées : `docs/FINANCE_IMPORT_BANCAIRE.md`.

## 2. Totaux multi-devises sans conversion implicite

`GET /api/frais/dossier/{id}/resume` agrège par devise avec `Decimal` et arrondi
au centime. Une seule devise conserve les clés historiques ; plusieurs devises
renvoient `consolide=false`, des clés historiques à `null` et le détail
`par_devise` avec avertissement. Aucun taux hypothétique n'est réactivé.

L'interface dossier affiche un tableau par devise plutôt qu'un total trompeur.
Un écran lecture seule « Opérations bancaires » est ajouté (`#finance/banque`),
et la description du rapprochement ne présente plus l'absence d'import comme
une limite définitive.

## 3. Docker et CI

- `Dockerfile` copie explicitement `config/default.json` dans l'image ; un test
  garde cette copie et vérifie que l'ordre des moteurs chargé est bien celui du
  fichier (`native_pdf, indra, tesseract`), pas le repli Python.
- Les workflows `ci.yml` et `customs-review.yml` se déclenchent aussi sur
  `arena/**`, pour couvrir la branche courante au push.

## 4. Tests et validation

Nouveaux tests :

- `tests/test_finance_banque.py` : import/déduplication/CSV, rapprochement
  unique/ambigu/sans import, pointage manuel/annulation/incompatibilité,
  multi-devises non consolidé, arrondi décimal ;
- `tests/test_config_docker.py` : copie Docker et chargement de la config ;
- `tests/test_p0_securite_metier.py` étendu au cloisonnement banque/rapprochement.

Résultats du 2026-11-14 :

```text
ruff check src tests benchmarks   → All checks passed!
pytest -q                         → 4500 passed, 15 failed, 13 skipped (268 s)
tests ciblés finance/P0/maritime  → 32 passed
node --check (ecrans/navigation/dossiers) → OK
npm run ui:product (Chromium)     → 412 routes, 4 viewports, 32 captures, 0 erreur JS, 0 mutation
```

Les 15 échecs restent les échecs environnementaux OCR déjà documentés
(Tesseract/Poppler absents, modèles Indra hors ligne), pas des régressions des
modules modifiés.

## 5. Ce qui n'est pas fermé par cette passe

- OCR terrain : corpus réel annoté, Tesseract/langues et modèles Indra installés,
  mesure CER/WER et exactitude par champ.
- Connecteurs externes réels (ALCES/ERP/portail) : spécifications, comptes de
  test et transmission/reprise autorisées.
- Référentiels douaniers : corpus officiel FR/AR, tarif 10 chiffres, droit à
  date, validation habilitée, publication contrôlée.
- Consolidation de change : taux datés et sourcés, règles comptables d'avoirs et
  paiements partiels.
- Hygiène du dépôt et verrou de dépendances minimal par cible.
