# Rapport lot 36 — préparation JSON de mesures indépendantes du tarif

Date : 7 novembre 2026. Branche : `arena/2cd4c91a-ocr-universal`.

## Audit et livré

Audit du tableau des restes, de TariffBatch/Mesure et des périodes, de la préparation
et du rejeu tarif/Code, du registre et des sauvegardes. Le contrat TariffBatch
imposait une nomenclature pour préparer des mesures. Ajout d'un contrat autonome :

- `MetadataMesuresAutonomes`/`MesuresAutonomesBatch` et deux schémas JSON ; réutilisation
  de Mesure/SourceDocument et du lecteur strict/limites existants, sans inventer de ligne.
- CLI `customs-fiscal-prepare`, plan par défaut ; écriture explicite dans un dossier
  neuf, source/sidecar conservés et manifeste en dernier.
- CLI `customs-fiscal-check`, empreintes et rejeu source/métadonnées/lot/rapport.
- Taux exacts en chaînes, null/zéro distingués, références locales et périodes propres.
- Aucune extension prématurée du registre : nouveaux lots refusés comme tarif/Code ;
  aucune UI isolée ou route susceptible de choisir silencieusement le mauvais chargeur.

[Contrat et limites](MESURES_AUTONOMES.md), [tableau](TABLEAU_LOTS.md).

## Vérifications exécutées

- **1 443 tests Python réussis**, sélection étendue **44 fichiers**, **26,54 s**,
  1 avertissement préexistant Starlette/httpx. Pas la suite OCR entière.
- **48 nouveaux cas Python** : plan/écriture/rejeu sans écrasement, taux précis/zéro/null,
  codes avec zéros sans validation d’existence nationale, dates distinctes, tableau
  vide, IDs/mesures/provenance/JSON/activation invalides, source symbolique, artefact
  trop volumineux, archives altérées y compris re-hachées, schémas et CLI.
- Sauvegarde/reprise réelle existante : octets du lot autonome conservés, chargement
  et rejeu réussis, option explicite exigée, aucun lot activé.
- **122 scénarios JSDOM existants réussis**, pas de nouvel écran. Pont existant :
  **12 exports JSON** et **1 copie PDF** revérifiés, sans extension aux lots autonomes.
- Ruff et `git diff --check` : succès.
- Empreintes historiques inchangées : base
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ; référentiels
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et état global

**0 nouvel original officiel acquis, 0 article/code10 officiel validé,
0 publication active.** Le chantier d'import fiscal autonome a maintenant un socle
JSON local ; sa qualification officielle, ses formats tabulaires/PDF, sa revue
administrative et le rapprochement multi-source restent à réaliser. Aucun calcul,
droit à date, validation humaine ou publication ajoutés. Aucune preuve de complétude.

Aperçu existant conservé (UI/API inchangées, cache v61) ; ce lot s'exécute via CLI.
Journaux existants préservés hors commit. Pas de benchmark national ou mémoire constante.
