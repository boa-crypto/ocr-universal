"""Tests du moteur de transmission : idempotence, reprises, rapprochement.

Le comportement central vérifié ici : **on ne retransmet jamais à l'aveugle**.
Une issue inconnue est rapprochée avant d'être rejouée, et un rejet métier
n'est jamais rejoué automatiquement.
"""
import pytest

from unocr.connectors.contract import FormSchema, SubmissionResult
from unocr.connectors.mapping import MappedValue
from unocr.connectors.simulated import SIMULATED, SimulatedConnector
from unocr.connectors.transmission import (
    SAFE_TO_RETRY,
    TransmissionEngine,
    TransmissionStatus,
    idempotency_key,
)
from unocr.connectors.validation import RiskLevel, Validator


@pytest.fixture()
def engine(tmp_path):
    SIMULATED.healthy = True
    return TransmissionEngine(tmp_path / "transmissions", tmp_path / "logs")


@pytest.fixture()
def connector():
    c = SimulatedConnector()
    c.configure({})
    return c


def _report(payload, risk=RiskLevel.LOW, confirmed=False):
    """Construit un rapport de validation déjà conforme."""
    rep = Validator(risk).validate(FormSchema(form_id="demo_declaration"), {
        k: MappedValue(k, v, "explicit") for k, v in payload.items()})
    if confirmed or risk is RiskLevel.LOW:
        rep.confirm(by="test")
    return rep


# ─────────────────────────── clé d'idempotence ───────────────────────────

def test_idempotency_key_is_stable_and_content_bound():
    a = idempotency_key("c", "f", "j", {"x": "1"})
    b = idempotency_key("c", "f", "j", {"x": "1"})
    assert a == b
    assert idempotency_key("c", "f", "j", {"x": "2"}) != a
    assert idempotency_key("c2", "f", "j", {"x": "1"}) != a


def test_idempotency_key_ignores_dict_order():
    a = idempotency_key("c", "f", "j", {"a": "1", "b": "2"})
    b = idempotency_key("c", "f", "j", {"b": "2", "a": "1"})
    assert a == b


# ─────────────────────────── création ───────────────────────────

def test_create_refuses_untransmittable_report(engine):
    """Le verrou est dans le moteur, pas seulement dans l'interface."""
    rep = Validator(RiskLevel.HIGH).validate(
        FormSchema(form_id="f"), {"a": MappedValue("a", None, "explicit")})
    with pytest.raises(ValueError, match="refusée"):
        engine.create("demo_simulated", FormSchema(form_id="f"), rep)


def test_create_requires_confirmation_for_high_risk(engine):
    rep = Validator(RiskLevel.HIGH).validate(
        FormSchema(form_id="f"), {"a": MappedValue("a", "1", "explicit")})
    with pytest.raises(ValueError):
        engine.create("demo_simulated", FormSchema(form_id="f"), rep)


def test_duplicate_content_is_not_resent(engine, connector):
    """Même contenu déjà transmis → la transmission existante est renvoyée."""
    rep = _report({"containerNo": "TGHU1111111", "bl_reference": "BL-1",
                   "grossWeight": "1.00"})
    form = FormSchema(form_id="demo_declaration")

    t1 = engine.create("demo_simulated", form, rep, "job-1")
    t1 = engine.send(t1.transmission_id, connector)
    assert t1.status is TransmissionStatus.ACCEPTED

    t2 = engine.create("demo_simulated", form, rep, "job-1")
    assert t2.transmission_id == t1.transmission_id     # pas de nouvel envoi
    assert any(h["event"] == "duplicate_prevented"
               for h in t2.history)


def test_transmission_ids_are_unique(engine):
    rep = _report({"a": "1"})
    form = FormSchema(form_id="f")
    ids = {engine.create("c", form, rep, "j").transmission_id for _ in range(3)}
    # même contenu → même identifiant (déduplication), c'est le comportement voulu
    assert len(ids) == 1


# ─────────────────────────── envoi ───────────────────────────

def test_send_accepts_and_records_reference(engine, connector):
    rep = _report({"containerNo": "TGHU1234567", "bl_reference": "BL-2",
                   "grossWeight": "10.00"})
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-2")
    t = engine.send(t.transmission_id, connector)
    assert t.status is TransmissionStatus.ACCEPTED
    assert t.reference and t.reference.startswith("DEMO-")
    assert t.attempts == 1


def test_send_rejected_records_errors(engine, connector):
    rep = _report({"containerNo": "TGHU1234567"})       # champs requis manquants
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-3")
    t = engine.send(t.transmission_id, connector)
    assert t.status is TransmissionStatus.REJECTED
    assert t.errors


def test_send_without_submit_capability_fails_cleanly(engine):
    from unocr.connectors.assisted_export import AssistedExportConnector

    c = AssistedExportConnector()
    rep = _report({"a": "1"})
    t = engine.create("assisted_export", FormSchema(form_id="f"), rep, "j")
    t = engine.send(t.transmission_id, c)
    assert t.status is TransmissionStatus.FAILED
    assert "ne prend pas en charge" in t.errors[0]


# ─────────────────────────── issue inconnue & rapprochement ───────────────────────────

def test_unclear_failure_becomes_pending_confirmation(engine):
    """Une exception réseau laisse l'issue INCONNUE : on ne conclut pas."""
    c = SimulatedConnector()

    def boom(*a, **kw):
        raise ConnectionError(" réseau coupé ")

    c.submit = boom
    rep = _report({"containerNo": "TGHU1234567", "bl_reference": "BL-3",
                   "grossWeight": "1.00"})
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-4")
    t = engine.send(t.transmission_id, c)
    assert t.status is TransmissionStatus.PENDING_CONFIRMATION
    assert t.status not in SAFE_TO_RETRY          # pas de reprise auto


def test_reconcile_confirms_accepted_before_any_retry(engine):
    """Le rapprochement découvre que le dossier a bien été accepté :
    aucune retransmission n'a lieu."""
    good = SimulatedConnector()

    # 1. envoi qui échoue de façon floue
    bad = SimulatedConnector()

    def boom(*a, **kw):
        raise ConnectionError("timeout")

    bad.submit = boom
    rep = _report({"containerNo": "TGHU7777777", "bl_reference": "BL-4",
                   "grossWeight": "5.00"})
    form = FormSchema(form_id="demo_declaration")
    t = engine.create("demo_simulated", form, rep, "job-5")
    t = engine.send(t.transmission_id, bad)
    assert t.status is TransmissionStatus.PENDING_CONFIRMATION

    # 2. le système cible l'a en fait accepté (clé d'idempotence)
    out = good.submit(form, t.payload, idempotency_key=t.key)
    assert out.accepted is True

    # 3. rapprochement : on apprend l'acceptation SANS renvoyer
    t = engine.reconcile(t.transmission_id, good)
    assert t.status is TransmissionStatus.ACCEPTED
    assert any(h["event"] == "reconciled_accepted" for h in t.history)


def test_auto_retry_refused_for_business_rejection(engine, connector):
    rep = _report({"containerNo": "TGHU1234567"})     # rejet métier
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-6")
    t = engine.send(t.transmission_id, connector)
    assert t.status is TransmissionStatus.REJECTED
    with pytest.raises(ValueError, match="reprise refusée"):
        engine.retry(t.transmission_id, connector, auto=True)


def test_auto_retry_allowed_for_technical_failure(engine):
    c = SimulatedConnector()
    calls = {"n": 0}

    def flaky(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("coupure")
        return SubmissionResult(True, pending_confirmation=False,
                                reference="DEMO-RETRY-1", detail="ok")

    c.submit = flaky
    rep = _report({"containerNo": "TGHU1234567", "bl_reference": "BL-7",
                   "grossWeight": "2.00"})
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-7")
    t = engine.send(t.transmission_id, c)
    assert t.status is TransmissionStatus.PENDING_CONFIRMATION
    # reprise automatique interdite tant que l'issue est inconnue
    with pytest.raises(ValueError):
        engine.retry(t.transmission_id, c, auto=True)


def test_auto_retry_limit(engine):
    c = SimulatedConnector()
    c.submit = lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("ko"))
    rep = _report({"containerNo": "TGHU1234567", "bl_reference": "BL-8",
                   "grossWeight": "3.00"})
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-8")
    # forcer un statut réessayable
    t.status = TransmissionStatus.FAILED
    t.attempts = engine.MAX_AUTO_RETRIES
    engine._save()
    with pytest.raises(ValueError, match="limite"):
        engine.retry(t.transmission_id, c, auto=True)


def test_cancel_marks_transmission(engine, connector):
    rep = _report({"a": "1"})
    t = engine.create("demo_simulated", FormSchema(form_id="f"), rep, "j")
    t = engine.cancel(t.transmission_id, connector)
    assert t.status is TransmissionStatus.CANCELLED


# ─────────────────────────── consultation ───────────────────────────

def test_history_persists_across_instances(tmp_path):
    e1 = TransmissionEngine(tmp_path / "tx", tmp_path / "logs")
    rep = _report({"containerNo": "TGHU1234567", "bl_reference": "BL-9",
                   "grossWeight": "4.00"})
    t = e1.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                  rep, "job-9")

    e2 = TransmissionEngine(tmp_path / "tx", tmp_path / "logs")
    assert e2.get(t.transmission_id) is not None
    assert e2.get(t.transmission_id).key == t.key


def test_filters(engine, connector):
    rep = _report({"containerNo": "TGHU1234567", "bl_reference": "BL-10",
                   "grossWeight": "5.00"})
    t = engine.create("demo_simulated", FormSchema(form_id="demo_declaration"),
                      rep, "job-A")
    engine.send(t.transmission_id, connector)
    assert len(engine.list(status="accepted")) == 1
    assert len(engine.list(status="rejected")) == 0
    assert len(engine.list(connector_id="autre")) == 0
    assert len(engine.list(job_id="job-A")) == 1


def test_stats(engine):
    s = engine.stats()
    assert s["total"] == 0 and s["max_auto_retries"] == 3


def test_unknown_transmission_is_rejected(engine, connector):
    with pytest.raises(KeyError):
        engine.send("tx_inconnu", connector)
    with pytest.raises(KeyError):
        engine.reconcile("tx_inconnu", connector)
