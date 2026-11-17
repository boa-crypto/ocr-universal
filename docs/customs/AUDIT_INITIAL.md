# Référentiels douaniers algériens — audit initial

Date : 2026-11-04. État inspecté : commit fe6e5f23, branche arena/2cd4c91a-ocr-universal.
**Mission non terminée. Aucun référentiel complet ni juridiquement validé disponible.**

## 1. Audit effectué avant implémentation

- `src/unocr/reglementation.py` : StoreReglementation JSON, cache global mutable,
  remplacement de fichier ; get() peut écrire un objet vide. Ne pas l'importer
  comme outil d'audit en lecture seule. Pas de registre documentaire vérifiable.
- `data/reglementation/base.json` : 9 codes à **4 chiffres**, 9 règles, 4 types de
  certificats. Version déclarée 1.0.0, date interne 2026-10-30. Aucun de ces nombres
  n'établit une couverture légale. SHA256 avant intervention :
  `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f`.
- Les 9 codes de ce fichier dupliquent les clés du littéral CODES_SH_ALGERIE du
  module. Les libellés n'ont pas de référence/page justificative. Ne pas corriger
  ni compléter ces libellés à partir de connaissances supposées.
- normaliser_code_sh ajoute des zéros ; verifier_code_sh accepte diverses longueurs
  et contient une pseudo-clé de contrôle. Ni l'un ni l'autre n'établit l'existence
  d'une sous-position nationale. À ne pas réutiliser pour le nouveau référentiel.
- **Danger critique** : calculer_droits utilise 5 % de droits hypothétiques, 9 % de
  TVA et 5 % de TPC, sans source applicable. Les routes `/api/reglementation/droits/*`
  les exposent. Décision : blocage explicite, aucun taux de remplacement inventé.
- `models.ClassificationTarifaire` : code libre, montants/taxes par défaut zéro,
  statut_validité vrai par défaut, pas de validation de provenance/date. Modèle
  historique non apte à servir de référence réglementaire vérifiée.
- `routes/referentiels.py` et `data/referentiels.json` : référentiels génériques.
  « tarifs » = grilles **de frais**, pas nomenclature douanière. 11 collections
  actuellement vides. SHA256 du fichier avant intervention :
  `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.
- `BusinessStore` SQLite : transactions BEGIN IMMEDIATE et objets JSON ; pas de
  gouvernance juridique, historique inviolable ou publication de versions.
- `backup.py` : sauvegarde SQLite et dossiers ; vérifier explicitement la prise
  en charge du futur magasin réglementaire avant publication. Ne pas déplacer
  ni écraser les données de l'ancien magasin pendant cette mission.

### StarterPack

Recherche du nom `*starter*` sous /home/user (hors .git, dépendances et venv), et
inventaire des chemins réglementaires : **UniOCR_Referentiels_StarterPack absent**.
Son contenu, ses doublons et sa provenance ne peuvent pas être audités. Il faut
fournir le paquet original ou son chemin réel. Aucun paquet de substitution créé.

### Dépendances et interfaces

- OCR : pipeline.py, ocr_integration.py, ExtractionOCR/ChampExtrait, profils facture,
  packing list et BL. Une transcription OCR n'est pas une source juridique validée.
- classification.py : classification **documentaire**, pas classement tarifaire.
- Marchandises : models.py position_tarifaire (champ libre). Déclarations :
  routes/declarations.py positions_tarifaires (liste libre). À relier à des
  identifiants de version centrale, sans écraser les valeurs historiques.
- Frais/factures : routes/frais.py, montants métier ; pas de calcul fiscal légal
  établi. Ne pas confondre barèmes de frais et droits/taxes douaniers.
- Connecteur customs.py : adaptateur d'API configurable, pas un accès ALCES acquis
  ni un téléchargeur certifié du tarif national.
- API : FastAPI, routes existantes /api/reglementation et /api/referentiels.
  RBAC central dans api.py : écritures opérateur par défaut ; sans rbac.json,
  contrôle historique permissif. Les futures validations réglementaires devront
  exiger un utilisateur habilité explicite, même si RBAC générique est désactivé.
- UI : web/ecrans.js + composants/DS existants. Écrans réglementation et
  référentiels déjà présents ; étendre, ne pas créer un second shell.

## 2. Recherche documentaire effectuée

Les accès ci-dessous sont des consultations par outil web, pas un archivage des
**octets originaux**. Aucun SHA256 de PDF officiel ne peut être annoncé sur cette
base. Une extraction markdown d'un PDF n'est pas le PDF d'origine.

| Source / URL consultée | Résultat observé | Conséquence |
|---|---|---|
| https://www.joradp.dz/HFR/Index.htm | Page consultée ; liens recherche/Journaux | Point d'entrée, pas inventaire exhaustif des modifications |
| https://www.douane.gov.dz/ | Page consultée | Liens vers textes, LF 2026, décisions |
| https://www.douane.gov.dz/spip.php?article23= | Page consultée, paginée | Liste des lois ; pagination non intégralement parcourue |
| https://www.douane.gov.dz/IMG/pdf/loi_no79-07_du_21_juillet_1979.pdf | Extraction partielle consultée, 7 chunks annoncés ; couverture PDF limitée par l'outil | En-tête « Modifiée et complétée / Mise à jour Juin 2017 » ; ni original 1979 ni consolidation courante prouvée |
| https://www.douane.gov.dz/IMG/pdf/loi_no_17-04_du_16_fevrier_2017_code_des_douanes.pdf | Échec fetch | Original à acquérir et vérifier au JO |
| https://www.douane.gov.dz/spip.php?breve74 | Page consultée, lien loi_de_finance_2026.pdf | Texte identifié, modifications non dépouillées |
| https://www.douane.gov.dz/spip.php?article790 | Page consultée, lien recueil_des_decisions_de_classement_tarifaire_2026.pdf | Recueil annoncé pour décisions 2025, pas nomenclature complète |
| https://www.douane.gov.dz/spip.php?rubrique170= | Échec fetch | Catalogue tarifaire non contrôlé |
| https://www.commerce.gov.dz/ et /fr | Échecs fetch | Ne pas conclure à une indisponibilité mondiale du site |
| https://www.commerce.gov.dz/fr/tarif-douanier-10-chiffres | Échec fetch HTTP 500 | Fichier national complet non acquis |
| https://alces.douane.gov.dz/ (redirection /main) | Page consultée ; entrée « Code SH » | Aucun export intégral ni API publique vérifiés ; aucun contournement d'authentification |
| https://www.wcoomd.org/ | Page « Service Unavailable / HTTP Error 503 » | RGI/notes officielles non acquises |
| https://www.wto.org/ | Accueil consulté | Pas de preuve de tarif national applicable |
| https://www.un.org/ | Accueil consulté | Pas de nomenclature nationale acquise |

Les résultats de recherche ont servi seulement à repérer des URL candidates.
Ils ont aussi renvoyé des résultats français/européens/canadiens hors périmètre :
**aucun n'est importé comme tarif algérien**. Aucun nombre annoncé de sous-positions
n'est utilisé comme dénominateur de complétude.

## 3. Blocages et décisions de sûreté

- Octets sources originaux manquants ; accès réseau direct du sandbox restreint.
  Les outils de consultation peuvent retourner du texte mais ne fournissent pas
  ici de copie binaire archivée. Ne pas contourner les restrictions réseau.
- Tarif officiel intégral courant non acquis ; version la plus récente non établie.
- Lois 79-07, 98-10, 17-04 : références initiales fournies par la mission ; corpus
  original complet, rectificatifs, LF et actes ultérieurs non contrôlés.
- Pas de validation juridique humaine, ni date d'applicabilité démontrée.
- **Aucune publication active** autorisée à partir de ces éléments. Importer en
  quarantaine seulement, conserver les fichiers, les empreintes et la provenance.
- Les tests devront utiliser des fixtures techniques identifiées comme telles ;
  ces fixtures ne seront jamais livrées comme données réglementaires officielles.

## 4. Plan d'architecture retenu pour le socle

Nouveau domaine customs_reference, séparé du legacy et des grilles de frais :
provenance + sources originales, nomenclature, hiérarchie explicite, mesures
séparées, articles originaux/modificatifs/consolidations provisoires distincts.
Le premier importateur sera local et sans publication : JSON canonique et CSV
mappé explicitement, avec parents indépendants, aucun code reconstitué par padding.
Les autres formats nécessitent des adaptateurs vérifiés contre leurs fichiers
réels ; PDF/OCR reste une extraction provisoire, jamais une validation juridique.

Les phases ultérieures (consolidation datée, recherche multilingue, classement IA,
relations documentées, API v1, validation habilitée et extension UI) ne doivent pas
être simulées. La source centrale ne remplace le legacy qu'après ces contrôles.


## 5. Compléments de recherche après l'audit initial

La variante https://www.douane.gov.dz/spip.php?rubrique170&lang=fr a ensuite
fonctionné (l'échec initial avec `rubrique170=` ne signifie donc pas que tout le
catalogue est inaccessible). Elle annonce notamment des amendements 2023/2024,
le SH 2022 et les corrélations SH 2017. Ces intitulés ne prouvent pas la dernière
version nationale applicable en 2026.

- https://www.douane.gov.dz/spip.php?article530 : page consultée, liens vers
  note_no4121_du_28.12_2023.pdf et table_de_correlation_-_eclatement_tarifaire_spt_autres2024_.pdf.
- https://www.douane.gov.dz/spip.php?rubrique170&lang=fr&debut_documents_joints=6 :
  liens FR/AR d'un arrêté daté du 19 décembre 2023 relatif au DAPS ; aucune liste
  de taux importée ni applicabilité courante déduite.
- https://www.douane.gov.dz/spip.php?article8 redirige vers
  https://www.douane.gov.dz/spip.php?page=tarif_douanier : table des sections et
  formulaire consultés, pas un export intégral des codes à 10 chiffres.
- https://www.douane.gov.dz/spip.php?article368 : page de présentation consultée.
- https://www.joradp.dz/JRN/ZF1979.htm et /JRN/ZF1998.htm : calendriers consultés,
  sans acquisition/identification du numéro contenant les textes recherchés.
  /JRN/ZF2017.htm a échoué dans cette tentative.
- https://www.douane.gov.dz/IMG/pdf/loi_de_finance_2026.pdf : extraction initiale
  consultée, en-tête « Loi n°25-17 du 14 décembre 2025 portant loi de finances
  pour 2026 ». 9 chunks annoncés et limite d'extraction PDF de l'outil : ce n'est
  pas un contrôle complet de ses dispositions douanières, ni un original archivé.

**Bilan documentaire inchangé :** aucun fichier tarifaire intégral ni PDF original
binaire archivé, aucune chronologie exhaustive ou consolidation validée. L'accès
à une interface de consultation ne vaut pas acquisition d'un jeu complet.
