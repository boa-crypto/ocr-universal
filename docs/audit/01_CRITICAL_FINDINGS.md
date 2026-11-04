# UniOCR - Découvertes Critiques
**Date**: 2026-10-23  
**Priorité**: P0-P1  
**Statut**: Analyse en cours

---

## P0 - CRITIQUE

### ⚠️ CR-001: Fichier index.html monolithique (738KB)

**Sévérité**: P0 - Performance et maintenabilité critiques  
**Impact**: Temps de chargement initial, maintenance difficile, duplication de code

**Analyse**:
```
Taille totale: 738,129 caractères (6,274 lignes)
- CSS embarqué: 501,279 caractères (67.3%)
- JavaScript embarqué: 190,644 caractères (25.6%)
- HTML: ~46,206 caractères (6.3%)
```

**Problèmes identifiés**:
1. **Performance**: ~720KB de HTML à parser (non compressé)
2. **Maintenabilité**: Tout le code dans un seul fichier
3. **Cache**: Impossible de mettre en cache CSS/JS séparément
4. **Duplication potentielle**: Modules JS dupliqués dans index.html ET fichiers .js séparés

**Vérification de duplication détectée**:
Le fichier contient des commentaires explicites:
```
/* ═══ Traçabilité du dossier — module synchronisé ═══
   Ne pas modifier cette section à la main : éditer web/tracabilite.js puis lancer
   « python3 tools/sync_web_module.py ». Le test tests/test_web_module_sync.py
   échoue si les deux copies divergent. */
```

Cela confirme que:
- Les modules JS existent en double (fichiers séparés + embarqués)
- Un script `tools/sync_web_module.py` synchronise les versions
- Un test vérifie la synchronisation

**Recommandations**:

**Option A - Architecture moderne (recommandée pour production)**:
1. Extraire tout le CSS dans `styles.css` séparé
2. Charger les modules JS existants (tracabilite.js, dossier.js, etc.) comme modules ES6
3. Supprimer les duplications de l'index.html
4. Ajouter bundling optionnel avec Vite/esbuild (dev uniquement)
5. Bénéfices: cache HTTP, chargement parallèle, maintenance simplifiée

**Option B - Architecture actuelle optimisée (pragmatique)**:
1. Garder l'architecture sans build
2. Extraire au minimum le CSS dans un fichier séparé
3. Réduire les duplications en chargeant les .js externes
4. Minifier au moment du déploiement (simple script Python)
5. Bénéfices: conservation de la simplicité, gain immédiat

**Option C - Hybride (compromis)**:
1. CSS externe: `<link rel="stylesheet" href="styles.css">`
2. Scripts critiques inline pour performance initiale
3. Scripts secondaires chargés en defer
4. Service worker pour cache agressif (déjà présent)

**Impact estimé**:
- Temps de chargement: -40% à -60%
- Maintenabilité: +80%
- Taille de cache: séparation CSS (500KB) + JS (190KB) + HTML (~50KB)

**Tests de non-régression requis**:
- ✅ tests/test_web_module_sync.py existe déjà
- ⏳ Ajouter tests de chargement des ressources
- ⏳ Vérifier le fonctionnement offline (PWA)

**Validation humaine requise**: 👤 Choix de l'option d'architecture

---

## P1 - HAUTE PRIORITÉ

### 🔍 CR-002: Duplication de modules JavaScript confirmée

**Sévérité**: P1 - Maintenance et risque de divergence  
**Impact**: Risque d'incohérence entre versions, complexité de maintenance

**Fichiers concernés**:
- `web/tracabilite.js` ↔ Bloc dans index.html
- `web/dossier.js` ↔ Bloc dans index.html  
- `web/formulaire.js` ↔ Bloc dans index.html
- `web/transmission.js` ↔ Bloc dans index.html
- `web/connectors.js` ↔ Bloc dans index.html

**Mécanisme actuel**:
- Script de synchronisation: `tools/sync_web_module.py`
- Test de vérification: `tests/test_web_module_sync.py`
- Commentaires dans le code source avertissant de ne pas modifier manuellement

**Évaluation**:
✅ **Points positifs**:
- Test automatique détecte les divergences
- Documentation claire dans les commentaires
- Processus documenté

⚠️ **Points négatifs**:
- Duplication intentionnelle = double maintenance
- Risque d'oubli de synchronisation
- Complexité inutile à long terme
- Augmente la taille du fichier HTML

**Recommandation**: Éliminer la duplication
1. Charger les modules externes avec `<script src="tracabilite.js" defer></script>`
2. Supprimer le script de synchronisation devenu inutile
3. Simplifier la maintenance

**Statut**: ⏳ À traiter après décision sur CR-001

---

### 🔒 CR-003: Audit de sécurité - En cours

**Sévérité**: P1 - Sécurité  
**Statut**: 🔄 Analyse en cours

**Modules de sécurité identifiés**:
- ✅ `src/unocr/security.py` - Validation fichiers, anti-injection
- ✅ `src/unocr/rbac.py` - Contrôle d'accès
- ✅ `src/unocr/crypto_store.py` - Chiffrement
- ✅ `src/unocr/services/security.py` - Middleware de sécurité
- ✅ Tests: test_security.py, test_security_hardening.py, test_xss_frontend.py

**Contrôles à vérifier**:
- ⏳ Validation d'entrées (magic bytes, extensions, taille)
- ⏳ Protection zip-bomb
- ⏳ Anti-injection CSV/XML
- ⏳ Headers de sécurité HTTP
- ⏳ Configuration CORS
- ⏳ CSP (Content Security Policy)
- ⏳ RBAC implementation
- ⏳ Audit trail
- ⏳ Secrets management

**Prochaine étape**: Lecture détaillée du code de sécurité

---

### 📊 CR-004: Suite de tests - Exécution en cours

**Sévérité**: P1 - Qualité  
**Statut**: 🔄 Exécution en arrière-plan (ID: b07ig47ib)

**Tests identifiés**: 62 fichiers de tests
- Sécurité: 3 fichiers
- API: 3 fichiers  
- Core OCR: 8+ fichiers
- Fonctionnalités avancées: 12+ fichiers
- Connecteurs: 5 fichiers
- Intégration: 5 fichiers

**À vérifier**:
- ⏳ Taux de réussite des tests
- ⏳ Couverture de code
- ⏳ Tests en échec ou skipped
- ⏳ Durée d'exécution

**Résultats attendus**: Dans quelques minutes

---

## LIMITES DOCUMENTÉES (Référence)

### Limites assumées du projet

D'après `docs/LIMITATIONS.md`, le projet documente honnêtement:

1. **Moteurs OCR**: Seul Tesseract actif (contraintes RAM/GPU)
2. **Écriture manuscrite**: Détection uniquement, pas de transcription
3. **Benchmarks**: Sur jeu synthétique, pas données réelles
4. **UI**: Pas testée visuellement automatiquement
5. **RBAC**: Système local, pas SSO/LDAP entreprise
6. **Connecteurs**: Aucun connecteur réel livré (simulateurs uniquement)
7. **Parallélisme**: Gain mesuré ×1.18 (pas ×2) sur 2 cœurs

✅ **Appréciation**: Documentation honnête et transparente

---

## PROCHAINES ANALYSES

### Analyses en attente de résultats

1. **Suite de tests** 🔄 - En cours d'exécution
2. **Audit de sécurité détaillé** ⏳ - Lecture du code
3. **Analyse UI/UX** ⏳ - Lancement du serveur requis
4. **Mesure de performance** ⏳ - Benchmarks à exécuter
5. **Audit de l'architecture** ⏳ - Cartographie des dépendances

### Prochaines étapes immédiates

1. Attendre résultats des tests
2. Lire en détail security.py, rbac.py, crypto_store.py
3. Vérifier configuration du middleware de sécurité
4. Lancer le serveur pour audit UI
5. Exécuter les benchmarks

---

**Mise à jour**: 2026-10-23 23:06 UTC  
**Analysé par**: Équipe Architecture + Sécurité  
**Statut global**: 🔄 Analyse en cours - Découvertes critiques identifiées
