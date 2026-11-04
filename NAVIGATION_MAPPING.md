# Navigation Mapping: Old Routes → New 12-Section Hierarchy

## Overview
Mapping of existing backend API routes and frontend pages to the new 12-section navigation hierarchy per mission specification.

---

## 1. COCKPIT (🏠) - `/#cockpit`
**Role**: `lecteur` | **Icon**: Dashboard/Gauge

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Vue d'ensemble | `#cockpit` | `GET /api/dashboard` (statistiques_generales) | ✅ Exists |
| Indicateurs clés | `#cockpit/kpis` | `GET /api/dashboard/indicateurs` | ✅ Exists |
| Alertes actives | `#cockpit/alertes` | `GET /api/dashboard/alertes` | ✅ Exists |
| Tâches prioritaires | `#cockpit/taches` | `GET /api/dashboard` + workflow | 🔄 Partial |
| Santé système | `#cockpit/sante` | `GET /api/dashboard/sante` | ✅ Exists |

**Frontend**: `tab-cockpit` section exists in index.html

---

## 2. MON ESPACE DE TRAVAIL (🏢) - `/#workspace`
**Role**: `lecteur` | **Icon**: Briefcase/Workspace

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Mes tâches | `#workspace/taches` | `GET /api/dossiers` + workflow stages | 🔄 Partial |
| À valider | `#workspace/valider` | `GET /api/dossiers?statut=en_validation` | 🔄 Partial |
| En attente | `#workspace/en-attente` | `GET /api/dossiers?statut=en_attente` | 🔄 Partial |
| Mes alertes | `#workspace/alertes` | `GET /api/dashboard/alertes` (user-scoped) | 🔄 Partial |
| Dossiers récents | `#workspace/recents` | `GET /api/dossiers` (sorted by date) | ✅ Exists |

**Frontend**: `tab-workspace` section exists with tabs structure

---

## 3. GESTION DES DOSSIERS (📁) - `/#dossiers`
**Role**: `agent_de_transit` | **Icon**: Folder

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Nouveau dossier | `#dossiers/nouveau` | `POST /transit/dossiers` | ✅ Exists |
| Tous les dossiers | `#dossiers/tous` | `GET /transit/dossiers` (with filters) | ✅ Exists |
| Dossiers en cours | `#dossiers/en-cours` | `GET /transit/dossiers?statut=en_cours` | ✅ Exists |
| Dossiers bloqués | `#dossiers/bloques` | `GET /transit/dossiers?statut=bloque` | ✅ Exists |
| Dossiers clôturés | `#dossiers/clotures` | `GET /transit/dossiers?statut=cloture` | ✅ Exists |
| Clients | `#dossiers/clients` | `GET/POST /api/dossiers/clients` | ✅ Exists |

**Frontend**: `tab-transit` section exists (needs restructuring)

---

## 4. DOCUMENTS & OCR (📄) - `/#documents`
**Role**: `lecteur` | **Icon**: FileText/Scan

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Scanner / Importer | `#documents/import` | `POST /api/import` + `/api/dossiers/{id}/documents` | ✅ Exists |
| Boîte de réception | `#documents/inbox` | `GET /api/dossiers/{id}/documents-ocr` | ✅ Exists |
| Classification | `#documents/classif` | `POST /api/dossiers/{id}/documents-ocr/auto-classifier` | ✅ Exists |
| Extraction OCR | `#documents/ocr` | `GET /api/dossiers/{id}/documents-ocr/{extraction_id}` | ✅ Exists |
| Vérification | `#documents/verification` | `POST /api/dossiers/{id}/documents-ocr/{id}/valider` | ✅ Exists |
| Archives | `#documents/archives` | `GET /api/dossiers/{id}/documents-ocr` (archived) | 🔄 Partial |

**Frontend**: `tab-import` section exists (needs restructuring)

---

## 5. CONTRÔLE & CONFORMITÉ (✅) - `/#controle`
**Role**: `controleur_documentaire` | **Icon**: CheckCircle

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Contrôle documentaire | `#controle/documentaire` | `POST /api/controle/analyser` | ✅ Exists |
| Comparaison documents | `#controle/comparaison` | `GET /api/controle/{id}/anomalies` (cross-doc) | 🔄 Partial |
| Documents manquants | `#controle/manquants` | `GET /api/controle/{id}/anomalies?type=missing` | 🔄 Partial |
| Anomalies | `#controle/anomalies` | `GET /api/controle/{id}/anomalies` | ✅ Exists |
| Historique contrôles | `#controle/historique` | `GET /transit/dossiers/{id}/historique` | ✅ Exists |

**Frontend**: `tab-quality` section exists (needs restructuring)

---

## 6. OPÉRATIONS MARITIMES (⚓) - `/#maritime`
**Role**: `agent_de_transit` | **Icon**: Anchor/Ship

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Escales | `#maritime/escales` | `GET/POST /transit/dossiers` (port calls) | ✅ Exists |
| Navires | `#maritime/navires` | `GET/POST /api/navires` | ✅ Exists |
| Voyages | `#maritime/voyages` | `GET/POST /api/expeditions` | ✅ Exists |
| Connaissances B/L | `#maritime/bl` | `GET/POST /api/connaissements/bl` | ✅ Exists |
| Conteneurs | `#maritime/conteneurs` | `GET/POST /api/conteneurs` | ✅ Exists |
| Suivi arrivées | `#maritime/arrivees` | `GET /transit/dossiers?statut=arrived` | ✅ Exists |

**Frontend**: Multiple sections in `tab-transit` (needs consolidation)

---

## 7. DOUANE & RÉGLEMENTATION (🏛️) - `/#douane`
**Role**: `agent_de_transit` | **Icon**: Building/Gavel

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Classement tarifaire | `#douane/tarif` | `GET /api/reglementation/tarif` | ✅ Exists |
| Déclarations | `#douane/declarations` | `GET/POST /api/declarations` | ✅ Exists |
| Contrôles douaniers | `#douane/controles` | `GET /api/declarations/{id}` (customs controls) | 🔄 Partial |
| Liquidation | `#douane/liquidation` | `GET/POST /api/declarations/liquidation` | ✅ Exists |
| Paiements | `#douane/paiements` | `GET/POST /api/frais` (douane category) | ✅ Exists |
| Mainlevées | `#douane/mainlevee` | `PATCH /api/declarations/{id} (mainlevee_obtenue)` | ✅ Exists |

**Frontend**: Routes exist in declarations.py, reglementation.py

---

## 8. ENLÈVEMENT & LIVRAISON (🚚) - `/#enlevissement`
**Role**: `agent_de_transit` | **Icon**: Truck/MapPin

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Ordres d'enlèvement | `#enlevissement/ordres` | `GET/POST /api/transport/ordres` | ✅ Exists |
| Planification | `#enlevissement/planning` | `GET /api/transport/planning` | 🔄 Partial |
| Transporteurs | `#enlevissement/transporteurs` | `GET/POST /api/transport/transporteurs` | ✅ Exists |
| Sortie portuaire | `#enlevissement/sortie-port` | `POST /transit/dossiers/{id}/sortie_port` | 🔄 Partial |
| Livraison | `#enlevissement/livraison` | `POST /transit/dossiers/{id}/livraison` | 🔄 Partial |
| Preuves de livraison | `#enlevissement/preuves` | `GET /api/transport/preuves` | 🔄 Partial |

**Frontend**: `tab-transport` and `tab-terminal` sections exist

---

## 9. FINANCE & FACTURATION (💰) - `/#finance`
**Role**: `responsable_financier` | **Icon**: CreditCard/DollarSign

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Frais du dossier | `#finance/frais-dossier` | `GET/POST /api/frais` | ✅ Exists |
| Débours | `#finance/debours` | `GET /api/frais?categorie=debours` | ✅ Exists |
| Factures fournisseurs | `#finance/factures-fournisseurs` | `GET/POST /api/frais/facture?type=recue` | ✅ Exists |
| Facturation client | `#finance/facturation` | `GET/POST /api/frais/facture?type=emisee` | ✅ Exists |
| Paiements | `#finance/paiements` | `POST /api/frais/{id}/paiement` | ✅ Exists |
| Rapprochement | `#finance/reconciliation` | `POST /api/frais/rapprochement/auto` | ✅ Exists |
| Clôture financière | `#finance/cloture` | `POST /transit/dossiers/{id}/cloturer` | ✅ Exists |

**Frontend**: `tab-frais` section exists (needs restructuring)

---

## 10. RAPPORTS & STATISTIQUES (📊) - `/#rapports`
**Role**: `lecteur` | **Icon**: BarChart/LineChart

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Statistiques | `#rapports/statistiques` | `GET /api/dashboard/indicateurs` | ✅ Exists |
| Graphiques | `#rapports/graphes` | `GET /api/dashboard/graphique/*` (8 endpoints) | ✅ Exists |
| Exports | `#rapports/exports` | `GET /api/dashboard/export` + dossier export | ✅ Exists |

**Frontend**: `tab-dashboard` section exists (needs restructuring)

---

## 11. RÉFÉRENTIELS & PARAMÈTRES (⚙️) - `/#referentiels`
**Role**: `lecteur` | **Icon**: Settings/Layers

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Profils | `#referentiels/profiles` | `GET/POST/PUT/DELETE /api/profiles` | ✅ Exists |
| Types de documents | `#referentiels/types-documents` | `GET /api/dossiers/types-documents` | ✅ Exists |
| Paramètres | `#referentiels/parametres` | `GET /api/system/config` | ✅ Exists |

**Frontend**: `tab-profiles` section exists

---

## 12. ADMINISTRATION & SÉCURITÉ (🔐) - `/#admin`
**Role**: `administrateur` | **Icon**: Shield/Users

| Sub-item | Route | Backend API | Status |
|----------|-------|-------------|--------|
| Utilisateurs | `#admin/utilisateurs` | `GET/POST /api/rbac/utilisateurs` | ✅ Exists |
| Rôles | `#admin/roles` | `GET/POST /api/rbac/roles` | ✅ Exists |
| Équipes | `#admin/equipes` | `GET/POST /api/rbac/equipes` | ✅ Exists |
| Paramètres généraux | `#admin/parametres` | `GET/PUT /api/system/config` | ✅ Exists |
| Paramètres OCR | `#admin/parametres-ocr` | `GET/PUT /api/system/ocr-config` | 🔄 Partial |
| Moteurs OCR | `#admin/moteurs-ocr` | `GET /api/system/engines` | ✅ Exists |
| Connecteurs API | `#admin/connecteurs-api` | `GET/POST /api/system/connectors` | 🔄 Partial |
| Workflows | `#admin/workflows` | `GET/POST /api/workflow/templates` | ✅ Exists |
| Référentiels | `#admin/referentiels` | `GET /api/reglementation/*` (refs) | ✅ Exists |
| Journal d'audit | `#admin/journal` | `GET /transit/audit` | ✅ Exists |
| Sauvegardes | `#admin/sauvegardes` | `GET/POST /api/system/backups` | ✅ Exists |

**Frontend**: `tab-utilisateurs` section exists (needs restructuring)

---

## Summary: Implementation Priority

### Phase 1: Navigation Infrastructure (Week 1)
- [ ] New sidebar component with 12 sections + RBAC filtering
- [ ] Hash-based router with sub-item support
- [ ] Page section mapping (12 main pages + ~60 sub-pages)
- [ ] Active state management

### Phase 2: Cockpit & Workspace (Week 1-2)
- [ ] Enhanced Cockpit with real-time KPIs, alerts, tasks
- [ ] Guided Workspace with 5 tabs + empty states
- [ ] User preference persistence

### Phase 3: Dossier Experience (Week 2)
- [ ] Structured Dossier page with timeline sidebar
- [ ] Kanban-style workflow visualization
- [ ] Document gallery with OCR preview
- [ ] Validation inbox with diff view

### Phase 4: Module Pages (Week 2-3)
- [ ] Restructure each of the 10 module pages
- [ ] Connect to real backend APIs
- [ ] Add empty/loading/error states

### Phase 5: Design System Harmonization (Week 3)
- [ ] CSS custom properties (tokens)
- [ ] Component library standardization
- [ ] Dark mode refinement
- [ ] Accessibility audit

### Phase 6: RBAC Integration (Week 3)
- [ ] Frontend permission guards
- [ ] Menu filtering by role
- [ ] Route protection

### Phase 7: Testing & Polish (Week 3-4)
- [ ] Navigation E2E tests
- [ ] Regression tests
- [ ] Performance optimization
- [ ] Documentation