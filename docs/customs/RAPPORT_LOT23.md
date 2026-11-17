# Avancement — lot 23 : subdivisions nationales explicitement déclarées

**2026-11-06 — contrat documentaire facultatif, aucune subdivision officielle importée.**

## Audit et livraison

Inspection de TariffBatch/LigneTarifaire, du mapping, du rejeu, de la fiche,
des comparaisons et du diagnostic de couverture. Le contrat passait directement
de SH6 à code10, avec une absence intermédiaire explicitement signalée. Extension
du modèle central, pas d’ajout de codes par troncature ou magasin parallèle.

- Subdivisions facultatives : code intermédiaire 7–9 chiffres ASCII, parent plus
  court SH6/subdivision, libellé et référence documentaire requis. Aucune longueur
  intermédiaire imposée au titre de la nomenclature nationale réelle.
- Lien de ligne `code_subdivision_nationale` facultatif/null. Existence, préfixe,
  source, unicité et chaîne de parents contrôlés ; croissance stricte sans cycle.
- Mapping commun pour les lignes, déclaration sourcée dans le lot du sidecar,
  mêmes garanties de préparation/rejeu et non-écrasement.
- Fiche : chaîne complète **déclarée** jusqu’au parent immédiat, ou liste vide/null ;
  aucune sélection automatique d’un parent à partir d’une ressemblance de préfixe.
- Diff : contenu et provenances séparés pour les subdivisions ; couverture avec
  compteurs descriptifs, sans pourcentage national ou validation juridique.
- Schémas TariffBatch et SubdivisionNationale livrés. API/UI JSON existantes
  réutilisées sans nouvelles routes, comptes, publications ou commandes de calcul.

[Contrat et compatibilité](SUBDIVISIONS_NATIONALES.md).
L’arbre reste une projection SH6→code10 et renvoie à la fiche pour ces intermédiaires ;
aucun nouveau niveau de navigation interactif n’est annoncé.

## Qualification

**1 080 tests Python réussis, 1 avertissement Starlette/httpx**, mêmes données/logs
isolés que le [lot 22](RAPPORT_LOT22.md) + `tests/test_customs_subdivisions.py` :
**1 055 + 25 nouveaux cas**. **48 scénarios UI JSDOM réussis**, aucun nouveau
scénario graphique revendiqué. Ruff et `git diff --check` passent ; pas de suite
complète du dépôt annoncée.

Cas nouveaux : import/rejeu JSON/CSV et mappings XLSX/XML, zéros initiaux, chaîne
à trois niveaux, contraintes de code/source/parent/libellé/preuve, doublons,
liens absents/incohérents, saut de niveau explicitement déclaré autorisé et aucune
inférence de lien quand il n’est pas fourni. Diff de contenu/provenance,
compteurs, schémas, CLI et vraie fiche API protégée testés sur fixtures NON OFFICIELLES.

Une archive de forme ancienne, sans les nouveaux champs, est chargée et rejouée
sans modifier ses fichiers. Le test reconstruit cette forme sur une fixture
contrôlée ; aucune archive utilisateur n’est réécrite pour la qualification.
Les valeurs facultatives sont ajoutées en mémoire seulement. Un ancien lecteur
strict peut refuser de nouveaux lots : compatibilité de lecture actualisée, pas
promesse de consommation par toutes les anciennes versions.

La première sélection ciblée a donné 138 réussites / 1 échec : une assertion
attendait l’ancienne mention « non décrite par le contrat ». Elle vérifie désormais
« déclaration explicite facultative sans inférence ». Sélection complète ci-dessus :
**1 080 réussites**.

Backend de prévisualisation redémarré sur 0.0.0.0:8000 : coque/module/service worker
200 avec hôte distant, revue anonyme 403. Coque v49 inchangée. Aucun compte/lot/registre
réel créé ; journaux préservés hors commit. Empreintes historiques identiques :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Une référence/hiérarchie cohérente reste une déclaration non vérifiée, pas une
preuve d’existence nationale, d’authenticité ou d’applicabilité. Aucune reconstruction
fiscale, classification, relation juridique inférée, validation humaine ou WORM.
Les schémas techniques version 1 évoluent avec champs facultatifs ; conserver les
originaux et mettre à jour les lecteurs, jamais faire de migration silencieuse.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux/modifications exhaustifs,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués ; mission réglementaire partielle.
