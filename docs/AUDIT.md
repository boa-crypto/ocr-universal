# Audit général — état réel du projet (2026-10-18)

Audit effectué sur le code tel qu'il est dans le workspace, sans supposer que ce
qui est déclaré fonctionne. Chaque constat indique sa preuve (fichier:ligne) et
la façon de le vérifier.

## 1. Méthode

| Contrôle | Outil / commande | Résultat |
|---|---|---|
| Suite complète | `pytest -q` (arrière-plan) | **486 passed / 0 failed** en 331,38 s |
| Hub seoul | 6 fichiers de tests connecteurs | **168 passed** en 23,50 s |
| Style / imports | `ruff check .` | **All checks passed** |
| Surface API réelle | introspection `app.routes` | **80 routes** : 72 sous `/api/` (dont **35** `/api/connectors/*`) + 8 hors API (`/`, `/docs`, `/openapi.json`, `/redoc`, `/icon.svg`, `/manifest.webmanifest`, `/sw.js`, `/docs/oauth2-redirect`) |
| Documentation API | comparaison routes ↔ `docs/API.md` | 72/72 documentées, mais **31 avec un nom de paramètre faux** (constat A5) |
| Code mort Python | recherche de définitions sans référence (hors décorateurs) | **6 fonctions** jamais appelées |
| Duplication JS | comparaison `web/connectors.js` ↔ copie inline | **copie périmée** (constat A1) |
| i18n | extraction des dictionnaires fr/en/ar | 27 clés × 3 langues, **2 clés manquantes** (A6) |
| Sécurité | `grep` secrets en dur, `eval`, `except nu` ; test réel du `SecretStore` | 0 / 0 / 0 ; chiffrement **vérifié en vrai** (voir §4) |
| Dette | `TODO|FIXME|XXX|HACK` | **0 occurrence** |
| Volume | `find` + `wc` | 35 modules, 9 843 lignes de source, 5 409 lignes de test |

Environnement : Debian 13, 2 CPU, 1 982 Mo de RAM (≈1,4 Go libres), sans GPU,
Tesseract 5.5.0 seul moteur raster réel. `pytest-cov`, `vulture`, `radon`,
`bandit` et `mypy` ne sont **pas** installés et le réseau n'est pas disponible :
la couverture de test n'a donc pas pu être mesurée (constat B6).

## 2. État des correctifs (mis à jour après livraison)

| Vague | Constats | Livré le | Preuve |
|---|---|---|---|
| 1 | A5, A6, B3 | 2026-10-18 | 8 occurrences `{fid}`/`{tid}` corrigées ; clé `h.connectors` ajoutée en fr/en/ar ; `TestResult` → `ConnectionTestResult` (24 renommages, 5 fichiers), avertissement pytest disparu |
| 2 | A1, B6, **A8** | 2026-10-18 | `tools/sync_web_module.py` + `tests/test_web_module_sync.py` (5 tests) ; plafond 800 Ko dans `ui_stub_check.js` ; **bug A8 trouvé par le garde-fou** : repli `stateBadge("not_configured")` → `unconfigured` |
| 3 | A2, A2 bis, B2, **A9**, **B8** | 2026-10-18 | `process_and_export` supprimé (−24 lignes) + import mort retiré ; bloc images de page factorisé en `ingest.page_images()` ; 5 fonctions mortes retirées ; `tests/test_cli.py` (5 tests) ; **A9** : `unocr process` valide le chemin (code 2, plus de traceback) |
| 4 | A7, B4 | 2026-10-18 | chmod journalisé + `vault_file_permissions`/`vault_file_secure` dans `describe()` ; avertissement de bind au démarrage ; `tests/test_audit_fixes.py` (7 tests) |
| 5 | A3, A4 | 2026-10-18 | `cleanup_temp()` câblé (route + `unocr clean`), purge conservant l'audit ; `retryable_jobs()` exposé par `GET /api/jobs/stale` ; `tests/test_retention_reprise.py` (8 tests) |
| 6 | B7 | 2026-10-18 | les 3 échecs silencieux rapportés (`page_images` journalise, `diagnose` remplit `memory_error` / `tesseract_languages_error`) |
| — | B1 (i18n de la rubrique), B5 (couverture) | **non fait** | B1 : 272 fragments, dernière vague prévue. B5 : `pytest-cov` introuvable ici |

**Résultat de la suite après livraison : 511 passed / 0 failed (328,86 s)**,
`ruff` clean, 168 tests hub inchangés et verts, contrôle de rendu du hub
toujours à 21 contrôles.

## 2. Constats classés

### A — Défauts à corriger (le code ne fait pas ce qu'il annonce)

**A1. `web/connectors.js` est une copie périmée qui n'est jamais chargée.**
Preuve : le fichier fait 39 868 caractères / 725 lignes ; le module réellement
servi, inline dans `web/index.html`, en fait 47 665 / 859 lignes ; aucun
`<script src="…connectors.js">` n'existe dans la page. La copie périmée
contient encore les bugs corrigés : `not_configured` (l'état réel est
`unconfigured`), `c.modes` (le catalogue expose `mode`), et l'assistant bloqué
aux étapes 3 et 6 (`if (wizardStep === 3) { await runWizardTest(); return; }`).
**Risque** : corriger dans ce fichier ne change rien à l'application, et le
croire cassé/corrigé à tort. C'est exactement le mécanisme qui a provoqué la
page « Connecteurs » muette au départ.
*Correctif proposé* : script `tools/sync_web_module.py` qui réinjecte
`connectors.js` dans `index.html` à un marqueur stable, plus un test qui échoue
si les deux copies divergent.

**A2. `process_and_export()` est mort et sa doc est fausse.**
`src/unocr/pipeline.py:519` déclare « utilisé par l'API, le CLI et les
benchmarks ». Vérification : `grep -rn process_and_export src tests` ne renvoie
**que la définition**. L'API appelle `Pipeline.process_file()`
(`api.py:111-112`), le CLI aussi (`cli.py:29`). La fonction recharge en plus le
document une seconde fois (`_ld(path, dpi=…)`) pour récupérer les images de
page — si elle était rebranchée, elle doublerait une partie de l'entrée/sortie.
*Correctif proposé* : supprimer, ou extraire le bloc « images de page » en
helper partagé avec `cli.py` (voir A2 bis).

**A2 bis. Le bloc « images de page » est dupliqué en trois endroits.**
`cli.py:33-40`, `pipeline.py:531-537` et `pipeline.py:519-540` contiennent le
même `try: load_document(…) except Exception: pass`. Trois copies d'un même
comportement dont l'échec est silencieux (voir A7).

**A3. La rétention de 30 jours est configurée mais inerte.**
`config/default.json` → `security.retention_days: 30`, mais
`JobStore.cleanup_temp()` (`storage.py:156`) n'a **aucun appelant** : ni route,
ni CLI, ni test (`grep -rn cleanup_temp src tests docs` → 1 ligne, la
définition). La méthode ne supprime de surcroît que le sous-répertoire `work/`
des jobs terminés, jamais le job lui-même. Conséquence mesurée : `data/jobs`
contient **93 répertoires pour 25 Mo** de résidus de tests.
*Correctif proposé* : câbler un `DELETE /api/admin/cleanup` (ou une commande
`unocr clean`) + test, et écrire dans `docs/LIMITATIONS.md` ce que la rétention
couvre exactement.

**A4. La reprise des jobs interrompus n'est pas câblée.**
`JobStore.retryable_jobs()` (`storage.py:148`) détecte les jobs `processing`
sans mise à jour depuis 600 s et `queued` depuis 3 600 s — et n'est appelé nulle
part. Un job tué net (arrêt du serveur, coupure) reste donc `processing` pour
toujours, invisible dans l'interface.
*Correctif proposé* : exposer la liste dans l'onglet Documents ou le tableau de
bord, avec action « relancer ».

**A5. `docs/API.md` nomme mal les paramètres de 8 routes.**
La doc écrit `/api/connectors/forms/{fid}` et
`/api/connectors/transmissions/{tid}/retry` ; le code expose `{form_id}` et
`{transmission_id}` — 8 occurrences concernées, couvrant les 31 routes dont le
nom de paramètre ne correspond pas à la doc. Un développeur qui copie la doc
obtient une 404 ou un chemin faux.
*Correctif proposé* : aligner les 31 occurrences (remplacement mécanique).

**A6. Une clé i18n est utilisée mais absente des trois langues.**
`h.connectors` (`index.html`, `<h1 data-i18n="h.connectors">`) n'est définie ni
en fr, ni en en, ni en ar. Sans gravité : `setUILang()` fait
`if (v === undefined || v === null) return;` — le texte français existant sert
de repli. Mais le titre de la page reste français en mode anglais ou arabe.
(`h.review`, initialement listé ici, n'est en fait utilisé nulle part : il n'a
pas été ajouté.)

**A7. `secrets.py:62` avale l'échec du `chmod`.**
```python
try:
    os.chmod(self.data_path, 0o600)
except OSError:
    pass
```
Si le `chmod` échoue (Windows, système de fichiers monté en `noexec`/`ro`,
partage réseau), le fichier de secrets est écrit avec les permissions par défaut
du répertoire et **rien ne le signale**. Le secret serait alors lisible par les
autres utilisateurs de la machine, en silence.
*Correctif proposé* : journaliser une erreur explicite et refuser de continuer
si le fichier n'est pas en 0600 (ou l'indiquer dans `/secrets/status`).
Vérification faite à part : sur ce système les permissions sont bien 0o600 pour
`secrets.enc` **et** `secret.key`, le contenu est chiffré, la clé n'est pas
dans le fichier chiffré, et l'aller-retour fonctionne.

**A8. Troisième variante de la confusion d'état d'origine : le repli du badge.**
`web/connectors.js` affichait `stateBadge(cur?.state || "not_configured")` —
un état qui n'existe pas dans `ConnectorState` ni dans `STATE_LABEL` (dont la
clé réelle est `unconfigured`). Comme `stateBadge` retombe sur
`STATE_LABEL[st] || [st, "off"]`, l'écran Configuration affichait
littéralement `not_configured` au lieu de « Non configuré » quand aucun
connecteur n'est sélectionné. Trouvé par le garde-fou anti-régression ajouté en
A1, corrigé, et désormais verrouillé par un test.

**A9. `unocr process` explosait en traceback sur un chemin absent.**
`cmd_process()` ne validait rien : `unocr process /tmp/absent.pdf` levait un
`FileNotFoundError` brut avec 40 lignes de traceback, et le code de retour était
ambigu. Corrigé : message lisible sur `stderr` et code 2, pour un fichier absent
comme pour un répertoire. Trouvé par le nouveau `tests/test_cli.py` (voir B8).

### B — Améliorations (qualité, sans effet fonctionnel immédiat)

**B1. L'i18n est nominale.** 27 clés × 3 langues, cohérentes entre elles, mais
la section Connecteurs contient ≈**272 fragments de texte statique de plus de
25 caractères, dont 0 traduit**. Le sélecteur fr/en/ar ne traduit donc que la
navigation et les titres de page : basculer en anglais laisse toute la rubrique
Connecteurs en français. À assumer explicitement (le dire dans l'interface ou
dans `docs/LIMITATIONS.md`), ou à étendre.

**B8. La CLI n'était couverte par aucun test.** Les occurrences de « cli »
dans les autres fichiers de tests correspondaient en fait à `client` (le
TestClient). `unocr process` — y compris après son rebranchement sur le helper
partagé — n'avait donc jamais été exécutée par une suite. `tests/test_cli.py`
(5 tests) couvre désormais `process`, `diagnose`, les erreurs de chemin et le
helper `page_images()`.

**B2. Six fonctions mortes** : `_csv_cell()` (api.py), `text_attributes()` et
`lang_of()` (direction.py), `redact_settings()` (connectors/secrets.py),
`connectors_data_dir()` (connectors/registry.py) — hors celle de A2. À
supprimer ou à brancher.

**B3. Avertissement pytest au chaque run** : `contract.py:90` déclare
`@dataclass class TestResult`, que pytest tente de collecter comme classe de
test (`PytestCollectionWarning`). Renommer en `ConnectionTestResult` (5
fichiers, aucun impact sur les données sérialisées puisque `as_dict()` renvoie
un dictionnaire) ou poser `__test__ = False`.

**B4. L'API est ouverte par défaut.** `security.token` vaut `null` : le
middleware laisse tout passer (`api.py:211-212`) et le serveur écoute sur
`0.0.0.0`. C'est un choix local-first assumé et documenté, mais sur un réseau
partagé n'importe qui peut lire les documents traités et piloter les
transmissions. *Proposition* : journaliser un avertissement au démarrage quand
le bind n'est pas loopback et qu'aucun jeton n'est défini.

**B5. Aucune mesure de couverture** (pas de `pytest-cov`, pas de réseau). Les
486 tests prouvent des comportements, pas un taux de couverture : des branches
entières peuvent ne jamais être exercées. À mesurer dès qu'un paquet peut être
installé.

**B6. Fichier unique de 667 Ko** (`web/index.html`). Accepté — c'est ce qui rend
la page 100 % hors ligne — mais sans garde-fou il grossira sans limite.
*Proposition* : faire échouer `ui_stub_check.js` au-delà d'un plafond (ex.
800 Ko) pour forcer une décision consciente, et intégrer le test de
synchronisation de A1.

**B7. 5 blocs `except` semi-muets** : `cli.py:38`, `cli.py:87`,
`pipeline.py:534`, `secrets.py:62` (traité en A7), `transmission.py:249`
(celui-ci est correct : état `pending_confirmation` + journalisation). Les trois
premiers perdent une information sans trace : export PDF sans images de page,
rapport de diagnostic sans champs mémoire.

### C — Ce qui est sain, vérifié

- **486 tests passent**, dont 168 sur le hub, sans test ignoré ni marqué
  « à faire ».
- **Chiffrement des secrets vérifié en réel**, pas seulement par un test : sur
  un répertoire temporaire, `secrets.enc` et `secret.key` sont tous deux en
  `0o600`, le contenu est illisible en clair, la clé n'est pas incluse dans le
  fichier chiffré, et la relève fonctionne.
- **0 `eval`/`exec`**, **0 secret en dur**, **0 `except:` nu**, **0 TODO/FIXME**.
- Authentification comparative par `hmac.compare_digest` (pas de fuite par
  timing), liste d'exemption explicite et commentée.
- `resources.py` est honnête : les seuils `ENGINE_RAM_MB` sont écrits comme des
  ordres de grandeur « à valider sur machine cible », et le refus de charger
  EasyOCR/PaddleOCR est motivé par la mémoire libre réelle.
- Documentation Windows présente (`docs/INSTALLATION.md` §6ter) et CLI en trois
  commandes (`process`, `serve`, `diagnose`).
- Les 35 routes du hub sont documentées, et la séparation littéral/paramétré des
  routes FastAPI est respectée.

## 3. Plan de perfection proposé

Ordre proposé par rapport valeur/risque, chaque vague étant livrée et testée
séparément.

| Vague | Contenu | Risque | Pourquoi maintenant |
|---|---|---|---|
| **1** | A5 (doc), A6 (i18n), B3 (`TestResult`) | nul | 3 corrections mécaniques, aucun comportement touché |
| **2** | A1 (synchronisation `connectors.js` + test) + B6 (plafond de taille) | faible | supprime la cause racine de la panne de page ; le test empêche la rechute |
| **3** | A2 + A2 bis (supprimer `process_and_export`, factoriser les images de page) + B2 (5 fonctions mortes) | faible | −150 lignes de code faux ou inutilisé |
| **4** | A7 (chmod) + B4 (avertissement de bind) | moyen | seule vraie faiblesse de sécurité trouvée |
| **5** | A3 + A4 (rétention et reprise câblées, avec route/CLI et tests) | moyen | rendent la promesse de rétention et de reprise réellement tenable |
| **6** | B1 (étendre l'i18n à la rubrique Connecteurs) | moyen | 272 fragments ; à faire par lots, avec relecture arabe |
| **7** | B5 (couverture), B7 (journaliser les 3 échecs silencieux) | faible | finitions d'observabilité |

Hors code : `data/jobs` (93 répertoires, 25 Mo) est à purger après la vague 3,
et le dossier `data/connectors/` est déjà propre (0 connecteur configuré, 0
secret stocké).

## 4. Non audité

- **Rendu visuel, clavier, mobile, lecteurs d'écran** : aucun navigateur
  headless n'est disponible. Le contrôle de rendu exécute le JS du hub sur un
  DOM simulé branché sur l'API réelle (21 contrôles), ce qui prouve la présence
  de contenu, pas sa justesse visuelle.
- **Comportement sous charge** : 2 workers, jamais exercés au-delà de quelques
  documents ; pas de test de concurrence soutenu.
- **Moteurs OCR lourds** : EasyOCR et PaddleOCR ne peuvent pas être chargés ici
  (1,4 Go de RAM libre) ; leurs seuils restent des ordres de grandeur.
- **Couverture de code** : non mesurable dans cet environnement.
- **Windows** : la documentation existe, mais aucun test n'a tourné sur
  Windows.
