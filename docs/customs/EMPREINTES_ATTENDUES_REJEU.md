# Rejeu contre empreintes attendues — lot 55

Références facultatives **fournies séparément par l'opérateur**, pas récupérées
comme valeurs attendues depuis l'export ou son manifeste. La confiance dans leur
provenance reste à établir hors de ce contrôleur : ce n'est ni signature ni WORM.

## Options

Rejeu simple :
`--expected-export-sha256 SHA` et `--expected-manifest-sha256 SHA`.

Rejeu à deux archives :
`--expected-export-sha256 SHA`, `--expected-before-manifest-sha256 SHA`,
`--expected-after-manifest-sha256 SHA`.

Python : `sha256_export_attendu`, `manifest_sha256_attendu` pour les fonctions
simples ; `sha256_export_attendu`, `manifest_avant_attendu`, `manifest_apres_attendu`
pour la paire. Arguments nommés facultatifs ; anciens appels sans références
conservés. Aucune référence fournie ne signifie pas qu'une vérification externe
ou une authentification aurait été effectuée.

## Ordre de contrôle

- Format validé avant lecture de l'export : chaîne de 64 caractères hexadécimaux
  minuscules, sans espaces ; None signifie non fourni, pas chaîne vide ou booléen.
- Empreinte d'export calculée sur ses **octets exacts**, avant analyse JSON : une
  différence refuse le contrôle, même si les deux JSON donnent le même résultat.
  Changement de date client, espaces ou ordre des clés peut changer cette empreinte.
  La comparaison sémantique/canonique du rapport reste distincte et inchangée.
- Après validation de structure/route/paramètres de requête, le manifeste du
  dossier explicitement fourni est lu/haché avant le service de rejeu, donc avant
  toute extraction PDF. Aucun nom ou URL de l'export ne choisit son chemin.
- Pour la paire, les deux préconditions de manifeste sont vérifiées avant de
  lancer la comparaison. Les rôles avant/après sont distincts et ordonnés.
- Les empreintes du ou des manifestes restitués par le service sont revérifiées
  contre les références après le rejeu. Pas de succès si le résultat renvoie un
  autre manifeste que celui attendu.

La lecture préliminaire d'un manifeste épinglé peut précéder la validation métier
complète des paramètres par le service. Elle ne remplace pas son rejeu d'archive.
Elle refuse dossier final symbolique, symlink final du manifeste, fichier non
régulier/FIFO, absence ou dépassement de 10 Mio, avec le lecteur borné existant.
Pas de refus général de tous les symlinks parents ni bac à sable OS revendiqué.

Toute précondition d'empreinte non satisfaite donne **refus / code CLI 2**, pas
« différent » / code 1 exploitable. Si les préconditions passent, le rejeu complet
produit toujours code 0 identique ou code 1 différent suivant le rapport.

## Restitution et limites

`empreintes_attendues` indique `export_epingle`, `manifestes_epingles` par rôle
(unique ou avant/après), `nombre_empreintes_verifiees`, et
`authenticite_des_references_verifiee:false`. Sans référence, le nombre vaut zéro.
Il n'est pas présenté comme « toutes références authentifiées » par vacuité.

Un fichier cohérent modifié peut satisfaire un rejeu sans épingle mais échouer à
une référence externe conservée. Si l'opérateur calcule au contraire ses références
sur les fichiers déjà altérés, ce contrôle ne peut pas découvrir cette altération
historique. Un manifeste identique dans une copie ne prouve pas son identité de
registre ou son origine. Aucun secret/chiffrement/signature fourni par SHA256.

Aucune transaction, verrou, WORM, signature, heure certifiée ou garantie contre
mutation concurrente après les lectures. L'identité du registre, l'audit serveur,
l'authenticité des références, la validation humaine et le droit applicable
restent non attestés. Aucun nouveau endpoint, contrôle UI ou cache ajouté.
