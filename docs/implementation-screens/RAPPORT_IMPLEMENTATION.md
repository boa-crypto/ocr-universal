# Rapport d'implémentation — écrans UniOCR

**Passes 1 et 2 — socle des écrans manquants, puis rubriques dossiers et espace de travail.**
Date : 2026-11-04. Branche : `arena/2cd4c91a-ocr-universal`.

Ce rapport décrit **ce qui a réellement été livré et vérifié**, pas ce qui est
prévu. La référence de l'état écran par écran reste
[`MATRICE_ECRANS.md`](MATRICE_ECRANS.md), régénérée depuis l'application.

---

## 1. Point de départ

L'audit de navigation (passe précédente) avait montré deux choses :

- **81 sous-items de menu** ouvraient une page : la navigation ne comptait plus
  de page morte, mais beaucoup de sous-menus retombaient sur un écran générique
  avec un bandeau « n'a pas encore d'écran dédié » ;
- **14 routes** affichaient ce bandeau et **6 référentiels métier** (ports,
  pays, devises, natures de marchandise, grilles tarifaires, règles
  documentaires, paramètres métier, équipes) n'avaient **aucun stockage** :
  impossible de les créer, de les modifier ou de les consulter.

Autrement dit : la coquille était complète, le contenu métier manquait.

## 2. Ce qui a été construit

### 2.1 Un moteur d'écrans déclaratif — `web/ecrans.js` (2 092 lignes)

Plutôt que 43 pages HTML copiées, un moteur unique décrit chaque écran par des
données : source, colonnes, formulaire, actions, état vide. Il fournit :

| Fonction | Comportement réel |
|---|---|
| Liste | chargement depuis une URL serveur, colonnes typées (date, montant, booléen, badge) |
| Recherche | plein texte sur toutes les colonnes, insensible à la casse |
| Filtres | un filtre par colonne à valeurs discrètes, cumulables avec la recherche |
| Tri | clic sur l'en-tête, bascule croissant/décroissant |
| Pagination | 25 lignes par page, compteur total |
| Formulaire | création et modification, champs requis, types text/number/date/email/select/checkbox/textarea, prise en charge des attributs libres (`attributs.*`) |
| Validation | côté client (champs obligatoires) **et** côté serveur (schémas Pydantic) |
| Actions | contextuelles par ligne ou globales, POST/PUT/DELETE, confirmation, affichage du verdict serveur |
| Export | CSV généré à partir des lignes réellement affichées |
| États | squelette de chargement, erreur avec « Réessayer », vide professionnel avec action de démarrage |
| Droits | `peutEcrire()` lit `/api/rbac/moi` ; le serveur re-vérifie systématiquement |

Le moteur n'invente jamais de donnée : une collection vide affiche un état vide
explicite et propose l'action de démarrage.

### 2.2 Quarante-trois écrans métier branchés sur l'API existante

| Rubrique | Écrans livrés |
|---|---|
| Contrôle & conformité | contrôle documentaire, comparaison, historique, règles |
| Opérations maritimes | escales, voyages, échéances |
| Douane & réglementation | contrôles, liquidation, paiements, autorisations, référentiel |
| Enlèvement & livraison | sortie portuaire, livraison, preuves, suivi |
| Finance & facturation | frais de dossier, débours, factures fournisseurs, facturation, paiements, rapprochement, clôture |
| Rapports | statistiques, exports |
| Référentiels | clients, fournisseurs, transporteurs, navires, ports, pays, devises, types de marchandises, tarifs, règles documentaires, paramètres métier, types de documents |
| Administration | permissions, équipes, catalogue des référentiels, configuration générale, configuration OCR |

Chaque écran est atteignable depuis le menu (99 sous-items au total, contre 81)
et depuis le parcours métier. Aucune route fantôme : les 43 écrans sont mappés
sur des routes serveur existantes, vérifiées automatiquement.

### 2.3 Un back-end de référentiels réellement persistant

`src/unocr/routes/referentiels.py` expose douze collections sous
`/api/referentiels` : catalogue avec totaux, liste avec recherche, CRUD complet.

- persistance dans `data/referentiels.json`, écriture atomique
  (`.json.tmp` + `os.replace`) ;
- unicité du code par collection (409 avec message explicite) ;
- audit de chaque écriture (`referentiel_cree`, `referentiel_modifie`,
  `referentiel_supprime`) ;
- configuration relue à chaque appel : les tests et les déploiements à
  répertoire variable écrivent là où l'application est configurée.

### 2.4 Design system — `web/uniocr-ds.css` §31

Un seul socle visuel pour les écrans : fil d'Ariane, en-tête, barre d'outils,
tableau triable, pagination, squelettes, états vides, surcouche de formulaire.
Thème sombre par défaut, **thème clair** complet, responsive sous 720 px,
animations supprimées sous `prefers-reduced-motion`.

## 2.5 Passe 2 — dossiers et espace de travail (même journée)

La matrice de la passe 1 laissait 14 entrées de menu en simple redirection :
elles ouvraient la vue d'ensemble du module avec un bandeau « pas encore
d'écran dédié ». Elles sont traitées, sans dupliquer ce qui existait déjà :

| Entrée | Traitement |
|---|---|
| Dossiers en cours / bloqués / clôturés | **écrans dédiés** (`web/ecrans.js`) filtrant `GET /api/dossiers` sur les états réellement présents : `en_preparation`, `archive`, et pour « bloqués » les dossiers **signalés par le contrôle** (croisement avec `/api/dashboard/alertes`, aucune notion inventée) |
| Mes tâches | écran dédié : dossiers en révision ou incomplets (file de travail) |
| En attente de pièces | écran dédié : dossiers ouverts sans aucune pièce reçue |
| Mes alertes | écran dédié sur `/api/dashboard/alertes`, chaque alerte ouvrant son dossier |
| Dossiers récents | écran dédié : 30 derniers dossiers par date d'ouverture |
| Tous les dossiers / Nouveau dossier | reliés à l'espace dossier existant (`#tab-dossiers`) : la création utilise le dialogue `#dos-create`, qui s'ouvre automatiquement |
| Clients (vue dossiers) | relié à la page clients existante `#tab-clients` |
| À valider | relié à la page existante `#tab-validation` |
| Profils / Paramètres / Graphiques | reliés aux pages existantes `#tab-profiles`, `#tab-params-gen`, `#tab-reports` |

Résultat mesuré : **plus aucune entrée de menu n'affiche le bandeau**. Les
compteurs affichés viennent tous du serveur (164 dossiers bloqués, 186 tâches,
435 dossiers en attente de pièces, 30 dossiers récents au moment de la mesure).

Deux ajustements d'ergonomie de données ont été faits au passage :

- les écrans **rechargent leur source à chaque entrée** (le cache ne sert plus
  qu'au tri, au filtre et à la pagination) : une création faite dans un autre
  écran est visible immédiatement, ce qui répond à l'exigence de cohérence ;
- une action de ligne peut désormais être une **navigation** (« Ouvrir » un
  dossier) sans passer par une requête d'écriture.

## 3. Défauts corrigés en route (trouvés par les tests, pas par hasard)

Le garde-fou `tests/test_route_ordering.py` (ajouté dans cette passe) détecte
les routes littérales **masquées** par une route paramétrique déclarée plus tôt.
Il a révélé trois endpoints déclarés mais inaccessibles, qui répondaient 404 :

| Endpoint | Cause | Conséquence |
|---|---|---|
| `GET /api/declarations/liquidation` | `/api/declarations/{declaration_id}` déclarée avant | liste des liquidations inaccessible |
| `GET /api/frais/facture` | `/api/frais/{frais_id}` déclarée avant | liste des factures inaccessible |
| `GET /api/workflow/workflow/template` | `/api/workflow/workflow/{dossier_id}` déclarée avant | modèle de workflow inaccessible |

Les trois routes ont été réordonnées ; le garde-fou passera au rouge si une
nouvelle route littérale est masquée.

À noter pour la suite : la version de FastAPI installée n'aplatit plus les
routeurs inclus (`_IncludedRouter`). Un test qui parcourt `app.routes`
directement ne voit que les routes déclarées dans `api.py` — d'où le helper
`tests/_routes.py`, qui parcourt l'arborescence complète (314 entrées,
216 chemins OpenAPI, 302 opérations).

## 4. Décisions assumées

1. **Un moteur déclaratif plutôt que 43 pages HTML.** L'index est déjà à
   202 Ko (plafond 220 Ko) : dupliquer un gabarit par écran n'était pas
   tenable. Le moteur rend chaque écran par données, ce qui garantit que les
   états vide/erreur/chargement et les permissions sont identiques partout.
2. **Aucune donnée fictive.** Les collections vides le restent ; les écrans
   affichent un état vide avec l'action de démarrage.
3. **Écritures gardées par le serveur.** L'UI masque les boutons, le serveur
   applique le RBAC : masquer un bouton n'est jamais la sécurité.
4. **Statuts honnêtes.** Un écran hérité non re-testé reste **PARTIEL**, même
   s'il « a l'air » fini. La matrice le dit explicitement.

## 5. Ce que ces passes ne font pas

- Les **57 écrans partiels** restent à re-certifier un par un (contenu, actions,
  permissions, états vides) : voir `FONCTIONNALITES_RESTANTES.md`.
- Certains écrans **réutilisent une page historique** (`#dossiers/tous`,
  `#tab-clients`, `#tab-profiles`…) : plus de bandeau, mais le contenu et les
  actions restent ceux de la page héritée, non re-testés.
- Les **actions contextuelles** (analyse de contrôle, rapprochement, sortie
  portuaire) sont branchées mais pas encore couvertes par un test automatisé.
- **Aucune comparaison** avec un ERP externe : aucun connecteur métier réel
  n'est disponible sur ce poste (voir limitations dans
  `FONCTIONNALITES_RESTANTES.md`).
