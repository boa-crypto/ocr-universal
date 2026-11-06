# Avancement — lot 24 : navigation détaillée des subdivisions

**2026-11-06 — enfants explicitement déclarés, aucun classement validé.**

## Audit et livraison

Inspection du modèle de subdivisions du lot 23, de la navigation tarifaire,
des actions UI et du CLI. Une simple substitution SH6→subdivisions aurait masqué
les lignes sans lien intermédiaire. Le nouveau niveau mélange donc, sous un même
parent, subdivisions et codes10 directement déclarés ; aucune affectation par
préfixe n’est effectuée.

- `level=subdivisions` pour un parent SH6 ou subdivision exact, 6–9 chiffres ASCII.
- Enfants directs typés, tri lexicographique et pagination commune, compteurs locaux.
- Projection historique `codes` inchangée dans son sens, disponible au CLI/API/UI.
- `niveau_suivant_detaille` propose la descente détaillée sans remplacer le champ
  historique `niveau_suivant=codes` d’un rapport SH6.
- Interface : nouvelle option détaillée, descente par subdivision, code10→fiche,
  gardes de requête/lot/session et contrôles des types/liens/préfixes/bornes.
- Mêmes lecteurs, magasins, habilitations, épingles et audit ; aucune nouvelle route
  ou écriture métier. Coque service worker version 50.

[Guide et sens des deux vues](NAVIGATION_SUBDIVISIONS.md).

## Qualification

**1 092 tests Python réussis, 1 avertissement Starlette/httpx**, sélection isolée du
[lot 23](RAPPORT_LOT23.md) + `tests/test_customs_subdivision_tree.py` : **1 080 + 12**.
**52 scénarios UI JSDOM réussis : 48 + 4 nouveaux.** Ruff, syntaxe des trois fichiers
JavaScript modifiés et `git diff --check` passent. Pas de suite complète du dépôt
ou qualification visuelle multi-navigateurs revendiquée.

Cas Python : enfants mixtes, chaîne déclarée jusqu’au code10, ligne directe non
rattachée malgré préfixe commun, projection conservée, pagination/hors fin,
parent absent, paramètres invalides avant lecture, CLI et API protégée/épinglée,
corpus inchangé. Les quatre nouveaux cas JSDOM couvrent enfants mixtes, refus
d’actions sur liens incohérents, pagination et proposition détaillée depuis SH6.

Le parcours JSDOM→HTTP→API réel réarchive le tarif de fixture dans un nouveau lot
avec trois intermédiaires, sans écraser les lots précédents. Il conserve des lignes
sans lien intermédiaire, descend SH6→7→8→9→code10 puis ouvre la fiche. PDF,
exports partiels et diff existants continuent à passer. Sources et comptes de test
NON OFFICIELS temporaires uniquement ; aucun lot/registre/compte utilisateur créé.

Première recette ciblée : 42 réussites / 1 échec de l’assertion qui attendait encore
le choix UI projeté `codes`. Le parcours vérifie désormais `subdivisions` et les
trois intermédiaires réels de la fixture ; sélection étendue : **1 092 réussites**.

Backend de prévisualisation redémarré sur 0.0.0.0:8000 : coque/module/service worker
200 avec hôte distant, nouvelle navigation anonyme 403. Journaux conservés hors
commit. Empreintes historiques après redémarrage identiques :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Pas d’arbre graphique dépliable/fil d’Ariane complet, niveau national inventé,
hiérarchie nationale officielle constituée, classification ou validation juridique.
La cohérence des références/préfixes ne certifie pas leur authenticité. Une page
vide/parent absent ne prouve pas absence de droit ; toutes les bornes des lecteurs
et de la quarantaine restent applicables.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux/modifications exhaustifs,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués ; mission réglementaire partielle.
