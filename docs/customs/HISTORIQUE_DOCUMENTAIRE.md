# Historique documentaire d’un article — lot 9

2026-11-06. **Quarantaine uniquement. Pas de texte applicable ni de consolidation.**

## Ce qui est présenté

Le service commun `customs_reference.history.historique_article` contrôle/rejoue
un lot Code complet avant toute réponse. Il sélectionne les transcriptions dont
`numero_article` correspond **exactement** à la chaîne demandée : pas de trim,
renumérotation, traduction, conversion de chiffres ou rapprochement flou.
Un même numéro dans deux documents ne prouve pas que les dispositions se succèdent.

Les versions sélectionnées restent séparées : originales, modificatives et
consolidées provisoires. Pour chaque version/page : ID, nature, hiérarchie,
référence et localisateur, version déclarée, références JO, statut juridique
**déclaré**, dates **déclarées**, historique de références modificatives et aperçus
FR/AR/intégraux de 512 caractères maximum (indicateur de troncature). Aucun champ
n’est réécrit dans l’archive ; aucune version n’est désignée comme en vigueur.

Tri : date de publication **du document source**, croissante ; dates inconnues
en fin ; puis ID source et ID article pour départager. La date de publication de
l’article, ses dates d’effet/fin/abrogation restent distinctes dans la réponse et
ne remplacent jamais une date source inconnue. Un tri chronologique ne suffit pas
à construire une succession juridique.

## Relations, preuves déclarées et contexte

Sont retenues uniquement les relations explicitement transcrites dont au moins
une extrémité est une version portant le numéro exact demandé. Leur sens,
type, justification et localisateur de preuve sont conservés. Pas de lien inféré
par similarité ou identité de numéro ; pas de clôture transitive.

La sélection des relations porte sur **toutes** les versions sélectionnées,
indépendamment de leur page. Les relations sont triées par ID et paginées
séparément. Les extrémités des relations de cette page qui ne figurent pas dans
la page de versions sont décrites dans `articles_contexte_relations` : par exemple,
une disposition modificative dont le numéro diffère de l’article modifié.
Un article du même numéro peut également figurer en contexte s’il est hors page.
Ce contexte n’est pas une seconde liste de versions applicables.

`documents_declares_page` fournit les sources des versions/contexte/références
présentés. Les documents sans article transcrit sont signalés séparément. Les
preuves des relations sont **déclarées, non vérifiées contre les PDF** ; les
contrôles de cohérence existants ne constituent pas une validation juridique.

## CLI local

```sh
PYTHONPATH=src python -m unocr.cli customs-code-history /chemin/lot-code \
  --article "$ARTICLE_EXACT" --limit 20 --offset 0 \
  --relations-limit 20 --relations-offset 0
```

Lecture seule, JSON sur stdout. Code retour 0 si le lot est cohérent et les
paramètres valides, y compris zéro correspondance ; 2 en cas de refus. Le CLI
reste réservé à l’opérateur ayant accès au système de fichiers, pas à une
habilitation juridique nouvelle. Les erreurs locales peuvent donner du contexte
technique, contrairement aux erreurs HTTP volontairement génériques.

## API et interface intégrée

GET `/api/v1/customs-review/lots/{lot_id}/history` :

- `article` requis, chaîne exacte non blanche de 1–256 caractères, sans contrôle ;
- `limit` / `relations_limit` : entiers de 1 à 100, défaut 20 ;
- `offset` / `relations_offset` : entiers de 0 à 1000000, défaut 0.

`total_versions_meme_numero` / `total_relations_declarees` comptent les éléments
du lot sélectionné ; `decalage_suivant` / `decalage_relations_suivant` valent null
en fin de leurs listes respectives. Une page vide au-delà des totaux est normale.

Mêmes droits nominatifs et registre épinglé que les autres lectures de revue,
empreinte épinglée avant lecture puis comparée au manifeste effectivement utilisé,
audit opération `historique` avec
IDs de lots, sans numéro d’article dans l’événement métier. Réponse `no-store`,
non validée/non publiée. Un lot tarifaire donne 422, pas une conversion implicite.
Les statuts 401/403/404/409/422/503 et leurs limites restent ceux du guide API.
Aucune route publique de corpus réglementaire n’est créée par cette étape.

Dans Administration → Revue douanière · quarantaine : sélectionner un lot Code,
renseigner le champ Article puis **Afficher l’historique documentaire**. Les
limite/décalage communs contrôlent la page des versions ; des champs distincts
contrôlent les relations. Le texte recherché et les filtres source/nature sont
explicitement **ignorés** pour cette vue de toutes les versions du numéro.
Les contrôles d’historique sont désactivés pour le tarif. Rendu JSON texte et
protections de confidentialité du lot 8 conservés ; coque service worker v41.

## Limites impératives

- Un seul lot à la fois ; pas d’historique global inter-lots ou de catalogue officiel.
- Ni dépouillement exhaustif du JO, ni preuve de correspondance texte/PDF ou FR/AR.
- Aucune décision fondée sur un statut déclaré `applicable`, une date ou une relation.
- Pas de reconstitution des textes modifiés, de validation humaine, de publication,
  d’export ou de calcul. Les dates contradictoires ne sont pas harmonisées ici.
- Aucune correspondance ne signifie pas absence de droit ou d’article.
- Les bornes et coûts du rejeu existant s’appliquent : pas de benchmark national ni
  de nouvelle garantie globale mémoire/temps face aux gros champs déclarés.
- Pas de verrouillage transactionnel contre un écrivain hostile, ni de WORM.

Le corpus officiel, ses modifications et leurs preuves restent à acquérir et
valider avant tout usage réel. [Qualification](RAPPORT_LOT9.md).
