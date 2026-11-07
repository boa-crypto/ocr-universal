# Pages sans sortie dans la qualité — lot 70

7 novembre 2026. Corrige la limite constatée au [lot 69](LOCALISATIONS_BAIDU_DECLAREES.md), sans modifier la reconnaissance ni la géométrie.

## Convention conservatrice

Pour une `PageResult` sans mots, non marquée `blank`, et dont le texte est vide
après `str.strip()` :

- une contribution **zéro** est ajoutée à chacune des moyennes moteur/globale ;
- son numéro est ajouté à `quality.pages_low_confidence`, **même avec un seuil
  de revue égal à zéro** ;
- l'anomalie d'erreur `OCR_FAILED` préexistante reste présente ;
- aucun mot, score fournisseur, run ou résultat de reconnaissance n'est inventé.

Ce zéro est une convention de pénalisation de sortie manquante, pas une
probabilité d'erreur mesurée. Le texte composé uniquement d'espaces Unicode
reconnus par `str.strip()` n'est plus crédité du repli historique 0,95.
Il ne s'agit pas d'une analyse sémantique de l'utilité ou de la langue du texte.

Une page sans mots marquée `blank=True` reste exclue des moyennes et de cette
liste. Cette politique utilise le drapeau existant ; elle ne certifie pas que
l'image est physiquement vide ni que sa détection est correcte.

## Agrégation par page, pas par moteur

Une page reconnue à 1,0, une page non vide sans sortie et une page déclarée vide
produisent désormais une moyenne de **0,5**, et non 1,0. La page échouée apparaît
dans la liste ; la page déclarée vide ne grossit pas le dénominateur.

Les moyennes existantes restent des moyennes arithmétiques de contributions
**par page**, pas un taux de mots corrects ou une pondération par contenu. Plusieurs
runs échoués sur une même page ne multiplient pas sa contribution. L'ordre des
pages de la liste suit celui du document ; aucune nouvelle unicité des numéros
n'est imposée au modèle. Les résultats sont arrondis comme auparavant.

## Chemins inchangés

- Mots présents : moyenne des confiances et facteur de qualité existants, même
  seuil de revue. La validité ou le contenu de ces mots n'est pas réévalué ici.
- Texte non blanc sans mots : repli historique **0,95 conservé**, pas requalifié
  comme score mesuré ou preuve d'origine native.
- Champs, statuts humains, désaccords, contrôle de contenu et calculs métier :
  inchangés. Cette correction ne traite pas les champs de confiance nulle ni
  toutes les incohérences possibles entre texte, mots et drapeaux de page.
- Document vide : pas de page échouée créée artificiellement.
- Aucun ancien résultat/export recalculé ou migré ; le changement porte sur les
  nouveaux rapports construits. Une relecture/export d'un rapport ancien ne le
  requalifie pas automatiquement.

Le champ existant est conservé dans le résultat JSON, le stockage, l'API et
l'export JSON. Pas nouveau schéma, file visuelle de revue, autorisation, verrou
juridique, transition d'état du job ou mécanisme de validation automatique.
L'inscription dans `pages_low_confidence` signale la revue ; elle ne prouve pas
qu'un humain l'a effectuée et ne bloque pas à elle seule une validation métier.

## Vérification et limites

Tests synthétiques couvrant pages isolées/mixtes, blancs, espaces Unicode,
seuils 0/0,7/1, absence ou échec de moteurs, runs multiples et non-mutation.
Une vraie image PNG est ingérée par le pipeline avec un registre explicitement
vide dans le harnais de test : aucune reconnaissance fictive n'est produite.
Le stockage temporaire et les routes HTTP de résultat/export sont exercés via
TestClient. Ce n'est pas une mesure d'OCR réel ou de charge.

La géométrie Baidu absente reste approximative ; les autres limites des lots
65–69, notamment OAuth query, scores non calibrés et absence de qualification
fournisseur, restent présentes. Pas acquisition officielle, validation juridique
ou fiscale. Voir [rapport et recette](RAPPORT_LOT70.md).
