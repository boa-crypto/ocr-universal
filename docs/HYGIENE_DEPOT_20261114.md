# Hygiène du dépôt UniOCR — inventaire et secrets

**Date :** 14 novembre 2026 (travail poursuivi le 15 novembre dans le bac à sable)  
**Branche :** `arena/a4e8bc76-ocr-universal`  
**Périmètre :** fichiers suivis par Git, règles d'ignore, garde-fou CI. Aucune
donnée métier n'a été purgée ; les fichiers désindexés restent présents sur le
disque de travail.

## 1. Méthode

L'inventaire est produit par :

```bash
python scripts/audit_repo_hygiene.py
python scripts/audit_repo_hygiene.py --json
python scripts/audit_repo_hygiene.py --strict-secrets
```

Le script lit `git ls-files`, ne supprime rien et n'affiche jamais le contenu
d'un secret. Il distingue :

- **secrets** : chemins de clés, fichiers `.env` non exemplaires, marqueurs PEM
  de clé privée dans les fichiers du projet ;
- **artefacts** : environnements virtuels, paquets temporaires, caches,
  journaux, métadonnées d'installation, scripts ponctuels historiques ;
- **données locales `data/`** : inventaire seulement, pas une autorisation de
  purge.

## 2. Résultat après désindexation

| Catégorie | Avant P4 | Après P4 | Traitement |
|---|---:|---:|---|
| Fichiers suivis au total | 24 817 | 23 684 | 1 133 désindexations |
| `.venv-agency/` | 19 905 | 19 905 | **dette restante**, ignore déjà présent mais fichiers encore suivis |
| `tmp_packages/` | 1 034 | 0 | désindexé, ignoré |
| `.agentic-qe/` | 10 | 0 | désindexé, ignoré |
| `data/keys/` | 1 | 0 | secret désindexé, ignoré |
| `logs/` | 2 | 0 | journaux désindexés, ignorés |
| `*.egg-info/` | 6 | 0 | métadonnées générées désindexées, ignorées |
| `__pycache__` / `.pyc` hors vendor | 71 | 0 | désindexés, ignorés |
| Scratch racine (`verify_*`, `write_import.py`, etc.) | 6 | 0 | désindexés, ignorés |
| `.claude/settings.local.json` | 1 | 0 | réglage local désindexé, ignoré |
| `server.log`, `tests/_last_run.log` | 2 | 0 | journaux désindexés, ignorés |
| `data/` métier hors clés | 1 879 | 1 879 | **conservé**, aucune purge |

Taille encore suivie dans `.venv-agency/` : **282 688 958 octets**.  
Taille des données locales `data/` conservées : **36 246 240 octets**.

## 3. Secrets identifiés : rotation requise

Deux secrets étaient suivis par Git. Ils ont été retirés de l'index et ignorés,
mais **leur présence dans l'historique Git n'est pas effacée par cette opération**.

| Fichier | Nature | SHA-256 du contenu au moment du retrait |
|---|---|---|
| `.agentic-qe/witness-keys/84ee584133ad3af5.key.pem` | clé privée PEM, métadonnée `retired: false` | `1ddd2968c513d121e4b2a31d8fa6c73d8da5f618aa8a90cb4d95ddc8ff839c03` |
| `data/keys/master.key` | clé brute locale de chiffrement (32 octets) | `c13eab890ba921745f79ef6d3162c4f572aa9e2adcc5e176752a6e7031b41f31` |

Actions à conduire par le responsable du dépôt / déploiement :

1. considérer ces clés comme compromises si le dépôt a été partagé ou poussé ;
2. révoquer / retirer la clé witness dans l'outil qui la consomme, puis en
   générer une nouvelle hors Git ;
3. si `data/keys/master.key` a servi à chiffrer des données, planifier une
   rotation avec déchiffrement / rechiffrement contrôlé et sauvegarde ;
4. purger l'historique seulement après sauvegarde et coordination des clones
   (`git filter-repo` ou équivalent), puis forcer la mise à jour des clones ;
5. vérifier les journaux et artefacts CI qui auraient pu recopier ces fichiers.

Aucune de ces actions externes n'a été exécutée automatiquement dans ce lot.

## 4. Garde-fous ajoutés

- `.gitignore` couvre désormais `/data/keys/`, `.agentic-qe/`,
  `.agentic-qe/witness-keys/`, `tmp_packages/`, `*.egg-info/`, `*.log`,
  `.claude/settings.local.json` et les scripts scratch historiques.
- `scripts/audit_repo_hygiene.py --strict-secrets` échoue si un secret détectable
  est suivi par Git.
- `.github/workflows/ci.yml` exécute ce garde-fou avant les tests.
- `tests/test_hygiene_depot.py` vérifie la détection, l'ignore, l'état courant du
  dépôt et la présence du garde-fou CI.

État vérifié après changements :

```text
Fichiers suivis : 23684
Secrets suivis : 0
Artefacts suivis : 19905 (282688958 octets)
  .venv-agency/: 19905
Données locales data/ : 1879 (36246240 octets) — inventaire, pas purge
```

## 5. Dette restante et décisions attendues

1. **`.venv-agency/` encore suivi.** La désindexation massive représente environ
   19 905 suppressions d'index ; elle doit être faite dans un changement dédié
   pour garder une revue lisible :

   ```bash
   git rm --cached -r .venv-agency
   git commit -m "hygiene: untrack vendored virtualenv"
   ```

   Ne pas supprimer le répertoire disque sans vérifier qu'aucun outillage local
   ne l'utilise encore.
2. **Données métier `data/`.** Les 1 879 fichiers restants ne sont pas purgés.
   Décider quels jeux sont fixtures, quelles données sont locales, et mettre en
   place sauvegarde / transfert avant toute désindexation.
3. **Historique Git.** La désindexation ne remplace pas une purge d'historique
   ni une rotation de secrets.
4. **Outillage `.claude/`.** Les fichiers locaux sensibles ont été retirés ; le
   reste de `.claude/` n'a pas été requalifié dans ce lot.
5. **Scripts d'installation.** `scripts/install.sh` / `install.ps1` ne sont pas
   encore alignés sur les verrous P3 ; le verrou Linux contient notamment
   `uvloop`, à traiter séparément pour Windows.

## 6. Reproduire

```bash
python scripts/audit_repo_hygiene.py --strict-secrets
python -m pytest tests/test_hygiene_depot.py -q
git diff --check
git diff --cached --check
```
