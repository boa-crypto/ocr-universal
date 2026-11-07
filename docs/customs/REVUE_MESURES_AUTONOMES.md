# Revue administrative des mesures autonomes — lot 37

Les préparations JSON du lot 36 rejoignent la **même revue centrale** que les lots
Code et tarif, sans être déclarées comme une nomenclature. Aucun import administratif,
rapprochement fiscal, validation juridique ou calcul activé par cette consultation.

## Inscription explicite au registre

Le schéma `RegistreRevue` accepte maintenant `type_lot: "mesures"` en plus de `code`
et `tarif`. Même dossier simple autorisé, ID de revue distinct et empreinte exacte
du manifeste. Aucun dossier n'est découvert ou inscrit automatiquement. Le fichier
reste une configuration locale gérée par un opérateur habilité ; ne pas écraser
un registre existant sans sauvegarde. Un ancien serveur/contrôleur à enum strict
refusera ce nouveau type : déployer le code et le schéma ensemble.

Le type de registre `mesures` désigne un manifeste
`type_lot=mesures_autonomes_documentaires`, produit par `customs-fiscal-prepare`.
Déclarer un lot tarif/Code comme mesures ou l'inverse ne contourne pas le rejeu.

## Quatre consultations autorisées

Routes sous `/api/v1/customs-review/lots/{lot_id}` :

- `/check` : empreintes et rejeu source/sidecar/lot/rapport, sans écriture ;
- `/measure-search?q=…&code10=…&measure_type=…&limit=20&offset=0` : descriptions
  normalisées FR/AR, filtre code10/type exacts ; requête ou filtre requis ;
- `/sources?q=…&source_id=…&limit=20&offset=0` : source déclarée et compteur de
  mesures, sans nature de document Code inventée ;
- `/coverage` : compteurs du lot, types et champs non renseignés, aucun pourcentage
  national ou score d'aptitude à publier.

Même administrateur nominatif/habilitation de revue, registre et manifeste épinglés,
rejeu central, empreinte de résultat contrôlée, audit obligatoire et `no-store`.
Refus intégrité 409 ; paramètres/type incompatibles 422 ; panne audit 503 sans
résultat. Aucune route d'écriture ou de publication ajoutée.

Recherche : `type_recherche=mesures_autonomes_documentaires`, `type_lot=mesures`,
source propre et taux exacts en chaînes, `ligne_declaree=null` pour chaque mesure,
`existence_codes_dans_nomenclature=non_verifiee` et
`rattachement_nomenclature=non_effectue`. Aucun accès à un tarif en arrière-plan.
Ordre/pagination/filtres de la recherche existante conservés. Source et couverture
n'annoncent pas de lignes/hiérarchies absentes du contrat autonome.

## Interface, CLI et export

Sélection « mesures » dans le même écran, contrôle, formulaire de recherche de
mesures, inventaire et couverture réutilisés. Recherche de désignations et outils
Code/nomenclature désactivés. Pas de bouton de fiche à partir d'un code autonome,
même s'il ressemble à un code présent ailleurs. Pas de téléchargement PDF : la
source de ce contrat est JSON. Retour vers Code/tarif restaure les outils adaptés.

CLI de consultation :

```text
customs-fiscal-search DOSSIER [--query TEXTE] [--code CODE10] [--type tva] [--limit 20] [--offset 0]
customs-sources DOSSIER --type mesures
customs-coverage DOSSIER --type mesures
```

Les rapports passent par l'export relu/audité existant, enveloppe 1 à provenance
simple, vérificateur hors ligne inchangé. L'export reste partiel, pas corpus complet,
source originale ou preuve d'authenticité.

## Refus explicites et limites

Le pipeline ferme par défaut toutes les autres opérations sur `mesures`, y compris
recherche de désignations/articles, historique, fiches et arbres, relations/PDF,
comparaisons simples ou doubles et copie PDF. Ces refus sont testés avant appel
d'un chargeur incompatible. Une future opération devra être explicitement autorisée.

Dates, sources, descriptions et codes restent déclarés. Aucune identité de mesure,
existence nationale de code, exemption, traduction, relation juridique, règle
applicable ou calcul n'est inféré. Import JSON strict seulement ; qualification
sur sources officielles, CSV/XLSX/PDF autonomes, rapprochement avec le tarif,
validation humaine et publication restent ouverts. Le lot entier est chargé/rejoué
avant pagination ; pas de garantie mémoire constante ou charge nationale.
