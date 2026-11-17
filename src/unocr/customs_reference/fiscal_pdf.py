"""PDF reçu opaque + transcription déclarée : aucun parseur PDF, OCR ou taux extrait."""
import hashlib

from .importer import ImportRefuse, _json


def lire_transcription_pdf(original: bytes, transcription: bytes):
    if not original.startswith(b"%PDF-"):
        raise ImportRefuse("Signature PDF absente ; aucun document reconstruit")
    mesures = _json(transcription)
    if not isinstance(mesures,list):
        raise ImportRefuse("Transcription PDF : tableau JSON de mesures déclaré requis")
    return mesures,{"format":"pdf", "contenu":"pdf_opaque_et_tableau_mesures_transcrites",
                    "taux":"chaines_decimales_ou_null", "transcription_sha256":hashlib.sha256(transcription).hexdigest(),
                    "signature_pdf_presente":True, "structure_pdf_verifiee":False, "lecture_pdf_effectuee":False,
                    "transcription_verification":"non_verifiee", "references":"declarees_non_generees"}
