"""Corpus documentaire déclaré : aucune consolidation ni applicabilité acquise."""
from collections import defaultdict, deque
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import ArticleVersion, RelationDocumentee, SourceDocument, StrictModel


class DocumentJuridique(SourceDocument):
    format: Literal["pdf"]
    nature_document: Literal["code_original", "acte_modificatif", "compilation"]


class RelationJuridique(RelationDocumentee):
    type_relation: Literal["modifie", "complete", "abroge", "rectifie", "renvoie_a"]


class CodeDocumentaireBatch(StrictModel):
    schema_version: Literal["1"] = "1"
    documents: list[DocumentJuridique] = Field(min_length=1, max_length=64)
    articles: list[ArticleVersion] = Field(default_factory=list, max_length=50_000)
    relations: list[RelationJuridique] = Field(default_factory=list, max_length=100_000)
    statut: Literal["quarantaine"] = "quarantaine"
    validation_juridique: Literal["non_validee"] = "non_validee"
    publication_active: Literal[False] = False

    @field_validator("publication_active", mode="before")
    @classmethod
    def aucune_publication(cls, valeur):
        if valeur is not False:
            raise ValueError("Publication active strictement false requise")
        return valeur

    @model_validator(mode="after")
    def integrite_documentaire(self):
        documents = {d.id: d for d in self.documents}
        articles = {a.id: a for a in self.articles}
        if len(documents) != len(self.documents) or len(articles) != len(self.articles):
            raise ValueError("Identifiant de document/article dupliqué")
        versions = set()
        roles = {"originale": "code_original", "modificative": "acte_modificatif", "consolidee_provisoire": "compilation"}
        for doc in self.documents:
            if not doc.id.strip() or not doc.titre.strip():
                raise ValueError("Document sans identifiant/titre non vide")
        for article in self.articles:
            refs = [article.reference, *article.historique_modifications]
            for ref in refs:
                if ref.source_id not in documents or not ref.localisateur.strip():
                    raise ValueError("Source absente ou localisateur vide")
            if any(documents[ref.source_id].nature_document != "acte_modificatif" for ref in article.historique_modifications):
                raise ValueError("Historique : source modificative distincte requise")
            for traduction in (article.texte_francais, article.texte_arabe):
                if traduction is not None and not traduction.strip():
                    raise ValueError("Texte linguistique vide : utiliser null")
            doc = documents[article.reference.source_id]
            if roles[article.nature_version] != doc.nature_document:
                raise ValueError("Nature d'article incompatible avec le rôle documentaire déclaré")
            if not article.id.strip() or not article.numero_article.strip() or not article.texte_integral.strip() or not article.version_juridique.strip():
                raise ValueError("Article sans identifiant/numéro/texte non vide")
            if (not article.hierarchie or article.hierarchie[0].niveau != "texte_legislatif"
                    or not any(n.niveau == "article" and n.identifiant == article.numero_article for n in article.hierarchie)
                    or any(not n.identifiant.strip() for n in article.hierarchie)):
                raise ValueError("Hiérarchie texte/article explicite et cohérente requise")
            cle = (doc.id, article.numero_article, article.version_juridique)
            if cle in versions:
                raise ValueError("Version d'article dupliquée pour la même source")
            versions.add(cle)
            if article.nature_version == "originale":
                if article.texte_origine is not None and article.texte_origine != article.texte_integral:
                    raise ValueError("Texte d'origine distinct : conserver une version séparée")
            elif article.nature_version == "modificative":
                if article.texte_origine is not None or (article.texte_modificatif is not None and article.texte_modificatif != article.texte_integral):
                    raise ValueError("Disposition modificative et texte original doivent rester séparés")
            elif article.texte_origine is not None or article.texte_modificatif is not None:
                raise ValueError("Compilation provisoire distincte des originaux et modifications")

        identifiants, preuves, liens = set(), set(), set()
        graphe, degres = defaultdict(set), {cle: 0 for cle in articles}
        for relation in self.relations:
            if not all(v.strip() for v in (relation.id, relation.justification, relation.reference.localisateur)):
                raise ValueError("Relation sans identifiant, justification ou localisateur")
            if relation.id in identifiants or relation.origine_id not in articles or relation.cible_id not in articles:
                raise ValueError("Relation dupliquée ou extrémité absente du lot")
            identifiants.add(relation.id)
            if relation.origine_id == relation.cible_id:
                raise ValueError("Auto-relation interdite")
            origine, cible = articles[relation.origine_id], articles[relation.cible_id]
            if relation.reference.source_id != origine.reference.source_id:
                raise ValueError("La preuve de relation doit référencer la source de l'article d'origine")
            cle = (relation.origine_id, relation.cible_id, relation.type_relation,
                   relation.reference.source_id, relation.reference.localisateur)
            if cle in preuves:
                raise ValueError("Preuve de relation dupliquée")
            preuves.add(cle)
            liens.add((relation.origine_id, relation.cible_id))
            if relation.type_relation != "renvoie_a":
                if origine.nature_version != "modificative":
                    raise ValueError("Modification/abrogation doit provenir d'une disposition modificative")
                debut = documents[origine.reference.source_id].date_publication
                fin = documents[cible.reference.source_id].date_publication
                if debut and fin and debut < fin:
                    raise ValueError("Chronologie de publication déclarée contradictoire")
                if relation.cible_id not in graphe[relation.origine_id]:
                    graphe[relation.origine_id].add(relation.cible_id)
                    degres[relation.cible_id] += 1
        for article in self.articles:
            if len(set(article.articles_lies)) != len(article.articles_lies):
                raise ValueError("Lien d'article dupliqué")
            if any((article.id, cible) not in liens for cible in article.articles_lies):
                raise ValueError("Lien d'article sans relation documentaire justifiée")
        # Renvois réciproques permis, cycles de modifications refusés ; pas de
        # récursion dépendant du nombre d'articles et pas de consolidation.
        file = deque(cle for cle, degre in degres.items() if degre == 0)
        visites = 0
        while file:
            cle = file.popleft()
            visites += 1
            for cible in graphe[cle]:
                degres[cible] -= 1
                if degres[cible] == 0:
                    file.append(cible)
        if visites != len(articles):
            raise ValueError("Cycle de modifications déclaré")
        return self


class EntreeDocument(StrictModel):
    document: DocumentJuridique
    fichier_recu: str = Field(min_length=1)


class MetadataCode(StrictModel):
    documents: list[EntreeDocument] = Field(min_length=1, max_length=64)
