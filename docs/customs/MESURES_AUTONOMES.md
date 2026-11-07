# Préparation de mesures autonomes — lot 36

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

Le fichier source est un **tableau JSON de Mesure**, pas un objet contenant une
nomenclature. Le sidecar suit `MetadataMesuresAutonomes` : source requise, version
1/statut quarantaine/validation non validée/publication false par défaut. Il ne
peut contenir de mesures, lignes ou autres champs inconnus. Sa source suit
SourceDocument, format **json uniquement** et empreinte exacte du fichier reçu.
Les schémas `MetadataMesuresAutonomes.schema.json` et
`MesuresAutonomesBatch.schema.json` sont dans `schemas/`.

### Règles explicites

- Source et références déclarées : domaine officiel HTTPS autorisé, SHA256 exact,
  ID/titre/organisme/version non blancs. Cela ne prouve pas l'authenticité.
- Chaque mesure fournit ID unique local au lot, type connu, description, code10
  chaîne exacte de dix chiffres ASCII, référence à la source du même lot et
  localisateur non blanc. Aucun ID, code, taux ou localisateur n'est généré.
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

Source et sidecar conservés octet pour octet : `source_mesures_recue.json`,
`metadata_original.json`, puis `lot_mesures.json`, `rapport.json`, `manifest.json`.
Le manifeste est écrit en dernier ; une interruption peut laisser un dossier
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

**Pas encore de type autonome dans le registre de revue, d'API/interface de lecture,
de diff/fiche ou de rapprochement inter-sources pour ces nouveaux lots.** Le registre
reste strictement code/tarif : ne pas y ajouter une entrée « mesures », ni déclarer
ce dossier comme tarif ou Code pour contourner le refus. Les anciennes routes,
fiches et recherches continuent à traiter leurs contrats précédents.

JSON strict seulement : pas d'import fiscal autonome CSV/XLSX/PDF qualifié, pas de
transcription automatique de texte fiscal. Aucun exemple de taux de production,
fichier officiel national, validation humaine, droit à date, publication ou calcul.
Les schémas et tests ne démontrent pas la complétude réglementaire. Les tests utilisent
exclusivement des fixtures explicitement NON OFFICIELLES.
