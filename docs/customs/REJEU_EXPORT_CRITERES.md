# Rejeu local d'un export de critères — lot 50

Le contrôleur `customs-review-export-check` reste un contrôle de **structure**.
La nouvelle commande compare en plus le résultat complet d'une recherche tarifaire
multicritère à un rejeu de l'archive fournie explicitement. Aucun contrôle de
signature, d'origine officielle, du registre serveur ou d'habilitation humaine.

```sh
unocr customs-review-export-replay rapport.json --lot CHEMIN_ARCHIVE --lot-id IDENTITE_LOCALE
```

Service Python : `verifier_rejeu_criteres(chemin_export, repertoire, lot_id)`.
Aucune route HTTP de lecture de chemin local ajoutée. Aucun import ou stockage.

## Périmètre strict

Seuls les exports dont la requête est
`/api/v1/customs-review/lots/IDENTITE_LOCALE/tariff-criteria?...` sont rejoués.
Les autres routes, même acceptées structurellement, sont refusées : pas de
rejeu partiel présenté comme général. L'identité est fournie par l'opérateur ;
**elle n'est ni découverte sur disque ni attestée contre le registre serveur**.

Paramètres admis : les cinq critères, `code_prefix`, `match_mode`, `limit`, `offset`.
Inconnus, doublons (y compris après décodage), encodage invalide, paramètres mal
formés et pagination non décimale ASCII sont refusés. Neuf paramètres au maximum.
Les limites et valeurs métier du service restent appliquées avant lecture du lot.
Les formes numériques tolérées par certains parseurs HTTP (`+1`, espaces, etc.)
ne sont pas acceptées par ce contrôleur strict ; les exports générés par l'UI
utilisent les formes décimales canoniques prises en charge.

Le chemin d'archive est **uniquement celui de l'argument explicite**, jamais
celui d'une URL, d'un paramètre de requête ou d'un champ du rapport. Aucune URL
suivie, requête réseau, sélection automatique d'archive ou recherche récursive.

## Lecture et comparaison

1. Lecture bornée de l'export, 10 Mio maximum, fichier régulier ; symlink final,
   FIFO, doublons JSON, nombres non finis, Unicode/profondeur/contrat invalides
   refusés par les gardes existants. Pas de refus général de tous les symlinks
   des répertoires parents ni de bac à sable OS.
2. Un seul contenu d'export lu, analysé puis reparsé en mémoire sans rouvrir le
   chemin. Validation de route/paramètres avant appel du moteur de recherche.
3. Rejeu complet existant du lot (empreintes, lecteurs et provenance) puis de la
   recherche avec les paramètres exportés. Archive incohérente ou paramètres
   invalides : refus, pas un rapport « différent » faussement exploitable.
4. Comparaison du **résultat entier**, sans ignorer diagnostic, positions, flags,
   source, filtres ou champs ajoutés/supprimés. Clés d'objets triées et espaces JSON
   ignorés ; ordre des listes conservé. Types JSON distingués : false ≠ 0,
   1 ≠ 1.0. Pas comparaison octet à octet des fichiers ou de lexèmes numériques.

L'enveloppe doit satisfaire le contrat structurel, mais son horodatage client
n'est ni rejoué ni certifié. Les nouveaux champs d'une autre version logicielle
peuvent faire différer le rapport : **différence ne signifie pas fraude**.
Aucun mode permissif ne retire des champs pour obtenir artificiellement une égalité.

## Résultat et codes CLI

- **0** : `rejeu_identique`, résultat identique selon la comparaison ci-dessus.
- **1** : `rejeu_different`, archive fournie cohérente mais résultat différent.
- **2** : `refuse`, export, route, paramètres ou archive incompatibles/illisibles.

Le constat restitue les empreintes de l'export, du manifeste local et des deux
résultats canoniques, `manifest_export_correspond`, `rapport_identique` et
`archive_fournie_coherente_au_rejeu`. Il ne recopie ni requête, ni texte de rapport,
ni détail des différences. Erreurs de rejeu d'archive neutralisées dans le constat.
Les empreintes ne sont pas un chiffrement ou une signature.

`authenticite_verifiee`, `identite_registre_verifiee`, `audit_serveur_verifie` restent
false ; lecture seule, publication false, validation juridique non validée. Une
copie d'archive ou un rapport entièrement recomposé et cohérent peut satisfaire ce
contrôle : il prouve la reproductibilité technique locale, **pas l'origine**.

Aucune écriture, publication, transaction multi-fichiers, protection WORM ou
garantie contre modification concurrente après lecture. Même limites de mémoire,
rejeu intégral et corpus non exhaustif que le moteur existant.
