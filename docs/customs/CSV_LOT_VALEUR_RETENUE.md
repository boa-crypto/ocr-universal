# Valeur humaine retenue dans le CSV groupé — lot 92

Route : `GET /api/batches/export/csv?ids=...`.

## Contrat de colonnes

Les six colonnes précédentes restent dans le même ordre : `document`, `champ`,
`valeur_brute`, `valeur_normalisee`, `confiance`, `statut`. Deux colonnes sont
**ajoutées à la fin** : `valeur_retenue`, `origine_valeur`. Les consommateurs
imposant exactement six colonnes doivent être adaptés ; pas compatibilité
binaire/structurelle totale revendiquée.

La valeur retenue reprend `_etat_champ` : première valeur non None dans
confirmed/corrected/normalized/raw. Une confirmation/correction vide `""` ne
retombe pas sur une ancienne valeur ; zéro/False legacy ne sont pas absents.
Toutes null donne cellule vide. Les colonnes brute/normalisée gardent leurs
valeurs, sans écrasement silencieux par la validation humaine.

`origine_valeur` reprend `value_origin` stocké, **pas une origine recalculée ou
certifiée**. Un legacy incohérent peut donc encore avoir origine/statut divergents
de sa valeur ; aucune migration ou machine à états introduite.

Les huit colonnes de données passent désormais par `sanitize_for_csv` : les
quatre déjà protégées restent inchangées, protection étendue à confiance/statut
et aux deux nouvelles. Le helper préfixe une apostrophe si la chaîne commence
par `=`, `+`, `-`, `@`, tabulation ou retour chariot. Conversion None en cellule
vide et autres objets en texte, conformément au helper existant.
**Pas garantie universelle contre toutes heuristiques/formules des tableurs** :
pas normalisation des espaces/préfixes Unicode ou qualification Excel/LibreOffice.
Les nombres négatifs sont également préfixés selon cette politique existante.

## Recette

41 nouveaux cas : quatre priorités non None, quatre valeurs vides, quatre zéros/
False legacy, toutes valeurs null, aucun champ, 12 confiance/statut avec six
préfixes, six valeurs retenues avec ces préfixes, une origine neutralisée,
trois gardes d'accès, un contrat des six anciennes colonnes plus deux,
un ordre/doublons de documents, trois chaînes HTTP confirmation/correction/undo.
CSV réel relu avec DictReader et UTF-8 BOM, stores/jobs/audits temporaires,
empreintes conservées hors modifications intentionnelles. Cas legacy malformés
pour démontrer le neutraliseur, pas statut/confiance invalides acceptés via PATCH.
Pas fournisseur OCR, navigateur ou test d'un tableur réel.

Contre-épreuve : seul ancien export_batch réinjecté en mémoire ; schéma/fixtures
et autres handlers conservés, checkout/aperçu non remplacés.
[Rapport](RAPPORT_LOT92.md), [recette](RECETTE_LOT92.json).

## Limites

**Contenu CSV seulement**. Fichier groupé toujours horodaté/partagé, risque de
collision entre requêtes non corrigé ici. Pas no-store/streaming ou borne de
mémoire nouvelle. JSON groupé isolé au lot91 ; autres formats/archives/sélections
inchangés. Ordre/doublons/limite200 et lectures par document non atomiques conservés.
Valeur retenue, pas preuve humaine ou validation qualité/fiscale ; export non
réécrit dans les résultats. Pas validation universelle de la structure legacy,
confidentialité/redaction, type numérique ou origine/statut.

Droits, audit best-effort, détail des erreurs, révision processus/ABA et autres
écrivains inchangés. Aperçu backend76 maintenu : code77–92 poussé/testé mais
non chargé avant redémarrage maîtrisé pour préserver les traitements.
RBAC non activé implicitement ; mission réglementaire toujours partielle.
