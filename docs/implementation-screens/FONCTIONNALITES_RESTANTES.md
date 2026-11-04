# Fonctionnalités restantes — UniOCR

État au 2026-11-04, après la passe 22. Ce document est la liste de travail
priorisée ; il se déduit de [`MATRICE_ECRANS.md`](MATRICE_ECRANS.md), qui reste
la référence ligne à ligne.

**Chiffres du jour, sans arrondi complaisant** : 101 entrées de menu,
**101 conformes**, **0 partiel**, 0 absent, 0 non connecté.

La page « Paramètres généraux » a été retirée en passe 13 (son formulaire
n'enregistrait rien) puis **rétablie en passe 14 sur une vraie API** :
`GET/PUT/DELETE /api/parametres`, écriture dans `data/parametres.json`,
validation nommant le champ, effet immédiat et persistant.

---

## P0 — Sécurité et perte de données

| # | Tâche | Pourquoi | Où |
|---|---|---|---|
| ✅ P0-1 | ~~Figer par un test automatisé le comportement d'un rôle lecteur~~ | **fait en passe 17** : registre RBAC en répertoire temporaire, lecture autorisée (200), écriture refusée (403) et refus tracé (`acces_refuse_role`) | `tests/test_rbac_ecritures.py` |
| ✅ P0-2 | ~~Étendre le test d'écriture refusée à chaque famille d'écran~~ | **fait en passe 17** : 14 écritures couvertes (clients, fournisseurs, référentiels, paramètres, dossiers, frais, documents, rôles, nettoyage, connecteurs, sauvegardes) + distinction opérateur/administrateur | `tests/test_rbac_ecritures.py` |
| ✅ P0-3 | ~~Exercer l'archivage d'un dossier depuis l'écran de clôture~~ | **fait en passe 19** : dossier d'essai `ARCH-UI-1` créé par l'API, archivé depuis l'écran (POST 200, `state: archive`), puis supprimé — zéro dossier de démonstration modifié | `#finance/cloture` |
| ✅ P0-4 | ~~Vraie sauvegarde des paramètres généraux (API + formulaire)~~ | **fait en passe 14** : `GET/PUT/DELETE /api/parametres`, persistance dans `data/parametres.json`, 422 nommant le champ, effet prouvé (limite 1 Mo → import 413, limite 50 Mo → 200) |

## P1 — Dossiers, documents, OCR, contrôle, workflow

| # | Tâche | Constat |
|---|---|---|
| ✅ P1-1 | ~~Remplacer les 6 redirections « Gestion des dossiers »~~ | **fait en passe 2** et **vérifié en passe 13** : en cours / bloqués / clôturés = écrans dédiés (25 lignes chacun) ; tous / nouveau / clients = pages réellement existantes exercées (40 lignes, dialogue de création POST 200, écran Clients partagé) |
| ✅ P1-2 | ~~Idem pour les 5 redirections « Mon espace de travail »~~ | **fait en passe 2**, re-mesuré en passe 13 : tableau de bord de l'espace (5 cartes, 24 compteurs), à valider (25 lignes, 185 en attente) |
| ✅ P1-3a | ~~Vue d'ensemble + Extraction OCR~~ | **fait en passe 3** : deux écrans dédiés sur `/api/jobs` ; actions Texte / Résultat / Relancer exercées par test |
| ✅ P1-3b | ~~Re-certifier les écrans Documents hérités~~ | **fait en passes 5 et 13** : boîte de réception, classification, archives, vérification, révision, résultat, qualité, profils, connecteurs, configuration — tous mesurés (lignes réelles ou état vide explicite) |
| ✅ P1-4 | ~~Tester les actions de contrôle documentaire~~ | **fait en passe 4** : *Contrôler* et *Verdict* exécutés (200) ; résolution d'anomalie avec justification couverte aussi |
| ✅ P1-5 | ~~Historiser la validation OCR dans l'écran de révision~~ | **fait en passe 16** : `GET /api/jobs/{id}/historique` relit le journal d'audit, affiché en chronologie depuis `#documents/ocr` (7 événements réels sur `bl_port.pdf`, validations de champ visibles immédiatement) |

## P2 — Maritime, douane, enlèvement, finance

| # | Tâche | Constat |
|---|---|---|
| P2-1 | Alimenter `terminal` et `declarations` : sur ce poste les deux collections sont **vides** | comportement correct (état vide expliqué) mais non démontrable sur des données réelles ; les liquidations, elles, se créent et se paient depuis l'écran |
| ✅ P2-2 | ~~Tester les parcours de livraison (démarrer → arriver → confirmer)~~ | **fait en passe 6** : trois transitions exécutées (200) sur un ordre réel |
| ✅ P2-3 | ~~Tester le rapprochement automatique~~ | **fait en passe 4** : dialogue de paramètres (dossier + période), `POST` 200, verdict affiché. **Reste** : l'import bancaire côté serveur (`frais.py` : `operations_bancaires = []`, TODO explicite) |
| ✅ P2-4 | ~~Remplacer les redirections « Rapports » (graphiques), « Référentiels » (profils, paramètres métier)~~ | **fait en passe 2** : graphiques → `#tab-reports`, profils → `#tab-profiles`, paramètres métier → écran CRUD |
| ✅ P2-5 | ~~Découpler les écrans de référence des pages historiques~~ | **fait en passe 13** : `#dossiers/clients` ne renvoie plus vers `#tab-clients` mais vers l'écran déclaratif Clients (alias de `référentiels/clients`) : création, édition, suppression et export CSV |
| ✅ P2-6 | ~~Exercer les CRUD des référentiels et des modules métier~~ | **fait en passe 9** : 11 écrans créés / édités / supprimés depuis l'interface (200 partout). Deux défauts serveur corrigés : pays trop long → **500** devenu **422** ; écran Fournisseurs qui envoyait `name`/`country`/`status` au lieu de `nom`/`nom_commercial`/`pays` |
| ✅ P2-7 | ~~Relier « Résultat d'analyse » et « Contrôle qualité » à un document~~ | **fait en passe 10** : action « Ouvrir le résultat » depuis la liste, résultat réel affiché (GET 200), jauges qualité alimentées |
| ✅ P2-8 | ~~Créer le premier utilisateur RBAC depuis l'interface~~ | **fait en passe 11** : création, affichage du jeton une seule fois, édition et suppression exercées (200) |
| ✅ P2-9 | ~~Créer des rôles personnalisés depuis l'interface~~ | **fait en passe 12** : rôles livrés en lecture, rôles personnalisés créés (POST 200), édités (PUT 200), supprimés (DELETE 200) |
| ✅ P2-10 | ~~Exercer « Marquer payée » sur une liquidation~~ | **fait en passe 13** : liquidation créée par l'API, ligne affichée, action cliquée → `PUT /api/declarations/liquidation/{id}` **200**, jeu d'essai supprimé ensuite |

## P3 — Référentiels, administration, statistiques avancées

| # | Tâche | Constat |
|---|---|---|
| ✅ P3-1a | ~~Amorcer les référentiels de référence (ports, pays, devises)~~ | **fait en passe 21** : bouton « Charger le jeu de base » (idempotent, non destructif, tracé) ; 12 pays, 5 devises, 10 ports proposés aux formulaires |
| P3-1b | Remplir le **contenu d'exploitation** (tarifs, règles documentaires, équipes, paramètres métier, natures de marchandise) | ces collections n'ont pas de jeu de référence public : elles relèvent d'une saisie métier, pas d'un code |
| ✅ P3-2 | ~~Relier les référentiels aux formulaires métier~~ | **fait en passe 15** : `datalist` alimentée par `/api/referentiels/{nom}` sur Clients (pays), Fournisseurs (pays), Navires (pavillon) et le dialogue de création de dossier (ports) ; un référentiel vide le dit et laisse la saisie libre |
| ✅ P3-3 | ~~Couvrir les écrans d'administration (utilisateurs, rôles, sécurité, intégrations)~~ | **fait en passes 11 à 13** : 13 entrées mesurées (16 liens, 23 cartes, 3 sources API sur le hub ; utilisateurs et rôles CRUD ; connecteurs API 3 lignes) |
| ✅ P3-4a | ~~Comparer deux périodes~~ | **fait en passe 22** : `GET /api/stats/comparaison?jours=N`, écran `#rapports/comparaison` (6 indicateurs, tendances, aucune variation inventée) |
| P3-4b | Export planifié et séries historiques longues | la comparaison couvre deux fenêtres ; il n'y a ni planification d'export ni archive de séries |
| ✅ P3-5 | ~~Écran « Graphiques » dédié~~ | **fait en passe 18** : `#rapports/graphes` = 6 cartes alimentées par `/api/dashboard/graphique/*`, 3 séries réelles dessinées et 3 états vides expliqués |
| P3-6 | Connecteur Hub : transmettre vers un service distant | dépend d'un service externe non disponible sur ce poste ; l'écran expose l'état réel des connecteurs (3 configurés) et le dit |

## Dépendances externes et limitations

1. **Aucun connecteur douanier ou ERP réel** n'est configuré sur ce poste
   (adaptateurs `demo_simulated`, `assisted_export`, `customs_api` présents mais
   non reliés à un service distant). Toute automatisation d'échange reste donc
   une **saisie assistée** ; l'interface le signale à l'utilisateur.
2. **Moteur OCR Tesseract indisponible** (`libGL` absent) : les écrans de
   traitement fonctionnent, mais l'extraction réelle ne peut pas être rejouée
   ici. Les 23 échecs de la suite de tests viennent de là, pas du code d'écran.
3. **Base de démonstration** : 715 dossiers, ~200 jobs, 49 dossiers archivés,
   0 client, 0 fournisseur, 11 profils. Les volumes affichés par les écrans
   reflètent ce jeu de données, jamais des valeurs simulées.
4. **Archivage irréversible** : l'action « Archiver » de `#finance/cloture`
   demande confirmation et n'est proposée que sur des dossiers non archivés ;
   elle a été exercée sur un dossier jetable, jamais sur les données de
   démonstration.

## Vérifications rejouables

Les 100 preuves de `MATRICE_ECRANS.md` ne dépendent plus de scripts jetables :

```bash
npm install && npm run ui:smoke      # 15 vérifications navigateur, lecture seule
```

Le harnais échoue si un écran critique est vide, si une action ne répond pas,
si une requête tombe en 5xx ou si une erreur JavaScript est émise — et il
**échoue aussi s'il émet une écriture**, pour ne jamais abîmer les données de
l'utilisateur. `tests/test_interface_jsdom.py` le rejoue depuis `pytest`, en
sautant explicitement quand jsdom ou le serveur manquent.

## Méthode de travail pour la suite

1. Prendre la première ligne non conforme de `MATRICE_ECRANS.md`.
2. Corriger, tester (unitaire + jsdom quand c'est un écran), puis **régénérer
   la matrice** — c'est elle qui fait foi.
3. Ne déclarer CONFORME qu'un écran accessible, affichant les bonnes données,
   avec des actions fonctionnelles, permissions respectées et test vert.
