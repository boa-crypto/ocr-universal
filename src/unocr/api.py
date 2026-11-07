"""API REST UniOCR (FastAPI) — upload, traitement async, résultats, exports, validation.

Documentation OpenAPI automatique : /docs (Swagger) et /openapi.json.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .calibration import Calibration
from .config import get_config
from .crypto_store import SALT_LEN, CryptoStore
from .exporters import export_all, export_xlsx
from .logging_setup import audit, audit_obligatoire, get_logger, setup_logging
from .models import FieldStatus, JobOptions, JobStatus, ValueOrigin
from .observabilite import HEADER_CORRELATION, CompteurDebit, nouvel_identifiant
from .ocr_engines import EngineRegistry
from .pipeline import Pipeline
from .profiles import (
    Profile,
    apply_profile,
    load_all_profiles,
)
from .rbac import (
    ADMINISTRATEUR,
    LECTEUR,
    OPERATEUR,
    ROLES,
    SUPERVISEUR,
    TOUS,
    RBACError,
    RegistreRBAC,
    Utilisateur,
)
from .resources import snapshot
from .routes.clients import router as clients_router
from .routes.connaissements import router as connaissements_router
from .routes.conteneurs import router as conteneurs_router
from .routes.controle_doc import router as controle_doc_router
from .routes.customs_review import creer_router_revue
from .routes.dashboard import router as dashboard_router
from .routes.declarations import router as declarations_router
from .routes.documents_ocr import router as documents_ocr_router
from .routes.expeditions import router as expeditions_router
from .routes.fournisseurs import router as fournisseurs_router
from .routes.frais import router as frais_router
from .routes.historique import router as historique_router
from .routes.navires import router as navires_router
from .routes.parametres import router as parametres_router
from .routes.profiles import router as profiles_router
from .routes.rbac_roles import router as rbac_roles_router
from .routes.referentiels import router as referentiels_router
from .routes.reglementation import router as reglementation_router
from .routes.statistiques import router as statistiques_router
from .routes.system import router as system_router
from .routes.terminal import router as terminal_router
from .routes.transit import router as transit_router
from .routes.transport import router as transport_router
from .routes.watch import router as watch_router
from .routes.workflow import router as workflow_router
from .security import sanitize_for_csv
from .services.jobs import jobs_semaphore
from .services.security import (
    _configured_allowed_hosts as _configured_allowed_hosts_service,
)
from .services.security import (
    _configured_cors_origins as _configured_cors_origins_service,
)
from .services.security import (
    configure_security_middleware,
)
from .services.security import (
    default_security_headers as _default_security_headers_service,
)
from .storage import JobStore

log = get_logger("api")

app = FastAPI(
    title="UniOCR API",
    version="0.1.0",
    description=(
        "Moteur OCR universel : extraction de texte, structure, champs, tableaux, "
        "scores de confiance, anomalies et exports (JSON/CSV/XLSX/XML/TXT/PDF)."
    ),
)

cfg = get_config()
setup_logging(cfg.log_dir)
store = JobStore(cfg)
registry = EngineRegistry()
app.state.registry = registry
app.state.cfg = cfg
app.state.store = store
_processing_lock = threading.Lock()

app.include_router(system_router)
app.include_router(profiles_router)
app.include_router(watch_router)
app.include_router(transit_router)
app.include_router(workflow_router)
app.include_router(clients_router)
app.include_router(fournisseurs_router)
app.include_router(navires_router)
app.include_router(conteneurs_router)
app.include_router(expeditions_router)
app.include_router(connaissements_router)
app.include_router(declarations_router)
app.include_router(frais_router)
app.include_router(terminal_router)
app.include_router(transport_router)
app.include_router(rbac_roles_router)
app.include_router(parametres_router)
app.include_router(historique_router)
app.include_router(statistiques_router)
app.include_router(documents_ocr_router)
app.include_router(controle_doc_router)
app.include_router(dashboard_router)
app.include_router(reglementation_router)
app.include_router(referentiels_router)
app.mount("/web", StaticFiles(directory=str(cfg.web_dir)), name="static")


def _configured_cors_origins() -> list[str]:
    return _configured_cors_origins_service(cfg)


def _configured_allowed_hosts() -> list[str]:
    return _configured_allowed_hosts_service(cfg)


def _default_security_headers() -> dict[str, str]:
    return _default_security_headers_service(cfg)

# ─────────────────────── Connecteur Hub ───────────────────────
from .connectors.contract import OPERATIONAL_STATES, ConnectorCapability, NotSupportedError  # noqa: E402
from .connectors.forms import FormDefinition, FormField, FormStore  # noqa: E402
from .connectors.hub import ConnectorHub  # noqa: E402
from .connectors.transmission import TransmissionEngine  # noqa: E402

_hub_root = cfg.data_dir / "connectors"
connector_hub = ConnectorHub(_hub_root, cfg.log_dir)
transmissions = TransmissionEngine(_hub_root, cfg.log_dir)
form_store = FormStore(_hub_root / "forms")

def _hsts_enabled() -> bool:
    """HSTS activé uniquement pour les déploiements HTTPS ou configurés."""
    return bool(cfg.get("api.hsts", False))


# CORS / host : l'UI est servie localement, sans ouvrir le service à n'importe
# quelle origine ni à n'importe quel host. Les déploiements distants doivent
# explicitement préciser les autorités autorisées.
configure_security_middleware(app, cfg)

SUPPORTED_EXPORTS = {"txt", "json", "csv", "xlsx", "xml", "pdf"}


# ─────────────────────── Booléens de formulaire ───────────────────────
#
# Piège FastAPI : une déclaration `flag: bool = Form(True)` **n'aboutit pas**
# à `True` quand le champ est absent du multipart. FastAPI applique
# `infer_false_if_missing` et renvoie `False` pour tout booléen absent — la
# valeur par défaut déclarée est ignorée. Concrètement, un client qui
# n'envoie que le fichier obtenait un traitement **sans** extraction de
# champs, sans tableaux et sans codes-barres, sans aucun signal d'erreur.
#
# On passe donc par un parseur explicite : la valeur par défaut n'est
# appliquée que si le champ est réellement absent, et une valeur transmise
# est lue sans ambiguïté.
_VRAIS = {"1", "true", "yes", "on", "oui", "vrai"}
_FAUX = {"0", "false", "no", "off", "non", "faux", ""}


def _form_bool(raw: str | None, default: bool = True) -> bool:
    """Lit un booléen de formulaire, en appliquant `default` si absent.

    Les valeurs `on`/`off` (natives des cases à cocher HTML) et `1`/`0`
    sont acceptées ; une valeur inconnue lève une erreur explicite plutôt
    que d'être silencieusement interprétée.
    """
    if raw is None:
        return default
    val = str(raw).strip().lower()
    if val in _VRAIS:
        return True
    if val in _FAUX:
        return False
    raise HTTPException(422, f"valeur booléenne invalide : {raw!r}")


# Nombre de pipelines autorisés à tourner en même temps. `jobs.workers` reste
# la source de réglage, mais il est borné par la mémoire réellement
# disponible : sur une machine contrainte, trois pipelines simultanés
# rendaient le processus en *segmentation fault* (moteurs natifs de rendu
# PDF). Le verrou garantit qu'un job attend son tour au lieu de tuer le
# serveur — et son statut reste `queued`, donc jamais « terminé » à tort.
def _jobs_semaphore() -> threading.Semaphore:
    """Sémaphore borné, calculé une fois à partir de la config et de la RAM."""
    sem = jobs_semaphore(cfg)
    log.info("jobs concurrents bornés à %s", sem._value if hasattr(sem, "_value") else "n/a")
    return sem


def _run_job(job_id: str) -> None:
    """Traitement d'un job dans un thread (asynchrone côté API)."""
    job = store.get(job_id)
    if job is None:
        return
    # Un job en file d'attente n'est jamais « terminé » : il reste `queued`
    # jusqu'à ce qu'une place se libère.
    with _jobs_semaphore():
        _traite_job(job_id, job)


def _traite_job(job_id: str, job) -> None:
    job.status = JobStatus.PROCESSING
    job.attempts += 1
    store.update(job)
    try:
        src = store.original_path(job_id)
        if src is None:
            raise FileNotFoundError("fichier original absent")

        def progress(stage: str, frac: float) -> None:
            j = store.get(job_id)
            if j:
                j.stage = stage
                j.progress = round(frac, 3)
                store.update(j)

        # Décisions humaines du passage précédent : elles doivent survivre à
        # une reprise. Sans cela, un `retry` effaçait les validations déjà
        # portées sur les champs (règle du prompt : « reprise après erreur
        # sans perte des originaux ni des corrections humaines »).
        decisions_humaines: dict[str, dict] = {}
        precedent = store.load_result(job_id)
        if precedent:
            for nom, fv in (precedent.get("fields") or {}).items():
                statut = fv.get("status")
                if statut in ("validated", "corrected") or fv.get("confirmed_value") \
                        or fv.get("corrected_value"):
                    decisions_humaines[nom] = {
                        "confirmed_value": fv.get("confirmed_value"),
                        "corrected_value": fv.get("corrected_value"),
                        "status": statut,
                        "value_origin": fv.get("value_origin"),
                    }

        pipeline = Pipeline(cfg, registry)
        result = pipeline.process_file(src, job.options, progress=progress,
                                        job_id=job_id)

        # réapplication des décisions humaines, avec les valeurs réellement
        # retenues pour que la traçabilité dise ce qui a été restauré
        restaures = []
        for nom, dec in decisions_humaines.items():
            fv = result.fields.get(nom)
            if fv is None:
                continue
            if dec["confirmed_value"] is not None:
                fv.confirmed_value = dec["confirmed_value"]
                fv.value_origin = ValueOrigin.CONFIRMED
                fv.status = FieldStatus.VALIDATED
                restaures.append(nom)
            if dec["corrected_value"] is not None:
                fv.corrected_value = dec["corrected_value"]
                # l'origine doit etre restauree aussi : sans cela une
                # reprise faisait disparaitre la trace de la decision
                # humaine, et la valeur corrigee s'affichait comme
                # sortie du moteur
                fv.value_origin = ValueOrigin.CORRECTED
                restaures.append(nom)
            elif dec["status"] == "validated":
                fv.status = FieldStatus.VALIDATED
        if restaures:
            audit(cfg.log_dir, "field_decisions_restored", job_id=job_id,
                  attempt=job.attempts, fields=sorted(set(restaures)))

        # exports
        export_dir = store.export_dir(job_id)
        fmts = [f for f in job.options.export_formats if f in SUPPORTED_EXPORTS] or ["json", "txt"]
        from .ingest import load_document
        page_images = {}
        try:
            loaded = load_document(src, dpi=cfg.get("render_dpi", 200))
            for lp in loaded.pages:
                if lp.image is not None:
                    page_images[lp.page_num] = lp.image
        except Exception:
            log.warning("images de page indisponibles pour export PDF")
        result.exports = export_all(result, export_dir, fmts,
                                    page_images=page_images or None)

        store.save_result(job_id, result.model_dump(mode="json"))
        job = store.get(job_id)
        if job:
            job.status = JobStatus.DONE
            job.result_id = result.id
            job.progress = 1.0
            job.stage = "done"
            store.update(job)
        audit(cfg.log_dir, "job_done", job_id=job_id, pages=len(result.pages),
              mean_confidence=result.quality.mean_global_confidence)
    except Exception as exc:
        log.exception("job %s en échec", job_id)
        job = store.get(job_id)
        if job:
            job.status = JobStatus.ERROR
            job.error = f"{type(exc).__name__}: {exc}"
            store.update(job)
        audit(cfg.log_dir, "job_error", job_id=job_id, error=str(exc))


# Dossier surveillé : instancié après _run_job (référence nécessaire).
from .watcher import FolderWatcher  # noqa: E402

_watch = FolderWatcher(lambda: store, _run_job, lambda: cfg)
app.state.watcher = _watch

# ─────────────────────── authentification optionnelle ───────────────────────
# Désactivée par défaut : UniOCR reste un outil local sans configuration.
# UNIOCR_TOKEN active un jeton unique comparé à temps constant, exigé sur
# toutes les routes /api/*. / et /docs restent ouverts (pas de donnée).
_AUTH_TOKEN = os.environ.get("UNIOCR_TOKEN", "").strip()
#: routes dispensées de la limitation de débit : la santé et la
#: coquille web ne doivent jamais être ralenties par un abus d'API.
_DEBIT_EXEMPT = {"/api/health", "/api/stats"}

# ─────────────────── rôles et cloisonnement par dossier ───────────────────
# Le jeton unique répond à « est-on autorisé ? » mais pas à « à quoi ? ».
# `data/rbac.json` ajoute les rôles et le périmètre par dossier. S'il est
# absent, le registre est inactif et **rien ne change** : pas de jeton exigé,
# aucune route fermée. C'est la garantie de compatibilité d'un déploiement
# existant — vérifiée par tests/test_rbac.py.
_rbac: RegistreRBAC = RegistreRBAC.charger(cfg.data_dir)
if not _rbac.actif:
    log.info("data/rbac.json absent : rôles et cloisonnement inactifs "
             "(comportement historique, jeton unique ou accès ouvert)")


def _recharge_rbac() -> RegistreRBAC:
    """Relit `data/rbac.json` — appelé après toute modification d'utilisateur."""
    global _rbac
    _rbac = RegistreRBAC.charger(cfg.data_dir)
    return _rbac


def _utilisateur_courant(request) -> Optional[Utilisateur]:
    """Utilisateur résolu par le middleware, ou None si RBAC inactif."""
    return getattr(request.state, "utilisateur", None)


def _autorise_revue_douaniere(request: Request) -> Utilisateur:
    """Frontière stricte, même quand les routes legacy sont en mode ouvert."""
    utilisateur = _utilisateur_courant(request)
    if (not _rbac.actif or utilisateur is None or utilisateur.environnement
            or ADMINISTRATEUR not in utilisateur.roles):
        audit(cfg.log_dir, "revue_douaniere_acces_refuse", methode=request.method,
              acteur=utilisateur.nom if utilisateur else "non_identifie")
        raise HTTPException(403, {"code": "administrateur_nominatif_rbac_requis"},
                            headers={"Cache-Control": "no-store"})
    return utilisateur


app.include_router(creer_router_revue(
    _autorise_revue_douaniere,
    lambda: cfg.data_dir / "customs-quarantine" / "registre.json",
    lambda **champs: audit_obligatoire(cfg.log_dir, "revue_douaniere", **champs),
))


def _exige(role: str):
    """Dépendance FastAPI : la route exige ce rôle au minimum.

    Quand RBAC est inactif, la dépendance laisse passer : sans fichier de
    rôles, aucune route ne se ferme. Quand il est actif, un rôle insuffisant
    est refusé **et tracé** — un refus non tracé ne se distingue pas d'un bug.
    """
    from fastapi import Request as _Request

    def dependance(request: _Request) -> Optional[Utilisateur]:
        u = _utilisateur_courant(request)
        if u is None:
            return None
        if u.a_role(role):
            return u
        audit(cfg.log_dir, "acces_refuse_role", route=request.url.path,
              methode=request.method, acteur=u.nom,
              roles=sorted(u.roles), requis=role)
        log.warning("accès refusé : %s sur %s (rôle %s requis, a %s)",
                    u.nom, request.url.path, role, sorted(u.roles))
        raise HTTPException(403, "rôle « %s » requis" % role)

    return dependance


_METHODES_ECRITURE = frozenset({"POST", "PUT", "PATCH", "DELETE"})

def _role_requis(request: Request) -> Optional[str]:
    """Politique centrale : aucun endpoint d'écriture ne tombe en accès libre."""
    path = request.url.path
    method = request.method
    if path == "/api/audit" and method == "GET":
        return SUPERVISEUR
    if path.startswith("/api/connectors"):
        if path == "/api/connectors/preview":
            return OPERATEUR
        if (method in _METHODES_ECRITURE or "/secrets" in path):
            return ADMINISTRATEUR
        return LECTEUR
    if method not in _METHODES_ECRITURE:
        return None
    if (path.startswith(("/api/admin/", "/api/backups", "/api/rbac/"))
            or path == "/api/calibration/fit"
            or path.startswith("/api/watch")
            or (path.startswith("/api/profiles/")
                and method in {"PUT", "DELETE"})):
        return ADMINISTRATEUR
    if method == "POST" and re.fullmatch(
            r"/api/dossiers/[^/]+/(coherence|transmission)", path):
        return SUPERVISEUR
    return OPERATEUR


def _verifie_role(request: Request, utilisateur: Optional[Utilisateur],
                  role: str) -> None:
    if utilisateur is None or utilisateur.a_role(role):
        return
    audit(cfg.log_dir, "acces_refuse_role", route=request.url.path,
          methode=request.method, acteur=utilisateur.nom,
          roles=sorted(utilisateur.roles), requis=role)
    log.warning("accès refusé : %s sur %s (rôle %s requis, a %s)",
                utilisateur.nom, request.url.path, role,
                sorted(utilisateur.roles))
    raise HTTPException(403, "rôle « %s » requis" % role)


def _exige_dossier(dossier_id: str, request) -> None:
    """Refuse l'accès à un dossier hors du périmètre de l'utilisateur.

    Renvoie 403 et non 404 : dans un outil local dont la liste d'utilisateurs
    est explicite, révéler l'existence d'un dossier n'apporte rien à un
    attaquant, alors qu'un message clair évite à l'opérateur de croire à un
    dossier perdu.
    """
    u = _utilisateur_courant(request)
    if u is None or u.voit_dossier(dossier_id):
        return
    audit(cfg.log_dir, "acces_refuse_dossier", route=request.url.path,
          methode=request.method, acteur=u.nom, dossier=dossier_id)
    log.warning("accès refusé : %s sur le dossier %s (hors périmètre)",
                u.nom, dossier_id)
    raise HTTPException(403, "dossier hors de votre périmètre")

def _forme_plausible(valeur: str) -> bool:
    """Un identifiant client n'est repris que s'il est inoffensif."""
    return (len(valeur) >= 8
            and all(c.isalnum() or c in "-_." for c in valeur))


# Actions RBAC par défaut applicables aux routes transit
RBAC_ACTIONS = {
    "consultation": "lecteur",
    "creation": "agent_de_transit",
    "modification": "agent_de_transit",
    "suppression_logique": "controleur_documentaire",
    "archivage": "controleur_documentaire",
    "validation_documentaire": "controleur_documentaire",
    "resolution_anomalies": "responsable_transport",
    "changement_statut": "agent_de_transit",
    "gestion_financière": "controleur_documentaire",
    "export": "controleur_documentaire",
    "configuration_métier": "administrateur",
}

_AUTH_EXEMPT = {"/", "/docs", "/openapi.json", "/redoc", "/api/health",
                "/api/auth/status", "/api/security"}
# ces routes sont publiques et ne doivent pas exposer de données métier ni
# de secrets ; la route /api/security est un diagnostic de sécurité lisible.


def _avertit_bind_ouvert() -> None:
    """Signale un service exposé sans jeton.

    En mode local-first, l'hôte par défaut est `127.0.0.1` pour éviter
    l'exposition réseau accidentelle. Si l'API est réellement ouverte sur une
    interface externe, il faut un jeton ou un contrôle strict du réseau.
    """
    try:
        hote = str(cfg.get("api.host", "127.0.0.1") or "")
    except Exception:
        hote = "127.0.0.1"
    ouvert = hote not in ("127.0.0.1", "localhost", "::1", "")
    if ouvert and not _AUTH_TOKEN:
        log.warning(
            "écoute sur %s SANS jeton : toute machine du réseau peut lire les "
            "documents traités et piloter les transmissions. Pour restreindre, "
            "définir UNIOCR_TOKEN ou api.host=127.0.0.1 dans config/default.json.",
            hote,
        )


_avertit_bind_ouvert()


# ─────────────── observabilité : corrélation + limitation de débit ───────────────
# L'identifiant de corrélation est posé avant tout traitement : une ligne de
# journal produite pendant une requête peut alors être rattachée à cette
# requête, ce qui était impossible auparavant.

_compteur = CompteurDebit(limite=int(cfg.get("api.rate_limit", 600) or 0),
                          fenetre=float(cfg.get("api.rate_window", 60) or 60))
_compteur.actif = _compteur.limite > 0


@app.middleware("http")
async def _correlation(request, call_next):
    """Attache un identifiant de corrélation à chaque requête.

    Un identifiant fourni par le client est repris tel quel s'il a une forme
    plausible : cela permet à un frontal ou un test de suivre une chaîne.
    """
    fourni = (request.headers.get(HEADER_CORRELATION)
              or request.headers.get("X-Correlation-ID") or "").strip()
    identifiant = fourni[:64] if _forme_plausible(fourni) else nouvel_identifiant()
    request.state.request_id = identifiant
    reponse = await call_next(request)
    reponse.headers[HEADER_CORRELATION] = identifiant
    return reponse


#: méthodes soumises à la limitation. Les lectures en sont exclues : l'interface
#: interroge /api/jobs/{id} en boucle pendant un traitement par lot, et brider
#: ce polling ferait échouer des traitements parfaitement légitimes. Ce qu'on
#: veut empêcher, c'est l'empilement d'écritures (réimports, transmissions).
_METHODES_LIMITEES = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@app.middleware("http")
async def _limitation_debit(request, call_next):
    """Refuse le dépassement, avec la date de retry disponible.

    Volontairement en mémoire et par adresse cliente : cela protège d'une
    boucle de réimport accidentelle, pas d'un attaquant distribué. Le journal
    le dit, plutôt que de laisser croire à une protection absolue.

    Seules les écritures sont limitées : l'interface interroge
    `/api/jobs/{id}` en boucle pendant un traitement par lot, et brider ce
    polling ferait échouer des traitements légitimes.
    """
    chemin = request.url.path
    if (request.method in _METHODES_LIMITEES
            and chemin.startswith("/api/") and chemin not in _DEBIT_EXEMPT):
        client = request.client.host if request.client else "inconnu"
        autorise, attente = _compteur.autorise(client)
        if not autorise:
            log.warning("débit dépassé pour %s sur %s (attente %.1fs)",
                        client, chemin, attente)
            return JSONResponse(
                {"detail": "trop de requêtes, réessayer plus tard",
                 "retry_after": round(attente, 1)},
                status_code=429,
                headers={"Retry-After": str(int(attente) + 1)})
    return await call_next(request)


@app.get("/api/observabilite")
def etat_observabilite() -> dict:
    """État de la limitation de débit — lisible, pour diagnostiquer un 429."""
    return _compteur.etat()


@app.get("/api/security")
def security_status() -> dict:
    """État de sécurité et de configuration HTTP exposé au client."""
    policy = _default_security_headers()
    return {
        "auth_required": bool(_AUTH_TOKEN) or _rbac.actif,
        "auth_mode": "token" if _AUTH_TOKEN else ("rbac" if _rbac.actif else "open"),
        "host": cfg.get("api.host", "127.0.0.1"),
        "allowed_hosts": _configured_allowed_hosts(),
        "cors_origins": _configured_cors_origins(),
        "headers": {
            "x_frame_options": policy["x_frame_options"],
            "x_content_type_options": policy["x_content_type_options"],
            "referrer_policy": policy["referrer_policy"],
            "permissions_policy": policy["permissions_policy"],
            "content_security_policy": policy["content_security_policy"],
        },
    }


@app.middleware("http")
async def _security_headers(request, call_next):
    """Ajoute des en-têtes HTTP défensifs sur chaque réponse."""
    response = await call_next(request)
    for key in ("server", "x-powered-by"):
        if key in response.headers:
            del response.headers[key]

    policy = _default_security_headers()
    if policy["x_frame_options"]:  # vide en mode aperçu (UI en iframe)
        response.headers.setdefault("X-Frame-Options", policy["x_frame_options"])
    response.headers.setdefault("X-Content-Type-Options", policy["x_content_type_options"])
    response.headers.setdefault("Referrer-Policy", policy["referrer_policy"])
    response.headers.setdefault("Permissions-Policy", policy["permissions_policy"])
    response.headers.setdefault("Content-Security-Policy", policy["content_security_policy"])
    response.headers.setdefault("Cache-Control", policy["cache_control"])
    if _hsts_enabled():
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


@app.middleware("http")
async def _optional_token_auth(request, call_next):
    # Le middleware ne décide plus seul : il résout l'utilisateur et le dépose
    # sur `request.state`. Les routes interrogent ensuite le rôle et le
    # périmètre. Un refus est donc toujours tracé par celui qui le décide.
    request.state.utilisateur = None
    path = request.url.path

    if not _rbac.actif:
        # ── comportement historique, inchangé ──
        if not _AUTH_TOKEN:
            return await call_next(request)
        if path in _AUTH_EXEMPT or not path.startswith("/api/"):
            return await call_next(request)
        supplied = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(supplied, _AUTH_TOKEN):
            return JSONResponse({"detail": "jeton requis (UNIOCR_TOKEN)"}, status_code=401)
        return await call_next(request)

    # ── RBAC actif ──
    if path in _AUTH_EXEMPT or not path.startswith("/api/"):
        return await call_next(request)
    supplied = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()

    # le jeton d'environnement reste un passe-partout, comportement historique
    # conservé pour les scripts existants ; chaque usage est tracé.
    if _AUTH_TOKEN and supplied and hmac.compare_digest(supplied, _AUTH_TOKEN):
        request.state.utilisateur = Utilisateur(
            nom="environnement", roles=frozenset({ADMINISTRATEUR}),
            dossiers=frozenset({TOUS}), environnement=True)
        audit(cfg.log_dir, "acces_jeton_environnement", route=path,
              methode=request.method)
        return await call_next(request)

    u = _rbac.resoudre(supplied)
    if u is None:
        audit(cfg.log_dir, "acces_refuse_jeton", route=path, methode=request.method)
        return JSONResponse({"detail": "jeton inconnu (voir data/rbac.json)"},
                            status_code=401)
    request.state.utilisateur = u
    role = _role_requis(request)
    if role:
        try:
            _verifie_role(request, u, role)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


# ─────────────────────── PWA : coquille installable ───────────────────────
# La coquille (polices incluses) est mise en cache par le service worker ;
# aucune réponse d'API n'est jamais mise en cache.
def _web_dir() -> Path:
    """Répertoire de l'interface livrée (contient manifest et sw.js)."""
    return Path(__file__).resolve().parents[2] / "web"


@app.get("/manifest.webmanifest", include_in_schema=False)
def webmanifest():
    path = _web_dir() / "manifest.webmanifest"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="manifest absent")
    return FileResponse(path, media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    path = _web_dir() / "sw.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="service worker absent")
    # toujours servi frais : un vieux SW bloquerait les mises à jour
    return FileResponse(path, media_type="text/javascript",
                        headers={"Cache-Control": "no-cache, no-store, must-revalidate",
                                 "Service-Worker-Allowed": "/"})


@app.get("/modules/i18n-controls.js", include_in_schema=False)
def i18n_controls_module():
    path = cfg.web_dir / "modules" / "i18n-controls.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="module i18n absent")
    return FileResponse(path, media_type="text/javascript")


# Modules chargés par index.html depuis la racine (`<script src="...">`).
# Sans ces routes, ils tombaient en 404 et l'UI perdait connecteurs, dossiers,
# formulaires, traçabilité et transmission.
MODULES_WEB_RACINE = (
    "connectors.js",
    "dossier.js",
    "formulaire.js",
    "tracabilite.js",
    "transmission.js",
)


def _fabrique_module_web(nom_fichier: str):
    def _module_web() -> FileResponse:
        path = cfg.web_dir / nom_fichier
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"{nom_fichier} absent")
        return FileResponse(path, media_type="text/javascript")
    return _module_web


for _nom_module in MODULES_WEB_RACINE:
    app.add_api_route(
        f"/{_nom_module}",
        _fabrique_module_web(_nom_module),
        methods=["GET"],
        include_in_schema=False,
        name=f"web_module_{_nom_module.replace('.', '_')}",
    )


@app.get("/icon.svg", include_in_schema=False)
def icon_svg():
    path = _web_dir() / "icon.svg"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="icône absente")
    return FileResponse(path, media_type="image/svg+xml")


# Le service worker précache `./index.html` et `./styles.css` ; sans ces deux
# routes l'installation du cache échouait en 404 et l'UI hors ligne était
# incomplète. On les sert à la racine, comme le fait déjà `sw.js`.
@app.get("/index.html", include_in_schema=False)
def index_html() -> HTMLResponse:
    path = cfg.web_dir / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="UI non installée")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/styles.css", include_in_schema=False)
def styles_css() -> FileResponse:
    path = cfg.web_dir / "styles.css"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="feuille de style absente")
    return FileResponse(path, media_type="text/css")


# ─────────────────────── A2 · calibration de confiance ───────────────────────
def _calibration_path() -> Path:
    return cfg.data_dir / "calibration.json"


@app.get("/api/calibration")
def get_calibration() -> dict:
    """État de la calibration : méthode, échantillons, caractère synthétique.

    N'expose jamais le contenu des documents — uniquement la provenance
    de la courbe, pour que l'interface puisse l'afficher honnêtement.
    """
    cal = Calibration.load(_calibration_path())
    out = cal.diagnostic()
    out["fitted_at_iso"] = (
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cal.fitted_at))
        if cal.fitted_at else None)
    return out


class CalibrationFitBody(BaseModel):
    force: bool = False


@app.post("/api/calibration/fit")
def fit_calibration(body: CalibrationFitBody) -> dict:
    """Réajuste la calibration sur les échantillons étiquetés disponibles.

    Un ajustement issu de données synthétiques reste inactif sauf force=True :
    mieux vaut une confiance brute connue qu'une probabilité inventée.
    """
    from .calibration import collect_pairs

    samples = Path(__file__).resolve().parents[2] / "benchmarks" / "field_samples"
    gt = samples / "ground_truth.json"
    if not gt.is_file():
        raise HTTPException(status_code=404,
                            detail="aucun échantillon étiqueté disponible")
    pairs, meta = collect_pairs(samples, gt)
    cal = Calibration()
    diag = cal.fit(pairs, force=body.force, synthetic=(meta["suite"] != "réelle"))
    cal.save(_calibration_path())
    diag["suite"] = meta["suite"]
    audit(cfg.log_dir, "calibration_fitted",
          method=diag["method"], active=diag["active"],
          n_samples=diag["n_samples"], synthetic=diag["synthetic"])
    return diag


# ─────────────────────── E1 ressources · E3 chiffrement ───────────────────────
def _crypto_store() -> "CryptoStore":
    """Chiffrement au repos selon la configuration.

    Désactivé par défaut : `security.encryption.enabled` doit être true ET une
    clé (fichier ou phrase de passe) doit être fournie. Un chiffrement à moitié
    configuré reste inactif — mieux vaut rien qu'un faux sentiment de sécurité.
    """
    enc = cfg.get("security.encryption", {}) or {}
    if not enc.get("enabled"):
        return CryptoStore(enabled=False)
    key_file = enc.get("key_file")
    if key_file:
        return CryptoStore.from_key_file(cfg.data_dir / key_file)
    passphrase = enc.get("passphrase", "")
    salt = (enc.get("salt") or "").encode("utf-8")
    if passphrase and len(salt) == SALT_LEN:
        return CryptoStore.from_passphrase(passphrase, salt)
    log.warning("chiffrement activé mais aucune clé valide : désactivé")
    return CryptoStore(enabled=False)


@app.get("/api/resources")
def get_resources() -> dict:
    """Ressources réelles de la machine et besoins des moteurs.

    Permet à l'interface d'expliquer *pourquoi* un moteur lourd n'est pas
    actif, au lieu d'afficher un simple « indisponible ».
    """
    return snapshot()


@app.get("/api/encryption")
def get_encryption() -> dict:
    """État du chiffrement au repos (ne révèle jamais la clé)."""
    store = _crypto_store()
    return store.status()


# ═══════════════════════ CONNECTEUR HUB ═══════════════════════
# Aucune de ces routes ne contacte un système externe réel : seuls les
# connecteurs configurés et testés le font, à la demande explicite.
# NOTE : les routes littérales sont déclarées AVANT les routes paramétrées,
# sinon `/{connector_id}` capture `/preview` et `/transmit`.
# ═══════════════════════ CONNECTEUR HUB ═══════════════════════
# Aucune de ces routes ne contacte un système externe réel : seuls les
# connecteurs configurés et testés le font, à la demande explicite.

@app.get("/api/connectors")
def list_connectors() -> dict:
    """Vue d'ensemble : adaptateurs disponibles, instances configurées, états."""
    return {"summary": connector_hub.summary(),
            "catalog": connector_hub.catalog(),
            "configured": connector_hub.list_configured()}


@app.get("/api/connectors/catalog")
def connectors_catalog() -> list[dict]:
    """Catalogue des adaptateurs (ce qui peut être instancié)."""
    return connector_hub.catalog()


@app.get("/api/connectors/configured")
def connectors_configured() -> list[dict]:
    """Connecteurs configurés, avec état et dernier test réel."""
    return connector_hub.list_configured()


class ConnectorSettingsBody(BaseModel):
    settings: dict = {}
    note: str = ""


@app.get("/api/connectors/secrets/status")
def secrets_status() -> dict:
    """État du coffre (aucun secret révélé)."""
    return connector_hub.secrets.describe()


# ─────────────────── mapping + validation + transmission ───────────────────

class MappingRuleBody(BaseModel):
    source_field: str
    target_field: str
    transform: str = "none"


class PreviewBody(BaseModel):
    job_id: str
    form_id: str = ""
    rules: list[MappingRuleBody] = []
    risk: str = "medium"


@app.post("/api/connectors/preview")
def preview_mapping(body: PreviewBody, request: Request) -> dict:
    """Préremplit un formulaire depuis un document traité, et valide.

    Ne transmet rien : c'est l'écran de contrôle. Chaque valeur reste reliée à
    sa source (document, page, valeur OCR, règle).
    """
    _exige_job(request, body.job_id)
    result = store.load_result(body.job_id)
    if result is None:
        raise HTTPException(404, "résultat indisponible pour ce document")
    form = _resolve_form(body.form_id, result)
    if form is None:
        raise HTTPException(400, "formulaire introuvable : "
                                 "précisez form_id ou configurez un connecteur")

    from .connectors.mapping import MappingEngine, MappingRule
    from .connectors.validation import RiskLevel, Validator

    eng = MappingEngine([MappingRule(r.source_field, r.target_field, r.transform)
                         for r in body.rules])
    ocr_fields = _ocr_fields(result)
    values = eng.apply(form, ocr_fields)
    suggestions = eng.suggest(form, ocr_fields)
    try:
        risk = RiskLevel(body.risk)
    except ValueError:
        risk = RiskLevel.MEDIUM
    report = Validator(risk).validate(form, values)
    return {"job_id": body.job_id, "form": form.as_dict(),
            "values": {k: v.as_dict() for k, v in values.items()},
            "suggestions": suggestions, "validation": report.as_dict()}


class TransmitBody(BaseModel):
    job_id: str
    form_id: str = ""
    rules: list[MappingRuleBody] = []
    risk: str = "medium"
    confirmed: bool = False
    confirmed_by: str = ""


@app.post("/api/connectors/transmit")
def transmit(body: TransmitBody, request: Request) -> dict:
    """Transmet vers un connecteur opérationnel, après validation humaine.

    Refuse si la validation n'est pas conforme : le verrou est côté serveur.
    """
    _exige_job(request, body.job_id)
    from .connectors.mapping import MappingEngine, MappingRule
    from .connectors.validation import RiskLevel, Validator

    result = store.load_result(body.job_id)
    if result is None:
        raise HTTPException(404, "résultat indisponible pour ce document")
    form = _resolve_form(body.form_id, result)
    if form is None:
        raise HTTPException(400, "formulaire introuvable")

    eng = MappingEngine([MappingRule(r.source_field, r.target_field, r.transform)
                         for r in body.rules])
    values = eng.apply(form, _ocr_fields(result))
    try:
        risk = RiskLevel(body.risk)
    except ValueError:
        risk = RiskLevel.MEDIUM
    report = Validator(risk).validate(form, values)
    if body.confirmed:
        report.confirm(by=body.confirmed_by or "api")

    # le connecteur doit être opérationnel (test réel réussi)
    target = None
    for cid in [r["connector_id"] for r in connector_hub.list_configured()]:
        inst = connector_hub.get(cid)
        if inst is not None and inst.state in OPERATIONAL_STATES:
            target = inst
            break
    if target is None:
        raise HTTPException(409, "aucun connecteur opérationnel : "
                                 "configurez puis testez-en un")

    try:
        tx = transmissions.create(target.connector_id, form, report, body.job_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    tx = transmissions.send(tx.transmission_id, target)
    return {"transmission": tx.as_dict(),
            "connector_id": target.connector_id,
            "is_real_external_system": target.is_real_external_system}


# ─────────────────── modèles de formulaires (phase 5) ───────────────────

@app.get("/api/connectors/forms")
def list_forms(include_inactive: bool = False) -> dict:
    """Modèles de formulaires déclarés localement (jamais devinés)."""
    return {"forms": [f.summary() for f in form_store.list(include_inactive)],
            "templates": ["customs_declaration", "port_call"]}


@app.get("/api/connectors/forms/templates")
def form_templates() -> list[dict]:
    """Trames de départ proposées — structures NON officielles."""
    from .connectors.forms import TEMPLATES

    out = []
    for name, fn in TEMPLATES.items():
        t = fn()
        out.append({"form_id": t.form_id, "name": t.name,
                    "description": t.description,
                    "fields": len(t.fields),
                    "required": sum(1 for f in t.fields if f.required)})
    return out


@app.get("/api/connectors/forms/{form_id}")
def get_form(form_id: str) -> dict:
    f = form_store.get(form_id)
    if f is None:
        raise HTTPException(404, f"formulaire inconnu : {form_id}")
    return {"form": f.model_dump(), "schema": f.schema().as_dict()}


@app.post("/api/connectors/forms")
def create_form(body: dict) -> dict:
    """Crée un modèle. `fields` = [{key, label, type, required, …}]."""
    fields = body.get("fields") or []
    if not fields:
        raise HTTPException(400, "un formulaire doit avoir au moins un champ")
    try:
        form = FormDefinition(
            form_id=str(body.get("form_id") or uuid.uuid4().hex[:12]),
            name=str(body.get("name") or ""),
            description=str(body.get("description") or ""),
            fields=[FormField(**{k: v for k, v in fd.items()
                                 if k in FormField.model_fields})
                    for fd in fields])
        form_store.create(form)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return form.summary()


@app.post("/api/connectors/forms/{form_id}")
def update_form(form_id: str, body: dict) -> dict:
    """Modifie → nouvelle version. L'ancienne reste traçable."""
    try:
        changes = {k: v for k, v in body.items()
                   if k in FormDefinition.model_fields}
        form = form_store.update(form_id, **changes)
    except KeyError:
        raise HTTPException(404, f"formulaire inconnu : {form_id}")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return form.summary()


@app.post("/api/connectors/forms/{form_id}/disable")
def disable_form(form_id: str) -> dict:
    """Désactive un modèle obsolète sans le supprimer."""
    try:
        form = form_store.disable(form_id)
    except KeyError:
        raise HTTPException(404, f"formulaire inconnu : {form_id}")
    return form.summary()


@app.delete("/api/connectors/forms/{form_id}")
def delete_form(form_id: str) -> dict:
    if not form_store.delete(form_id):
        raise HTTPException(404, f"formulaire inconnu : {form_id}")
    return {"deleted": form_id}


@app.post("/api/connectors/forms/{form_id}/from-template")
def form_from_template(form_id: str, template: str = "") -> dict:
    """Copie une trame de départ dans un modèle modifiable."""
    from .connectors.forms import load_template

    t = load_template(template or form_id)
    if t is None:
        raise HTTPException(404, f"trame inconnue : {template}")
    if form_store.get(t.form_id) is not None:
        raise HTTPException(409, f"formulaire déjà existant : {t.form_id}")
    form_store.create(t)
    return t.summary()


@app.get("/api/connectors/transmissions")
def list_transmissions(connector_id: str = "", status: str = "",
                       job_id: str = "", limit: int = 100) -> dict:
    """Historique des transmissions (phase 9)."""
    items = transmissions.list(connector_id=connector_id, status=status,
                               job_id=job_id, limit=limit)
    return {"stats": transmissions.stats(),
            "transmissions": [t.as_dict() for t in items]}


@app.post("/api/connectors/transmissions/{transmission_id}/reconcile")
def reconcile_transmission(transmission_id: str, connector_id: str = "") -> dict:
    """Rapproche une transmission à l'issue inconnue AVANT toute reprise."""
    tx = transmissions.get(transmission_id)
    if tx is None:
        raise HTTPException(404, "transmission inconnue")
    inst = connector_hub.get(connector_id or tx.connector_id)
    if inst is None:
        raise HTTPException(404, "connecteur inconnu")
    tx = transmissions.reconcile(transmission_id, inst)
    return tx.as_dict()


@app.post("/api/connectors/transmissions/{transmission_id}/retry")
def retry_transmission(transmission_id: str, connector_id: str = "",
                       auto: bool = False) -> dict:
    """Reprend une transmission. Les reprises automatiques sont limitées et
    refusées après un rejet métier."""
    tx = transmissions.get(transmission_id)
    if tx is None:
        raise HTTPException(404, "transmission inconnue")
    inst = connector_hub.get(connector_id or tx.connector_id)
    if inst is None:
        raise HTTPException(404, "connecteur inconnu")
    try:
        tx = transmissions.retry(transmission_id, inst, auto=auto)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return tx.as_dict()


@app.post("/api/connectors/transmissions/{transmission_id}/cancel")
def cancel_transmission(transmission_id: str, connector_id: str = "") -> dict:
    tx = transmissions.get(transmission_id)
    if tx is None:
        raise HTTPException(404, "transmission inconnue")
    inst = connector_hub.get(connector_id or tx.connector_id)
    if inst is None:
        raise HTTPException(404, "connecteur inconnu")
    return transmissions.cancel(transmission_id, inst).as_dict()


def _ocr_fields(result: dict) -> dict:
    """Champs extraits d'un résultat, tels que consommés par le mapping."""
    fields = (result or {}).get("fields") or {}
    return fields


def _resolve_form(form_id: str, result: dict):
    """Trouve le formulaire cible : id explicite, sinon celui du connecteur
    opérationnel. Renvoie None si aucun schéma n'est disponible — on ne
    devine jamais une structure."""

    if form_id:
        # 1) formulaire déclaré localement (builder)
        local = form_store.get(form_id)
        if local is not None and local.active:
            return local.schema()
        # 2) sinon, formulaire exposé par un connecteur
        for cid in [r["connector_id"] for r in connector_hub.list_configured()]:
            inst = connector_hub.get(cid)
            if inst is None:
                continue
            try:
                for f in inst.discover_forms():
                    if f.form_id == form_id:
                        return f
            except Exception:
                continue
        return None
    for cid in [r["connector_id"] for r in connector_hub.list_configured()]:
        inst = connector_hub.get(cid)
        if inst is None or inst.state not in OPERATIONAL_STATES:
            continue
        try:
            forms = inst.discover_forms()
            if forms:
                return forms[0]
        except Exception:
            continue
    return None


@app.post("/api/connectors/{connector_id}")
def create_connector(connector_id: str, body: ConnectorSettingsBody) -> dict:
    """Crée/met à jour une instance. Repart à « à tester » — jamais opérationnel
    d'office."""
    try:
        inst = connector_hub.create(connector_id, body.settings, body.note)
    except KeyError:
        raise HTTPException(404, f"adaptateur inconnu : {connector_id}")
    return inst.describe()

@app.get("/api/connectors/{connector_id}")
def get_connector(connector_id: str) -> dict:
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    return inst.describe()

@app.delete("/api/connectors/{connector_id}")
def delete_connector(connector_id: str) -> dict:
    """Supprime la configuration et les secrets. Les transmissions archivées
    restent (preuve de ce qui a été fait)."""
    if not connector_hub.delete(connector_id):
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    return {"deleted": connector_id}

@app.post("/api/connectors/{connector_id}/disable")
def disable_connector(connector_id: str) -> dict:
    """Désactive SANS supprimer configuration, historique ni transmissions."""
    if not connector_hub.disable(connector_id):
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    return {"connector_id": connector_id, "state": "disabled"}

@app.post("/api/connectors/{connector_id}/enable")
def enable_connector(connector_id: str) -> dict:
    """Réactive — le connecteur repart à « à tester » (un interrupteur ne rend
    jamais un connecteur opérationnel)."""
    if not connector_hub.enable(connector_id):
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    return {"connector_id": connector_id, "state": "to_test"}

@app.post("/api/connectors/{connector_id}/test")
def test_connector(connector_id: str) -> dict:
    """Test de connexion RÉEL. L'état évolue selon la preuve obtenue."""
    try:
        result = connector_hub.test(connector_id)
    except KeyError:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    return {"connector_id": connector_id, **result.as_dict(),
            "state": connector_hub.get(connector_id).state.value}

@app.get("/api/connectors/{connector_id}/status")
def connector_status(connector_id: str) -> dict:
    """État réel du connecteur, issu de son dernier test documenté."""
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    st = inst.status()
    return {"connector_id": connector_id, "state": st.state.value,
            "detail": st.detail,
            "last_test": st.last_test.as_dict() if st.last_test else None}


@app.get("/api/connectors/{connector_id}/metadata")
def connector_metadata(connector_id: str) -> dict:
    """Métadonnées déclarées par le connecteur (organisme, version d'interface…)."""
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    try:
        return {"connector_id": connector_id, **inst.fetch_metadata()}
    except NotSupportedError:
        return {"connector_id": connector_id, "metadata": None,
                "detail": "ce connecteur n'expose pas de métadonnées"}


@app.post("/api/connectors/{connector_id}/auth")
def connector_check_auth(connector_id: str) -> dict:
    """Vérification d'authentification — sans jamais révéler de secret."""
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    r = inst.check_auth()
    return {"connector_id": connector_id, **r.as_dict()}


@app.get("/api/connectors/{connector_id}/submission/{reference}")
def connector_submission(connector_id: str, reference: str) -> dict:
    """Statut d'une soumission + accusé de réception chez le système cible."""
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    out = {"connector_id": connector_id, "reference": reference}
    try:
        out["status"] = inst.get_status(reference)
    except NotSupportedError:
        out["status"] = {"detail": "statut non pris en charge par ce connecteur"}
    try:
        out["acknowledgement"] = inst.get_acknowledgement(reference)
    except NotSupportedError:
        out["acknowledgement"] = {"detail": "accusé non pris en charge"}
    try:
        out["errors"] = inst.list_errors(reference)
    except NotSupportedError:
        out["errors"] = []
    return out


class ExportBody(BaseModel):
    form_id: str = ""
    rules: list[MappingRuleBody] = []
    job_id: str = ""


@app.post("/api/connectors/{connector_id}/export")
def connector_export(connector_id: str, body: ExportBody,
                     request: Request) -> dict:
    """Mode C : produit l'export assisté (CSV + correspondance + traçabilité).

    N'envoie rien à l'extérieur : le fichier est à importer manuellement.
    """
    if body.job_id:
        _exige_job(request, body.job_id)
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    result = store.load_result(body.job_id) if body.job_id else None
    if result is None and body.job_id:
        raise HTTPException(404, "résultat indisponible pour ce document")
    form = _resolve_form(body.form_id, result) if result else None
    if form is None:
        raise HTTPException(400, "formulaire introuvable")
    from .connectors.mapping import MappingEngine, MappingRule
    from .connectors.validation import RiskLevel, Validator

    eng = MappingEngine([MappingRule(r.source_field, r.target_field, r.transform)
                         for r in body.rules])
    values = eng.apply(form, _ocr_fields(result))
    report = Validator(RiskLevel.LOW).validate(form, values)
    export = getattr(inst, "export", None)
    if export is None or not inst.supports(ConnectorCapability.EXPORT_DATA):
        raise HTTPException(400, "ce connecteur ne produit pas d'export assisté "
                                 "(mode C) — utilisez un connecteur d'export")
    return {"connector_id": connector_id, "validation": report.as_dict(),
            **export(form, report, job_id=body.job_id)}


@app.post("/api/connectors/{connector_id}/cancel/{reference}")
def connector_cancel(connector_id: str, reference: str) -> dict:
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    try:
        r = inst.cancel(reference)
        return {"connector_id": connector_id, **r.as_dict()}
    except NotSupportedError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/connectors/{connector_id}/resume/{reference}")
def connector_resume(connector_id: str, reference: str) -> dict:
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    try:
        r = inst.resume(reference)
        return {"connector_id": connector_id, **r.as_dict()}
    except NotSupportedError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/connectors/{connector_id}/forms")
def connector_forms(connector_id: str) -> dict:
    """Formulaires déclarés par le connecteur.

    Un connecteur sans capacité de découverte renvoie une liste vide : il ne
    prétend jamais deviner la structure d'un système auquel il n'a pas accès.
    """
    inst = connector_hub.get(connector_id)
    if inst is None:
        raise HTTPException(404, f"connecteur inconnu : {connector_id}")
    try:
        forms = inst.discover_forms()
    except Exception:
        forms = []
    return {"connector_id": connector_id,
            "forms": [f.as_dict() for f in forms]}

@app.get("/api/connectors/{connector_id}/secrets")
def connector_secret_keys(connector_id: str) -> dict:
    """Noms des secrets définis — JAMAIS leurs valeurs."""
    return {"connector_id": connector_id,
            "keys": connector_hub.secrets.keys_for(connector_id)}


class SecretBody(BaseModel):
    key: str
    value: str

@app.put("/api/connectors/{connector_id}/secrets")
def put_connector_secret(connector_id: str, body: SecretBody) -> dict:
    """Enregistre un secret chiffré (AES-256-GCM). Jamais en clair."""
    try:
        connector_hub.secrets.set(connector_id, body.key, body.value)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    audit(cfg.log_dir, "connector_secret_set", connector=connector_id,
          key=body.key)
    return {"connector_id": connector_id, "key": body.key, "stored": True}

@app.delete("/api/connectors/{connector_id}/secrets/{key}")
def delete_connector_secret(connector_id: str, key: str) -> dict:
    if not connector_hub.secrets.delete(connector_id, key):
        raise HTTPException(404, "secret inconnu")
    audit(cfg.log_dir, "connector_secret_deleted", connector=connector_id,
          key=key)
    return {"deleted": key}


@app.get("/api/auth/status")
def auth_status() -> dict:
    """Indique si l'authentification est active (sans révéler le jeton)."""
    return {"required": bool(_AUTH_TOKEN), "header": "Authorization: Bearer <jeton>"}


# ─────────────────────── rôles et cloisonnement ───────────────────────

@app.get("/api/rbac/moi")
def rbac_moi(request: Request) -> dict:
    """Identité et droits de l'appelant, tels qu'ils sont appliqués.

    L'interface s'en sert pour griser ce que l'utilisateur ne peut pas faire,
    plutôt que de le laisser découvrir un 403. Le jeton n'est jamais renvoyé.
    """
    u = _utilisateur_courant(request)
    if u is None:
        return {"actif": False, "roles": sorted(ROLES),
                "administrateur": True, "dossiers": [TOUS],
                "detail": "data/rbac.json absent : aucun cloisonnement appliqué"}
    return {"actif": True, **u.public(),
            "roles_disponibles": list(ROLES),
            "administrateur": u.a_role(ADMINISTRATEUR)}


@app.get("/api/rbac/utilisateurs")
def rbac_utilisateurs(request: Request,
                      _: None = None) -> dict:
    """Liste des utilisateurs — **sans les jetons**."""
    _exige(ADMINISTRATEUR)(request)
    return {"actif": _rbac.actif, "utilisateurs": _rbac.liste(),
            "roles_disponibles": list(ROLES)}


@app.post("/api/rbac/utilisateurs")
def rbac_creer(body: dict, request: Request) -> dict:
    """Crée un utilisateur. Le jeton est généré ici et renvoyé **une fois**.

    Il n'est plus relisible ensuite : le réafficher obligerait à le stocker en
    clair côté client. Un jeton perdu se régénère, il ne se consulte pas.
    """
    _exige(ADMINISTRATEUR)(request)
    nom = str(body.get("nom") or "").strip()
    roles = body.get("roles") or []
    dossiers = body.get("dossiers")
    try:
        u = _rbac.ajouter(nom, roles, dossiers)
    except RBACError as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(cfg.log_dir, "rbac_utilisateur_cree", acteur=_acteur(request),
          cree=u.nom, roles=sorted(u.roles), dossiers=sorted(u.dossiers))
    return {"ok": True, "utilisateur": u.public(), "jeton": u.jeton}


@app.put("/api/rbac/utilisateurs/{nom}")
def rbac_maj(nom: str, body: dict, request: Request) -> dict:
    """Modifie rôles et périmètre d'un utilisateur.

    Le jeton n'est pas modifiable ici : il a sa propre route, pour qu'une
    rotation de secret soit une action distincte et tracée comme telle.
    """
    _exige(ADMINISTRATEUR)(request)
    try:
        u = _rbac.maj(nom, body.get("roles"), body.get("dossiers"))
    except RBACError as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(cfg.log_dir, "rbac_utilisateur_modifie", acteur=_acteur(request),
          cible=u.nom, roles=sorted(u.roles), dossiers=sorted(u.dossiers))
    return {"ok": True, "utilisateur": u.public()}


@app.post("/api/rbac/utilisateurs/{nom}/jeton")
def rbac_jeton(nom: str, request: Request) -> dict:
    """Régénère le jeton d'un utilisateur (secret compromis ou perdu).

    L'ancien jeton cesse immédiatement de fonctionner. Action tracée, et
    réservée à l'administrateur : n'importe qui pouvant régénérer un jeton
    pourrait prendre la place de n'importe qui.
    """
    _exige(ADMINISTRATEUR)(request)
    try:
        jeton = _rbac.regenerer(nom)
    except RBACError as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(cfg.log_dir, "rbac_jeton_regene", acteur=_acteur(request), cible=nom)
    return {"ok": True, "nom": nom, "jeton": jeton}


@app.delete("/api/rbac/utilisateurs/{nom}")
def rbac_retirer(nom: str, request: Request) -> dict:
    """Retire un utilisateur : révocation immédiate de son accès."""
    _exige(ADMINISTRATEUR)(request)
    if not _rbac.retirer(nom):
        raise HTTPException(404, "utilisateur introuvable")
    audit(cfg.log_dir, "rbac_utilisateur_retire", acteur=_acteur(request), cible=nom)
    return {"deleted": True}


def _dossiers_du_job(job_id: str) -> list[str]:
    """Identifiants des dossiers qui contiennent ce document.

    Un document n'appartient pas forcément à un dossier : à l'import, il existe
    seul. C'est le seul cas où le cloisonnement ne s'applique pas — un document
    non classé ne peut être attribué à personne.
    """
    trouves = []
    for d in _dossiers.liste():
        if d.piece_par_job(job_id) is not None:
            trouves.append(d.id)
    return trouves


def _job_visible(request, job_id: str) -> bool:
    utilisateur = _utilisateur_courant(request)
    if utilisateur is None:
        return True
    dossiers = _dossiers_du_job(job_id)
    return not dossiers or any(utilisateur.voit_dossier(d) for d in dossiers)


def _exige_job(request, job_id: str) -> None:
    """Refuse l'accès à un document qu'aucun dossier visible ne contient.

    **Pourquoi cette garde existe.** Le cloisonnement par dossier seul se
    contourne : `GET /api/jobs/{id}/result` renvoie l'intégralité du contenu
    d'un document sans passer par la route du dossier. Un utilisateur bloqué
    sur un dossier lisait donc chaque document qu'il contient. La garde est
    posée au niveau du document, en aval du dossier.

    **La règle est « au moins un dossier visible », pas « aucun invisible ».**
    Un même document peut être classé dans plusieurs dossiers — c'est légitime
    (une facture commune à deux expéditions). Avec la règle inverse, classer un
    document dans le dossier de quelqu'un d'autre rendait ce document
    **illisible à son propriétaire** : un déni de service sur un accès
    légitime, et un garde imprévisible. Comme le contenu est le même document,
    y avoir accès par un dossier qu'on voit n'expose rien de plus.

    Document non classé : accès régi par le seul rôle. C'est la limite assumée
    et documentée du cloisonnement — un document qui n'appartient à aucun
    dossier ne peut être attribué à personne.
    """
    u = _utilisateur_courant(request)
    if u is None:
        return
    dossiers = _dossiers_du_job(job_id)
    if not dossiers:
        return                      # non classé : régi par le rôle seul
    if any(u.voit_dossier(d) for d in dossiers):
        return                      # visible par au moins un dossier
    audit(cfg.log_dir, "acces_refuse_document", route=request.url.path,
          methode=request.method, acteur=u.nom, job=job_id,
          dossiers=dossiers)
    log.warning("accès refusé : %s sur le document %s (classé dans %d dossier(s) "
                "hors périmètre)", u.nom, job_id, len(dossiers))
    raise HTTPException(403, "document hors de votre périmètre")


def _acteur(request) -> str:
    """Nom de l'utilisateur appelant, pour l'audit."""
    u = _utilisateur_courant(request)
    return u.nom if u else "anonyme"


@app.post("/api/rbac/recharger")
def rbac_recharger(request: Request) -> dict:
    """Relit `data/rbac.json` après une édition manuelle du fichier.

    Utile quand l'administrateur édite le JSON à la main : sans rechargement,
    il faudrait redémarrer le service pour que les changements portent.
    """
    _exige(ADMINISTRATEUR)(request)
    try:
        reg = _recharge_rbac()
    except RBACError as exc:
        raise HTTPException(422, "rechargement impossible : %s" % exc) from exc
    audit(cfg.log_dir, "rbac_recharge", acteur=_acteur(request),
          utilisateurs=len(reg.utilisateurs))
    return {"ok": True, "actif": reg.actif, "utilisateurs": reg.liste()}


class _UploadTooLarge(Exception):
    pass


async def _read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read bounded chunks and stop as soon as an upload exceeds its cap."""
    limite = max(0, int(max_bytes))
    contenu = bytearray()
    while True:
        taille = min(1024 * 1024, limite - len(contenu) + 1)
        bloc = await upload.read(taille)
        if not bloc:
            return bytes(contenu)
        contenu.extend(bloc)
        if len(contenu) > limite:
            raise _UploadTooLarge


@app.post("/api/documents")
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    profile: str = Form("generic"),
    languages: str = Form(""),
    quality_mode: str = Form("accurate"),
    preprocess: str = Form("true"),
    preprocess_mode: str = Form("standard"),
    variant_comparison: str = Form("true"),
    export_formats: str = Form("json,txt"),
    page_range: str = Form(""),
    render_dpi: int = Form(200),
    engine: str = Form("auto"),
    extract_fields: str = Form("true"),
    extract_tables: str = Form("true"),
    extract_barcodes: str = Form("true"),
    min_confidence_review: float = Form(0.7),
    dedupe: str = Form("true"),
) -> dict:
    import tempfile

    from .security import SecurityError, sanitize_filename, validate_file
    fname = sanitize_filename(file.filename or "document")
    max_bytes = int(cfg.get("max_file_size_mb", 50)) * 1024 * 1024
    try:
        data = await _read_upload_limited(file, max_bytes)
    except _UploadTooLarge as exc:
        raise HTTPException(413, "fichier trop volumineux") from exc
    langs = [ln.strip() for ln in languages.split(",") if ln.strip()]
    fmts = [f.strip() for f in export_formats.split(",") if f.strip()]
    options = JobOptions(
        languages=langs, profile=profile or "generic",
        quality_mode=quality_mode, preprocess=_form_bool(preprocess),
        preprocess_mode=preprocess_mode if preprocess_mode in ("off", "standard", "aggressive") else "standard",
        variant_comparison=_form_bool(variant_comparison),
        export_formats=fmts or ["json", "txt"],
        page_range=page_range or "",
        render_dpi=max(72, min(400, render_dpi)),
        engine=engine if engine in ("auto", "tesseract", "native") else "auto",
        extract_fields=_form_bool(extract_fields),
        extract_tables=_form_bool(extract_tables),
        extract_barcodes=_form_bool(extract_barcodes),
        min_confidence_review=max(0.0, min(1.0, min_confidence_review)),
    )
    # validation AVANT création du job : refus immédiat (400) si format/taille invalide
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=Path(fname).suffix or ".bin",
                                         delete=False) as tf:
            tf.write(data)
            tmp = Path(tf.name)
        validate_file(tmp, max_size_mb=cfg.get("max_file_size_mb", 50),
                      max_zip_uncompressed_mb=cfg.get("security.max_zip_uncompressed_mb", 200),
                      max_zip_ratio=cfg.get("security.max_zip_ratio", 100))
        if _form_bool(dedupe):
            import hashlib
            existing = store.find_by_hash(hashlib.sha256(data).hexdigest())
            if existing is not None:
                audit(cfg.log_dir, "job_deduped", job_id=existing.id,
                      filename=fname, source="upload")
                return {"job_id": existing.id, "status": existing.status.value,
                        "filename": existing.filename, "cached": True,
                        "cached_from": existing.id}
        job = store.create_job(fname, data, options)
    except SecurityError as exc:
        raise HTTPException(400, str(exc))
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    background.add_task(_run_job, job.id)
    return {"job_id": job.id, "status": job.status.value, "filename": fname,
            "cached": False}


@app.get("/api/jobs")
def list_jobs(request: Request, limit: int = Query(50, le=500),
              offset: int = 0) -> list[dict]:
    jobs = [j for j in store.list_jobs(limit=10000)
        if _job_visible(request, j.id)]
    return [j.model_dump(mode="json") for j in jobs[offset:offset + limit]]


# Route littérale déclarée AVANT /api/jobs/{job_id} : sinon FastAPI la capture
# et « stale » serait pris pour un identifiant de job.
@app.get("/api/jobs/stale")
def list_stale_jobs(request: Request) -> dict:
    """Jobs interrompus (traitement tué net, serveur arrêté).

    **Pourquoi.** `JobStore.retryable_jobs()` détectait ces jobs mais n'était
    appelé nulle part : un traitement interrompu restait `processing` pour
    toujours, invisible dans l'interface. La liste est désormais exposée, avec
    l'action de reprise existante (`POST /api/jobs/{id}/retry`).
    """
    jobs = [j for j in store.retryable_jobs() if _job_visible(request, j.id)]
    return {
        "count": len(jobs),
        "jobs": [j.model_dump(mode="json") for j in jobs],
    }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict:
    _exige_job(request, job_id)
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job introuvable")
    return job.model_dump(mode="json")


@app.get("/api/jobs/{job_id}/result")
def get_result(job_id: str, request: Request) -> dict:
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "job introuvable")
        raise HTTPException(409, f"résultat pas encore disponible (statut: {job.status.value})")
    return result


@app.get("/api/jobs/{job_id}/text")
def get_text(job_id: str, request: Request, page: Optional[int] = None) -> dict:
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(409, "résultat pas encore disponible")
    pages = result.get("pages", [])
    if page is not None:
        pages = [p for p in pages if p.get("page_num") == page]
        if not pages:
            raise HTTPException(404, f"page {page} introuvable")
    return {"pages": [{"page_num": p["page_num"], "text": p["text"]} for p in pages]}


@app.get("/api/jobs/{job_id}/fields")
def get_fields(job_id: str, request: Request) -> dict:
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(409, "résultat pas encore disponible")
    return {"fields": result.get("fields", {})}


@app.get("/api/jobs/{job_id}/tables")
def get_tables(job_id: str, request: Request) -> dict:
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(409, "résultat pas encore disponible")
    return {"tables": result.get("tables", [])}


@app.get("/api/jobs/{job_id}/quality")
def get_quality(job_id: str, request: Request) -> dict:
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(409, "résultat pas encore disponible")
    return result.get("quality", {})


class FieldPatch(BaseModel):
    confirmed_value: Optional[str] = None
    corrected_value: Optional[str] = None
    status: Optional[str] = None
    user: Optional[str] = None
    reason: Optional[str] = None


@app.patch("/api/jobs/{job_id}/fields/{name}")
def patch_field(job_id: str, name: str, patch: FieldPatch, request: Request) -> dict:
    """Validation/correction humaine d'un champ. Tout est tracé (audit)."""
    # rôle exigé : valider/corriger un champ. RBAC inactif = contrôle sans effet.
    _exige(OPERATEUR)(request)
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(409, "résultat pas encore disponible")
    fields = result.get("fields", {})
    if name not in fields:
        raise HTTPException(404, f"champ '{name}' introuvable")
    fv = fields[name]
    # L'état **avant** modification doit être traité : annuler une correction
    # exige de savoir ce qu'elle a remplacé. Enregistrer `raw_value` ne suffit
    # pas — la valeur affichée était peut-être déjà normalisée ou confirmée.
    precedent = _etat_champ(fv)
    if patch.confirmed_value is not None:
        fv["confirmed_value"] = patch.confirmed_value
        fv["value_origin"] = "confirmed"
        fv["status"] = "validated"
    if patch.corrected_value is not None:
        fv["corrected_value"] = patch.corrected_value
        # l'origine doit basculer : laisser « normalized » ferait croire que
        # la valeur affichée sort du moteur alors qu'un humain l'a tranché
        fv["value_origin"] = "corrected"
        if patch.status is None:
            fv["status"] = "corrected"
    if patch.status is not None:
        fv["status"] = patch.status
    fields[name] = fv
    result["fields"] = fields
    store.save_result(job_id, result)
    acteur = str(getattr(patch, "user", None) or "utilisateur")
    audit(cfg.log_dir, "field_validated", job_id=job_id, field=name,
          confirmed=patch.confirmed_value, corrected=patch.corrected_value,
          acteur=acteur, motif=getattr(patch, "reason", None),
          ancienne_valeur=precedent["valeur"],
          ancienne_origine=precedent["origine"],
          ancien_statut=precedent["statut"])
    return {"ok": True, "field": fv}


def _etat_champ(fv: dict) -> dict:
    """Ce qu'un champ affichait avant modification.

    Suit la même priorité que l'affichage : confirmée > corrigée > normalisée >
    brute. C'est cet état qu'une annulation doit restituer, pas la valeur
    brute — sinon annuler ferait perdre la normalisation déjà faite.
    """
    valeur = (fv.get("confirmed_value") or fv.get("corrected_value")
              or fv.get("normalized_value") or fv.get("raw_value"))
    return {"valeur": valeur,
            "origine": fv.get("value_origin"),
            "statut": fv.get("status")}


@app.post("/api/jobs/{job_id}/fields/{name}/undo")
def annuler_correction(job_id: str, name: str, request: Request,
                      body: dict | None = None) -> dict:
    """Annule la dernière correction humaine d'un champ.

    « Annuler » n'efface rien : la correction reste dans le journal d'audit,
    et l'annulation y est tracée à son tour avec son acteur et son motif.
    Restaurer l'état d'avant exige de l'avoir traité — c'est ce que fait
    `field_validated` depuis le lot 5.
    """
    # rôle exigé : annuler une correction. RBAC inactif = contrôle sans effet.
    _exige(OPERATEUR)(request)
    _exige_job(request, job_id)
    body = body or {}
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(409, "résultat pas encore disponible")
    fields = result.get("fields", {})
    if name not in fields:
        raise HTTPException(404, f"champ '{name}' introuvable")
    fv = fields[name]
    if not (fv.get("confirmed_value") or fv.get("corrected_value")):
        raise HTTPException(409, "aucune correction humaine à annuler sur ce champ")

    precedent = _derniere_correction(job_id, name)
    if precedent is None:
        raise HTTPException(409, "état antérieur introuvable dans l'audit : "
                                 "annulation impossible sans perdre la valeur")
    fv["confirmed_value"] = None
    fv["corrected_value"] = None
    fv["value_origin"] = precedent.get("ancienne_origine") or "raw"
    fv["status"] = precedent.get("ancien_statut") or "detected"
    fields[name] = fv
    result["fields"] = fields
    store.save_result(job_id, result)
    acteur = str(body.get("user") or "utilisateur")
    motif = str(body.get("motif") or "").strip()
    audit(cfg.log_dir, "field_correction_annulee", job_id=job_id, field=name,
          acteur=acteur, motif=motif,
          valeur_annulee=precedent.get("valeur_apres"),
          valeur_restauree=precedent.get("ancienne_valeur"))
    return {"ok": True, "field": fv,
            "restaure": {"valeur": precedent.get("ancienne_valeur"),
                         "origine": precedent.get("ancienne_origine"),
                         "statut": precedent.get("ancien_statut")}}


def _derniere_correction(job_id: str, name: str) -> dict | None:
    """Dernière correction humaine tracée pour ce champ, ou None.

    Le journal est lu à l'envers : c'est la modification la plus récente qu'on
    annule, pas la plus ancienne.
    """
    journal = cfg.log_dir / "audit.log"
    if not journal.is_file():
        return None
    for ligne in reversed(journal.read_text(encoding="utf-8").splitlines()):
        if "field_validated" not in ligne:
            continue
        try:
            entree = json.loads(ligne)
        except ValueError:
            continue
        if entree.get("job_id") != job_id or entree.get("field") != name:
            continue
        entree["valeur_apres"] = (entree.get("confirmed")
                                  or entree.get("corrected"))
        return entree
    return None


def _ensure_export(job_id: str, fmt: str) -> Path:
    """Retourne le fichier d'export, en le générant à la demande s'il est absent.

    Un export demandé est TOUJOURS produit si le résultat est disponible :
    plus aucun 404 parce que le job initial n'avait pas demandé ce format.
    """
    export_dir = store.export_dir(job_id)
    result_json = store.load_result(job_id)
    if result_json is None:
        raise HTTPException(409, "résultat pas encore disponible")
    from . import exporters as ex
    from .models import DocumentResult
    result = DocumentResult.model_validate(result_json)

    if fmt == "csv":
        candidates = sorted(export_dir.glob("*.csv"))
        if not candidates:
            candidates = ex.export_csv(result, export_dir)
        if len(candidates) == 1:
            return candidates[0]
        import zipfile
        bundle = export_dir / "csv_exports.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            for c in candidates:
                zf.write(c, c.name)
        return bundle

    names = {"txt": "result.txt", "json": "result.json", "xlsx": "result.xlsx",
             "xml": "result.xml", "pdf": "searchable.pdf"}
    path = export_dir / names[fmt]
    if not path.is_file():
        if fmt == "txt":
            ex.export_txt(result, path)
        elif fmt == "json":
            ex.export_json(result, path)
        elif fmt == "xlsx":
            ex.export_xlsx(result, path)
        elif fmt == "xml":
            ex.export_xml(result, path)
        elif fmt == "pdf":
            src = store.original_path(job_id)
            if src is None:
                raise HTTPException(
                    422, "document purement numérique : PDF consultable impossible (pas d'image source)")
            from .ingest import load_document
            loaded = load_document(src, dpi=200)
            page_images = {page.page_num: page.image for page in loaded.pages
                           if page.image is not None}
            ex.export_searchable_pdf(result, path, page_images)
    return path


@app.get("/api/jobs/{job_id}/export/{fmt}")
def export_job(job_id: str, request: Request, fmt: str):
    _exige_job(request, job_id)
    if fmt not in SUPPORTED_EXPORTS:
        raise HTTPException(400, f"format non supporté: {fmt}")
    if store.get(job_id) is None:
        raise HTTPException(404, "job introuvable")
    try:
        path = _ensure_export(job_id, fmt)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("échec de génération de l'export %s pour %s", fmt, job_id)
        raise HTTPException(500, f"échec de l'export {fmt}: {exc}")
    media = None
    if path.suffix == ".zip":
        media = "application/zip"
    return FileResponse(path, filename=path.name, media_type=media)


@app.get("/api/jobs/{job_id}/export/{fmt}/selected")
def export_selected(job_id: str, request: Request, fmt: str,
                    fields: str = Query(..., min_length=1)) -> FileResponse:
    """Export limité à une sélection de champs.

    Généré à la volée (non mis en cache) : la sélection est propre à une
    demande. `fields` = liste de noms de champs séparés par des virgules.
    Un champ inconnu est ignoré silencieusement — mieux vaut exporter ce qui
    existe que faire échouer toute la sélection.
    """
    _exige_job(request, job_id)
    if fmt not in SUPPORTED_EXPORTS:
        raise HTTPException(400, f"format non supporté: {fmt}")
    if store.get(job_id) is None:
        raise HTTPException(404, "job introuvable")
    result_json = store.load_result(job_id)
    if result_json is None:
        raise HTTPException(409, "résultat pas encore disponible")

    from . import exporters as ex
    from .models import DocumentResult

    wanted = [f.strip() for f in fields.split(",") if f.strip()]
    result = DocumentResult.model_validate(result_json)
    kept = {k: v for k, v in result.fields.items() if k in wanted}
    if not kept:
        raise HTTPException(400, "aucun champ de la sélection n'existe dans ce document")
    result = result.model_copy(update={"fields": kept})

    out_dir = store.export_dir(job_id) / "selected"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "selection_" + "_".join(sorted(kept))[:40]
    try:
        if fmt == "csv":
            # Une sélection de champs ne concerne que les champs : on n'emballe
            # pas les tableaux du document dans une archive ZIP, le résultat
            # doit rester un CSV lisible par un tableur.
            paths = ex.export_csv(result, out_dir, champs_seulement=True)
            path = paths[0]
        elif fmt == "xlsx":
            path = ex.export_xlsx(result, out_dir / f"{stem}.xlsx")
        elif fmt == "json":
            path = out_dir / f"{stem}.json"
            ex.export_json(result, path)
        elif fmt == "txt":
            path = out_dir / f"{stem}.txt"
            ex.export_txt(result, path)
        elif fmt == "xml":
            path = out_dir / f"{stem}.xml"
            ex.export_xml(result, path)
        elif fmt == "pdf":
            path = out_dir / f"{stem}.pdf"
            ex.export_searchable_pdf(result, path, _page_images(job_id))
        else:  # pragma: no cover - gardé par SUPPORTED_EXPORTS
            raise HTTPException(400, f"format non supporté: {fmt}")
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("échec de l'export ciblé %s pour %s", fmt, job_id)
        raise HTTPException(500, f"échec de l'export {fmt}: {exc}")

    audit(cfg.log_dir, "export_selected", job_id=job_id, fmt=fmt,
          fields=sorted(kept))
    media = "application/zip" if path.suffix == ".zip" else None
    return FileResponse(path, filename=path.name, media_type=media)


def _page_images(job_id: str) -> list:
    """Images des pages, pour le PDF consultable ([] si indisponibles)."""
    images = []
    for i in range(1, 200):
        p = store.job_dir(job_id) / "work" / f"page_{i}.png"
        if p.is_file():
            images.append(p)
        elif images:
            break
    return images


@app.get("/api/jobs/{job_id}/page/{page_num}/image")
def page_image(job_id: str, request: Request, page_num: int):
    """Image de la page originale (pour la visionneuse + surbrillance des zones)."""
    _exige_job(request, job_id)
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job introuvable")
    src = store.original_path(job_id)
    if src is None:
        raise HTTPException(404, "original absent")
    cache = store.job_dir(job_id) / "work" / f"page_{page_num}.png"
    if not cache.is_file():
        from .ingest import load_document
        try:
            loaded = load_document(src, dpi=150)
        except Exception as exc:
            raise HTTPException(422, f"document illisible: {exc}")
        page = next((p for p in loaded.pages if p.page_num == page_num), None)
        if page is None:
            raise HTTPException(404, f"page {page_num} introuvable")
        if page.image is None:
            raise HTTPException(422, "page purement numérique : pas d'image")
        cache.parent.mkdir(parents=True, exist_ok=True)
        page.image.save(cache)
    return FileResponse(cache, media_type="image/png")


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, background: BackgroundTasks, request: Request) -> dict:
    _exige_job(request, job_id)
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job introuvable")
    if job.status == JobStatus.PROCESSING:
        raise HTTPException(409, "job déjà en cours")
    job.status = JobStatus.QUEUED
    job.error = None
    store.update(job)
    background.add_task(_run_job, job_id)
    return {"job_id": job_id, "status": "queued"}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, request: Request) -> dict:
    _exige_job(request, job_id)
    ok = store.delete_job(job_id)
    if not ok:
        raise HTTPException(404, "job introuvable")
    return {"deleted": True}


@app.post("/api/admin/cleanup")
def admin_cleanup(request: Request, days: int | None = None,
                  dry_run: bool = False) -> dict:
    """Purge les jobs terminés au-delà de la rétention.

    **Pourquoi.** `security.retention_days` (30 jours) ne déclenchait rien :
    `JobStore.cleanup_temp()` n'était appelé par aucune route, aucune commande.
    La purge conserve l'événement d'audit de chaque job supprimé.

    `days` permet de forcer une valeur pour un appel donné ; `dry_run=true`
    renvoie ce qui serait supprimé sans rien toucher.
    """
    _exige(ADMINISTRATEUR)(request)
    purges = store.cleanup_temp(retention_days=days, dry_run=dry_run)
    return {
        "purged": len(purges),
        "job_ids": purges,
        "dry_run": dry_run,
        "retention_days": days if days is not None
        else cfg.get("security.retention_days", 30),
    }


# ─────────────────────── sauvegarde & restauration (P0) ───────────────────────
# Le magasin est la seule trace des documents traités, des corrections
# humaines et des transmissions. Sans sauvegarde, un `clean` trop large ou un
# disque plein détruit irrémédiablement ce travail.


@app.get("/api/backups")
def lister_sauvegardes() -> dict:
    """Sauvegardes disponibles, la plus récente d'abord."""
    from . import backup as _backup

    repertoire = cfg.data_dir.parent / "sauvegardes"
    return {"repertoire": str(repertoire),
            "sauvegardes": _backup.lister_sauvegardes(repertoire)}


@app.post("/api/backups")
def creer_sauvegarde(request: Request, body: dict | None = None) -> dict:
    """Crée une sauvegarde horodatée et vérifiée du magasin."""
    # rôle exigé : sauvegarder le magasin. RBAC inactif = contrôle sans effet.
    _exige(ADMINISTRATEUR)(request)
    from . import backup as _backup

    body = body or {}
    try:
        res = _backup.creer_sauvegarde(cfg, etiquette=str(body.get("tag") or ""))
    except _backup.BackupError as exc:
        raise HTTPException(409, str(exc)) from exc
    conserver = int(body.get("keep", 5))
    purgees: list[str] = []
    if conserver >= 1:
        purgees = _backup.purger_sauvegardes(res.chemin.parent,
                                            conserver=conserver)
    sortie = res.as_dict()
    sortie["purgees"] = purgees
    return sortie


@app.post("/api/backups/verify")
def verifier_sauvegarde(body: dict, request: Request) -> dict:
    """Contrôle les empreintes d'une sauvegarde avant toute restauration."""
    # rôle exigé : verifier une sauvegarde. RBAC inactif = contrôle sans effet.
    _exige(ADMINISTRATEUR)(request)
    from . import backup as _backup

    chemin = str(body.get("chemin") or "").strip()
    if not chemin:
        raise HTTPException(422, "chemin requis")
    try:
        return _backup.verifier_sauvegarde(Path(chemin))
    except _backup.BackupError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/backups/restore")
def restaurer_sauvegarde(body: dict, request: Request) -> dict:
    """Restaure le magasin. Refuse d'écraser un magasin non vide sans force.

    Restaurer par-dessus ferait disparaître des documents plus récents que la
    sauvegarde : l'opérateur doit le demander explicitement.
    """
    # rôle exigé : restaurer le magasin. RBAC inactif = contrôle sans effet.
    _exige(ADMINISTRATEUR)(request)
    from . import backup as _backup

    chemin = str(body.get("chemin") or "").strip()
    if not chemin:
        raise HTTPException(422, "chemin requis")
    try:
        resultat = _backup.restaurer_sauvegarde(cfg, Path(chemin),
                                                force=bool(body.get("force")))
    except _backup.BackupError as exc:
        raise HTTPException(409, str(exc)) from exc
    # La restauration reecrit data/rbac.json : le registre en memoire de ce
    # processus ne le sait pas. Sans rechargement, les droits restaures
    # resteraient ignores jusqu'au redemarrage — un utilisateur revoque
    # continuerait d'acceder a ses anciens dossiers.
    _recharge_rbac()
    audit(cfg.log_dir, "magasin_restaure", acteur=_acteur(request),
          fichiers=resultat.get("fichiers"))
    return resultat


@app.get("/api/stats")
def stats() -> dict:
    jobs = store.list_jobs(limit=1000)
    done = [j for j in jobs if j.status == JobStatus.DONE]
    errors = [j for j in jobs if j.status == JobStatus.ERROR]
    import psutil
    return {
        "jobs_total": len(jobs),
        "jobs_done": len(done),
        "jobs_error": len(errors),
        "jobs_processing": sum(1 for j in jobs if j.status == JobStatus.PROCESSING),
        "mean_progress": round(sum(j.progress for j in jobs) / max(1, len(jobs)), 3),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "engines": registry.list_engines(),
    }


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    index_path = cfg.web_dir / "index.html"
    if not index_path.is_file():
        return HTMLResponse("<h1>UniOCR</h1><p>UI non installée. API : /docs</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ─────────────────────────── Recherche & révision ───────────────────────────
# Ajouts purs : aucun endpoint existant n'est modifié.

REVIEW_FLAGGED = ("invalid", "ambiguous", "not_detected")


@app.get("/api/review")
def review_queue(
    request: Request,
    limit: int = Query(50, le=500),
    threshold: float = Query(0.75, ge=0.0, le=1.0),
    include_undetected: bool = Query(False),
) -> dict:
    """File de révision humaine.

    Parcourt les documents terminés et remonte les champs `invalid`,
    `ambiguous`, ou dont la confiance est sous le seuil. Les champs
    `not_detected` sont exclus par défaut : un champ absent n'est pas une
    erreur à trancher (sur le jeu de test, ils représentent ~83 % des
    entrées et noieraient la file). `include_undetected=true` les rajoute.
    """
    items: list[dict] = []
    visibles = (j for j in store.list_jobs(limit=10000)
                if _job_visible(request, j.id))
    parcourus = 0
    for j in visibles:
        if parcourus >= limit:
            break
        parcourus += 1
        if j.status != JobStatus.DONE:
            continue
        res = store.load_result(j.id)
        if not res:
            continue
        flagged = []
        for name, fv in (res.get("fields") or {}).items():
            status = fv.get("status", "")
            conf = float(fv.get("confidence") or 0.0)
            if status == "validated":
                continue
            if status == "not_detected" and not include_undetected:
                continue
            reasons = []
            if status in REVIEW_FLAGGED:
                reasons.append(status)
            if conf < threshold:
                reasons.append(f"confiance {round(conf * 100)}%")
            if not reasons:
                continue
            flagged.append({
                "field": name,
                "label": fv.get("label") or name,
                "value": fv.get("raw_value") or fv.get("normalized_value") or "",
                "status": status,
                "confidence": conf,
                "reasons": reasons,
            })
        if not flagged:
            continue
        items.append({
            "job_id": j.id,
            "filename": j.filename,
            "created_at": j.created_at,
            "profile": (j.options.profile if j.options else None),
            "fields": flagged,
        })
    return {
        "documents": len(items),
        "fields": sum(len(i["fields"]) for i in items),
        "threshold": threshold,
        "include_undetected": include_undetected,
        "items": items,
    }


@app.get("/api/search")
def search(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=100),
) -> dict:
    """Recherche plein texte inter-documents (champs + texte reconnu).

    Balaye les résultats stockés localement. Coût proportionnel au nombre
    de documents — acceptable pour un déploiement local, à remplacer par un
    index dédié au-delà de quelques centaines de documents.
    """
    needle = q.lower()
    hits: list[dict] = []

    def add(hit: dict) -> bool:
        hits.append(hit)
        return len(hits) >= limit

    # les dossiers d'abord : chercher « DOSSIER-… » doit trouver le dossier,
    # pas seulement les documents qu'il contient
    for dos_obj in _dossiers.liste():
        dos = dos_obj.as_dict()
        utilisateur = _utilisateur_courant(request)
        if utilisateur is not None and not utilisateur.voit_dossier(dos_obj.id):
            continue
        intitule = " ".join(str(dos.get(k) or "") for k in
                            ("id", "label", "profile", "state_label")).lower()
        if needle in intitule:
            if add({
                "dossier_id": dos.get("id"),
                "filename": dos.get("label") or dos.get("id"),
                "kind": "dossier",
                "label": dos.get("label") or "",
                "state": dos.get("state_label") or dos.get("state") or "",
                "pieces": len(dos.get("pieces") or []),
            }):
                return _search_payload(q, hits, limit)

    for j in store.list_jobs(limit=10000):
        if not _job_visible(request, j.id):
            continue
        res = store.load_result(j.id)
        if not res:
            continue
        for name, fv in (res.get("fields") or {}).items():
            blob = " ".join(
                str(fv.get(k) or "")
                for k in ("raw_value", "normalized_value", "confirmed_value",
                          "corrected_value", "label")
            ).lower()
            if needle in blob:
                if add({
                    "job_id": j.id,
                    "filename": j.filename,
                    "kind": "field",
                    "field": name,
                    "label": fv.get("label") or name,
                    "value": fv.get("raw_value") or fv.get("normalized_value") or "",
                    "status": fv.get("status", ""),
                }):
                    return _search_payload(q, hits, limit)
        for p in (res.get("pages") or []):
            text = p.get("text") or ""
            idx = text.lower().find(needle)
            if idx < 0:
                continue
            a, b = max(0, idx - 60), min(len(text), idx + len(needle) + 60)
            if add({
                "job_id": j.id,
                "filename": j.filename,
                "kind": "text",
                "page": p.get("page_num"),
                "snippet": text[a:b].replace("\n", " ").strip(),
            }):
                return _search_payload(q, hits, limit)
    return _search_payload(q, hits, limit)


def _search_payload(q: str, hits: list[dict], limit: int) -> dict:
    return {
        "query": q,
        "returned": len(hits),
        "truncated": len(hits) >= limit,
        "hits": hits,
    }


# ─────────────── recherche transverse & amorçage de la coque ───────────────

def _magasin(request: Request, nom: str) -> dict:
    """Lit un store `app.state` sans le créer (recherche en lecture seule)."""
    magasin = getattr(request.app.state, nom, None)
    return magasin if isinstance(magasin, dict) else {}


def _champ(objet: object, nom: str, defaut: str = "") -> str:
    valeur = getattr(objet, nom, defaut)
    return str(valeur) if valeur is not None else defaut


@app.get("/api/search/global")
def search_global(
    request: Request,
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(6, ge=1, le=20),
) -> dict:
    """Recherche transverse : dossiers, clients, B/L, conteneurs, documents.

    Un dossier est trouvé par identifiant, libellé, référence, client,
    fournisseur, B/L, conteneur, scellé, navire ou code SH. Les autres
    groupes lisent les stores du serveur et restent vides s'ils n'ont pas
    encore d'enregistrement : aucune entrée n'est fabriquée.
    """
    terme = q.strip().lower()

    def contient(*valeurs: object) -> bool:
        return terme in " ".join(str(v or "") for v in valeurs).lower()

    utilisateur = _utilisateur_courant(request)
    groupes: dict[str, list[dict]] = {
        "dossiers": [], "clients": [], "connaissements": [], "conteneurs": [], "documents": [],
    }
    total = 0

    for dossier in _dossiers.liste():
        if len(groupes["dossiers"]) >= limit:
            break
        if utilisateur is not None and not utilisateur.voit_dossier(dossier.id):
            continue
        conteneurs = " ".join(str(c) for c in (getattr(dossier, "conteneurs_associes", []) or []))
        if not contient(dossier.id, dossier.reference, dossier.label, dossier.client_importateur,
                        dossier.fournisseur, dossier.reference_bl, dossier.numero_conteneur,
                        dossier.numero_scelle, dossier.navire, dossier.code_sh, conteneurs):
            continue
        groupes["dossiers"].append({
            "kind": "dossier",
            "id": dossier.id,
            "label": dossier.label or dossier.id,
            "reference": dossier.reference or dossier.id,
            "meta": dossier.state.value.replace("_", " "),
            "client": dossier.client_importateur or "",
            "route": "dossiers/tous",
        })
        total += 1

    for identifiant, client in _magasin(request, "client_store").items():
        if len(groupes["clients"]) >= limit:
            break
        if contient(identifiant, _champ(client, "name"), _champ(client, "legal_name"),
                    _champ(client, "tax_id"), _champ(client, "email")):
            groupes["clients"].append({
                "kind": "client",
                "id": identifiant,
                "label": _champ(client, "name") or identifiant,
                "meta": _champ(client, "legal_name"),
                "route": "dossiers/clients",
            })
            total += 1

    for identifiant, bl in _magasin(request, "bl_store").items():
        if len(groupes["connaissements"]) >= limit:
            break
        if contient(identifiant, _champ(bl, "numero_bl"), _champ(bl, "chargeur"),
                    _champ(bl, "destinataire"), _champ(bl, "navire"),
                    _champ(bl, "port_decharge"), _champ(bl, "marchandise")):
            groupes["connaissements"].append({
                "kind": "bl",
                "id": identifiant,
                "label": _champ(bl, "numero_bl") or identifiant,
                "meta": _champ(bl, "port_decharge") or _champ(bl, "dossier_id"),
                "route": "maritime/bl",
            })
            total += 1

    for identifiant, conteneur in _magasin(request, "conteneur_store").items():
        if len(groupes["conteneurs"]) >= limit:
            break
        if contient(identifiant, _champ(conteneur, "numero_conteneur"),
                    _champ(conteneur, "seal_number"), _champ(conteneur, "position_actuelle"),
                    _champ(conteneur, "dossier_id")):
            groupes["conteneurs"].append({
                "kind": "conteneur",
                "id": identifiant,
                "label": _champ(conteneur, "numero_conteneur") or identifiant,
                "meta": _champ(conteneur, "statut"),
                "route": "maritime/conteneurs",
            })
            total += 1

    for job in store.list_jobs(limit=500):
        if len(groupes["documents"]) >= limit:
            break
        if not _job_visible(request, job.id):
            continue
        if contient(job.id, job.filename):
            groupes["documents"].append({
                "kind": "document",
                "id": job.id,
                "label": job.filename or job.id,
                "meta": str(getattr(job.status, "value", job.status)),
                "route": "documents/ocr",
            })
            total += 1

    return {"query": q, "total": total, "limite_par_groupe": limit, "groupes": groupes}


@app.get("/api/ui/bootstrap")
def ui_bootstrap(request: Request) -> dict:
    """Tout ce dont la coque a besoin à l'affichage : identité et compteurs.

    Les compteurs sont recalculés sur les dossiers réels ; une clé absente
    côté serveur vaut zéro plutôt que d'inventer une valeur.
    """
    utilisateur = _utilisateur_courant(request)
    identite = utilisateur.public() if utilisateur is not None else None

    etats: dict[str, int] = {}
    total = 0
    visibles = 0
    for dossier in _dossiers.liste():
        total += 1
        if utilisateur is not None and not utilisateur.voit_dossier(dossier.id):
            continue
        visibles += 1
        etat = dossier.state.value
        etats[etat] = etats.get(etat, 0) + 1

    en_cours = sum(etats.get(e, 0) for e in
                   ("en_preparation", "traitement_en_cours", "revision_requise",
                    "incomplet", "en_validation"))
    a_valider = sum(etats.get(e, 0) for e in ("en_validation", "revision_requise"))
    clos = sum(etats.get(e, 0) for e in ("exporte", "archive"))
    bloques = etats.get("incomplet", 0) + etats.get("erreur_traitement", 0)

    notifications = _magasin(request, "notification_store")
    non_lues = sum(1 for n in notifications.values() if not getattr(n, "lue", False))

    return {
        "utilisateur": identite,
        "rbac_actif": identite is not None,
        "compteurs": {
            "dossiers": visibles,
            "dossiers_total": total,
            "dossiers_en_cours": en_cours,
            "dossiers_a_valider": a_valider,
            "dossiers_clos": clos,
            "dossiers_bloques": bloques,
            "notifications_non_lues": non_lues,
        },
        "etats": etats,
    }


# ─────────────────────── traitement par lots ───────────────────────
# Ajouts purs : POST /api/documents et les exports unitaires sont intacts.

@app.post("/api/batches")
async def upload_batch(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    profile: str = Form("generic"),
    languages: str = Form(""),
    quality_mode: str = Form("accurate"),
    preprocess: str = Form("true"),
    preprocess_mode: str = Form("standard"),
    variant_comparison: str = Form("true"),
    export_formats: str = Form("json,txt"),
    page_range: str = Form(""),
    render_dpi: int = Form(200),
    engine: str = Form("auto"),
    extract_fields: str = Form("true"),
    extract_tables: str = Form("true"),
    extract_barcodes: str = Form("true"),
    min_confidence_review: float = Form(0.7),
    dedupe: str = Form("true"),
) -> dict:
    """Envoi de plusieurs documents en une requête.

    Renvoie un identifiant de lot et, pour chaque fichier, le job créé —
    ou le job existant lorsque l'empreinte correspond à un document déjà
    traité (`cached: true`). Les fichiers invalides sont écartés et
    signalés dans `rejected` ; ils ne font pas échouer le lot.
    """
    import hashlib
    import tempfile

    from .models import new_id
    from .security import SecurityError, sanitize_filename, validate_file

    batch_id = new_id("batch_")
    langs = [ln.strip() for ln in languages.split(",") if ln.strip()]
    fmts = [f.strip() for f in export_formats.split(",") if f.strip()]
    options = JobOptions(
        languages=langs, profile=profile or "generic",
        quality_mode=quality_mode, preprocess=_form_bool(preprocess),
        preprocess_mode=preprocess_mode if preprocess_mode in ("off", "standard", "aggressive") else "standard",
        variant_comparison=_form_bool(variant_comparison),
        export_formats=fmts or ["json", "txt"],
        page_range=page_range or "",
        render_dpi=max(72, min(400, render_dpi)),
        engine=engine if engine in ("auto", "tesseract", "native") else "auto",
        extract_fields=_form_bool(extract_fields),
        extract_tables=_form_bool(extract_tables),
        extract_barcodes=_form_bool(extract_barcodes),
        min_confidence_review=max(0.0, min(1.0, min_confidence_review)),
    )
    max_bytes = int(cfg.get("max_file_size_mb", 50)) * 1024 * 1024
    max_batch_bytes = int(cfg.get("max_batch_size_mb", 200)) * 1024 * 1024
    if len(files) > 200:
        raise HTTPException(413, "lot trop important (200 documents maximum)")

    jobs: list[dict] = []
    rejected: list[dict] = []
    octets_lus = 0
    for index, up in enumerate(files):
        fname = sanitize_filename(up.filename or "document")
        restant = max(0, max_batch_bytes - octets_lus)
        limite_fichier = min(max_bytes, restant)
        try:
            data = await _read_upload_limited(up, limite_fichier)
            octets_lus += len(data)
            with tempfile.NamedTemporaryFile(suffix=Path(fname).suffix or ".bin",
                                             delete=False) as tf:
                tf.write(data)
                tmp = Path(tf.name)
            try:
                validate_file(
                    tmp, max_size_mb=cfg.get("max_file_size_mb", 50),
                    max_zip_uncompressed_mb=cfg.get("security.max_zip_uncompressed_mb", 200),
                    max_zip_ratio=cfg.get("security.max_zip_ratio", 100))
            finally:
                tmp.unlink(missing_ok=True)

            if _form_bool(dedupe):
                existing = store.find_by_hash(hashlib.sha256(data).hexdigest())
                if existing is not None:
                    jobs.append({"job_id": existing.id, "filename": existing.filename,
                                 "status": existing.status.value, "cached": True})
                    audit(cfg.log_dir, "job_deduped", batch_id=batch_id,
                          job_id=existing.id, filename=fname, source="batch")
                    continue
            job = store.create_job(fname, data, options)
            jobs.append({"job_id": job.id, "filename": job.filename,
                         "status": job.status.value, "cached": False})
            background.add_task(_run_job, job.id)
        except SecurityError as exc:
            rejected.append({"filename": fname, "error": str(exc)})
        except _UploadTooLarge:
            rejected.append({"filename": fname, "error": "limite de taille dépassée"})
            if restant < max_bytes:
                rejected.extend({"filename": sanitize_filename(item.filename or "document"),
                                 "error": "limite totale du lot dépassée"}
                                for item in files[index + 1:])
                break
        except OSError as exc:  # lecture impossible : on écarte le fichier
            rejected.append({"filename": fname, "error": f"illisible : {exc}"})

    audit(cfg.log_dir, "batch_created", batch_id=batch_id,
          accepted=len(jobs), rejected=len(rejected), profile=options.profile)
    return {"batch_id": batch_id, "jobs": jobs, "rejected": rejected,
            "accepted": len(jobs)}


@app.get("/api/batches/export/{fmt}")
def export_batch(request: Request, fmt: str,
                 ids: str = Query(..., min_length=1)) -> FileResponse:
    """Export groupé de plusieurs documents.

    - `xlsx` : une feuille par document (reprenant les feuilles unitaires)
    - `csv` : un fichier long, colonne `document` en première position
    - `json` : tableau des résultats complets
    - `txt` : concaténation séparée par document
    - tout autre format : archive ZIP des exports unitaires
    """
    import zipfile

    job_ids = [i.strip() for i in ids.split(",") if i.strip()]
    if not job_ids:
        raise HTTPException(400, "aucun identifiant de job fourni")
    if len(job_ids) > 200:
        raise HTTPException(413, "lot trop important (200 documents maximum)")

    results = []
    for jid in job_ids:
        _exige_job(request, jid)
        job = store.get(jid)
        if job is None:
            raise HTTPException(404, f"job '{jid}' introuvable")
        res = store.load_result(jid)
        if res is None:
            raise HTTPException(409, f"résultat pas encore disponible pour '{jid}'")
        results.append((job.filename, res))

    out_dir = store.export_dir("batch_" + "_".join(job_ids)[:60])
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        path = out_dir / f"lot_{stamp}.json"
        path.write_text(json.dumps([r for _, r in results], ensure_ascii=False,
                                   indent=2), encoding="utf-8")
    elif fmt == "txt":
        path = out_dir / f"lot_{stamp}.txt"
        parts = [f"══════════ {fn} ══════════\n" +
                 "\n\n".join(f"───── Page {p.get('page_num')} ─────\n{p.get('text','')}"
                             for p in (r.get("pages") or []))
                 for fn, r in results]
        path.write_text("\n\n".join(parts), encoding="utf-8")
    elif fmt == "csv":
        import csv

        path = out_dir / f"lot_{stamp}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["document", "champ", "valeur_brute", "valeur_normalisee",
                        "confiance", "statut"])
            for fn, r in results:
                for name, fv in (r.get("fields") or {}).items():
                    w.writerow([
                        sanitize_for_csv(fn), sanitize_for_csv(name),
                        sanitize_for_csv(fv.get("raw_value")),
                        sanitize_for_csv(fv.get("normalized_value")),
                        fv.get("confidence"), fv.get("status"),
                    ])
    elif fmt == "xlsx":
        path = out_dir / f"lot_{stamp}.xlsx"
        _merge_xlsx(results, path)
    else:
        # archive des exports unitaires
        path = out_dir / f"lot_{stamp}.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn, r in results:
                single = out_dir / Path(fn).stem
                single.mkdir(exist_ok=True)
                for f in export_all(r, single):
                    zf.write(f, arcname=f"{Path(fn).stem}/{f.name}")

    audit(cfg.log_dir, "batch_exported", fmt=fmt, documents=len(results))
    return FileResponse(str(path), filename=path.name,
                        media_type="application/octet-stream")


def _merge_xlsx(results: list[tuple[str, dict]], out: Path) -> None:
    """Un classeur par document : concatène les feuilles unitaires.

    Les valeurs sont recopiées (les styles ne sont pas transportés) : le
    contenu est fidèle, la mise en page reste celle du classeur généré.
    """
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    used: set[str] = set()

    def uniq(base: str) -> str:
        name = base[:31] or "feuille"
        n, cand = 1, name
        while cand.lower() in used:
            n += 1
            cand = f"{name[:28]}~{n}"
        used.add(cand.lower())
        return cand

    from .models import DocumentResult

    for fn, res in results:
        tmp = out.parent / ("_single_" + Path(fn).stem + ".xlsx")
        try:
            export_xlsx(DocumentResult.model_validate(res), tmp)
            src = openpyxl.load_workbook(tmp)
            for ws in src.worksheets:
                nws = wb.create_sheet(uniq(ws.title))
                for row in ws.iter_rows():
                    for c in row:
                        if c.value is None:
                            continue
                        nws.cell(row=c.row, column=c.column, value=c.value)
                for col, dim in ws.column_dimensions.items():
                    if dim.width:
                        nws.column_dimensions[col].width = dim.width
            src.close()
        finally:
            tmp.unlink(missing_ok=True)
    wb.save(out)


# ─────────────────────── journal d'audit consultable ───────────────────────

@app.get("/api/audit")
def audit_log(
    limit: int = Query(100, le=1000),
    event: str = Query("", description="filtre exact sur le type d'événement"),
    q: str = Query("", description="filtte libre sur le contenu"),
) -> dict:
    """Journal d'audit JSONL, événements les plus récents d'abord.

    Le journal est la source de vérité : aucune ligne n'est modifiée ni
    reformatée, seules les clés techniques (ts, job_id) sont exposées.
    """
    path = cfg.log_dir / "audit.log"
    rows: list[dict] = []
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in reversed(lines):
            if len(rows) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event and entry.get("event") != event:
                continue
            if q and q.lower() not in json.dumps(entry, ensure_ascii=False).lower():
                continue
            rows.append(entry)
    events = sorted({r.get("event", "?") for r in rows})
    return {"entries": rows, "returned": len(rows), "events": events,
            "filters": {"event": event, "q": q}}


@app.post("/api/profiles/test")
def test_profile(body: dict, request: Request) -> dict:
    """Teste un profil (non enregistré) contre un document réel.

    Corps : `{"profile": {...}, "job_id": "..."}`, `{"profile": {...}, "text": "..."}`
    ou `{"profile": "nom_du_profil", "text": "..."}` (profil déjà enregistré).
    Rien n'est écrit : c'est un essai à blanc.
    """
    payload = body.get("profile")
    if isinstance(payload, str):
        # profil existant (utilisateur ou livré) désigné par son nom
        name = payload.strip()
        if not name:
            raise HTTPException(400, "nom de profil vide")
        known = load_all_profiles(cfg.profiles_dir, cfg.user_profiles_dir)
        if name not in known:
            raise HTTPException(404, f"profil inconnu : {name}")
        prof = known[name]
    elif isinstance(payload, dict):
        try:
            prof = Profile.model_validate(payload)
        except Exception as exc:
            raise HTTPException(400, f"profil invalide : {exc}")
    else:
        raise HTTPException(400, "corps « profile » manquant (nom ou définition)")

    res = None
    job_id = body.get("job_id")
    if job_id:
        _exige_job(request, str(job_id))
        res = store.load_result(job_id)
        if res is None:
            raise HTTPException(409, "résultat pas encore disponible")
        text = "\n\n".join(p.get("text", "") for p in (res.get("pages") or []))
    else:
        text = body.get("text") or ""
    if not text.strip():
        raise HTTPException(400, "fournissez 'text' ou 'job_id'")

    from .extract_fields import locate_value

    def locate(value):
        try:
            return locate_value(res.get("pages") or [], value)
        except Exception:
            return (1, None, 0.0)

    try:
        fields = apply_profile(text, prof, locate=locate)
    except Exception as exc:
        raise HTTPException(400, f"extraction impossible : {exc}")
    return {"profile": prof.name,
            "fields": {k: v.model_dump(mode="json") for k, v in fields.items()},
            "detected": sum(1 for v in fields.values() if v.status.value == "detected"),
            "total": len(fields)}


# ─────────────── parcours documentaire : classification, dossier, paquet ───────────────
# Ces routes exposent les étapes 4 (classification), 8 (cohérence interdocumentaire),
# 11 (dossier) et 13 (paquet de données). Elles s'appuient sur les modules dédiés ;
# aucune ne simule un résultat.

from .classification import (  # noqa: E402
    CLASSIFIER_VERSION,
    DocumentClassifier,
    classification_manuelle,
    consigne_classification,
)
from .coherence import ChampDocument, CoherenceEngine  # noqa: E402
from .dossier import (  # noqa: E402
    LIBELLES_ETATS,
    PROFILS_DOSSIER,
    DossierState,
    DossierStore,
)
from .packaging import (  # noqa: E402
    DocumentPaquet,
    consigne_paquet,
    genere_json,
    genere_xlsx,
    genere_zip,
)

_dossiers = DossierStore(cfg.data_dir / "dossiers", log_dir=cfg.log_dir)
_classifier = DocumentClassifier(profiles_dir=cfg.profiles_dir,
                                 user_types_dir=cfg.data_dir / "document_types")
_coherence = CoherenceEngine(cfg.get("coherence") or {})


def _texte_resultat(result: dict) -> str:
    """Texte d'un résultat (dictionnaire JSON), pour la classification."""
    morceaux = [str(result.get("source_file") or "")]
    for page in result.get("pages") or []:
        for bloc in page.get("blocks") or []:
            morceaux.append(str(bloc.get("text") or ""))
    return "\n".join(morceaux)


def _etats_documents(dossier) -> dict:
    """État réel de chaque pièce, déduit du job et de ses champs.

    - `status` : celui du job (queued / processing / done / error) ;
    - `needs_review` : un champ reste à trancher (ambiguous, invalid, detected) ;
    - `valide` : tous les champs ont été regardés par un humain (validated).

    Aucun de ces états n'est posé par un bouton : ils sont lus.
    """
    etats = {}
    for piece in dossier.pieces:
        job = store.get(piece.job_id)
        if job is None:
            etats[piece.job_id] = {"status": "error", "needs_review": True,
                                   "valide": False}
            continue
        result = store.load_result(piece.job_id) or {}
        champs = result.get("fields") or {}
        a_revoir = any(f.get("status") in ("detected", "ambiguous", "invalid")
                       for f in champs.values())
        valide = bool(champs) and all(f.get("status") == "validated"
                                      for f in champs.values())
        etats[piece.job_id] = {
            "status": job.status.value,
            "needs_review": a_revoir,
            "valide": valide,
        }
    return etats


def _champs_pour_coherence(result: dict, job_id: str, filename: str,
                           category: str) -> list[ChampDocument]:
    """Champs extraits d'un document, vus par le moteur de cohérence.

    La valeur retenue suit la même priorité que `FieldValue.value` :
    confirmée > corrigée > normalisée > brute.
    """
    champs = []
    for nom, fv in (result.get("fields") or {}).items():
        valeur = (fv.get("confirmed_value") or fv.get("corrected_value")
                  or fv.get("normalized_value") or fv.get("raw_value"))
        champs.append(ChampDocument(
            job_id=job_id, filename=filename, category=category,
            key=nom, value=valeur, label=fv.get("label") or nom))
    return champs


@app.get("/api/document-types")
def document_types() -> dict:
    """Catégories documentaires connues, y compris celles sans indice.

    Les catégories désactivées sont renvoyées telles quelles : les cacher
    laisserait croire qu'elles sont détectables.
    """
    return {
        "classifier_version": CLASSIFIER_VERSION,
        "categories": [
            {"id": c.id, "label": c.label, "source": c.source,
             "active": c.active, "profile": c.profil,
             "indicators": len(c.indicateurs)}
            for c in _classifier.categories.values()
        ],
        "disabled": _classifier.disabled_categories(),
    }


@app.post("/api/jobs/{job_id}/classify")
def classify_job(job_id: str, request: Request) -> dict:
    """Classe un document traité et consigne le résultat."""
    _exige_job(request, job_id)
    result = store.load_result(job_id)
    if result is None:
        raise HTTPException(404, "résultat introuvable : traitez d'abord le document")
    res = _classifier.classify(_texte_resultat(result))
    consigne_classification(cfg.log_dir, job_id, res)
    return {"job_id": job_id, "classification": res.as_dict(),
            "profile_suggere": _classifier.profil_pour(res.category)}


@app.get("/api/jobs/{job_id}/classification")
def get_classification(job_id: str, request: Request) -> dict:
    """Classification retenue pour un document, avec ses preuves.

    La valeur affichée est celle du résultat (donc après correction manuelle
    éventuelle) ; le journal d'audit n'apporte que l'horodatage et le fait
    qu'une décision humaine soit intervenue. Renvoyer le seul journal ferait
    disparaître libellé, preuves et alternatives — soit les sources mêmes qui
    permettent de contester une classification.
    """
    _exige_job(request, job_id)
    import json as _json

    journal = cfg.log_dir / "audit.log"
    trace = None
    if journal.is_file():
        for ligne in journal.read_text(encoding="utf-8").splitlines():
            if "document_classified" not in ligne:
                continue
            try:
                entree = _json.loads(ligne)
            except ValueError:
                continue
            if entree.get("job_id") == job_id:
                trace = entree
    resultat = store.load_result(job_id)
    retenue = (resultat or {}).get("classification")
    if retenue is None:
        if trace is None:
            return {"job_id": job_id, "classification": None}
        retenue = {k: trace.get(k) for k in
                   ("category", "confidence", "classifier_version",
                    "needs_review", "manual")}
    payload = dict(retenue)
    if trace is not None:
        payload["ts"] = trace.get("ts")
        # une correction humaine consignée après coup reste une correction
        payload["manual"] = bool(payload.get("manual")) or bool(trace.get("manual"))
    return {"job_id": job_id, "classification": payload}


@app.patch("/api/jobs/{job_id}/classification")
def patch_classification(job_id: str, request: Request, body: dict) -> dict:
    """Correction manuelle de la catégorie (document inconnu classé à la main)."""
    _exige_job(request, job_id)
    categorie = str(body.get("category") or "").strip()
    acteur = str(body.get("user") or "utilisateur")
    if not categorie:
        raise HTTPException(422, "catégorie requise")
    try:
        res = classification_manuelle(categorie, acteur,
                                      categories=set(_classifier.categories))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    consigne_classification(cfg.log_dir, job_id, res, manuel=True)
    return {"job_id": job_id, "classification": res.as_dict(),
            "profile_suggere": _classifier.profil_pour(categorie)}


# ─────────────────────────── dossiers ───────────────────────────

@app.post("/api/dossiers")
def creer_dossier(body: dict, request: Request) -> dict:
    # rôle exigé : creer un dossier. RBAC inactif = contrôle sans effet.
    _exige(OPERATEUR)(request)
    # `ref`/`reference` sont acceptés comme libellé : le formulaire Transit
    # envoie une référence, l'écran Dossiers un libellé — les deux désignent
    # le même champ, et refuser l'un des deux rendait le formulaire inutilisable.
    label = str(body.get("label") or body.get("ref") or body.get("reference") or "").strip()
    if not label:
        raise HTTPException(422, "libellé de dossier requis")
    profil = str(body.get("profile") or "personnalise")
    if profil not in PROFILS_DOSSIER:
        raise HTTPException(422, f"profil inconnu : {profil}")
    acteur = str(body.get("user") or "utilisateur")
    dossier = _dossiers.creer(label, profil, acteur=acteur)
    # Champs facultatifs fournis à la création (client, référence, priorité…).
    champs_initiaux = {
        nom: body[cle] for cle, nom in (
            ("client", "client_importateur"),
            ("client_importateur", "client_importateur"),
            ("reference", "reference"),
            ("priorite", "priorite"),
            ("gestionnaire", "gestionnaire"),
            ("port_chargement", "port_chargement"),
            ("port_destination", "port_destination"),
        ) if body.get(cle) not in (None, "")
    }
    if champs_initiaux:
        dossier = _dossiers.mettre_a_jour(dossier.id, champs_initiaux, acteur=acteur) or dossier
    # Un opérateur au périmètre restreint doit voir le dossier qu'il vient de
    # créer : son identifiant est généré par le système, il ne peut pas figurer
    # à l'avance dans son périmètre. Sans cet ajout, créer un dossier le
    # rendrait invisible à son auteur — un cloisonnement qui bloque son
    # propre travail n'est pas un cloisonnement, c'est un bug.
    _etend_perimetre_si_restreint(request, dossier.id)
    return dossier.as_dict()


def _etend_perimetre_si_restreint(request, dossier_id: str) -> None:
    """Ajoute un dossier au périmètre de son créateur s'il est restreint.

    Ne fait rien pour un utilisateur à périmètre « tous » (rien à étendre) ni
    quand le RBAC est inactif. L'ajout est tracé dans l'audit : un
    cloisonnement qui s'élargit tout seul doit être visible.
    """
    u = _utilisateur_courant(request)
    if u is None or TOUS in u.dossiers or dossier_id in u.dossiers:
        return
    try:
        _rbac.maj(u.nom, dossiers=sorted(set(u.dossiers) | {dossier_id}))
    except RBACError as exc:      # périmètre non extensible : on le dit
        log.warning("périmètre non étendu pour %s : %s", u.nom, exc)
        return
    audit(cfg.log_dir, "rbac_perimetre_etendu", acteur=u.nom,
          dossier=dossier_id, motif="creation par l'utilisateur")


@app.get("/api/dossiers")
def liste_dossiers(request: Request) -> list[dict]:
    """Dossiers visibles. Le cloisonnement filtre la liste, pas seulement l'accès.

    Renvoyer tous les dossiers puis laisser un 403 à l'ouverture révélerait
    l'existence de dossiers hors périmètre et nuirait à la navigation.
    """
    u = _utilisateur_courant(request)
    dossiers = _dossiers.liste()
    if u is not None:
        dossiers = [d for d in dossiers if u.voit_dossier(d.id)]
    return [d.as_dict() for d in dossiers]


@app.get("/api/dossiers/{dossier_id}")
def get_dossier(dossier_id: str, request: Request) -> dict:
    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    _exige_dossier(dossier_id, request)
    dossier = _dossiers.recalculer_etat(dossier_id, _etats_documents(dossier))
    return _dossiers.synthese(dossier)


@app.delete("/api/dossiers/{dossier_id}")
def supprimer_dossier(dossier_id: str, request: Request) -> dict:
    """Supprime le dossier — les documents, eux, restent en place."""
    _exige_dossier(dossier_id, request)
    from .business_links import exiger_dossier, exiger_dossier_sans_liens
    from .business_store import BusinessStore
    from .models import DeclarationDouaniere

    magasin = BusinessStore(cfg.data_dir / "metier.sqlite3", "declaration", DeclarationDouaniere)
    with magasin.transaction() as transaction:
        exiger_dossier(cfg, dossier_id, absent=404)
        exiger_dossier_sans_liens(transaction, dossier_id)
        if not _dossiers.supprimer(dossier_id, acteur="utilisateur"):
            raise HTTPException(404, "dossier introuvable")
    return {"deleted": True}


@app.post("/api/dossiers/{dossier_id}/pieces")
def ajouter_piece(dossier_id: str, body: dict, request: Request) -> dict:
    _exige_dossier(dossier_id, request)
    job_id = str(body.get("job_id") or "").strip()
    if not job_id:
        raise HTTPException(422, "job_id requis")
    if store.get(job_id) is None:
        raise HTTPException(404, f"document introuvable : {job_id}")
    _exige_job(request, job_id)
    # Le client n'a pas à connaître le nom ni le type du document : on les
    # relit dans le résultat. Les replir à la main ferait apparaître des
    # identifiants techniques (« job_… », « unknown ») dans les constats de
    # cohérence que l'utilisateur doit trancher.
    resultat = store.load_result(job_id) or {}
    filename = str(body.get("filename") or "").strip() or str(
        resultat.get("source_file") or job_id)
    category = str(body.get("category") or "").strip()
    if not category or category == "unknown":
        category = str((resultat.get("classification") or {}).get("category")
                       or resultat.get("info", {}).get("doc_type") or "unknown")
    try:
        dossier = _dossiers.ajouter_piece(
            dossier_id, job_id, filename,
            category=category,
            sha256=str(body.get("sha256") or ""),
            acteur=str(body.get("user") or "utilisateur"))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    dossier = _dossiers.recalculer_etat(dossier_id, _etats_documents(dossier))
    return _dossiers.synthese(dossier)


@app.delete("/api/dossiers/{dossier_id}/pieces/{job_id}")
def retirer_piece(dossier_id: str, job_id: str, request: Request) -> dict:
    _exige_dossier(dossier_id, request)
    try:
        dossier = _dossiers.retirer_piece(dossier_id, job_id, acteur="utilisateur",
                                          motif="retrait depuis l'interface")
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    dossier = _dossiers.recalculer_etat(dossier_id, _etats_documents(dossier))
    return _dossiers.synthese(dossier)


@app.post("/api/dossiers/{dossier_id}/state")
def forcer_etat_dossier(dossier_id: str, body: dict, request: Request) -> dict:
    """Changement d'état explicite (export, archivage), tracé et motivé."""
    _exige_dossier(dossier_id, request)
    etat = str(body.get("state") or "").strip()
    try:
        cible = DossierState(etat)
    except ValueError as exc:
        raise HTTPException(422, f"état inconnu : {etat}") from exc
    try:
        dossier = _dossiers.forcer_etat(dossier_id, cible, acteur="utilisateur",
                                        motif=str(body.get("motif") or ""))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return dossier.as_dict()


def _constats_coherence(dossier) -> tuple[list, int]:
    """Constats de cohérence d'un dossier + nombre de documents analysés.

    Extrait de la route `coherence` pour que l'aperçu de transmission puisse
    signaler les anomalies non tranchées sans dupliquer la collecte.

    Renvoie un tuple parce que `Constat` ne porte pas de `job_id` : le nombre
    de documents analysés ne peut pas être recalculé depuis les constats.
    """
    champs: list[ChampDocument] = []
    empreintes: dict[str, str] = {}
    for piece in dossier.pieces:
        if piece.sha256:
            empreintes[piece.job_id] = piece.sha256
        result = store.load_result(piece.job_id)
        if result is None:
            continue
        champs += _champs_pour_coherence(result, piece.job_id, piece.filename,
                                         piece.category)
    profil = PROFILS_DOSSIER.get(dossier.profile)
    attendus = {}
    if profil:
        # on attend la référence de facture dans les autres pièces du profil
        if any(p.category == "invoice" for p in profil.pieces):
            autres = [p.category for p in profil.pieces if p.category != "invoice"]
            attendus["invoice_number"] = autres
    constats = _coherence.analyser(champs, attendus=attendus, empreintes=empreintes)
    _reappliquer_arbitrages(dossier, constats)
    return constats, len({c.job_id for c in champs})


def anomalies_coherence(dossier) -> list[dict]:
    """Anomalies qu'aucun humain n'a tranchées, au format de l'aperçu.

    Une anomalie déjà arbitrée (`accepte`, `corrige`, `ignore`) ne bloque
    plus rien : quelqu'un a décidé, et sa décision est respectée.
    """
    tranchees = {"accepte", "corrige", "ignore"}
    sortie = []
    for c in _constats_coherence(dossier)[0]:
        if c.status in tranchees or c.resultat == "ok":
            continue
        sortie.append({"champ": (c.champs[0].get("key") if c.champs else ""),
                       "regle": c.rule, "statut": c.status,
                       "message": c.explication or c.rule})
    return sortie


#: decisions recevables sur un constat de coherence
ARBITRAGES_RECEVABLES = frozenset({"accepte", "corrige", "ignore"})


def _reappliquer_arbitrages(dossier, constats: list) -> None:
    """Reinjecte dans les constats recalcules les decisions humaines.

    Les constats sont reconstruits depuis les documents a chaque lecture ; un
    arbitrage pose par un humain doit donc leur etre reapplique, sinon la
    divergence qu'il a tranchee reviendrait « a trancher » et sa decision
    disparaitrait de l'affichage comme de l'apercu de transmission.
    """
    for c in constats:
        arb = (dossier.arbitrages or {}).get(c.rule)
        if not arb:
            continue
        c.status = str(arb.get("status") or "accepte")
        c.decision_par = arb.get("acteur")


@app.get("/api/coherence/regles")
def regles_coherence() -> dict:
    """Règles de rapprochement réellement appliquées.

    Un constat qui surprend (ou qui manque) doit pouvoir être expliqué :
    cette route dit quelles tolérances, quelles clés de référence et quelles
    règles sont actives, désactivées ou bloquantes. Sans elle, un opérateur
    ne peut pas savoir si une règle a été coupée par configuration.
    """
    return _coherence.configuration_effective()


@app.get("/api/dossiers/{dossier_id}/coherence")
def coherence_dossier(dossier_id: str, request: Request) -> dict:
    """Contrôles de cohérence entre les documents du dossier."""
    _exige_dossier(dossier_id, request)
    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    constats, nb_documents = _constats_coherence(dossier)
    transmissible, motif = _coherence.peut_transmettre(constats)
    return {
        "dossier_id": dossier_id,
        "constats": [c.as_dict() for c in constats],
        "transmissible": transmissible,
        "motif": motif,
        "documents_analyses": nb_documents,
    }


@app.post("/api/dossiers/{dossier_id}/coherence")
def trancher_constat(dossier_id: str, request: Request, body: dict) -> dict:
    """Arbitre un constat de coherence : accepte, corrige ou ignore.

    La decision est datee, attribuee et motivee. Elle ne modifie aucun
    document : elle acte qu'un humain a vu la divergence et a tranche.
    """
    _exige_dossier(dossier_id, request)
    regle = str(body.get("rule") or "").strip()
    if not regle:
        raise HTTPException(422, "regle (rule) requise")
    statut = str(body.get("status") or "").strip()
    if statut not in ARBITRAGES_RECEVABLES:
        raise HTTPException(422, "statut inconnu : %s — attendu %s"
                            % (statut, sorted(ARBITRAGES_RECEVABLES)))
    acteur = str(body.get("user") or "utilisateur")
    motif = str(body.get("motif") or "").strip()
    if not motif:
        raise HTTPException(422, "motif requis : un arbitrage sans raison "
                                 "ne peut pas etre conteste plus tard")
    dossier = _dossiers.trancher_constat(dossier_id, regle, statut, acteur,
                                        motif)
    return dossier.as_dict()


@app.post("/api/dossiers/{dossier_id}/package")
def generer_paquet(dossier_id: str, request: Request, body: dict | None = None) -> dict:
    """Génère le paquet de données (xlsx / json / zip).

    Les documents originaux ne sont inclus dans le ZIP que si
    `include_documents` est explicitement vrai.
    """
    _exige_dossier(dossier_id, request)
    body = body or {}
    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    fmt = str(body.get("format") or "zip").lower()
    if fmt not in ("xlsx", "json", "zip"):
        raise HTTPException(422, f"format inconnu : {fmt}")

    documents: list[DocumentPaquet] = []
    anomalies = []
    for piece in dossier.pieces:
        result = store.load_result(piece.job_id)
        if result is None:
            continue
        champs = {}
        for nom, fv in (result.get("fields") or {}).items():
            valeur = (fv.get("confirmed_value") or fv.get("corrected_value")
                      or fv.get("normalized_value") or fv.get("raw_value"))
            statut = fv.get("status")
            # statuts réels de FieldStatus : validated (humain), corrected
            # (règle métier) — « detected » reste à tranccher.
            champs[nom] = {
                "valeur": valeur,
                "origine": fv.get("value_origin", "raw"),
                "valide": statut in ("validated", "corrected"),
                "page": fv.get("page_num"),
                "confiance": fv.get("confidence"),
                "label": fv.get("label") or nom,
            }
        fichiers = []
        if body.get("include_documents"):
            originaux = store.original_dir(piece.job_id)
            if originaux.is_dir():
                fichiers = [p for p in originaux.iterdir() if p.is_file()]
        documents.append(DocumentPaquet(
            job_id=piece.job_id, filename=piece.filename,
            category=piece.category, champs=champs, fichiers=fichiers,
            sha256=piece.sha256))

    # Meme collecte que la route de coherence, donc memes arbitrages
    # appliques : un classeur qui listerait « a trancher » une anomalie
    # deja tranchee par un humain contredirait la decision prise.
    constats, _ = _constats_coherence(dossier)
    anomalies = [c.as_dict() for c in constats]
    # les arbitrages humains font partie du livrable : un classeur qui ne
    # montrerait que les anomalies encore ouvertes ferait disparaitre les
    # corrections deja tranchees de l'historique du dossier.
    arbitrages = list((dossier.arbitrages or {}).values())
    manquants = _dossiers.pieces_manquantes(dossier)

    sortie = cfg.data_dir / "exports" / dossier_id
    sortie.mkdir(parents=True, exist_ok=True)
    if fmt == "xlsx":
        chemin = genere_xlsx(documents, sortie / "paquet.xlsx", dossier_id,
                             dossier.label, anomalies, manquants, arbitrages)
    elif fmt == "json":
        chemin = genere_json(documents, sortie / "paquet.json", dossier_id,
                             dossier.label, anomalies, manquants, arbitrages)
    else:
        chemin = genere_zip(documents, sortie / "paquet.zip", dossier_id,
                            dossier.label, anomalies, manquants,
                            inclure_documents=bool(body.get("include_documents")),
                            arbitrages=arbitrages)
    consigne_paquet(cfg.log_dir, dossier_id, chemin, len(documents),
                    acteur=str(body.get("user") or "utilisateur"))
    return {
        "dossier_id": dossier_id, "format": fmt, "fichier": chemin.name,
        "chemin": str(chemin), "taille": chemin.stat().st_size,
        "documents": len(documents), "anomalies": len(anomalies),
        "pieces_manquantes": len(manquants),
    }


@app.get("/api/dossier-profiles")
def dossier_profiles() -> dict:
    """Profils de dossier — conventions, pas obligations réglementaires."""
    return {
        "profiles": [
            {"id": p.id, "label": p.label, "description": p.description,
             "pieces": [{"category": x.category, "label": x.label,
                         "required": x.required, "min_count": x.min_count}
                        for x in p.pieces]}
            for p in PROFILS_DOSSIER.values()
        ],
        "states": [{"id": e.value, "label": LIBELLES_ETATS[e]}
                   for e in DossierState],
    }


# ─────────────────── form builder du dossier (étape 12) ───────────────────
# Distinct de `connectors/forms.py` : ce module décrit la structure interne
# d'un dossier, pas un formulaire destiné à un système externe. Aucune
# soumission, aucun endpoint, aucun format officiel prétendu.

from .formulaire import (  # noqa: E402
    FORM_VERSION,
    TYPES_CHAMP,
    FormulaireStore,
    ajoute_champ,
    apercu_textuel,
    construit_depuis_dossier,
    renseigne,
    retire_champ,
)

_formulaires = FormulaireStore(cfg.data_dir / "formulaires", log_dir=cfg.log_dir)


def _documents_dossier(dossier) -> list[dict]:
    """Documents d'un dossier, au format attendu par le form builder."""
    documents = []
    for piece in dossier.pieces:
        result = store.load_result(piece.job_id) or {}
        documents.append({
            "job_id": piece.job_id,
            "filename": piece.filename,
            "category": piece.category,
            "champs": result.get("fields") or {},
        })
    return documents


def _formulaire_ou_404(formulaire_id: str, request: Request):
    formulaire = _formulaires.charge(formulaire_id)
    if formulaire is None:
        raise HTTPException(404, f"formulaire introuvable : {formulaire_id}")
    _exige_dossier(formulaire.dossier_id, request)
    return formulaire


@app.get("/api/formulaire-types")
def formulaire_types() -> dict:
    """Types de champ reconnus — aide à l'affichage, jamais une contrainte."""
    return {"version": FORM_VERSION, "types": list(TYPES_CHAMP)}


@app.post("/api/dossiers/{dossier_id}/formulaire")
def cree_formulaire(dossier_id: str, request: Request) -> dict:
    """Construit le formulaire d'un dossier à partir de ses documents.

    Un champ n'apparaît que si une valeur a réellement été extraite. Un
    document sans champ reconnu n'ajoute rien.
    """
    _exige_dossier(dossier_id, request)
    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    formulaire = construit_depuis_dossier(dossier, _documents_dossier(dossier))
    _formulaires.sauve(formulaire)
    return formulaire.as_dict()


@app.get("/api/dossiers/{dossier_id}/formulaire")
def get_formulaire(dossier_id: str, request: Request) -> dict:
    """Dernier formulaire connu d'un dossier, ou une construction à la volée."""
    _exige_dossier(dossier_id, request)
    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    existants = [f for f in _formulaires.liste() if f.dossier_id == dossier_id]
    if existants:
        return existants[-1].as_dict()
    # rien d'enregistré : on décrit la structure sans l'écrire
    return construit_depuis_dossier(dossier, _documents_dossier(dossier)).as_dict()


@app.get("/api/formulaires/{formulaire_id}")
def get_formulaire_id(formulaire_id: str, request: Request) -> dict:
    return _formulaire_ou_404(formulaire_id, request).as_dict()


@app.post("/api/formulaires/{formulaire_id}/champs")
def ajoute_champ_formulaire(formulaire_id: str, request: Request,
                            body: dict) -> dict:
    """Ajout humain explicite d'un champ — tracé comme tel."""
    formulaire = _formulaire_ou_404(formulaire_id, request)
    try:
        ajoute_champ(formulaire, str(body.get("key") or ""),
                     label=str(body.get("label") or ""),
                     type=str(body.get("type") or "text"),
                     required=bool(body.get("required")),
                     valeur=body.get("valeur"),
                     aide=str(body.get("aide") or ""))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    _formulaires.sauve(formulaire)
    return formulaire.as_dict()


@app.delete("/api/formulaires/{formulaire_id}/champs/{key}")
def retire_champ_formulaire(formulaire_id: str, key: str,
                            request: Request) -> dict:
    """Retire un champ du formulaire — le document source n'est pas touché."""
    formulaire = _formulaire_ou_404(formulaire_id, request)
    retire_champ(formulaire, key)
    _formulaires.sauve(formulaire)
    return formulaire.as_dict()


@app.patch("/api/formulaires/{formulaire_id}/champs/{key}")
def renseigne_champ_formulaire(formulaire_id: str, key: str,
                               request: Request, body: dict) -> dict:
    """Renseigne un champ existant. Un champ inconnu est refusé."""
    formulaire = _formulaire_ou_404(formulaire_id, request)
    try:
        renseigne(formulaire, key, body.get("valeur"),
                  valide=bool(body.get("valide")))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    _formulaires.sauve(formulaire)
    return formulaire.as_dict()


@app.get("/api/formulaires/{formulaire_id}/apercu")
def apercu_formulaire(formulaire_id: str, request: Request) -> dict:
    """Rendu texte du formulaire — lisible sans aucune dépendance graphique."""
    formulaire = _formulaire_ou_404(formulaire_id, request)
    return {"formulaire_id": formulaire_id,
            "texte": apercu_textuel(formulaire)}


@app.get("/api/formulaires")
def liste_formulaires(request: Request) -> list[dict]:
    utilisateur = _utilisateur_courant(request)
    formulaires = _formulaires.liste()
    if utilisateur is not None:
        formulaires = [f for f in formulaires
                       if utilisateur.voit_dossier(f.dossier_id)]
    return [f.as_dict() for f in formulaires]


# ───────────── archivage et traçabilité (étape 15) ─────────────
# L'archivage est un état, pas une suppression : rien n'est effacé. La trace
# est un journal applicatif, et elle le dit — elle n'est pas présentée comme
# une preuve inviolable.

from .tracabilite import (  # noqa: E402
    AVERTISSEMENT_TRACABILITE,
    GARANTIES_ARCHIVAGE,
    LIMITES_ARCHIVAGE,
    archiver_dossier,
    synthese_tracabilite,
)


@app.post("/api/dossiers/{dossier_id}/archiver")
def api_archiver_dossier(dossier_id: str, request: Request, body: dict | None = None) -> dict:
    """Archive un dossier. Les documents et les corrections restent en place.

    Un dossier incomplet est archivé avec un avertissement : l'archivage ne
    crée pas les pièces manquantes.
    """
    _exige_dossier(dossier_id, request)
    body = body or {}
    try:
        return archiver_dossier(_dossiers, dossier_id,
                                motif=str(body.get("motif") or ""),
                                acteur=str(body.get("user") or "utilisateur"))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/dossiers/{dossier_id}/trace")
def api_trace_dossier(dossier_id: str, request: Request) -> dict:
    """Trace d'un dossier : événements du dossier et de ses documents.

    La réponse porte **toujours** l'avertissement sur ce que le journal est —
    et ce qu'il n'est pas.
    """
    _exige_dossier(dossier_id, request)
    try:
        return synthese_tracabilite(_dossiers, dossier_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/tracabilite/avertissement")
def api_avertissement_tracabilite() -> dict:
    """Ce que la traçabilité garantit, et ce qu'elle ne garantit pas.

    Exposé séparément pour que l'interface puisse l'afficher à côté de la
    trace, pas une fois pour toutes dans une page d'aide.
    """
    return {
        "avertissement": AVERTISSEMENT_TRACABILITE,
        "garanties": list(GARANTIES_ARCHIVAGE),
        "limites": list(LIMITES_ARCHIVAGE),
    }


# ─────────── transmission d'un dossier entier (étape 14) ───────────
# Même discipline que `POST /api/connectors/transmit`, mais la source est le
# formulaire du dossier et non un document isolé. Les valeurs non validées
# par un humain ne partent pas ; « envoyé » n'est jamais « accepté ».

from .transmission_dossier import (  # noqa: E402
    CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS,
    apercu_transmission_dossier,
    resout_form_cible,
    transmettre_dossier,
)


class TransmetDossierBody(BaseModel):
    form_id: str = ""
    rules: list[MappingRuleBody] = []
    risk: str = "medium"
    confirmed: bool = False
    confirmed_by: str = ""


@app.get("/api/dossiers/{dossier_id}/transmission")
def api_apercu_transmission_dossier(dossier_id: str, request: Request,
                                    form_id: str = "") -> dict:
    """Aperçu de ce qui serait transmis. N'envoie jamais rien.

    Volontairement en GET : un aperçu est une lecture. L'envoi, lui, est un
    POST — et exige une confirmation explicite.

    Sans règles de correspondance, l'aperçu signale chaque champ du dossier
    comme « sans correspondance » : c'est l'information utile. Il renvoie
    aussi des **suggestions** de mapping par similarité de nom — jamais
    appliquées seules, l'utilisateur les valide.
    """
    _exige_dossier(dossier_id, request)
    from .connectors.mapping import MappingEngine

    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    from .formulaire import construit_depuis_dossier

    existants = [f for f in _formulaires.liste() if f.dossier_id == dossier_id]
    formulaire = (existants[-1] if existants
                  else construit_depuis_dossier(dossier,
                                                _documents_dossier(dossier)))
    form_cible = resout_form_cible(connector_hub, form_store, form_id)
    ap = apercu_transmission_dossier(dossier, _dossiers.synthese(dossier),
                                     formulaire, form_cible, [],
                                     anomalies_coherence(dossier))
    sortie = ap.as_dict()
    if form_cible is not None:
        source = {c.key: str(c.valeur) for c in formulaire.champs
                  if c.est_rempli}
        sortie["suggestions_mapping"] = MappingEngine().suggest(form_cible,
                                                                source)
    return sortie


@app.post("/api/dossiers/{dossier_id}/transmission")
def api_transmettre_dossier(dossier_id: str, request: Request,
                            body: TransmetDossierBody) -> dict:
    """Transmet le contenu d'un dossier vers un connecteur opérationnel.

    Refuse si le rapport de contrôle n'est pas transmissible, si aucun
    formulaire cible n'est résolu, ou si aucun connecteur n'est opérationnel.
    """
    _exige_dossier(dossier_id, request)
    from .connectors.mapping import MappingRule

    dossier = _dossiers.get(dossier_id)
    if not dossier:
        raise HTTPException(404, "dossier introuvable")
    rules = [MappingRule(r.source_field, r.target_field, r.transform)
             for r in body.rules]
    try:
        return transmettre_dossier(
            _dossiers, transmissions, connector_hub, dossier_id,
            _documents_dossier, _formulaires, form_store,
            form_id=body.form_id, rules=rules, risque=body.risk,
            confirme=body.confirmed,
            confirme_par=body.confirmed_by or "utilisateur",
            anomalies=anomalies_coherence(dossier))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/dossiers/{dossier_id}/transmissions")
def api_transmissions_dossier(dossier_id: str, request: Request) -> dict:
    """Historique des transmissions de ce dossier, avec le rappel permanent."""
    _exige_dossier(dossier_id, request)
    if not _dossiers.get(dossier_id):
        raise HTTPException(404, "dossier introuvable")
    return {
        "dossier_id": dossier_id,
        "transmissions": [t.as_dict()
                          for t in transmissions.list_for_dossier(dossier_id)],
        "ne_garantit_pas": list(CE_QUE_LA_TRANSMISSION_NE_GARANTIT_PAS),
    }
