"""Moteur de transmission — envoi, idempotence, reprises, rapprochement (phase 9).

**Règle absolue.** Une transmission n'est considérée comme acceptée que sur
**preuve** : accusé de réception ou statut vérifiable. Tant que la preuve
manque, l'état est `pending_confirmation` et le système **ne retransmet pas**
à l'aveugle — il rapproche d'abord (interroge le statut) pour savoir si le
système cible a enregistré le dossier.

**Anti-doublon.** Chaque transmission porte une clé d'idempotence dérivée de
(connecteur, formulaire, document, contenu). Si l'API cible la prend en charge,
elle est envoyée ; sinon, le rapprochement par `get_acknowledgement` sert de
garde-fou avant toute reprise.

**Reprises.** Manuelles toujours ; automatiques uniquement quand c'est sûr
(erreur réseau, service indisponible), jamais après un rejet métier — un
dossier refusé pour cause de données invalides doit être corrigé, pas renvoyé.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from ..logging_setup import audit, get_logger
from .contract import (
    BaseConnector,
    ConnectorCapability,
    FormSchema,
    NotSupportedError,
)
from .validation import ValidationReport

log = get_logger("connectors.transmission")


class TransmissionStatus(str, Enum):
    PENDING = "pending"                      # créée, pas encore envoyée
    SENT = "sent"                            # envoyée, sans preuve d'acceptation
    PENDING_CONFIRMATION = "pending_confirmation"  # issue inconnue → rapprocher
    ACCEPTED = "accepted"                    # preuve d'acceptation
    REJECTED = "rejected"                    # refus explicite du système cible
    FAILED = "failed"                        # échec technique (réessayable)
    CANCELLED = "cancelled"                  # annulée par l'utilisateur


# statuts pour lesquels une reprise automatique est SÛRE
SAFE_TO_RETRY = {TransmissionStatus.FAILED}


def idempotency_key(connector_id: str, form_id: str, job_id: str,
                    payload: dict, dossier_id: str = "") -> str:
    """Clé d'idempotence stable dérivée du contenu réel envoyé.

    Deux envois du même contenu vers le même connecteur produisent la même
    clé : le système cible peut dédupliquer, et nous aussi.
    """
    h = hashlib.sha256()
    h.update(connector_id.encode("utf-8"))
    h.update(b"|")
    h.update(form_id.encode("utf-8"))
    h.update(b"|")
    h.update((job_id or "").encode("utf-8"))
    h.update(b"|")
    h.update((dossier_id or "").encode("utf-8"))
    h.update(b"|")
    h.update(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                        default=str).encode("utf-8"))
    return h.hexdigest()[:32]


@dataclass
class Transmission:
    """Une transmission, avec son identifiant interne unique et son histoire."""
    transmission_id: str
    connector_id: str
    form_id: str
    job_id: str = ""
    #: dossier d'origine, quand la transmission porte un dossier entier et
    #: non un document isolé. Vide pour une transmission documentaire.
    dossier_id: str = ""
    status: TransmissionStatus = TransmissionStatus.PENDING
    payload: dict = field(default_factory=dict)
    reference: Optional[str] = None          # n° chez le système cible
    key: str = ""                            # clé d'idempotence
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    risk: str = "medium"
    confirmed_by: str = ""
    # Vrai tant qu'aucun envoi n'a eu lieu pour ce contenu. Mis à False quand
    # `create()` détecte un doublon déjà accepté : l'appelant ne doit alors
    # surtout pas renvoyer (ce serait un doublon côté système cible).
    needs_send: bool = True

    def _log(self, what: str, **kw) -> None:
        self.history.append({"at": time.time(), "event": what, **kw})
        self.updated_at = time.time()

    def as_dict(self) -> dict:
        return {
            "transmission_id": self.transmission_id,
            "connector_id": self.connector_id, "form_id": self.form_id,
            "job_id": self.job_id, "dossier_id": self.dossier_id,
            "status": self.status.value,
            "payload": self.payload, "reference": self.reference,
            "key": self.key, "created_at": self.created_at,
            "updated_at": self.updated_at, "attempts": self.attempts,
            "errors": self.errors, "evidence": self.evidence,
            "history": self.history[-25:], "risk": self.risk,
            "confirmed_by": self.confirmed_by,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transmission":
        t = cls(d["transmission_id"], d["connector_id"], d["form_id"],
                d.get("job_id", ""))
        t.dossier_id = d.get("dossier_id", "")
        t.status = TransmissionStatus(d.get("status", "pending"))
        t.payload = d.get("payload") or {}
        t.reference = d.get("reference")
        t.key = d.get("key", "")
        t.created_at = d.get("created_at", time.time())
        t.updated_at = d.get("updated_at", t.created_at)
        t.attempts = d.get("attempts", 0)
        t.errors = d.get("errors") or []
        t.evidence = d.get("evidence") or {}
        t.history = d.get("history") or []
        t.risk = d.get("risk", "medium")
        t.confirmed_by = d.get("confirmed_by", "")
        return t


class TransmissionEngine:
    """Enregistre, envoie, rapproche et reprend les transmissions."""

    MAX_AUTO_RETRIES = 3

    def __init__(self, root: Path, log_dir: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir)
        self._items: dict[str, Transmission] = {}
        self._load()

    # ─────────────────────────── persistance ───────────────────────────

    def _path(self) -> Path:
        return self.root / "transmissions.json"

    def _load(self) -> None:
        p = self._path()
        if not p.is_file():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for tid, rec in (data.get("transmissions") or {}).items():
                self._items[tid] = Transmission.from_dict(rec)
        except (json.JSONDecodeError, OSError, KeyError):
            log.exception("historique des transmissions illisible")

    def _save(self) -> None:
        p = self._path()
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(
            {"transmissions": {k: v.as_dict() for k, v in self._items.items()}},
            ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)

    # ─────────────────────────── création ───────────────────────────

    def create(self, connector_id: str, form: FormSchema,
               report: ValidationReport, job_id: str = "",
               dossier_id: str = "") -> Transmission:
        """Crée une transmission à partir d'un rapport de validation.

        Refuse de créer une transmission non transmissible : le verrou est
        posé ici, pas dans l'interface.

        `job_id` et `dossier_id` décrivent ce qui est transmis : un document
        isolé, ou un dossier entier. Un dossier transmet son contenu, pas ses
        fichiers — c'est l'appelant qui décide du format.
        """
        ok, why = report.can_transmit()
        if not ok:
            raise ValueError(f"transmission refusée : {why}")

        payload = report.payload()
        key = idempotency_key(connector_id, form.form_id, job_id, payload,
                              dossier_id)
        tid = f"tx_{hashlib.sha256(key.encode()).hexdigest()[:16]}"

        # même contenu déjà transmis avec succès → on ne renvoie pas
        existing = self.find_by_key(key)
        if existing and existing.status in (
                TransmissionStatus.ACCEPTED, TransmissionStatus.SENT,
                TransmissionStatus.PENDING_CONFIRMATION):
            existing._log("duplicate_prevented",
                          detail="contenu identique déjà transmis")
            self._save()
            existing.needs_send = False
            return existing

        t = self._items.get(tid) or Transmission(tid, connector_id, form.form_id,
                                                 job_id, dossier_id)
        t.needs_send = True
        t.dossier_id = dossier_id
        t.payload = payload
        t.key = key
        t.risk = report.risk.value
        t.confirmed_by = report.confirmed_by
        t.status = TransmissionStatus.PENDING
        t.errors = []
        t._log("created", fields=len(payload))
        self._items[tid] = t
        self._save()
        audit(self.log_dir, "transmission_created", transmission=tid,
              connector=connector_id, form=form.form_id, job=job_id,
              dossier=dossier_id)
        return t

    # ─────────────────────────── envoi ───────────────────────────

    def send(self, transmission_id: str,
             connector: BaseConnector) -> Transmission:
        """Envoie réellement. L'état reflète la preuve obtenue, pas l'intention."""
        t = self._items.get(transmission_id)
        if t is None:
            raise KeyError(f"transmission inconnue : {transmission_id}")

        # doublon déjà accepté : on ne renvoie jamais, quoi que demande l'appelant
        if not t.needs_send and t.status in (
                TransmissionStatus.ACCEPTED, TransmissionStatus.SENT,
                TransmissionStatus.PENDING_CONFIRMATION):
            t._log("send_skipped_duplicate",
                   detail="contenu déjà transmis — envoi évité")
            self._save()
            return t

        if not connector.supports(ConnectorCapability.SUBMIT):
            t.status = TransmissionStatus.FAILED
            t.errors = ["le connecteur ne prend pas en charge la soumission"]
            t._log("send_refused", detail=t.errors[0])
            self._save()
            return t

        t.attempts += 1
        t._log("send_attempt", n=t.attempts)
        try:
            form = self._form_for(connector, t.form_id)
            result = connector.submit(form, t.payload, idempotency_key=t.key)
        except NotSupportedError as exc:
            t.status = TransmissionStatus.FAILED
            t.errors = [str(exc)]
            t._log("send_failed", detail=str(exc))
            self._save()
            return t
        except Exception as exc:
            # échec technique : issue inconnue → rapprocher avant de rejouer
            t.status = TransmissionStatus.PENDING_CONFIRMATION
            t.errors = [f"erreur technique : {exc}"]
            t._log("send_unclear", detail=str(exc))
            self._save()
            return t

        t.evidence = result.evidence
        if result.accepted and not result.pending_confirmation:
            t.status = TransmissionStatus.ACCEPTED
            t.reference = result.reference
            t.errors = []
            t._log("accepted", reference=result.reference)
            audit(self.log_dir, "transmission_accepted",
                  transmission=t.transmission_id, connector=t.connector_id,
                  reference=result.reference)
        elif result.pending_confirmation:
            # le système cible n'a pas encore donné de preuve
            t.status = TransmissionStatus.PENDING_CONFIRMATION
            t._log("pending_confirmation", detail=result.detail)
        else:
            t.status = TransmissionStatus.REJECTED
            t.errors = list(result.errors) or [result.detail]
            t._log("rejected", errors=t.errors)
            audit(self.log_dir, "transmission_rejected", transmission=t.transmission_id,
                  connector=t.connector_id, errors=t.errors[:3])
        self._save()
        return t

    def _form_for(self, connector: BaseConnector, form_id: str) -> FormSchema:
        """Retrouve le schéma du formulaire chez le connecteur."""
        try:
            for f in connector.discover_forms():
                if f.form_id == form_id:
                    return f
        except NotSupportedError:
            pass
        # repli : schéma minimal (les noms de champs sont déjà ceux du payload)
        return FormSchema(form_id=form_id, fields=[], source="declared")

    # ─────────────────────────── rapprochement ───────────────────────────

    def reconcile(self, transmission_id: str,
                  connector: BaseConnector) -> Transmission:
        """Issue inconnue : interroge le système cible AVANT de rejouer.

        C'est le garde-fou anti-doublon : on ne retransmet jamais sans avoir
        d'abord demandé au système cible ce qu'il a fait de la demande.
        """
        t = self._items.get(transmission_id)
        if t is None:
            raise KeyError(f"transmission inconnue : {transmission_id}")
        if t.status != TransmissionStatus.PENDING_CONFIRMATION:
            return t

        ref = t.reference or t.key
        how = "reference" if t.reference else "idempotency_key"
        try:
            if connector.supports(ConnectorCapability.GET_ACKNOWLEDGEMENT):
                ack = connector.get_acknowledgement(ref)
                if ack.get("acknowledged"):
                    t.status = TransmissionStatus.ACCEPTED
                    t.reference = ack.get("reference", t.reference)
                    t.errors = []
                    t._log("reconciled_accepted", reference=t.reference,
                           matched_by=how)
                    audit(self.log_dir, "transmission_reconciled",
                          transmission=t.transmission_id, outcome="accepted")
                else:
                    t._log("reconciled_unknown", detail=str(ack))
            elif connector.supports(ConnectorCapability.GET_STATUS):
                st = connector.get_status(ref)
                if st.get("status") == "accepted":
                    t.status = TransmissionStatus.ACCEPTED
                    t.reference = st.get("reference", t.reference)
                    t._log("reconciled_accepted", reference=t.reference,
                           matched_by=how)
                else:
                    t._log("reconciled_unknown", detail=str(st))
            else:
                t._log("reconcile_unsupported",
                       detail="le connecteur ne peut pas être interrogé : "
                              "reprise manuelle requise")
        except Exception as exc:
            t._log("reconcile_failed", detail=str(exc))
        self._save()
        return t

    # ─────────────────────────── reprises ───────────────────────────

    def retry(self, transmission_id: str, connector: BaseConnector,
              auto: bool = False) -> Transmission:
        """Reprend une transmission.

        `auto=True` n'est autorisé que pour un échec technique, et dans la
        limite de `MAX_AUTO_RETRIES`. Un rejet métier n'est jamais rejoué
        automatiquement : les données doivent être corrigées.
        """
        t = self._items.get(transmission_id)
        if t is None:
            raise KeyError(f"transmission inconnue : {transmission_id}")
        if t.status not in SAFE_TO_RETRY and not (
                t.status == TransmissionStatus.PENDING_CONFIRMATION and not auto):
            raise ValueError(
                f"reprise refusée : statut « {t.status.value} » — "
                "corriger les données ou rapprocher manuellement")
        if auto and t.attempts >= self.MAX_AUTO_RETRIES:
            raise ValueError(
                f"limite de reprises automatiques atteinte ({self.MAX_AUTO_RETRIES})")
        return self.send(transmission_id, connector)

    def cancel(self, transmission_id: str, connector: BaseConnector) -> Transmission:
        t = self._items.get(transmission_id)
        if t is None:
            raise KeyError(f"transmission inconnue : {transmission_id}")
        try:
            if connector.supports(ConnectorCapability.CANCEL) and t.reference:
                connector.cancel(t.reference)
        except Exception as exc:
            log.warning("annulation distante impossible : %s", exc)
        t.status = TransmissionStatus.CANCELLED
        t._log("cancelled")
        self._save()
        audit(self.log_dir, "transmission_cancelled",
              transmission=t.transmission_id, connector=t.connector_id)
        return t

    # ─────────────────────────── consultation ───────────────────────────

    def get(self, transmission_id: str) -> Optional[Transmission]:
        return self._items.get(transmission_id)

    def find_by_key(self, key: str) -> Optional[Transmission]:
        for t in self._items.values():
            if t.key == key:
                return t
        return None

    def list_for_dossier(self, dossier_id: str) -> list[Transmission]:
        """Transmissions portant un dossier donné, des plus anciennes aux récentes."""
        return sorted((t for t in self._items.values() if t.dossier_id == dossier_id),
                      key=lambda t: t.created_at)

    def list(self, connector_id: str = "", status: str = "",
             job_id: str = "", limit: int = 100) -> list[Transmission]:
        out = list(self._items.values())
        if connector_id:
            out = [t for t in out if t.connector_id == connector_id]
        if status:
            out = [t for t in out if t.status.value == status]
        if job_id:
            out = [t for t in out if t.job_id == job_id]
        out.sort(key=lambda t: t.created_at, reverse=True)
        return out[:limit]

    def stats(self) -> dict:
        by_status: dict[str, int] = {}
        for t in self._items.values():
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        return {"total": len(self._items), "by_status": by_status,
                "max_auto_retries": self.MAX_AUTO_RETRIES}
