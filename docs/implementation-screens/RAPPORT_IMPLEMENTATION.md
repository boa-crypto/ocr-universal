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

## 2.6 Passe 3 — Documents & OCR

Audit des 14 sous-rubriques du module. Trois n'avaient aucun écran propre :

| Entrée | Avant | Maintenant |
|---|---|---|
| Vue d'ensemble | retombait sur l'atelier (`#tab-dashboard`) | **écran dédié** : file de traitement réelle (`GET /api/jobs`, 200 documents), filtres par état, moteur, progression |
| Extraction OCR | même repli | **écran dédié** avec trois actions serveur exercées par test : *Texte* (`GET /api/jobs/{id}/text`), *Résultat* (`…/result`), *Relancer* (`POST …/retry`) |
| Scanner / Importer | page d'accueil quasi vide (`#tab-import`, 1 Ko, aucun contrôle) | relié à l'atelier de capture réel (`#tab-dashboard` : import fichier, caméra, lot, options) |

La page `#tab-import` — coquille d'accueil sans aucun contrôle — a été retirée
de la coque HTML et de la table de routes ; sa fonction est portée par l'atelier.
L'index passe de 202 à 201 Ko pour un plafond de 220 Ko.

Deux défauts d'ergonomie corrigés au passage :

- **le panneau de résultat était effacé** : une action de lecture affichait la
  réponse puis rechargeait la liste, ce qui remplaçait le panneau. Les actions
  de lecture ne rechargent plus ; les actions d'écriture affichent leur verdict
  *après* le rechargement ;
- **les clés imbriquées** (`options.engine`) n'étaient pas lisibles par les
  colonnes, les filtres ni le tri : un accesseur de clé pointée a été ajouté,
  ainsi qu'un format « progression » (pourcentage).

## 2.7 Passe 4 — actions réellement exercées

Trois écrans à actions sont passés du statut « partiel » à « conforme » parce
que leurs actions ont été **exécutées contre le serveur**, pas seulement
inspectées :

| Écran | Actions exercées | Résultat |
|---|---|---|
| Contrôle documentaire | *Contrôler* (`POST /api/controle/analyser`), *Verdict* (`GET /api/controle/{dossier}/statut`) | 200 + panneau de verdict |
| Extraction OCR | *Texte*, *Résultat*, *Relancer* | 200 ; 409 correctement affiché sur un document non terminé |
| Rapprochement financier | *Lancer le rapprochement* (`POST /api/frais/rapprochement/auto`) | 200 + verdict serveur |

Ce dernier a révélé un **vrai défaut** : l'action envoyait une requête vide et
le serveur répondait 422 (le rapprochement exige un dossier et une période).
Le moteur dispose maintenant d'un **dialogue d'action paramétrée** : l'écran
demande les champs requis par l'API, les valide, puis envoie la requête. Le
même mécanisme servira aux actions qui exigeront un motif ou un commentaire.

Limite signalée dans l'écran et dans la matrice : le rapprochement bancaire
n'a **aucun flux bancaire** côté serveur (l'import est un TODO explicite dans
`frais.py`). L'écran le dit et n'invente aucun rapprochement.

## 2.8 Passe 5 — re-certification des écrans Documents hérités

Cinq écrans historiques ont été **exercés** dans un navigateur simulé, pas
seulement regardés :

| Écran | Ce qui a été vérifié | Statut |
|---|---|---|
| Boîte de réception (`#tab-center`) | 25 lignes réelles, recherche 25 → 0, pagination | CONFORME |
| Classification (`#tab-classif`) | 21 catégories réelles (`/api/document-types`), recherche | CONFORME |
| Archives / GED (`#tab-ged`) | 25 lignes filtrées sur `archive`, recherche, pagination, « Ouvrir » → dossier | CONFORME |
| Vérification (`#tab-validation`) | 25 lignes, recherche, pagination, « Ouvrir » → dossier | CONFORME |
| Révision humaine (`#tab-review`) | file chargée automatiquement, champs réels, « Actualiser » → 200 | CONFORME |

Deux vrais défauts trouvés au passage :

1. **La file de révision ne se chargeait jamais à l'ouverture.** La page était
   conçue pour être ouverte par un clic d'onglet (ancienne coque) ; atteinte
   par le routage au hash, elle restait vide jusqu'à « Actualiser ». Elle
   s'auto-charge désormais quand la route devient `documents/revue`.
2. **Une erreur de rendu était présentée comme « API non jointe ».** Le
   `catch` masquait la cause ; il journalise maintenant l'erreur réelle et
   l'affiche. C'est ce qui a permis d'identifier un `scrollIntoView` absent
   (navigateurs anciens et tests), désormais appelé seulement s'il existe.

Les écrans **résultat, qualité, profils, connecteurs, configuration** restent
PARTIEL : ils dépendent d'un document sélectionné ou exposent des écritures
(profils, connecteurs) qui n'ont pas encore été exercées.

## 2.9 Passe 6 — enlèvement et livraison : les cinq transitions exercées

Les écrans **Sortie portuaire** et **Livraisons** étaient marqués partiels pour
une raison précise : aucune donnée d'exploitation, donc aucune action
exécutable. Un jeu d'essai a été créé **par l'API** (un enlèvement, une
livraison), les actions ont été jouées dans l'interface, puis les
enregistrements ont été supprimés. Rien n'est simulé côté écran.

| Action | Requête réellement émise | Résultat |
|---|---|---|
| Autoriser la sortie | `POST /api/terminal/{id}/autoriser_sortie?mainlevee_obtenue=true&bad_obtenu=true&frais_portuaires_payes=true&justificatif_sortie=…` | 200 + liste rechargée |
| Enregistrer la sortie | `POST /api/terminal/{id}/sortie?date_sortie=2026-11-04` | 200 |
| Démarrer | `POST /api/transport/livraisons/{id}/demarrer?date_depart=2026-11-04` | 200 |
| Arrivée | `POST /api/transport/livraisons/{id}/arriver?date_reelle=2026-11-04` | 200 |
| Confirmer | `POST /api/transport/livraisons/{id}/confirmer?preuve_signee=true&date_signature=2026-11-04` | 200, puis preuve visible |

### Défauts corrigés

1. **Ces cinq actions renvoyaient 422.** Le serveur attend des paramètres
   d'URL (scalaires FastAPI), l'écran envoyait un corps JSON vide. Le moteur
   sait maintenant construire la *query string* (`emplacement: "query"`) et
   chaque action déclare ses champs : dates préremplies au jour, conditions
   portuaires en oui/non, justificatif obligatoire.
2. **La table des livraisons affichait quatre colonnes inexistantes**
   (`numero_conteneur`, `date_planifiee`, `adresse_livraison`,
   `date_confirmation`) : cellules vides en production. Remplacées par les
   champs réels du modèle (`lieu_livraison`, `camion_id`, `date_prevue`,
   `date_reelle`, `reserves_eventuelles`).
3. **L'écran Preuves de livraison ne pouvait rien afficher** : son filtre
   cherchait « livr » dans un statut qui vaut `confirme`. Il s'appuie désormais
   sur `preuve_livraison_signee` / `date_signature` — la preuve réelle du
   serveur. Vérifié : la livraison confirmée apparaît avec « Oui » et sa date.

## 2.10 Passe 7 — administration : contrôles morts et routage

| Écran | Constat mesuré | Correction |
|---|---|---|
| Moteurs OCR (`#admin/moteurs-ocr`) | la route `admin/moteurs` **n'existait pas** dans la carte : l'écran affichait la page Administration générique | route ajoutée ; l'écran rend les 6 moteurs réels (disponibilité, actif, RAM) |
| Workflows | **bouton « + Nouveau workflow » sans gestionnaire** : aucun script ne le référençait | dialogue de création → `POST /api/rbac/workflows` 200, liste rechargée, ligne visible |
| Journal d'audit | barre de filtres et bac « Chargement… » **jamais pilotés** ; le bac restait affiché indéfiniment | contrôles morts retirés, la liste réelle (recherche + pagination) occupe la page ; état vide explicite |
| Rôles | 9 rôles réels affichés | lecture seule assumée |
| Sauvegardes | 8 sauvegardes réelles (nom, taille, date) | liste vérifiée ; **création non exercée** : l'API purge au-delà de 5 et les 8 archives sont suivies par git — le risque de perte est réel |
| Utilisateurs | `actif: false`, liste vide → état vide honnête | reste PARTIEL : aucun écran de création/modification d'utilisateur |

## 2.11 Passe 8 — profils d'extraction et rapports

### Profils d'extraction (`#documents/profils`, `#referentiels/profiles`)

L'éditeur existait de bout en bout mais n'avait jamais été exercé. Parcours
réel, mesuré :

| Étape | Requête | Résultat |
|---|---|---|
| Liste | `GET /api/profiles` + `/api/profiles/catalog` | **11 profils** réels (carte grise, facture…) |
| Création | `PUT /api/profiles/profil_essai_ui` (1 champ, motif `FACTURE\s*(\S+)`) | **200** — « enregistré (1 champ) » |
| Essai à blanc | `POST /api/profiles/test` sur « FACTURE 2026-0421… » | **1/1 champ détecté**, valeur extraite `2026-0421` |
| Suppression | `DELETE /api/profiles/profil_essai_ui` | **200** — retour à 11 profils |

Correctif mineur : le message affichait « 1 champs ».

### Rapports (`#rapports`, `#rapports/graphes`)

Les **7 graphiques** sont réels (dossiers par état 715, anomalies 46, série
financière…), rendus en SVG par `web/rapports.js`. Mais la page conservait
**trois boutons sans aucun gestionnaire** (« Voir les statistiques », « Voir les
graphiques », « Exporter les données ») et un attribut HTML cassé
(`<div classpage-header__meta>`). Remplacés par deux liens vers des écrans
réellement existants ; le balisage est corrigé.

### Exports (`#rapports/exports`)

Actions de téléchargement exercées : `GET /api/jobs/{id}/export/csv` → **200**
(toast « Export téléchargé »), `export/json` → **200** (96 Ko vérifiés).

## 2.12 Passe 9 — référentiels : un 500, un contrat d'API faux, neuf CRUD exercés

### Le 500 qui cachait un 422

Créer un client depuis l'écran avec « Algérie » dans le champ Pays renvoyait
une **erreur 500** (`Internal Server Error`, sans corps). Cause : le modèle
`Client` limite `country` à deux caractères (ISO 3166-1), mais le corps de
requête ne le vérifiait pas — la construction du modèle levait une
`ValidationError` non rattrapée.

Corrections : contrainte `max_length=2` sur le corps (`ClientCreate` /
`ClientUpdate`) et garde-fou `ValidationError → 422` avec un message lisible.
L'écran, lui, bride le champ à deux signes, propose `DZ` par défaut et
explique le format. Vérifié : `country: "Algérie"` → **422** nommant le champ,
`country: "DZ"` → **200**.

### L'écran Fournisseurs parlait une autre langue que l'API

L'écran envoyait `name`, `country`, `status` ; l'API attend `nom`,
`nom_commercial` (obligatoire), `pays`. **Toute création renvoyait 422.** Les
colonnes, la création et l'édition ont été réalignées sur le modèle réel.

### Neuf CRUD exercés de bout en bout

Un harnais jsdom générique ouvre chaque écran, remplit les champs obligatoires,
crée, édite quand l'action existe, puis supprime. Résultats mesurés :

| Écran | Création | Édition | Suppression |
|---|---|---|---|
| Clients | POST 200 | PUT 200 (ville modifiée) | DELETE 200 |
| Fournisseurs | POST 200 | PUT 200 | DELETE 200 |
| Transporteurs | POST 200 | — | DELETE 200 |
| Navires | POST 200 | — | DELETE 200 |
| Permissions | POST 200 | — | DELETE 200 |
| Voyages (expéditions) | POST 200 | — | DELETE 200 |
| Contrôles douaniers | POST 200 | PUT 200 | DELETE 200 |
| Liquidation | POST 200 | — | DELETE 200 |
| Frais du dossier | POST 200 | PUT 200 | DELETE 200 |
| Factures fournisseurs | POST 200 | — | DELETE 200 |
| Facturation client | POST 200 | PUT 200 | DELETE 200 |

### La matrice ne s'accorde plus de crédit

Règle durcie : un écran doté d'un CRUD déclaré **n'est plus « conforme » par
simple déclaration** — il faut une preuve d'exercice (`PREUVES`). Effet
immédiat et assumé : 9 écrans sont repassés en « partiel » le temps de les
exercer, puis sont revenus en « conforme » avec leur mesure. Le total reste
63 conformes / 37 partiels, mais chaque « conforme » de type CRUD a maintenant
une ligne de test derrière lui.

## 2.13 Passe 10 — résultat d'analyse et contrôle qualité reliés

Ces deux écrans affichent **le document courant**, mais aucun chemin de la
nouvelle coque ne le désignait : atteints par le routage au hash, ils
restaient vides (viewer « — », jauges « — »), sans explication.

Mise en place d'un point d'entrée unique :

| Élément | Comportement |
|---|---|
| Action « Ouvrir le résultat » sur la liste des documents | refusée si le document n'est pas `done` (message « Document non traité »), sinon charge `/api/jobs/{id}/result` et bascule sur l'écran |
| Écran « Résultat d'analyse » | texte réel du document, pagination, badges langue/variante, recherche dans le texte |
| Écran « Contrôle qualité » | jauges alimentées par le même document (moteur, global, anomalies) |
| Aucun document ouvert | message explicite orientant vers « Vue d'ensemble » / « Extraction OCR », au lieu de tirets |

Mesures jsdom :

- document `bl_port.pdf` (`done`) → `GET /result` **200**, texte « BILL OF
  LADING / B/L No: MSCU123456789… » affiché ;
- page qualité ensuite → moteur **100 %**, **3 anomalies** ;
- document `queued` → action refusée, **aucune requête** émise ;
- aucun document → message d'état vide sur les deux écrans.

## 2.14 Passe 11 — créer le premier utilisateur (RBAC)

La page « Gestion des utilisateurs » affichait « Aucun utilisateur pour
l'instant » et ne proposait **aucun moyen d'en créer un** : le cloisonnement
RBAC ne pouvait donc jamais s'activer depuis l'interface.

L'écran déclaratif `#admin/utilisateurs` remplace la page héritée :

| Élément | Détail |
|---|---|
| Source | `/api/rbac/utilisateurs` (clé `utilisateurs`), colonnes utilisateur, rôles, dossiers, jeton d'environnement |
| Création | identifiant + **rôles** et **dossiers** saisis en listes (nouveau type de champ `liste` : « a, b » → `["a","b"]`) |
| Jeton | le serveur ne le renvoie **qu'une fois** : il est affiché dans un panneau aussitôt après la création, avec l'avertissement qu'il n'est plus relisible |
| Édition / suppression | rôles et périmètre modifiables, révocation immédiate à la suppression |
| État vide | explique que le cloisonnement est inactif et propose « Créer un utilisateur » |

Mesures (serveur isolé, jeu de données temporaire, jamais le poste de travail) :

- état vide explicite + bouton de création ;
- création `karim.b` avec `superviseur, agent_de_transit` → **POST 200**, ligne
  affichée avec les deux rôles, jeton affiché une seule fois ;
- édition des rôles → **PUT 200**, ligne mise à jour ;
- suppression → **DELETE 200**, retour à l'état vide.

La page héritée `#tab-utilisateurs` a été retirée (section, définition de
sous-page, table de correspondance) : une seule page, un seul comportement.

## 2.15 Passe 12 — rôles : livrés contre personnalisés

La page « Rôles et permissions » n'affichait que le catalogue (9 rôles) en
lecture seule : impossible de créer un rôle propre à l'exploitation, alors que
`/api/rbac/roles` le permet.

L'écran déclaratif fusionne deux sources et **distingue l'origine** :

| Origine | Contenu | Actions proposées |
|---|---|---|
| **livré** | 9 rôles du catalogue (`roles_disponibles`) | aucune — un rôle livré ne se modifie pas |
| **personnalisé** | rôles du magasin RBAC | Modifier, Supprimer |

Mesures jsdom : 9 lignes livrées **sans bouton** ; création `chef_escale`
(niveau 2, permissions « ecriture, export ») → **POST 200**, ligne marquée
« personnalisé » avec ses deux boutons ; édition → **PUT 200** ; suppression →
**DELETE 200**, retour à 9 lignes.

Le moteur gagne le **masquage d'action par ligne** (`masquer(ligne)` sur
`edition`, `suppression` et chaque action) : c'est ce qui garantit qu'aucune
action destructrice n'est offerte sur un rôle livré.

## 2.16 Passe 13 — la matrice ne compte plus de page fantôme

La passe 12 laissait 67 écrans conformes sur 100 entrées. Le reste ne se
corrige pas en écrivant du code : il faut aller mesurer chaque écran, puis
décider s'il mérite d'exister.

### Une page qui ne pouvait pas sauvegarder

`#referentiels/parametres` affichait un formulaire « Paramètres généraux »
pré-rempli de trois valeurs. Vérification faite, la page **n'émettait aucun
appel d'écriture** : `Config` n'expose ni `set` ni persistance, et le moteur
hérité (`app-extras.js`) ne branchait rien sur le bouton. Un écran qui accepte
une saisie sans jamais l'enregistrer est pire qu'une absence : il donne la
fausse impression que la configuration est réglée.

La page a donc été **supprimée** (entrée de menu, route, correspondance
`tab-params-gen`, section HTML : `index.html` passe de 195 à **191 Ko**).
Les paramètres réellement applicables restent exposés, mais en **lecture
seule et honnêtes** : `#admin/parametres` (chiffrement, sécurité, traçabilité),
`#admin/parametres-ocr` (surveillance des dossiers) et `#documents/configuration`
(moteurs disponibles : `tesseract` signalé « non installé », `native_pdf` actif).
La vraie sauvegarde des paramètres généraux est inscrite en **P0-4** plutôt
que maquillée.

### « Clients » ne renvoyait plus nulle part

`#dossiers/clients` basculait sur `tab-clients`, une page héritée tellement
ancienne qu'elle ne rendait **aucune ligne, aucun bouton** : l'entrée de menu
« Clients » du module Dossiers était morte. L'écran déclaratif Clients
(`référentiels/clients`, CRUD exercé en passe 9) est maintenant aliasé sous
`dossiers/clients` : trois boutons (Nouveau, Exporter CSV, Créer un client) et
un état vide explicite — « Aucun client enregistré. Créez le premier pour
rattacher des dossiers. »

### Mesurer au lieu de supposer

Les 20 partiels restants n'étaient pas cassés : ils n'étaient **pas mesurés**.
Un harnais jsdom a donc parcouru chaque hub et chaque liste, en comptant liens,
cartes, compteurs et appels API :

| Écran | Mesure |
|---|---|
| `#cockpit` | 3 liens, 6 cartes, 25 compteurs (`/api/dashboard/*`) |
| `#workspace`, `#workspace/valider` | 5 cartes, 24 compteurs ; 25 lignes à valider (185 en attente) |
| `#dossiers/tous` | 40 lignes, compteurs 715 / 666 / 185 / 49 |
| `#dossiers/nouveau` | dialogue de création → **POST /api/dossiers 200** |
| `#controle`, `#controle/manquants`, `#controle/anomalies` | 10 liens, 11 cartes ; 25 lignes (164 pièces / 164 anomalies) |
| `#maritime`, `#douane`, `#enlevissement`, `#finance` | 11 / 12 / 10 / 10 liens, 6 / 2 / 2 / 1 sources API |
| `#referentiels`, `#admin` | 16 liens chacune, 16 et 23 cartes |
| `#admin/connecteurs-api` | 3 connecteurs configurés |
| `#douane/paiements` | liquidation réelle créée, « Marquer payée » → **PUT 200** |

Deux écrans seulement ne pouvaient pas être soldés :

- `#finance/cloture` : l'action « Archiver » est branchée, mais l'archivage est
  **irréversible** et les dossiers de démonstration sont suivis par git. La
  matrice le déclare **PARTIEL** avec sa raison, plutôt que de le certifier
  sans l'avoir exercé.
- « Connecteur Hub » vers un service distant : aucun service externe sur ce
  poste, l'écran expose l'état réel des connecteurs et le dit.

Résultat : **99 entrées, 98 conformes, 1 partiel, 0 absent, 0 non connecté**
(contre 67 conformes en début de passe).

## 2.17 Passe 14 — des paramètres qui s'appliquent vraiment

La passe 13 avait supprimé la page « Paramètres généraux » : son formulaire
n'enregistrait rien. Supprimer ne suffisait pas — un poste sans réglage reste
un poste qu'on ne peut pas exploiter. Cette passe rend la fonction réelle.

### Ce qui est écrit, et où

`PUT /api/parametres/{cle}` écrit dans **`data/parametres.json`**, jamais dans
`config/default.json` : une mise à jour du projet ne doit pas écraser les
réglages d'exploitation, et un réglage d'exploitation ne doit pas réécrire les
défauts livrés. Le fichier est relu au démarrage ; l'effet est aussi immédiat
en mémoire, sans redémarrage.

Sept réglages sont exposés — **uniquement ceux que le code lit réellement**,
chacun accompagné de l'effet qu'il produit :

| Réglage | Effet appliqué | Bornes |
|---|---|---|
| Taille maximale d'un fichier | refus à l'import (413) | 1–500 Mo |
| Taille maximale d'un lot | plafond de l'import groupé | 1–2000 Mo |
| Pages maximales | pages lues dans un PDF | 1–5000 |
| Rétention des jobs | purge des jobs terminés | 1–3650 jours |
| ZIP décompressé / ratio | garde-fous de décompression | 1–5000 Mo · 1–1000:1 |
| Langues OCR par défaut | langues proposées au moteur | codes de 3 lettres |

Les réglages lus nulle part (`ocr.tesseract_psm`) ont été **écartés** : les
afficher aurait reproduit le défaut corrigé en passe 13.

### La validation nomme le champ

Une valeur hors bornes ne produit pas un 500 ni un message générique :

```
PUT /api/parametres/max_file_size_mb  {"valeur": 9999}
422 {"detail": {"champ": "max_file_size_mb",
                "message": "Taille maximale d'un fichier : maximum 500 Mo (reçu 9999)."}}
```

L'écran réaffiche ce message tel quel et **laisse le dialogue ouvert** : la
saisie fautive n'est pas perdue. Les langues sont normalisées (`FRA, eng` →
`fra, eng`) et refusées si un code ne fait pas trois lettres.

### La preuve par l'effet

Les tests ne se contentent pas du code HTTP : ils vérifient que le serveur
change de comportement.

- limite à 1 Mo → import d'un PDF de 2 Mo : **413** « fichier trop volumineux » ;
- limite rétablie à 50 Mo → même fichier : **200**, job créé ;
- `DELETE /api/parametres/{cle}` rétablit la valeur livrée, et une seconde
  réinitialisation renvoie **409** plutôt qu'un faux succès ;
- fichier de réglages corrompu → le serveur démarre quand même sur les défauts.

Mesures jsdom : 7 lignes, colonne « État » (`défaut` / `modifié`), édition
`PUT 200` (valeur 42 affichée), « Rétablir le défaut » `DELETE 200`, saisie
9999 → message d'erreur affiché, dialogue maintenu.

La matrice repasse à **100 entrées : 99 conformes, 1 partiel** (l'archivage
irréversible de `#finance/cloture`).

## 2.18 Passe 15 — les référentiels entrent dans les formulaires

Les référentiels (pays, ports) existaient, se remplissaient, et ne servaient
à rien : les formulaires métier demandaient le pays ou le port en texte libre.
Saisir « DZ » ici et « Algérie » là produit des listes qui ne se recoupent
jamais.

### Ce qui change dans les formulaires

Un champ peut désormais déclarer `referentiel: "pays"`. Le moteur interroge
`/api/referentiels/{nom}`, alimente une **`<datalist>`** et affiche ce qu'il a
trouvé :

- *1 entrée proposée depuis le référentiel « pays »* — la suggestion est là ;
- *Référentiel « pays » vide : saisie libre. Ajoutez des entrées dans
  Référentiels pour les proposer ici.* — la liste vide est dite, pas subie.

Le champ reste un champ texte : un port absent du référentiel n'empêche pas de
créer un dossier. **Relier n'est pas verrouiller.**

### Où c'est branché

| Écran | Champ | Référentiel |
|---|---|---|
| Clients (création) | Pays (ISO 2 lettres) | `pays` |
| Fournisseurs (création) | Pays (ISO 2 lettres) | `pays` |
| Navires (création) | Pavillon | `pays` |
| Dossier → Créer (`#dossiers/nouveau`) | Port de chargement / destination | `ports` |

Le dialogue de création de dossier charge les ports à l'ouverture et le dit :
*1 port proposé par le référentiel* (ou *référentiel des ports vide : saisie
libre*). Le référentiel est interrogé une fois par session, pas à chaque
frappe.

### Mesures

- pays `DZ` créé par l'API → formulaire Client : `list` renseigné, option `DZ`,
  note « 1 entrée proposée » ; après suppression de l'entrée, note « vide :
  saisie libre » ;
- port `DZORAN` créé → dialogue de dossier : « 1 port proposé », option
  `DZORAN` ; sans entrée : message explicite, zéro option ;
- aucune erreur réseau dans les deux cas ; entrées d'essai supprimées.

## 2.19 Passe 16 — l'historique d'un document, tiré du journal d'audit

Le journal d'audit enregistrait déjà chaque étape (document reçu, classé,
analysé, champs validés, rattachement à un dossier) mais **rien ne le lisait
par document**. L'écran de révision montrait un état sans son passé : qui a
corrigé ce champ, quand, et pourquoi le document est-il dans cet état ?

### Une route qui lit, pas qui invente

`GET /api/jobs/{job_id}/historique` parcourt `logs/audit.log`, ne garde que
les lignes de ce document et les présente dans l'ordre chronologique, avec un
vocabulaire lisible :

| Événement du journal | Ce que l'écran affiche |
|---|---|
| `job_created` | **Document reçu** — fichier, taille, profil |
| `document_classified` | **Document classé** — catégorie et confiance |
| `job_done` | **Analyse terminée** — pages, confiance moyenne |
| `field_validated` | **Champ validé** (ou **corrigé**) — champ et valeur |
| `dossier_piece_added` | **Rattaché à un dossier** — dossier concerné |

Trois détails qui comptent :

- un événement **inconnu n'est pas masqué** : il apparaît avec son nom brut,
  parce qu'un historique troué est pire qu'un historique technique ;
- les **lignes illisibles** du journal sont comptées et signalées, pas passées
  sous silence ;
- un document **sans événement** répond 200 avec un message qui explique
  pourquoi (document antérieur au journal, ou identifiant inconnu) — un 404
  aurait seulement dit « perdu ».

### Une chronologie, pas du JSON

L'action « Historique » de `#documents/ocr` affiche une frise : horodatage,
libellé, détail, acteur. Le moteur sait maintenant deux rendus d'action —
`afficher` (JSON brut, pour les charges techniques) et `timeline` (frise).
Le premier jet tombait dans le panneau JSON : corrigé, et couvert par un test.

### Mesures

- document `bl_port.pdf` : **7 événements** dans l'ordre, du 29/10 (réception,
  classification à 91 %, analyse à 76 %) à la validation de champ du jour ;
- validation d'un champ par l'API → l'événement **apparaît immédiatement** dans
  la frise (« Champ validé — date confirmé, par utilisateur ») ;
- document inconnu : 200, message explicite, zéro ligne ;
- `tests/test_historique.py` : 5 tests (ordre, filtrage par job, valeurs,
  événement inconnu, lignes illisibles).

## 2.20 Passe 17 — un lecteur ne peut rien écrire (et le dit)

La politique d'écriture existait dans le code : `_role_requis` exige au moins
`operateur` sur toute méthode d'écriture, `administrateur` sur l'administration,
les connecteurs, les sauvegardes et les rôles. Elle n'était **prouvée qu'à la
main**, sur un serveur isolé. Une réutilisation pouvait la casser sans que
rien ne le signale.

### Ce que les tests exercent

`tests/test_rbac_ecritures.py` installe un registre RBAC **dans un répertoire
temporaire** (le poste de travail n'est jamais cloisonné), puis essaie
**quatorze écritures**, une par famille :

| Famille | Écriture essayée |
|---|---|
| Clients / fournisseurs | `POST`, `DELETE` |
| Référentiels | `POST /api/referentiels/pays` |
| Paramètres | `PUT /api/parametres/max_pages` |
| Dossiers | `POST /api/dossiers` |
| Frais | `POST /api/frais` |
| Documents | `PATCH /api/jobs/{id}/fields/{nom}`, `POST …/retry` |
| Administration | `POST/DELETE /api/rbac/utilisateurs`, `POST /api/admin/cleanup` |
| Connecteurs / sauvegardes | `POST /api/connectors/{id}/test`, `POST /api/backups` |

Chaque tentative, avec un jeton `lecteur`, renvoie **403** *et* laisse une
entrée `acces_refuse_role` dans le journal, nominative. Un refus muet ne se
distingue pas d'un bug : il est tracé.

### Deux précautions de méthode

- **Charges invalides, identifiants inexistants.** Un 422 ou un 404 prouve que
  le contrôle de rôle a laissé passer **sans rien écrire** ; aucun jeu de
  données n'est créé par la suite de tests.
- **Le poste reste ouvert.** Le fichier de rôles vit dans `tmp_path` et le
  registre est rechargé à la fin : hors RBAC, la dernière assertion vérifie
  qu'une écriture invalide répond 422 (validée), pas 403 — comportement
  historique conservé.

Résultat : **18 tests verts**, dont 14 refus attendus, la lecture autorisée
(`/api/health`, `/api/stats`, `/api/clients`, `/api/parametres` en 200), et la
distinction opérateur/administrateur.

## 2.21 Passe 18 — « Graphiques » devient un écran

L'entrée de menu « Graphiques » ouvrait la page « Rapports » : un titre, deux
boutons, aucune courbe. Six routes de graphiques existaient pourtant côté
serveur, calculées sur les vraies données et jamais appelées par l'interface.

### Ce que l'écran dessine

`#rapports/graphes` ouvre désormais une page dédiée (`web/graphiques.js`,
séries lues dans `/api/dashboard/graphique/*` et `serie-dossiers`) :

| Carte | Source | Rendu |
|---|---|---|
| Dossiers par état | `graphique/etat-dossiers` | barres horizontales |
| Activité (30 jours) | `serie-dossiers?jours=30` | courbes Créés / Traités / Clôturés |
| Répartition par port | `graphique/repartition-par-port` | anneau + légende |
| Principaux clients | `graphique/top-clients` | anneau + légende |
| Anomalies par type | `graphique/anomalies-par-type` | barres |
| Frais par gestionnaire | `graphique/fret-par-gestionnaire` | barres |

Un bandeau indique l'heure de lecture (« Séries à jour — 18:12 ») et
`Actualiser` relit les six séries ; les appels sont groupés, pas rejoués à
chaque navigation.

### Une série vide n'est pas un cadre muet

C'est le point qui distingue un graphique honnête d'une décoration. Sur cette
base de démonstration, trois cartes n'ont **rien** à tracer ; elles le disent :

- *« Tous les dossiers sont sans port renseigné : il n'y a rien à répartir
  (715 dossiers) »* ;
- *« Aucun client rattaché : renseignez le client importateur des dossiers »* ;
- *« Aucun frais imputé : les montants par gestionnaire restent à zéro »*.

Le module reconnaît aussi les valeurs de repli du serveur (`non défini`,
`inconnu`) : un anneau à une seule part « non défini » n'apprend rien, il est
remplacé par la phrase qui dit combien de dossiers sont concernés.

### Mesures

jsdom sur `#rapports/graphes` : page `tab-graphiques` visible, **3 séries
dessinées** (8, 98 et 10 éléments SVG) et **3 états vides expliqués**,
**6 appels API en 200**, aucune erreur réseau, bandeau à l'heure locale.
`web/index.html` : 196 → **198 Ko** (plafond 220 Ko). Matrice : 100 entrées,
la ligne « Graphiques » passe de « page historique » à **écran dédié**.

## 2.22 Passe 19 — la matrice passe à 100 conformes (et le mérite)

Depuis la passe 13, un écran restait **PARTIEL** : `#finance/cloture`. Son
action « Archiver » était branchée, mais jamais exercée. La raison invoquée
était prudente et juste : l'archivage est **irréversible**, et les dossiers de
démonstration sont suivis par git. Archiver l'un d'eux, c'est modifier une
donnée de référence pour toute l'équipe.

### La façon de le prouver sans rien abîmer

Un dossier **jetable** résout le problème : la suite crée
`Dossier archivage UI` (`ARCH-UI-1`) par l'API, l'archive depuis l'écran, puis
le supprime. Aucun dossier de démonstration n'est touché.

Mesure jsdom :

1. `#finance/cloture` → recherche `ARCH-UI-1` → **1 ligne** ;
2. clic sur « Archiver » → confirmation ;
3. `POST /api/dossiers/{id}/archiver` → **200** ;
4. relecture serveur : `state: archive`, libellé intact ;
5. `DELETE` du dossier d'essai → **200**, base de démonstration inchangée
   (715 dossiers).

### Pourquoi la ligne reste honnête

La déclaration dans la matrice n'est pas devenue « conforme » parce qu'un test
suffisait : la colonne « Action requise » porte désormais la contrainte réelle —
*« Archiver » est irréversible : confirmation demandée ; exercée depuis l'écran
sur un dossier d'essai, supprimé ensuite*. Le garde-fou est aussi dans l'écran :
le filtre exclut les dossiers déjà archivés, et l'action demande confirmation
(les deux sont vérifiés par `tests/test_ui_premium.py`).

**Matrice : 100 entrées, 100 conformes, 0 partiel, 0 absent, 0 non connecté.**

## 2.23 Passe 20 — les preuves deviennent rejouables

Les passes 13 à 19 ont mesuré chaque écran dans un navigateur simulé. Mais les
harnais vivaient dans `/tmp` : les preuves étaient vraies le jour où elles ont
été prises, et personne ne pouvait les rejouer. Une preuve qu'on ne peut pas
refaire n'est pas une preuve, c'est une anecdote.

### `tests/ui_smoke.js` — quinze vérifications, aucune écriture

Le harnais est désormais **dans le dépôt** (`npm install` puis
`npm run ui:smoke`), et il tient trois promesses :

| Vérification | Ce que cela attrape |
|---|---|
| 8 écrans critiques s'ouvrent avec leur section attendue | une route qui ne mène plus nulle part |
| `#documents/ocr` : clic « Historique » → chronologie | une action branchée mais muette |
| `#rapports/graphes` : 6 cartes, chacune dessinée **ou** expliquée | un graphique vide sans message |
| `#referentiels/parametres` : le formulaire s'ouvre avec son champ | un écran de réglages décoratif |
| `#dossiers/nouveau` : dialogue et champs présents | un bouton « Créer » sans formulaire |
| **aucune requête non-GET** | un test qui modifierait les données de l'utilisateur |
| **aucun 5xx** | une erreur serveur masquée par un état vide |
| **aucune erreur JavaScript** | une exception avalée par un `catch` |

Sortie réelle sur ce poste :

```
Écrans :
  ✓ #cockpit (tab-cockpit) — 2380 caractères
  ✓ #dossiers/tous (tab-dossiers) — 2587 caractères
  ✓ #documents/ocr (tab-ecran) — 2426 caractères
  ✓ #referentiels/parametres (tab-ecran) — 964 caractères
  ✓ #admin/utilisateurs (tab-ecran) — 403 caractères
  ✓ #rapports/graphes (tab-graphiques) — 1023 caractères
  ✓ #finance/cloture (tab-ecran) — 1567 caractères
  ✓ #douane/paiements (tab-ecran) — 316 caractères
Interactions :
  ✓ Historique d'un document — 1 événement(s)
  ✓ Graphiques — 6 cartes : 3 dessinée(s), 3 expliquée(s)
  ✓ Paramètres : formulaire — 7 réglage(s), champ valeur
  ✓ Création de dossier — 6 champ(s), 0 port(s) proposé(s)
  ✓ Aucune écriture émise — lecture seule
  ✓ Aucune erreur serveur — 0 × 5xx
  ✓ Aucune erreur JavaScript — 0 erreur

15/15 vérifications passées
```

### Un test qui dit quand il ne peut pas tourner

`tests/test_interface_jsdom.py` lance ce script depuis `pytest`. Il dépend de
deux choses extérieures (jsdom, un serveur en marche) : plutôt que de faire
semblant, il **saute explicitement** en nommant ce qui manque
(`jsdom absent : lancer npm install`, `aucun serveur sur …`). Quand les deux
sont là, il échoue franchement et affiche la sortie complète du harnais.

Les codes de sortie sont utilisables en CI : `0` tout passe, `1` une
vérification tombe, `2` environnement (serveur injoignable).

## 2.24 Passe 21 — un poste neuf peut charger ses référentiels

La passe 15 avait relié les référentiels aux formulaires : le champ « Pays »
propose ce que contient le référentiel. Mais sur un poste neuf, le référentiel
est **vide** — la suggestion ne servait à rien tant que quelqu'un n'avait pas
saisi douze pays, dix ports et cinq devises à la main.

### Ce que l'amorçage apporte, et ce qu'il n'est pas

`POST /api/referentiels/{collection}/base` ajoute les entrées **manquantes**
d'un jeu de référence public : pays (DZ, FR, ES, IT, DE, BE, MA, TN, TR, CN,
AE, US), devises (DZD, EUR, USD, GBP, CNY), ports (Alger, Oran, Arzew,
Mostaganem, Skikda, Béjaïa, Annaba, Marseille, Valence, Gênes).

Ce ne sont **pas des données d'exemple** : aucun dossier, aucun montant, aucune
pièce n'est créé. Ce sont des listes stables et vérifiables, que personne ne
devrait ressaisir. Chaque entrée porte `origine: "jeu de base"`, ce qui permet
de distinguer plus tard une saisie métier d'une entrée d'amorçage.

### Trois garde-fous

1. **Idempotent** : relancé, l'amorçage n'ajoute que ce qui manque (mesuré :
   12 ajoutés puis 0 ajouté, 12 déjà présents).
2. **Jamais destructif** : une entrée saisie à la main avec le même code n'est
   pas réécrite (test dédié : `Algerie (saisie locale)` reste intacte).
3. **Tracé et borné** : `referentiel_amorce` dans le journal ; `tarifs` — qui
   n'a pas de base — répond 404 en listant les collections disponibles.

### Côté écran

Les trois référentiels concernés affichent un bouton global **« Charger le jeu
de base »** (confirmation, puis rechargement de la liste). Le résultat ne
s'affiche plus en JSON mais en phrase : *« 12 entrées ajoutées, 0 déjà
présente — total 12 »*, ou *« Rien à ajouter : les 12 entrées de référence sont
déjà présentes »*. Le moteur gagne pour cela un résumé optionnel d'action
(`resumer`), sans casser le panneau JSON utilisé ailleurs.

Mesure jsdom : `#referentiels/ports` vide → clic → `POST …/base 200`, **10
lignes**, puis le dialogue de création de dossier propose **10 ports** — la
liaison de la passe 15 trouve enfin sa matière. Les données de démonstration du
dépôt n'ont pas été modifiées : c'est l'opérateur qui décide de l'amorçage.

## 2.25 Passe 22 — comparer deux périodes sans mentir

L'écran Statistiques donne un état : *715 dossiers, 185 à valider*. Il ne
répond pas à la question qu'on se pose vraiment — **est-ce plus ou moins
qu'avant ?** — et c'est celle qui décide d'un renfort ou d'un délai.

### Deux fenêtres, six indicateurs

`GET /api/stats/comparaison?jours=30` compare `[J-30, aujourd'hui)` à
`[J-60, J-30)` sur les dates réelles : création du dossier, archivage, fin de
traitement du job, dernière modification. Indicateurs exposés : dossiers
ouverts, archivés, à revoir, mis à jour, documents traités, documents en
erreur. La fenêtre est bornée côté serveur (1 à 365 jours).

### Les trois pièges évités

| Piège | Traitement |
|---|---|
| période précédente vide → « +∞ % » | variation **non calculable**, la ligne dit *« 49 sur la période, aucun équivalent avant »* |
| date absente → comptée « ancienne » | ces dossiers ne sont comptés nulle part et `sans_date` les déclare |
| état énuméré (`DossierState.ARCHIVE`) | normalisé : les 49 archivés sont bien comptés (ils étaient à 0 avant la normalisation) |

Un `avertissement` explicite est renvoyé quand la période précédente est
entièrement vide : sur cette base de démonstration, tout se situe dans les
trente derniers jours, et l'écran le dit plutôt que de suggérer un bond
d'activité.

### Écran

Nouvelle entrée **« Comparaison de périodes »** (`#rapports/comparaison`,
lecture seule) : six lignes, colonnes *30 derniers jours* / *30 jours
précédents* / *tendance* / *lecture* / *date utilisée*, filtre par tendance.

Mesure jsdom : 6 lignes rendues avec leurs valeurs réelles (715 / 49 / 200 / 5 /
186 / 715), filtre « hausse » opérationnel, zéro erreur réseau.
`tests/test_stats_comparaison.py` : 10 tests sur la fonction pure (hausse,
baisse, stabilité, périodes vides, dates manquantes, énumérations, bornes API,
fenêtres consécutives).

Matrice : **101 entrées, 101 conformes**.

## 2.26 Passe 23 — choisir un dossier plutôt que recopier son identifiant

Les formulaires génériques d'expédition, déclaration (Contrôles), liquidation
et frais demandaient un `dossier_id` brut. Ils proposent désormais un datalist
alimenté par `/api/dossiers`, avec le libellé, la référence et l'état du dossier.
La valeur envoyée reste l'identifiant : les libellés ne remplacent jamais les clés.
La liquidation propose également les déclarations de `/api/declarations`.

Le chargement est partagé entre champs simultanés puis invalidé à la résolution ;
une réouverture recharge les choix. Un échec réseau est expliqué et la saisie
inconnue est refusée avant l'envoi, y compris pendant le chargement. Une liste
vide indique où créer l'objet manquant. La validation serveur reste nécessaire :
ces suggestions ne sont pas une garantie d'intégrité référentielle côté API.

Mesure en lecture seule : 715 dossiers proposés, libellé « arbitrage persistant ·
Révision requise », `dos_inconnu` refusé. Harnais versionné :
`npm run ui:registres [URL]` (serveur actif et au moins un dossier requis).
Aucune donnée d'exploitation ajoutée : cette passe facilite la saisie, elle ne
constitue ni une importation automatique ni l'alimentation du terminal.

## 2.27 Passe 24 — statistiques : corriger les faux traités et expliciter les limites

La revue de la passe 22 a trouvé une erreur : « Documents traités » comptait tous
les jobs, même queued, processing, cancelled et error. Désormais, seuls les jobs
actuellement `done` sont comptés : sur ce poste, **131 au lieu de 200**. Les erreurs
sont identifiées par égalité exacte (`error`), pas par suffixe.

Les dates disponibles sont des créations et dernières modifications : elles ne
prouvent pas la date exacte d'une transition. La colonne « Date utilisée » indique
notamment « dernière modification des dossiers actuellement archivés ». Un bloc
visible précise que les six lignes sont une photographie des états actuels, pas
un journal historique. L'avertissement période précédente vide et les dossiers
sans date exploitable sont maintenant affichés, pas seulement renvoyés par l'API.

Une panne de lecture renvoie 503 plutôt qu'une fausse période vide. La limite de
2000 documents est détectée avec une ligne sentinelle et signalée dans les limites
visibles ; les nombres NaN et infinis sont traités comme dates manquantes.

Preuve rejouable : `npm run ui:comparaison [URL]` vérifie six lignes et le bloc
explicatif, sans écriture. Tests statistiques : **18 passed**, dont huit nouveaux
cas sur statuts non terminés, dates invalides, panne de lecture et troncature.

## 2.28 Passe 25 — Déclarations : remplacer le formulaire inerte

L'entrée `#douane/declarations` ouvrait un ancien formulaire HTML dont le bouton
`declCreer` n'avait aucun gestionnaire. Le formulaire connecté existait uniquement
sur Contrôles. La navigation ouvre maintenant le moteur générique, avec une
copie distincte de la définition de Contrôles (état de route non partagé), un titre
de préparation et le même contrat `/api/declarations`. L'ancien écran ne conserve
qu'un lien vers le parcours actif ; ses champs et son bouton inertes sont retirés.

`npm run ui:declarations [URL]` teste la navigation, l'avertissement, le refus d'un
identifiant inconnu, puis une création complète avec POST **simulé** : identifiant
du dossier et numéro envoyés, boîte fermée, ligne relue dans la liste. Dossiers et
déclarations sont simulés ; seuls les fichiers UI et autres GET viennent du serveur.
Aucune déclaration métier réelle n'est créée. Ce n'est pas un dépôt officiel.

Limite explicitement affichée : le stockage des déclarations est en mémoire et ne
survit pas au redémarrage. La persistance reste une prochaine tâche, pas un acquis.

La matrice régénérée classe cette route en PARTIEL : la création est testée avec
un serveur simulé, mais le CRUD complet de cette entrée n'est pas re-certifié.
Bilan honnête : **101 routes, 100 conformes, 1 partielle**. Le total précédent à
101 conformes ne détectait pas le bouton inerte de cet écran historique.

## 2.29 Passe 26 — persistance locale des trois modules métier

Déclarations, liquidations et enlèvements utilisaient des dictionnaires attachés
à l'application. Ils utilisent désormais `BusinessStore`, un magasin SQLite dans
`cfg.data_dir/metier.sqlite3` (exclu de Git). Trois collections séparées, documents
JSON validés par Pydantic, écritures transactionnelles, connexions fermées après
chaque opération et copies à la lecture. Les mises à jour et chaque étape du
workflow terminal enregistrent explicitement la nouvelle version avant succès.

Neuf tests isolés dans `tmp_path` couvrent :
- création, modification et suppression de chacune des trois collections relues
  après construction d'une **nouvelle application FastAPI** ;
- planification, autorisation puis sortie terminal relues entre applications ;
- lecture dans un **autre processus Python** ;
- absence de mutation implicite et refus de persister un objet invalide ;
- sauvegarde SQLite cohérente via `Connection.backup`, restauration et refus
  d'écraser une base existante sans confirmation.

Le contrat API expose `id`, pas `declaration_id`/`liquidation_id` comme identifiant
primaire. Le moteur d'écrans et le registre de déclarations sont corrigés, ainsi
que la fixture navigateur qui reproduisait la mauvaise clé. Les champs du modèle
`date_depôt` et `agent_declarat` perdaient les valeurs canoniques du formulaire :
ils sont renommés `date_depot` et `agent_declarant`, avec alias de lecture des
anciens noms. Un test vérifie leur conservation après réouverture.

L'écran indique maintenant la conservation locale après redémarrage. L'ancien
stockage volatil ne laisse aucun fichier à migrer : cette passe ne récupère pas
des objets perdus lors d'un ancien arrêt. Aucun jeu de données métier n'est ajouté.
La base ne remplace pas le contrôle des transitions métier et n'offre pas de
transaction entre collections ; les mises à jour concurrentes d'un même objet
restent en dernière écriture gagnante. Restaurer les sauvegardes serveur arrêté.
La matrice reste à **100 conformes / 1 partielle** : la persistance API ne certifie
pas à elle seule toutes les interactions navigateur de l'entrée Déclarations.

## 2.30 Passe 27 — CRUD Déclarations contre une API réelle, avec redémarrages

La preuve de création de la passe 25 utilisait un POST simulé. Elle ne suffisait
pas pour certifier l'édition, la suppression et la conservation réelle des valeurs.
`tests/test_declarations_e2e.py` démarre maintenant l'application complète via
uvicorn sur un port libre et avec `UNOCR_DATA_DIR`, `UNOCR_LOG_DIR` et les profils
utilisateur dans `tmp_path`. Il n'utilise jamais le serveur du poste sur le port 8000.

`tests/ui_declarations_e2e.js` charge l'interface dans jsdom et appelle les vraies
routes API. Il ne simule aucune réponse métier. Il refuse les écritures navigateur
autres que POST/PUT/DELETE vers les déclarations du serveur isolé. Le test Python
prépare un dossier dans ce même magasin temporaire, puis vérifie :

1. **Création** dans le formulaire : choix du dossier, numéro, date de dépôt, agent.
2. **Édition** : numéro et statut changés, fermeture et liste actualisée.
3. **Arrêt réel du processus**, redémarrage : les quatre valeurs sont relues via API.
4. **Suppression annulée** : aucune requête DELETE.
5. **Suppression confirmée** : DELETE réel et état vide visible.
6. **Nouvel arrêt/redémarrage** : liste toujours vide.

Les processus sont arrêtés en `finally`, les journaux et données restent dans les
répertoires temporaires. Sans node/jsdom le test est sauté avec motif explicite.
Commande rejouable : `npm install` puis
`python -m pytest tests/test_declarations_e2e.py -q` (**1 passed**, environ 10 s).
Ce test jsdom n'est pas un test de rendu graphique Chromium ni un dépôt douanier.

La matrice est régénérée après parcours des 101 entrées ; Déclarations porte
maintenant cette preuve complète : **101 conformes, 0 partiel**. Cela certifie
le parcours CRUD local, pas l'intégrité référentielle, les règles de transition
métier ou une connexion à un service douanier externe.

## 2.31 Passe 28 — verrouiller les transitions du terminal

Le stockage durable ne suffisait pas : une demande pouvait être créée directement
au statut `sortis`, le PUT générique pouvait remplacer le statut, et l'action de
sortie ne vérifiait pas l'autorisation. La séquence prise en charge est désormais :
`demande` → `planifie` → `sortie_autorisee` → `sortis`.

- Création exclusivement en demande, dossier/B-L/conteneur non vides.
- Planification autorisée pour demande/planifie uniquement, avec date canonique
  AAAA-MM-JJ et informations transport/chauffeur non vides.
- Autorisation exclusivement depuis planifie, mainlevée/BAD/frais à vrai et
  référence de justificatif non vide. Ces valeurs restent des déclarations de
  l'opérateur, pas une vérification auprès d'un service externe.
- Sortie exclusivement depuis sortie_autorisee, avec recontrôle des trois
  prérequis, du justificatif et d'une date valide. Une seconde sortie est refusée.
- PUT ne change pas le statut ; date/preuve de sortie réservées au workflow.
  Après autorisation, seules les observations peuvent changer. Une valeur nulle
  incompatible renvoie 422 avant écriture, pas une erreur de validation tardive.
- Refus de transition tracés `enlevement_transition_refusee`, erreur 409 (état),
  400 (prérequis manquants) ou 422 (données invalides).

`tests/test_terminal_workflow.py` : **16 passed**, API réelle avec magasins
SQLite temporaires et relecture après refus. La fixture d'API temporaire est
partagée via conftest avec les neuf tests de persistance.

L'écran Sortie portuaire utilise la vraie clé `id` (pas `enlevement_id`) et
masque les actions hors étape. `npm run ui:terminal` vérifie quatre états avec
données simulées, aucune écriture ; les tests API vérifient les refus côté serveur.

Limites : pas de migration des anciens statuts intermédiaires, pas de procédure
d'annulation/révocation ni de verrou optimiste entre deux requêtes concurrentes.
Le parcours complet de création/planification terminal dans l'UI n'est pas certifié
par ce test de visibilité. Le contrôle de l'existence des dossiers reste à faire.
Matrice inchangée : 101 entrées, aucun nouvel écran ajouté.

## 2.32 Passe 29 — liens liquidation/déclaration transactionnels

Les suggestions UI n'empêchaient pas un appel API de créer une liquidation pour
une déclaration inexistante ou un autre dossier. Désormais, création et modification
d'une liquidation exigent une déclaration existante portant le même `dossier_id`.
Parent absent : 422 ; dossier incohérent : 409. Une modification invalide (y compris
null sur un champ non nullable) est validée avant écriture et laisse l'objet intact.

Une déclaration utilisée par au moins une liquidation ne peut plus être supprimée
ni déplacée dans un autre dossier (409). Ses autres champs restent modifiables.
Après suppression ou réaffectation cohérente de ses liquidations, le parent est
libéré. Aucun effacement en cascade n'est introduit.

`BusinessStore.transaction()` réserve l'écriture par `BEGIN IMMEDIATE` ; `related()`
ouvre une autre collection sur la même connexion. Vérification du lien, sauvegarde,
contrôle avant déplacement et suppression du parent sont donc sérialisés dans la
même base. Une exception annule la transaction complète. Le magasin ne devient
pas pour autant une base relationnelle avec contraintes SQL : ces règles sont
appliquées par les routes concernées, pas aux écritures directes hors API.

`tests/test_liquidation_integrity.py` : **12 passed**, incluant valeurs invalides,
refus sans changement après réouverture, parent protégé/libéré, réaffectation
cohérente, rollback de deux collections et cinq courses création/suppression
sur deux applications distinctes. Dans chaque course, soit la liquidation est
créée et la suppression refusée, soit le parent est supprimé et la création refusée.

Les fixtures de persistance créent maintenant un vrai parent avant leur liquidation.
Le formulaire indique que la déclaration doit appartenir au dossier choisi.

Limites : pas de migration/correction automatique des anciens liens invalides ;
pas encore de contrôle de l'existence du dossier dans son magasin JSON, ni de
protection de la suppression du dossier parent. Les états métier et les montants
ne sont pas validés par cette seule intégrité de lien. Matrice inchangée (101 routes).

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
   198 Ko (plafond 220 Ko) : dupliquer un gabarit par écran n'était pas
   tenable. Le moteur rend chaque écran par données, ce qui garantit que les
   états vide/erreur/chargement et les permissions sont identiques partout.
2. **Aucune donnée fictive.** Les collections vides le restent ; les écrans
   affichent un état vide avec l'action de démarrage.
3. **Écritures gardées par le serveur.** L'UI masque les boutons, le serveur
   applique le RBAC : masquer un bouton n'est jamais la sécurité.
4. **Statuts honnêtes.** Un écran hérité non re-testé reste **PARTIEL**, même
   s'il « a l'air » fini. La matrice le dit explicitement.

## 5. Ce que ces passes ne font pas

- **Aucun écran n'est laissé PARTIEL** : `#finance/cloture` a été exercé en
  passe 19 sur un dossier jetable, sans toucher aux données de démonstration.
- Certains écrans **réutilisent une page historique** (`#dossiers/tous`,
  `#tab-profiles`, `#documents/configuration`…) : mesurés et documentés, mais
  leur contenu reste celui de la page héritée.
- Les **actions contextuelles** sont exercées à la main (mesures jsdom
  reproductibles) mais toutes ne sont pas figées par un test automatisé.
- **Aucune comparaison** avec un ERP externe : aucun connecteur métier réel
  n'est disponible sur ce poste (voir limitations dans
  `FONCTIONNALITES_RESTANTES.md`).
