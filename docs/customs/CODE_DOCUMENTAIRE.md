# Code des douanes : format de préparation documentaire

2026-11-06. **Quarantaine uniquement, aucune applicabilité ni authenticité attestée.**

## Périmètre

Le lecteur reçoit des PDF locaux et une transcription structurée **déclarée**.
Il conserve les octets reçus, sans analyse de leur texte, OCR, téléchargement,
exécution, déchiffrement, traduction ou consolidation. Il n’établit pas que les
PDF sont les originaux de l’éditeur, que la transcription correspond aux pages,
que les numéros/dates/relations sont exacts ou que le corpus est complet.

La seule vérification de format PDF est le préfixe `%PDF-` : ni qualification
structurelle, ni validation de signature numérique, ni analyse antivirus.
Une URL autorisée et un SHA256 ne constituent pas une authentification.
Un rôle documentaire déclaré peut être faux : la cohérence du lot n’en prouve
pas la véracité. Toute admission réglementaire reste une revue humaine future.

## Entrées

### Transcription JSON

Objet contenant **exactement** `articles` et `relations`, deux tableaux pouvant
être vides. Pas de source, activation ou ligne de texte fournie par le sidecar.
Les champs d’un article sont ceux d’`ArticleVersion` ; les relations ont les
champs de `RelationJuridique` dans le schéma du lot. Pas de champ inconnu, clé
JSON dupliquée, NaN ou conversion implicite d’un nombre en numéro d’article.

- `id`, `numero_article`, `version_juridique` et `texte_integral` non vides.
  Numérotation conservée littéralement, y compris suffixes et espaces ; aucune
  normalisation automatique de « bis », d’arabe ou de chiffres.
- `numero_article` désigne l’unité transcrite **dans son document**. Un article
  d’une loi modificative peut avoir un numéro différent de l’article du Code
  visé : la cible est une relation explicite, jamais une égalité de numéros.
- Hiérarchie ordonnée et sans niveau dupliqué, avec `texte_legislatif` et
  `article` ; l’identifiant de ce dernier égale le numéro transcrit. Les niveaux
  intermédiaires inconnus ne sont pas inventés.
- `reference.source_id` doit identifier un document reçu ; `localisateur` non
  vide, déclaré par le transcripteur (page/article/alinéa, à vérifier ensuite).
- `nature_version=originale` exige un document déclaré `code_original` ;
  `modificative`, un `acte_modificatif` ; `consolidee_provisoire`, une
  `compilation`. Cela ne qualifie pas le contenu réel du PDF.
- L’original ne reçoit pas de `texte_modificatif`. Si `texte_origine` est fourni,
  il doit égaler son `texte_integral`. Une disposition modificative ne reçoit
  pas de texte original ; son éventuel `texte_modificatif` égale son texte
  intégral. Les compilations sont des versions séparées, sans ces deux champs.
  Les reconstructions à partir de plusieurs textes ne sont pas implémentées.
- FR/AR restent optionnels, sans traduction ni vérification linguistique.
  Une chaîne linguistique vide doit être remplacée par null par le fournisseur,
  jamais automatiquement corrigée par le lecteur.
- Unicité par ID et par `(source_id, numero_article, version_juridique)` ;
  plusieurs versions peuvent partager un numéro, sans être fusionnées.
- Les références d’`historique_modifications` pointent sur des documents
  modificatifs archivés. C’est un historique **déclaré**, pas un moteur juridique.
- `validation_juridique=non_validee` demeure obligatoire. Un
  `statut_juridique_declare=applicable` ne donne aucune autorisation d’usage.

### Relations

Types acceptés : `modifie`, `complete`, `abroge`, `rectifie`, `renvoie_a`.
Chaque relation identifie deux articles effectivement présents dans ce lot,
une justification non vide et une preuve localisée dans la source de l’article
à l’origine de la relation. Pas de cible fantôme, d’auto-relation ni de preuve
exactement dupliquée. Plusieurs preuves distinctes d’un lien restent possibles.

Les quatre premiers types exigent une origine modificative. Si les deux dates
de publication documentaires sont déclarées, la modification ne peut pas
précéder le document cible. Cela ne détermine pas une date d’effet : les règles
rétroactives, transitoires et territoriales ne sont pas évaluées. Les cycles de
modifications sont refusés ; les renvois réciproques sont permis.

Les IDs d’`articles_lies` nécessitent une relation sortante justifiée correspondante.
Le verbe `abroge` représente une assertion documentaire non validée : il ne
change pas silencieusement le statut ou le texte cible. Les relations inter-lots
et article/code tarifaire ne sont pas encore traitées. Ne pas fabriquer un article
pour résoudre une cible absente : conserver la question pour la revue documentaire.

### Sidecar JSON

Objet avec le seul champ `documents` : tableau de 1 à 64 objets comprenant :

- `document` : `DocumentJuridique` (`id`, `titre`, `url`, `organisme`,
  `version_source`, `sha256`, `format="pdf"`, `nature_document`, éventuellement
  `date_publication`, et `verification="non_verifiee"`).
- `fichier_recu` : nom local simple du PDF, dans le dossier du sidecar. Aucun
  chemin absolu, séparateur, traversée, lecteur Windows ou lien symbolique.

Les fichiers locaux répétés sont refusés ; deux noms distincts ayant le même
SHA256 sont conservés et signalés comme doublon d’octets, sans fusion silencieuse.
Les sources non utilisées par une transcription d’article restent archivées et
signalées : cela permet l’acquisition documentaire sans inventer de transcription.

## Commandes et sorties

```sh
# Plan : lit et vérifie, ne crée pas de lot ni de store.
PYTHONPATH=src python -m unocr.cli customs-code-prepare /chemin/transcription.json --metadata /chemin/metadata.json

# Écriture explicite : parent existant, dossier de destination neuf.
PYTHONPATH=src python -m unocr.cli customs-code-prepare /chemin/transcription.json --metadata /chemin/metadata.json --out /chemin/lot-code-neuf --write
```

Sortie JSON ; code 0 = préparation techniquement admise, **pas validité juridique** ;
code 2 = refus. `--out` seul ne crée rien ; `--write` exige `--out`.

Limites : 64 Mio pour chaque fichier d’entrée, 128 Mio au total (transcription et
sidecar compris), 64 documents, 50 000 articles, 100 000 relations par lot. Ces
limites ne sont pas une garantie globale de mémoire ou de temps d’exécution.

Tous les contrôles précèdent la création du dossier. Les fichiers sont écrits
en création exclusive, dans un dossier neuf :

- `transcription_recue.json`, `metadata_original.json` : octets exacts reçus ;
- `document_0001.pdf`, etc. : octets exacts des documents reçus, sans décodage ;
- `lot_code.json` : structure normalisée, distincte des originaux archivés ;
- `rapport.json` : périmètre, compteurs, sources sans article, doublons, limites ;
- `manifest.json` en dernier : correspondances source/nom reçu/nom d’archive,
  date machine UTC et SHA256 de tous les fichiers précédents.

Une interruption peut laisser un dossier partiel, conservé sans remplacement ni
nettoyage automatique. Pas de garantie de coupure électrique, de journal WORM ou
d’immutabilité contre un administrateur. Aucun chargement en référentiel actif.

`customs-diff` est réservé aux lots **tarifaires** et refuse ces lots de Code.
Le vérificateur/rejeu et le diff des lots de Code, la déduplication inter-lots,
la reconstruction, la sélection à date et les API de consultation/validation
ne sont pas livrés dans cette étape. Le manifeste seul ne suffit pas à publier.
