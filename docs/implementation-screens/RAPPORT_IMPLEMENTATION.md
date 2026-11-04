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
   191 Ko (plafond 220 Ko) : dupliquer un gabarit par écran n'était pas
   tenable. Le moteur rend chaque écran par données, ce qui garantit que les
   états vide/erreur/chargement et les permissions sont identiques partout.
2. **Aucune donnée fictive.** Les collections vides le restent ; les écrans
   affichent un état vide avec l'action de démarrage.
3. **Écritures gardées par le serveur.** L'UI masque les boutons, le serveur
   applique le RBAC : masquer un bouton n'est jamais la sécurité.
4. **Statuts honnêtes.** Un écran hérité non re-testé reste **PARTIEL**, même
   s'il « a l'air » fini. La matrice le dit explicitement.

## 5. Ce que ces passes ne font pas

- Un **seul écran reste PARTIEL** : `#finance/cloture`, dont l'action
  « Archiver » n'a pas été exercée sur des données de démonstration suivies par
  git. Voir `FONCTIONNALITES_RESTANTES.md`.
- Certains écrans **réutilisent une page historique** (`#dossiers/tous`,
  `#tab-profiles`, `#documents/configuration`…) : mesurés et documentés, mais
  leur contenu reste celui de la page héritée.
- Les **actions contextuelles** sont exercées à la main (mesures jsdom
  reproductibles) mais toutes ne sont pas figées par un test automatisé.
- **Aucune comparaison** avec un ERP externe : aucun connecteur métier réel
  n'est disponible sur ce poste (voir limitations dans
  `FONCTIONNALITES_RESTANTES.md`).
