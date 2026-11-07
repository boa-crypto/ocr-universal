# Pistes tarifaires documentaires partielles — lot 58

## But et différence avec la recherche stricte

`customs-tariff-criteria` conserve sa conjonction : **tous les termes de tous les
critères doivent être retrouvés dans les libellés FR/AR d'une même ligne**. Aucun
basculement automatique n'est ajouté lorsque cette recherche ne retourne rien.

La nouvelle commande explicite `customs-tariff-candidates` admet, au contraire,
une ligne si **au moins une paire critère/terme** est retrouvée. Elle sert à
inspecter des pistes partielles, pas à retenir un classement douanier.

```sh
unocr customs-tariff-candidates /dossier/lot-tarif \
  --designation "équipement" --matiere "acier" --usage "contrôle" \
  --match-mode mots_entiers --limit 20 --offset 0
```

Python : `rechercher_pistes_tarifaires(Path(...), designation=..., matiere=...,
fonction=..., usage=..., caracteristiques=..., code_prefix=..., limite=20,
decalage=0, match_mode="sous_chaine")` dans `customs_reference.tariff_candidates`.
Les cinq critères sont des étiquettes de la requête, pas des attributs certifiés.

Au moins un critère textuel est requis ; le préfixe seul est refusé. `code_prefix`
est un filtre ASCII de 1–10 chiffres, pas une déduction d'un code à partir d'un
nom de produit. Un code fourni dans `designation` est recherché comme texte de
libellé, pas automatiquement dans le champ code10.

## Règle publique de tri

Pour chaque ligne ayant une correspondance, tri lexicographique par :

1. nombre de critères dont **tous** les termes sont retrouvés, décroissant ;
2. nombre de paires critère/terme retrouvées, décroissant ;
3. code10 textuel croissant pour départager les égalités.

Ce tri est documentaire, déterministe pour les mêmes données/paramètres ; **ce
n'est ni une probabilité, ni une confiance, ni un ordre de pertinence juridique**.
Un critère complet passe avant plusieurs termes partiels. Un même terme sous
plusieurs critères compte plusieurs paires : compteurs non indépendants. Un terme
présent dans FR et AR ne compte qu'une fois pour une même paire. Les répétitions
normalisées au sein d'un critère sont dédupliquées. Aucun score pondéré caché,
modèle, traduction, expansion de synonymes, RGI ou règle d'exclusion ajoutés.

Exemple NON OFFICIEL : pour équipement/acier/contrôle, une ligne « équipement de
contrôle » peut précéder « équipement mécanique » ; **aucune ne prouve la matière
acier**, ni une classification correcte. Le moteur ne transforme pas un terme
non retrouvé dans les libellés en attribut manquant ou en absence de droit.

## Restitution et provenance

Chaque piste conserve la ligne, son code10, sa référence source, les libellés
originaux, les correspondances par critère/terme, les critères complètement
retrouvés et les termes non retrouvés. `rang_documentaire` commence à 1 dans la
liste triée avant pagination, pas dans chaque page isolément.

`conjonction_documentaire_complete` ne vaut que pour la recherche littérale.
Même true n'est jamais une validation du produit ou d'un classement. Les positions
sont en points de code Unicode Python, première occurrence comme dans le moteur
existant ; **16 extraits maximum par ligne**, positions conservées pour toutes
les paires et indicateur de troncature. Aucune preuve de fidélité PDF ajoutée.

Le lot fourni est relu/haché/rejoué via `charger_lot` avant tout résultat ; archive
altérée ou incohérente refusée entièrement, pas de liste partielle présentée comme
fiable. Sources, langues, unités et dates restent déclarées non validées.
Mesures fiscales et textes juridiques ne participent pas à cette recherche ; null
ne signifie toujours pas zéro ou exonération.

## Bornes et limites

Critères : 256 caractères et 16 termes normalisés maximum chacun ; limites
existantes partagées avec la recherche AND. Pagination 1–100, offset 0–1 000 000 ;
booléens refusés comme entiers. Modes sous-chaîne (défaut) ou mots entiers normalisés,
pas analyse morphologique. Validation avant lecture du lot.

Le lot et la liste des candidats sont en mémoire et entièrement parcourus ; seuls
les extraits de la page sont matérialisés. Pas streaming, benchmark national ou
transaction filesystem. Empreinte/rejeu ne certifient pas l'origine officielle.

CLI : code **0** pour un rapport technique, y compris vide ; code **2** pour refus.
Il n'y a pas de code « candidat validé ». `publication_active`,
`classement_ia_effectue`, `classement_douanier_valide`,
`candidat_retenu_automatiquement`, `probabilite_classement_etablie`,
`attributs_techniques_certifies`, `taux_calcules` restent false.

Portée initiale du lot 58 : Python/CLI. **Complément lot 59** :
[API privée et rejeu typé](API_PISTES_TARIFAIRES.md) des rapports de pistes,
sans UI nouvelle, cache ou publication. La recherche stricte existante ne change
pas de contrat. Ces lots avancent l'exploration documentaire de la phase 4,
sans prétendre livrer l'IA métier.
