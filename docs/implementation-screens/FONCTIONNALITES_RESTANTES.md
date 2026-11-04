# Fonctionnalités restantes — UniOCR

État au 2026-11-04, après la passe 41. Ce document est la liste de travail
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

### État corrigé après la passe 25

La matrice régénérée compte **101 entrées, 100 conformes et 1 partielle** :
Déclarations utilise enfin le formulaire connecté, mais son CRUD complet reste à
re-certifier. Le parcours de création est vérifié avec POST simulé via
`npm run ui:declarations`. Le stockage des déclarations, liquidations et enlèvements
est encore en mémoire : leur persistance doit être traitée avant usage durable.

### Passe 26 — stockage métier durable

✅ Déclarations, liquidations et enlèvements sont maintenant conservés dans
`data/metier.sqlite3` et inclus dans les sauvegardes (instantané SQLite).
La limite « en mémoire » indiquée en passe 25 est levée pour les nouvelles
écritures. Les anciennes données volatiles déjà perdues ne sont pas récupérables.
Restent : re-certification CRUD navigateur complète de Déclarations, contrôles
métier des transitions et intégrité référentielle côté serveur. Matrice inchangée :
**100 conformes, 1 partielle**. Ce stockage n'est pas une alimentation automatique.

### Passe 27 — re-certification Déclarations terminée

✅ Le CRUD navigateur de Déclarations est vérifié contre la vraie API isolée,
avec trois démarrages serveur et relecture du stockage SQLite. Commande :
`python -m pytest tests/test_declarations_e2e.py -q` (node/jsdom requis).
La matrice régénérée revient à **101 conformes, 0 partiel**. Les bilans 25–26
ci-dessus sont historiques. Restent les contrôles d'intégrité référentielle et
les règles de transition métier ; la certification CRUD n'est pas une validation
douanière officielle.

### Passe 28 — garde-fous terminal

✅ Séquence API demande → planification → autorisation → sortie, prérequis et
preuve obligatoires, contournements de statut par création/PUT refusés.
Tests : `pytest tests/test_terminal_workflow.py -q` (16 cas) et
`npm run ui:terminal` (visibilité par état, données simulées).
Restent l'intégrité référentielle, les écritures concurrentes d'un même objet,
une procédure de révocation/correction et le parcours terminal UI complet.

### Passe 29 — intégrité du lien liquidation/déclaration

✅ Une liquidation référence une déclaration existante du même dossier ; parent
utilisé protégé contre suppression et déplacement. Contrôles/écritures sont dans
une transaction SQLite, y compris face à création et suppression concurrentes.
Restent les références vers le magasin JSON des dossiers, la protection de leur
suppression, les règles de montants et états douaniers et la correction explicite
d'éventuels anciens liens invalides. Aucune migration destructive automatique.

### Passe 30 — références dossier contrôlées

✅ Déclarations/enlèvements : dossier existant exigé à la création et réaffectation.
✅ Suppression du dossier refusée s'il est utilisé par une déclaration, liquidation
ou un enlèvement ; contrôle coordonné aux écritures concernées par SQLite.
Les constats des passes précédentes sur ces références sont donc levés pour ces
modules. Restent les autres modules liés au dossier, la réparation explicite des
anciens liens invalides et les interventions hors API (restauration serveur arrêté).
Cette coordination n'est pas une transaction distribuée entre JSON et SQLite.

### Passe 31 — expéditions intégrées au stockage métier

✅ Les expéditions survivent au redémarrage et sont incluses dans les sauvegardes.
✅ Leur dossier doit exister ; sa suppression est bloquée tant qu'il est référencé.
Les limites de la passe 30 sur les expéditions sont levées. Restent notamment
frais/factures et justificatifs, règles sémantiques maritimes et interventions
hors API. Aucun nouveau CRUD navigateur complet Voyages n'est revendiqué.

### Passe 32 — frais et factures intégrés

✅ Frais et factures persistants, sauvegardés, références dossier vérifiées et
suppression du dossier protégée. Les limites précédentes sur ces deux objets sont
levées. Paiements utilise les vrais identifiants et statuts ; preuve navigateur
rejouable avec API simulée : `npm run ui:finance`.
Restent en priorité les justificatifs (métadonnées, fichiers, téléversement,
suppression cohérente, sauvegarde), l'import bancaire réel et la validation
comptable des montants/devises. Le rapprochement ne simule aucune opération réelle.

### Passe 33 — stockage et API justificatifs

✅ Métadonnées et lien au frais persistants, fichiers dans le répertoire configuré,
téléversement borné, téléchargement contrôlé, suppression cohérente sur erreurs
gérées et sauvegarde/restauration testée ailleurs. La limite « en mémoire » des
passes précédentes est levée pour les nouvelles pièces de ce circuit API.
Restent l'interface utilisateur de gestion des pièces, la récupération/collecte
explicite d'anciens blobs ou quarantaines, le contrôle antivirus et le comportement
après arrêt brutal à toutes les frontières fichier/DB. Aucun ancien fichier migré
automatiquement. Le circuit ne représente pas un import bancaire.

### Passe 34 — interface des justificatifs

✅ Action Justificatifs depuis les frais : liste, ajout, téléchargement, suppression,
erreurs/reprises et mode lecteur sans mutation. Harnais `npm run ui:justificatifs`
(API simulée), rejoué depuis pytest ; tests multipart API réels séparés.
La limite d'interface de la passe 33 est levée pour ce dialogue. Restent un test
navigateur contre l'API réelle pour ce parcours, la collecte de blobs/quarantaines,
l'antivirus et les tests d'arrêt brutal. Aucun nouvel écran de menu.

### Passe 35 — justificatifs : preuve UI/API réelle obtenue

✅ Le parcours du dialogue est testé contre une API uvicorn réelle isolée,
avec multipart, téléchargement et trois démarrages. Commande :
`pytest tests/test_justificatifs_e2e.py -q` après `npm install`.
La limite de preuve avec API simulée de la passe 34 est levée pour ce parcours.
Il reste une preuve jsdom, pas une validation graphique/native Chromium.
Antivirus, collecte des blobs/quarantaines et scénarios d'arrêt brutal restent ouverts.

### Passe 36 — diagnostic des pièces disponible

✅ `pieces-check --data-dir <magasin> [--json]` inventorie fichiers, liens et
quarantaines sans modification. En checkout :
`PYTHONPATH=src python -m unocr.cli pieces-check --data-dir data --json`.
Codes 0/1/2 ; pas de faux classement orphelin quand la base est absente/inexploitable.
Restent la réparation/restauration explicitement contrôlée et la collecte des
résidus, les tests de véritable arrêt brutal et l'antivirus. Ne pas convertir ce
diagnostic en purge automatique ; suspendre les écritures pour une mesure stable.


### Passe 37 — récupération contrôlée disponible pour une pièce référencée

✅ `pieces-recover ID --data-dir <magasin> [--json]` prépare sans écriture ;
`--apply` copie une quarantaine vérifiée sans écraser la destination, sans modifier
les métadonnées ni supprimer la source. 15 tests isolés réussis. Sauvegarde,
copie séparée des `.tmp`, arrêt des écritures et conservation du rapport requis.
Restent la récupération des métadonnées/liens absents (non automatisée), la
collecte explicite des résidus, l'antivirus et les tests d'arrêt brutal.
La quarantaine conservée reste visible au diagnostic ; aucune purge automatique.


### Passe 38 — arrêts brutaux de récupération couverts à deux points

✅ Vrai SIGKILL du processus de récupération avant/après publication : données
préservées, résidus inventoriés, reprise ou refus d'écrasement vérifiés. Cette
preuve ciblée lève la limite d'absence de test d'arrêt brutal pour ces deux points
seulement, pas pour l'ensemble des flux fichiers.
Restent les coupures électriques/durabilité répertoire, les interruptions pendant
upload/suppression/backup, la collecte contrôlée des résidus et l'antivirus.
Aucune purge ou collecte automatique ajoutée.


### Passe 39 — collision de quarantaine sécurisée

✅ Suppression et rollback n'écrasent plus une quarantaine/destination existante.
Refus 409 en cas de quarantaine déjà présente ; copie conservée et erreur 503
explicite si rétablissement impossible. 9 nouveaux cas isolés, 59 tests ciblés
réussis avec le parcours UI/API réel. Pas de purge automatique.
Restent le vrai SIGKILL pendant cette séquence de suppression (notamment entre
création du lien et retrait du blob), la durabilité après coupure électrique,
la collecte contrôlée des preuves/résidus et l'antivirus.


### Passe 40 — suppression : quatre points SIGKILL couverts

✅ Tests réels après lien, après retrait, avant et après commit : intégrité,
quarantaine, références et suites opérateur vérifiées. La limite SIGKILL de la
passe 39 est levée pour ces quatre points, pas pour tout arrêt possible.
**À traiter :** audit transactionnel/reconciliation. Un commit peut précéder la
réponse HTTP et l'événement d'audit ; une absence de réponse/audit ne signifie pas
que la suppression a été annulée. Relire l'état, ne pas forcer une purge.
Restent aussi les coupures électriques, interruptions upload/backup, collecte
contrôlée des résidus et antivirus. Aucune purge automatique ajoutée.


### Passe 41 — trace SQLite atomique de suppression disponible

✅ Un reçu local est validé/annulé avec les métadonnées de suppression.
`pieces-receipt ID --data-dir <magasin> [--json]` le consulte sans écrire.
Les tests SIGKILL confirment absence avant commit et présence après commit ;
sauvegarde/restauration couvertes. 78 tests ciblés réussis.
Le trou de consultation locale de la passe 40 est levé pour les nouvelles
suppressions de pièces, pas pour le journal fichier ni les opérations historiques.
Restent relais/réconciliation audit.log, traces transactionnelles des autres
opérations, durabilité après coupure électrique, interruptions upload/backup,
collecte contrôlée des résidus et antivirus. Le reçu n'est ni infalsifiable ni
une attribution vérifiée ; son absence ne prouve jamais une annulation.
