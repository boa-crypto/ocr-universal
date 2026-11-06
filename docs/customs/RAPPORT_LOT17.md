# Avancement — lot 17 : schéma et contrôle hors ligne des exports

**2026-11-06 — contrôle structurel, aucune validation réglementaire.**

## Audit préalable et périmètre

Relecture du format réellement produit au lot 16, des schémas Pydantic existants,
du CLI, des réponses de contrôle/diff et du pont UI/HTTP isolé. Réutilisation des
modèles stricts et du mécanisme de sortie JSON CLI. Aucun magasin ou interface
parallèle ; aucune nouvelle route publique ou commande d’import.

## Livré

- Modèle d’enveloppe d’export version 1 et JSON Schema versionné, test de concordance.
- `customs-review-export-check FICHIER`, lecture seule, sortie JSON :
  **0 structure compatible / 2 refus** ; pas de validation officielle implicite.
- Lecture UTF-8 bornée à 10 Mio, profondeur 64, doublons JSON/nombres non finis/
  Unicode invalide refusés ; fichier régulier, symlink final et FIFO refusés.
- Marqueurs exacts non publié/non validé, provenance SHA256 simple ou double,
  cohérence route/provenance et calendrier, refus des contradictions de marqueurs.
- Constat avec SHA256 des octets reçus, taille, manifestes déclarés et limites,
  sans recopier la requête, le texte métier ou les valeurs des erreurs de validation.
- Pas d’écriture du fichier contrôlé, d’import, d’initialisation de magasin,
  d’accès réseau, de vérification d’audit serveur ou d’archives originales.

[Guide et règles détaillées](CONTROLE_EXPORT_REVUE.md).

## Qualification

**850 tests Python réussis, 1 avertissement Starlette/httpx** en environnement de
données/journaux isolé : sélection du [lot 15](RAPPORT_LOT15.md) +
`tests/test_customs_review_export.py`, soit **781 + 69 nouveaux cas**.
**40 scénarios UI JSDOM réussis**, sans augmentation revendiquée du nombre UI.
Ruff, syntaxe du script d’intégration JavaScript et `git diff --check` passent.
Ce n’est pas une recette de la suite complète du dépôt.

Les 69 cas couvrent enveloppe/versions/champs/types, altérations, données sensibles
non recopiées, JSON invalide/ambigu, profondeurs, fichiers trop grands, lecture
seule, fichiers dangereux, calendrier, manifeste/provenance, schéma et CLI sans
création de magasins. Douze cas vérifient les réponses de l’API réelle sur fixtures
NON OFFICIELLES : contrôles Code/tarif, recherches Code/tarif, histoire, fiche,
couvertures Code/tarif, arbre, fragment d’article et diff Code/tarif. Les corpus de
quarantaine sont identiques avant/après.

Le pont JSDOM/HTTP/API existant transmet en outre le JSON du véritable Blob produit
par le bouton au contrôleur Python, qui l’accepte sans lui accorder d’authenticité.
L’émission de ce JSON dans stdout appartient au harnais de test isolé uniquement,
pas au code du navigateur déployé ou à une journalisation des documents réels.

Une première recette étendue a donné **849 réussites / 1 échec** : le contrôle Code
possède une liste `archives` de PDF déclarés, différente de la paire de comparaison
`archives.avant/apres`. La règle de provenance a été corrigée sans changer les
rapports ou les données sources ; réexécution : **850 réussites**.

Empreintes historiques inchangées :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

L’interface de production et ses routes ne changent pas ; aucun redémarrage du
serveur ou nouvelle coque n’est nécessaire pour cette commande CLI hors ligne.

## Limites et mission restante

Le contenu métier hors marqueurs/provenances reste opaque. Les paramètres HTTP ne
sont pas rejoués. Le schéma seul ne couvre pas toutes les contraintes sémantiques
CLI. Pas de signature, WORM, horodatage certifié, authentification du fichier,
comparaison au registre/archives ou attestation de livraison. Un fichier forgé peut
être structurellement compatible. Le SHA256 calculé ne l’officialise pas.
Les contrôles ne constituent pas une garantie mémoire globale ou une transaction
face à un autre écrivain ; les ancêtres du chemin ne sont pas cloisonnés.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, corpus original/modificatif exhaustif,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués.
