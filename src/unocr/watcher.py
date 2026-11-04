"""Dossier surveillé — traitement automatique des documents déposés.

Principe : un thread balaie périodiquement un répertoire ; tout fichier
nouveau y est traité comme le ferait `POST /api/documents`. Un fichier dont
l'empreinte SHA-256 correspond à un document déjà traité n'est **pas**
recalculé (déduplication) et son job existant est simplement renvoyé.

Sécurité :
- le répertoire est résolu et vérifié (`resolve()` + `is_dir()`) avant usage ;
- les fichiers passent par la même validation que l'upload (`security.validate_file`) ;
- un fichier est traité **après** avoir été stabilisé (taille identique sur
  deux balayages), pour ne pas lire une copie en cours ;
- rien n'est exécuté depuis le contenu des documents.
"""
from __future__ import annotations

import hashlib
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from .logging_setup import audit, get_logger
from .models import JobOptions
from .security import SecurityError, sanitize_filename, validate_file

log = get_logger("watcher")

POLL_SECONDS = 5.0
STABILISE_SECONDS = 1.5
MAX_FILE_MB = 50
_SEEN_MAX = 5000


class WatchConfig:
    """Configuration du dossier surveillé (validée par l'appelant)."""

    def __init__(self, enabled: bool = False, path: str = "data/watch",
                 profile: str = "generic", languages: str = "",
                 quality_mode: str = "accurate", poll_seconds: float = POLL_SECONDS,
                 move_done: bool = False):
        self.enabled = enabled
        self.path = path
        self.profile = profile or "generic"
        self.languages = languages
        self.quality_mode = quality_mode if quality_mode in ("fast", "accurate") else "accurate"
        self.poll_seconds = max(2.0, min(600.0, float(poll_seconds)))
        self.move_done = move_done


class FolderWatcher:
    """Balaye un dossier et déclenche le traitement des nouveaux fichiers."""

    def __init__(self, store_getter, run_job, cfg_getter):
        # Accesseurs et non références directes : le store et la config peuvent
        # être remplacés (tests isolés, reconfiguration) sans recréer le surveillant.
        self._store_getter = store_getter
        self.run_job = run_job          # callable(job_id) — même fonction que l'API
        self._cfg_getter = cfg_getter
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seen: dict[str, float] = {}     # empreinte -> dernier traitement
        self._sizes: dict[Path, tuple[int, float]] = {}
        self._cfg = WatchConfig()
        self.processed = 0
        self.skipped = 0
        self.rejected = 0
        self.last_job_id: Optional[str] = None
        self.last_scan: Optional[float] = None
        self.last_error: Optional[str] = None

    @property
    def store(self):
        return self._store_getter()

    @property
    def cfg(self):
        return self._cfg_getter()

    # ------------------------------------------------------------ configuration
    def reset(self) -> None:
        """Oublie les fichiers déjà vus et remet les compteurs à zéro.

        Utile après un changement de dossier surveillé, et pour isoler les tests.
        """
        with self._lock:
            self._seen.clear()
            self._sizes.clear()
            self.processed = 0
            self.skipped = 0
            self.rejected = 0
            self.last_job_id = None
            self.last_error = None

    def configure(self, cfg: WatchConfig) -> None:
        with self._lock:
            was = self._cfg.enabled
            self._cfg = cfg
        if cfg.enabled and not was:
            self.start()
        elif not cfg.enabled and was:
            self.stop()

    def state(self) -> dict:
        with self._lock:
            c = self._cfg
        return {
            "enabled": c.enabled,
            "path": c.path,
            "profile": c.profile,
            "languages": c.languages,
            "quality_mode": c.quality_mode,
            "poll_seconds": c.poll_seconds,
            "running": self._thread is not None and self._thread.is_alive(),
            "last_job_id": self.last_job_id,
            "processed": self.processed,
            "skipped_duplicates": self.skipped,
            "rejected": self.rejected,
            "last_scan": self.last_scan,
            "last_error": self.last_error,
        }

    # ------------------------------------------------------------ cycle de vie
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="unocr-watch",
                                        daemon=True)
        self._thread.start()
        audit(self.cfg.log_dir, "watch_started", path=self._cfg.path)

    def stop(self) -> None:
        self._stop.set()
        audit(self.cfg.log_dir, "watch_stopped")

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.scan_once()
            except Exception as exc:  # le surveillant ne doit jamais s'arrêter
                self.last_error = str(exc)
                log.exception("erreur du dossier surveillé")
            self._stop.wait(self._cfg.poll_seconds)

    # ------------------------------------------------------------ balayage
    def scan_once(self) -> dict:
        """Un passage : traite les fichiers nouveaux et stabilisés."""
        with self._lock:
            c = self._cfg
        self.last_scan = time.time()
        if not c.enabled:
            return {"scanned": False, "reason": "désactivé",
                    "processed": self.processed, "rejected": self.rejected}

        root = Path(c.path).expanduser()
        try:
            root = root.resolve()
        except OSError as exc:
            self.last_error = str(exc)
            return {"scanned": False, "reason": f"chemin invalide : {exc}",
                    "processed": 0, "rejected": 0, "skipped_duplicates": 0}
        if not root.is_dir():
            self.last_error = f"dossier absent : {root}"
            return {"scanned": False, "reason": self.last_error,
                    "processed": 0, "rejected": 0, "skipped_duplicates": 0}

        # Compteurs de CE balayage (les totaux cumulés restent dans state()).
        n_proc = n_rej = n_skip = found = 0
        last_id = None
        for entry in sorted(root.iterdir()):
            if not entry.is_file():
                continue
            if entry.name.startswith("."):
                continue
            if not self._stabilise(entry):
                continue
            found += 1
            issue = self._handle(entry, c)
            if issue == "processed":
                n_proc += 1
                last_id = self.last_job_id
            elif issue == "rejected":
                n_rej += 1
            elif issue == "duplicate":
                n_skip += 1
        return {"scanned": True, "path": str(root), "files_seen": found,
                "processed": n_proc, "rejected": n_rej,
                "skipped_duplicates": n_skip, "last_job_id": last_id,
                "totals": {"processed": self.processed, "rejected": self.rejected,
                           "skipped_duplicates": self.skipped}}

    def _stabilise(self, path: Path) -> bool:
        """Vrai si la taille du fichier est stable depuis le balayage précédent."""
        try:
            size = path.stat().st_size
        except OSError:
            return False
        now = time.time()
        prev = self._sizes.get(path)
        self._sizes[path] = (size, now)
        if prev is None:
            return False
        prev_size, prev_at = prev
        return prev_size == size and (now - prev_at) >= STABILISE_SECONDS

    # ------------------------------------------------------------ traitement
    def _handle(self, path: Path, c: WatchConfig) -> str:
        """Traite un fichier. Renvoie « processed », « duplicate » ou « rejected »."""
        fname = sanitize_filename(path.name)
        try:
            data = path.read_bytes()
        except OSError as exc:
            self.rejected += 1
            self.last_error = f"{fname} : {exc}"
            return "rejected"

        digest = hashlib.sha256(data).hexdigest()
        with self._lock:
            if digest in self._seen:
                self.skipped += 1
                return "duplicate"
            self._seen[digest] = time.time()
            if len(self._seen) > _SEEN_MAX:
                # on garde les empreintes les plus récentes
                for old in sorted(self._seen, key=self._seen.get)[:1000]:
                    del self._seen[old]

        try:
            with tempfile.NamedTemporaryFile(suffix=path.suffix or ".bin",
                                             delete=False) as tf:
                tf.write(data)
                tmp = Path(tf.name)
            try:
                validate_file(
                    tmp, max_size_mb=MAX_FILE_MB,
                    max_zip_uncompressed_mb=self.cfg.get("security.max_zip_uncompressed_mb", 200),
                    max_zip_ratio=self.cfg.get("security.max_zip_ratio", 100))
            finally:
                tmp.unlink(missing_ok=True)
        except SecurityError as exc:
            self.rejected += 1
            self.last_error = f"{fname} refusé : {exc}"
            audit(self.cfg.log_dir, "watch_rejected", filename=fname, reason=str(exc))
            return "rejected"

        existing = self.store.find_by_hash(digest)
        if existing is not None:
            self.skipped += 1
            audit(self.cfg.log_dir, "watch_deduped", filename=fname,
                  job_id=existing.id, source="watch")
            self._relocate(path, c, existing.id)
            return "duplicate"

        langs = [ln.strip() for ln in c.languages.split(",") if ln.strip()]
        options = JobOptions(languages=langs, profile=c.profile,
                             quality_mode=c.quality_mode)
        job = self.store.create_job(fname, data, options)
        self.last_job_id = job.id
        audit(self.cfg.log_dir, "watch_processed", filename=fname, job_id=job.id,
              profile=c.profile)
        self.processed += 1
        try:
            self.run_job(job.id)
        except Exception as exc:  # le job reste consultable via l'API
            self.last_error = f"{fname} : {exc}"
            log.exception("traitement du fichier surveillé en échec")
        self._relocate(path, c, job.id)
        return "processed"

    def _relocate(self, path: Path, c: WatchConfig, job_id: str) -> None:
        """Option : range le fichier traité dans un sous-dossier `done/`."""
        if not c.move_done:
            return
        try:
            done = path.parent / "done"
            done.mkdir(exist_ok=True)
            path.rename(done / f"{path.stem}__{job_id[:12]}{path.suffix}")
        except OSError as exc:
            self.last_error = f"classement impossible : {exc}"
