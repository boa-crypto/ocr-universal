# Matrice des Rôles et Permissions - Module Transit Maritime

## Rôles définis

| Rôle | Niveau hiérarchique | Description |
|------|---------------------|-------------|
| `lecteur` | 0 | Accès en lecture seule à tous les dossiers dans son périmètre |
| `agent_de_transit` | 1 | Opérations courantes de saisie et mise à jour |
| `responsable_transit` | 2 | Supervision, résolution d'anomalies, validation |
| `declarant_habile` | 3 | Accès aux déclarations, validation des documents |
| `controleur_documentaire` | 4 | Contrôle qualité, validation, export |
| `responsable_financier` | 5 | Gestion des frais, paiements, export complet |
| `administrateur` | 6 | Accès complet, configuration, gestion utilisateurs |

## Matrice des Permissions par Action

| Action | lecteur | agent_de_transit | responsable_transit | declarant_habile | controleur_doc | responsable_financier | administrateur |
|--------|:-------:|:----------------:|:-------------------:|:----------------:|:--------------:|:---------------------:|:--------------:|
| consultation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| création | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| modification | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| prise_emplacement | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| eta_update | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| bl_receive | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| frais_creation | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| mainlevee_obtenir | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| conteneur_liberer | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| livraison_confirmer | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| suppression_logique | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| archivage | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| validation_documentaire | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| resolution_anomalies | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| changement_statut | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| gestion_financiere | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| export | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| configuration_metier | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

## Cloisonnement par Dossier

Chaque utilisateur a un périmètre de dossiers spécifique :

```json
{
  "utilisateurs": [
    {
      "nom": "marie",
      "roles": ["agent_de_transit"],
      "dossiers": ["D1", "D2", "D3"]
    }
  ]
}
```

- `dossiers: ["*"]` = Accès à tous les dossiers
- `dossiers: []` = Aucun accès (dossier invalide)
- `dossiers: ["D1"]` = Accès uniquement au dossier D1

## Héritage des Permissions

Les rôles supérieurs héritent automatiquement des permissions des rôles inférieurs :

```
lecteur < agent_de_transit < responsable_transit < declarant_habile
        < controleur_documentaire < responsable_financier < administrateur
```

Un `administrateur` peut tout faire : consultation, création, modification, suppression, archivage, validation, résolution d'anomalies, gestion financière, export, configuration.

## Alias de Compatibilité

Pour la compatibilité descendante :

| Ancien rôle | Nouveau rôle équivalent |
|-------------|------------------------|
| `operateur` | `agent_de_transit` |
| `superviseur` | `responsable_transit` |

## API Endpoints et Permissions

| Endpoint | Méthode | Rôle requis |
|----------|---------|-------------|
| `POST /transit/dossiers` | POST | agent_de_transit+ |
| `GET /transit/dossiers` | GET | lecteur+ |
| `GET /transit/dossiers/{id}` | GET | lecteur+ (avec accès dossier) |
| `PATCH /transit/dossiers/{id}` | PATCH | agent_de_transit+ (avec accès dossier) |
| `POST /transit/dossiers/{id}/prise_emplacement` | POST | agent_de_transit+ |
| `POST /transit/dossiers/{id}/eta` | POST | agent_de_transit+ |
| `POST /transit/dossiers/{id}/bl_receive` | POST | agent_de_transit+ |
| `POST /transit/dossiers/{id}/frais` | POST | responsable_transit+ |
| `POST /transit/dossiers/{id}/paiement` | POST | responsable_financier+ |
| `POST /transit/dossiers/{id}/export` | POST | controleur_documentaire+ |
| `POST /transit/dossiers/{id}/cloturer` | POST | administrateur |

## Journalisation d'Audit

Toutes les opérations sensibles sont enregistrées :

| Événement | Champs clés |
|-----------|-------------|
| `dossier_cree` | acteur, dossier, label |
| `dossier_modifie` | acteur, dossier, champs |
| `prise_emplacement_enregistree` | acteur, dossier, conteneur |
| `eta_mis_a_jour` | acteur, dossier, ancien_eta, nouveau_eta |
| `bl_reçu` | acteur, dossier, reference_bl |
| `frais_cree` | acteur, dossier, type_frais, montant |
| `paiement_enregistre` | acteur, dossier, frai_id, montant |
| `dossier_exporte` | acteur, dossier, formats |
| `dossier_cloture` | acteur, dossier, motif |
| `acces_refuse_role` | acteur, rôle, requis, route |
| `acces_refuse_dossier` | acteur, dossier, route |

## Considérations de Sécurité

1. **403 vs 404** : Les erreurs retournent 403 (Forbidden) plutôt que 404 (Not Found) pour ne pas révéler l'existence d'objets inaccessibles.

2. **Jetons secrets** : Les jetons sont générés aléatoirement (`secrets.token_urlsafe(24)`) et ne sont jamais renvoyés dans les réponses après création.

3. **Audit obligatoire** : Toute opération sensible est journalisée avec l'identité de l'acteur.

4. **Validation serveur** : Toutes les entrées sont validées côté serveur (longueur, format, valeurs autorisées).