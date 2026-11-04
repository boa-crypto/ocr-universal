"""Gestionnaire de formulaires — création sans code, versionnement.

Le builder décrit des formulaires cibles *déclarés par l'utilisateur* : il ne
prétend pas découvrir la structure d'un système distant. Chaque version est
conservée, comparable, et un modèle obsolète peut être désactivé sans perdre
l'historique des mappings qui l'ont utilisé.
"""
from __future__ import annotations

import copy
import json
import logging
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .contract import FieldSchema

log = logging.getLogger("unocr.connectors.forms")

# les 9 types de champs imposés par le cahier des charges
FIELD_TYPES = ("text", "number", "date", "amount", "currency", "list",
               "checkbox", "identifier", "repeating_table", "linked_reference")

# types pour lesquels une valeur vide est refusée à la validation
_FORMAT_HINTS = {
    "number": "nombre",
    "amount": "montant décimal",
    "date": "AAAA-MM-JJ",
    "currency": "code devise ISO",
    "identifier": "identifiant",
    "checkbox": "oui/non",
}

_TYPED_FORMATS = {
    "number": "decimal",
    "amount": "decimal",
    "date": "iso_date",
    "currency": "decimal",
    "identifier": "identifier",
    "checkbox": "boolean",
}


class FieldRule(BaseModel):
    """Règle de validation déclarée sur un champ."""
    kind: str = "format"          # format | required | length | allowed_values
    value: Any = None
    message: str = ""


class FormField(BaseModel):
    """Un champ du formulaire, tel que décrit dans le builder."""
    key: str
    label: str = ""
    type: str = "text"
    required: bool = False
    default_value: str | None = None
    allowed_values: list[str] = Field(default_factory=list)
    min_length: int | None = None
    max_length: int | None = None
    decimals: int | None = None
    help_text: str = ""
    order: int = 0

    @field_validator("type")
    @classmethod
    def _type_must_be_known(cls, v: str) -> str:
        if v not in FIELD_TYPES:
            raise ValueError(f"type de champ inconnu : {v}")
        return v

    @field_validator("key")
    @classmethod
    def _key_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("clé de champ vide")
        return v.strip()

    def to_schema(self) -> FieldSchema:
        """Convertit en schéma de champ consommable par le mapping/validateur."""
        rules: list[FieldRule] = []
        if self.required:
            rules.append(FieldRule(kind="required", message="champ obligatoire"))
        fmt = _TYPED_FORMATS.get(self.type)
        if fmt:
            rules.append(FieldRule(kind="format", value=fmt))
        hint = _FORMAT_HINTS.get(self.type, "")
        if self.decimals is not None:
            hint = f"{self.decimals} décimale(s)"
        if self.max_length:
            rules.append(FieldRule(kind="length", value=self.max_length))
        if self.allowed_values:
            rules.append(FieldRule(kind="allowed_values",
                                   value=list(self.allowed_values)))
        return FieldSchema(
            external_name=self.key, label=self.label or self.key,
            field_type=self.type, required=self.required,
            allowed_values=list(self.allowed_values),
            max_length=self.max_length, format_hint=hint,
            source="declared",
        )


class FormDefinition(BaseModel):
    """Un modèle de formulaire, versionné."""
    form_id: str
    name: str = ""
    description: str = ""
    fields: list[FormField] = Field(default_factory=list)
    version: int = 1
    active: bool = True
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    notes: str = ""

    def schema(self):
        from .contract import FormSchema

        return FormSchema(
            form_id=self.form_id, label=self.name or self.form_id,
            fields=[f.to_schema() for f in self.fields],
            version=str(self.version), source="declared",
            notes=self.description or self.notes,
        )

    def summary(self) -> dict:
        return {"form_id": self.form_id, "name": self.name or self.form_id,
                "version": self.version, "active": self.active,
                "fields": len(self.fields), "updated_at": self.updated_at}


class FormStore:
    """Persistance locale des modèles de formulaires (JSON atomique)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "forms.json"
        self._forms: dict[str, FormDefinition] = {}
        self._load()

    # ─────────────────────────── persistance ───────────────────────────
    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for fid, raw in data.items():
                self._forms[fid] = FormDefinition(**raw)
        except (OSError, ValueError) as exc:
            # un fichier illisible ne doit jamais empêcher l'application de
            # démarrer : on repart d'un magasin vide
            log.warning("formulaires illisibles (%s) : magasin réinitialisé", exc)
            self._forms = {}

    def _save(self) -> None:
        data = {fid: f.model_dump() for fid, f in self._forms.items()}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self.path)

    # ─────────────────────────── API ───────────────────────────
    def create(self, form: FormDefinition) -> FormDefinition:
        if form.form_id in self._forms:
            raise ValueError(f"identifiant de formulaire déjà utilisé : "
                             f"{form.form_id}")
        self._forms[form.form_id] = form
        self._save()
        log.info("formulaire créé : %s (%d champs)", form.form_id,
                 len(form.fields))
        return form

    def get(self, form_id: str) -> FormDefinition | None:
        return self._forms.get(form_id)

    def list(self, include_inactive: bool = False) -> list[FormDefinition]:
        out = [f for f in self._forms.values() if include_inactive or f.active]
        return sorted(out, key=lambda f: (f.name or f.form_id).lower())

    def update(self, form_id: str, **changes) -> FormDefinition:
        """Modifie un formulaire **en créant une nouvelle version**.

        L'ancienne version reste consultable via `versions()`.
        """
        cur = self._forms.get(form_id)
        if cur is None:
            raise KeyError(f"formulaire inconnu : {form_id}")
        new = copy.deepcopy(cur)
        for k, v in changes.items():
            if hasattr(new, k) and v is not None:
                setattr(new, k, v)
        new.version = cur.version + 1
        new.updated_at = time.time()
        self._forms[form_id] = new
        self._save()
        log.info("formulaire %s → version %d", form_id, new.version)
        return new

    def disable(self, form_id: str) -> FormDefinition:
        """Désactive un modèle obsolète sans le supprimer."""
        cur = self._forms.get(form_id)
        if cur is None:
            raise KeyError(f"formulaire inconnu : {form_id}")
        new = copy.deepcopy(cur)
        new.active = False
        new.updated_at = time.time()
        self._forms[form_id] = new
        self._save()
        log.info("formulaire %s désactivé (conservé)", form_id)
        return new

    def delete(self, form_id: str) -> bool:
        if form_id not in self._forms:
            return False
        del self._forms[form_id]
        self._save()
        return True

    def diff(self, form_id: str, other: FormDefinition) -> dict:
        """Compare deux versions : champs ajoutés, retirés, modifiés."""
        a = self._forms.get(form_id)
        if a is None:
            raise KeyError(f"formulaire inconnu : {form_id}")
        return self._compare(a, other)

    @staticmethod
    def _compare(a: FormDefinition, b: FormDefinition) -> dict:
        fa = {f.key: f.model_dump() for f in a.fields}
        fb = {f.key: f.model_dump() for f in b.fields}
        added = sorted(set(fb) - set(fa))
        removed = sorted(set(fa) - set(fb))
        changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
        return {"added": added, "removed": removed, "changed": changed,
                "from_version": a.version, "to_version": b.version}


class FormBuilder:
    """Construction interactive d'un formulaire (utilisé par l'assistant)."""

    def __init__(self) -> None:
        self._fields: list[FormField] = []

    def add_field(self, key: str, label: str = "", type: str = "text",
                  required: bool = False, **kw) -> FormBuilder:
        if type not in FIELD_TYPES:
            raise ValueError(f"type de champ inconnu : {type} "
                             f"(autorisés : {', '.join(FIELD_TYPES)})")
        if not key or not key.strip():
            raise ValueError("clé de champ vide")
        if any(f.key == key for f in self._fields):
            raise ValueError(f"champ déjà défini : {key}")
        self._fields.append(FormField(
            key=key.strip(), label=label or key, type=type,
            required=required, order=len(self._fields), **kw))
        return self

    def build(self, form_id: str, name: str = "", description: str = "") -> FormDefinition:
        if not self._fields:
            raise ValueError("un formulaire doit avoir au moins un champ")
        return FormDefinition(form_id=form_id, name=name or form_id,
                              description=description,
                              fields=list(self._fields))

    @staticmethod
    def field_types() -> list[str]:
        return list(FIELD_TYPES)


# ─────────────────── formuliers types préremplis (Mode C) ───────────────────

def customs_declaration_template() -> FormDefinition:
    """Trame déclaration douanière — **structure proposée, non officielle**.

    Aucun de ces champs n'est validé comme étant le format officiel d'un
    organisme : c'est une base de travail à ajuster selon la spécification
    fournie par l'administration concernée.
    """
    b = FormBuilder()
    b.add_field("declaration_number", "N° de déclaration", "identifier", True)
    b.add_field("manifest_reference", "N° de manifeste", "identifier")
    b.add_field("bill_of_lading", "N° de connaissement (BL)", "identifier")
    b.add_field("importer_name", "Importateur", "text", True)
    b.add_field("exporter_name", "Exportateur", "text")
    b.add_field("customs_broker", "Transitaire", "text")
    b.add_field("tax_id", "Identifiant fiscal", "identifier", True)
    b.add_field("hs_code", "Code SH", "identifier", True)
    b.add_field("goods_description", "Description des marchandises", "text", True,
                max_length=500)
    b.add_field("origin_country", "Pays d'origine", "list", True,
                allowed_values=["DZ", "FR", "ES", "IT", "DE", "CN", "US", "TN",
                                "MA", "TR"])
    b.add_field("regime", "Régime douanier", "list",
                allowed_values=["import", "export", "transit", "temporary"])
    b.add_field("packages", "Nombre de colis", "number", True)
    b.add_field("gross_weight", "Poids brut (kg)", "amount", True, decimals=3)
    b.add_field("net_weight", "Poids net (kg)", "amount", decimals=3)
    b.add_field("customs_value", "Valeur en douane", "amount", True, decimals=2)
    b.add_field("currency", "Devise", "currency", True,
                allowed_values=["DZD", "EUR", "USD"])
    b.add_field("containers", "Conteneurs", "repeating_table")
    b.add_field("seals", "Scellés", "repeating_table")
    b.add_field("loading_port", "Port de chargement", "text")
    b.add_field("discharge_port", "Port de déchargement", "text")
    return b.build("customs_declaration", "Déclaration en douane",
                   "Trame de travail — à conformer à la spécification officielle")


def port_call_template() -> FormDefinition:
    """Trame escale / autorité portuaire — **structure proposée**.

    Idem : à valider contre la documentation réelle du port concerné.
    """
    b = FormBuilder()
    b.add_field("port_call_id", "Identifiant d'escale", "identifier", True)
    b.add_field("vessel_name", "Nom du navire", "text", True)
    b.add_field("voyage_number", "N° de voyage", "identifier", True)
    b.add_field("imo_number", "N° OMI", "identifier")
    b.add_field("eta", "Arrivée estimée", "date", True)
    b.add_field("etd", "Départ estimé", "date")
    b.add_field("arrival_notice", "Annonce d'arrivée", "identifier")
    b.add_field("manifest_id", "Manifeste", "identifier")
    b.add_field("bill_of_lading", "Connaissement", "identifier")
    b.add_field("goods_count", "Nombre de marchandises", "number")
    b.add_field("container_count", "Nombre de conteneurs", "number")
    b.add_field("previous_port", "Port précédent", "text")
    b.add_field("next_port", "Port suivant", "text")
    b.add_field("status", "Statut d'escale", "list",
                allowed_values=["planned", "arrived", "berthed", "departed"])
    b.add_field("declaration_refs", "Déclarations liées", "linked_reference")
    return b.build("port_call", "Escale portuaire",
                   "Trame de travail — à valider avec l'autorité portuaire")


TEMPLATES = {
    "customs_declaration": customs_declaration_template,
    "port_call": port_call_template,
}


def load_template(name: str) -> FormDefinition | None:
    fn = TEMPLATES.get(name)
    return fn() if fn else None
