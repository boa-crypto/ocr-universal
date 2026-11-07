# Préparation de mesures autonomes — JSON (36), CSV (39), XLSX (40), XLS (41), PDF transcrit (42)

Premier contrat indépendant d'une nomenclature : droits, TVA, autres taxes,
restrictions, autorisations et régimes reçus avec leur propre source, références
et périodes. Aucune ligne tarifaire ou hiérarchie artificielle nécessaire.
**Préparation locale uniquement, pas référentiel actif ou fiscalité applicable.**

## CLI : plan par défaut, écriture explicite

```sh
unocr customs-fiscal-prepare SOURCE.json --metadata METADATA.json
unocr customs-fiscal-prepare SOURCE.json --metadata METADATA.json --out NOUVEAU_DOSSIER --write
unocr customs-fiscal-check NOUVEAU_DOSSIER
```

Sans `--write`, aucune écriture, même si `--out` est fourni. Avec `--write`, `--out`
est obligatoire et le dossier doit être neuf, parent existant. Pas de remplacement
ni modification des anciens lots. Code de sortie 0 si succès, 2 si refus.

Pour le format JSON, le fichier source est un **tableau JSON de Mesure**, pas un objet contenant une
nomenclature. Le sidecar suit `MetadataMesuresAutonomes` : source requise, version
1/statut quarantaine/validation non validée/publication false par défaut. Il ne
peut contenir de mesures, lignes ou autres champs inconnus. Sa source suit
SourceDocument, format **json, csv, xlsx, xls ou pdf** et empreinte exacte du fichier reçu.
Pour CSV, le sidecar suit `ConfigurationMesuresAutonomes` : voir le
[contrat CSV](MESURES_AUTONOMES_CSV.md), mapping explicite requis.
Pour XLSX : [feuille et mapping explicites](MESURES_AUTONOMES_XLSX.md),
cellules mappées textuelles exclusivement.
Pour XLS : [sous-ensemble OLE/BIFF8 textuel](MESURES_AUTONOMES_XLS.md),
contrôles binaires et restrictions plus fortes que XLSX.
Pour PDF : [document opaque et transcription JSON séparée](MESURES_AUTONOMES_PDF.md),
option `--transcription` requise, aucune extraction automatique.
Les schémas `MetadataMesuresAutonomes.schema.json` et
`MesuresAutonomesBatch.schema.json` sont dans `schemas/`.

### Règles explicites

- Source et références déclarées : domaine officiel HTTPS autorisé, SHA256 exact,
  ID/titre/organisme/version non blancs. Cela ne prouve pas l'authenticité.
- Chaque mesure fournit ID unique local au lot, type connu, description, code10
  chaîne exacte de dix chiffres ASCII, référence à la source du même lot et
  localisateur non blanc. En JSON ou transcription PDF aucun ID, code, taux ou localisateur n'est généré ;
  en CSV/XLSX/XLS seul le localisateur physique est généré, sans signification juridique.
- **Taux JSON uniquement en chaîne décimale ou null**, jamais nombre JSON converti
  via float. Zéro déclaré distinct de null. Taux non négatif, fini ; unité
  `pourcent` obligatoire avec un taux et interdite seule ; aucun taux sur une
  restriction/autorisation/régime. Aucune conversion de devise/unité ou arrondi.
- Dates ISO propres aux mesures, non héritées de la publication, d'une nomenclature
  ou d'une autre source. Fin antérieure au début refusée.
- Tableau vide admis : aucune mesure reçue, jamais exonération ou absence de droit.
- Codes contrôlés syntaxiquement seulement : **existence nationale et rattachement
  à une ligne non vérifiés**. Un même code peut recevoir plusieurs mesures sans
  fusion ni choix de taux, de régime, de source ou de période applicable.
- JSON à clés dupliquées/constantes non standard refusé. Fichiers réguliers non
  symboliques, lecture bornée à 64 Mio ; maximum 100 000 mesures par modèle.

## Archive et contrôle

Source et sidecar conservés octet pour octet : `source_mesures_recue.json` ou
`source_mesures_recue.csv`, `source_mesures_recue.xlsx` ou
`source_mesures_recue.xls` ou `source_mesures_recue.pdf` selon le format
(une seule source),
`metadata_original.json`, puis `lot_mesures.json`, `rapport.json`, `manifest.json`.
Avec PDF, ajouter `transcription_mesures_recue.json` original exact : six fichiers,
sinon cinq. Le manifeste est écrit en dernier ; une interruption peut laisser un dossier
incomplet, non rejouable, jamais réutilisé silencieusement. Pas de transaction FS,
fsync/WORM/signature ou garantie contre les courses multi-processus ajoutée.
Les artefacts générés trop volumineux pour la lecture bornée sont refusés avant
création du dossier. La préparation en mémoire n'est pas un import en streaming.

Le chargeur exige le type autonome, UTC, fichiers exacts et empreintes cohérentes,
puis rejoue source/métadonnées et compare le lot normalisé et le rapport. Re-hacher
un lot normalisé substantiellement altéré ne contourne pas le rejeu. Un attaquant
capable de remplacer ensemble source/métadonnées/manifeste ne devient pas authentifié.

La sauvegarde existante `--include-customs-quarantine` et la reprise dans un magasin
neuf conservent aussi ce dossier lorsqu'il est placé dans la quarantaine ; test
exécuté, sans changement de leur contrat ni activation du lot repris.

## Limites de cette livraison

Depuis le [lot 37](REVUE_MESURES_AUTONOMES.md), le type `mesures` peut être inscrit
explicitement au registre et consulté dans la revue centrale : contrôle, recherche
de mesures, inventaire de source, couverture et exports. Pas de diff/fiche de
nomenclature, lecture/téléchargement PDF, rapprochement fiscal ou publication pour ce type ; les anciennes
routes incompatibles sont refusées, jamais détournées vers un chargeur tarif/Code.

JSON strict, CSV/XLSX/XLS textuels à mapping explicite et PDF opaque avec
transcription déclarée : aucun fichier fiscal officiel qualifié, aucune
transcription automatique de texte fiscal. Aucun exemple de taux de production,
fichier officiel national, validation humaine, droit à date, publication ou calcul.
Les schémas et tests ne démontrent pas la complétude réglementaire. Les tests utilisent
exclusivement des fixtures explicitement NON OFFICIELLES.

Lot 38 : [consultation nomenclature et mesures autonomes](CONSULTATION_TARIF_MESURES.md), CLI `customs-tariff-measures`, API racine `/tariff-measures`. Paire tarif/mesures explicitement autorisée pour cette seule opération, sources/paginations séparées et export à double provenance. Aucun rattachement juridique établi.
