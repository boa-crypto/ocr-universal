# Avancement — lot 18 : import XML tabulaire explicite

**2026-11-06 — préparation en quarantaine, aucune publication réglementaire.**

## Audit préalable

Inspection du lecteur CSV/JSON/XLSX, du mapping commun, des contrôles TariffBatch,
du rejeu central, du CLI et de la sauvegarde. `SourceDocument.format` prévoyait XML,
mais aucun adaptateur ne le lisait et le chargeur refusait l’archive `.xml`.
Extension du chemin central plutôt que création d’un magasin ou importateur isolé.
Aucun nouveau fichier officiel ou StarterPack n’est apparu dans le dépôt.

## Livré

- Lecteur XML 1.0 UTF-8 tabulaire plat, noms racine/ligne explicitement déclarés,
  mapping existant par nom d’élément, champs textuels sans conversion numérique.
- DTD/entités déclarées/résolution externe/commentaires/instructions de traitement,
  attributs, namespaces, champs imbriqués, contenu mixte et encodages autres refusés.
- Bornes lignes/colonnes/cellules/champ/source, aucune ligne partielle publiée.
- Codes chaînes, zéros initiaux, parents, doublons, désignations et sources contrôlés
  par les mêmes modèles ; aucun taux ou parent inventé.
- `customs-prepare` inchangé : plan sans écriture, préparation sur option explicite
  vers répertoire neuf, source XML et sidecar archivés sans modification.
- Provenance par élément/ligne physique, périmètre XML et colonnes non importées
  documentés ; chargeur de lots étendu pour empreintes et rejeu XML/mapping.
- Revue et sauvegarde/reprise réutilisées, sans import HTTP ou activation nouvelle.

[Contrat, commandes et limites](IMPORT_XML.md).
Les valeurs suivent les règles XML (entités prédéfinies/numériques, CDATA, fins de
ligne) ; la conservation octet à octet concerne le fichier source archivé, pas une
prétendue identité lexicale entre les valeurs interprétées et leurs octets source.

## Qualification

**911 tests Python réussis, 1 avertissement Starlette/httpx**, sélection douanière
isolée du lot 17 + `tests/test_customs_xml.py` : **850 + 61 nouveaux cas**.
**40 scénarios UI JSDOM réussis**, sans nouveau scénario UI revendiqué.
Ruff et `git diff --check` passent. Pas de suite complète du dépôt annoncée.

Cas XML : plan sans écriture, archivage identique aux octets reçus, zéros initiaux,
TVA inconnue null, provenance physique, chargeur/rejeu/diff, refus de sortie
existante, FR/AR, entités prédéfinies/CDATA, ordre de champs variable, colonnes
non importées signalées, doublons, champs manquants/dupliqués, erreurs de structure,
DTD/entités externes, options hors contrat, limites et contrôles métier réutilisés.

Cinq cas exercent de vrais GET API sur un lot XML temporaire épinglé : contrôle,
recherche, arbre, fiche et couverture, avec audit et corpus inchangé après lecture.
Un cas sauvegarde et restaure les octets XML en magasin neuf, puis rejoue le lot.
Un lot normalisé altéré puis re-haché est refusé pour divergence du rejeu.
CLI plan/refus et interdiction des options XML hors XML sont vérifiés.
Toutes les fixtures sont **NON OFFICIELLES**, distinctes des magasins utilisateur.

Première sélection étendue : 909 réussites / 1 échec d’assertion de test, qui lisait
`publication_active` sur TariffBatch au lieu du rapport. Assertion corrigée sans
modification du contrat métier ; ajout du contrôle d’altération/rejeu, puis
réexécution complète de cette sélection : **911 réussites**.

Prévisualisation backend redémarrée sur 0.0.0.0:8000 avec le lecteur à jour :
coque/module/service worker 200 avec hôte de prévisualisation, revue anonyme 403.
Aucun lot/registre/compte de production créé pour ce contrôle. Coque v48 inchangée.
Journaux de service conservés et non inclus dans le commit.
Empreintes historiques après redémarrage inchangées :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Qualification d’un contrat technique, **pas qualification du format d’un fichier
national officiel acquis**. Pas d’XSD officiel, XPath, XML hiérarchique/namespacé,
XSLT, XLS, import tarifaire PDF ou ZIP qualifié. Le fichier XML et le sidecar
n’authentifient pas l’éditeur. Aucune complétude nationale, fiscalité courante,
consolidation, validation juridique, immutabilité WORM ou calcul applicable établi.
Les bornes ne garantissent pas une consommation globale RAM/temps constante.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux et modifications exhaustifs,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués.
