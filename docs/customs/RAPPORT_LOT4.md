# Avancement — lot 4 : contrôle/rejeu et comparaison des lots du Code

**2026-11-06 — contrôle documentaire local, aucune validation juridique.**

## Livré

- `customs-code-check LOT` : vérifie un lot Code archivé et rejoue sa préparation
  depuis les octets contrôlés, sans relire les fichiers d’origine hors archive.
- `customs-code-diff AVANT APRES` : vérifie les deux lots puis rapporte les écarts
  entre documents, articles et relations, en lecture seule.
- Lecture stricte des manifestes Code : quarantaine, absence de publication,
  date machine UTC, inventaire exact, indices continus des PDF et SHA256.
  Refus des fichiers absents/inattendus, répertoires substitués et symlinks directs.
- Rejeu commun avec l’importeur du lot 3, en mémoire : contrôle du lot normalisé,
  du rapport complet et de la correspondance documents/noms reçus/archives.
  Les types JSON imbriqués sont comparés sans assimiler `true` à `1`.
- Appariement par ID déclaré, **pas par numéro d’article ni ressemblance**.
  Ajouts/retraits détaillés avec leurs références ; localisateurs primaires
  séparés des changements de contenu ; textes et arabe non normalisés.
- Avertissements pour périmètres différents, version documentaire inchangée
  avec PDF différents et ID d’article conservé malgré changement de numéro,
  nature ou version juridique. Aucune conclusion d’abrogation/date d’effet.

[Commandes, format, bornes et interprétation détaillés](CODE_DOCUMENTAIRE.md).
L’importeur conserve son interface et ses archives du lot 3 ; les schémas ne
changent pas. Aucune dépendance ajoutée, aucun endpoint HTTP ni store actif créé.
Les lots tarifaires et les lots Code ne sont pas interchangeables.

## Ce que signifie un résultat positif

`integrite_locale=coherente_au_rejeu` signifie uniquement que les fichiers
concordent avec le résultat du lecteur courant. Les mêmes archives peuvent
être contrôlées après déplacement, même si le dossier d’acquisition a disparu.

Cela ne vérifie **ni l’origine officielle ni la correspondance transcription/PDF**.
Une personne pouvant réécrire toutes les sources, sorties et empreintes peut
produire un nouveau lot cohérent. Pas de WORM, d’horodatage certifié ou de preuve
de validité juridique. Le préfixe `%PDF-` reste un simple contrôle de signature
de format, pas une analyse structurelle/antivirus du PDF.

Code 0 = contrôle/comparaison technique effectué ; code 2 = refus intégral.
Si l’un des lots est incohérent, aucun diff partiel n’est présenté comme valide.
Aucun document, rapport, manifeste ou store n’est modifié. La lecture reste
bornée à 64 Mio par fichier et 256 Mio pour l’archive complète, manifeste compris.

## Validation technique

**282 tests réussis, 1 avertissement Starlette/httpx**, sous répertoires data/logs
isolés : les 221 cas de la sélection lot 3 et **61 nouveaux cas** de contrôle/diff.
Il s’agit d’une sélection ciblée, pas de la suite complète du dépôt.

```sh
python -m pytest tests/test_customs_legal_comparison.py tests/test_customs_legal.py \
  tests/test_customs_reference.py tests/test_customs_xlsx.py \
  tests/test_customs_comparison.py tests/test_corrections_routes.py \
  tests/test_referentiels.py tests/test_referentiels_base.py \
  tests/test_customs_connector.py -q
```

Les nouveaux tests couvrent : identité, portabilité sans fichiers d’origine,
textes/AR/espaces/périodes/historiques déclarés, sources, relations, changements
d’ID, provenance, retrait sans abrogation, périmètres, PDF différents sous la
même version déclarée, archivage sans article, corruption d’empreintes,
lot/métadonnées/rapport modifiés puis re-hachés, types JSON incohérents,
manifestes non admissibles, traversées, symlinks, fichiers supplémentaires,
indices discontinus, décalage de nombre de documents, JSON à clés dupliquées,
limite de taille, bornes admises de 1 et 64 documents, et commandes dans un processus indépendant sans création de stores.

Fixtures exclusivement **NON OFFICIELLES**, temporaires, jamais un corpus public.
Ruff `src tests`, identité des schémas (tests existants) et `git diff --check`
contrôlés également. Les SHA256 historiques sont inchangés :

- `data/reglementation/base.json` :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`
- `data/referentiels.json` :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`

## Complétude et suites

**0 nouveau document officiel acquis, 0 article officiel validé, 0 publication.**
Le corpus original/modificatif exhaustif et sa chronologie, le StarterPack,
l’export national tarifaire et les sources fiscales restent manquants.
Les deux calculs douaniers legacy non sourcés restent bloqués.

La déduplication inter-lots, le registre central avec historique protégé, le
workflow humain habilité, les relations Code/tarif, la reconstruction provisoire,
la sélection à date juridiquement revue, les API v1, la recherche FR/AR, l’IA et
l’administration intégrée restent à construire. Les présents outils ne publient
pas leur contenu dans les modules marchandise/transit/facturation. Aucun usage
douanier réel n’est autorisé par une simple réussite du contrôle local.
