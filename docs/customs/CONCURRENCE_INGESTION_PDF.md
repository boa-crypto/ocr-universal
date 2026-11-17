# Lot 64 — concurrence PDFium et durée de vie native

7 novembre 2026. Périmètre : ingestion des PDF par `unocr.ingest`, pas une
qualification de charge, de PDF malveillants ou de calcul réglementaire.

## Constat reproduit

Le lot 63 signalait une perte de serveur pendant deux dépôts concurrents, sans
cause établie. Un essai distinct a lancé quatre threads qui chargent des PDF
synthétiques différents dans un **processus sacrifiable**, avec faulthandler.
Avant correction : arrêt natif `corrupted size vs. prev_size`,
`Fatal Python error: Aborted`, code shell **134**, avant le bilan des 20 chargements.
Cet incident démontre un défaut d'ingestion concurrente ; il n'est pas une preuve
rétrospective de la cause exacte de la perte du serveur du lot 63.

Le README amont de [pypdfium2](https://github.com/pypdfium2-team/pypdfium2/blob/b829293387dc6fb6a07716fa0e8438810ba91f8b/README.md#incompatibility-with-threading)
indique explicitement que PDFium n'est pas thread-safe. Source lue via l'API
GitHub ; pas extrapolation à partir de la seule trace de crash.

## Correction

`_load_pdf` utilise un **RLock unique au module, par processus**, avant toute
création de document PDFium. Le verrou couvre le comptage des pages, l'extraction
native, le rendu, la copie des pixels et la fermeture des ressources. L'extraction
pdfminer reste également dans cette section pour conserver le contrôle du nombre
de pages avant son exécution, sans réouverture native intermédiaire.

- Document fermé par son gestionnaire de contexte, y compris refus `max_pages`.
- Page et bitmap fermés explicitement avec `contextlib.closing`, y compris les
  exceptions de lecture, rendu ou conversion. Ces deux objets ne fournissent pas
  de gestionnaire de contexte dans la version installée.
- L'image Pillow est convertie en RGB **avant** la fermeture du bitmap : les
  pixels copiés restent utilisables après la fermeture des objets natifs.
- Retour limité aux images et structures Python ; aucun objet PDFium n'échappe
  à cette section. Le sémaphore global des jobs n'est pas artificiellement réduit
  à un seul job : OCR et étapes suivantes restent hors du verrou PDFium.

Le worker d'extraction documentaire `customs_reference/pdf_worker.py` conserve
son fonctionnement séparé : appel dans un processus jetable par `pdf_page.py`,
sans rendu/OCR. Il n'est pas transformé en appel concurrent dans le processus API.
Le verrou d'ingestion ne protège pas une extension tierce qui appellerait PDFium
directement ailleurs, ni une exécution après fork pendant qu'un verrou est détenu.

## Contrôles

**12 cas unitaires avec doubles**, distincts des preuves natives : création,
comptage, layouts, accès page, dimensions, mots natifs, rendu, `to_pil`, conversion,
refus du nombre de pages, succès et quatre appels concurrents. Chaque callback
natif exige la possession du verrou ; toute ressource effectivement obtenue doit
être fermée. Après chaque erreur, un **autre thread** doit pouvoir reprendre :
une réentrée du même thread dans un RLock n'aurait pas détecté un verrou oublié.
L'ordre bitmap → page → document est contrôlé.

**Trois essais de PDFium réel**, chacun dans un processus enfant avec timeout,
quatre threads et cinq chargements par thread, à 72/100/144 DPI : **60 chargements,
90 pages** au total. Mélange natif, scan et multipage ; texte natif vérifié et
pixels RGB accessibles après fermeture. La reconnaissance du scan n'est pas
prétendue : ce test qualifie le chargement/rendu, pas l'OCR.

**Un test HTTP réel** dépose quatre PDF natifs simultanément, dans le serveur
isolé du lot 63. Quatre identifiants distincts, état `done`, une tentative par job,
SHA-256 du document correspondant, nombre de pages et textes natifs, puis health
encore joignable. Deux documents de préparation restent séquentiels dans la
fixture UI ; les quatre dépôts du nouveau test partent d'une barrière commune.
Le nombre de jobs effectivement exécutés en parallèle reste borné par le sémaphore
et la mémoire : quatre requêtes simultanées ne signifient pas quatre rendus natifs
simultanés — leur sérialisation est précisément la correction.

```sh
.venv/bin/python -m pytest tests/test_pdf_ingest_lifecycle.py \
  tests/test_pdf_ingest_concurrency.py tests/test_pdf_upload_concurrency.py -q
```

Pas besoin de Tesseract/Indra pour cette sélection : PDF natifs lus tels quels,
scans seulement rendus. Documents synthétiques sous répertoires temporaires,
magasin de l'aperçu non utilisé. Les 16 nouveaux tests et les huit tests d’ingestion existants sont ajoutés en
étape CI, distincte des huit tests UI et de la sélection documentaire historique.
Le double du test historique de limite de pages a été adapté au gestionnaire
de contexte réel : refus avant extraction/rendu conservé, assertion de fermeture
ajoutée. Une première complète avait signalé cette incompatibilité du double.

## Coûts et limites

L'ingestion PDF est désormais sérialisée à l'intérieur d'un processus, avec coût
de débit possible ; pas garantie FIFO, de latence ou d'équité du RLock. Un parseur
bloqué peut retenir ce verrou : pas nouveau timeout natif ni sandbox OS ajouté
au chemin d'ingestion principal. Les timeouts des essais protègent **les tests**,
pas le serveur de production. Le verrou ne constitue pas une réparation interne
de PDFium, une preuve d'absence de tous ses défauts mémoire, ou un certificat de
traitement de fichiers hostiles. Les autres limites de volume/mémoire restent
celles de l'application. Pas benchmark national ni garantie « zéro crash ».

Les règles métier, API, cache suspendu, codecs/modèles OCR et documents suivis
ne sont pas modifiés. Aucun corpus officiel acquis ou validé par cette correction.
