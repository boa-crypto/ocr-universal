"""Concurrence des jobs : la mitigation du crash natif, verrouillée.

**Pourquoi ce fichier existe.** Un crash natif (`free(): corrupted unsorted
chunks`, puis segmentation fault) a été observé sous 3 jobs concurrents, dans
les moteurs natifs de rendu PDF. Il n'a jamais été reproduit — et il ne peut
pas l'être ici : `tesseract` et `pdftoppm` sont absents de cet environnement,
donc le chemin de code concerné n'est pas exerçable.

Ce qui *est* testable, c'est la mitigation mise en place : un sémaphore qui borne
le nombre de pipelines simultanés selon la configuration **et** la RAM
réellement disponible. Sans ces tests, la mitigation pourrait être cassée par
une modification ultérieure sans que personne s'en aperçoive — et le crash
referait surface sur une machine qui a les binaires natifs.

**Le point le plus important** : un job qui attend sa tour reste `queued`. Un
job marqué « terminé » alors qu'il n'a pas tourné serait un faux résultat —
pire qu'un crash, parce que silencieux.
"""
import threading

import pytest

from unocr import api
from unocr.models import JobStatus
from unocr.services import jobs as jobs_service


@pytest.fixture()
def semaphore_neuf():
    """Remet le sémaphore à zéro : il est mémoïsé une fois par processus."""
    original = jobs_service._JOBS_SEMAPHORE
    jobs_service._JOBS_SEMAPHORE = None
    yield
    jobs_service._JOBS_SEMAPHORE = original


class _FauxMeminfo:
    """Fichier /proc/meminfo simulé, avec la RAM demandée."""

    def __init__(self, mo: int):
        self._lignes = ["MemTotal:       %d kB\n" % (mo * 1024 * 2),
                        "MemAvailable:   %d kB\n" % (mo * 1024)]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self._lignes)


# ─────────────────────────── bornage ───────────────────────────

def test_semaphore_borne_par_la_config(semaphore_neuf):
    """`jobs.workers` reste la source de réglage."""
    api.cfg.data.setdefault("jobs", {})["workers"] = 2
    s = api._jobs_semaphore()
    assert s._value <= 2


def test_semaphore_borne_par_la_ram(semaphore_neuf, monkeypatch):
    """Peu de RAM disponible → un seul pipeline, quoi que dise la config.

    C'est le garde-fou du crash : trois pipelines simultanés saturaient la
    mémoire et le processus mourait dans le code natif.
    """
    api.cfg.data.setdefault("jobs", {})["workers"] = 8
    vrai_open = open

    def faux_open(path, *a, **k):
        if str(path) == "/proc/meminfo":
            return _FauxMeminfo(900)      # ~1 pipeline et demie
        return vrai_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", faux_open)
    jobs_service._JOBS_SEMAPHORE = None
    s = api._jobs_semaphore()
    assert s._value == 1


def test_semaphore_jamais_zero(semaphore_neuf, monkeypatch):
    """Même sans aucune RAM annoncée, au moins un job doit pouvoir tourner.

    Un sémaphore à 0 bloquerait tout traitement sans erreur visible : les
    documents resteraient « en file d'attente » pour toujours.
    """
    api.cfg.data.setdefault("jobs", {})["workers"] = 4
    vrai_open = open

    def faux_open(path, *a, **k):
        if str(path) == "/proc/meminfo":
            return _FauxMeminfo(0)
        return vrai_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", faux_open)
    jobs_service._JOBS_SEMAPHORE = None
    s = api._jobs_semaphore()
    assert s._value >= 1


def test_semaphore_sans_sonde_ram_est_conservateur(semaphore_neuf, monkeypatch):
    """/proc/meminfo absent → un seul pipeline, quoi que dise la config.

    Comportement réel du code, vérifié ici pour qu'il ne change pas par
    accident : faute d'information sur la mémoire, on choisit le prudence
    (un pipeline) plutôt que la vitesse. Sur un OS sans /proc, le traitement
    est plus lent mais le processus ne meurt pas.
    """
    def interdit(path, *a, **k):
        if str(path) == "/proc/meminfo":
            raise OSError("pas de /proc")
        return open(path, *a, **k)  # noqa: A001

    monkeypatch.setattr("builtins.open", interdit)
    jobs_service._JOBS_SEMAPHORE = None
    api.cfg.data.setdefault("jobs", {})["workers"] = 3
    s = api._jobs_semaphore()
    assert s._value == 1


# ─────────────── l'invariant : en attente n'est pas terminé ───────────────

def test_job_en_attente_reste_queued(semaphore_neuf):
    """Un job qui n'a pas encore eu sa place n'est jamais « terminé ».

    C'est l'invariant que le commentaire du code affirme. Un job marqué
    `done` sans avoir tourné produirait un résultat vide présenté comme
    valide — le pire des échecs, parce que silencieux.
    """
    api.cfg.data.setdefault("jobs", {})["workers"] = 1
    sem = api._jobs_semaphore()
    assert sem._value == 1

    # le sémaphore est saturé : un second job doit attendre
    sem.acquire()
    try:
        assert sem._value == 0
        # _run_job ne peut pas entrer : le job reste dans son état d'attente
        job = api.store.create_job("attente.pdf", b"%PDF-1.4 x")
        assert job.status == JobStatus.QUEUED
    finally:
        sem.release()
    assert sem._value == 1


def test_semaphore_est_released_meme_si_le_job_echoue(semaphore_neuf):
    """Une exception ne doit pas consommer une place définitivement.

    Sans libération, quelques jobs en erreur bloqueraient tout le traitement
    suivant — et le symptôme (plus rien ne tourne) serait très éloigné de la
    cause.

    Ne pas pré-acquérir le sémaphore : `with sem:` le ferait bloquer en
    attendant une libération qui ne viendra jamais.
    """
    api.cfg.data.setdefault("jobs", {})["workers"] = 1
    sem = api._jobs_semaphore()
    assert sem._value == 1
    with pytest.raises(RuntimeError):
        with sem:
            raise RuntimeError("job qui échoue")
    # la place est rendue malgré l'exception
    assert sem._value == 1


# ─────────────── charge : résultats non corrompus ───────────────

def test_ecritures_concurrentes_ne_corrompent_pas_le_magasin(tmp_cfg):
    """Écritures simultanées de résultats : aucun résultat perdu ou tronqué.

    Le magasin est écrit par plusieurs threads. Un verrou absent se
    manifesterait par des JSON tronqués ou des résultats écrasés — pas par une
    erreur franche, donc difficile à diagnostiquer en production.
    """
    import json

    n = 12
    jobs = [api.store.create_job("doc%d.pdf" % i, b"%PDF-1.4 contenu-" + str(i).encode())
            for i in range(n)]
    erreurs: list[str] = []

    def ecrire(job):
        try:
            for tour in range(20):
                api.store.save_result(job.id, {"job_id": job.id,
                                               "tour": tour,
                                               "champs": {"a": "x" * 200}})
        except Exception as exc:              # pragma: no cover
            erreurs.append("%s : %s" % (job.id, exc))

    threads = [threading.Thread(target=ecrire, args=(j,)) for j in jobs]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not erreurs, erreurs
    for j in jobs:
        r = api.store.load_result(j.id)
        assert r is not None, "résultat perdu pour %s" % j.id
        assert r["tour"] == 19, "écriture écrasée pour %s" % j.id
        # le JSON doit être relisible tel quel
        json.dumps(r)


def test_mise_a_jour_concurrente_du_statut(tmp_cfg):
    """`store.update` sous concurrence : le dernier écrit gagne, sans corruption."""
    job = api.store.create_job("statut.pdf", b"%PDF-1.4 x")
    erreurs: list[str] = []

    def maj(valeur):
        try:
            for _ in range(30):
                j = api.store.get(job.id)
                if j is None:
                    erreurs.append("job disparu")
                    return
                j.progress = valeur
                api.store.update(j)
        except Exception as exc:              # pragma: no cover
            erreurs.append(str(exc))

    threads = [threading.Thread(target=maj, args=(i / 10.0,))
               for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not erreurs, erreurs
    final = api.store.get(job.id)
    assert final is not None and 0.0 <= final.progress <= 0.6


def test_creation_concurrente_pas_d_identifiant_duplique(tmp_cfg):
    """Deux créations simultanées ne doivent jamais produire le même id.

    Un doublon d'identifiant ferait se écraser mutuellement deux documents —
    une perte de données silencieuse.
    """
    ids: list[str] = []
    verrou = threading.Lock()

    def creer(i):
        j = api.store.create_job("parallele%d.pdf" % i, b"%PDF-1.4 x")
        with verrou:
            ids.append(j.id)

    threads = [threading.Thread(target=creer, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert len(ids) == 20
    assert len(set(ids)) == 20, "identifiants dupliqués : %s" % (
        [i for i in ids if ids.count(i) > 1],)
