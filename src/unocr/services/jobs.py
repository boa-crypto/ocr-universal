"""Services de gestion des jobs et de la concurrence."""
from __future__ import annotations

import threading
from typing import Any, Optional

_JOBS_SEMAPHORE: Optional[threading.Semaphore] = None
_JOBS_SEMAPHORE_LOCK = threading.Lock()


def jobs_semaphore(cfg: Any) -> threading.Semaphore:
    """Sémaphore borné, calculé une fois à partir de la config et de la RAM."""
    global _JOBS_SEMAPHORE
    with _JOBS_SEMAPHORE_LOCK:
        if _JOBS_SEMAPHORE is None:
            voulu = int(cfg.get("jobs.workers", 1) or 1)
            try:
                with open("/proc/meminfo", encoding="utf-8") as fh:
                    dispo = 0
                    for ligne in fh:
                        if ligne.startswith("MemAvailable:"):
                            dispo = int(ligne.split()[1]) // 1024
                            break
            except OSError:
                dispo = 0
            par_memoire = max(1, dispo // 600) if dispo else 1
            limite = max(1, min(voulu, par_memoire))
            _JOBS_SEMAPHORE = threading.Semaphore(limite)
        return _JOBS_SEMAPHORE
