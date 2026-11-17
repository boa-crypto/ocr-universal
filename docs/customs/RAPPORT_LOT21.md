# Avancement — lot 21 : lecture native des pages PDF reçues

**2026-11-06 — service, CLI et API seulement ; aucune validation réglementaire.**

## Audit et livraison

Inspection du lecteur/rejeu Code, des correspondances document→archive, de la
lecture fragmentée d’article et du moteur PDF existant (`ingest`, pypdfium2).
Le chemin d’ingestion général rend les pages et peut mener à l’OCR ; il n’est pas
réutilisé comme prétendue transcription juridique vérifiée. Le même moteur PDF,
déjà dépendance, est utilisé sans rendu/OCR dans un worker minimal distinct.

- Service `lire_page_pdf`, CLI `customs-code-pdf-read`, route protégée
  `/api/v1/customs-review/lots/{lot_id}/pdf`, ID exact de document et page physique.
- Lot intégral contrôlé/rejoué, puis octets PDF relus et empreinte vérifiée contre
  document/manifeste avant extraction ; aucun chemin reçu du navigateur.
- Fragment de texte natif, provenance/empreintes, longueur, page/fragment suivants,
  marqueurs non validés, absence de texte explicitement signalée sans OCR automatique.
- Processus jetable PDFium pour éviter un nouveau partage entre threads du serveur,
  délai parent et bornes ; diagnostics parseur non exposés. Pas de dépendance ajoutée.
- Même autorisation nominative, registre, épingle, no-store et audit obligatoire.
  Le succès d’audit `lecture_pdf` ne contient ni fragment, document_id ou page.

[Guide et limites](LECTURE_PDF.md). **Aucun bouton PDF/lecteur visuel/export PDF UI
ajouté**. Le contrôle hors ligne des exports garde son périmètre antérieur.
Ce lot ne qualifie pas un import tarifaire PDF, l’ordre visuel ou la transcription.

## Qualification

**1 055 tests Python réussis, 1 avertissement Starlette/httpx**, données/journaux
isolés : sélection du [lot 20](RAPPORT_LOT20.md) + `tests/test_customs_pdf_page.py`,
soit **1 022 + 33 nouveaux cas**. **40 scénarios UI JSDOM réussis**, sans nouveau
scénario graphique PDF revendiqué. Ruff et `git diff --check` passent.
Pas de suite complète du dépôt annoncée.

PDF ReportLab temporaires NON OFFICIELS : pages natives 1/2, page blanche, fragments,
hors fin, empreinte des octets et source inchangée, document/page absents,
paramètres stricts avant accès disque, corruption/symlink/absence, pseudo-PDF opaque
refusé, véritable PDF chiffré refusé sans mot de passe. Timeout/crash/réponse worker
invalide/trop longue testés par injection contrôlée, erreurs sans valeur sensible.
CLI 0/2 et vrais GET API : pin, no-store, audit sans texte, panne audit→503 sans
résultat, refus anonyme/lecteur/tarif/paramètres/document absent. Aucune fixture
ou compte/registre/lot de production créé.

Première sélection PDF : 28 réussites / 4 échecs. Deux problèmes techniques corrigés :
le subprocess ne bénéficiait pas du sys.path pytest, et PdfPage n’implémente pas le
context manager dans la version installée. Lancement par chemin interne du worker,
fermetures explicites page/texte ; ajout du cas chiffré, puis sélection étendue
réexécutée : **1 055 réussites**.

Prévisualisation backend redémarrée sur 0.0.0.0:8000 : coque/module/service worker
200 avec hôte distant, liste et nouvelle route PDF anonymes 403. Coque v48 inchangée.
Journaux conservés hors commit. Empreintes historiques après redémarrage identiques :

- base : `688cb720eaeeddd8a88ea2e47021b6b9b17192d7226cc9e5218006b5adcb961f` ;
- référentiels : `b292d47e67f52c2fa7478b8a0d3dd963d1016b58efbb5964cf95420c55e17c3b`.

## Limites et mission restante

Un texte natif peut être absent, mal ordonné ou différer des glyphes visibles.
Page physique ≠ numéro imprimé ; aucun article localisé automatiquement. Aucune
comparaison automatique avec la transcription, traduction ou consolidation.
Processus séparé ≠ bac à sable OS/réseau complet ou antivirus ; quotas Unix tentés
si disponibles, pas de garantie globale RAM/concurrence ou innocuité du parseur C.

**0 nouvel original officiel acquis, 0 article/code national officiel validé,
0 publication active.** StarterPack, originaux/modifications exhaustifs,
tarif national courant et sources fiscales restent à acquérir et valider humainement.
Les calculs legacy non sourcés restent bloqués. La mission reste partielle.
