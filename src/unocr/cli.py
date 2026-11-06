"""CLI UniOCR : traitement de fichier, serveur, diagnostic."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_process(args) -> int:
    # Validation avant tout travail : un chemin absent ou un répertoire doit
    # donner un message lisible, pas un traceback brut.
    chemin = Path(args.file)
    if not chemin.exists():
        print(f"erreur : fichier introuvable : {chemin}", file=sys.stderr)
        return 2
    if not chemin.is_file():
        print(f"erreur : ce n'est pas un fichier : {chemin}", file=sys.stderr)
        return 2

    from .config import get_config
    from .exporters import export_all
    from .ingest import page_images as page_images_for
    from .models import JobOptions
    from .pipeline import Pipeline

    cfg = get_config()
    options = JobOptions(
        languages=[ln for ln in (args.lang or "").split(",") if ln],
        profile=args.profile,
        quality_mode=args.quality_mode,
        preprocess=not args.no_preprocess,
        export_formats=[f for f in args.export.split(",") if f],
    )
    pipeline = Pipeline(cfg)

    def progress(stage: str, frac: float) -> None:
        print(f"[{frac*100:5.1f}%] {stage}", file=sys.stderr)

    result = pipeline.process_file(args.file, options, progress=progress)
    out_dir = Path(args.out) if args.out else Path(args.file).parent / "exports"
    page_images = page_images_for(args.file, dpi=cfg.get("render_dpi", 200))
    result.exports = export_all(result, out_dir, options.export_formats,
                                page_images=page_images or None)
    # Forcer l'encodage UTF-8 pour la sortie standard pour éviter les erreurs d'encodage sous Windows
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
    print(json.dumps({
        "id": result.id,
        "source": result.source_file,
        "pages": len(result.pages),
        "fields_detected": sum(1 for f in result.fields.values() if f.value),
        "tables": len(result.tables),
        "anomalies": len(result.quality.anomalies),
        "mean_engine_confidence": result.quality.mean_engine_confidence,
        "mean_global_confidence": result.quality.mean_global_confidence,
        "engines": result.engines_used,
        "exports": [e.path for e in result.exports],
        "timings_ms": result.timings_ms,
    }, ensure_ascii=False, indent=2))
    sys.stdout.flush()
    return 0


def cmd_serve(args) -> int:
    import uvicorn

    from .config import get_config
    cfg = get_config()
    uvicorn.run("unocr.api:app", host=args.host or cfg.get("api.host", "127.0.0.1"),
                port=args.port or cfg.get("api.port", 8000), reload=False)
    return 0


def cmd_diagnose(args) -> int:
    import os
    import platform

    from .config import get_config
    from .ocr_engines import EngineRegistry
    cfg = get_config()
    reg = EngineRegistry()
    report = {
        "os": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "engines": reg.list_engines(),
        "profiles_dir": str(cfg.profiles_dir),
    }
    try:
        import psutil
        report["memory_total_mb"] = round(psutil.virtual_memory().total / 1e6)
        report["memory_available_mb"] = round(psutil.virtual_memory().available / 1e6)
    except Exception as exc:
        # un rapport de diagnostic doit dire ce qu'il n'a pas pu mesurer
        report["memory_error"] = f"psutil indisponible ou illisible : {exc}"
        print(f"avertissement : mémoire non mesurée ({exc})", file=sys.stderr)
    import shutil
    report["binaries"] = {b: shutil.which(b) for b in
                          ["tesseract", "pdftoppm", "gs", "soffice", "magick"]}
    try:
        tess = reg.get("tesseract")
        if tess and tess.is_available():
            report["tesseract_languages"] = tess.supported_languages()
    except Exception as exc:
        report["tesseract_languages_error"] = f"langues non listées : {exc}"
        print(f"avertissement : langues tesseract non listées ({exc})", file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="unocr", description="UniOCR — moteur OCR universel")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("process", help="traiter un document")
    p.add_argument("file")
    p.add_argument("--profile", default="generic")
    p.add_argument("--lang", default="", help="langues séparées par virgule (défaut: auto)")
    p.add_argument("--quality-mode", default="accurate", choices=["fast", "accurate"])
    p.add_argument("--no-preprocess", action="store_true")
    p.add_argument("--export", default="json,txt")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_process)

    s = sub.add_parser("serve", help="lancer l'API + l'interface web")
    s.add_argument("--host", default="")
    s.add_argument("--port", type=int, default=0)
    s.set_defaults(func=cmd_serve)

    d = sub.add_parser("diagnose", help="diagnostic de l'environnement")
    d.set_defaults(func=cmd_diagnose)

    c = sub.add_parser("clean", help="purger les jobs terminés au-delà de la rétention")
    c.add_argument("--days", type=int, default=None,
                   help="forcer la rétention en jours (défaut : security.retention_days)")
    c.add_argument("--dry-run", action="store_true",
                   help="afficher ce qui serait supprimé, sans rien toucher")
    c.set_defaults(func=cmd_clean)

    b = sub.add_parser("backup", help="sauvegarder le magasin (jobs, dossiers, exports, audit)")
    b.add_argument("--out", default="",
                   help="répertoire de destination (défaut : sauvegardes, ou sauvegardes-quarantaine avec option explicite)")
    b.add_argument("--tag", default="", help="étiquette ajoutée au nom du fichier")
    b.add_argument("--keep", type=int, default=5,
                   help="nombre de sauvegardes à conserver (0 = ne pas purger)")
    b.add_argument("--include-customs-quarantine", action="store_true", help="inclure explicitement la quarantaine (CLI local seulement)")
    b.set_defaults(func=cmd_backup)

    r = sub.add_parser("restore", help="restaurer le magasin depuis une sauvegarde")
    r.add_argument("fichier", help="chemin du .zip de sauvegarde")
    r.add_argument("--force", action="store_true",
                   help="autoriser l'écriture sur un magasin non vide")
    r.add_argument("--include-customs-quarantine", action="store_true", help="reprendre explicitement la quarantaine dans un magasin neuf")
    r.set_defaults(func=cmd_restore)

    lb = sub.add_parser("backups", help="lister les sauvegardes disponibles")
    lb.add_argument("--dir", default="", help="répertoire des sauvegardes")
    lb.set_defaults(func=cmd_backups)

    pc = sub.add_parser("pieces-check", help="diagnostiquer les justificatifs sans rien modifier")
    pc.add_argument("--data-dir", default="", help="répertoire du magasin à inspecter")
    pc.add_argument("--json", action="store_true", dest="json_output", help="rapport structuré")
    pc.set_defaults(func=cmd_pieces_check)

    pr = sub.add_parser("pieces-recover", help="préparer la copie vérifiée d'une quarantaine référencée")
    pr.add_argument("id", help="identifiant du justificatif")
    pr.add_argument("--data-dir", default="", help="magasin à examiner")
    pr.add_argument("--apply", action="store_true", help="appliquer explicitement le plan, sans écrasement")
    pr.add_argument("--json", action="store_true", dest="json_output", help="rapport structuré")
    pr.set_defaults(func=cmd_pieces_recover)

    pe = sub.add_parser("pieces-receipt", help="consulter le reçu local de suppression d'une pièce")
    pe.add_argument("id", help="identifiant du justificatif supprimé")
    pe.add_argument("--data-dir", default="", help="magasin à examiner sans modification")
    pe.add_argument("--json", action="store_true", dest="json_output", help="rapport structuré")
    pe.set_defaults(func=cmd_pieces_receipt)

    pa = sub.add_parser("pieces-audit", help="préparer le relais ciblé d'un reçu vers audit.log")
    pa.add_argument("id", help="identifiant du justificatif supprimé")
    pa.add_argument("--data-dir", default="", help="magasin source")
    pa.add_argument("--audit-file", required=True, help="journal JSONL cible, parent existant")
    pa.add_argument("--apply", action="store_true", help="ajouter explicitement après arrêt des écritures")
    pa.add_argument("--json", action="store_true", dest="json_output", help="rapport structuré")
    pa.set_defaults(func=cmd_pieces_audit)

    cr = sub.add_parser("customs-prepare", help="préparer un tarif CSV/JSON/XLSX en quarantaine, jamais l'activer")
    cr.add_argument("source", help="fichier source local")
    cr.add_argument("--metadata", required=True, help="provenance, hiérarchie et mapping explicites")
    cr.add_argument("--out", default="", help="nouveau répertoire de préparation")
    cr.add_argument("--write", action="store_true", help="écrire explicitement le lot en quarantaine")
    cr.set_defaults(func=cmd_customs_prepare)

    cd = sub.add_parser("customs-diff", help="comparer deux lots en quarantaine sans modification")
    cd.add_argument("avant", help="répertoire du premier lot préparé")
    cd.add_argument("apres", help="répertoire du second lot préparé")
    cd.set_defaults(func=cmd_customs_diff)

    cc = sub.add_parser("customs-code-prepare", help="archiver PDF et transcriptions du Code en quarantaine")
    cc.add_argument("transcription", help="JSON déclaré : articles et relations, éventuellement vides")
    cc.add_argument("--metadata", required=True, help="documents, empreintes et noms locaux des PDF reçus")
    cc.add_argument("--out", default="", help="nouveau répertoire de préparation")
    cc.add_argument("--write", action="store_true", help="écrire explicitement, sans publication")
    cc.set_defaults(func=cmd_customs_code_prepare)

    ck = sub.add_parser("customs-code-check", help="vérifier et rejouer un lot Code sans le modifier")
    ck.add_argument("lot", help="répertoire du lot Code préparé")
    ck.set_defaults(func=cmd_customs_code_check)

    dc = sub.add_parser("customs-code-diff", help="comparer deux lots Code vérifiés sans modification")
    dc.add_argument("avant", help="premier lot Code")
    dc.add_argument("apres", help="second lot Code")
    dc.set_defaults(func=cmd_customs_code_diff)

    ts = sub.add_parser("customs-tariff-search", help="rechercher des désignations ou préfixes dans un lot tarifaire contrôlé")
    ts.add_argument("lot", help="lot tarifaire en quarantaine")
    ts.add_argument("--query", required=True, help="texte FR/AR ou préfixe de 1 à 10 chiffres ASCII")
    ts.add_argument("--limit", type=int, default=20, help="résultats par page, 1 à 100")
    ts.add_argument("--offset", type=int, default=0, help="décalage, 0 à 1000000")
    ts.set_defaults(func=cmd_customs_tariff_search)

    cs = sub.add_parser("customs-code-search", help="rechercher des textes ou filtrer les articles d'un lot Code contrôlé")
    cs.add_argument("lot", help="lot documentaire Code en quarantaine")
    cs.add_argument("--query", default="", help="texte FR/AR, ou filtre explicite requis")
    cs.add_argument("--article", default=None, help="numéro d'article exactement tel que déclaré")
    cs.add_argument("--source", default=None, help="ID exact du document déclaré")
    cs.add_argument("--nature", choices=["originale", "modificative", "consolidee_provisoire"], default=None)
    cs.add_argument("--limit", type=int, default=20)
    cs.add_argument("--offset", type=int, default=0)
    cs.set_defaults(func=cmd_customs_code_search)

    ch = sub.add_parser("customs-code-history", help="historique documentaire d'un article, sans droit applicable")
    ch.add_argument("lot", help="lot Code en quarantaine")
    ch.add_argument("--article", required=True, help="numéro exactement tel que déclaré")
    ch.add_argument("--limit", type=int, default=20)
    ch.add_argument("--offset", type=int, default=0)
    ch.add_argument("--relations-limit", type=int, default=20)
    ch.add_argument("--relations-offset", type=int, default=0)
    ch.set_defaults(func=cmd_customs_code_history)

    tf = sub.add_parser("customs-tariff-show", help="fiche documentaire d'un code exact, sans droits applicables")
    tf.add_argument("lot", help="lot tarifaire contrôlé en quarantaine")
    tf.add_argument("--code", required=True, help="chaîne exacte de dix chiffres ASCII")
    tf.add_argument("--measures-limit", type=int, default=20)
    tf.add_argument("--measures-offset", type=int, default=0)
    tf.set_defaults(func=cmd_customs_tariff_show)

    args = parser.parse_args(argv)
    return args.func(args)


def _racine_pieces(data_dir: str) -> Path:
    if data_dir:
        return Path(data_dir)
    else:
        import os

        from .config import get_config
        cfg = get_config()
        # Ne pas utiliser cfg.data_dir : cette propriété crée le répertoire.
        chemin_env = os.environ.get("UNOCR_DATA_DIR")
        return Path(chemin_env).resolve() if chemin_env else cfg.root / cfg.get("jobs.data_dir", "data")


def cmd_pieces_check(args) -> int:
    from .justificatifs_diagnostic import diagnostiquer_pieces

    racine = _racine_pieces(args.data_dir)
    resultat = diagnostiquer_pieces(racine)
    if args.json_output:
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    else:
        print(f"Justificatifs — {resultat['etat']} — {resultat['pieces_referencees']} pièce(s) référencée(s)")
        print(resultat["limite"])
        for anomalie in resultat["anomalies"]:
            print(f"  {anomalie['categorie']} : {anomalie['cible']} — {anomalie['detail']}")
    return {"conforme": 0, "anomalies": 1, "indisponible": 2}[resultat["etat"]]


def _afficher_lecture_douaniere(operation, *chemins) -> int:
    try:
        resultat = operation(*(Path(chemin) for chemin in chemins))
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"statut": "refuse", "lecture_seule": True, "publication_active": False,
                          "validation_juridique": "non_validee", "detail": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


def cmd_customs_tariff_search(args) -> int:
    from .customs_reference.search import rechercher_tarif

    return _afficher_lecture_douaniere(lambda chemin: rechercher_tarif(chemin, args.query, args.limit, args.offset), args.lot)


def cmd_customs_code_search(args) -> int:
    from .customs_reference.search import rechercher_code

    return _afficher_lecture_douaniere(lambda chemin: rechercher_code(chemin, args.query, args.limit, args.offset,
                                       args.article, args.source, args.nature), args.lot)


def cmd_customs_tariff_show(args) -> int:
    from .customs_reference.tariff_detail import consulter_code

    return _afficher_lecture_douaniere(lambda chemin: consulter_code(
        chemin, args.code, args.measures_limit, args.measures_offset), args.lot)


def cmd_customs_code_history(args) -> int:
    from .customs_reference.history import historique_article

    return _afficher_lecture_douaniere(lambda chemin: historique_article(
        chemin, args.article, args.limit, args.offset, args.relations_limit, args.relations_offset), args.lot)


def cmd_customs_code_check(args) -> int:
    from .customs_reference.legal_comparison import charger_lot_code

    return _afficher_lecture_douaniere(lambda chemin: charger_lot_code(chemin)[1], args.lot)


def cmd_customs_code_diff(args) -> int:
    from .customs_reference.legal_comparison import comparer_lots_code

    return _afficher_lecture_douaniere(comparer_lots_code, args.avant, args.apres)


def cmd_customs_code_prepare(args) -> int:
    from .customs_reference.legal_importer import preparer_code

    if args.write and not args.out:
        print("--out est requis avec --write", file=sys.stderr)
        return 2
    try:
        resultat = preparer_code(Path(args.transcription), Path(args.metadata), Path(args.out) if args.write else None)
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"statut": "refuse", "publication_active": False, "detail": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


def cmd_customs_diff(args) -> int:
    from .customs_reference.comparison import comparer_lots

    try:
        resultat = comparer_lots(Path(args.avant), Path(args.apres))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"statut": "refuse", "lecture_seule": True, "publication_active": False, "detail": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


def cmd_customs_prepare(args) -> int:
    from pydantic import ValidationError

    from .customs_reference.importer import preparer_tarif

    if args.write and not args.out:
        print("--out est requis avec --write", file=sys.stderr)
        return 2
    try:
        resultat = preparer_tarif(Path(args.source), Path(args.metadata), Path(args.out) if args.write else None)
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
        print(json.dumps({"statut": "refuse", "publication_active": False, "detail": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


def cmd_pieces_audit(args) -> int:
    from .pieces_audit import relayer_suppression

    resultat = relayer_suppression(_racine_pieces(args.data_dir), args.id, Path(args.audit_file), args.apply)
    if args.json_output:
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    else:
        print(f"Relais {args.id} : {resultat['etat']}.")
        print(resultat["limite"])
        if resultat.get("detail"):
            print(resultat["detail"], file=sys.stderr)
    return 2 if resultat["etat"] in {"refuse", "indetermine"} else 0


def cmd_pieces_receipt(args) -> int:
    from .pieces_receipts import consulter_suppression

    resultat = consulter_suppression(_racine_pieces(args.data_dir), args.id)
    if args.json_output:
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    else:
        print(f"Reçu de suppression {args.id} : {resultat['etat']}.")
        print(resultat["limite"])
        if resultat.get("detail"):
            print(resultat["detail"], file=sys.stderr)
    return 2 if resultat["etat"] == "indisponible" else 0


def cmd_pieces_recover(args) -> int:
    from .justificatifs_recovery import RecuperationRefusee, recuperer_piece

    try:
        resultat = recuperer_piece(_racine_pieces(args.data_dir), args.id, appliquer=args.apply)
        code = 0
    except RecuperationRefusee as exc:
        resultat = {"etat": "refuse", "applique": False, "detail": str(exc)}
        code = 2
    if args.json_output:
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    elif code:
        print("Récupération refusée : " + resultat["detail"], file=sys.stderr)
    else:
        print(f"Justificatif {args.id} : {resultat['etat']}. Quarantaine conservée.")
        if not args.apply:
            print("Plan uniquement. Sauvegarder, copier la quarantaine à part et suspendre les écritures avant --apply.")
        if resultat.get("residu_temporaire"):
            print("Nettoyage manuel à examiner : " + resultat["residu_temporaire"])
    return code


def cmd_backup(args) -> int:
    """Crée une sauvegarde horodatée du magasin, puis purge les anciennes."""
    from pathlib import Path

    from .backup import BackupError, creer_sauvegarde, purger_sauvegardes
    from .config import get_config

    cfg = get_config()
    destination = Path(args.out) if args.out else None
    try:
        res = creer_sauvegarde(cfg, destination=destination, etiquette=args.tag,
                               inclure_quarantaine=getattr(args, "include_customs_quarantine", False))
    except BackupError as exc:
        print(f"sauvegarde refusée : {exc}", file=sys.stderr)
        return 2
    print(f"sauvegarde créée : {res.chemin}")
    print(f"  {res.fichiers} fichier(s), {res.octets} octets "
          f"({res.taille} octets compressés)")
    print(f"  empreinte SHA-256 : {res.empreinte[:32]}…")
    if args.keep:
        repertoire = res.chemin.parent
        supprimees = purger_sauvegardes(repertoire, conserver=args.keep)
        if supprimees:
            print(f"  purgées ({len(supprimees)}) : {', '.join(supprimees)}")
    return 0


def cmd_restore(args) -> int:
    """Restaure après vérification d'intégrité, jamais à l'aveugle."""
    from pathlib import Path

    from .backup import BackupError, restaurer_sauvegarde
    from .config import get_config

    cfg = get_config()
    try:
        res = restaurer_sauvegarde(cfg, Path(args.fichier), force=args.force,
                                    inclure_quarantaine=getattr(args, "include_customs_quarantine", False))
    except BackupError as exc:
        print(f"restauration refusée : {exc}", file=sys.stderr)
        return 2
    print(f"magasin restauré depuis {res['chemin']}")
    print(f"  {res['fichiers']} fichier(s) réécrits")
    return 0


def cmd_backups(args) -> int:
    """Liste les sauvegardes, la plus récente d'abord."""
    from pathlib import Path

    from .backup import lister_sauvegardes
    from .config import get_config

    cfg = get_config()
    repertoire = (Path(args.dir) if args.dir
                  else cfg.data_dir.parent / "sauvegardes")
    trouvailles = lister_sauvegardes(repertoire)
    if not trouvailles:
        print(f"aucune sauvegarde dans {repertoire}")
        return 0
    for entree in trouvailles:
        print(f"  {entree['nom']:44s} {entree['taille']:>10} octets")
    return 0


def cmd_clean(args) -> int:
    from .config import get_config
    from .storage import JobStore

    cfg = get_config()
    store = JobStore(cfg)
    purges = store.cleanup_temp(retention_days=args.days, dry_run=args.dry_run)
    jours = args.days if args.days is not None else cfg.get("security.retention_days", 30)
    if args.dry_run:
        print(f"{len(purges)} job(s) seraient supprimés (rétention {jours} jours).")
    else:
        print(f"{len(purges)} job(s) supprimés (rétention {jours} jours).")
    for jid in purges:
        print(f"  - {jid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
