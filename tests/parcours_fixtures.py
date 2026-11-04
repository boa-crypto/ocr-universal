"""Documents synthétiques du scénario de référence (non sensibles).

Facture commerciale + connaissement maritime + liste de colisage, écrits avec
reportlab pour que l'OCR et l'extraction native travaillent sur du vrai texte.
Aucune donnée réelle, aucune entreprise réelle.
"""
from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _pdf(lignes: list[str], path: Path, taille: int = 11) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for ligne in lignes:
        c.setFont("Helvetica", taille)
        c.drawString(60, y, ligne)
        y -= 16
    c.save()
    return path


FACTURE = [
    "COMMERCIAL INVOICE",
    "Invoice No: INV-2024-118",
    "Date: 12/03/2024",
    "Seller: EXPEDITEUR TEST SARL",
    "Buyer: CLIENT TEST SA",
    "INCOterm: FOB ALGER",
    "Currency: EUR",
    "",
    "Description            Qty     Unit price    Amount",
    "Ref A                  100     12,50         1 250,00",
    "",
    "TOTAL AMOUNT: 1 250,00 EUR",
]

BL = [
    "BILL OF LADING",
    "B/L No: BL-2024-0456",
    "Invoice ref: INV-2024-118",
    "SHIPPER: EXPEDITEUR TEST SARL",
    "CONSIGNEE: CLIENT TEST SA",
    "NOTIFY PARTY: TRANSIT TEST",
    "VESSEL: MV TEST STAR",
    "VOYAGE: 12E",
    "PORT OF LOADING: DZALG",
    "PORT OF DISCHARGE: FRMRS",
    "",
    "Container  MSCU1234567  seal 778899",
    "Container  TGHU7654321  seal 112233",
    "GROSS WEIGHT: 12 000 KG",
    "FREIGHT PREPAID",
]

COLISAGE = [
    "PACKING LIST",
    "Invoice ref: INV-2024-118",
    "B/L ref: BL-2024-0456",
    # un seul des deux conteneurs du BL est listé ici : c'est l'incohérence
    # que le contrôle interdocumentaire doit faire remonter
    "Container  MSCU1234567  seal 778899",
    "GROSS WEIGHT: 13 500 KG",
    "NET WEIGHT: 11 500 KG",
    "CARTONS: 40",
    "PALLETS: 4",
]


def creer_fixtures() -> dict[str, Path]:
    """Écrit les trois documents et renvoie leurs chemins."""
    FIXTURES.mkdir(parents=True, exist_ok=True)
    return {
        "facture": _pdf(FACTURE, FIXTURES / "parcours_facture.pdf"),
        "bl": _pdf(BL, FIXTURES / "parcours_bl.pdf"),
        "colisage": _pdf(COLISAGE, FIXTURES / "parcours_colisage.pdf"),
    }
