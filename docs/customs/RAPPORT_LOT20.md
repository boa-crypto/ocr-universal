# Avancement — lot 20 : sous-ensemble XLS OLE/BIFF8 textuel

**2026-11-06 — préparation locale en quarantaine, aucun tarif national validé.**

## Audit préalable

Inspection de `xlrd` 2.0.2, déjà dépendance runtime, du mapping central, des lecteurs
XLSX/XML/ZIP et du rejeu. L’API cellule xlrd restitue des caches de formules ; elle
ne suffit pas à garantir un code littéral. Le lecteur ajoute donc un contrôle
OLE/BIFF8 préalable, sans évaluation de formules ou reconstruction de codes.
Le support XLS du modèle était prévu mais aucun adaptateur qualifié n’existait.

## Livré

- Sous-ensemble OLE/BIFF8, flux Workbook et feuilles tabulaires ; feuille/mapping
  explicites, cellules texte ou vides uniquement après l’en-tête.
- Parcours des records du flux complet avant lecture : refus des formules,
  chiffrement, noms/liens, objets/dessins, fusions et sections hors contrat reconnus.
- Répertoire OLE limité aux flux admis ; pas de projets VBA/stockages supplémentaires.
- Codes chaînes et zéros initiaux préservés, nombres/formats d’affichage non utilisés
  pour fabriquer un code, mêmes contrôles de parents/doublons/provenance/mesures.
- Plan sans écriture, préparation explicite vers répertoire neuf, source reçue
  intacte, manifeste, chargeur et rejeu centraux ; membre XLS accepté dans ZIP.
- Aucun nouveau magasin, endpoint ou mécanisme d’activation.
- `xlwt==1.3.0` ajouté au groupe dev et verrou de qualification pour écrire les
  fixtures uniquement. Production : lecteur xlrd existant, pas d’usage de xlwt.

[Contrat détaillé et restrictions](IMPORT_XLS.md).

## Qualification

**1 022 tests Python réussis, 1 avertissement Starlette/httpx**, données/journaux
isolés : sélection du [lot 19](RAPPORT_LOT19.md) + `tests/test_customs_xls.py`, soit
**966 + 56 nouveaux cas**. xlwt installé pour cette exécution, aucun cas XLS sauté.
**40 scénarios UI JSDOM réussis**, Ruff et `git diff --check` passent.
Pas de suite complète du dépôt ou de qualification visuelle/nationale annoncée.

Cas : plan sans écriture, octets archivés identiques, rejeu, zéros initiaux et TVA
inconnue null, provenance feuille/ligne ; véritables formules xlwt sur feuille
sélectionnée et non sélectionnée refusées ; cellules numériques/booléennes,
en-têtes ambigus, feuille cachée, fusions et cellule hors en-tête refusés ; options,
BIFF incomplet/ancien/macro, records interdits et bornes testés. Les gardes de
répertoire OLE sont aussi testées par métadonnées synthétiques contrôlées, pas
présentées comme analyse de binaires VBA réels.

Cinq cas HTTP/API réels consultent un lot XLS temporaire épinglé (contrôle,
recherche, fiche, arbre, couverture), corpus inchangé après lecture. Un XLS membre
d’un ZIP est préparé et rejoué. Le cas ZIP « format non pris en charge » utilise
maintenant XLSB plutôt que XLS, sans relâcher les autres gardes.
Fixtures techniques NON OFFICIELLES uniquement ; aucun compte/lot/registre réel créé.

Prévisualisation backend redémarrée sur 0.0.0.0:8000 : coque/module/service worker
200 avec hôte de prévisualisation, revue anonyme 403. Coque v48 inchangée. Journaux
conservés hors commit. Empreintes historiques après redémarrage identiques :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Ce n’est pas un lecteur universel XLS : BIFF antérieur, macrosheets, graphiques,
cellules numériques/dates Excel, objets, liens, fusions et structures hors contrat
restent refusés. Pas d’antivirus, détection exhaustive de tout record inconnu,
garantie RAM/temps, bac à sable OS, réparation, signature, WORM ou preuve éditeur.
Les dimensions déclarées peuvent être mensongères ; les bornes après chargement
ne constituent pas une garantie mémoire préalable. Les flux de résumé admis ne
sont pas certifiés. Aucune donnée calculée ne doit être substituée à un code source.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** PDF tarifaire encore non qualifié ; StarterPack,
originaux/modifications exhaustifs, tarif national courant et sources fiscales
restent à acquérir et valider humainement. Les calculs legacy non sourcés restent
bloqués. Ce lot ne clôture pas la mission réglementaire.
