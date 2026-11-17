# Avancement — lot 11 : diagnostic de couverture documentaire

**2026-11-06 — éléments reçus et inconnus, pas score de complétude réglementaire.**

## Audit et choix

Inspection préalable des modèles, des rapports de préparation/rejeu, des compteurs
déjà calculés, de l’API et de la coque de revue. Les services existants contrôlent
l’intégrité du lot avant le diagnostic ; aucune seconde base/index n’est créée.
Les indicateurs distinguent explicitement champs optionnels non renseignés,
compteurs locaux, cohérence au rejeu et validation réglementaire toujours absente.

## Livré

- Service commun `diagnostiquer_couverture` sur un seul lot Code ou tarif déclaré.
- Tarif : compteurs hiérarchie/lignes/mesures, champs linguistiques/unités/dates/taux
  non renseignés, types de mesures, lignes sans mesure et parents sans ligne code10.
- Code : documents/articles/numéros exacts/relations, natures, champs non renseignés,
  documents sans article transcrit, empreintes PDF identiques sans fusion,
  articles sans relation et occurrences de niveaux hiérarchiques.
- Sources identifiées par ID/empreinte/non-vérification, sans dump des transcriptions.
- `nombre_officiel_attendu=null`, `pourcentage_completude_reglementaire=null`,
  `completude_reglementaire=non_etablie`, `utilisable_pour_calcul_douanier=false`.
  Aucun seuil, score ou verdict « prêt à publier ».
- CLI `customs-coverage --type code|tarif`, GET protégé `/lots/{lot_id}/coverage`,
  bouton intégré pour les deux types. Même registre nominatif, épingles et audit,
  réponses `no-store`, rendu texte, pas de nouvelle persistance documentaire.
  Coque service worker version 43, API toujours exclue du cache.

[Guide, définitions et limites](COUVERTURE_DOCUMENTAIRE.md).
Un champ absent n’est pas automatiquement une erreur ; zéro valeur déclarée n’est
pas null, et zéro article transcrit ne signifie pas transcription complète.

## Qualification

**669 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
644 cas du lot 10 + **25 nouveaux cas de couverture**. Pas de suite complète annoncée.

```sh
python -m pytest tests/test_customs_coverage.py tests/test_customs_tariff_detail.py \
 tests/test_customs_history.py tests/test_customs_backup.py tests/test_backup.py \
 tests/test_customs_review.py tests/test_customs_review_ui.py tests/test_customs_search.py \
 tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
 tests/test_customs_reference.py tests/test_customs_xlsx.py tests/test_customs_comparison.py \
 tests/test_corrections_routes.py tests/test_referentiels.py tests/test_referentiels_base.py \
 tests/test_customs_connector.py tests/test_rbac.py tests/test_rbac_ecritures.py \
 tests/test_rbac_reprise.py tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

Couverture nouvelle : exactitude des compteurs Code/tarif, champs de langue
non renseignés, zéro décimal déclaré distinct d’inconnu, documents sans article,
dates manquantes distinctes, empreintes identiques signalées sans suppression,
parents sans ligne, chaîne blanche, type explicite/refus d’autodécouverte,
corruption/symlinks, CLI et processus réel isolé, habilitations HTTP, type pris au
registre, empreintes incohérentes refusées et registre absent. Instantanés des
sources inchangés. Les fixtures sont NON OFFICIELLES et uniquement temporaires.

**24 scénarios UI JSDOM** passent : 23 précédents + diagnostic pour les deux types,
avec dénominateur/pourcentage inconnus conservés. Le parcours d’intégration
UI → HTTP → véritable middleware/API vérifie le diagnostic d’un lot Code réel de
test, sans possibilité de calcul ni pourcentage inventé. Pas de réponse métier
simulée dans ce parcours d’intégration ; aucun compte ou registre de production créé.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation redémarrée :
coque/module/service worker 200 avec hôte de prévisualisation ; diagnostic anonyme
403. Les empreintes historiques sont inchangées après redémarrage :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Corpus et mission restante

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** Les compteurs ne résolvent pas le manque du StarterPack,
des originaux/modifications exhaustifs, du tarif national courant ou de ses sources
fiscales. Leur acquisition, rapprochement et validation humaine restent nécessaires.

Pas de contrôle exhaustif contre une référence nationale, de consolidation à date,
de qualification des preuves PDF, de validation humaine signée, de publication,
de classification IA ou de calcul. Les deux calculs legacy non sourcés restent
bloqués. Qualification JSDOM/backend isolé, pas homologation navigateur/accessibilité
complète ni benchmark national ; limites de charge/concurrence du rejeu conservées.
Aucun diagnostic de ce lot ne permet un usage réglementaire réel.
