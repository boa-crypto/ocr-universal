# Feuille de route — pour finir UniOCR

État de référence : 2026-10-18 (vagues 1 et 2 livrées). Base : 18 modules, ~4450 lignes de `src/`, **177 tests**,
161 tests verts, UI 100 % hors ligne, 7 profils, 6 formats d'export,
API 17 endpoints, 1 seul moteur OCR réellement installé (Tesseract 5.5).

Chaque proposition indique : **ce que c'est**, **pourquoi ça compte pour ce
produit précisément**, l'**effort** (S ≤ 1 h, M = demi-journée, L = 1 à 2 jours)
et les **contraintes honnêtes** (ce qui est bloqué dans cet environnement).

---

## A — Crédibilité des mesures (priorité absolue)

Le point faible du produit n'est pas le code, c'est que **ses chiffres ne sont
pas encore honnêtes sur documents réels**. Tout ce qui suit en découle.

| # | Proposition | Pourquoi | Effort | Contrainte |
|---|---|---|---|---|
| A1 | **Corpus de référence réel + benchmark reproductible** : 25–30 documents réels annotés, `benchmarks/run_all.sh` qui régénère un rapport daté, alerte si le CER régresse | Ferme la limite n°7 (CER 0,008 mesuré sur du synthétique). C'est ce qui transforme « ça marche chez moi » en « ça marche, voici la preuve ». Le gabarit `--init-template` existe déjà. | M | **Bloqué sur toi** : il faut fournir les photos (voir `benchmarks/field/README.md`). Je peux livrer le harnais complet avant. |
| A2 | **Calibration des scores de confiance** : mapper la confiance brute Tesseract vers une probabilité réelle (Platt/isotonic) apprise sur le corpus | Les indicateurs d'incertitude de l'UI deviennent fiables : un champ à « 60 % » voudra vraiment dire 60 % de chances d'être juste. Aujourd'hui c'est une confiance moteur non calibrée. | M | Dépend de A1 |
| A3 | **CI GitHub Actions** : `pytest` + `ruff` + contrôle de build à chaque push | Empêche toute régression silencieuse. Coût nul, crédibilité immédiate. | S | Aucune |

## B — Ce qui manque au quotidien

| # | Proposition | Pourquoi | Effort | Contrainte |
|---|---|---|---|---|
| B1 | **File de révision ciblée** : un onglet qui ne présente **que** les champs `invalid`, `ambiguous` ou sous un seuil, avec validation au clavier (Entrée = accepter, Tab = suivant) | Plus fort levier d'usage réel. Sur une carte grise, valider 32 champs un par un est pénible ; en pratique il y en a 3 à reprendre. C'est la différence entre « démo » et « outil de travail ». | M | Aucune |
| B2 | **Recherche plein texte inter-documents** : `GET /api/search?q=` sur le texte et les champs extraits, avec surlignage du passage | Avec 84 jobs, retrouver « le document qui contient ce VIN » est impossible aujourd'hui : `docSearch` ne filtre que le **nom de fichier**. | S | Aucune |
| B3 | **Lots** : déposer un dossier entier, une barre de progression globale, puis un **export groupé** (un XLSX, une feuille par document ; ou un CSV long) | Cas d'usage dominant en facturation : 50 documents, un tableau. Aujourd'hui c'est 50 aller-retours. | M | Aucune |
| B4 | **Dossier surveillé** : un répertoire en entrée, traitement automatique à l'arrivée d'un fichier (+ webhook sortant optionnel) | Automatisation locale sans surveillance humaine. | S | Aucune |
| B5 | **Éditeur de profils dans l'UI** : créer/modifier motifs et validateurs sans éditer le JSON à la main, avec test en direct sur un document | Les 7 profils livrés couvrent des cas connus ; le vrai besoin d'un utilisateur sera toujours un 8ème profil. L'éditeur est ce qui rend le produit adaptable. | M | Aucune — ajout pur, ne touche pas à `profiles.py` |
| B6 | **Cache par empreinte** : hachage du fichier → résultat réutilisé | Re-déposer le même document devient instantané. Utile en lot et en démonstration. | S | Aucune |

## C — Finition de l'interface

| # | Proposition | Pourquoi | Effort | Contrainte |
|---|---|---|---|---|
| C1 | **Raccourcis clavier + palette de commandes** (`/` recherche, `g`+`1…6` onglets, `j/k` navigation, `?` aide) | Zéro raccourci aujourd'hui. Un outil de production se pilote au clavier. | S | Testable partiellement ici |
| C2 | **Multi-sélection et export ciblé** : cases à cocher dans les tableaux, exporter seulement la sélection ou seulement les champs validés | Évite l'export complet quand on ne veut que 3 lignes. | S | Aucune |
| C3 | **i18n de l'UI (fr / en / ar + RTL)** | Le moteur lit l'arabe ; l'interface est francophone uniquement. Le RTL serait une signature forte et cohérente avec le produit. | M | Aucune |
| C4 | **PWA / coquille hors ligne** : service worker qui met l'app en cache | Les polices sont déjà embarquées : il manque le service worker pour que l'UI s'ouvre sans serveur du tout. | S | Non testable ici (pas de navigateur) |
| C5 | **Journal d'audit filtrable + vue « Activité »** | Le journal existe côté JS/API ; le rendre consultable et filtrable ferme la limite n°17 côté visibilité. | S | Aucune |

## D — Déploiement (aligné sur ta contrainte Windows)

| # | Proposition | Pourquoi | Effort | Contrainte |
|---|---|---|---|---|
| D1 | **Docker + docker-compose** : une commande, environnement reproductible, Tesseract et les 11 langues inclus dans l'image | Supprime la classe entière des problèmes d'installation (2 CPU / 2 Go RAM / Debian 13 → n'importe quelle machine). | S | Docker non installé ici ; je livre les fichiers, tu valides le build |
| D2 | **Scripts PowerShell Windows** (`install.ps1`, `run.ps1`) | Tu avais demandé du compatible Windows ; seuls des scripts bash existent. C'est un écart réel à fermer. | S | Non testable ici (pas de Windows) |
| D3 | **Authentification par jeton optionnelle** (`UNIOCR_TOKEN`, désactivée par défaut) | Ferme la limite n°17 sans casser le usage local : par défaut rien ne change. | S | Aucune |

## E — Moteur : ce qui est bloqué ici

À faire sur une machine avec plus de RAM, **pas dans cet environnement**.
Je les liste pour que la feuille de route soit complète, pas pour les promettre.

| # | Proposition | Pourquoi | Effort | Contrainte |
|---|---|---|---|---|
| E1 | **Second moteur OCR réel** (EasyOCR ou PaddleOCR) | Le consensus multi-moteurs est implémenté et testé avec des moteurs **simulés** ; il n'a jamais tourné sur deux moteurs réels. C'est la limite n°1 documentée. | L | **Bloqué** : torch dépasse les 2 Go de RAM. Adaptateurs déjà écrits, activation automatique à l'installation. |
| E2 | **Typage des zones** : manuscrit, signature, case à cocher (détection **sans** transcription) | Ferme la limite n°11 en partie. La transcription manuscrite resterait explicitement non fonctionnelle — mais un formulaire serait au moins segmenté et ses zones signalées. | M | Aucune pour la détection |
| E3 | **Chiffrement au repos optionnel** des documents | Ferme la limite n°21. | S | Aucune |
| E4 | **Traitement parallèle des pages** | ~2–7 s/page en mode `accurate` sur 2 cœurs ; le parallélisme par page est le gain le plus direct. | S | À mesurer sur le corpus réel |

---

## Séquençage recommandé

**Vague 1 — rendre le produit défendable** (A1 harnais, A3, B1, B2, D1, C1) — ✅ **LIVRÉE**
La preuve de performance et le workflow de révision : c'est ce qui manque
pour qu'un utilisateur réel puisse travailler avec.

**Vague 2 — le rendre productif** (B3, B4, B5, B6, C2, D2, C5) — ✅ **LIVRÉE** sauf B5
Lots, automatisation, profils personnalisés, Windows.

**Vague 3 — le rendre complet** (A2, E2, C3, C4, D3, B5) — ✅ **LIVRÉE** le 2026-10-18
Calibration, typage de zones, i18n/RTL, PWA, jeton, éditeur de profils.

**Vague 4 — sur machine dédiée** (E1, E3, E4) — ✅ **LIVRÉE** le 2026-10-18
Garde-fou moteurs, chiffrement au repos, parallélisme des pages.

## Ce que je ne ferais pas (discipline de périmètre)

- **File distribuée Celery/Redis** — hors sujet pour un déploiement local 2 CPU ; le thread par job suffit et se mesure.
- **IAM complet multi-utilisateurs** — un jeton optionnel couvre le besoin réel ; le reste appartient au reverse proxy.
- **Réécrire les exporters** — 6 formats fonctionnent et sont testés ; on ajoute, on ne refond pas.
- **Modèles de transcription manuscrite (HTR)** — ne pas promettre ce qui ne peut pas être vérifié ici.


---

## Journal d'avancement
### Vague 4 — livrée le 2026-10-18

| # | Livrable | Vérifié |
|---|---|---|
| E1 | Garde-fou mémoire : un moteur dont la bibliothèque est installée mais qui dépasse la RAM n'est **jamais activé** ; `GET /api/resources` + `unavailable_reason` par moteur | 12 tests (bibliothèque simulée présente, mémoire absente → refus motivé) |
| E3 | Chiffrement au repos optionnel AES-256-GCM (fichier de clé 0600 ou PBKDF2 depuis phrase de passe), `GET /api/encryption` | 17 tests : aller-retour, altération détectée, mauvaise clé refusée, activé-sans-clé → inactif |
| E4 | Parallélisme des pages (threads, workers bornés par cœurs **et** RAM), `timings_ms.ocr_workers` | 8 tests ; en direct sur 4 pages : `ocr_workers: 2.0` |

**Résultat de la suite complète** : 318 tests, 0 échec.

**Ce qui est livré mais doit être dit clairement** :

1. **E1 n'est pas un second moteur.** Aucun moteur lourd n'a pu être chargé
   ici : easyocr/paddleocr ne sont pas installés et torch dépasse la RAM
   disponible. Ce qui est livré, c'est le **garde-fou** qui empêche
   l'activation d'un moteur qui ferait tuer le processus — et la raison
   affichée. Les seuils de mémoire (2,2 Go / 1,8 Go) sont des ordres de
   grandeur non mesurés sur ce matériel. Le consensus multi-moteurs reste
   testé avec des moteurs simulés.
2. **E3 est désactivé par défaut** et protège le stockage, pas le traitement
   (les documents sont déchiffrés en mémoire pour l'analyse). Perdre la clé
   rend les données définitivement illisibles.
3. **E4 : gain mesuré ×1,18**, pas ×2. Sur 4 pages scannées, 2 cœurs, mode
   `fast` : 18,44 s → 15,68 s (médiane de 3 exécutions). L'ingestion, la
   qualité et les exports restent séquentiels, et la RAM limite à 2 workers.
   Les résultats sont identiques au traitement séquentiel.

**Bugs réels trouvés et corrigés pendant la vague 4** :

- `_available_ram_mb()` était **appelé sans être défini** (NameError au
  premier document multipage) ;
- `self.cfg.jobs_workers` n'existait pas — le réglage réel est
  `jobs.workers`, lu via `cfg.get()` ;
- le helper de RAM avait été inséré **au milieu du bloc d'imports** (E402) ;
- un serveur obsolète occupait le port 8000 et masquait les nouvelles routes
  (symptôme : 404 sur `/api/resources` alors que les tests passaient).

### Vague 3 — livrée le 2026-10-18

| # | Livrable | Vérifié |
|---|---|---|
| B5 | Éditeur de profils : CRUD dans `data/profiles/` (jamais dans `profiles/`), essai à blanc, catalogue des validateurs, onglet « Profils » | 18 tests ; contrôle UI 115 identifiants |
| A2 | Calibration des confiances (Platt + isotonique), persistance `data/calibration.json`, `GET /api/calibration` + `POST /api/calibration/fit` | 16 tests ; en direct : 32 paires étiquetées, 31 correctes |
| E2 | Typage de zones (`src/unocr/zone_typing.py`) : cases à cocher, signatures, manuscrit | 3 tests ; manuscrit signalé, **jamais transcrit** |
| C3 | i18n de l'interface (fr/en/ar, sélecteur, `localStorage`) + détection de direction RTL (`src/unocr/direction.py`) | 14 tests dont 2 d'intégration ; document arabe → `direction: "rtl"` |
| C4 | PWA : `manifest.webmanifest`, `sw.js`, icônes SVG, installation hors ligne | 2 tests ; les 3 fichiers servis en 200 |
| D3 | Jeton optionnel `UNIOCR_TOKEN` (comparaison à temps constant, routes `/api/*`) | 4 tests ; en direct : 401 sans jeton, 200 avec, exemptions ouvertes |

**Résultat de la suite complète** : 273 tests, 0 échec.

**Ce qui est livré mais doit être dit clairement** :

1. **La calibration n'est pas activée.** Elle est ajustée sur 32 paires
   étiquetées issues d'échantillons *synthétiques*, dont 31 déjà correctes :
   il n'y a presque aucun contre-exemple à apprendre. Un ajustement issu de
   synthétique est donc enregistré mais laissé inactif (`active: false`) —
   l'activer donnerait une fausse précision. Il faut des photos réelles.
2. **L'i18n couvre la navigation et les en-têtes de page** (français, anglais,
   arabe). Les libellés situés à l'intérieur des panneaux restent en français :
   le mécanisme `data-i18n` est en place et testé (aucune clé manquante dans
   une langue), mais l'ensemble du vocabulaire n'est pas encore traduit.
3. **Le typage de zones (E2) est un générateur de candidats, pas un
   détecteur fiable.** Mesuré sur le formulaire de contrôle synthétique :
   rappel 4/4 mais précision 17 % (23 candidats pour 4 cases réelles), et
   15 candidats sur une carte grise qui n'a aucune case. La détection de
   signatures a été écrite puis **retirée** : elle classait un code QR comme
   « manuscrit ». Ces chiffres sont verrouillés par des tests.
4. **Le RTL est fonctionnel côté données et rendu** (attribut `dir`, miroir
   CSS en propriétés logiques), mais aucun document arabe réel n'a été fourni :
   la vérification porte sur une image de test fabriquée pour l'occasion.
5. **La PWA n'a pas pu être installée sur un vrai mobile** : pas d'appareil
   ni de navigateur mobile ici. Le manifeste et le service worker sont servis
   et testés ; l'installation réelle reste à confirmer par l'utilisateur.
6. **Bugs réels trouvés et corrigés pendant la vague 3** : `POST
   /api/profiles/test` renvoyait 500 (au lieu de 404) pour un profil désigné
   par son nom, car `load_all_profiles` renvoie un dictionnaire ; le service
   worker et le manifeste étaient introuvables (`_web_dir()` pointait vers
   `src/web`) ; `/api/auth/status` était bloqué par le jeton qu'il doit
   justement signaler ; le détecteur de cases rejetait les cases **cochées**
   (seuil d'encre intérieure trop strict).

### Vague 1 — livrée le 2026-10-18

| # | Livrable | Vérifié |
|---|---|---|
| A1 | `benchmarks/run_all.sh` (tests + 2 suites, rapport horodaté) + `benchmarks/corpus/README.md` (guide d'annotation, confidentialité) | exécuté : rapport généré, la suite terrain annonce honnêtement l'absence de photos réelles |
| A3 | `.github/workflows/ci.yml` : lint, tests, benchmark, build + healthcheck Docker | lint et tests verts localement ; le build Docker ne peut pas être validé ici (Docker absent) |
| B1 | `GET /api/review` + page « Révision » dans l'UI, validation clavier | 6 tests ; en direct : 49 documents, 564 → 94 champs après filtrage des non détectés |
| B2 | `GET /api/search` + résultats dans la recherche globale (surlignage, extraits) | 4 tests ; en direct sur un VIN |
| D1 | `Dockerfile` + `docker-compose.yml` + `.dockerignore` + `UNOCR_DATA_DIR`/`UNOCR_LOG_DIR` | config testée (9 tests) ; build Docker non validé ici |
| C1 | Raccourcis clavier (`/`, `g`+chiffre, `j/k`, Entrée, `o`, `t`, `?`) + aide | chargement sans `ReferenceError` sur DOM simulé |

**Défauts trouvés et corrigés au passage** (non prévus dans la feuille de route) :

1. **Les tests API polluaient `data/jobs/` réel** — `store` était instancié à
   l'import, donc `tmp_cfg` ne l'isolait pas : chaque exécution de la suite
   créait de vrais jobs et gonflait les statistiques affichées dans l'UI.
   Corrigé dans `tests/conftest.py` (+ un test qui utilisait l'ancien store).
2. **`api()` était appelée mais jamais définie** — `initLangChips()` échouait
   silencieusement dans son `try/catch` : **les puces de langue ne se
   chargeaient jamais**. Rétabli comme alias de `fetchJson`.
3. **Le halo au curseur était à moitié câblé** — le JS positionne `--mx/--my`
   sur `.card`, mais aucune règle CSS ne les consommait. Micro-interaction
   opérationnelle.
4. **3 variables mortes** et **46 variables nommées `l`** (illisible dans un
   moteur OCR où l/1/I se confondent) renommées en `ln`.


---

### Vague 2 — livrée le 2026-10-18 (sauf B5)

| # | Livrable | Vérifié |
|---|---|---|
| B6 | Empreinte SHA-256 sur les jobs + `find_by_hash` + `dedupe` sur l'upload et les lots | ✅ 4 tests ; en direct : re-dépôt → `cached=true`, 0 recalcul |
| B3 | `POST /api/batches`, `GET /api/batches/export/{fmt}` + panneau « Lots » dans l'UI | ✅ 8 tests ; en direct : XLSX 10 feuilles, CSV long, JSON 2 docs, ZIP |
| B4 | Module `watcher.py` (thread, stabilisation, déduplication, classement) + `GET/PUT /api/watch`, `POST /api/watch/scan` | ✅ 5 tests ; en direct : doublon détecté, `.exe` refusé |
| C5 | `GET /api/audit` + panneau filtrable (le `auditLog` n'était **jamais** rempli par le JS) | ✅ 3 tests ; en direct : événements réels |
| C2 | `GET /api/jobs/{id}/export/{fmt}/selected` + cases à cocher dans le tableau des champs | ✅ 4 tests ; en direct : CSV ne contenant que le champ demandé |
| D2 | `scripts/install.ps1`, `scripts/run.ps1` | ⚠️ **écrits, non exécutés** — aucun PowerShell ici |
| B5 | Éditeur de profils dans l'UI | ❌ **non fait** — reporté en vague 3 |

**Nouveau contrôle automatisé** : `tests/ui_stub_check.js` (syntaxe + chargement
sur DOM simulé + cohérence de 98 identifiants + absence de ressource externe),
intégré à `benchmarks/run_all.sh`.

**Défauts trouvés et corrigés au passage** :

1. **Le journal d'audit était scindé** entre la config réelle (lue par
   `/api/audit`) et la config isolée des tests (utilisée par le store) : des
   événements semblaient disparaître. Corrigé en réalignant `api.cfg`.
2. **Le surveillant capturait le store à l'import** — non isolé par les tests,
   il aurait pollué les données réelles. Passé en accesseurs.
3. **Compteurs cumulés non réinitialisables** sur un singleton : un appelant ne
   pouvait pas savoir ce qu'un balayage avait fait. Compteurs par balayage +
   totaux séparés, et `reset()`.
4. **`export_xlsx` attend un `DocumentResult`**, pas un dict — l'export groupé
   plantait. Aligné sur `_ensure_export`.
5. **Environnement** : les paquets Python et Tesseract ont été perdus entre les
   tours (non persistés). Restaurés depuis `requirements.lock.txt` + `apt`.

---

## Chantier en cours — Connecteur Hub (2026-10-18)

Tâche transversale demandée en complément des vagues : un **hub d'intégration**
qui relie les documents traités aux systèmes qui doivent les recevoir, sans
jamais simuler une intégration qui n'existe pas.

### Livré et testé (486 tests au total, 0 échec)

| Phase | Livrable | Vérifié |
|---|---|---|
| 2 | `contract.py` — 4 modes d'intégration, 8 états, 13 capacités, `SubmissionResult` (jamais `accepted=True` sans preuve) | 29 tests |
| 3 | `registry.py` + `hub.py` — adaptateurs vs instances, persistance atomique, désactivation non destructrice | idem |
| 4 | `mapping.py` — règles explicites, suggestions **jamais appliquées seules**, dates/décimales/unités, versionnement, traçabilité | 36 tests |
| 5 | `forms.py` — 10 types de champs, règles, versions, comparaison, trames douane/escale (bases de travail, non officielles) | 27 tests |
| 6 | `simulated.py` — simulateur local, `is_real_external_system=False`, index d'idempotence, panne simulable | inclus |
| 8 | `validation.py` — écran avant transmission, niveaux de risque, confirmation humaine | 21 tests |
| 9 | `transmission.py` — clé d'idempotence, rapprochement avant reprise, reprise auto ≤ 3 seulement sur échec technique, anti-doublon | 19 tests |
| UI | rubrique « Connecteurs » — 12 sous-menus, assistant 9 étapes, écran de validation, hors ligne | vérifs statiques |
| API | 35 routes `/api/connectors/*` | 36 tests d'intégration |

### Parcours complet exécuté en réel

Import d'un document → OCR (Tesseract) → champs extraits → mapping par règles
explicites → validation (3 champs obligatoires manquants détectés,
transmission refusée avec 409) → règles corrigées → confirmation humaine →
transmission acceptée (`DEMO-2026-00001`) → statut `accepted` → accusé de
réception → nouvel envoi du même contenu : **1 seule tentative, aucune reprise**
(`send_skipped_duplicate`). Export mode C : CSV + tableau de correspondance +
JSON de traçabilité.

### Défauts trouvés et corrigés dans mon propre code

1. `POST /api/connectors/preview` était capturé par `POST /{connector_id}` —
   les routes littérales doivent précéder les routes paramétrées (erreur déjà
   rencontrée par ailleurs, reproduite ici).
2. L'anti-doublon empêchait le doublon d'enregistrement mais **renvoyait quand
   même les données** : `attempts` montait à 3. Corrigé par un drapeau
   `needs_send` + garde-fou dans `send()`.
3. Le rapprochement par clé d'idempotence était impossible : `get_acknowledgement`
   ne cherchait que par référence. Ajout de la recherche par clé.
4. `status` est une **méthode** du contrat, pas une propriété.
5. `export` n'existe que sur le mode C : appel générique → `AttributeError`.
   Remplacé par une garde de capacité.
6. Le type de champ n'était pas validé à la construction ; un formulaire déclaré
   localement n'était pas utilisable comme cible de mapping.

### Défauts d'interface trouvés et corrigés (au contrôle de rendu)

1. **La page ne affichait qu'un texte** : une chaîne JS non terminée (guillemet
   interne non échappé, puis chaîne multi-lignes en `"`) faisait échouer le
   **troisième** bloc `<script>` — donc tout le module du hub. Le contrôle
   statique ne vérifiait que le premier bloc : il passe maintenant en revue
   **tous** les blocs (3), et intègre un contrôle de rendu qui exécute le
   module sur un DOM simulé branché sur l'API réelle (21 contrôles :
   12 sous-menus + 9 étapes de l'assistant).
2. **Le sous-menu « Configuration » restait vide** : `show()` ne l'appelait
   jamais. Idem pour « Flux d'intégration ».
3. **L'assistant restait bloqué** aux étapes « test » et « essai » : le bouton
   « Suivant » lançait l'action puis faisait `return` sans avancer.
4. `/api/jobs` renvoie une **liste**
5. **Le contrôle de rendu se déclarait « ignoré » à tort** : le harnais
   traitait comme un échec les panneaux « Connecteurs actifs » et
   « Configuration » lorsqu'aucun connecteur n'est configuré (état vide
   légitime, message `cnx-empty`), sortait en code 1, et le message annonçait
   alors « serveur local absent ». Les états vides explicites sont désormais
   acceptés, et l'erreur réelle est affichée (`API locale injoignable (ECONNREFUSED)`).
   Les fichiers temporaires du contrôle sont supprimés en fin d'exécution.

### Non fait (à documenter, pas à simuler)

- **Phase 7 — connecteurs réels** : aucun accès autorisé ni documenté. Les
  noms de champs réels (`external_name`), la méthode d'authentification et la
  version d'interface restent à obtenir auprès de chaque organisme.
- **Contrôle visuel de l'interface** : aucun navigateur headless disponible ici.

---

## Audit général et perfection (2026-10-18, vagues 1 à 6)

Audit complet du projet (`docs/AUDIT.md`), puis livraison des vagues 1 à 6 du
plan de correction. Chaque constat est tracé à sa preuve.

### Fichiers créés

| Fichier | Contenu |
|---|---|
| `docs/AUDIT.md` | audit : 9 constats A (défauts), 8 constats B (améliorations), preuves fichier:ligne, plan en 7 vagues |
| `tools/sync_web_module.py` | injecte `web/connectors.js` dans `web/index.html` entre les marqueurs `CNXHUB:BEGIN/END` ; `--check` échoue si les copies divergent ; vérifie la syntaxe du bloc avant d'écrire |
| `tests/test_web_module_sync.py` | 5 tests : synchronisation, marqueurs, module servi identique, et garde-fou anti-régression (`not_configured`, `c.modes`, assistant bloqué) |
| `tests/test_cli.py` | 5 tests : la CLI n'était couverte par aucun test |
| `tests/test_retention_reprise.py` | 8 tests : rétention et reprise, enfin câblées |
| `tests/test_audit_fixes.py` | 7 tests : permissions du coffre, avertissement de bind |

### Fichiers modifiés

| Fichier | Changement |
|---|---|
| `web/connectors.js` | réaligné sur le code réellement servi (il était périmé), puis corrigé : repli `stateBadge` sur `unconfigured` |
| `web/index.html` | marqueurs `CNXHUB:BEGIN/END` ; module régénéré depuis `connectors.js` ; clé i18n `h.connectors` en fr/en/ar |
| `src/unocr/connectors/contract.py` | `TestResult` → `ConnectionTestResult` (+ hub, simulated, assisted_export, tests) |
| `src/unocr/pipeline.py` | `process_and_export` supprimé (−24 lignes) et import `export_all` retiré |
| `src/unocr/ingest.py` | nouveau `page_images(path, dpi)` — helper partagé qui journalise au lieu d'avaler |
| `src/unocr/cli.py` | utilise le helper partagé ; valide le chemin d'entrée (code 2, plus de traceback) ; nouvelle commande `clean` ; `diagnose` rapporte ses échecs |
| `src/unocr/storage.py` | `cleanup_temp()` supprime le job (plus seulement `work/`), conserve l'audit, accepte `days`/`dry_run`, renvoie la liste |
| `src/unocr/api.py` | `GET /api/jobs/stale`, `POST /api/admin/cleanup`, avertissement de bind au démarrage |
| `src/unocr/connectors/secrets.py` | échec du `chmod` journalisé ; `describe()` expose `vault_file_permissions` / `vault_file_secure` |
| `src/unocr/connectors/registry.py`, `direction.py` | 3 fonctions mortes et leurs imports retirés |
| `tests/ui_stub_check.js` | garde-fou de taille (plafond 800 Ko), testé par abaissement temporaire |
| `docs/API.md` | 74 routes documentées (2 nouvelles), noms de paramètres alignés sur le code |

### Bugs réellement corrigés (pas seulement du nettoyage)

1. **Page muette** : le module du hub n'était pas celui de `web/connectors.js` —
   la copie servie avait les correctifs, le fichier non (A1).
2. **`stateBadge("not_configured")`** : troisième variante de la confusion d'état ;
   l'écran Configuration affichait la clé brute au lieu de « Non configuré » (A8).
3. **`unocr process` sur un chemin absent** : traceback brut de 40 lignes (A9).
4. **Rétention inerte** : `security.retention_days` ne déclenchait rien (A3).
5. **Reprise invisible** : `retryable_jobs()` n'était appelé nulle part (A4) —
   au premier appel sur le serveur réel, **2 jobs bloqués ont été trouvés**.
6. **Coffre de secrets** : un `chmod` en échec passait sous silence (A7).

### Vérifications

- Suite complète : **511 passed / 0 failed** (328,86 s), contre 486 avant l'audit.
- `ruff check .` : All checks passed.
- `node tests/ui_stub_check.js` : tout OK — 3 blocs de script, 164 identifiants,
  aucune ressource externe, 647 Ko (plafond 800), **21 contrôles de rendu**.
- Synchronisation web testée dans les deux sens : divergence détectée (code 1),
  injection effective, état restauré.
- Nouvelles routes vérifiées sur le serveur réel après redémarrage :
  `/api/jobs/stale` → 2 jobs trouvés ; `/api/admin/cleanup?dry_run=true` →
  `retention_days: 30` ; `/api/connectors/secrets/status` → nouveaux champs.

### Reste ouvert

- **B1** : l'i18n de la rubrique Connecteurs (272 fragments non traduits).
- **B5** : couverture de code non mesurable ici (`pytest-cov` absent, pas de réseau).
- `data/jobs` conserve les répertoires des sessions de test : à purger avec
  `unocr clean --days 0` si l'utilisateur le souhaite (commande désormais
  opérationnelle).

---

## Parcours documentaire de bout en bout — phase API (2026-10-18)

**Exigence du prompt** : 15 étapes, chacune visible dans l'interface avec un état
explicite, et un scénario de référence (facture + connaissement + liste de
colisage) allant de l'import au classeur Excel, avec reprise après erreur.

### Ce qui est fait et vérifié

**Le classifieur est désormais branché dans le pipeline (étape 4).** Avant ce
tour, la classification n'existait qu'en module isolé : l'extraction utilisait
**toujours** le profil générique, quel que soit le document. Le classifieur
s'exécute maintenant après l'OCR et **choisis le profil** d'extraction. Le
profil nommé par l'utilisateur reste prioritaire — la classification ne le
contourne jamais. Relevé sur les trois documents de référence :

| document | catégorie retenue | confiance | profil appliqué | champs extraits |
|---|---|---|---|---|
| facture | `invoice` | 0,86 | `invoice` | 17 |
| connaissement | `bill_of_lading` | 0,91 | `port_bl` | 37 |
| liste de colisage | `packing_list` | 0,81 | `packing_list` | 19 |

**12 routes API montées** : `/api/document-types`, `/api/jobs/{id}/classify`,
`GET|PATCH /api/jobs/{id}/classification`, `POST|GET /api/dossiers`,
`GET|DELETE /api/dossiers/{id}`, `POST|DELETE /api/dossiers/{id}/pieces[…]`,
`POST /api/dossiers/{id}/state`, `GET /api/dossiers/{id}/coherence`,
`POST /api/dossiers/{id}/package`, `GET /api/dossier-profiles`.

**L'état du dossier est déduit, jamais posé.** `_etats_documents()` lit le
statut réel de chaque job et de ses champs (`detected` / `ambiguous` /
`invalid` → révision requise ; `validated` → validé). Recalculé à chaque
mutation et à chaque lecture de synthèse.

### Défauts réels trouvés par le scénario de référence — tous corrigés

1. **`multiline` était déclaré dans le schéma des profils mais jamais
   implémenté.** Un connaissement déclarant deux conteneurs n'en gardait
   qu'un : le second était invisible pour le contrôle de cohérence.
   `apply_profile` collecte maintenant toutes les occurrences, dédoublonnées
   et réunies par ` | `.
2. **Les séparateurs de milliers perdaient la valeur.** `GROSS WEIGHT: 12 000 KG`
   ressortait en `12` : le motif du profil ne connaissait que `\d+(?:[.,]\d{1,3})?`.
   Le contrôle de cohérence détectait donc une divergence sur des valeurs
   fausses. Motifs corrigés + normalisation `amount` → `12000`.
3. **`INVOICE_NO_RE` capturait des mots-clés.** « NOTIFY PARTY » fournissait
   `TIFY`, et « B/L No » fournissait le numéro de connaissement comme référence
   de facture. Deux garde-fous : mot-clé délimité par `\b`, **et** valeur
   capturée qui ne doit pas être elle-même un mot-clé (sinon
   « COMMERCIAL INVOICE » faisait capturer `INVOICE`).
4. **`verifie_conteneurs` ne coupait pas sur ` | `**, le séparateur
   multi-valeurs des profils.
5. **La reprise d'un job détruisait les corrections humaines.** `_run_job`
   réécrivait `result.json` sans tenir compte des validations déjà portées.
   Les décisions (`confirmed_value`, `corrected_value`, `status`) sont
   maintenant relues avant traitement et réappliquées après, avec un
   événement d'audit `field_decisions_restored`.

### Résultats mesurés

**Scénario de référence, serveur réel (uvicorn, port 8124)** — trois documents
importés puis traités **un par un** :

```
facture    -> job_1abd049d0738 done      invoice            conf=0.86 profil=invoice
bl         -> job_0ea589ef62de done      bill_of_lading     conf=0.91 profil=port_bl
colisage   -> job_3c450cd73272 done      packing_list       conf=0.81 profil=packing_list
dossier dos_87a1e7ab9a97 : 3 pièces, état = revision_requise
[anomalie    ] poids_divergent:gross_weight  écart 1500.00 / moyenne 12750.00 (11,8 %)
[avertissement] conteneur_absent:container_number->packing_list  TGHU7654321
transmissible = True (aucun blocage)
xlsx 17924 o. | json 15434 o. | zip 20930 o. — 3 documents, 2 anomalies, 2 pièces manquantes
audit document_classified : 3 entrées (une par document, avec confiance)
```

L'état `revision_requise` est **déduit** de l'anomalie de poids : le dossier
n'est jamais déclaré valide tant qu'un constat reste à trancher.

**Tests** : `tests/test_parcours_bout_en_bout.py` — 3 tests, tous verts. Le
premier couvre les 15 étapes ; le second prouve qu'une reprise après panne
conserve l'original **et** la correction humaine ; le troisième vérifie qu'un
job figé remonte dans `/api/jobs/stale`.

**Suite complète : 555 passed / 23 failed.** Les 23 échecs sont **tous**
environnementaux : le binaire Tesseract a disparu du bac à sable entre les
tours et `apt` exige les droits root. Aucun moteur raster → les documents
image ne produisent aucun texte → champs non détectés, direction non détectée.
Aucune régression : les modules touchés (profils, extraction, classification,
cohérence, dossier, paquet) totalisent 134 passed / 7 failed, les 7 étant des
fixtures photo.

### Reste ouvert

- **Interface** : aucune des 12 routes n'est encore affichée dans `web/`. Les
  étapes 4, 8, 11 et 13 existent côté API mais restent invisibles pour
  l'utilisateur.
- **Segfault sous charge** : avec `jobs.workers = 2`, trois imports rapprochés
  lancent trois pipelines simultanés et le serveur se termine par un
  *segmentation fault* (≈1,4 Go de RAM disponible). Le traitement séquentiel
  fonctionne. À traiter par une file d'attente bornée, pas par un changement
  de la valeur par défaut.
- Les 23 échecs OCR se résoudront au rétablissement de Tesseract.

---

## Parcours documentaire — phase interface (2026-10-18)

**L'exigence du prompt** : « chaque étape visible dans l'interface avec un état
explicite et un résultat vérifiable ». Les étapes 4, 8, 11 et 13 existaient en
API mais restaient invisibles pour l'utilisateur. C'est ce que cette phase
corrige.

### Ce qui a été fait

**Un onzième onglet « Parcours documentaire »** (`tab-dossier`), et un module
JS dédié. Architecture respectée : inspection de l'existant avant toute
modification, réutilisation des classes CSS (`.badge`, `.card`, `.stat-row`,
`.anom`, `.pill`), des helpers (`api()`, `esc()`, `toast()`) et du mécanisme de
navigation (`.hidden` + `page-enter`, `PAGE_META`).

**Source unique, comme pour le Connecteur Hub.** Le module vit dans
`web/dossier.js` et est injecté dans `web/index.html` par
`tools/sync_web_module.py`, entre les marqueurs `DOSSIER:BEGIN` / `DOSSIER:END`.
L'outil a été généralisé pour gérer les deux modules sans casser son contrat
existant. `tests/test_web_module_sync.py` passe toujours, et un test dédié
vérifie en plus que les deux copies du nouveau module rest synchronisées.

Ce que la page montre, et d'où vient chaque donnée :

| Bloc | Source | Ce qui est affiché |
|---|---|---|
| Nouveau dossier | `POST /api/dossiers` | libellé + profil, avec le rappel que le profil est une convention |
| Dossiers existants | `GET /api/dossiers` | libellé, profil, nombre de pièces, **état déduit**, version |
| Types reconnus | `GET /api/document-types` | version du classifieur, catégories, **et celles sans indice** |
| Pièces | synthèse du dossier | fichier, catégorie, confiance, empreinte, retrait motivé |
| Pièces attendues | profil | requis / optionnel, présent ou non |
| Cohérence | `GET /api/dossiers/{id}/coherence` | un badge de gravité par constat, le détail, **les valeurs relevées**, le statut `a_trancher` |
| Paquet | `POST /api/dossiers/{id}/package` | xlsx / json / zip, taille réelle, anomalies, pièces manquantes |

Deux formulations ont été choisies à dessein : un constat non tranché
s'affiche comme `a_trancher`, jamais comme résolu ; et un paquet généré
s'affiche avec la mention qu'il n'est **ni validé ni envoyé** — ce sont des
décisions humaines séparées.

### Défauts trouvés en route — tous corrigés

1. **Apostrophe dans une chaîne JS** : `« le document n'est pas supprimé »`
   coupait la chaîne et rendait le module entier invalide. Révélé par
   `node --check`, pas par la lecture. Corrigé avec l'apostrophe
   typographique.
2. **`const module`** dans le harnais de test entrait en conflit avec l'objet
   `module` de CommonJS et empêchait node de charger le fichier.
3. **Mon harnais lui-même avait trois défauts**, qui masquaient du vrai
   travail : il lisait `dossierCoh` là où le module écrit `dosCoh` ; son
   `innerHTML` simulé ne faisait pas exister les identifiants qu'il contenait ;
   et il traitait `/api/jobs` comme un objet alors que la route renvoie une
   **liste**. Les trois corrigés — sans quoi le harnais aurait validé une page
   muette.

### Résultats mesurés

**32 contrôles de rendu, tous verts**, module servi sur DOM simulé branché sur
l'API réelle du serveur de prévisualisation (port 8123) :

```
loadAll, types de documents, version du classifieur
catégories sans indice signalées, sélecteur de profil rempli
liste des dossiers, création (POST réel), message de succès
ouverture d'un dossier : pièces, pièces attendues, cohérence, paquet
profil présenté comme une convention, paquet présenté comme non envoyé
dossier vide annoncé comme vide
analyse de cohérence, badge de gravité, a_trancher, valeurs relevées
nombre de constats, transmissibilité annoncée, état = révision et non « terminé »
génération xlsx (POST réel), taille réelle affichée
ZIP sans les originaux, format inconnu refusé par l'API avec message affiché
échec de génération = message d'erreur, pas un succès
```

**Contrôles statiques** (`node tests/ui_stub_check.js`) : 7 + 21 (hub) + 32
(parcours) = 60 contrôles, tous verts. Fichier unique à 670 Ko (plafond 800).

**Tests** : `tests/test_ui_dossier.py` — 2 tests verts. `ruff` All checks
passed.

**Suite complète : 557 passed / 23 failed.** Les 23 échecs sont **les mêmes
qu'avant cette phase**, intégralement dus à l'absence du binaire Tesseract :
documents image → aucun texte → champs non détectés. Aucune régression.

### Ce qui n'a pas pu être contrôlé ici

À dire clairement, conformément à l'exigence du prompt :

- **rendu visuel** (polices, couleurs, espacement, thème clair/sombre) ;
- **clavier** (tabulation, `j`/`k`, Entrée) ;
- **mobile et lecteurs d'écran** ;
- **les 21 contrôles du Connecteur Hub et les 32 du parcours** ont été faits
  sur un **DOM simulé**, pas dans un navigateur : ils prouvent que le code
  produit les bons éléments et les bonnes données, pas que l'œil les voit
  bien.

---

## Parcours documentaire — phase form builder (étape 12, 2026-10-18)

### Ce qui a été fait

**`src/unocr/formulaire.py` — nouveau module.** Il décrit la structure des
données qu'un dossier porte : quels champs, dans quel ordre, d'où vient chaque
valeur, ce qui reste à remplir.

La règle centrale : **un champ n'existe que si une valeur a réellement été
extraite**, ou si un humain l'a ajouté explicitement. Rien n'est inventé pour
« compléter » un formulaire. Un document sans champ reconnu n'ajoute rien, et
un formulaire vide s'affiche comme vide.

Trois origines, toujours affichées à côté de la valeur : `extrait` (avec le
document source et le nom du champ), `ajoute` (humain, tracé comme tel),
`calcule`. Persistance JSON atomique via `FormulaireStore`, avec le même
assainissement de chemin que les autres magasins.

**9 routes API** : `GET /api/formulaire-types`,
`POST|GET /api/dossiers/{id}/formulaire`, `GET /api/formulaires`,
`GET /api/formulaires/{id}`, `GET /api/formulaires/{id}/apercu`,
`POST|DELETE|PATCH /api/formulaires/{id}/champs[/{key}]`.

**Le form builder est distinct de `connectors/forms.py`.** Celui-là décrit des
formulaires destinés à des systèmes externes ; celui-ci décrit la structure
interne d'un dossier. Aucun endpoint, aucune soumission, aucun format officiel
prétendu. L'interface le dit explicitement à l'utilisateur.

**Interface** : un bloc « Formulaire du dossier » dans l'onglet existant, plus
le module `web/formulaire.js` (source unique, troisième module enregistré dans
`tools/sync_web_module.py`). Ouvrir un dossier charge son formulaire.

### Deux défauts d'extraction révélés par le form builder

Le formulaire met côte à côte **toutes** les valeurs extraites d'un dossier :
deux défauts qui passaient inaperçus champ par champ sont devenus visibles.

1. **`QTY_UNIT_RE` capturait « 000 » dans « 12 000 KG ».** Le regard derrière
   n'interdisait qu'un caractère de mot, pas un chiffre suivi d'un séparateur.
   Corrigé par un second regard derrière **et** par l'acceptation des
   séparateurs de milliers dans le nombre — sinon la correction rendait la
   quantité introuvable au lieu de la rendre juste.
2. **`packing_list_number` capturait « INVOICE »** depuis la ligne suivante
   (« PACKING LIST / Invoice ref: … »). Même garde-fou que celui déjà appliqué
   à `INVOICE_NO_RE` : la valeur capturée ne doit pas être elle-même un
   mot-clé. Le champ reste maintenant vide quand la liste de colisage ne porte
   pas son propre numéro — mieux vaut rien qu'une valeur qui n'existe pas.

### Le piège de la copie dupliquée, une seconde fois

J'ai d'abord câblé le chargement du formulaire en modifiant `web/index.html`
directement. `tools/sync_web_module.py` a ensuite **écrasé** cette
modification en réinjectant `web/dossier.js`. Le harnais l'a détecté
immédiatement (« ouvrir un dossier charge aussi le formulaire » en échec).
Correction appliquée dans la source, `dossier.js`, puis réinjectée. C'est le
même piège que celui qui avait rendu la page Connecteurs muette : **la source
unique est le fichier `.js`, jamais `index.html`.**

### Résultats mesurés

**Scénario réel sur serveur (port 8123)** — trois documents importés et
traités, dossier constitué :

```
formulaire frm_dos_9c5fc00f0f3d — 21 champs
  invoice_number  identifier  extrait  INV-2024-118
  gross_weight    number      extrait  12000
  net_weight      number      extrait  11500
  bl_number       identifier  extrait  BL-2024-0456
  … (17 autres)
ajout humain : reference_dossier, requis → requis manquants : [reference_dossier]
faute de frappe « invoice_numbre » → refus 422 « champ inconnu »
relecture disque : 22 champs, ajout conservé
aperçu texte : 115 lignes
```

**37 contrôles de rendu, tous verts** (module servi sur DOM simulé, API
réelle), dont 4 nouveaux pour le form builder : le module est exposé, ouvrir un
dossier charge le formulaire, le bloc se rend, et il affirme explicitement
qu'il ne transmet rien.

**Tests** : `tests/test_formulaire.py` — 29 tests verts, dont 4 de
non-régression sur les deux défauts d'extraction. `ruff` All checks passed.

**Suite complète : 586 passed / 23 failed.** Les 23 échecs sont toujours les
mêmes, intégralement dus à l'absence du binaire Tesseract. Aucune régression.

---

## Parcours documentaire — archivage et traçabilité (étape 15)

**Ce qui a été livré.** `src/unocr/tracabilite.py` (archivage, trace, synthèse,
lecture du journal), trois routes API (`POST /api/dossiers/{id}/archiver`,
`GET /api/dossiers/{id}/trace`, `GET /api/tracabilite/avertissement`), le
module d'interface `web/tracabilite.js` (4ᵉ module enregistré dans
`tools/sync_web_module.py`), `tests/test_tracabilite.py` (17 tests) et
`tests/test_tracabilite_api.py` (12 tests).

### La contrainte structurante, et comment elle est tenue

Le journal applicatif **n'est pas une preuve inviolable** : c'est un fichier
texte écrit par l'application, modifiable par quiconque a un accès
administrateur à la machine. L'avertissement est donc porté par le module
métier (`AVERTISSEMENT_TRACABILITE`) et renvoyé par **chaque** réponse de
trace — pas une fois pour toutes dans une page d'aide. Dans l'interface, il
est rendu **en tête de la trace**, hors de tout repli, accompagné de deux
listes : ce que l'archivage conserve, ce qu'il ne fait pas. Deux tests
négatifs vérifient qu'aucune garantie ne promet « inviolable », « inaltérable »
« infalsifiable » ni « preuve ».

L'archivage est un **état**, pas une suppression : rien n'est effacé, et les
pièces manquantes ne sont pas créées — le dossier archivé le signale.

### Trois défauts trouvés en cours de route, tous réels

1. **La trace fuitait entre dossiers.** Elle remontait les événements du
   dossier *et* de ses `job_id`. Mais un même document peut être joint à
   plusieurs dossiers : les « pièce ajoutée » des *autres* dossiers
   apparaissaient dans celle-ci. Le store réel l'a montré (deux
   `dossier_piece_added` datés de 20 minutes plus tôt, appartenant à
   d'autres dossiers). Correctif : un `dossier_id` explicite l'emporte sur le
   `job_id`. Verrouillé par
   `test_trace_exclut_le_rattachement_du_meme_document_ailleurs`.

2. **Consulter un dossier archivé le désarchivait.** `recalculer_etat` déduit
   l'état des faits, et l'appliquait sans garde : afficher un dossier archivé
   le faisait revenir « incomplet », en écrivant un `state_changed` au
   passage. L'archivage ne tenait donc qu'aussi longtemps qu'on ne regardait
   pas. `ORDRE_ETATS` existait avec le commentaire « utilisé pour empêcher un
   retour en arrière silencieux » — **et n'était utilisé nulle part**.
   Correctif : `ETATS_VERROUILLES = {EXPORTE, ARCHIVE}`, et le recalcul s'arrête
   là. Le docstring de `recalculer_etat` le promettait déjà ; le code ne
   l'appliquait pas. Verrouillé par
   `test_archivage_survit_a_une_relecture_du_dossier`.

3. **Le module traçabilité n'avait nulle part où s'écrire.** `dessineDossier`
   réécrit tout le contenu de `dossierDetail`, mais ne créait aucun conteneur
   pour les modules frères : `FormulaireUI` comme `TracabiliteUI` trouvaient
   `null` et retournaient sans un mot. Le form builder de l'étape 12 était
   donc **muet en pratique** — le harnais vérifiait que `charge()` était
   appelé, pas qu'un conteneur existait. Correctif : `dossier.js` crée
   `#dossierForm` et `#dossierTrace` à chaque rendu.

### Résultats mesurés

**Scénario réel sur serveur (port 8123)** — deux dossiers partageant un même
document, l'un archivé :

```
trace de A : job_created, job_done, dossier_created, dossier_piece_added,
             dossier_state_changed, dossier_state_forced, dossier_archived
             → 1 seul « pièce ajoutée », celui de A
trace de B : aucun archivage, aucun rattachement de A
consultation ×3 d'un dossier archivé → état « archive », 0 state_changed
double archivage → HTTP 409 « ce dossier est déjà archivé »
dossier inconnu → HTTP 404
```

**48 contrôles de rendu, tous verts** (module servi sur DOM simulé, API
réelle), dont 11 nouveaux : module exposé, ouverture du dossier chargeant la
trace, avertissement affiché à côté de la trace et nommant qui peut modifier
le journal, limites et garanties listées, dossier archivé ne proposant plus de
l'archiver, état forcé distingué d'un état déduit, archivage présent dans la
trace comme événement.

**Tests** : 17 tests de traçabilité + 12 tests d'API. `ruff` All checks
passed. **Suite complète : 615 passed / 23 failed** — les 23 mêmes échecs,
intégralement dus à l'absence du binaire Tesseract. Aucune régression.

---

## Parcours documentaire — transmission du dossier (étape 14, 2026-10-18)

**Le chaînon manquant.** `POST /api/connectors/transmit` ne portait que sur un
`job_id` : un dossier entier ne pouvait pas partir, il fallait transmettre ses
documents un par un et perdre la structure. Entre l'étape 13 (paquet de
données) et l'étape 15 (archivage), il manquait donc l'envoi du dossier.

**Ce qui a été livré.** `src/unocr/transmission_dossier.py`, trois routes API
(`GET|POST /api/dossiers/{id}/transmission`,
`GET /api/dossiers/{id}/transmissions`), le module d'interface
`web/transmission.js` (5ᵉ module), `tests/test_transmission_dossier.py`
(18 tests) et `tests/test_transmission_dossier_api.py` (12 tests).

### Pourquoi un mapping, et pas un envoi direct des clés du dossier

Ma première version envoyait les clés du formulaire de dossier telles quelles
(`invoice_number`, `gross_weight`). Le connecteur les a **rejetées** : le
système cible attend `containerNo`, `bl_reference`, `grossWeight`. Le rejet
était le bon comportement, mais il révélait une erreur de conception de ma
part — envoyer des clés que personne ne comprend produirait un rejet, ou
pire, un enregistrement silencieusement faux.

Le dossier passe donc par le même mécanisme de correspondance qu'un document.
**Sans formulaire cible ni règle de mapping, la transmission est refusée** :
on ne devine jamais la structure attendue par le système cible. Un champ du
dossier sans correspondance bloque aussi — il serait perdu en silence.

Deuxième correction, plus subtile : j'avais d'abord réutilisé
`MappingEngine.apply()`. Il produit une confiance `explicit` ou `exact` selon
l'origine de la règle et **perd l'information « validée par un humain »**. Or
c'est exactement cette information qui doit faire bloquer le `Validator` :
une valeur sortie de l'OCR et non relue ne doit pas partir vers un système
réel comme si elle était confirmée. Le mapping est donc refait dans le
module, en conservant la confiance, et en réutilisant `apply_transform` pour
rester cohérent avec les transformations du hub.

### La règle absolue, et comment elle est tenue

`SENT` n'est pas `ACCEPTED`. Tant qu'aucune preuve d'acceptation n'est
revenue, le système ne suppose jamais que le dossier a été enregistré chez
le cible. `CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS` est renvoyé par chaque
réponse — aperçu, envoi, historique — et rendu dans l'interface **hors de
tout repli**, à côté de l'écran d'envoi. Les messages de retour distinguent
`accepted` (avec référence), `sent` (attente de preuve),
`pending_confirmation` (issue inconnue, à rapprocher) et les échecs.

L'aperçu est un **GET** : il n'envoie jamais rien. L'envoi est un POST, avec
confirmation humaine explicite quand le niveau de risque l'exige — et le refus
vient du serveur, pas de la page. Deux envois du même contenu produisent la
même clé d'idempotence : le second n'est pas renvoyé.

### Trois défauts trouvés en cours de route

1. **`Transmission` ne portait pas de dossier.** Le modèle avait un `job_id`
   et rien d'autre. Étendu avec un `dossier_id` rétrocompatible
   (`from_dict` en `.get()`), et `idempotency_key` intègre dorénavant le
   dossier — sans quoi deux dossiers au contenu identique (deux dossiers
   vides, par exemple) auraient partagé la même clé, et le second envoi
   aurait été silencieusement évité.
2. **`DossierStore.journaliser` n'existait pas.** `_journalise` est privé et
   travaille sur un dossier déjà chargé ; un module voisin n'a qu'un
   identifiant. Une porte d'entrée publique a été ajoutée, ce qui garantit
   aussi que l'événement porte bien le préfixe `dossier_`.
3. **`dossier_transmitted` absent de `EVENEMENTS_DOSSIER`.** Le libellé
   existait mais pas le tuple : la transmission était tracée dans le journal
   et **invisible dans la trace du dossier**. Un test l'a attrapé.

### Le piège de l'environnement, pas du code

En cours de route, le bac à sable a perdu plusieurs paquets (`ruff`,
`reportlab`, `segno`, `fastapi`…). La suite est passée de 23 à 26 échecs sans
que le code ait changé. Réinstallé depuis `requirements.txt` — retour aux 23
échoucs de référence. À garder en tête : **un échec nouveau n'est pas
forcément une régression**, il faut d'abord vérifier l'environnement.

Par ailleurs, un script de repro que j'avais écrit hors pytest a pollué le
magasin réel `data/jobs` avec `job_f`/`job_b`, ce qui a fait ramasser au
harnais de rendu de mauvais documents de référence (« Aucune divergence
détectée »). Nettoyé. Leçon : un script de diagnostic qui touche `api.store`
doit isoler sa config, comme le fait le fixture `tmp_cfg`.

### Résultats mesurés

**Scénario réel sur serveur (port 8123)** :

```
aperçu  : transmissible=false, form_id=(aucun), 3 missing_required
          fichiers_joints=false, rappel permanent présent
envoi réel (via TestClient) : status 200, transmission dossier_id renseigné,
          renvoyé_évité=false, puis true au second appel
trace   : dossier_transmitted apparaît dans les événements du dossier
refus sans confirmation  → 409 « confirmation humaine exigée »
refus sans connecteur    → 409 « aucun connecteur opérationnel »
refus sans règles        → 409 « n'a pas de correspondance »
```

**55 contrôles de rendu, tous verts** (module servi sur DOM simulé, API
réelle), dont 7 nouveaux : module exposé, ouverture du dossier chargeant
l'aperçu, bloc rendu, rappel « envoyé n'est pas accepté », mention que les
documents ne partent pas, distinction du contenu réellement envoyé, et
confirmation humaine exigée pour l'envoi.

**Tests** : 18 tests de transmission + 12 tests d'API. `ruff` All checks
passed. **Suite complète : 645 passed / 23 failed** — les 23 mêmes échecs,
intégralement dus à l'absence du binaire Tesseract. Aucune régression.

## Audit maître et lots P0/P1/P3 (2026-10-18)

Audit mené face au cahier des charges complet, sur le code réel. Constat dressé
dans `docs/AUDIT_MAITRE.md`. Trois lots livrés, chacun testé.

### Lot 1 — P0 : sauvegarde et restauration (le trou le plus grave)

**Constat.** Le magasin (`data/jobs`, `data/dossiers`, `data/exports`,
`logs/audit.log`) était la seule trace des documents traités, des corrections
humaines et des transmissions. Aucune sauvegarde, aucune restauration. Un
`unocr clean` trop large ou un disque plein détruisait ce travail sans recours.

**Livré.** `src/unocr/backup.py` (nouveau, 265 lignes) :
- `creer_sauvegarde()` — ZIP horodaté + manifeste listant chaque fichier et son
  empreinte SHA-256. Deux sauvegardes dans la même minute ne s'écrasent pas.
- `verifier_sauvegarde()` — relit l'archive et contrôle chaque empreinte. Une
  sauvegarde qu'on ne vérifie pas est un fichier qu'on espère bon.
- `restaurer_sauvegarde()` — refuse d'écraser un magasin non vide sans `force`,
  et route `data/` vers le magasin, `logs/` vers le répertoire des journaux.
- `purger_sauvegardes()` — ne garde que les N plus récentes, sinon la sauvegarde
  finit par échouer faute de place.
- CLI `unocr backup` / `restore` / `backups`, et 4 routes `/api/backups*`.

**Deux défauts trouvés en route, tous réels.**
1. Le journal d'audit vit dans `log_dir`, **pas** dans `data_dir` : ma première
   version ne le sauvegardait pas. L'historique des transmissions aurait été
   perdu. Corrigé par des préfixes d'archive `data/` et `logs/`.
2. `restaurer_sauvegarde` extrayait tout sous `data/`, ce qui aurait mis
   l'audit au mauvais endroit — il n'aurait plus jamais été relu.

**Tests.** `tests/test_backup.py` — 16 tests, dont : archive altérée refusée,
archive sans manifeste refusée, chemin traversant (`../evasion.txt`) refusé,
restauration refusée sans `force`, arbitrages humains et journal restaurés.

### Lot 2 — P1/P3 : observabilité

**Constat.** Aucun identifiant de corrélation : une requête qui échoue ne peut
pas être rattachée à ce que l'opérateur a fait. Aucune limitation de débit :
une boucle de réimport peut saturer le magasin.

**Livré.** `src/unocr/observabilite.py` (nouveau) + deux middlewares :
- `X-Request-ID` posé avant tout traitement, repris tel quel si le client en
  fournit un de forme plausible (rejet de `<script>…`).
- Limitation par adresse cliente, fenêtre glissante (un compteur remis à zéro à
  date fixe laisse passer 2× la limite à cheval sur deux fenêtres), avec
  `Retry-After` et `retry_after` dans le corps.
- `GET /api/observabilite` expose l'état, pour diagnostiquer un 429.

**Défaut trouvé par les tests, réel et corrigé.** Ma première version limitait
**toutes** les requêtes. L'interface interroge `/api/jobs/{id}` en boucle
pendant un traitement par lot (`web/index.html:3758`) : brider ce polling
faisait échouer des traitements légitimes. La limitation ne porte donc plus que
sur les écritures (`POST/PUT/PATCH/DELETE`). Un test verrouille ce
comportement. La limite par défaut est passée de 120 à 600/min : un lot de 200
documents légitime ne doit pas être pris pour un abus.

**Tests.** `tests/test_observabilite.py` — 17 tests, dont le polling jamais
bridé, la fenêtre glissante qui libère les places, et la remise à zéro du
compteur entre deux tests (sans elle, la suite entière recevait des 429).

### Lot 3 — P3 : recherche globale

**Constat.** `/api/search` existait mais omettait `corrected_value` — la valeur
que l'opérateur retient est précisément celle qu'il veut retrouver — et ne
cherchait pas dans les dossiers.

**Livré.** `corrected_value` ajouté au corpus cherché ; les dossiers sont
cherchés en premier, avec leur état et leur nombre de pièces.

**Tests.** `tests/test_search.py` — 8 tests.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| Suite complète | 653 passed / 23 failed | **692 passed / 23 failed** |
| Nouveaux tests | — | 41 (16 + 17 + 8) |
| Rendu interface | 55 contrôles, 0 échec | **inchangé**, 168 identifiants (était 165), 707 Ko |
| `ruff check src tests tools` | clean | clean |
| Scénario obligatoire 10 étapes | — | **35/35 contrôles réussis** |

Les 23 échecs restants sont intégralement l'absence du binaire Tesseract dans
cet environnement.

### Reste ouvert

- Autorisation par rôle et cloisonnement par dossier (P2) — non traité.
- Règles de rapprochement non configurables par fichier (P2) — non traité.
- Raccourcis clavier et annulation dans la validation (P3) — non traité.
- Crash natif observé une fois (`free(): corrupted unsorted chunks`) sous 3 jobs
  concurrents, **non reproductible** en 6 tentatives. Le magasin persiste, mais
  le processus meurt. À surveiller.

## Lot 4 — règles de rapprochement configurables (P2, 2026-10-18)

**Constat.** Le moteur de cohérence annonçait « configurable » dans sa
docstring, mais une seule chose l'était : la liste des règles bloquantes. La
tolérance de pesée était un paramètre de fonction (`tolerance: float = 0.02`)
qu'aucune configuration ne pouvait atteindre, et aucune règle ne pouvait être
désactivée. Écrire « configurable » sans pouvoir configurer est pire que pas de
configuration : l'opérateur croit maîtriser des contrôles qu'il ne pilot pas.

**Livré.** Section `coherence` dans `config/default.json` :

```json
"coherence": {
  "tolerances": {"gross_weight": 0.02, "quantity": 0.05, "amount": 0.01, …},
  "regles_bloquantes": [],
  "regles_desactivees": [],
  "cles_reference": ["invoice_number"]
}
```

- `CoherenceEngine(configuration)` lit tout cela ; `tolerance(cle)` et
  `active(regle)` sont les deux points d'entrée.
- Chaque règle **se garde elle-même** avec `self.active(...)` : une règle
  désactivée se taît quel que soit l'appelant, pas seulement via `analyser()`.
- `GET /api/coherence/regles` renvoie la configuration réellement appliquée —
  tolérances, règles bloquantes, règles désactivées, clés de référence. Un
  constat qui surprend ou qui manque doit pouvoir être expliqué.
- L'explication d'un constat cite le seuil **réellement** appliqué.

**Trois défauts trouvés par les tests, tous réels.**
1. `CoherenceEngine(["règle"])` — l'ancien appel positionnel passait la liste
   des règles bloquantes en premier argument. Ma nouvelle signature l'aurait
   interprétée comme un dictionnaire de configuration, cassant tous les
   appelants existants. Corrigé par une détection de type explicite.
2. Les gardes n'étaient posées que dans `analyser()` : appeler
   `verifie_poids()` directement contournait la désactivation. Corrigé en
   déplaçant la garde dans chaque règle.
3. Un script d'insertion automatique avait placé deux gardes dans les mauvaises
   méthodes (la regex captait un docstring plus loin). Détecté par les tests,
   corrigé à la main, et `analyser()` simplifié puisque la garde vit désormais
   dans les règles.

**Tests.** `tests/test_coherence_config.py` — 18 tests : tolérance plus large
qui fait disparaître le constat, plus stricte qui le fait apparaître, seuil
annoncé dans l'explication, tolérance par clé indépendante, règle désactivée
réellement muette (y compris en appel direct), désactivation par faute de frappe
qui ne désactive rien, règle bloquante qui interdit la transmission puis
arbitrage qui la débloque, clés de référence multiples, configuration vide ou
malsaine sans crash.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_coherence_config.py` | — | 18 passed |
| `tests/test_coherence.py` | 16 passed | 16 passed (comportement par défaut inchangé) |
| Parcours bout en bout + corrections | 11 passed | 11 passed |
| Route `/api/coherence/regles` | absente | opérationnelle |

## Lot 5 — raccourcis clavier et annulation (P3, 2026-10-18)

**Constat.** L'écran de validation demandait une souris par clic, et surtout :
**aucune correction n'était annulable**. Une erreur de saisie restait dans le
dossier, à corriger par-dessus — donc deux corrections successives au lieu
d'une, et un historique qui ne dit plus laquelle était la bonne.

**Deux faux départs, écartés en inspectant le code existant.**
1. J'avais écrit un **second** gestionnaire clavier (`j/k/Entrée/o`). Il en
   existait déjà un, correct, plus haut dans le fichier. Deux gestionnaires
   auraient fait descendre le curseur de deux lignes par frappe. Supprimé ;
   seul `u` a été ajouté au gestionnaire existant.
2. J'avais fait recevoir le focus clavier à la ligne focalisée. Ça **cassait**
   `j/k` : dès que l'input avait le focus, `typing()` laissait passer la touche
   et « j » s'écrivait dans le champ au lieu de descendre. Supprimé.

**Livré.**
- `POST /api/jobs/{job_id}/fields/{name}/undo` — restitue l'état d'avant.
- L'audit traite désormais l'**état réellement remplacé** (`ancienne_valeur`,
  `ancienne_origine`, `ancien_statut`). Avant, il notait `raw_value` : annuler
  aurait restauré la valeur brute et fait perdre la normalisation du moteur.
  La valeur restaurée suit la même priorité que l'affichage (confirmée >
  corrigée > normalisée > brute).
- L'annulation est elle-même tracée (`field_correction_annulee`, avec acteur,
  motif, valeur annulée, valeur restaurée). La correction d'origine **n'est pas
  écrasée** — sinon l'historique mentirait.
- Raccourci `u` + bouton « Annuler » dans la file de révision. Le motif est
  demandé : une annulation sans explication est une trace d'audit inexpliquée.

**Tests.** `tests/test_annulation_correction.py` — 7 tests : restauration de
l'état d'avant, annulation tracée sans écraser la correction, annulation d'une
valeur normalisée qui **ne** perd pas la normalisation, refus quand il n'y a
rien à annuler, refus d'une deuxième annulation, état précédent présent dans
l'audit, champ annulé puis re-corrigé.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_annulation_correction.py` | — | 7 passed |
| Suite complète | 711 passed / 23 failed | **718 passed / 23 failed** |
| Raccourcis file de révision | j, k, Entrée, o | + `u` (annuler) |
| Correction annulable | non | oui, tracée, sans perte |

## Lot 6 — rôles et cloisonnement par dossier (P2, 2026-10-19)

**Constat.** UniOCR n'avait qu'un jeton unique et partagé. C'est du tout ou
rien : celui qui le détient lit tous les documents, valide tous les champs,
arbitre tous les constats, restaure toutes les sauvegardes. Dans un service où
un opérateur saisit, un superviseur arbitre et un auditeur consulte, ce modèle
ne décrit aucune de ces frontières. C'était le dernier P2 resté ouvert.

**Livré.** `src/unocr/rbac.py` + `data/rbac.json` (absent par défaut) :
quatre rôles ordonnés (`lecteur` < `operateur` < `superviseur` <
`administrateur`), cloisonnement par dossier, routes d'administration, jeton
régénérable, et interface (fenêtre de saisie du jeton, puce d'identité).

**Le choix structurant : inactif sans fichier.** `data/rbac.json` n'existe pas
par défaut. Dans ce cas aucune route n'exige de jeton, aucun cloisonnement
n'est appliqué, et l'application se comporte exactement comme avant. Un
déploiement existant n'a rien à migrer — et c'est verrouillé par des tests.

**Trois défauts trouvés par les tests, tous réels.**
1. **La hiérarchie des rôles n'était pas implémentée.** `a_role()` testait
   l'appartenance exacte : un `operateur` ne couvrait pas `lecteur`. Il aurait
   fallu répéter `lecteur` dans chaque rôle supérieur, et l'oublier une fois
   aurait suffi à fermer la consultation à un superviseur. Corrigé par
   comparaison des niveaux.
2. **Un créateur restreint ne voyait pas son dossier.** Un opérateur cantonné à
   « D1 » créait un dossier dont l'identifiant est généré par le système — donc
   absent de son périmètre — et ne pouvait plus l'ouvrir. Corrigé : le
   périmètre s'étend au dossier créé, et l'ajout est tracé dans l'audit.
3. **`Utilisateur` était gelé**, donc `regenerer()` ne pouvait pas remplacer un
   jeton compromis. La protection contre les modifications accidentelles porte
   maintenant sur `roles` et `dossiers` (des `frozenset`), pas sur le jeton.

**Refusé en cours de route.** J'avais commencé à insérer les gardes par script,
avec une regex qui captait un docstring plus loin : deux gardes se sont
retrouvées en plein docstring, le transformant en simple chaîne. Détecté en
relisant, corrigé à la main. Les leçons des lots 4 et 5 ont porté.

**Tests.** `tests/test_rbac.py` — 35 tests : compatibilité sans fichier (4 tests
qui vérifient que rien ne change), hiérarchie des rôles, cloisonnement, échec
fermé, jetons jamais divulgués, refus tracés, régénération et révocation,
passe-partout d'environnement, extension de périmètre.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_rbac.py` | — | 35 passed |
| Suite complète | 718 passed / 23 failed | **754 passed / 23 failed** |
| Rôles | aucun (tout ou rien) | 4 rôles hiérarchisés |
| Cloisonnement par dossier | aucun | oui, liste filtrée |
| Correction annulable | non | oui (lot 5) |
| Routes API | 91 | 118 |

## Lot 7 — le cloisonnement survit à une reprise (P0, 2026-10-19)

**Constat, trouvé en inspectant ce que le lot 6 avait laissé de côté.**
`rbac.json` vit à la racine de `data/`, donc en dehors des répertoires que le
module de sauvegarde parcourt (`jobs`, `dossiers`, `exports`…). Il n'était ni
archivé ni restauré. Scénario de catastrophe reproduit :

1. l'opérateur sauvegarde, comme documenté ;
2. le magasin est perdu (disque, suppression accidentelle) ;
3. il restaure — et croit retrouver son installation ;
4. `rbac.json` n'est pas dans l'archive : le registre redevient inactif ;
5. **l'API repasse ouverte à tous**, silencieusement.

Un cloisonnement perdu en silence est pire qu'un cloisonnement jamais mis en
place : l'opérateur prend ses décisions d'accès sur une croyance fausse.

**Correctif, deux moitiés.**

1. `rbac.json` rejoint `FICHIERS` dans `backup.py` — il est désormais archivé
   et restauré comme `audit.log`.
2. La route de restauration **recharge le registre du processus**. Sans cela,
   les droits restaurés restaient ignorés jusqu'au redémarrage : un utilisateur
   révoqué avant la sauvegarde aurait continué d'accéder à ses anciens
   dossiers après la restauration. La restauration est aussi tracée
   (`magasin_restaure`).

**Tests.** `tests/test_rbac_reprise.py` — 4 tests : l'archive contient le
fichier, le cloisonnement survit à une reprise complète, un déploiement sans
RBAC sauvegarde toujours normalement, et le processus voit les droits restaurés.
Vérifié en sens inverse : sans le correctif, 3 de ces 4 tests échouent.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_rbac_reprise.py` | — | 4 passed |
| `rbac.json` archivé | non | oui |
| Registre rechargé après restauration | non | oui |
| Suite complète | 754 passed / 23 failed | **757 passed / 23 failed** |

**Défaut trouvé en vérifiant ce lot — dans la suite de tests elle-même.** Après
ajout de `test_rbac_reprise.py`, la suite complète est passée à **81 échecs**
(alors que chaque fichier passait isolément). Cause : mon test remplaçait
`api._rbac`, état global du module, sans le restaurer — il le laissait pointant
vers un répertoire temporaire supprimé. Le RBAC restait actif, plus aucun jeton
ne résolvait, et tous les tests suivants recevaient des 401 inexpliqués.

La classe entière de bugs d'isolation est maintenant couverte par un filet dans
`tests/conftest.py` : `tmp_cfg` sauvegarde et restaure `api._rbac`. Vérifié en
réintroduisant volontairement le bug — les tests voisins passent quand même.

Leçon retenue, la même qu'aux lots 4 et 5 : **lancer la suite complète, jamais
seulement le fichier que l'on vient d'écrire.** Un test qui passe seul ne prouve
rien sur l'ensemble.

## Lot 8 — le cloisonnement se contournait par les documents (P0, 2026-10-19)

**Constat.** Le cloisonnement du lot 6 ne gardait que les routes de dossier. Je
l'ai vérifié en conditions réelles, avec deux opérateurs de périmètres
différents :

```
paul (hors périmètre)  GET /api/dossiers/<celui de marie>  -> 403   ✅
paul (hors périmètre)  GET /api/jobs/<doc du dossier>/result -> 200  ❌
```

**Le contournement.** `GET /api/jobs/{id}/result` renvoie l'intégralité du
contenu d'un document — texte, champs, tableaux, qualité, image de page — sans
passer par la route du dossier. Un utilisateur bloqué sur un dossier lisait
donc chaque document qu'il contient, et pouvait même le supprimer.

**Correctif.** Une garde au niveau du document, en aval du dossier :
`_exige_job(request, job_id)`, posée sur les 13 routes de document. Le document
doit être classé dans **au moins un dossier visible**.

**Défaut de conception dans ma propre garde, trouvé en la testant.** Ma première
version refusait dès qu'*un seul* dossier contenant le document était hors
périmètre. Un document classé dans quatre dossiers — dont trois à soi —
devenait **illisible à son propriétaire**. C'est un déni de service sur un
accès légitime, et une garde imprévisible : il suffisait à quelqu'un de classer
votre document dans son dossier pour vous en bloquer l'accès. La règle correcte
est « au moins un dossier visible » : le contenu étant le même document, y
accéder par un dossier qu'on voit n'expose rien de plus.

**Limite assumée et documentée.** Un document non classé dans aucun dossier
n'est pas cloisonnable — il n'y a personne à qui l'attribuer. Son accès est régi
par le seul rôle.

**Tests.** `tests/test_rbac.py` passe de 35 à 41 tests : lecture autorisée pour
le propriétaire sur les 6 routes, refus hors périmètre, refus de suppression,
refus tracé (`acces_refuse_document`), document multi-classé reste lisible,
document non classé régi par le rôle. Vérifié en sens inverse : garde neutralisée
⇒ 3 échecs.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_rbac.py` | 35 passed | **41 passed** |
| `GET /api/jobs/{id}/result` hors périmètre | 200 (fuite) | **403** |
| `DELETE /api/jobs/{id}` hors périmètre | 200 (fuite) | **403** |
| Document multi-classé, propriétaire | — | 200 (pas de déni de service) |
| Suite complète | 757 passed / 23 failed | **763 passed / 23 failed** |

## Lot 9 — la mitigation du crash natif, verrouillée par des tests (P1, 2026-10-19)

**Le risque restant.** Un crash natif (`free(): corrupted unsorted chunks`, puis
segmentation fault) avait été observé sous 3 jobs concurrents, dans les moteurs
natifs de rendu PDF. Il n'a jamais été reproduit — **et il ne peut pas l'être
dans cet environnement** : `tesseract` et `pdftoppm` sont absents, donc le
chemin de code concerné n'est pas exerçable. C'est la seule ligne du tableau des
risques encore ouverte, et elle le restera tant qu'une machine avec les binaires
natifs ne l'aura pas rejoué.

**Ce qui était déjà en place, et ce qui manquait.** Une mitigation existait :
un sémaphore borne le nombre de pipelines simultanés selon `jobs.workers` **et**
la RAM réellement disponible. Personne ne l'avait testée. Une mitigation non
testée est une mitigation qui peut être cassée sans que personne s'en aperçoive —
et le crash referait surface exactement là où on croyait être protégé.

**Livré.** `tests/test_concurrence_jobs.py` — 9 tests :

- bornage par la config, bornage par la RAM, jamais zéro (un sémaphore à 0
  bloquerait tout traitement sans erreur visible) ;
- comportement réel quand la sonde RAM est indisponible : **un seul pipeline**,
  choix de prudence documenté plutôt que de vitesse ;
- l'invariant central : **un job qui attend sa place reste `queued`**, jamais
  « terminé ». Un job marqué `done` sans avoir tourné produirait un résultat
  vide présenté comme valide — pire qu'un crash, parce que silencieux ;
- la place est rendue même si le job échoue ;
- charge : 12 threads × 20 écritures de résultats, aucun résultat perdu ni
  tronqué ; mises à jour de statut concurrentes ; 20 créations simultanées sans
  identifiant dupliqué.

**Deux défauts dans mes propres tests, attrapés en les exécutant.** Un
pré-acquittement du sémaphore suivi d'un `with sem:` provoquait un **deadlock**
(la suite hangait à 300 s sans rien dire) ; et un test affirmait un comportement
de repli qui n'était pas celui du code. Tous deux corrigés — le second en
documentant le comportement réel.

**Vérifié en sens inverse** : borne RAM neutralisée ⇒ 2 échecs.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_concurrence_jobs.py` | — | 9 passed |
| Mitigation du crash natif testée | non | **oui** |
| Suite complète | 763 passed / 23 failed | **773 passed / 23 failed** |
| Crash natif reproductible | non | **non** (binaires natifs absents) |

## Lot 11 — la provenance manquait des exports (P2, 2026-10-19)

**Constat.** En auditant le chemin d'export — livrable explicite de l'étape 9 du
scénario (« fichier Excel avec données validées, références documentaires et
anomalies non résolues ») — j'ai trouvé un trou réel :

```
colonnes Champs : name, label, raw_value, normalized_value, corrected_value,
                  confirmed_value, confidence, engine_confidence, status, page
  origine  présent ? False
  source   présent ? False
  zone     présent ? False
```

Le modèle `FieldValue` porte pourtant `value_origin` (extrait / normalisé /
règle métier / validé par un humain), `source` (ocr | native | rule | user |
digital) et `bbox` (la zone sur le document). Aucun des trois n'était exporté en
XLSX ni en XML.

**Pourquoi c'est un défaut et pas un détail.** Le cahier des charges exige une
« provenance complète par champ » et des « alertes expliquées avec zones
sources ». Sans `origine`, un export présente sur le même plan une transcription
OCR et une valeur tranchée par un humain : le lecteur ne peut plus distinguer ce
qui a été **extrait** de ce qui a été **interprété**. Sans `zone`, une alerte ne
peut pas être vérifiée sans relire tout le document. Le CSV, lui, exportait déjà
`source` — les deux formats n'étaient donc pas cohérents entre eux.

**Correctif.**

- `_origine()` rend l'origine **en clair** : « règle métier », « validé par un
  humain ». « corrected » seul ne dit pas si c'est une règle ou une faute de
  frappe du concepteur.
- `_zone()` rend la zone source, ou chaîne vide — **jamais une zone inventée**.
- XLSX, CSV et XML exportent les trois ; le JSON sérialisait déjà tout le modèle.
- CSV et XLSX sont désormais alignés colonne pour colonne.

**Tests.** `tests/test_export_provenance.py` — 10 tests : les trois formats
portent la provenance ; deux champs de valeur affichée comparable restent
distinguables ; la zone est exportée puis laissée vide quand le moteur ne l'a
pas fournie ; CSV et XLSX alignés ; JSON complet ; et une valeur extraite
hostile (`=SOMME(A1:A9)" ; rm -rf /`) neutralisée plutôt qu'exécutée.

Vérifié en sens inverse : provenance retirée ⇒ 7 échecs.

### Résultats mesurés

| Contrôle | Avant | Après |
|---|---|---|
| `tests/test_export_provenance.py` | — | 10 passed |
| XLSX : origine / source / zone | absents | **présents** |
| XML : origin / source / zone | absents | **présents** |
| CSV et XLSX alignés | non | **oui** |
| Suite complète | 773 passed / 23 failed | **783 passed / 23 failed** |
| Scénario 10 étapes | 35/35 | **35/35** |
