# Intégration des deux PDF juridiques fournis

## Documents intégrés

Lot local de revue : **`lois_recues_1979_2017`**, type `code`, statut quarantaine.
PDF archivés intégralement, octet pour octet ; empreintes contrôlées et manifeste
épinglé au registre local. Aucun téléchargement ni URL officielle inventée.

| Fichier reçu | Qualification documentaire retenue | Pages physiques |
|---|---|---:|
| `loi_no_17-04_du_16_fevrier_2017_code_des_douanes.pdf` | Acte modificatif17-04 ; copie présentant le JO n°11 du19 février2017 | 35 |
| `loi_no79-07_du_21_juillet_1979.pdf` | **Compilation affichant « Mise à jour Juin2017 »**, et non édition originale de1979 | 186 |

La date de publication indiquée pour la première copie vient de son en-tête.
Aucune date de publication de1979 n'a été attribuée à la compilation. Les deux
sources restent séparées ; pas de fusion ni de consolidation automatique.

## Conservation et exploitation documentaire

- Archives conformes au format existant, contrôlables avec `customs-code-check`.
- Documents répertoriés par le catalogue de sources de la revue, avec leur
  nature, empreinte, titre et provenance **pièce jointe utilisateur**.
- Nouveau contrat `DocumentJuridiqueRecu` pour une copie sans URL connue ;
  l'ancien contrat de référence officielle et ses contrôles restent inchangés.
- Texte natif extrait pour **221 pages**, avec numéro physique et SHA du texte
  UTF8 par page. Aucun OCR, traduction ou remplacement silencieux de caractères.
- Les copies restent consultables par le lecteur PDF natif contrôlé du module.
- **0 article transcrit dans le modèle juridique et0 relation juridique inférée** :
  les textes intégraux des PDF sont conservés, mais ne sont pas découpés en
  articles juridiquement qualifiés. Une recherche structurée d'articles ne doit
  donc pas être confondue avec l'accès aux pages et au texte brut extrait.

Le PDF17-04 contient un texte natif avec caractères dégradés, par exemple
« fÈvrier ». L'extraction les conserve. Une correction contrôlée ou un OCR avec
rapprochement visuel devra précéder son utilisation comme transcription fiable.
L'ordre d'extraction des colonnes peut aussi différer de l'ordre visuel.

## Emplacements et portabilité

- Lot : `data/customs-quarantine/lois_recues_1979_2017/`.
- Registre : `data/customs-quarantine/registre.json`.
- Copies reçues, métadonnées et extractions page par page :
  `data/legal-receipts/lois_recues_1979_2017/`.
- Reçu et empreintes : [RECEPTION_LOIS_1979_2017.json](RECEPTION_LOIS_1979_2017.json).
- Paquet transportable : `/home/user/livraisons/documents_juridiques_1979_2017.zip`.

Les PDF, extractions et registre local sont **hors Git**, dans le workspace
persistant. Le paquet ZIP contient les copies, le lot, ses preuves et le registre
fermé ; il doit être conservé séparément pour une reprise dans une autre
installation. Les schémas, tests et reçu d'intégration sont versionnés.
Ne pas remplacer un registre existant par celui du paquet : fusion et habilitations
à effectuer par l'exploitant après vérification des empreintes.

## Vérifications exécutées

- **174 tests ciblés réussis**, dont12 nouveaux cas de provenance/schéma/import,
  rejeu, catalogue et maintien des contrôles de l'ancien format.
- **2276 tests documentaires réussis**, aucun échec/ignoré ;212 scénarios JSDOM
  historiques réussis dans la recette.
- Sur les **vrais fichiers reçus** : rejeu du lot, catalogue des deux sources,
  comparaison des SHA aux pièces jointes et lecture contrôlée des premières et
  dernières pages de chaque PDF réussis (pages1/35 et1/186).
- Ruff source/tests/recette et diff réussis. Schémas JSON régénérés après extension ;
  leur égalité avec les modèles est testée.
- La suite OCR complète n'a pas été relancée pour cette réception ; ses résultats
  historiques ne sont pas présentés comme une nouvelle qualification.

Artefacts de recette : `/home/user/recettes-unocr/reception-lois/`.

## Statut juridique et disponibilité dans l'application

**Deux copies utilisateur intégrées ; authenticité, exhaustivité et applicabilité
non établies.** Aucune publication, activation de règles, calcul fiscal ou
consolidation à date. Les SHA identifient les copies, pas leur autorité juridique.
Le texte original de1979 n'est pas apporté par la compilation de2017.

Le registre a été créé sans attribuer de nouvelle habilitation (`reviseurs: []`).
Les droits ne sont pas ouverts automatiquement pour rendre l'écran accessible.
Le serveur partagé existant n'a pas été redémarré : sa version chargée ne sait
pas nécessairement lire ce nouveau contrat de provenance. La consultation par
l'interface de revue exige donc un backend actualisé et un compte nominatif
habilité ; l'archivage et les lecteurs locaux actuels sont vérifiés.
