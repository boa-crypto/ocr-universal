"""Index natif dérivé, épinglé au registre ; jamais transcription juridique."""
import hashlib
import json
import time
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .importer import _json, _lire
from .legal_comparison import charger_lot_code
from .models import StrictModel
from .pdf_page import extraire_octets_pdf
from .search import ParamRechercheInvalide, _correspondances, _parametres, _rapport
from .search_excerpt import extraits_correspondants

MAX_INDEX = 12 * 1024 * 1024
MAX_TEXTE = 4_000_000
MAX_PAGES_INDEX = 1000


class PageNative(StrictModel):
    page: int = Field(ge=1, le=10000)
    texte: str = Field(max_length=200000)
    sha256_texte_utf8: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def integrite(self):
        if hashlib.sha256(self.texte.encode()).hexdigest() != self.sha256_texte_utf8:
            raise ValueError("Empreinte de texte incohérente")
        return self


class DocumentIndexe(StrictModel):
    document_id: str = Field(min_length=1, max_length=256)
    pdf_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pages: list[PageNative] = Field(min_length=1, max_length=MAX_PAGES_INDEX)

    @model_validator(mode="after")
    def continuite(self):
        if [p.page for p in self.pages] != list(range(1,len(self.pages)+1)):
            raise ValueError("Pages non contiguës")
        return self


class IndexPDF(StrictModel):
    schema_version: Literal["1"] = "1"
    manifest_lot_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    methode: Literal["texte_natif_pdfium_sans_ocr"] = "texte_natif_pdfium_sans_ocr"
    version_extracteur: str = Field(min_length=1, max_length=64)
    documents: list[DocumentIndexe] = Field(min_length=1, max_length=64)
    verification: Literal["non_verifiee"] = "non_verifiee"
    publication_active: Literal[False] = False

    @model_validator(mode="after")
    def bornes(self):
        if (len({d.document_id for d in self.documents}) != len(self.documents)
                or sum(len(d.pages) for d in self.documents) > MAX_PAGES_INDEX
                or sum(len(p.texte) for d in self.documents for p in d.pages) > MAX_TEXTE):
            raise ValueError("Index dupliqué ou hors limites")
        return self


def construire_index(repertoire: Path, sortie: Path):
    lot, rapport = charger_lot_code(repertoire)
    debut, documents, total_pages, total_texte = time.monotonic(), [], 0, 0
    for numero, document in enumerate(lot.documents,1):
        contenu = _lire(repertoire/f"document_{numero:04d}.pdf")
        if hashlib.sha256(contenu).hexdigest() != document.sha256:
            raise ValueError("PDF modifié")
        pages, nombre, page = [], 1, 1
        while page <= nombre:
            if time.monotonic()-debut > 180 or total_pages >= MAX_PAGES_INDEX:
                raise ValueError("Budget d'indexation dépassé")
            texte, nombre = extraire_octets_pdf(contenu,page)
            total_pages += 1
            total_texte += len(texte)
            if total_texte > MAX_TEXTE or total_pages+nombre-page > MAX_PAGES_INDEX:
                raise ValueError("Volume d'index dépassé")
            pages.append(PageNative(page=page,texte=texte,sha256_texte_utf8=hashlib.sha256(texte.encode()).hexdigest()))
            page += 1
        documents.append(DocumentIndexe(document_id=document.id,pdf_sha256=document.sha256,pages=pages))
    _, apres = charger_lot_code(repertoire)
    if rapport["archive"] != apres["archive"]:
        raise ValueError("Source modifiée pendant l'indexation")
    index = IndexPDF(manifest_lot_sha256=rapport["archive"]["manifest_sha256"],
                     version_extracteur=version("pypdfium2"),documents=documents)
    brut = index.model_dump_json(indent=2).encode()
    if len(brut) > MAX_INDEX:
        raise ValueError("Fichier index trop volumineux")
    # Publication locale explicite, fichier nouveau seulement ; pas d'activation juridique.
    import os
    fd = os.open(sortie,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as fichier:
        fichier.write(brut)
        fichier.flush()
        os.fsync(fichier.fileno())
    return {"index_sha256":hashlib.sha256(brut).hexdigest(),"pages":total_pages,
            "caracteres":total_texte,"manifest_lot_sha256":index.manifest_lot_sha256}


def rechercher_pages(repertoire: Path, index_path: Path, empreinte: str, requete: str,
                      document_id: str | None = None, limite=20, decalage=0):
    termes = _parametres(requete,limite,decalage)
    if document_id is not None and (not isinstance(document_id,str) or not document_id.strip() or len(document_id)>256):
        raise ParamRechercheInvalide("Document exact invalide")
    lot, rapport, index = charger_index(repertoire,index_path,empreinte)
    resultats, total = [], 0
    for doc in index.documents:
        if document_id is not None and doc.document_id != document_id:
            continue
        for page in doc.pages:
            preuves = _correspondances({"texte_integral":page.texte},termes)
            if preuves is None:
                continue
            if decalage <= total < decalage+limite:
                resultats.append({"document_id":doc.document_id,"page_pdf":page.page,
                                  "pdf_sha256":doc.pdf_sha256,"sha256_texte_utf8":page.sha256_texte_utf8,
                                  "correspondances":preuves,"extraits":extraits_correspondants({"texte_integral":page.texte},termes)})
            total += 1
    r = _rapport("pages_pdf_natives",requete,termes,"sous_chaines_normalisees_tous_termes_meme_page",
                 {"document_id_exact":document_id},rapport,total,resultats,limite,decalage)
    r.update(index_sha256=empreinte,methode=index.methode,version_extracteur=index.version_extracteur,
             pages_indexees=sum(len(d.pages) for d in index.documents),transcription_verification="non_verifiee",
             articles_localises_automatiquement=False,ocr_effectue=False)
    r["avertissements"].extend(["Index dérivé épinglé ; pas correction des caractères PDF ou du flux des colonnes.",
                                "Résultats par pages physiques, pas articles ou occurrences, pas édition authentifiée."])
    return r


def charger_index(repertoire: Path, index_path: Path, empreinte: str):
    lot, rapport = charger_lot_code(repertoire)
    if index_path.parent.is_symlink() or index_path.is_symlink() or not index_path.is_file():
        raise ValueError("Index absent ou symbolique")
    brut = _lire(index_path)
    if len(brut)>MAX_INDEX or hashlib.sha256(brut).hexdigest() != empreinte:
        raise ValueError("Index non épinglé")
    index = IndexPDF.model_validate_json(json.dumps(_json(brut),ensure_ascii=False,allow_nan=False))
    if (index.manifest_lot_sha256 != rapport["archive"]["manifest_sha256"]
            or [(d.document_id,d.pdf_sha256) for d in index.documents] != [(d.id,d.sha256) for d in lot.documents]):
        raise ValueError("Index et archive différents")
    return lot, rapport, index
