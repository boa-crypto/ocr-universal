# Limites connues (assumées et documentées)

Dernière mise à jour : 2026-10-18 — environnement de référence Debian 13,
2 CPU, 2 Go RAM, **sans GPU**.

## Moteurs et modèles

1. **Un seul moteur OCR raster est actif** dans cet environnement : Tesseract 5.5.
   L'architecture multi-moteurs (registre, sélection, consensus, désaccords) est
   implémentée et **testée avec des moteurs simulés**, mais la comparaison réelle
   entre moteurs nécessite l'installation d'EasyOCR et/ou PaddleOCR — impossible
   ici sans GPU/RAM supplémentaire (torch seul dépasse la RAM disponible).
   Les adaptateurs existent et s'activent automatiquement quand les paquets sont
   installés (`pip install easyocr` ou `paddleocr paddlepaddle`).
2. **Écriture manuscrite** : la détection de zones manuscrites n'est pas couplée à
   un modèle de transcription (aucun modèle HTR installable dans les contraintes
   matérielles). **La transcription manuscrite n'est pas fonctionnelle.**
3. **Tamazight (tifinagh)** : aucun modèle tessdata installé → **non supporté**.
   Le support est activable en installant `tesseract-ocr-amh`-style ou un modèle
   dédié, puis en l'ajoutant à la configuration.
4. **Arabe algérien** : le modèle `ara` (arabe standard) est disponible ; les
   particularités dialectales (lettres latines mixées, mots empruntés) ne sont pas
   modélisées et dégradent la précision.
5. **Chinois** : `chi_sim` uniquement (simplifié) ; pas de `chi_tra`.
6. **RTL** : l'ordre des lignes est préservé (colonnes inversées pour l'arabe),
   mais l'ordre interne des mots RTL dans une ligne mixte peut être dégradé selon
   le moteur.

## Reconnaissance

7. CER/WER publiés = mesures sur un **jeu synthétique de 9 fichiers généré
   programmatiquement** (benchmarks/results/latest.md). Ce ne sont **pas** des
   promesses sur documents réels bruités/anciens/manuscrits.
8. Les numéros ambigus (O/0, I/l/1) sont signalés (`AMBIGUOUS_CHARS`) mais pas
   corrigés silencieusement — la validation humaine est recommandée.
9. Tableaux sans filets : la détection repose sur l'alignement récurrent des mots ;
   les tableaux très irréguliers ou avec cellules multilignes serrées peuvent être
   segmentés à tort (contrôles structurels ≥ 2 lignes pour limiter les faux positifs).
10. Tableaux multipages : fusion uniquement si même nombre de colonnes ET pages
    consécutives ; une rupture de colonnes entre pages empêche la fusion.
11. Formulaires manuscrits / cases à cocher / signatures : les zones ne sont pas
    encore typées (détection de zones manuscrites et signatures **non implémentée**
    dans cette version).
12. Perspective extrême (> ~40°) ou documents sur fond très texturé : la détection
    du quadrilatère peut échouer (l'original reste intact).

## Formats

13. DOCX/ODT : texte et tableaux extraits ; la mise en page (colonnes, images
    légendées) n'est pas restituée ; géométrie de localisation **estimée** pour ces
    formats purement numériques (elle sert au surlignage, pas à la mise en page réelle).
14. XLS anciens (BIFF) : lecture via xlrd 2.x limitée aux fichiers `.xls` (pas de
    `.xlsb`).
15. PDF protégés par mot de passe non supportés (erreur explicite).
16. PDF consultable : reconstruction image + couche texte invisible ; la police
    d'origine n'est pas reproduite (Helvetica).

## API / UI

17. Le RBAC local par jeton et périmètre de dossiers est implémenté, mais ce
    n'est pas un IAM d'entreprise : pas de SSO, LDAP, expiration de session ni
    gestion centralisée des identités. `data/rbac.json` doit être protégé et
    l'API ne doit pas être exposée au réseau sans authentification explicite.
18. Traitement asynchrone par thread unique par job ; pas de file d'attente
    distribuée (Celery/Redis) — hors périmètre local 2 CPU.
19. L'UI n'est toujours pas testée dans un navigateur réel (aucun outil headless
    disponible dans l'environnement de référence) : le rendu visuel, le
    responsive et les contrastes ne sont **pas** vérifiés automatiquement.
    Ce qui est vérifié : la cohérence entre les identifiants DOM et le script
    (74 références, aucun manquant), la syntaxe du script, son chargement sans
    `ReferenceError` sur un DOM simulé, et le fait que les classes générées par
    le script sont bien stylées. Les endpoints qu'elle appelle sont couverts par
    les tests API. **À valider par un utilisateur dans un navigateur.**
19bis. `GET /api/search` balaye linéairement les résultats stockés : le coût
    croît avec le nombre de documents. Acceptable jusqu'à quelques centaines
    de documents ; au-delà, prévoir un index dédié.

## Sécurité

20. La détection de prompt-injection est un **signalement** heuristique
    (regex) ; elle n'est pas un pare-feu sémantique complet.
21. Le chiffrement au repos est optionnel et désactivé par défaut. Il protège
    les fichiers stockés, pas les données en mémoire pendant l'OCR. La rétention
    est configurable (`security.retention_days`).

## Typage de zones (E2)

23. La détection de cases à cocher est **heuristique et géométrique**, sans
    modèle appris. Mesures sur images *synthétiques* : rappel 4/4 et précision
    17 % sur un formulaire de contrôle, 0 faux positif sur 5 documents sans
    case, 15 candidats sur une carte grise qui n'en contient aucune. Les
    zones sont des **candidats à confirmer**, jamais des faits.
24. La détection de signatures et d'écriture manuscrite a été implémentée
    puis **retirée** : elle classait un code-barres 2D comme « manuscrit » et
    trouvait 21 « signatures » sur une carte grise. Aucun discriminateur
    géométrique fiable n'a été trouvé ; la capacité n'est pas revendiquée.
    Aucune transcription manuscrite (HTR) n'est effectuée.

## Moteurs OCR (E1)

25. **Aucun second moteur OCR n'a pu être validé ici.** EasyOCR et PaddleOCR
    ne sont pas installés et torch dépasse la RAM disponible (2 Go au total,
    ~1,4 Go libre). Le consensus multi-moteurs reste donc testé uniquement
    avec des moteurs simulés. Ce qui est livré et testé : un **garde-fou
    mémoire** qui refuse d'activer un moteur dont la bibliothèque est présente
    mais qui ne tiendrait pas en RAM, en affichant la raison
    (`unavailable_reason`). Les seuils de mémoire annoncés (2,2 Go EasyOCR,
    1,8 Go PaddleOCR) sont des ordres de grandeur **non mesurés** sur ce
    matériel.

## Chiffrement (E3)

26. Le chiffrement au repos est **optionnel et désactivé par défaut**. Il
    protège le stockage (disque, sauvegarde), pas le traitement : les
    documents sont déchiffrés en mémoire pour être analysés. Perdre la clé
    rend les données définitivement illisibles.

## Parallélisme (E4)

27. Gain mesuré sur un document de 4 pages scannées, 2 cœurs, mode `fast` :
    **×1,18** (18,44 s → 15,68 s, médiane de 3 exécutions). Ce n'est pas ×2 :
    l'ingestion, la qualité et les exports restent séquentiels, et la RAM
    limite le nombre de workers à 2. Résultats strictement identiques au
    traitement séquentiel (texte, champs, ordre des pages).

## Matériel

22. Aucune accélération GPU (CUDA/Vulkan) — **non vérifiée car absente**, jamais
    revendiquée. Temps de traitement : ~2–7 s/page sur le jeu de test en mode
    `accurate` (2 cœurs).

## Connecteur Hub (intégration)

28. **Aucun connecteur réel n'est livré.** Aucun accès API douanière ou
    portuaire n'a été obtenu, documenté ni autorisé. Le catalogue ne contient
    que deux adaptateurs locaux : un **simulateur** et un **export assisté**
    (mode C). Le simulateur n'est pas une intégration réelle : il renvoie des
    références `DEMO-…` et son accusé de réception ne vaut que pour lui-même.
29. **La structure des formulaires cibles est déclarée, pas officielle.** Les
    trames « Déclaration en douane » et « Escale portuaire » sont des bases de
    travail construites à partir du cahier des charges. Aucune n'a été validée
    contre une spécification d'organisme : les noms de champs réels
    (`external_name`) restent à renseigner. Un mapping automatique fiable est
    impossible sans cette documentation.
30. **Le rapprochement par clé d'idempotence ne fonctionne que si le système
    cible expose une recherche par clé.** Le simulateur la fournit ; une API
    réelle devra être vérifiée avant d'activer la reprise automatique. Sans
    cette capacité, une transmission à l'issue inconnue reste
    `pending_confirmation` et nécessite une vérification manuelle.
31. **Les reprises automatiques sont limitées à 3 et uniquement après un échec
    technique** (`failed`). Un rejet métier (`rejected`) n'est jamais rejoué,
    car il indique que le système cible a refusé la demande pour un motif
    métier — la rejouer identiquement produirait le même refus.
32. **Le secret zéro n'est pas vérifiable par un test automatisé ici.** Les
    tests confirment que les valeurs ne fuient pas dans les réponses HTTP de
    cette API, mais un déploiement différent (proxy, journal d'accès) doit
    être audité séparément.
33. **L'interface du hub n'a pas pu être contrôlée visuellement** : aucun
    navigateur headless n'est disponible dans cet environnement. Les contrôles
    effectués sont : syntaxe de **chacun** des blocs `<script>`, chargement sans
    `ReferenceError` sur DOM simulé, cohérence des identifiants HTML/JS, absence
    de ressource externe, parcours HTTP complet contre l'API réelle, et
    **contrôle de rendu** qui exécute le module JS du hub sur un DOM simulé
    branché sur l'API (21 contrôles : 12 sous-menus + 9 étapes de l'assistant).
    Le rendu visuel lui-même (polices, espacements, animations, comportement au
    clavier, mobile, lecteurs d'écran) n'a pas été vérifié.
34. **Le contrôle de rendu suppose le serveur local démarré** sur le port 8000.
    Sans lui, il est ignoré (message `[--]`) plutôt que de faire échouer la
    suite — un serveur absent n'est pas un défaut de l'interface.
    Le message distingue désormais les deux cas (`API locale injoignable
    (ECONNREFUSED)` vs. autre cause) : pendant le développement, le contrôle
    s'était une fois déclaré « ignoré » alors que le serveur écoutait, parce que
    le harnais sortait en code 1 sur les panneaux « Connecteurs actifs » et
    « Configuration » à l'état **vide** — ce qui est un rendu valide (message
    `cnx-empty`). Les états vides explicites sont acceptés depuis.
35. **Le contrôle de rendu valide la présence de contenu, pas son exactitude
    visuelle.** Un sous-menu est déclaré rendu s'il produit au moins 3 éléments
    ou un état vide explicite ; il ne vérifie ni l'ordre d'affichage, ni les
    libellés attendus champ par champ, ni le style. Une régression de mise en
    page resterait invisible.

