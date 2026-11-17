# Matrice des Rôles et Permissions - Module Transit Maritime

Mise à jour P4 du 2026-11-14 : les routes `/transit/*` passent par le même
middleware d'authentification que `/api/*`. La finance historique utilise le
magasin métier persistant et une action dédiée au paiement.

## Rôles définis

| Rôle | Niveau hiérarchique | Description |
|------|---------------------|-------------|
| `lecteur` | 0 | Accès en lecture seule aux dossiers de son périmètre |
| `operateur` | 1 | Alias de compatibilité, couvert par `agent_de_transit` |
| `superviseur` | 2 | Alias de compatibilité, couvert par `responsable_transit` |
| `agent_de_transit` | 3 | Opérations courantes de saisie et mise à jour |
| `responsable_transit` | 4 | Supervision, résolution d'anomalies, création de frais |
| `declarant_habile` | 5 | Accès aux déclarations, validation des documents |
| `controleur_documentaire` | 6 | Contrôle qualité, validation, export, archivage |
| `responsable_financier` | 7 | Gestion des frais, paiements, export complet |
| `administrateur` | 8 | Accès complet, configuration, gestion utilisateurs, clôture/restauration |

Les niveaux sont ceux de `unocr.rbac.ROLES`. Un rôle couvre toutes les actions
dont le rôle minimum est situé avant lui dans cet ordre ; les tuples `ACTIONS`
expriment donc des **minimums**, pas des listes exclusives.

## Matrice des Permissions par Action

| Action | lecteur | agent_de_transit | responsable_transit | declarant_habile | controleur_doc | responsable_financier | administrateur |
|--------|:-------:|:----------------:|:-------------------:|:----------------:|:--------------:|:---------------------:|:--------------:|
| consultation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| creation | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| modification | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| prise_emplacement | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| eta_update | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| bl_receive | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| frais_creation | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| paiement_frais | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| cloture_dossier | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| restauration_dossier | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| mainlevee_obtenir | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| conteneur_liberer | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| livraison_confirmer | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| suppression_logique | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| archivage | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| validation_documentaire | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| resolution_anomalies | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| changement_statut | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| gestion_financiere | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| export | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| configuration_metier | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

Les orthographes accentuées `gestion_financière` et `configuration_métier`
restent des alias de compatibilité ; les routes utilisent les clés ASCII.

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

- `dossiers: ["*"]` = accès à tous les dossiers ;
- `dossiers: []` = aucun accès ;
- `dossiers: ["D1"]` = accès uniquement au dossier D1.

## Héritage des Permissions

```
lecteur < operateur < superviseur < agent_de_transit < responsable_transit
        < declarant_habile < controleur_documentaire < responsable_financier
        < administrateur
```

Un `administrateur` peut tout faire. Les alias `operateur` et `superviseur`
sont conservés pour les déploiements historiques ; ils ne créent pas une
frontière supplémentaire entre `lecteur` et `agent_de_transit`.

## API Endpoints et Permissions

| Endpoint | Méthode | Rôle requis |
|----------|---------|-------------|
| `/transit/dossiers` | POST | agent_de_transit+ |
| `/transit/dossiers` | GET | lecteur+ |
| `/transit/dossiers/{id}` | GET | lecteur+ (avec accès dossier) |
| `/transit/dossiers/{id}` | PATCH | agent_de_transit+ (avec accès dossier) |
| `/transit/dossiers/{id}/prise_emplacement` | POST | agent_de_transit+ |
| `/transit/dossiers/{id}/eta` | POST | agent_de_transit+ |
| `/transit/dossiers/{id}/bl_receive` | POST | agent_de_transit+ |
| `/transit/dossiers/{id}/frais` | POST | responsable_transit+ |
| `/transit/dossiers/{id}/paiement` | POST | responsable_financier+ |
| `/transit/dossiers/{id}/export` | POST/GET | controleur_documentaire+ |
| `/transit/dossiers/{id}/cloturer` | POST | administrateur |
| `/transit/dossiers/{id}/archiver` | POST | controleur_documentaire+ |
| `/transit/dossiers/{id}/restorer` | POST | administrateur |
| `/transit/dossiers/{id}/conteneurs` | POST/DELETE | agent_de_transit+ |
| `/transit/dossiers/{id}/conteneurs` | GET | lecteur+ (avec accès dossier) |
| `/transit/dossiers/{id}/historique` | GET | lecteur+ (avec accès dossier) |
| `/transit/dossiers/doublons` | POST | lecteur+ (résultats filtrés par périmètre) |
| `/transit/audit` | GET | lecteur+ ; entrées sans dossier visibles seulement par administrateur |
| `/transit/security` | GET | lecteur+ quand RBAC actif |

## Journalisation d'Audit

Toutes les opérations sensibles sont enregistrées :

| Événement | Champs clés |
|-----------|-------------|
| `dossier_cree` | acteur, dossier, label |
| `dossier_modifie` | acteur, dossier, champs |
| `prise_emplacement_enregistree` | acteur, dossier, conteneur, quai |
| `eta_mis_a_jour` | acteur, dossier, ancien_eta, nouveau_eta |
| `bl_reçu` | acteur, dossier, reference_bl |
| `frais_cree` | acteur, dossier, frais_id, type_frais, montant, devise |
| `paiement_enregistre` | acteur, dossier, frais_id, montant, devise, reference |
| `dossier_exporte` | acteur, dossier, formats |
| `dossier_cloture` | acteur, dossier, motif |
| `dossier_archive` | acteur, dossier, motif |
| `dossier_restaurer` | acteur, dossier |
| `conteneur_lie` / `conteneur_delié` | acteur, dossier, conteneur, conteneur_id |
| `acces_refuse_role` | acteur, rôles, requis, route |
| `acces_refuse_dossier` | acteur, dossier, route |
| `acces_refuse_jeton` | route, méthode |

## Considérations de Sécurité

1. **403 vs 404** : les refus de périmètre renvoient 403 ; une référence métier
   absente ou incohérente avec le dossier demandé renvoie 404.
2. **Jetons secrets** : générés aléatoirement, jamais renvoyés après création.
   Un jeton inconnu reçoit 401 lorsque RBAC est actif.
3. **Audit obligatoire** : toute opération sensible est journalisée avec
   l'identité de l'acteur résolu côté serveur.
4. **Validation serveur** : les charges financières sont validées par Pydantic
   (montant fini strictement positif, devise ISO à trois lettres, identifiant
   de frais requis). L'alias historique `frai_id` reste accepté pour le
   paiement, mais la réponse et l'audit utilisent `frais_id`.
5. **Finance persistante** : `/transit/dossiers/{id}/frais` et
   `/transit/dossiers/{id}/paiement` écrivent dans `BusinessStore[Frais]`,
   partagé avec `/api/frais`. Aucune liste JSON annexe n'est créée dans le
   dossier.
