# Fonctionnalités restantes — UniOCR

État au 2026-11-04 (commit `929766cb`). Ce document est la liste de travail
priorisée ; il se déduit de [`MATRICE_ECRANS.md`](MATRICE_ECRANS.md), qui reste
la référence ligne à ligne.

**Chiffres de départ, sans arrondi complaisant** : 100 entrées de menu,
43 écrans dédiés livrés, **30 conformes**, **70 partiels**, 0 absent,
0 non connecté — mais 14 de ces « partiels » sont encore des **redirections**
vers un écran générique (l'application l'annonce elle-même par un bandeau).

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
| P1-1 | Remplacer les 6 redirections « Gestion des dossiers » par des écrans dédiés (tous / en cours / bloqués / clôturés / clients / nouveau) | le menu ouvre `#tab-dossiers` avec un bandeau « pas encore d'écran dédié » |
| P1-2 | Idem pour les 5 redirections « Mon espace de travail » (mes tâches, à valider, en attente, mes alertes, dossiers récents) | chaque entrée devrait filtrer sa propre liste |
| P1-3 | Re-certifier les 14 écrans Documents & OCR (contenu, actions, permissions, états vides) | tous marqués PARTIEL faute de re-test dans cette passe |
| P1-4 | Brancher et tester les actions de contrôle documentaire (analyse, résolution d'anomalie, statut) | actions branchées, aucun test automatisé |
| P1-5 | Historiser la validation OCR dans l'écran de révision | la route existe, l'écran hérité n'a pas été re-testé |

## P2 — Maritime, douane, enlèvement, finance

| # | Tâche | Constat |
|---|---|---|
| P2-1 | Alimenter `terminal` et `declarations` : sur ce poste les deux collections sont **vides**, donc sortie portuaire, contrôles et liquidation n'affichent que l'état vide | aucune donnée à afficher, comportement correct mais non démontrable en conditions réelles |
| P2-2 | Tester les parcours de livraison (démarrer → arriver → confirmer) de bout en bout | routes existantes, aucun test d'écran |
| P2-3 | Tester le rapprochement automatique (`POST /api/frais/rapprochement/auto`) depuis l'écran | action globale branchée, non testée |
| P2-4 | Remplacer les 2 redirections « Rapports » (graphiques) et « Référentiels » (profils, paramètres) | bandeau encore affiché |

## P3 — Référentiels, administration, statistiques avancées

| # | Tâche | Constat |
|---|---|---|
| P3-1 | **Remplir les 12 référentiels** (ports, pays, devises, natures, tarifs, règles documentaires, paramètres, équipes, types de documents…) | tous vides : les écrans sont conformes mais sans contenu d'exploitation |
| P3-2 | Relier les référentiels aux formulaires métier (listes déroulantes alimentées par `/api/referentiels`) | aujourd'hui les champs référentiels sont saisis en texte libre |
| P3-3 | Couvrir les écrans d'administration (utilisateurs, rôles, sécurité, intégrations) | 13 entrées, majoritairement PARTIEL |
| P3-4 | Statistiques avancées (séries, comparaisons, export planifié) | l'écran actuel affiche les indicateurs réels de `/api/stats`, rien de plus |

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
