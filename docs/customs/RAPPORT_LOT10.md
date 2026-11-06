# Avancement — lot 10 : fiche tarifaire documentaire

**2026-11-06 — lecture seule, aucun tarif applicable ou calcul douanier établi.**

## Audit et périmètre

Inspection préalable de `LigneTarifaire`, `Mesure`, de leurs contrôles de parents,
du lecteur/rejeu tarifaire et de l’API/interface de revue. Les champs fiscaux
inconnus de la ligne et les mesures documentées sont déjà séparés : la nouvelle
consultation conserve cette frontière. Les lots sont mono-source ; aucune jointure
avec une fiscalité externe n’est improvisée. Aucune subdivision nationale
intermédiaire n’est inventée depuis un préfixe du code.

## Livré

- Service commun `consulter_code` : code exact, chaîne de dix chiffres ASCII,
  avec zéros initiaux conservés, sans conversion ou remplissage.
- Fiche de la ligne reçue, désignations FR/AR, unités/dates/références déclarées,
  section/chapitre/position/SH6 reçus et leurs localisateurs, provenance de source.
- Mesures explicitement liées au code, séparées des taux inconnus de la ligne,
  triées par ID et paginées. Taux décimaux transmis comme chaînes exactes ;
  aucun arrondi, choix d’applicabilité ou calcul.
- Absence explicitement délimitée au lot, sans faux code ou exonération :
  `ligne_trouvee=false`, ligne/hiérarchie nulles et mesures vides.
- CLI `customs-tariff-show`, GET de revue `/lots/{lot_id}/tariff/{code10}` et
  contrôles dédiés dans la coque existante, désactivés pour un lot Code juridique.
- Habilitations nominatives, épingles de manifestes, audit minimal, `no-store`
  et rendu texte sûr réutilisés ; aucune nouvelle persistance documentaire.
  Coque service worker version 42, API toujours exclue du cache.

[Contrat, commandes et limites](FICHE_TARIFAIRE.md).
**Une mesure absente ne prouve pas une exonération. Un taux null n’est pas zéro.**
Un taux déclaré zéro reste une déclaration non validée, pas un droit applicable.

## Qualification

**644 tests Python réussis, 1 avertissement Starlette/httpx**, data/logs isolés :
609 cas du lot 9 + **35 nouveaux cas de fiche tarifaire**. Pas de résultat annoncé
pour la suite complète du dépôt.

```sh
python -m pytest tests/test_customs_tariff_detail.py tests/test_customs_history.py \
 tests/test_customs_backup.py tests/test_backup.py tests/test_customs_review.py \
 tests/test_customs_review_ui.py tests/test_customs_search.py \
 tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
 tests/test_customs_reference.py tests/test_customs_xlsx.py tests/test_customs_comparison.py \
 tests/test_corrections_routes.py tests/test_referentiels.py tests/test_referentiels_base.py \
 tests/test_customs_connector.py tests/test_rbac.py tests/test_rbac_ecritures.py \
 tests/test_rbac_reprise.py tests/test_ui_premium.py tests/test_web_architecture_refactored.py -q
npm run ui:customs-review
```

Couverture nouvelle : hiérarchie et références, zéros initiaux, désignations
bilingues, absence de ligne/mesures et inconnus préservés, précision décimale et
zéro déclaré distinct de null, dates de mesures distinctes, pagination, paramètres
stricts/booléens/chiffres non ASCII, archives corrompues/symlinks, CLI et vrai
processus isolé, droits HTTP, mode ouvert refusé, type de lot incompatible,
manifestes incohérents refusés. Instantanés de fichiers source inchangés.

**23 scénarios JSDOM réussis**, dont 2 nouveaux pour la fiche et ses paramètres,
les codes invalides et sa désactivation sur un lot Code juridique. Le parcours
UI → HTTP → véritable API/middleware, sur magasin temporaire, est étendu à la
fiche avec parents SH6 et absence de fiscalité applicable établie. Les fixtures
NON OFFICIELLES restent uniquement dans les tests, pas dans le magasin réel.

Ruff, syntaxe JavaScript et `git diff --check` passent. Prévisualisation redémarrée :
coque/module/service worker 200 avec hôte de prévisualisation ; fiche anonyme 403.
Aucun registre/compte de production créé. Empreintes historiques recontrôlées :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

**Ce dixième lot ne signifie pas achèvement des dix phases de la mission.**
Aucun nouvel original officiel, aucune ligne nationale officielle validée et
aucune publication active. Le StarterPack, le tarif national courant complet,
le corpus original/modificatif exhaustif et les sources fiscales restent à acquérir,
rapprocher et valider humainement.

Pas de subdivision intermédiaire nationale documentée, de rapprochement fiscal
multi-source, de choix à date, de calcul, de validation humaine signée, de
publication, d’API publique officielle ou de classification IA. Les deux calculs
legacy non sourcés demeurent bloqués. Qualification JSDOM et backend isolé, pas
homologation visuelle/accessibilité complète ni benchmark national. Les limites
de charge et de concurrence des lecteurs restent applicables ; pas de WORM.
Aucun résultat de cette fiche ne doit être utilisé pour un calcul douanier réel.
