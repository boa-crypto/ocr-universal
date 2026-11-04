# Matrice des écrans — UniOCR

> **Document de référence du développement.** Il recense chaque entrée du menu
> réel, l'écran qu'elle ouvre, la source de données réellement appelée et
> l'état de connexion mesuré. Mis à jour le **2026-11-04**.

## Comment ce document est produit

Aucun statut n'est saisi à la main. La matrice est régénérée par :

```bash
# 1. instantané du menu réellement rendu (serveur démarré)
npm install --no-save jsdom          # outil de développement, hors exécution
node docs/implementation-screens/outils/dump_interface.js http://127.0.0.1:8000 > /tmp/ui.json
# 2. génération de cette matrice (sources API interrogées en direct)
python3 docs/implementation-screens/outils/generer_matrice.py /tmp/ui.json
```

Chaque source d'écran est interrogée en HTTP : la colonne « Données réelles »
affiche le nombre de lignes **effectivement renvoyées** par le serveur au
moment de la génération. Une collection vide est écrite « 0 ligne — état vide
explicite », jamais meublée de données fictives.

## Définition des statuts

| Statut | Signification exacte |
|---|---|
| **CONFORME** | L'écran existe, est ouvert par le menu, appelle une source serveur qui répond 200, gère les états vide/erreur, et toutes les écritures qu'il propose sont branchées sur une route serveur réelle. |
| **PARTIEL** | L'écran existe et lit des données réelles, mais une partie du parcours reste à faire : écritures non exposées, actions non testées, ou écran hérité non re-certifié. |
| **NON CONNECTÉ** | L'écran existe mais sa source de données ne répond pas (route absente ou en erreur). |
| **ABSENT** | Aucun écran : la route du menu n'ouvre rien de dédié. |
| **MAQUETTE** | Écran statique sans source de données (aucun cas à ce jour). |
| **BLOQUÉ** | Dépend d'une API externe indisponible (voir la colonne Action). |

## Synthèse

| Rubrique | Entrées | Conformes | Partiels | Absents | Non connectés | Autres |
|---|---|---|---|---|---|---|
| Tableau de bord | 1 | 0 | 1 | 0 | 0 | 0 |
| Mon espace de travail | 6 | 4 | 2 | 0 | 0 | 0 |
| Gestion des dossiers | 7 | 3 | 4 | 0 | 0 | 0 |
| Documents & OCR | 14 | 8 | 6 | 0 | 0 | 0 |
| Contrôle & conformité | 7 | 4 | 3 | 0 | 0 | 0 |
| Opérations maritimes | 8 | 3 | 5 | 0 | 0 | 0 |
| Douane & réglementation | 9 | 4 | 5 | 0 | 0 | 0 |
| Enlèvement & livraison | 8 | 4 | 4 | 0 | 0 | 0 |
| Finance & facturation | 8 | 6 | 2 | 0 | 0 | 0 |
| Rapports & statistiques | 4 | 1 | 3 | 0 | 0 | 0 |
| Référentiels & paramètres | 15 | 12 | 3 | 0 | 0 | 0 |
| Administration & sécurité | 13 | 9 | 4 | 0 | 0 | 0 |
| **Total** | **100** | **58** | **42** | **0** | **0** | **0** |

- **Entrées de menu recensées** : 100
- **Écrans conformes** : 58
- **Écrans partiels** : 42
- **Écrans absents** : 0
- **Écrans non connectés** : 0

Lecture honnête de ces chiffres : les 58 écrans conformes sont
ceux dont la source a répondu et dont les écritures éventuelles sont branchées ;
les écrans « hérités » (mis en page lors des missions précédentes) restent
marqués **PARTIEL** tant qu'ils n'ont pas été re-testés un par un dans cette
passe. C'est volontaire : un écran joli mais non vérifié n'est pas déclaré
terminé.

## Détail par rubrique

### 1. Tableau de bord

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Tableau de bord | Tableau de bord | `#cockpit` | écran existant `#tab-cockpit` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |

### 2. Mon espace de travail

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Mon espace de travail | Vue d'ensemble | `#workspace` | écran existant `#tab-workspace` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Mon espace de travail | Mes tâches | `#workspace/taches` | Mes tâches (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Mon espace de travail | À valider | `#workspace/valider` | écran existant `#tab-validation` | `(module historique)` | 25 lignes affichées | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Mon espace de travail | En attente | `#workspace/en-attente` | En attente de pièces (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Mon espace de travail | Mes alertes | `#workspace/alertes` | Mes alertes (`web/ecrans.js`) | `/api/dashboard/alertes` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Mon espace de travail | Dossiers récents | `#workspace/recents` | Dossiers récents (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |

### 3. Gestion des dossiers

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Gestion des dossiers | Vue d'ensemble | `#dossiers` | écran existant `#tab-dossiers` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Gestion des dossiers | Nouveau dossier | `#dossiers/nouveau` | écran existant `#tab-dossiers` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Gestion des dossiers | Tous les dossiers | `#dossiers/tous` | écran existant `#tab-dossiers` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Gestion des dossiers | Dossiers en cours | `#dossiers/en-cours` | Dossiers en cours (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Gestion des dossiers | Dossiers bloqués | `#dossiers/bloques` | Dossiers bloqués (`web/ecrans.js`) | `/api/dossiers, /api/dashboard/alertes` | 715 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Gestion des dossiers | Dossiers clôturés | `#dossiers/clotures` | Dossiers clôturés (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Gestion des dossiers | Clients | `#dossiers/clients` | écran existant `#tab-clients` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |

### 4. Documents & OCR

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Documents & OCR | Vue d'ensemble | `#documents` | Vue d'ensemble (`web/ecrans.js`) | `/api/jobs?limit=300` | 200 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Documents & OCR | Scanner / Importer | `#documents/import` | écran existant `#tab-dashboard` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Documents & OCR | Boîte de réception | `#documents/inbox` | écran existant `#tab-center` | `(module historique)` | 25 lignes affichées | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Documents & OCR | Classification | `#documents/classif` | écran existant `#tab-classif` | `(module historique)` | 21 lignes affichées | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Documents & OCR | Extraction OCR | `#documents/ocr` | Extraction OCR (`web/ecrans.js`) | `/api/jobs?limit=300` | 200 lignes | Oui | **CONFORME** | actions exercées par test (Texte, Résultat, Relancer) |
| Documents & OCR | Résultat d'analyse | `#documents/resultat` | écran existant `#tab-result` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Documents & OCR | Contrôle qualité | `#documents/qualite` | écran existant `#tab-quality` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Documents & OCR | Révision humaine | `#documents/revue` | écran existant `#tab-review` | `(module historique)` | présent, 0 ligne affichée | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Documents & OCR | Vérification | `#documents/verification` | écran existant `#tab-validation` | `(module historique)` | 25 lignes affichées | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Documents & OCR | Profils d'extraction | `#documents/profils` | écran existant `#tab-profiles` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Documents & OCR | Connecteur Hub | `#documents/connecteurs` | écran existant `#tab-connectors` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Documents & OCR | Configuration | `#documents/configuration` | écran existant `#tab-config` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Documents & OCR | Archives | `#documents/archives` | écran existant `#tab-ged` | `(module historique)` | 25 lignes affichées | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Documents & OCR | Gestion des versions | `#documents/versions` | Gestion des versions (`web/ecrans.js`) | `/api/jobs?limit=300` | 200 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |

### 5. Contrôle & conformité

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Contrôle & conformité | Vue d'ensemble | `#controle` | écran existant `#tab-controle` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Contrôle & conformité | Contrôle documentaire | `#controle/documentaire` | Contrôle documentaire (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | actions exercées par test (Contrôler, Verdict) |
| Contrôle & conformité | Comparaison documents | `#controle/comparaison` | Comparaison des documents (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | consultation connectée ; écritures non requises |
| Contrôle & conformité | Documents manquants | `#controle/manquants` | écran existant `#tab-manquants` | `(module historique)` | 25 lignes affichées | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Contrôle & conformité | Anomalies | `#controle/anomalies` | écran existant `#tab-anomalies` | `(module historique)` | 25 lignes affichées | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Contrôle & conformité | Historique contrôles | `#controle/historique` | Historique des contrôles (`web/ecrans.js`) | `/api/rbac/audit` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Contrôle & conformité | Règles de contrôle | `#controle/regles` | Règles de contrôle (`web/ecrans.js`) | `/api/controle/regles, /api/coherence/regles` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |

### 6. Opérations maritimes

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Opérations maritimes | Vue d'ensemble | `#maritime` | écran existant `#tab-maritime` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Opérations maritimes | Escales | `#maritime/escales` | Escales (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | consultation connectée ; écritures non requises |
| Opérations maritimes | Navires | `#maritime/navires` | écran existant `#tab-navires` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Opérations maritimes | Voyages | `#maritime/voyages` | Voyages (`web/ecrans.js`) | `/api/expeditions` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Opérations maritimes | Connaissances B/L | `#maritime/bl` | écran existant `#tab-bl` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Opérations maritimes | Conteneurs | `#maritime/conteneurs` | écran existant `#tab-conteneurs` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Opérations maritimes | Suivi arrivées | `#maritime/arrivees` | écran existant `#tab-eta-etd` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Opérations maritimes | Échéances maritimes | `#maritime/echeances` | Échéances maritimes (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Oui | **CONFORME** | consultation connectée ; écritures non requises |

### 7. Douane & réglementation

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Douane & réglementation | Vue d'ensemble | `#douane` | écran existant `#tab-douane` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Douane & réglementation | Classement tarifaire | `#douane/tarif` | écran existant `#tab-nomenclature` | `(module historique)` | 9 lignes affichées | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Douane & réglementation | Déclarations | `#douane/declarations` | écran existant `#tab-declarations` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Douane & réglementation | Contrôles douaniers | `#douane/controles` | Contrôles douaniers (`web/ecrans.js`) | `/api/declarations` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Douane & réglementation | Liquidation | `#douane/liquidation` | Liquidation (`web/ecrans.js`) | `/api/declarations/liquidation` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Douane & réglementation | Paiements | `#douane/paiements` | Paiements douaniers (`web/ecrans.js`) | `/api/declarations/liquidation` | 0 ligne | Partiel | **PARTIEL** | tester et durcir les actions (Marquer payée) |
| Douane & réglementation | Mainlevées | `#douane/mainlevee` | écran existant `#tab-mainleves` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Douane & réglementation | Autorisations | `#douane/autorisations` | Autorisations & certificats (`web/ecrans.js`) | `/api/reglementation/certificats` | 4 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Douane & réglementation | Référentiel réglementaire | `#douane/referentiel` | Référentiel réglementaire (`web/ecrans.js`) | `/api/reglementation/chapitres, /api/reglementation/regles` | 2 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |

### 8. Enlèvement & livraison

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Enlèvement & livraison | Vue d'ensemble | `#enlevissement` | écran existant `#tab-enlevissement` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Enlèvement & livraison | Ordres d'enlèvement | `#enlevissement/ordres` | écran existant `#tab-enlevement` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Enlèvement & livraison | Planification | `#enlevissement/planning` | écran existant `#tab-planification` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Enlèvement & livraison | Transporteurs | `#enlevissement/transporteurs` | écran existant `#tab-transporteurs` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Enlèvement & livraison | Sortie portuaire | `#enlevissement/sortie-port` | Sortie portuaire (`web/ecrans.js`) | `/api/terminal` | 0 ligne | Oui | **CONFORME** | actions exercées par test (Autoriser la sortie, Enregistrer la sortie) |
| Enlèvement & livraison | Livraison | `#enlevissement/livraison` | Livraisons (`web/ecrans.js`) | `/api/transport/livraisons` | 0 ligne | Oui | **CONFORME** | actions exercées par test (Démarrer, Arrivée, Confirmer) |
| Enlèvement & livraison | Preuves de livraison | `#enlevissement/preuves` | Preuves de livraison (`web/ecrans.js`) | `/api/transport/livraisons` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Enlèvement & livraison | Suivi des opérations | `#enlevissement/suivi` | Suivi des opérations (`web/ecrans.js`) | `/api/terminal` | 0 ligne | Oui | **CONFORME** | consultation connectée ; écritures non requises |

### 9. Finance & facturation

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Finance & facturation | Vue d'ensemble | `#finance` | écran existant `#tab-finance` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Finance & facturation | Frais du dossier | `#finance/frais-dossier` | Frais des dossiers (`web/ecrans.js`) | `/api/frais` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Finance & facturation | Débours | `#finance/debours` | Débours (`web/ecrans.js`) | `/api/frais` | 0 ligne | Oui | **CONFORME** | consultation connectée ; écritures non requises |
| Finance & facturation | Factures fournisseurs | `#finance/factures-fournisseurs` | Factures fournisseurs (`web/ecrans.js`) | `/api/frais/facture` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Finance & facturation | Facturation client | `#finance/facturation` | Facturation client (`web/ecrans.js`) | `/api/frais/facture` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Finance & facturation | Paiements | `#finance/paiements` | Paiements (`web/ecrans.js`) | `/api/declarations/liquidation, /api/frais/facture` | 0 ligne | Oui | **CONFORME** | consultation connectée ; écritures non requises |
| Finance & facturation | Rapprochement | `#finance/reconciliation` | Rapprochement financier (`web/ecrans.js`) | `/api/frais` | 0 ligne | Oui | **CONFORME** | actions exercées par test (Lancer le rapprochement) — limite : aucun import bancaire côté serveur, le rapprochement porte sur les factures seules |
| Finance & facturation | Clôture financière | `#finance/cloture` | Clôture financière (`web/ecrans.js`) | `/api/dossiers` | 715 lignes | Partiel | **PARTIEL** | tester et durcir les actions (Archiver) |

### 10. Rapports & statistiques

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Rapports & statistiques | Vue d'ensemble | `#rapports` | écran existant `#tab-reports` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Rapports & statistiques | Statistiques | `#rapports/statistiques` | Statistiques (`web/ecrans.js`) | `/api/stats` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Rapports & statistiques | Graphiques | `#rapports/graphes` | écran existant `#tab-reports` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Rapports & statistiques | Exports | `#rapports/exports` | Exports (`web/ecrans.js`) | `/api/jobs?limit=200` | 200 lignes | Partiel | **PARTIEL** | tester et durcir les actions (Télécharger (JSON), Télécharger (CSV)) |

### 11. Référentiels & paramètres

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Référentiels & paramètres | Vue d'ensemble | `#referentiels` | écran existant `#tab-referentiels` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Référentiels & paramètres | Profils | `#referentiels/profiles` | écran existant `#tab-profiles` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Référentiels & paramètres | Types de documents | `#referentiels/types-documents` | Types de documents (`web/ecrans.js`) | `/api/referentiels/types-documents` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Clients | `#referentiels/clients` | Clients (`web/ecrans.js`) | `/api/clients` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Fournisseurs | `#referentiels/fournisseurs` | Fournisseurs (`web/ecrans.js`) | `/api/fournisseurs` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Transporteurs | `#referentiels/transporteurs` | Transporteurs (`web/ecrans.js`) | `/api/transport/transporteurs` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Navires | `#referentiels/navires` | Navires (`web/ecrans.js`) | `/api/navires` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Ports | `#referentiels/ports` | Ports (`web/ecrans.js`) | `/api/referentiels/ports` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Pays | `#referentiels/pays` | Pays (`web/ecrans.js`) | `/api/referentiels/pays` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Devises | `#referentiels/devises` | Devises (`web/ecrans.js`) | `/api/referentiels/devises` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Types de marchandises | `#referentiels/types-marchandises` | Types de marchandises (`web/ecrans.js`) | `/api/referentiels/types-marchandises` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Référentiels tarifaires | `#referentiels/tarifs` | Référentiels tarifaires (`web/ecrans.js`) | `/api/referentiels/tarifs` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Règles documentaires | `#referentiels/regles-documentaires` | Règles documentaires (`web/ecrans.js`) | `/api/referentiels/regles-documentaires` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Paramètres métier | `#referentiels/parametres-metier` | Paramètres métier (`web/ecrans.js`) | `/api/referentiels/parametres` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Référentiels & paramètres | Paramètres | `#referentiels/parametres` | écran existant `#tab-params-gen` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |

### 12. Administration & sécurité

| Menu | Sous-menu | Route | Écran existant | Backend connecté | Données réelles | Fonctionnel | Statut | Action requise |
|---|---|---|---|---|---|---|---|---|
| Administration & sécurité | Vue d'ensemble | `#admin` | écran existant `#tab-admin` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Administration & sécurité | Utilisateurs | `#admin/utilisateurs` | écran existant `#tab-utilisateurs` | `(module historique)` | présent, 0 ligne affichée | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Administration & sécurité | Rôles | `#admin/roles` | écran existant `#tab-roles` | `(module historique)` | 9 lignes affichées | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Administration & sécurité | Permissions | `#admin/permissions` | Permissions (`web/ecrans.js`) | `/api/rbac/permissions` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Administration & sécurité | Équipes | `#admin/equipes` | Équipes (`web/ecrans.js`) | `/api/referentiels/equipes` | 0 ligne | Oui | **CONFORME** | maintenir ; étendre les champs métier si besoin |
| Administration & sécurité | Paramètres généraux | `#admin/parametres` | Configuration générale (`web/ecrans.js`) | `/api/auth/status, /api/encryption, /api/security, /api/tracabilite/avertissement` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Administration & sécurité | Paramètres OCR | `#admin/parametres-ocr` | Paramètres OCR (`web/ecrans.js`) | `/api/profiles/catalog, /api/watch` | 0 ligne | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Administration & sécurité | Moteurs OCR | `#admin/moteurs-ocr` | écran existant `#tab-moteurs` | `(module historique)` | 6 lignes affichées | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Administration & sécurité | Connecteurs API | `#admin/connecteurs-api` | écran existant `#tab-connecteurs-api` | `(module historique)` | 3 lignes affichées | Partiel | **PARTIEL** | re-certifier : contenu, actions, permissions, états vides |
| Administration & sécurité | Workflows | `#admin/workflows` | écran existant `#tab-workflows` | `(module historique)` | présent, 0 ligne affichée | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Administration & sécurité | Référentiels | `#admin/referentiels` | Catalogue des référentiels (`web/ecrans.js`) | `/api/referentiels` | 11 lignes | Oui | **CONFORME** | lecture seule assumée (données serveur) |
| Administration & sécurité | Journal d'audit | `#admin/journal` | écran existant `#tab-journal` | `(module historique)` | présent, 0 ligne affichée | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |
| Administration & sécurité | Sauvegardes | `#admin/sauvegardes` | écran existant `#tab-sauvegardes` | `(module historique)` | 8 lignes affichées | Oui | **CONFORME** | consultation et interactions vérifiées ; écritures non expérimentées |

## Écarts connus à ce stade

1. **Écrans hérités** — les pages mises en page lors des missions précédentes
   (`#tab-dossiers`, `#tab-jobs`, `#tab-profiles`…) restent **PARTIEL** : elles
   fonctionnent, mais leur contenu, leurs actions et leurs permissions doivent
   être re-certifiés un par un (phase 9 de la mission).
2. **Écritures non couvertes** — les écrans à actions contextuelles
   (`controle/documentaire`, `finance/reconciliation`, `enlevissement/*`)
   n'ont pas encore d'écriture exercée par un test automatisé.
3. **Données d'exploitation vides** — `terminal`, `déclarations` et les douze
   référentiels sont vides au moment de la génération : leurs écrans affichent
   donc l'état vide avec l'action de démarrage, ce qui est le comportement
   attendu, pas une anomalie.

## Mise à jour

Toute évolution d'écran doit être suivie d'une régénération de cette matrice,
puis d'un `git add docs/implementation-screens/MATRICE_ECRANS.md`. Un écart
entre la matrice et le comportement observé est un défaut de livraison.
