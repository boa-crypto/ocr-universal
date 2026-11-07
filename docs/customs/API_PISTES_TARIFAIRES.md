# API et rejeu des pistes documentaires — lot 59

## Lecture administrative explicite

`GET /api/v1/customs-review/lots/{lot_id}/tariff-candidates`

Paramètres : `designation`, `matiere`, `fonction`, `usage`, `caracteristiques`,
`code_prefix`, `match_mode`, `limit`, `offset`. Au moins un critère textuel ; préfixe
seul refusé. Les bornes et la règle de tri sont celles de
[PISTES_TARIFAIRES.md](PISTES_TARIFAIRES.md). Aucun fallback de `/tariff-criteria`.

Accès par administrateur RBAC nominatif **et** réviseur inscrit dans l'allowlist
locale. Le chemin vient du registre, jamais d'un paramètre HTTP. Tarif uniquement ;
Code et mesures autonomes refusés. Manifeste enregistré contrôlé avant traitement,
archive complète rejouée, manifeste du résultat comparé à la référence du registre.
Tout succès doit être sérialisé puis audité avant libération du résultat. Réponse
200 `Cache-Control:no-store`, enveloppe lecture seule/non validée habituelle.

Opération d'audit : `recherche_pistes_tarifaires`, acteur, IDs, statut, empreintes
pour succès ; pas termes de requête, texte des libellés, candidats ou chemins dans
cet événement. Audit obligatoire indisponible : 503 sans résultat ; incohérence de
lot/empreinte : 409 sans résultat. Authentification 401, habilitation 403, lot absent
404, paramètres/type incompatibles 422. Les erreurs de validation FastAPI antérieures
à l'action conservent le mécanisme commun du serveur, pas un nouvel audit métier.

La nouvelle route refuse paramètres inconnus/dupliqués (y compris nom percent-encodé),
plus de neuf paramètres, requête mal formée, échappement percent invalide ou UTF-8
invalide. Pagination : ASCII explicite sur 1–7 chiffres avant bornes métier, pas
signe `+`, notation scientifique ou chiffre Unicode. Les chaînes de critères
peuvent contenir du FR/AR UTF-8 percent-encodé. Ni URL ni chemin de source ne peuvent
choisir un autre fichier. Ces refus ne changent pas les anciens contrats de routes.

## Contrôle d'un rapport et rejeu local

Le format d'export revue **v1** est étendu additivement à cette route, avec provenance
simple `resultat.archive`. Le schéma JSON publié est synchronisé. Aucune nouvelle
route d'émission de fichier ou enveloppe signée n'est ajoutée : un client peut
placer le `resultat` HTTP dans l'enveloppe de revue habituelle. Cela n'atteste pas
que l'enveloppe provient du serveur ou a été auditée.

- `customs-review-export-check` contrôle sa structure ; pas fidélité du résultat.
- `customs-review-export-replay FILE --lot DOSSIER --lot-id ID --type-lot tarif`
  rejoue la recherche contre une archive **explicitement fournie**.
- Les [empreintes attendues](EMPREINTES_ATTENDUES_REJEU.md) facultatives d'export et
  manifeste s'appliquent sans modification. Elles sont fournies séparément par
  l'opérateur ; leur authenticité reste non attestée.
- Comparaison canonique de l'intégralité du résultat : rangs, tri, termes non
  retrouvés, indicateurs, positions/extraits, ordre de liste, provenance et drapeaux.
  Sortie limitée aux constats/empreintes/avertissements, sans texte ni diff recopié.
- Codes du rejeu : 0 identique, 1 différent, 2 refus ; aucun ne signifie « code10
  validé ». Le contrôleur historique de seuls critères AND refuse cette route.
  Types Code/mesures et comparaison de deux archives ne sont pas des fallbacks.

Pas réseau, registre serveur, authentification du reçu, signature ou audit serveur
revérifiés par le rejeu local. Une fabrication cohérente reste possible sans une
référence externe digne de confiance ; le résultat identique n'établit pas un droit.

## Limites métier et interface

Pistes littérales partielles d'un lot en quarantaine, pas IA, pertinence juridique,
probabilité, RGI, notes/exclusions ou validation de matière/fonction/usage. Pas taux,
dates applicables, publication, écriture métier ou sélection automatique. Une
conjonction complète est documentaire seulement. Le lot 59 ne livrait pas de contrôle UI. Le
[complément du lot 60](INTERFACE_PISTES_TARIFAIRES.md) ajoute l’action explicite dans
la revue, avec cache de coquille v70 sans mise en cache des réponses API.
La qualification des nouvelles lectures HTTP porte sur cinq rapports API réels
NON OFFICIELS (dont cas vide, FR/AR, pagination, mot entier), pas un corpus national.
