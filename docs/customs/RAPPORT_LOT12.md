# Avancement — lot 12 : navigation hiérarchique tarifaire documentaire

**2026-11-06 — parents/enfants reçus, sans nomenclature officielle complète.**

## Audit et périmètre

Inspection préalable des modèles section/chapitre/position/SH6/code10, des liens
parentaux contrôlés au rejeu, de la fiche tarifaire et de la revue existante.
La navigation réutilise ces objets et références sans seconde base/index ou
conversion des codes. La subdivision nationale intermédiaire absente du contrat
n’est pas inventée. La présentation est un parcours par formulaire et rapports
JSON lisibles, pas encore un arbre graphique dépliable.

## Livré

- Service partagé `parcourir_tarif`, après contrôle/rejeu complet du lot.
- Sections → chapitres → positions → SH6 → codes dix chiffres déclarés.
- Parent exact, références et libellés reçus, zéros initiaux conservés, pas de
  normalisation numérique, traduction, préfixe substitué à un lien ou remplissage.
- Parent absent distingué de parent présent sans enfant ; racine sans parent ;
  compteurs, tri déterministe et pagination à chaque niveau, niveau suivant explicite.
- CLI `customs-tariff-tree`, GET de revue `/lots/{lot_id}/tree` et contrôles dédiés
  dans la coque administrative. Groupe désactivé sur les lots Code juridiques,
  parent non transmis à la racine, pas de filtre de recherche réutilisé implicitement.
- Habilitations nominatifs, registre/empreintes épinglées, audit minimal, `no-store`
  et rendu texte existants conservés. Coque service worker v44, API hors cache.

[Contrat, paramètres et procédure](NAVIGATION_TARIFAIRE.md).
Aucun taux applicable, calcul, subdivision nationale ou classement officiel inféré.

## Qualification

**711 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
669 cas du lot 11 + **42 nouveaux cas de navigation**. Pas de suite complète annoncée.

```sh
python -m pytest tests/test_customs_tariff_tree.py tests/test_customs_coverage.py \
 tests/test_customs_tariff_detail.py tests/test_customs_history.py \
 tests/test_customs_backup.py tests/test_backup.py tests/test_customs_review.py \
 tests/test_customs_review_ui.py tests/test_customs_search.py \
 tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
 tests/test_customs_reference.py tests/test_customs_xlsx.py tests/test_customs_comparison.py \
 tests/test_corrections_routes.py tests/test_referentiels.py tests/test_referentiels_base.py \
 tests/test_customs_connector.py tests/test_rbac.py tests/test_rbac_ecritures.py \
 tests/test_rbac_reprise.py tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

Couverture nouvelle : parcours complet et références, champs FR/AR et taux inconnus
conservés, codes/parents exacts avec zéros, IDs de section Unicode, pagination,
parent présent vide et absent, paramètres stricts/contrôles/chiffres non ASCII,
booléens refusés, archives corrompues/symlinks, CLI et processus réel isolé,
autorisations HTTP, type de lot incompatible et épingle incohérente refusée.
Les instantanés de sources restent inchangés ; fixtures uniquement NON OFFICIELLES.

**26 scénarios UI JSDOM** passent : 24 précédents + 2 pour le parcours racine/SH6,
les parents exacts et la désactivation/refus des paramètres manquants. Le parcours
UI → HTTP → véritable middleware/API vérifie cinq enfants code10 d’un SH6 du lot
réel de test, sans réponses métier simulées dans ce parcours. Aucun compte ou lot
de production n’est créé pour une démonstration.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation redémarrée :
coque/module/service worker 200 avec hôte de prévisualisation ; navigation anonyme
403. Les empreintes historiques restent inchangées après redémarrage :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Corpus et mission restante

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** Un parent sans enfant ne prouve pas une absence nationale,
ni une hiérarchie réglementaire erronée. La complétude demeure non établie.
StarterPack, originaux/modifications exhaustifs, tarif national courant et sources
fiscales restent à acquérir, rapprocher et valider humainement.

Pas de consolidation à date, rapprochement fiscal multi-source, validation humaine
signée, publication, API publique officielle, classification IA ou calcul. Les deux
calculs legacy non sourcés restent bloqués. JSDOM ne constitue pas homologation
visuelle/accessibilité complète ni benchmark national ; limites de charge et de
concurrence du rejeu conservées. Aucun usage réglementaire réel n’est autorisé.
