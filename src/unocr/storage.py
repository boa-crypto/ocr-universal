"""Stockage : jobs (état persistant, reprise), artefacts, journal d'audit.

Un job est un répertoire : original conservé intact, artefacts de travail,
résultat JSON, exports. Les écritures JSON sont atomiques (temp + rename).
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from itertools import count
from pathlib import Path

from .config import Config
from .logging_setup import audit, get_logger
from .models import Job, JobOptions, JobStatus

log = get_logger("storage")

_LOCK = threading.Lock()

#: Compteur d'unicité pour les noms de fichiers temporaires.
_COMPTEUR_TMP = count()

#: Nombre de tentatives pour remplacer un fichier sur Windows, où un
#: lecteur concurrent peut bloquer le remplacement pendant un instant.
_TENTATIVES_REMPLACEMENT = 5


def _atomic_write_json(path: Path, data: dict) -> None:
    """Écrit un JSON de façon atomique, sans collision entre threads.

    Le nom du fichier temporaire doit être **unique par écriture** : avec un
    nom fixe (`cible.tmp`), deux écritures concurrentes de la même cible
    partagent le même temporaire. La première qui termine le remplace, et la
    seconde échoue avec « accès refusé » (Windows) ou corrompt la cible.

    On utilise donc l'identifiant du thread et un compteur, puis `os.replace`
    qui est atomique sur les deux plateformes.
    """
    unique = f"{os.getpid()}-{threading.get_ident()}-{next(_COMPTEUR_TMP)}"
    tmp = path.with_suffix(path.suffix + f".{unique}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
        _remplace_atomique(tmp, path)
    finally:
        # en cas d'échec, on ne laisse pas de temporaire derrière soi
        try:
            tmp.unlink(missing_ok=True)
        except OSError:      # pragma: no cover - course avec un autre écriture
            pass


def _remplace_atomique(tmp: Path, cible: Path) -> None:
    """Remplace `cible` par `tmp`, en réessayant si Windows refuse.

    Sur Windows, `os.replace` échoue avec « accès refusé » si un autre
    lecteur tient le fichier cible ouvert ( antivirus, indexeur, ou un
    `read_text` concurrent ). L'écriture est atomique côté lecteur : le
    contenu est soit l'ancien, soit le nouveau, jamais un mélange.
    """
    for tentative in range(_TENTATIVES_REMPLACEMENT):
        try:
            os.replace(tmp, cible)
            return
        except PermissionError:
            if tentative == _TENTATIVES_REMPLACEMENT - 1:
                raise
            # brefs délais : le lecteur concurrent finit par libérer le
            # fichier. Assez courts pour ne pas pénaliser le cas normal.
            time.sleep(0.01 * (tentative + 1))


class JobStore:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = cfg.data_dir / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------- chemins
    def job_dir(self, job_id: str) -> Path:
        return self.root / job_id

    def original_dir(self, job_id: str) -> Path:
        p = self.job_dir(job_id) / "original"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def work_dir(self, job_id: str) -> Path:
        p = self.job_dir(job_id) / "work"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def export_dir(self, job_id: str) -> Path:
        p = self.job_dir(job_id) / "exports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------- cycle de vie
    def create_job(self, filename: str, file_bytes: bytes,
                   options: JobOptions | None = None) -> Job:
        import hashlib

        from .security import sanitize_filename
        job = Job(filename=filename, options=options or JobOptions())
        job.file_hash = hashlib.sha256(file_bytes).hexdigest()
        with _LOCK:
            jd = self.job_dir(job.id)
            jd.mkdir(parents=True, exist_ok=True)
            from .security import sanitize_filename
            dest = self.original_dir(job.id) / sanitize_filename(filename)
            dest.write_bytes(file_bytes)
            job.attempts = 0
            self._write_job(job)
        audit(self.cfg.log_dir, "job_created", job_id=job.id, filename=filename,
              size=len(file_bytes), profile=job.options.profile)
        return job

    def _job_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def _write_job(self, job: Job) -> None:
        job.updated_at = time.time()
        _atomic_write_json(self._job_path(job.id), job.model_dump(mode="json"))

    def update(self, job: Job) -> None:
        with _LOCK:
            self._write_job(job)

    def get(self, job_id: str) -> Job | None:
        p = self._job_path(job_id)
        if not p.is_file():
            return None
        try:
            return Job.model_validate(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            log.exception("job.json corrompu: %s", job_id)
            return None

    def list_jobs(self, limit: int = 100, offset: int = 0) -> list[Job]:
        jobs: list[Job] = []
        if not self.root.is_dir():
            return jobs
        for d in self.root.iterdir():
            if d.is_dir() and (d / "job.json").is_file():
                j = self.get(d.name)
                if j:
                    jobs.append(j)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[offset:offset + limit]

    def find_by_hash(self, file_hash: str) -> Job | None:
        """Job DONE portant la même empreinte SHA-256 (déduplication).

        Permet de rendre un résultat déjà calculé sans relancer l'OCR.
        """
        if not file_hash:
            return None
        for j in self.list_jobs(limit=1000):
            if j.file_hash == file_hash and j.status.value == "done":
                return j
        return None

    def save_result(self, job_id: str, result_json: dict) -> Path:
        path = self.job_dir(job_id) / "result.json"
        _atomic_write_json(path, result_json)
        return path

    def load_result(self, job_id: str) -> dict | None:
        p = self.job_dir(job_id) / "result.json"
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def original_path(self, job_id: str) -> Path | None:
        od = self.original_dir(job_id)
        files = [f for f in od.iterdir() if f.is_file()]
        return files[0] if files else None

    def delete_job(self, job_id: str, keep_audit: bool = True) -> bool:
        """Suppression contrôlée : artefacts effacés, événement journalisé."""
        jd = self.job_dir(job_id)
        if not jd.is_dir():
            return False
        shutil.rmtree(jd)
        audit(self.cfg.log_dir, "job_deleted", job_id=job_id, keep_audit=keep_audit)
        return True

    def retryable_jobs(self) -> list[Job]:
        """Jobs interrompus (processing sans mise à jour récente) → reprise."""
        stale: list[Job] = []
        for j in self.list_jobs(limit=1000):
            if j.status == JobStatus.PROCESSING and time.time() - j.updated_at > 600:
                stale.append(j)
            elif j.status == JobStatus.QUEUED and time.time() - j.updated_at > 3600:
                stale.append(j)
        return stale

    def cleanup_temp(self, retention_days: int | None = None,
                     dry_run: bool = False) -> list[str]:
        """Purge les jobs terminés au-delà de la rétention.

        **Pourquoi cette méthode existait sans être appelée.** Elle était définie
        mais jamais utilisée : `security.retention_days` (30 jours par défaut)
        ne déclenchait donc rien, et `data/jobs` grossissait sans limite. Elle
        ne supprimait de surcroît que le sous-répertoire `work/`, jamais le job.

        Elle supprime maintenant le répertoire du job **en conservant
        l'événement d'audit** (`delete_job(keep_audit=True)`), conformément à la
        règle « la désactivation ne supprime ni l'historique ni les données
        déjà traitées ». `dry_run=True` renvoie ce qui serait supprimé sans
        toucher au disque.
        """
        jours = retention_days
        if jours is None:
            jours = self.cfg.get("security.retention_days", 30)
        cutoff = time.time() - float(jours) * 86400
        purges: list[str] = []
        for j in self.list_jobs(limit=10000):
            if j.status == JobStatus.DONE and j.updated_at < cutoff:
                purges.append(j.id)
                if not dry_run:
                    self.delete_job(j.id, keep_audit=True)
        if purges:
            audit(self.cfg.log_dir, "jobs_purged", count=len(purges),
                  retention_days=jours, dry_run=dry_run)
        return purges
