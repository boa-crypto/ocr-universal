"""Rétention et reprise enfin câblées (vague 5 de l'audit).

**Pourquoi ce fichier.** Deux mécanismes existaient mais n'étaient appelés par
personne :

- `JobStore.cleanup_temp()` — `security.retention_days` (30 jours) ne
  déclenchait donc aucune purge, et `data/jobs` grossissait sans limite.
- `JobStore.retryable_jobs()` — un traitement tué net restait `processing`
  pour toujours, sans qu'aucune route ni commande permette de le voir.

Les deux sont désormais exposés (`POST /api/admin/cleanup`, `GET /api/jobs/stale`,
`unocr clean`) et testés ici.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from unocr.api import app
from unocr.models import Job, JobStatus


@pytest.fixture()
def client(tmp_cfg, fixtures_dir):
    with TestClient(app) as c:
        yield c


def _evenements_audit(log_dir) -> list[dict]:
    """Lit le journal d'audit (JSONL) — pas de read_audit dans logging_setup."""
    chemin = log_dir / "audit.log"
    if not chemin.is_file():
        return []
    lignes = [ln for ln in chemin.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lignes]


# ───────────────────────────── rétention ─────────────────────────────────────

def _job_termine(store, age_days: float) -> Job:
    """Crée un job DONE puis le viellit artificiellement.

    `store.update()` remet `updated_at` à maintenant : il faut donc réécrire le
    fichier après coup pour simuler un job ancien.
    """
    job = store.create_job("doc.pdf", b"%PDF-1.4 faux\n")
    job.status = JobStatus.DONE
    store.update(job)
    chemin = store._job_path(job.id)
    data = json.loads(chemin.read_text(encoding="utf-8"))
    data["updated_at"] = time.time() - age_days * 86400
    chemin.write_text(json.dumps(data), encoding="utf-8")
    return store.get(job.id)


def test_cleanup_supprime_les_jobs_anciens(tmp_cfg) -> None:
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    ancien = _job_termine(store, age_days=40)      # au-delà de 30 jours
    recent = _job_termine(store, age_days=2)       # dans la rétention
    purges = store.cleanup_temp()
    assert ancien.id in purges, "un job de 40 jours aurait dû être purgé"
    assert recent.id not in purges, "un job de 2 jours ne doit pas être purgé"
    assert store.get(ancien.id) is None
    assert store.get(recent.id) is not None


def test_cleanup_dry_run_ne_touche_a_rien(tmp_cfg) -> None:
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    ancien = _job_termine(store, age_days=90)
    purges = store.cleanup_temp(dry_run=True)
    assert purges == [ancien.id], "le dry-run doit annoncer ce qui serait purgé"
    assert store.get(ancien.id) is not None, "le dry-run ne doit rien supprimer"


def test_cleanup_respecte_le_parametre_days(tmp_cfg) -> None:
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    moyen = _job_termine(store, age_days=10)
    vieux = _job_termine(store, age_days=40)

    # rétention 30 jours : seul le job de 40 jours dépasse
    purges = store.cleanup_temp(retention_days=30)
    assert purges == [vieux.id]
    assert store.get(moyen.id) is not None

    # rétention ramenée à 5 jours : le job de 10 jours devient purgéable
    purges = store.cleanup_temp(retention_days=5)
    assert purges == [moyen.id]
    assert store.get(moyen.id) is None


def test_cleanup_laisse_un_evenement_daudit(tmp_cfg) -> None:
    """Purger ne doit pas effacer la trace : l'audit subsiste."""
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    ancien = _job_termine(store, age_days=60)
    store.cleanup_temp()
    evenements = _evenements_audit(tmp_cfg.log_dir)
    assert any(e.get("event") == "jobs_purged" for e in evenements), (
        "aucun événement de purge consigné"
    )
    assert any(e.get("event") == "job_deleted" and e.get("job_id") == ancien.id
               for e in evenements), (
        "la suppression du job doit rester traçable dans l'audit"
    )


# ───────────────────────────── reprise ───────────────────────────────────────

def _job_vieilli(store, age_seconds: float, status: JobStatus) -> Job:
    job = store.create_job("doc.pdf", b"%PDF-1.4 faux\n")
    job.status = status
    store.update(job)
    chemin = store._job_path(job.id)
    data = json.loads(chemin.read_text(encoding="utf-8"))
    data["updated_at"] = time.time() - age_seconds
    chemin.write_text(json.dumps(data), encoding="utf-8")
    return store.get(job.id)


def test_retryable_detecte_les_jobs_bloques(tmp_cfg) -> None:
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    bloque = _job_vieilli(store, 3600, JobStatus.PROCESSING)      # 1 h figé
    vivant = _job_vieilli(store, 0, JobStatus.PROCESSING)         # actif
    file_attente = _job_vieilli(store, 7200, JobStatus.QUEUED)    # 2 h figé

    trouves = {j.id for j in store.retryable_jobs()}
    assert bloque.id in trouves, "un processing figé depuis 1 h doit être détecté"
    assert file_attente.id in trouves, "un queued figé depuis 2 h doit être détecté"
    assert vivant.id not in trouves, "un processing actif ne doit pas être proposé"


def test_api_expose_les_jobs_bloques(client, tmp_cfg) -> None:
    from unocr import api
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    bloque = _job_vieilli(store, 3600, JobStatus.PROCESSING)

    r = client.get("/api/jobs/stale")
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["count"] == 1
    assert corps["jobs"][0]["id"] == bloque.id
    assert api.store is not None


def test_api_cleanup_dry_run_puis_reel(client, tmp_cfg) -> None:
    from unocr.storage import JobStore

    store = JobStore(tmp_cfg)
    ancien = _job_termine(store, age_days=90)

    sec = client.post("/api/admin/cleanup", params={"dry_run": "true"})
    assert sec.status_code == 200, sec.text
    corps = sec.json()
    assert corps["purged"] == 1 and corps["dry_run"] is True
    assert store.get(ancien.id) is not None, "le dry-run ne doit rien supprimer"

    reel = client.post("/api/admin/cleanup", params={"days": 30})
    assert reel.status_code == 200, reel.text
    assert reel.json()["purged"] == 1
    assert store.get(ancien.id) is None


def test_api_stale_est_une_route_littérale(client) -> None:
    """`/api/jobs/stale` ne doit pas être capturé par `/api/jobs/{job_id}`."""
    r = client.get("/api/jobs/stale")
    assert r.status_code == 200, (
        "la route littérale est capturée par la route paramétrée : "
        "déclarer /api/jobs/stale avant /api/jobs/{job_id}"
    )
    assert "count" in r.json()
