# Subdivisions nationales explicitement déclarées — lot 23

2026-11-06. **Modèle documentaire en quarantaine, aucune nomenclature nationale acquise.**

## Contrat facultatif

Le lot tarifaire accepte `subdivisions_nationales`, liste vide par défaut. Chaque
entrée contient `code`, `code_parent`, `designation` et `reference` (source et
localisateur). Le schéma est [SubdivisionNationale](schemas/SubdivisionNationale.schema.json),
également inclus dans [TariffBatch](schemas/TariffBatch.schema.json).

Un code intermédiaire est une chaîne de **7 à 9 chiffres ASCII** : cela borne les
longueurs possibles entre SH6 et code10, sans imposer un niveau à huit chiffres.
Le parent, plus court et préfixe du code, doit être un SH6 ou une autre subdivision
**explicitement déclaré**. On peut déclarer un saut de longueur : aucun niveau
manquant n’est fabriqué. La croissance stricte des longueurs exclut les cycles.
Doublons, source différente, libellé/localisateur blanc, parent absent et liens
incohérents sont refusés par le modèle central.

Une ligne code10 peut fournir `code_subdivision_nationale`, null par défaut.
Ce code doit désigner une subdivision reçue et être préfixe de la ligne. Même si
un préfixe semble correspondre à une subdivision présente, **aucun lien n’est choisi
automatiquement**. Les lignes non renseignées restent reliées à leur SH6 déclaré.
Null ne démontre ni inexistence d’un niveau national ni erreur du fichier.

## Import et restitution

- Pour JSON : champ facultatif de la ligne structurée ; subdivisions dans le lot
  du sidecar. Pour tabulaire : mapping explicite vers `code_subdivision_nationale`.
  Les lecteurs et la quarantaine existants sont réutilisés, sans migration.
- Fiche : `hierarchie_declaree.subdivisions_nationales` donne le chemin reçu du
  premier intermédiaire au parent immédiat. Le champ singulier existant
  `subdivision_nationale_intermediaire` donne ce parent ou null.
- Diff : ajout/suppression/modification des subdivisions, plus changements de
  provenance séparés ; changement du lien sur une ligne également visible.
- Couverture : nombre de subdivisions et de lignes sans lien déclaré. Aucun
  dénominateur national, pourcentage, code inventé ou conclusion réglementaire.
- API et affichage JSON réutilisent les services, habilitations, épingles et audit.
  Aucun nouveau bouton/niveau de navigation n’est ajouté : l’arbre actuel reste
  une **projection SH6→code10**, avec renvoi à la fiche pour les intermédiaires.

## Compatibilité et limites

Les nouveaux champs sont facultatifs dans le contrat technique version 1 actualisé.
Une archive ancienne sans ces champs reste lisible/rejouable **sans modification de
ses octets ni de ses empreintes**. Le logiciel utilise des valeurs absentes/null
ou listes vides en mémoire ; il ne réécrit pas le fichier pour les ajouter.
Les anciens lecteurs/schémas stricts peuvent refuser les nouveaux champs : mettre
à jour les lecteurs avant d’échanger un nouveau lot, jamais supprimer une source
ou réécrire une archive historique pour le rendre compatible.

Une subdivision déclarée, sa source et un préfixe cohérent ne prouvent pas son
existence officielle, son libellé exact ou son applicabilité. Aucune décision de
classement/fiscalité, authenticité, validation humaine ou publication n’est accordée.
Il faut le fichier national et ses justificatifs réels pour constituer ces données.

[Rapport et qualification](RAPPORT_LOT23.md).
