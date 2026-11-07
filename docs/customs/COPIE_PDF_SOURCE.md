# Téléchargement contrôlé du PDF source reçu — lot 35

La revue peut remettre les octets d'un PDF **déjà archivé dans un lot Code inscrit**,
pour permettre sa consultation dans un lecteur externe sécurisé. Ce n'est pas une
acquisition de document officiel ni une authentification de son contenu.

## API et service

```text
GET /api/v1/customs-review/lots/{lot_id}/pdf-source?document_id=ID_EXACT
copier_pdf_source(repertoire, document_id) -> (rapport_interne, octets)
```

ID exact non blanc, maximum 256 points de code, sans contrôle ni substitut Unicode
isolé. Le service le vérifie avant toute lecture. Lot tarifaire : 422 ; source
absente : 409 ; lot inconnu : 404. Pas de chemin de fichier HTTP ni d'URL distante
suivie. La sélection reprend l'ordre documentaire et les noms d'archive contrôlés.

Même administrateur nominatif/habilitation de revue, registre/manifeste épinglés,
rejeu du lot entier. Les octets sont relus et leur SHA256 comparé au document et
au manifeste contrôlé. Le constructeur de réponse vérifie encore taille/empreinte
contre le rapport, ainsi que le manifeste de résultat par le pipeline existant.
Réponse construite **avant** audit obligatoire `copie_pdf_source`, puis libérée
seulement après succès de l'audit. Échec audit : 503 JSON sans PDF. Cela n'atteste
pas la réception réseau ni une transaction entre réseau et journal local.

Réponse de succès : `application/pdf`, pièce jointe `Content-Disposition: attachment`,
nom ASCII `uniocr-source-non-validee-SHA256.pdf` sans identifiant/titre utilisateur,
`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, CSP sandbox/default-src
none ; en-têtes `X-UniOCR-Source-SHA256`, `X-UniOCR-Manifest-SHA256` et
`X-UniOCR-Validation: non_validee`. Aucun fichier temporaire ou réécriture de lot.

Cette route binaire n'est **pas** un rapport JSON exportable ; elle n'est pas
ajoutée à la whitelist de l'enveloppe d'export. Pour conserver les métadonnées et
le contexte, exporter séparément l'inventaire des sources du même lot.

## Interface intégrée

Dans l'inventaire des sources d'un lot Code, une source PDF cohérente propose le
bouton « Télécharger le PDF reçu … — non validé ». Avertissement d'absence de
validation/antivirus avant action. Requête authentifiée par le jeton courant,
jamais jeton dans une URL ou lien direct externe ; pas d'iframe ou rendu PDF.

Vérification du type MIME, des empreintes de source et du manifeste contre la
sélection, du marqueur non validé et de la taille annoncée (1–64 Mio). Après
réception, taille réelle et SHA256 Web Crypto doivent correspondre avant création
d'un Blob/lien à nom fixe. Sans Web Crypto disponible : refus avant requête.
Le navigateur doit fournir un contexte sécurisé supportant cette API (HTTPS de
prévisualisation, par exemple). Changement de lot, compte, résultat ou navigation
pendant le transfert : aucun lien de téléchargement créé par ce résultat obsolète.
L'URL Blob est révoquée après la demande, pas conservée dans le stockage applicatif.

## Risques et limites impératives

- **Pas d'antivirus, de désarmement du contenu actif ou de qualification complète
  du format PDF.** Un fichier reçu peut être malformé ou dangereux malgré un SHA256
  cohérent. L'application ne l'ouvre pas et ne doit pas le considérer sûr. Employer
  un lecteur externe à jour, isolé et configuré pour des documents non fiables.
- Les headers sandbox/nosniff/attachment ne sécurisent pas tous les lecteurs externes.
- Une signature `%PDF` et le rejeu existant ne prouvent ni authenticité, validité
  juridique, fidélité des transcriptions, traduction, droit à date ou complétude.
- Limite de lecture existante 64 Mio par fichier. Chargement/rejeu entier en mémoire,
  puis réponse complète/ArrayBuffer/Blob : pas streaming, Range, mémoire constante,
  quota global ou benchmark de charge nationale. Le contrôle de taille navigateur
  après réception ne constitue pas une borne mémoire face à un serveur défaillant.
- Les fichiers seront persistés par le navigateur si l'utilisateur les enregistre ;
  `no-store` n'efface pas ses téléchargements et la révocation d'une URL Blob n'est
  pas un effacement sécurisé des octets en mémoire.
- Tests sur fixtures NON OFFICIELLES ; JSDOM/API réelle ne remplacent pas une recette
  visuelle/téléchargement Chrome/Firefox, contrôle humain ou analyse de sécurité PDF.
