# P3 — socle technique : transactions, OCR/contrôle, verrous reproductibles

**Date : 14 novembre 2026**  
**Branche : `arena/a4e8bc76-ocr-universal`**  
**Périmètre : durcissement interne sans nouvelle donnée métier, sans taux de change et sans intégration externe.**

## 1. Réalisé

### 1.1. Transactions métier imbriquées sûres

`BusinessStore.transaction()` utilisait un simple `yield self` lorsqu'une transaction était déjà active : une sous-opération pouvait donc partager le sort du parent sans point de reprise propre.

Le magasin utilise désormais des **savepoints SQLite** :

- une transaction imbriquée peut être annulée sans effacer le travail déjà fait dans le parent ;
- sa validation reste subordonnée au commit du parent ;
- les collections obtenues par `related(...)` partagent le même verrou et la même transaction ;
- les noms de savepoints sont uniques, ce qui permet plusieurs niveaux d'imbrication.

Tests ajoutés dans `tests/test_business_persistence.py` : rollback partiel d'un enfant, conservation du parent, écriture liée validée, et rollback global si le parent échoue après un enfant validé.

### 1.2. OCR, contrôle documentaire et dashboard liés à la config de requête

Les modules OCR/contrôle/dashboard ne doivent pas capturer un singleton de configuration à l'import puis le réutiliser dans un serveur reconfiguré ou isolé.

Modifications :

- `OCRTransitIntegration` accepte une configuration explicite et l'utilise pour le `JobStore` et l'audit ;
- `ExtractionOCRStore` expose `sauvegarder(...)` comme porte d'écriture atomique publique ; les routes n'appellent plus `_ecrire(...)` ;
- `routes/documents_ocr.py` construit l'intégration depuis `request.app.state.cfg` ;
- `DocumentOCRUpdate` borne `statut` aux valeurs connues et refuse les champs fournis à `null` ;
- les audits de modification/création/auto-classification OCR portent l'acteur serveur ;
- `ControleDocumentaireEngine` et `analyser_dossier_complet` acceptent la configuration de requête ;
- `DashboardService` et les routes dashboard utilisent la configuration de requête au lieu du singleton global.

Tests ajoutés ou adaptés : refus des statuts invalides/null sans mutation, audit serveur des modifications OCR, intégration OCR liée à la config de requête, non-régression du périmètre et des acteurs.

### 1.3. Verrous de dépendances minimaux par cible

L'ancien `requirements.lock.txt` mélangeait runtime, outillage de notebook, bibliothèques d'agent et paquets sans rapport avec le serveur.

Nouvelle séparation :

- `requirements.lock.txt` : verrou runtime minimal, fermeture transitive de `pyproject.toml`, cible Linux/CI Python 3.11 ;
- `requirements-dev.lock.txt` : inclut le verrou runtime, puis pytest/ruff/xlwt/requests et le moteur Indra utilisé par la CI ;
- `requirements.txt` reste la liste multiplateforme à plages minimales ;
- `opencv-python` est remplacé par `opencv-python-headless` dans le projet et les requirements, afin d'éviter la dépendance GUI/libGL côté serveur.

Chaîne d'installation durcie :

- Docker installe `requirements.lock.txt`, puis le projet avec `--no-deps` ;
- la CI générale et la recette douanière installent `requirements-dev.lock.txt`, puis le projet en éditable avec `--no-deps`, et vérifient `pip check` ;
- les versions épinglées ont été vérifiées comme existantes sur PyPI et compatibles avec la cible Python 3.11 ;
- `tests/test_config_docker.py` vérifie la présence des verrous, leur forme minimale, l'absence d'outillage interdit et leur usage par Docker/CI.

## 2. Validation locale

| Contrôle | Résultat |
|---|---:|
| `ruff check src tests benchmarks` | réussi |
| `git diff --check` | réussi |
| `node --check web/ecrans.js` et `node --check tests/ui_finance_banque.js` | réussi |
| `pip check` après installation éditable sans dépendances | réussi |
| Tests ciblés métier/OCR/backup/RBAC/config | **377 réussis** |
| Tests UI/statuts/architecture web sans serveur | **63 réussis, 3 ignorés** |
| Suite Python complète isolée | **4 537 réussis, 15 échecs, 14 ignorés** |

Les **15 échecs restants** sont les échecs environnementaux déjà identifiés : Tesseract/Poppler absents et modèles Indra non disponibles localement avec `HF_HUB_OFFLINE=1`. Ils ne sont pas masqués par un skip automatique.

Les ignorés incluent les tests OCR raster nécessitant Tesseract/tessdata, les tests navigateur opt-in et les tests jsdom nécessitant un serveur vivant non démarré pendant cette passe.

Commande de suite complète utilisée :

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
UNOCR_DATA_DIR="$PWD/.cache/p3-validation/data" \
UNOCR_LOG_DIR="$PWD/.cache/p3-validation/logs" \
UNOCR_USER_PROFILES_DIR="$PWD/.cache/p3-validation/profiles" \
python -m pytest tests -q --junitxml=.cache/p3-validation/pytest.xml
```

## 3. Ce qui n'est pas revendiqué

- Pas de build Docker exécuté dans ce bac à sable.
- Pas de qualification OCR terrain : Tesseract/langues et modèles Indra réels restent à installer et mesurer.
- Pas de corpus douanier officiel, pas de taux de change, pas de connecteur externe réel.
- Pas de purge des données métier ni des gros artefacts déjà suivis par Git.

## 4. Backlog restant prioritaire

1. **Hygiène du dépôt** : inventorier et séparer `.venv-agency`, `tmp_packages`, données locales, journaux et métadonnées générées ; vérifier clés/secrets avant toute décision de retrait.
2. **OCR terrain** : binaires/langues/modèles épinglés, corpus annoté, mesures CER/WER et exactitude par champ.
3. **CI OCR complète** : exécuter la suite raster avec prérequis réels, distinguer échec environnemental et régression.
4. **Finance/transit legacy** : remplacer l'append JSON divergent de `transit.py::creer_frais` par le magasin métier transactionnel.
5. **Connecteurs et référentiels douaniers** : spécifications officielles, accès autorisés, corpus FR/AR, validation habilitée.
6. **i18n et parcours UI mutants** : compléter les modules récents et les scénarios création → contrôle → validation → export → clôture sur magasin jetable.
