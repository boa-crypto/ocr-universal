"""Repères typographiques candidats ; aucune délimitation juridique d'article."""
import hashlib
import json
import re
import unicodedata

from .pdf_index import charger_index
from .pdf_page import valider_parametres_pdf
from .search import ParamRechercheInvalide, _parametres, _rapport

# Début de ligne seulement ; ni renvois en prose ni réparation de l'encodage.
REPERES = re.compile(
    r"(?m)^[ \t]*(?P<entete>(?:Art\.?|Article)[ \t]{1,8}"
    r"(?P<numero>(?:[0-9]{1,4}(?:er|[ \t]{0,4}(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies)(?:[ \t]{1,4}[0-9]{1,2})?)?|premier))"
    r")(?=[ \t]*(?:[.\-–—:()ó]|$))", re.IGNORECASE)


def _filtre(valeur, longueur):
    if valeur is not None and (not isinstance(valeur,str) or not valeur.strip() or len(valeur)>longueur
                              or any(unicodedata.category(c) in {"Cc","Cs"} for c in valeur)):
        raise ParamRechercheInvalide("Filtre exact non blanc et sans contrôle requis")


def reperer_articles(repertoire,index_path,empreinte,document_id=None,numero=None,limite=20,decalage=0):
    _filtre(document_id,256)
    _filtre(numero,32)
    _parametres("",limite,decalage,True)
    _,rapport,index=charger_index(repertoire,index_path,empreinte)
    resultats,total=[],0
    for document in index.documents:
        if document_id is not None and document.document_id!=document_id:
            continue
        for page in document.pages:
            for match in REPERES.finditer(page.texte):
                if numero is not None and match['numero']!=numero:
                    continue
                if decalage<=total<decalage+limite:
                    debut,fin=match.span('entete')
                    identite=[document.document_id,document.pdf_sha256,page.page,debut,fin,page.sha256_texte_utf8]
                    resultats.append({"repere_id":hashlib.sha256(json.dumps(identite,ensure_ascii=False).encode()).hexdigest(),
                                      "document_id":document.document_id,"pdf_sha256":document.pdf_sha256,
                                      "page_pdf":page.page,"sha256_texte_utf8":page.sha256_texte_utf8,
                                      "numero_litteral":match['numero'],"entete_litteral":page.texte[debut:fin],
                                      "debut":debut,"fin":fin,"unite_decalage":"points_de_code_unicode_python",
                                      "contexte_debut":max(0,debut-80),"contexte":page.texte[max(0,debut-80):fin+240],
                                      "statut":"repere_candidat_non_valide"})
                total+=1
    r=_rapport("reperes_articles_pdf",numero or "",[],"entetes_de_ligne_candidats_sans_interpretation",
               {"document_id_exact":document_id,"numero_litteral_exact":numero},rapport,total,resultats,limite,decalage)
    r.update(index_sha256=empreinte,methode=index.methode,ocr_effectue=False,articles_localises_automatiquement=False,
             reperes_detectes_automatiquement=True,transcription_verification="non_verifiee")
    r['avertissements'].extend(["Un repère peut appartenir à une disposition citée ou remplacée ; pas article autonome attesté.",
                               "Débuts de lignes seulement ; pas de délimitation, fusion inter-pages ou exhaustivité garantie.",
                               "Numéros conservés littéralement ; distinction de casse/espaces et absence de traduction."])
    return r


def lire_page_indexee(repertoire,index_path,empreinte,document_id,page=1,limite=4000,decalage=0):
    valider_parametres_pdf(document_id,page,limite,decalage)
    _,rapport,index=charger_index(repertoire,index_path,empreinte)
    document=next((d for d in index.documents if d.document_id==document_id),None)
    if document is None or page>len(document.pages):
        raise LookupError("Document ou page absente de l'index contrôlé")
    native=document.pages[page-1]
    fragment=native.texte[decalage:decalage+limite]
    suivant=decalage+len(fragment)
    return {"type_rapport":"lecture_page_pdf_indexee","archive":rapport['archive'],"index_sha256":empreinte,
            "document_id":document_id,"pdf_sha256":document.pdf_sha256,"page_pdf":page,
            "nombre_pages_pdf":len(document.pages),"sha256_texte_utf8":native.sha256_texte_utf8,
            "fragment":fragment,"decalage":decalage,"limite":limite,"total_caracteres":len(native.texte),
            "decalage_suivant":suivant if suivant<len(native.texte) else None,
            "unite_decalage":"points_de_code_unicode_python","methode":index.methode,
            "version_extracteur":index.version_extracteur,"lecture_seule":True,"ocr_effectue":False,
            "publication_active":False,"validation_juridique":"non_validee","transcription_verification":"non_verifiee",
            "avertissements":["Copie indexée du texte natif, pas extraction fraîche ni transcription juridique validée.",
                               "Ordre des colonnes et défauts de caractères conservés, aucune correction silencieuse."]}
