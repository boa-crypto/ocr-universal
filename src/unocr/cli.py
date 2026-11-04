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
                   help="répertoire de destination (défaut : <data>/../sauvegardes)")
    b.add_argument("--tag", default="", help="étiquette ajoutée au nom du fichier")
    b.add_argument("--keep", type=int, default=5,
                   help="nombre de sauvegardes à conserver (0 = ne pas purger)")
    b.set_defaults(func=cmd_backup)

    r = sub.add_parser("restore", help="restaurer le magasin depuis une sauvegarde")
    r.add_argument("fichier", help="chemin du .zip de sauvegarde")
    r.add_argument("--force", action="store_true",
                   help="autoriser l'écriture sur un magasin non vide")
    r.set_defaults(func=cmd_restore)

    lb = sub.add_parser("backups", help="lister les sauvegardes disponibles")
    lb.add_argument("--dir", default="", help="répertoire des sauvegardes")
    lb.set_defaults(func=cmd_backups)

    pc = sub.add_parser("pieces-check", help="diagnostiquer les justificatifs sans rien modifier")
    pc.add_argument("--data-dir", default="", help="répertoire du magasin à inspecter")
    pc.add_argument("--json", action="store_true", dest="json_output", help="rapport structuré")
    pc.set_defaults(func=cmd_pieces_check)

    args = parser.parse_args(argv)
    return args.func(args)


def cmd_pieces_check(args) -> int:
    from .justificatifs_diagnostic import diagnostiquer_pieces

    if args.data_dir:
        racine = Path(args.data_dir)
    else:
        import os

        from .config import get_config
        cfg = get_config()
        # Ne pas utiliser cfg.data_dir : cette propriété crée le répertoire.
        chemin_env = os.environ.get("UNOCR_DATA_DIR")
        racine = Path(chemin_env).resolve() if chemin_env else cfg.root / cfg.get("jobs.data_dir", "data")
    resultat = diagnostiquer_pieces(racine)
    if args.json_output:
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    else:
        print(f"Justificatifs — {resultat['etat']} — {resultat['pieces_referencees']} pièce(s) référencée(s)")
        print(resultat["limite"])
        for anomalie in resultat["anomalies"]:
            print(f"  {anomalie['categorie']} : {anomalie['cible']} — {anomalie['detail']}")
    return {"conforme": 0, "anomalies": 1, "indisponible": 2}[resultat["etat"]]


def cmd_backup(args) -> int:
    """Crée une sauvegarde horodatée du magasin, puis purge les anciennes."""
    from pathlib import Path

    from .backup import BackupError, creer_sauvegarde, purger_sauvegardes
    from .config import get_config

    cfg = get_config()
    destination = Path(args.out) if args.out else None
    try:
        res = creer_sauvegarde(cfg, destination=destination, etiquette=args.tag)
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
        res = restaurer_sauvegarde(cfg, Path(args.fichier), force=args.force)
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
