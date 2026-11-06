# Avancement — lot 8 : interface intégrée de revue en quarantaine

**2026-11-06 — lecture seule, aucune validation ni publication réglementaire.**

## Audit et choix d’intégration

Avant modification : inspection de `web/navigation.js`, `web/ecrans.js`,
`web/souspages.js`, `web/index.html`, du design system, du service worker et des
routes de revue. Les écrans métier déclaratifs génériques possèdent des actions
d’écriture et un cache de listes : ils ne sont pas réutilisés pour ce périmètre
confidentiel strictement en lecture seule. La coque, sa navigation, son mécanisme
de session et ses styles sont réutilisés, sans nouvelle application ou base.
Les services et contrôles métier restent exclusivement ceux du lot 6.

## Livré

- Entrée **Administration → Revue douanière · quarantaine**, route
  `#admin/revue-douaniere`, section reconnue par la navigation existante.
- Liste des lots et SHA256 attendus, avec avertissement d’intégrité non contrôlée
  par la seule liste ; aucun faux zéro en cas d’absence de registre ou de refus.
- Contrôle/rejeu d’un lot, recherche FR/AR avec filtres Code et pagination par
  limite/décalage, comparaison de lots de même type.
- Rapports JSON rendus comme texte, conservant champs, preuves et statuts du
  service commun ; pas de contenu documentaire interprété comme HTML.
- GET relatifs uniquement ; serveur autoritaire pour les droits. Traitement
  explicite des statuts d’erreur, sans corps d’erreur interne ni chemin serveur.
- Absence de nouveau cache documentaire, effacement de la zone à la navigation,
  priorité à la requête la plus récente, rejet des retours tardifs et des réponses
  avec marqueurs de publication/validation incompatibles. Relecture au retour
  depuis le cache de navigation. Coque précachée version 40, API toujours exclue.
- Aucun compte ou lot de production créé pour faire apparaître une démonstration.

[Guide utilisateur, sécurité et limites](INTERFACE_REVUE.md).

## Qualification

**559 tests Python réussis, 1 avertissement Starlette/httpx**, avec data/logs
isolés : sélection de 495 cas du lot 7, 63 cas existants de coque/architecture
et 1 nouveau test d’intégration UI/API réelle. Pas de suite complète annoncée.

```sh
python -m pytest tests/test_customs_backup.py tests/test_backup.py \
 tests/test_customs_review.py tests/test_customs_review_ui.py \
 tests/test_customs_search.py tests/test_customs_legal_comparison.py \
 tests/test_customs_legal.py tests/test_customs_reference.py tests/test_customs_xlsx.py \
 tests/test_customs_comparison.py tests/test_corrections_routes.py \
 tests/test_referentiels.py tests/test_referentiels_base.py tests/test_customs_connector.py \
 tests/test_rbac.py tests/test_rbac_ecritures.py tests/test_rbac_reprise.py \
 tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

**19 scénarios JSDOM** supplémentaires : liste, contrôle, injection HTML traitée
comme texte, recherche arabe/encodage/filtres/pagination, filtres tarif exclus,
comparaisons compatibles/incompatibles, 401/403/404/409/422/503, liste vide,
réponse invalide, retour tardif après navigation, ordre concurrent des réponses,
changement de compte, effacement au départ et retour de cache de navigation.
Ces réponses de contrat sont des fixtures de test NON OFFICIELLES.

L’intégration appelle les vrais services du backend, avec RBAC et épingles sur
un magasin temporaire ; pas de réponses métier simulées dans ce parcours.
Les fichiers du corpus de test sont inchangés après les appels.
Les tests de structure HTML et navigation passent avec la nouvelle section.
Prévisualisation existante contrôlée : `/`, le nouveau module statique et le
service worker version 40 répondent 200 ; l’API de revue anonyme répond 403.
Les fichiers statiques sont servis directement, sans redémarrage nécessaire.
Ruff et vérification du diff effectués. Les empreintes des deux données historiques
restent celles des lots précédents :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Non livré et état documentaire

L’écran de revue ne représente pas l’administration réglementaire complète :
ni import HTTP, validation humaine signée, publication, export, aperçu PDF,
consolidation à date, API publique réglementaire ou classification IA.
L’interface est en français, peut transmettre/afficher l’arabe, mais n’est pas
une traduction arabe complète de la coque. Qualification JSDOM, pas homologation
visuelle/accessibilité complète en navigateur réel ni benchmark national.

**Aucun nouvel original officiel acquis, aucun article/code national officiel
validé, aucune publication active.** StarterPack, originaux/modifications exhaustifs,
tarif national courant et fiscalité officielle restent à acquérir et vérifier.
Les calculs legacy non sourcés demeurent bloqués. La revue technique ne détermine
ni l’authenticité des sources, ni le droit applicable ou une validation juridique.
