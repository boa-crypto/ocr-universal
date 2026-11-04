# Fonctionnalités restantes — UniOCR

État au 2026-11-04, après la passe 2. Ce document est la liste de travail
priorisée ; il se déduit de [`MATRICE_ECRANS.md`](MATRICE_ECRANS.md), qui reste
la référence ligne à ligne.

**Chiffres du jour, sans arrondi complaisant** : 100 entrées de menu,
**52 conformes**, **48 partiels**, 0 absent, 0 non connecté, et
**plus aucun bandeau « pas encore d'écran dédié »** (contre 14 en début de
passe 2). Les 57 partiels sont désormais des écrans qui lisent des données
réelles mais n'ont pas encore été re-certifiés, ou dont les actions d'écriture
ne sont pas couvertes par un test.

---

## P0 — Sécurité et perte de données

| # | Tâche | Pourquoi | Où |
|---|---|---|---|
| P0-1 | Écrire `data/rbac.json` dans les environnements de production et couvrir le cas « rôle lecteur » | sur ce poste le RBAC est inactif : aucune preuve que les écrans respectent les droits | `src/unocr/routes/rbac*.py`, tests d'écran |
| P0-2 | Test d'écriture refusée (403) sur chaque famille d'écran | la sécurité serveur n'est vérifiée que sur les routes historiques | `tests/test_referentiels.py` + équivalents |
| P0-3 | Vérifier l'archivage/suppression des dossiers depuis les écrans | opération destructive : doit être confirmée et tracée | `#dossiers/*`, `POST /api/dossiers/{id}/archiver` |

## P1 — Dossiers, documents, OCR, contrôle, workflow

| # | Tâche | Constat |
|---|---|---|
| ✅ P1-1 | ~~Remplacer les 6 redirections « Gestion des dossiers »~~ | **fait en passe 2** : en cours / bloqués / clôturés = écrans dédiés (`web/ecrans.js`) ; tous / nouveau / clients = pages réellement existantes désormais reliées (fin du bandeau) |
| ✅ P1-2 | ~~Idem pour les 5 redirections « Mon espace de travail »~~ | **fait en passe 2** : mes tâches, en attente, mes alertes, dossiers récents = écrans dédiés ; à valider = page `#tab-validation` reliée |
| ✅ P1-3a | ~~Vue d'ensemble + Extraction OCR~~ | **fait en passe 3** : deux écrans dédiés sur `/api/jobs` ; actions Texte / Résultat / Relancer exercées par test |
| ✅ P1-3b | ~~Re-certifier les écrans Documents hérités~~ | **fait en passe 5** pour 5 écrans (boîte de réception, classification, archives, vérification, révision) : données + recherche + pagination + ouverture de dossier vérifiées ; **reste** résultat, qualité, profils, connecteurs, configuration (dépendent d'un document sélectionné ou exposent des écritures) |
| ✅ P1-4 | ~~Tester les actions de contrôle documentaire~~ | **fait en passe 4** : *Contrôler* et *Verdict* exécutés (200) ; reste la **résolution d'anomalie** avec justification, qui demande un motif |
| P1-5 | Historiser la validation OCR dans l'écran de révision | la route existe, l'écran hérité n'a pas été re-testé |

## P2 — Maritime, douane, enlèvement, finance

| # | Tâche | Constat |
|---|---|---|
| P2-1 | Alimenter `terminal` et `declarations` : sur ce poste les deux collections sont **vides**, donc sortie portuaire, contrôles et liquidation n'affichent que l'état vide | aucune donnée à afficher, comportement correct mais non démontrable en conditions réelles |
| P2-2 | Tester les parcours de livraison (démarrer → arriver → confirmer) de bout en bout | routes existantes, aucun test d'écran |
| ✅ P2-3 | ~~Tester le rapprochement automatique~~ | **fait en passe 4** : dialogue de paramètres (dossier + période), `POST` 200, verdict affiché. **Reste à faire** : l'import bancaire côté serveur (`frais.py` : `operations_bancaires = []`, TODO explicite) — sans lui le rapprochement ne peut rien rapprocher |
| ✅ P2-4 | ~~Remplacer les redirections « Rapports » (graphiques), « Référentiels » (profils, paramètres)~~ | **fait en passe 2** : graphiques → `#tab-reports`, profils → `#tab-profiles`, paramètres → `#tab-params-gen` ; plus aucun bandeau dans l'application |
| P2-5 | Découpler les écrans de référence des pages historiques : `#dossiers/tous` ouvre encore la page héritée `#tab-dossiers` | fonctionne, mais le contenu et les actions restent ceux de la page historique |

## P3 — Référentiels, administration, statistiques avancées

| # | Tâche | Constat |
|---|---|---|
| P3-1 | **Remplir les 12 référentiels** (ports, pays, devises, natures, tarifs, règles documentaires, paramètres, équipes, types de documents…) | tous vides : les écrans sont conformes mais sans contenu d'exploitation |
| P3-2 | Relier les référentiels aux formulaires métier (listes déroulantes alimentées par `/api/referentiels`) | aujourd'hui les champs référentiels sont saisis en texte libre |
| P3-3 | Couvrir les écrans d'administration (utilisateurs, rôles, sécurité, intégrations) | 13 entrées, majoritairement PARTIEL |
| P3-4 | Statistiques avancées (séries, comparaisons, export planifié) | l'écran actuel affiche les indicateurs réels de `/api/stats`, rien de plus |
| P3-5 | Écran « Graphiques » dédié | aujourd'hui rattaché à la page rapports ; aucun écran de graphiques autonome |

## Dépendances externes et limitations

1. **Aucun connecteur douanier ou ERP réel** n'est configuré sur ce poste
   (adaptateurs `demo_simulated`, `assisted_export`, `customs_api` présents mais
   non reliés à un service distant). Toute automatisation d'échange reste donc
   une **saisie assistée** ; l'interface le signale à l'utilisateur.
2. **Moteur OCR Tesseract indisponible** (`libGL` absent) : les écrans de
   traitement fonctionnent, mais l'extraction réelle ne peut pas être rejouée
   ici. Les 23 échecs de la suite de tests viennent de là, pas du code d'écran.
3. **Base de démonstration** : 715 dossiers, 198 jobs, 0 ETA. Les volumes
   affichés par les écrans reflètent ce jeu de données, jamais des valeurs
   simulées.

## Méthode de travail pour la suite

1. Prendre la première ligne non conforme de `MATRICE_ECRANS.md`.
2. Corriger, tester (unitaire + jsdom quand c'est un écran), puis **régénérer
   la matrice** — c'est elle qui fait foi.
3. Ne déclarer CONFORME qu'un écran accessible, affichant les bonnes données,
   avec des actions fonctionnelles, permissions respectées et test vert.
