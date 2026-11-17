# P2 — Durcissement finance et liens métier (2026-11-14)

Suite des passes P0 et P1. Cette passe ne prétend pas fermer l'OCR terrain,
les connecteurs douaniers externes ni la consolidation de change. Elle ferme
des incohérences concrètes relevées à la relecture du rapprochement bancaire.

## 1. Intégrité du pointage bancaire

- `delete_facture` est transactionnel et refuse une facture rapprochée ; aucune
  opération bancaire ne reste liée à une facture fantôme.
- `update_facture` refuse de modifier dossier, sens, montant, devise, référence,
  dates ou paiement d'une facture pointée. Les notes/documents restent éditables.
- L'annulation restaure l'état de paiement antérieur (statut, date, référence)
  via un snapshot porté par l'opération, au lieu de forcer `en_attente`.
- Un lien facture ↔ opération est écrit dans une seule transaction SQLite ;
  un échec d'écriture ne laisse pas un demi-pointage.
- Le rapprochement automatique exige un score ≥ 2 : montant/devise seuls ne
  suffisent plus. Le taux est calculé sur toutes les factures du dossier, avec
  compteurs séparés pour les déjà pointées et les candidates.
- Un dossier sans frais ni facture renvoie un état vide explicite, pas un
  avertissement « plusieurs devises ».

## 2. Import bancaire plus strict

- Montants finis uniquement, deux décimales maximum ; booléens, `NaN`,
  `Infinity`, notation scientifique et séparateurs ambigus sont rejetés.
- Formats non ambigus acceptés : `1234,56`, `1 234,56`, `1,234.56`,
  `1.234,56`, `(50,25)`.
- Un identifiant externe réimporté avec un contenu différent est un rejet 409,
  pas un doublon silencieux.
- CSV : colonnes dupliquées et lignes surnuméraires refusées ; limite de
  10 000 opérations par import.
- L'écran `#finance/banque` propose désormais un import CSV multipart et un
  import JSON fichier, avec validation de taille et résumé importées/doublons/
  rejetées. Le pointage automatique/manuel/annulation est réservé aux
  superviseurs dans l'API et masqué côté UI selon `/api/rbac/moi`.

## 3. RBAC et liens dossier

- Clés canoniques ASCII `gestion_financiere` et `configuration_metier` ajoutées
  dans `rbac.ACTIONS` et `api.RBAC_ACTIONS` ; les orthographes accentuées restent
  des alias compatibles. La route transit paiement n'utilise plus une clé absente.
- `exiger_dossier_sans_liens` couvre aussi conteneur, connaissement, bon à
  délivrer, livraison et opération bancaire.
- `/api/rbac/moi` expose `ecriture` et `supervision` pour que l'interface ne
  confonde pas lecteur, opérateur et superviseur.

## 4. Tests et validations

```text
ruff check src tests benchmarks                     → All checks passed!
tests ciblés finance/RBAC/P0/maritime/backup        → 183 passed
tests interface jsdom (serveur isolé + fixture)     → 3 passed
npm run ui:product (Chromium)                       → 412 routes, 4 viewports,
                                                      32 captures, 0 erreur JS,
                                                      0 mutation
suite complète isolée HF_HUB_OFFLINE=1              → 4530 passed, 16 failed,
                                                      11 skipped (485 s)
```

Les 16 échecs de la suite complète sont les 15 échecs environnementaux OCR
connus (Tesseract/Poppler absents, modèles Indra hors ligne) plus
`test_interface_jsdom` qui exigeait un document déjà présent dans le magasin
de recette. Après amorçage d'un PDF natif dans ce magasin isolé, les trois
tests interface jsdom passent (109 s). Aucun échec métier finance/RBAC n'est
observé.

## 5. Reste ouvert

- OCR terrain : corpus réel annoté, binaires/langues et modèles installés,
  mesure CER/WER et exactitude par champ.
- Connecteurs externes réels et référentiels douaniers officiels FR/AR :
  spécifications, comptes de test, corpus tarifaire 10 chiffres, validation
  habilitée et publication contrôlée.
- Consolidation de change : taux datés et sourcés, règles comptables d'avoirs
  et paiements partiels.
- Hygiène du dépôt et verrou de dépendances minimal par cible.
