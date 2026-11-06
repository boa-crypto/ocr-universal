# Avancement — lot 3 : Code, documents reçus et transcriptions déclarées

**2026-11-06 — socle documentaire en quarantaine ; aucune publication juridique.**

## Livré

- Nouveau contrat `CodeDocumentaireBatch` : sources PDF déclarées, articles
  individuels, versions originales/modificatives/compilations provisoires
  séparées, relations documentaires explicitement justifiées.
- Commande `customs-code-prepare` : plan sans écriture par défaut ; écriture
  explicite dans un dossier neuf, octets PDF et transcription préservés,
  manifeste final et empreintes. L’archivage avec zéro article est possible.
- Contrôles : sources/localisateurs, hiérarchie, unicité, périodes déclarées,
  séparation des textes, correspondance des rôles documentaires, liens
  justifiés, absence de cible fantôme, chronologie de publication déclarée,
  cycles de modifications. Les renvois réciproques sont permis.
- Deux JSON Schemas générés et testés : `CodeDocumentaireBatch` et `MetadataCode`.
- [Guide du format, des commandes et des limites](CODE_DOCUMENTAIRE.md).

L’article d’un acte modificatif et celui du Code visé peuvent porter des numéros
**différents** : c’est la relation sourcée qui les relie, pas une ressemblance.
Les anciens modèles et données ne sont ni migrés ni remplacés. Pas de deuxième
interface ni de store métier actif ; intégration future sur le domaine central.
Aucune dépendance supplémentaire introduite.

## Ce qui n’est pas établi

La commande ne fait **aucun OCR ni rapprochement transcription/PDF**. Le rôle,
les références, langues et dates restent déclarés et non validés. Le contrôle
`%PDF-` n’est pas un contrôle structurel, d’authenticité ou antivirus du document.
La compilation reste provisoire ; aucun nouveau texte consolidé n’est produit.

**0 document officiel acquis, 0 article officiel importé/validé dans ce lot.**
Les tests utilisent seulement des fixtures temporaires NON OFFICIELLES ; leurs
PDF minimaux ne sont pas des copies de JO et ne qualifient pas un corpus réel.
Le StarterPack, les originaux et modifications complets, l’export national tarifaire
et la validation humaine restent manquants. Aucun taux applicable, date d’effet
ou abrogation juridiquement établie n’est déduit de ces préparations.

Restent notamment : lecteur/rejeu et diff des lots Code, déduplication inter-lots,
corpus exhaustif et chronologie, liens inter-domaines, reconstruction provisoire,
restitution à date juridiquement revue, validation habilitée, publication, recherche
FR/AR, classification IA, API v1 et administration intégrée. Le CLI de préparation
ne contourne pas l’absence d’un workflow de validation sécurisé.

## Résultats techniques

**221 tests réussis, 1 avertissement Starlette/httpx**, sous répertoires data/logs
isolés : les 155 tests de la sélection lot 2 + **66 nouveaux cas** documentaires.
Ce n’est pas la suite complète du dépôt.

```sh
python -m pytest tests/test_customs_legal.py tests/test_customs_reference.py \
  tests/test_customs_xlsx.py tests/test_customs_comparison.py \
  tests/test_corrections_routes.py tests/test_referentiels.py \
  tests/test_referentiels_base.py tests/test_customs_connector.py -q
```

Nouveaux contrôles exercés : conservation exacte des PDF non UTF-8, texte et
arabe non normalisés, numéros d’articles distincts entre acte et cible, sources
séparées, doublons, formalisme du JSON, références absentes, liens sans preuve,
fusions interdites, cycles, chronologie contradictoire, chemins et symlinks,
limite totale, drapeaux de publication stricts, sortie existante non écrasée,
interruption Python avant manifeste final et CLI dans un processus indépendant
sans création de stores. Ce test d’interruption n’est pas une panne électrique.
Ruff `src tests`, identité des schémas et `git diff --check` contrôlés également.

SHA256 des deux données historiques toujours préservés :

- `data/reglementation/base.json` :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`
- `data/referentiels.json` :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`

Les deux calculs douaniers legacy non sourcés restent bloqués. La préparation
locale n’est connectée à aucun calcul ni référentiel activable automatiquement.
