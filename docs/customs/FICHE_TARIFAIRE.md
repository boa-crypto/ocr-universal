# Fiche tarifaire documentaire — lot 10

2026-11-06. **Lecture seule d’un lot en quarantaine, non validé/non publié.**

## Contrat et séparation des inconnus

`customs_reference.tariff_detail.consulter_code` contrôle/rejoue le lot tarifaire
complet, puis cherche le code **exact** : chaîne de dix chiffres ASCII. Aucun
zfill, trim, conversion numérique ou de chiffres arabes/pleine chasse. Les zéros
initiaux sont préservés. L’entrée d’un champ texte HTML suit la normalisation
habituelle du navigateur ; le service et l’API vérifient strictement la chaîne reçue.

La fiche fournit :

- `ligne_declaree` : champs de la ligne archivée, désignations FR/AR reçues, unités,
  dates déclarées et localisateur, sans traduction ni correction ;
- `hierarchie_declaree` : section, chapitre, position et SH6 réellement déclarés et
  contrôlés, avec leurs propres références ;
- `subdivision_nationale_intermediaire` : parent intermédiaire explicitement
  déclaré ou null ; depuis le lot 23, `subdivisions_nationales` restitue la chaîne
  sourcée reçue. Aucun préfixe à huit chiffres n’est créé automatiquement ;
- `source_declaree` : document, URL déclarée, version, SHA256 et date source ;
- `mesures_declarees` : mesures explicitement liées au code dans ce même lot,
  avec références, taux/unité éventuels, descriptions, dates et statut `a_verifier`.

Les taux de la ligne restent inconnus (`null`) ; ils ne sont pas remplis depuis
les mesures. Les mesures fiscales/réglementaires restent séparées, sans choix
d’applicabilité, addition, calcul, harmonisation de dates ou transfert vers les
modules transit/facturation. Ce lot mono-source ne rapproche pas une fiscalité
d’autres documents. Les valeurs décimales sont rendues comme chaînes exactes,
sans flottants ni arrondi. Un taux déclaré `"0"` n’est pas un `null`, mais n’est
pas davantage validé ou applicable par cette fiche.

**Aucune mesure ne signifie pas exonération. Un taux inconnu ne signifie pas zéro.**
Une ligne absente donne `ligne_trouvee=false`, `ligne_declaree=null`, hiérarchie
null et liste de mesures vide ; ce résultat ne prouve pas l’inexistence nationale
d’un code. Source et ancrage du lot restent présents pour délimiter la recherche.

## CLI, API et écran

```sh
PYTHONPATH=src python -m unocr.cli customs-tariff-show /chemin/lot-tarif \
  --code "$CODE10_EXACT" --measures-limit 20 --measures-offset 0
```

JSON en lecture seule : retour 0 pour une consultation réussie, même sans ligne ;
2 pour refus de paramètres/lot. Accès local au système de fichiers requis.

GET `/api/v1/customs-review/lots/{lot_id}/tariff/{code10}` :

- `measures_limit` entier 1–100, défaut 20 ;
- `measures_offset` entier 0–1000000, défaut 0 ;
- mesures triées par ID déclaré, `total_mesures_declarees` explicite et
  `decalage_mesures_suivant` null en fin ; la ligne et ses parents restent visibles
  même si la page de mesures est vide.

Les droits nominatifs, le registre serveur et l’épingle du lot sont ceux de
[l’API de revue](API_REVUE.md). Empreinte vérifiée avant traitement et comparée
à celle du lecteur ; audit `fiche_tarif` avec IDs de lots, sans code dans l’événement
métier ; JSON `no-store`. Un code absent du lot donne **200 avec absence explicite**,
un ID de lot inconnu 404, un code mal formé ou un lot Code juridique 422.
Les autres statuts de refus/incohérence restent inchangés. Aucun chemin ou URL
ne peut être choisi par l’appelant HTTP. Ce n’est pas la future API publique d’un
tarif national validé.

Dans **Administration → Revue douanière · quarantaine**, choisir un lot tarifaire,
saisir le code exact et « Consulter la fiche tarifaire ». Les contrôles sont
séparés du formulaire de recherche et désactivés pour un lot Code juridique.
Les résultats sont du JSON lisible rendu comme texte, pas du HTML documentaire.
La coque service worker passe à v42 ; aucune nouvelle persistance métier.
Les limites de confidentialité et de révocation de [l’écran](INTERFACE_REVUE.md)
restent applicables : les journaux HTTP/proxy peuvent contenir le code dans l’URL.

## Limites et qualification

Pas de tarif national acquis ou complet, d’authentification éditoriale, de preuve
d’exactitude des transcriptions, de taux applicable, de validation humaine,
de publication, de calcul ou de classification. Les limites de taille, de rejeu
et de concurrence des lecteurs existants s’appliquent, sans nouvelle garantie
globale mémoire/temps. Pas de qualification navigateur visuelle complète : JSDOM
et intégration HTTP/backend isolée, pas homologation juridique ou ergonomique.

[Tests, résultats et état du corpus](RAPPORT_LOT10.md).

[Contrat et compatibilité du lot 23](SUBDIVISIONS_NATIONALES.md).
