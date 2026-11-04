"""Tests unitaires pour les indicateurs et le dashboard maritime."""

from fastapi.testclient import TestClient
from unocr.api import app


def test_dashboard_indicateurs_expose_routes():
    """Vérifier que les routes dashboard sont bien exposées."""
    client = TestClient(app)

    # Route d'état général
    res = client.get("/api/dashboard")
    assert res.status_code == 200, f"Route /api/dashboard retourne {res.status_code}"

    # 15+ indicateurs opérationnels
    res = client.get("/api/dashboard/indicateurs")
    assert res.status_code == 200, f"Route /api/dashboard/indicateurs retourne {res.status_code}"
    data = res.json()
    # Vérifier les indicateurs clés
    assert "total_jobs" in data
    assert "taux_reussite" in data
    assert "confiance_moyenne" in data
    assert "repartition_par_etat" in data
    assert "total_frais" in data
    assert "total_avances" in data
    assert "taux_recouvrement" in data
    assert "cout_moyen_fret" in data
    assert "pieces_requises" in data
    assert "pieces_presentes" in data
    assert "taux_completion_pieces" in data
    assert "taux_anomalies" in data
    assert "en_retard_7_jours" in data
    assert "taux_retard" in data
    assert "top_clients" in data
    assert "top_ports" in data
    assert "top_gestionnaires" in data
    assert "statut_documentaire" in data
    assert "type_operation" in data
    assert "top_barcodes" in data
    # Vérifier le nombre d'indicateurs (devrait être >= 15)
    indicator_keys = [k for k in data if k not in ("top_clients", "top_ports", "top_gestionnaires", "statut_documentaire", "type_operation", "top_barcodes")]
    assert len(indicator_keys) >= 15, f"Expected >= 15 indicators, got {len(indicator_keys)}"


def test_dashboard_graphiques_expose_routes():
    """Vérifier que les routes de graphiques sont bien exposées."""
    client = TestClient(app)

    # Graphique répartition par état
    res = client.get("/api/dashboard/graphique/etat-dossiers")
    assert res.status_code == 200, f"Route graphique etat-dossiers retourne {res.status_code}"
    data = res.json()
    assert data["type"] == "bar"
    assert "series" in data
    assert "ordre" in data

    # Graphique financier mensuel
    res = client.get("/api/dashboard/graphique/financier-mensuel")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "line"
    assert "series" in data

    # Graphique répartition par port
    res = client.get("/api/dashboard/graphique/repartition-par-port")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "pie"
    assert "series" in data

    # Top clients
    res = client.get("/api/dashboard/graphique/top-clients?limite=5")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "doughnut"
    assert "series" in data


def test_dashboard_filtres():
    """Tester que les filtres fonctionnent correctement."""
    client = TestClient(app)

    # Test avec filtre période
    res = client.get("/api/dashboard/indicateurs?period=30j")
    assert res.status_code == 200
    data = res.json()
    assert "total_jobs" in data

    # Test avec filtre client
    res = client.get("/api/dashboard/indicateurs?client=inconnu")
    assert res.status_code == 200

    # Test avec filtre port
    res = client.get("/api/dashboard/indicateurs?port=all")
    assert res.status_code == 200

    # Test avec filtre gestionnaire
    res = client.get("/api/dashboard/indicateurs?manager=all")
    assert res.status_code == 200


def test_dashboard_sante():
    """Tester la route santé du dashboard."""
    client = TestClient(app)

    res = client.get("/api/dashboard/sante")
    assert res.status_code == 200, f"Route /api/dashboard/sante retourne {res.status_code}"
    data = res.json()
    assert data["systeme_actif"] is True
    assert "statistiques" in data
    assert "alertes" in data
    assert "sante_financiere" in data


def test_dashboard_alertes():
    """Tester la route alertes."""
    client = TestClient(app)

    res = client.get("/api/dashboard/alertes")
    assert res.status_code == 200
    data = res.json()
    assert "alertes" in data
    assert "nb_total" in data
    # Vérifier la structure des alertes
    if data["alertes"]:
        alerte = data["alertes"][0]
        assert "type" in alerte
        assert "niveau" in alerte
        assert "titre" in alerte
        assert "message" in alerte


def test_dashboard_kpi_values():
    """Vérifier que les KPI ont des valeurs numériques."""
    client = TestClient(app)

    res = client.get("/api/dashboard/indicateurs")
    assert res.status_code == 200
    data = res.json()

    # Vérifier que les valeurs sont des nombres
    assert isinstance(data["total_jobs"], (int, float))
    assert isinstance(data["taux_reussite"], (int, float))
    assert isinstance(data["confiance_moyenne"], (int, float))
    assert isinstance(data["taux_anomalies"], (int, float))
    assert isinstance(data["taux_retard"], (int, float))
    assert isinstance(data["cout_moyen_fret"], (int, float))
    assert isinstance(data["pieces_requises"], (int, float))
    assert isinstance(data["pieces_presentes"], (int, float))