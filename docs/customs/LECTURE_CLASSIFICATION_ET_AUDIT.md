# Classification stockée et journal : ne pas confondre les décisions — lot 78

7 novembre 2026. Périmètre : `GET /api/jobs/{job_id}/classification`.

## Défaut corrigé

Le GET combinait le `manual` stocké avec celui de la dernière ligne du journal
retenue pour le job. Un événement manuel d'une autre catégorie ou décision
pouvait ainsi marquer la décision automatique stockée comme manuelle. Son
horodatage était également joint sans vérifier la concordance. Une simple
mention textuelle de `document_classified` dans un autre événement pouvait être
retenue ; certaines valeurs JSON non objets provoquaient une erreur `.get`.

Désormais, après le préfiltre littéral préexistant, seules les entrées JSON
objets dont `event` vaut exactement `document_classified` et `job_id` correspond
sont retenues. Lignes JSON illisibles et valeurs non objets sont ignorées.
La dernière entrée de ce type pour le job reste la seule candidate.

Si une classification est stockée, ses champs, notamment `manual`, restent
**la référence de lecture**. Le journal ne réécrit pas cet indicateur. `ts` est
joint seulement si catégorie, confiance, version du classifieur, besoin de revue
et indicateur manuel concordent avec les valeurs stockées. En cas de conflit,
on ne reprend pas l'horodatage d'un événement plus ancien correspondant.
Libellé, preuves, alternatives et autres champs stockés sont conservés.

Sans classification stockée, le repli historique sur les cinq champs de la
dernière entrée explicite reste disponible, avec son horodatage. Ce repli
n'est pas une reconstitution de preuve documentaire complète ou une migration
des anciennes corrections seulement journalisées.

## Mesure

22 nouveaux cas : cinq divergences de champs de décision, un événement concordant,
deux sens de conflit de `manual`, six bruits JSON/non-événements, JSON cassé,
autre job, événement conflictuel récent après un ancien concordant, deux absences
de trace, un repli historique et deux refus avant lecture du résultat.
Stores/jobs/audits réels temporaires, empreinte du résultat sur divergence,
aucun OCR fournisseur ou navigateur réel exécuté par ces nouveaux cas.

Témoin : corps exact de l'ancien GET réinjecté uniquement en mémoire dans un
processus de test, mêmes 22 cas, sans remplacer le checkout ou l'aperçu.
Résultats dans [le rapport](RAPPORT_LOT78.md), [recette](RECETTE_LOT78.json).

## Limites importantes

La concordance est une égalité déclarative sur cinq champs, **pas une identité
de révision**, un hash de contenu, une signature ou une vérification des preuves.
Deux décisions distinctes ayant ces cinq valeurs identiques restent
indistinguables. Pas validation stricte des types/horodatages du journal,
calibration ou attestation de présence humaine. Le préfiltre littéral ne devient
pas un importeur universel de tous les encodages JSON possibles.

Pas journal borné/streamé, refonte du repli historique, archivage complet,
transaction/concurrence ou résolution des anciennes données contradictoires.
L'audit reste legacy best-effort ; pas signé/WORM. Un résultat stocké malformé
n'est pas globalement réparé par ce correctif. `corrected_by` déclaratif de la
classification manuelle et score manuel historique inchangés. Gardes et politiques
de visibilité existantes conservées ; aucune activation automatique du RBAC.

Aperçu maintenu avec le backend 76 pour préserver les traitements : code 77/78
poussé et testé, mais non chargé dans ce processus avant redémarrage maîtrisé.
