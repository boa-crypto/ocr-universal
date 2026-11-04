# Guide utilisateur

> Variables de configuration, procédure de déploiement et retour arrière lot par lot : `docs/DEPLOIEMENT.md`.

## 1. Se connecter au serveur

L'interface web et l'API sont servies par **le même processus** (port 8000) :
une fois le serveur lancé, la connexion est automatique.

### En local (déploiement classique, Windows/Linux/macOS)
```bash
cd ocr-universal
./scripts/install.sh          # dépendances Python
./scripts/run_server.sh       # uvicorn sur 0.0.0.0:8000
```
Ouvrez ensuite **http://localhost:8000** : la page sonde l'API sur son propre
hôte au chargement et passe en « connecté ». Équivalent manuel :
`PYTHONPATH=src python -m unocr.cli serve --host 0.0.0.0 --port 8000`.

### Dans un environnement cloud / aperçu distant
Le serveur est publié sous une URL du type `https://8000-<sandbox>.e2b.app`
(affichée par le panneau « live preview » du processus). Ouvrez **cette URL**
directement : l'UI et l'API partagent le même hôte, rien à saisir.

Si vous consultez le fichier `web/index.html` dans un lecteur statique (bac à
sable sans réseau), l'UI ne peut pas joindre l'API toute seule :
- ouvrez plutôt l'URL du serveur live ci-dessus (recommandé) ;
- ou collez l'URL du serveur dans le champ **« URL de l'API »** du bandeau
  jaune puis cliquez **Connecter**.

### Vérifier la connexion
- l'indicateur d'état passe au vert (« connecté ») ;
- l'onglet **Configuration** affiche les moteurs (Tesseract : disponible) et
  les modèles de langues installés ;
- le bandeau jaune d'avertissement disparaît.

### Appeler l'API depuis un script
Le CORS est ouvert, aucune clé n'est requise :
```bash
curl -F "file=@bl.pdf" -F "profile=port_bl" http://localhost:8000/api/documents
```
La documentation OpenAPI est sur `http://localhost:8000/docs`.

> **Note** : un serveur lancé dans un bac à sable peut s'arrêter entre deux
> sessions de travail. Si l'API ne répond plus, relancez `./scripts/run_server.sh`
> (ou demandez le redémarrage à votre agent).

## 2. Interface web (`http://localhost:8000`)

### Onglet Import
1. Glissez-déposez un fichier (ou « Parcourir… »).
   **📷 Prendre une photo** capture directement depuis la caméra (conteneur,
   plaque, facture…) : le type de capture prépare le profil métier adapté ;
   sans caméra disponible (poste fixe, iframe), le sélecteur de fichier
   s'ouvre à la place (sur mobile, il ouvre l'appareil photo).
2. Choisissez le **profil métier** :
   - `generic` : champs courants (dates, contacts, montants, identifiants)
   - `invoice` : facture (numéro, dates, TVA, totaux)
   - `port_bl` : connaissement maritime (BL, conteneurs ISO 6346, navire, ports…)
   - `packing_list` : liste de colisage
   - `container` : photo de conteneur (n° ISO 6346 avec chiffre de contrôle)
   - `vehicle_plate` : photo de plaque / véhicule (11 pays : FR, DZ, ES, DE, IT,
     PT/NL, BE, UK, TR, MA, TN ; VIN)
   - `carte_grise` : certificat d'immatriculation (plaque, VIN, marque, énergie,
     date de 1re immatriculation, puissances, PTAC, couleur, titulaire)
3. **Langues** : cliquez les chips des modèles installés (aucune sélection =
   auto-détection).
4. Mode `accurate` (défaut) compare les variantes de prétraitement et garde la
   meilleure ; `fast` est plus rapide sur de gros lots.
5. **Options avancées** (panneau dépliable) :
   - **Prétraitement** : `standard` (adapté à la qualité détectée), `agressif`
     (photos, scans dégradés), ou `désactivé` (image d'origine brute) ;
   - **Résolution de rendu** : 150 à 400 DPI pour les PDF scannés ;
   - **Moteur OCR** : `auto` (sélection + consensus), `tesseract` uniquement, ou
     couche texte `native` uniquement (repli Tesseract si le PDF n'en a pas) ;
   - **Pages à traiter** : ex. `1-3, 5` — une sélection entièrement hors
     document est refusée ;
   - **Seuil de revue humaine** : en dessous, champs et pages sont signalés dans
     l'onglet Qualité ;
   - **Modules d'extraction** : champs, tableaux, codes-barres, comparaison de
     variantes — chacun peut être désactivé ;
   - **Exports automatiques** : formats générés en fin de traitement (les autres
     restent téléchargeables à la demande depuis l'onglet Résultat).
6. « Traiter le document » — la barre de progression reflète les étapes réelles.

### Onglet Documents
Historique des traitements, filtres par statut et recherche. Actions : ouvrir,
rejouer (reprise), supprimer (journalisé).

### Onglet Résultat
- **Visionneuse** : image source avec les zones OCR. Cliquez sur un champ dans le
  tableau pour **surligner sa zone** sur le document.
- **Texte reconnu** : texte complet par page, recherche intégrée.
- **Champs extraits** : valeur lue, normalisée, confiance (barre colorée),
  statut. Colonne « Correction humaine » : saisissez la valeur et « Valider » —
  la validation est tracée et la valeur d'origine conservée.
- **Tableaux reconstruits** : matrices avec méthode (`ruled`/`clustering`) et
  confiance, badge multipages.
- **Codes-barres / QR** : contenu décodé + page.
- **Comparaison moteurs** : visible dès que plusieurs moteurs ont tourné.

### Onglet Qualité
Confiance moteur vs confiance globale (distinctes), liste des **anomalies**
(page floue, champ obligatoire absent, date incohérente, numéro ISO 6346
invalide, caractères ambigus O/0, contenu injecté signalé…), désaccords moteurs.

### Onglet Résultat — valider au clavier

La file de révision se parcourt sans souris :

| Touche | Effet |
|---|---|
| `j` / `↓` | champ incertain suivant |
| `k` / `↑` | champ incertain précédent |
| `Entrée` | valider la valeur du champ focalisé |
| `u` | annuler la correction du champ focalisé |
| `o` | ouvrir le document source |
| `?` | aide des raccourcis |

**Annuler une correction.** Le bouton « Annuler » (ou `u`) restitue l'état
d'avant la correction. Rien n'est effacé : la correction d'origine reste dans
l'historique, et l'annulation y est enregistrée à son tour avec votre nom et le
motif demandé. Annuler ne fait pas perdre la normalisation déjà faite par le
moteur — la valeur restaurée est celle qui était réellement affichée.

### Onglet Configuration
Moteurs OCR réellement disponibles (les moteurs non installés sont affichés
comme tels), langues des modèles installés, profils chargés.

**Contrôles de cohérence configurables.** Les tolérances de rapprochement
(écart de poids, quantité, montant), les règles qui bloquent la transmission et
les clés de référence servant au rapprochement se règlent dans
`config/default.json`, section `coherence`. Une règle peut être désactivée par
son nom exact. La route `GET /api/coherence/regles` affiche la configuration
réellement appliquée — c'est la première chose à consulter quand un constat
surprend ou manque.

### Onglet Tableau de bord
Volumes de jobs, erreurs, ressources machine — tous mesurés, jamais estimés.

**Sauvegarde du magasin.** Le tableau de bord porte un panneau dédié. Le
magasin local (`data/` + `logs/audit.log`) est la seule trace des documents
traités, des corrections humaines et des transmissions : rien ne le protégeait
d'une suppression accidentelle. « Sauvegarder maintenant » crée une archive
horodatée, en vérifie chaque empreinte, et ne conserve que les 5 plus
récentes. « Lister les sauvegardes » permet de restaurer : la restauration
réécrit le magasin, elle demande donc une confirmation **et** un motif, parce
que les documents postérieurs à la sauvegarde seront perdus.

## 3. Ligne de commande

```bash
# traitement simple
PYTHONPATH=src python -m unocr.cli process mon_document.pdf \
    --profile port_bl --lang fra,eng --export json,txt,csv,xlsx,xml,pdf --out ./sortie

# diagnostic de l'environnement (à joindre à toute demande de support)
PYTHONPATH=src python -m unocr.cli diagnose

# serveur
PYTHONPATH=src python -m unocr.cli serve --port 8000

# sauvegarde du magasin (jobs, dossiers, exports, journal d'audit)
PYTHONPATH=src python -m unocr.cli backup --tag avant-migration

# lister les sauvegardes disponibles
PYTHONPATH=src python -m unocr.cli backups

# restaurer — refuse d'écraser un magasin non vide sans --force
PYTHONPATH=src python -m unocr.cli restore sauvegardes/sauvegarde-20261018-213000.zip --force
```

La sauvegarde écrit dans `sauvegardes/` (à côté de `data/`), porte
l'horodatage dans son nom, et affiche son empreinte SHA-256. `--keep 5` (par
défaut) ne conserve que les 5 plus récentes : une sauvegarde qu'on ne purge
jamais finit par remplir le disque et faire échouer la suivante.

La sortie JSON récapitule : pages, champs détectés, tableaux, anomalies,
confiances, moteurs utilisés, temps par étape, chemins d'exports.

## 4. Profils métier

Fichiers JSON dans `profiles/` — ajoutez-en **sans modifier le code** :

```json
{
  "name": "mon_profil",
  "label": "Mon profil",
  "fields": [
    {"key": "ma_ref", "label": "Ma référence",
     "patterns": ["(?:R[ée]f[érence]*)\\s*[:#]?\\s*([A-Z0-9\\-]{4,20})"],
     "required": true, "validators": ["not_empty"],
     "normalize": "upper", "category": "identifiants"}
  ],
  "relations": [
    {"type": "date_order", "before": "date_debut", "after": "date_fin"}
  ],
  "consistency_checks": [], "export_rules": {}
}
```

- `patterns` : liste de regex testées dans l'ordre, **groupe 1 = valeur**
- `validators` : `iso6346`, `luhn`, `iban`, `date_iso`, `container_type`, `not_empty`,
  `plate` (plaques : FR SIV/FNI, Algérie 01–58, Espagne, Allemagne, Italie,
  Portugal/Pays-Bas, Belgique, Royaume-Uni, Turquie 01–81, Maroc, Tunisie),
  `vin` (ISO 3779, 17 car.), `vin_check` (check digit position 9 — VIN nord-
  américains uniquement ; signale les lectures OCR fautives), `energy`
  (essence, diesel, électrique, hybride, GPL…)
- `required` : déclenche une anomalie `MISSING_REQUIRED_FIELD` si absent
- `relations` : `date_order`, `sum_equals` (contrôles de cohérence)
- Champs absents → `not_detected`, valeur `null`. **Aucune valeur n'est inventée.**

Profils livrés : `generic`, `invoice`, `port_bl`, `packing_list`, `container`
(photo conteneur ISO 6346), `vehicle_plate` (plaque / VIN, 11 pays),
`carte_grise` (plaque, VIN + check digit, marque, modèle, énergie, 1re
immatriculation, puissances, PTAC, poids à vide, cylindrée, genre, couleur,
n° moteur, n° de carte, titulaire).

## 5. Contrôle qualité au quotidien

- Confiance < 70 % → vérifier manuellement (surlignage UI).
- Anomalies `INVALID_FORMAT` sur un conteneur ISO 6346 → le chiffre de contrôle
  ne passe pas : **ne pas valider sans vérification humaine**.
- `UNTRUSTED_CONTENT` : le document contient du texte ressemblant à une
  instruction (« ignore all previous instructions… ») — il est ignoré par le
  système et signalé, jamais exécuté.
- Toute correction est réversible : `raw_value` reste dans le JSON et l'audit.

## 6. Export et intégration

- JSON : structure complète (mots, boîtes, cellules, confiances, provenance)
- XLSX : feuilles Champs / Tables / Texte / Anomalies / Métadonnées
- XML : structure stable pour systèmes tiers
- PDF consultable : recherche/copie du texte, rendu de la source
- CSV : protégé contre l'injection de formules (`=` préfixé par `'`)

## 7. Cas portuaire (exemple)

```bash
PYTHONPATH=src python -m unocr.cli process bl.pdf --profile port_bl --export json,xlsx
```

Le profil `port_bl` détecte : BL, Booking, conteneur (validation ISO 6346
**avec chiffre de contrôle**), code type ISO, sceau, navire, voyage, armateur,
expéditeur/destinataire/notified, ports, marchandises, colis, poids, volume,
HS code, marquage, ETA/ETD, manifeste, référence douanière. Les relations
conteneur ↔ BL ↔ marchandises sont préservées via les tableaux reconstruits
(les lignes ne sont jamais mélangées entre documents).

## 8. Rôles et cloisonnement par dossier

Par défaut, UniOCR n'exige aucun jeton : c'est un outil local. Dès que plusieurs
personnes y accèdent, ce n'est plus tenable — un jeton unique et partagé
donnerait à tout le monde les mêmes droits, y compris la restauration des
sauvegardes.

**Activer les rôles.** Créez `data/rbac.json` :

```json
{
  "utilisateurs": [
    {"nom": "marie", "roles": ["operateur"], "dossiers": ["*"], "jeton": "un-secret-long"},
    {"nom": "audit", "roles": ["lecteur"], "dossiers": ["D-2026-001"], "jeton": "un-autre-secret"},
    {"nom": "admin", "roles": ["administrateur"], "dossiers": ["*"], "jeton": "le-secret-admin"}
  ]
}
```

Puis rechargez sans redémarrer : `POST /api/rbac/recharger` (en administrateur),
ou redémarrez le service.

**Les quatre rôles**, du plus restreint au plus large :

| Rôle | Ce qu'il permet |
|---|---|
| `lecteur` | consulter documents, dossiers, résultats, exports |
| `operateur` | + valider et corriger les champs, créer des dossiers |
| `superviseur` | + arbitrer un constat bloquant, transmettre un dossier |
| `administrateur` | + sauvegardes, restauration, gestion des utilisateurs |

Chaque rôle contient les précédents : un `superviseur` peut tout ce que fait un
`operateur`.

**Le périmètre.** `"dossiers": ["*"]` donne accès à tout. Une liste
d'identifiants limite la vue à ces dossiers — et la liste des dossiers est
filtrée, un dossier hors périmètre n'apparaît pas. Une liste vide ne donne
accès à rien.

**Le cloisonnement porte aussi sur les documents.** Ouvrir un document passe
normalement par son dossier ; mais `GET /api/jobs/{id}/result` renvoie tout son
contenu directement. Sans garde à ce niveau, être bloqué sur un dossier
n'empêchait pas de lire chaque document qu'il contient. Un document est donc
accessible s'il est classé dans **au moins un dossier que vous voyez**.

Un même document peut légitimement appartenir à plusieurs dossiers (une facture
commune à deux expéditions). Le voir par l'un ne donne accès à rien de plus que
par l'autre : c'est le même document.

**Ce qui n'est pas cloisonnable : un document non classé.** Un document qui
n'appartient à encore aucun dossier ne peut être attribué à personne ; son accès
est régi par le seul rôle. Classez vos documents dans des dossiers pour que le
cloisonnement s'applique.

Un opérateur cantonné à un dossier qui en **crée** un nouveau le voit
automatiquement : son identifiant est généré par le système, il ne pouvait pas
figurer à l'avance dans son périmètre. L'ajout est tracé dans l'audit
(`rbac_perimetre_etendu`) — un cloisonnement qui s'élargit doit se voir.

**Le jeton.** Il se saisit dans l'interface au démarrage (une fenêtre le demande
si l'API en exige un) et se conserve dans le navigateur. Pour les scripts, il
passe en en-tête :

```bash
curl -H "Authorization: Bearer <jeton>" http://localhost:8000/api/dossiers
```

**Gérer les utilisateurs** (administrateur seul) : `GET/POST /api/rbac/utilisateurs`,
`PUT /api/rbac/utilisateurs/{nom}`, `POST /api/rbac/utilisateurs/{nom}/jeton`
pour régénérer un jeton perdu, `DELETE /api/rbac/utilisateurs/{nom}` pour
révoquer. **Le jeton n'est affiché qu'une fois**, à la création — il ne se
consulte pas ensuite.

**Ce que les rôles ne sont pas.** Pas d'annuaire d'entreprise : pas de SSO, pas
de LDAP, pas d'expiration de jeton. Les jetons sont des secrets porteurs
conservés dans `data/rbac.json` (permissions 0600), comparés à temps constant.
Un jeton qui fuite donne les droits de son porteur jusqu'à révocation.

**Le cloisonnement survit aux sauvegardes.** `data/rbac.json` est archivé avec
le magasin et restauré avec lui, et le service recharge les droits au moment de
la restauration. Sans cela, une reprise après incident aurait rendu l'API
**ouverte à tous** en silence — vous croiriez vos rôles toujours en place.

**Sans `data/rbac.json`, rien ne change** : aucun jeton exigé, aucune route
fermée. C'est vérifié par des tests dédiés.
