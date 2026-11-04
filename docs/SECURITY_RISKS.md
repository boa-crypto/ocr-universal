# Risques de Sécurité et Mitigations - Module Transit Maritime

## Tableau des Risques

| Risque | Niveau | Description | Mitigation | Statut |
|--------|--------|-------------|------------|--------|
| Exposition données financières | ÉLEVÉ | Accès aux frais, paiements non restreints | RBAC: rôle `responsable_financier` requis pour accès complet | ✅ Implémenté |
| Contournement cloisonnement | MOYEN | Routes non filtrées par dossier | Ajout `_exige_dossier()` sur toutes les routes transit | ✅ Corrigé |
| Tampering ETA/ETD | MOYEN | Modification non tracée des dates critiques | Audit obligatoire (`eta_mis_a_jour`) | ✅ Implémenté |
| Erreur de configuration RBAC | ÉLEVÉ | Mauvaise configuration laisse tout ouvert | Validation RBAC au démarrage, alertes critiques | ⚠️ À vérifier |
| Jetons environnement exposés | ÉLEVÉ | `UNIOCR_TOKEN` donne accès administrateur | Désactiver en production, utiliser authentification par rôle | ✅ Documenté |
| Escalade de privilèges | ÉLEVÉ | Un utilisateur modifie les rôles d'un autre | Toutes les routes RBAC nécessitent `ADMINISTRATEUR` | ✅ Implémenté |
| Injection de données | MOYEN | Valeurs malveillantes dans les champs | Validation serveur (longueur, format, valeurs) | ✅ Implémenté |
| Accès non autorisé aux documents | ÉLEVÉ | Téléchargement sans vérification du dossier | `_exige_dossier()` appliqué aux routes documents | ⚠️ À étendre |
| Fuite de jetons | ÉLEVÉ | Jetons révélés dans les logs ou réponses | Jetons jamais dans les logs, `public()` exclut le jeton | ✅ Implémenté |
|attaque par force brute | MOYEN | Tentatives de deviner les jetons | Comparaison à temps constant (`secrets.compare_digest`) | ✅ Implémenté |

## Détails des Risques

### 1. Exposition des Données Financières

**Description** : Les informations de frais, montants, devises et données de paiement sont des données sensibles pouvant être exploitées pour des activités frauduleuses.

**Impact** : Vol de données financières, usurpation d'identité commerciale.

**Mitigation implémentée** :
- Les routes `/frais` nécessitent le rôle `responsable_financier`
- Les routes `/export` nécessitent `controleur_documentaire` ou `responsable_financier`
- Le masquage des données sensibles lors de l'export pour les rôles non-administrateurs

### 2. Contournement du Cloisonnement par Dossier

**Description** : Un utilisateur pourrait potentiellement accéder aux documents d'un autre dossier en modifiant l'identifiant dans l'URL.

**Impact** : Violation de la confidentialité, fuite de données client.

**Mitigation implémentée** :
- Vérification systématique du périmètre avec `_exige_dossier(dossier_id, request)`
- Retour 403 (et non 404) pour éviter la divulgation de l'existence des dossiers

### 3. Tampering des ETA/ETD

**Description** : Les dates estimées d'arrivée/départ sont des informations critiques pour la planification. Une modification non autorisée pourrait affecter les opérations.

**Impact** : Retards de transport non prévus, dommages matériels.

**Mitigation implémentée** :
- Action RBAC `eta_update` réservée aux rôles appropriés
- Journalisation obligatoire de chaque modification (`eta_mis_a_jour`)
- Conservation des valeurs précédentes dans l'audit

### 4. Erreur de Configuration RBAC

**Description** : Une configuration incorrecte du fichier `rbac.json` peut laisser le système ouvert ou inaccessible.

**Impact** : Accès non autorisé ou blocage complet du système.

**Atténuation** :
- Validation stricte des rôles au chargement (`RBACError` sur rôle inconnu)
- Journalisation au démarrage de l'état RBAC
- Alertes critiques dans les logs

### 5. Jetons Environnement Exposés

**Description** : Le jeton `UNIOCR_TOKEN` donne un accès administrateur complet au système.

**Impact** : Contrôle total du système, modification de tous les données.

**Mitigation** :
- Utiliser uniquement en développement/test
- En production, configurer des utilisateurs dans `rbac.json`
- Chaque utilisation est tracée dans l'audit (`acces_jeton_environnement`)

### 6. Escalade de Privilèges

**Description** : Un utilisateur malveillant pourrait tenter de modifier les rôles ou permissions d'un autre utilisateur.

**Impact** : Prise de contrôle du système.

**Mitigation implémentée** :
- Toutes les routes de modification RBAC nécessitent `ADMINISTRATEUR`
- Les routes POST/PUT/PATCH/DELETE sur `/api/rbac/*` sont réservées aux administrateurs
- Les jetons sont régénérés en cas de suspicion de compromission

### 7. Injection de Données

**Description** : Un utilisateur malveillant pourrait envoyer des données contenant des scripts malveillants ou des formats anormaux.

**Impact** : Exécution de code, corruption des données, déni de service.

**Mitigation implémentée** :
- Validation des longueurs de champs
- Validation des formats (références BL, numéros de voyage)
- Sanitisation des noms de fichiers
- Validation des valeurs numériques (montants positifs)

### 8. Accès Non Autorisé aux Documents

**Description** : Les routes de téléchargement pourraient permettre d'accéder à des documents sans vérification du dossier.

**Impact** : Fuite de documents confidentiels.

**Plan d'action** :
- Appliquer `_exige_dossier()` à toutes les routes de documents
- Vérifier le dossier d'origine du document (`/api/jobs/{id}`)

---

## Recommandations pour la Période en Production

1. **Surveillance continue** : Activer l'alerte sur les tentatives d'accès refusées (>10 par heure)

2. **Rotation des jetons** : Planifier une rotation mensuelle des jetons utilisateurs

3. **Revue RBAC** : Audit trimestriel des droits d'accès

4. **Sauvegarde** : Sauvegarder régulièrement le fichier `rbac.json` avec les sauvegardes système

5. **Monitoring** : Surveiller les logs d'audit pour les activités inhabituelles