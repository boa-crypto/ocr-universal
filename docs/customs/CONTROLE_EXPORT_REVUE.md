# Contrôle hors ligne d’un export de revue — lot 17

2026-11-06. **Contrôle technique, pas authentification ou validation juridique.**

## Utilisation sans import

```sh
PYTHONPATH=src python -m unocr.cli customs-review-export-check /chemin/uniocr-revue-non-validee.json
```

Sortie JSON ; code **0 = structure compatible**, **2 = refus**.
La commande n’initialise pas les magasins de données/journaux, ne contacte aucune
API et n’écrit ni le fichier fourni ni une archive/référence/configuration. Elle ne
relance pas la lecture protégée du lot 16 et ne peut pas vérifier une révocation.
Le chemin est local et explicite ; aucun fichier exporté réel n’est requis pour
les tests, qui utilisent uniquement des fixtures NON OFFICIELLES.

Le constat ne reproduit pas le texte documentaire, la requête ou les identifiants
métier. Il contient la taille, le SHA256 des **octets reçus**, les empreintes de
manifestes **déclarées**, les limites de confiance et les marqueurs non validés.
Un JSON refusé produit un message générique, pas l’erreur Pydantic détaillée
susceptible de contenir des valeurs documentaires ou des chemins internes.

## Contrat version 1

[Schéma JSON versionné](schemas/ExportRevue.schema.json), généré à partir du modèle
Pydantic strict et rapproché automatiquement par test. Il couvre :

- les neuf champs obligatoires d’enveloppe du lot 16, sans champs supplémentaires ;
- version/type/portée exacts, lecture seule vraie, publication fausse, validation
  juridique `non_validee`, sans substitution booléen/entier ;
- horodatage au format millisecondes UTC généré par le navigateur ;
- chemin relatif d’une des lectures connues, sans hôte externe ou fragment ;
- provenance simple `archive.manifest_sha256`, ou deux provenances
  `archives.avant/apres` pour les comparaisons, empreintes hexadécimales minuscules.

Le CLI applique aussi les règles sémantiques non entièrement exprimées par le
schéma : calendrier réel, cohérence route simple/diff, rejet des marqueurs
contradictoires à la racine du rapport et des provenances ambiguës. La liste
`archives` des PDF déclarés d’un contrôle Code est distinguée de la paire de
comparaison. Les paramètres HTTP ne sont pas réinterprétés ni rejoués.

Les autres champs métier du résultat restent des valeurs JSON opaques : leur
validité, exactitude, état juridique et cohérence interne ne sont **pas** attestés.
Le schéma n’est ni un schéma national de publication ni un schéma de consolidation.

## Lecture et limites de sûreté

- UTF-8 strict sans BOM ; doublons de clés refusés à toute profondeur.
- JSON fini : NaN/Infinity et nombres flottants hors plage finie refusés ; JSON
  tronqué, valeurs racines incompatibles et substituts Unicode isolés refusés.
- Fichier non vide ≤10 Mio, profondeur ≤64 ; lecture bornée, fichier régulier,
  symlink final refusé. `O_NOFOLLOW`/`O_NONBLOCK` utilisés lorsque disponibles.
- Pas de parcours réseau, décompression, suivi d’URL source, réparation, OCR,
  signature, chiffrement ou écriture du contenu.

Les limites ne garantissent pas une consommation RAM constante. Les ancêtres du
chemin ne sont pas cloisonnés ; ce n’est pas un bac à sable contre un administrateur
OS hostile ni une lecture transactionnelle face aux écritures concurrentes.
Le SHA256 identifie uniquement les octets effectivement lus, pas leur authenticité.

Un fichier modifié puis doté de marqueurs/provenances syntaxiquement valides peut
passer ce contrôle. Il faut une lecture serveur autorisée, l’accès aux archives et
une procédure juridique habilitée pour aller au-delà. Le résultat indique toujours
`authenticite_verifiee=false`, `integrite_archives_verifiee=false`,
`audit_serveur_verifie=false`, `publication_active=false` et `non_validee`.
Aucun usage de calcul réglementaire réel n’est autorisé par un code retour 0.

[Qualification et rapport](RAPPORT_LOT17.md).
