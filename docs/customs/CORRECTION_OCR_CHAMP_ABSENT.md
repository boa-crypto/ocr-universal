# Correction OCR : un champ absent n'est pas une correction — lot 74

7 novembre 2026. Complète le [cloisonnement du lot 73](CLOISONNEMENT_OCR_DOSSIERS.md).

## Défaut et décision

`OCRTransitIntegration.correct_field` retournait `True` dès que l'extraction
existait, même sans champ correspondant. Il changeait `modifie_le`, réécrivait
le JSON et écrivait `ocr_champ_corrige`. La route `/corriger` renvoyait donc 200
avec un audit de correction alors qu'aucune valeur n'avait été corrigée.

Désormais, la fin de recherche sans correspondance retourne `False` avant toute
mutation, persistance ou audit de succès. La branche de refus déjà présente dans
la route renvoie **404**, `Document OCR ou champ introuvable`. Une extraction
absente conserve le même refus. Les gardes de rôle, dossier et appartenance du
lot 73 restent en amont : ce changement ne permet pas de sonder un dossier caché.

## Contrat conservé

Le nom est comparé **exactement**, sans changement de casse, suppression d'espaces,
traduction ou normalisation Unicode. Deux noms visuellement proches ne deviennent
pas identiques. La première occurrence d'un nom existant reste celle corrigée ;
le traitement des doublons n'est pas refondu.

Une correction réellement applicable conserve son comportement : valeur corrigée
et confirmée, origine et statut du champ `corrected`, nouvel horodatage de
l'extraction, persistance et audit de succès. Valeurs vides, chaîne `0`, accents,
arabe et sauts de ligne ne sont pas réinterprétés. Valeur OCR originale,
confiance, anomalies et autres champs sont conservés. Pas de recalcul de qualité,
de changement du statut global d'extraction ou de preuve de validation humaine.

En cas de champ absent : contenu de l'extraction, horodatage et fichier inchangés,
pas de `ocr_champ_corrige`. Une lecture froide peut remplir le cache avec la
fiche existante ; elle ne doit pas modifier cette fiche.

## Recette

38 nouveaux cas : 14 recherches infructueuses avec écritures/audit piégés,
2 extractions absentes, 12 corrections réelles service, 6 refus API dans les
états extracted/validated/corrected et 4 corrections réelles API. Stores JSON
et cache réels temporaires, relecture par un store neuf, empreintes de tous les
JSON temporaires et contrôle des audits. Rôles API synthétiques explicites,
aucun fournisseur OCR exécuté ni source officielle ajoutée.

Contre-épreuve : corps exact de l'ancienne méthode réinjecté en mémoire dans le
processus de test, sans remplacer le checkout ou le serveur d'aperçu. Les mêmes
38 cas doivent distinguer les refus manquants des opérations autorisées.
Voir les résultats mesurés dans [le rapport](RAPPORT_LOT74.md).

## Limites

Pas transaction stockage/audit, concurrence, historique/annulation des corrections
de ces extractions, résolution des doublons ou invalidation de validation globale.
L'audit de succès existant reste best-effort ; pas journal WORM/signé ou nouveau
journal de refus dédié. Les identités historiques fournies au service ne deviennent
pas des attestations d'authentification. Les anciens faux événements ne sont ni
supprimés ni requalifiés. Les autres routes et modèles ne sont pas déclarés
couverts exhaustivement ; le mode sans RBAC configuré reste historique ouvert.
