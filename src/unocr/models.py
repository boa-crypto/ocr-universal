"""Modèles de données UniOCR (pydantic v2).

Chaque valeur extraite conserve : la transcription brute (raw), la valeur normalisée,
la valeur corrigée par règle métier, et la valeur confirmée par un utilisateur.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from fastapi import Body
from pydantic import AliasChoices, BaseModel, Field


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


# ============================================================ workflow
# Système de suivi visuel intelligent des dossiers clients (mission UniOCR)

class WorkflowStatus(str, Enum):
    TERMINE = "termine"    # vert
    EN_COURS = "en_cours"  # bleu
    EN_ATTENTE = "en_attente"  # gris
    BLOQUE = "bloque"      # rouge
    A_VALIDER = "a_valider"  # orange
    NON_APPLICABLE = "non_applicable"  # gris neutre


class WorkflowStage(str, Enum):
    ETAPE_1_CREATION = "etape_1_creation"
    ETAPE_2_SCAN = "etape_2_scan"
    ETAPE_3_OCR = "etape_3_ocr"
    ETAPE_4_VERIFICATION = "etape_4_verification"
    ETAPE_5_DOUANE = "etape_5_douane"
    ETAPE_6_PORT = "etape_6_port"
    ETAPE_7_TRANSPORT = "etape_7_transport"
    ETAPE_8_CLOTURE = "etape_8_cloture"


class WorkflowStageStatus(BaseModel):
    """Statut d'une étape de workflow avec suivi dynamique."""
    stage: WorkflowStage
    status: WorkflowStatus
    date_debut: Optional[float] = None
    date_fin: Optional[float] = None
    duree: Optional[float] = None  # en secondes
    responsable: str = ""
    pourcentage: float = 0.0  # 0-100
    motif_blocage: str = ""
    détails: dict[str, Any] = Field(default_factory=dict)


class WorkflowTemplate(BaseModel):
    """Modèle de workflow définissant les 8 étapes et leur configuration."""
    id: str = Field(default_factory=lambda: new_id("wf_tpl_"))
    nom: str
    description: str
    etapes: list[WorkflowStage] = Field(default_factory=lambda: [
        WorkflowStage.ETAPE_1_CREATION,
        WorkflowStage.ETAPE_2_SCAN,
        WorkflowStage.ETAPE_3_OCR,
        WorkflowStage.ETAPE_4_VERIFICATION,
        WorkflowStage.ETAPE_5_DOUANE,
        WorkflowStage.ETAPE_6_PORT,
        WorkflowStage.ETAPE_7_TRANSPORT,
        WorkflowStage.ETAPE_8_CLOTURE,
    ])
    conditions_entree: dict[str, Any] = Field(default_factory=dict)
    conditions_sortie: dict[str, Any] = Field(default_factory=dict)
    actif: bool = True


class WorkflowInstance(BaseModel):
    """Une instance de workflow liée à un dossier de transit."""
    id: str = Field(default_factory=lambda: new_id("wf_inst_"))
    dossier_id: str
    template_id: str
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    etapes: dict[WorkflowStage, WorkflowStageStatus] = Field(default_factory=dict)
    statut_global: WorkflowStatus = WorkflowStatus.EN_ATTENTE
    responsable_global: str = ""
    historique: list[dict[str, Any]] = Field(default_factory=list)
    arbitrages: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def get_etape(self, stage: WorkflowStage) -> WorkflowStageStatus:
        if stage not in self.etapes:
            # Créer automatiquement l'étape si elle n'existe pas
            self.etapes[stage] = WorkflowStageStatus(stage=stage, status=WorkflowStatus.EN_ATTENTE)
        return self.etapes[stage]

    def set_etape_status(self, stage: WorkflowStage, status: WorkflowStatus,
                        responsable: str = "", motif: str = "") -> WorkflowStageStatus:
        etape = self.get_etape(stage)
        etape.status = status
        if status == WorkflowStatus.TERMINE:
            etape.date_fin = time.time()
            if etape.date_debut:
                etape.duree = etape.date_fin - etape.date_debut
        elif status == WorkflowStatus.EN_COURS and not etape.date_debut:
            etape.date_debut = time.time()
        etape.responsable = responsable
        if motif:
            etape.motif_blocage = motif
        self.updated_at = time.time()
        self._journaliser("etape_modifiee", {
            "stage": stage.value,
            "status": status.value,
            "responsable": responsable,
            "motif": motif,
        })
        return etape

    def _journaliser(self, action: str, detail: dict[str, Any]) -> None:
        self.historique.append({
            "ts": time.time(),
            "action": action,
            "detail": detail,
        })
        # Garder seulement les 200 derniers événements
        if len(self.historique) > 200:
            self.historique = self.historique[-200:]


class DocumentValidation(BaseModel):
    """Validation d'un document dans le workflow."""
    id: str = Field(default_factory=lambda: new_id("dv_"))
    dossier_id: str
    piece_job_id: str  # job_id de la pièce
    validee: bool = False
    valide_par: str = ""
    date_validation: Optional[float] = None
    commentaire: str = ""
    anomalies_detectees: list[str] = Field(default_factory=list)
    notes: str = ""

    def marquer_validee(self, par: str, commentaire: str = "") -> None:
        self.validee = True
        self.valide_par = par
        self.date_validation = time.time()
        self.commentaire = commentaire
        self._journaliser("validee", {"par": par, "commentaire": commentaire})


class UserAssignment(BaseModel):
    """Affectation d'un utilisateur à une étape de workflow."""
    id: str = Field(default_factory=lambda: new_id("ua_"))
    workflow_id: str
    etape: WorkflowStage
    utilisateur: str  # identifiant utilisateur
    rôle: str
    date_assignation: float = Field(default_factory=time.time)
    derniere_activation: float = Field(default_factory=time.time)
    motif: str = ""

    def rafraîchir_activation(self) -> None:
        self.derniere_activation = time.time()


class WorkflowNotification(BaseModel):
    """Notification liée au workflow."""
    id: str = Field(default_factory=lambda: new_id("wf_notif_"))
    workflow_id: str
    type: str  # etape_modifiee, blocage, validation, blocage_levé, etc.
    titre: str
    message: str
    lu: bool = False
    create_at: float = Field(default_factory=time.time)
    lien_action: str = ""  # URL ou identifiant pour l'action


# Helper pour calculer la progression globale du workflow
def calculer_progression(workflow: WorkflowInstance) -> dict[str, Any]:
    """Calcule la progression globale basée sur les étapes terminées."""
    etapes = workflow.etapes
    if not etapes:
        return {"globale": 0, "etapes_par_statut": {}, "étape_courante": None}

    # Compter les étapes par statut
    comptage: dict[str, int] = {}
    for stage in WorkflowStage:
        if stage in etapes:
            s = etapes[stage].status
            comptage[s] = comptage.get(s, 0) + 1

    # Calculer pourcentage: uniquement les étapes TERMINÉE comptent
    total_etapes = len(etapes)
    etapes_terminees = comptage.get(WorkflowStatus.TERMINE.value, 0)
    progression_globale = round(etapes_terminees / total_etapes * 100) if total_etapes > 0 else 0

    # Trouver l'étape en cours (la première non TERMINÉE dans l'ordre)
    ordre = [
        WorkflowStage.ETAPE_1_CREATION,
        WorkflowStage.ETAPE_2_SCAN,
        WorkflowStage.ETAPE_3_OCR,
        WorkflowStage.ETAPE_4_VERIFICATION,
        WorkflowStage.ETAPE_5_DOUANE,
        WorkflowStage.ETAPE_6_PORT,
        WorkflowStage.ETAPE_7_TRANSPORT,
        WorkflowStage.ETAPE_8_CLOTURE,
    ]

    etape_courante: Optional[WorkflowStageStatus] = None
    for s in ordre:
        if s in etapes:
            etape = etapes[s]
            if etape.status != WorkflowStatus.TERMINE:
                etape_courante = etape
                break

    # Si toutes terminées, l'étape courante est la dernière
    if etape_courante is None and etapes_terminees == total_etapes:
        # Toutes terminées, pas d'étape en cours
        etape_courante = None

    return {
        "globale": progression_globale,
        "etapes_par_statut": {k: v for k, v in comptage.items()},
        "étape_courante": etape_courante.stage.value if etape_courante else None,
    }


# Helper pour obtenir la liste des étapes non applicables
def obtenir_etapes_non_applicables(workflow: WorkflowInstance) -> list[dict[str, Any]]:
    """Retourne les étapes marquées comme NON APPLICABLE avec justification."""
    resultats = []
    for stage, etape in workflow.etapes.items():
        if etape.status == WorkflowStatus.NON_APPLICABLE:
            resultats.append({
                "stage": stage.value,
                "motif": etape.motif_blocage,
                "responsable": etape.responsable,
                "justification": etape.détaillés.get("justification", ""),
            })
    return resultats


# Helper pour vérifier si une étape peut être passée à l'étape suivante
def peut_passer_suivante(workflow: WorkflowInstance) -> bool:
    """Vérifie si toutes les étapes obligatoires avant l'étape courante sont terminées."""
    ordre = [
        WorkflowStage.ETAPE_1_CREATION,
        WorkflowStage.ETAPE_2_SCAN,
        WorkflowStage.ETAPE_3_OCR,
        WorkflowStage.ETAPE_4_VERIFICATION,
        WorkflowStage.ETAPE_5_DOUANE,
        WorkflowStage.ETAPE_6_PORT,
        WorkflowStage.ETAPE_7_TRANSPORT,
    ]

    # Vérifier que toutes les étapes précédentes sont TERMINÉE
    for s in ordre:
        if s not in workflow.etapes:
            # Étape absente du workflow - continuer (peut être non applicable)
            continue
        if workflow.etapes[s].status != WorkflowStatus.TERMINE:
            return False

    return True


class BBox(BaseModel):
    """Boîte englobante en pixels, origine haut-gauche de la page."""
    x0: float
    y0: float
    x1: float
    y1: float
    page_width: Optional[float] = None
    page_height: Optional[float] = None

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def as_list(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]

    def to_relative(self) -> list[float]:
        if not self.page_width or not self.page_height:
            return self.as_list()
        return [
            self.x0 / self.page_width,
            self.y0 / self.page_height,
            self.x1 / self.page_width,
            self.y1 / self.page_height,
        ]


# ---------------------------------------------------------------- unités texte
class Word(BaseModel):
    text: str
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)  # confiance moteur
    engine: str = "unknown"
    page_num: int = 1


class TextLine(BaseModel):
    text: str
    bbox: BBox
    words: list[Word] = Field(default_factory=list)
    direction: str = "ltr"  # ltr | rtl
    confidence: float = 1.0


class TextBlock(BaseModel):
    text: str
    bbox: BBox
    order: int = 0
    column: int = 0
    lines: list[TextLine] = Field(default_factory=list)
    kind: str = "paragraph"  # paragraph | heading | table | form | other


# ---------------------------------------------------------------- tableaux
class Cell(BaseModel):
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    text: str = ""
    bbox: Optional[BBox] = None
    confidence: float = 1.0
    engine: str = "unknown"
    is_header: bool = False


class Table(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tbl_"))
    page_num: int = 1
    bbox: Optional[BBox] = None
    n_rows: int = 0
    n_cols: int = 0
    cells: list[Cell] = Field(default_factory=list)
    method: str = "unknown"  # ruled | clustering | native | digital
    confidence: float = 1.0
    multipage: bool = False
    page_nums: list[int] = Field(default_factory=list)
    header_rows: int = 0

    def to_matrix(self) -> list[list[str]]:
        grid = [[""] * self.n_cols for _ in range(self.n_rows)]
        for c in self.cells:
            if 0 <= c.row < self.n_rows and 0 <= c.col < self.n_cols:
                grid[c.row][c.col] = c.text
        return grid


# ---------------------------------------------------------------- champs
class FieldStatus(str, Enum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"
    VALIDATED = "validated"


class ValueOrigin(str, Enum):
    RAW = "raw"            # transcription OCR / texte natif
    NORMALIZED = "normalized"
    CORRECTED = "corrected"  # règle métier
    CONFIRMED = "confirmed"  # humain


class FieldValue(BaseModel):
    name: str
    label: str = ""
    raw_value: Optional[str] = None           # transcription originale
    normalized_value: Optional[str] = None    # normalisation automatique
    corrected_value: Optional[str] = None     # correction par règle métier (traçable)
    confirmed_value: Optional[str] = None     # validation humaine
    value_origin: ValueOrigin = ValueOrigin.RAW
    source: str = "ocr"                       # ocr | native | rule | user | digital
    confidence: float = 0.0                   # confiance globale système
    calibrated_confidence: Optional[float] = None   # A2 : probabilité calibrée
    engine_confidence: float = 0.0            # confiance du moteur OCR
    page_num: Optional[int] = None
    bbox: Optional[BBox] = None
    status: FieldStatus = FieldStatus.DETECTED
    pattern: Optional[str] = None             # motif ayant permis la détection
    anomalies: list[str] = Field(default_factory=list)
    profile: Optional[str] = None

    @property
    def value(self) -> Optional[str]:
        """Valeur finale : confirmée > corrigée > normalisée > brute."""
        return (
            self.confirmed_value
            or self.corrected_value
            or self.normalized_value
            or self.raw_value
        )


# ---------------------------------------------------------------- qualité
class PageQuality(BaseModel):
    brightness: float = 0.0          # 0-255
    contrast: float = 0.0            # écart-type luminance
    blur_score: float = 0.0          # variance laplacienne
    noise_score: float = 0.0
    estimated_skew_deg: float = 0.0
    estimated_dpi: float = 0.0
    ink_ratio: float = 0.0           # proportion de pixels "encre"
    is_blank: bool = False
    issues: list[str] = Field(default_factory=list)


class PreprocessOp(BaseModel):
    name: str
    applied: bool = False
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class EngineRun(BaseModel):
    engine: str
    page_num: int
    languages: list[str] = Field(default_factory=list)
    mean_confidence: float = 0.0
    word_count: int = 0
    duration_ms: float = 0.0
    ok: bool = True
    error: Optional[str] = None


class Anomaly(BaseModel):
    code: str
    severity: str = "info"  # info | warning | error
    message: str
    page_num: Optional[int] = None
    bbox: Optional[BBox] = None
    context: dict[str, Any] = Field(default_factory=dict)


class Disagreement(BaseModel):
    """Désaccord entre moteurs sur une zone."""
    page_num: int
    bbox: Optional[BBox] = None
    text_by_engine: dict[str, str] = Field(default_factory=dict)
    resolution: str = "flagged"  # flagged | best_confidence | human_review


class PageResult(BaseModel):
    page_num: int
    width: float
    height: float
    text: str = ""
    blocks: list[TextBlock] = Field(default_factory=list)
    lines: list[TextLine] = Field(default_factory=list)
    words: list[Word] = Field(default_factory=list)
    quality: PageQuality = Field(default_factory=PageQuality)
    preprocess_ops: list[PreprocessOp] = Field(default_factory=list)
    engine_runs: list[EngineRun] = Field(default_factory=list)
    orientation_deg: int = 0
    detected_languages: list[str] = Field(default_factory=list)
    has_native_text: bool = False
    native_text_ratio: float = 0.0     # couverture du texte natif sur la page
    variant_selected: str = "original" # original | preprocessed
    direction: str = "ltr"            # C3 : ltr | rtl | neutral
    blank: bool = False


class QualityReport(BaseModel):
    mean_engine_confidence: float = 0.0
    mean_global_confidence: float = 0.0
    pages_low_confidence: list[int] = Field(default_factory=list)
    fields_low_confidence: list[str] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)  # contrôles de cohérence


class DocumentInfo(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = None
    doc_number: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    issuer: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    languages: list[str] = Field(default_factory=list)
    page_count: int = 0
    source_format: str = ""

# Données maritimes
class Armement(BaseModel):
    nom_navire: str = ""
    numero_voyage: str = ""
    date_ETA: Optional[str] = None
    date_arrivee_effective: Optional[str] = None
    numero_bl: str = ""
    type_bl: str = ""
    incoterm: str = ""
    lieu_incoterm: str = ""
    devise: str = "EUR"
    valeur_commerciale: Optional[float] = None
    nombre_colis: Optional[int] = None
    poids_brut: Optional[float] = None
    poids_net: Optional[float] = None
    description_marchandises: str = ""
    code_SH: Optional[str] = None
    nombre_conteneurs: Optional[int] = None
    references_conteneurs: list[str] = Field(default_factory=list)

class Expeditions(BaseModel):
    id: str = Field(default_factory=lambda: new_id("exp_"))
    dossier_id: str
    navire: str = ""
    porte_chargement: str = ""
    porte_destination: str = ""
    ETA: Optional[str] = None
    arrivee_effective: Optional[str] = None
    numero_bl: str = ""
    type_bl: str = ""
    date_emission: Optional[str] = Field(default=None, validation_alias=AliasChoices("date_emission", "date_émission"))
    nom_gestionnaire: str = ""
    priorite: str = "normale"
    observations: str = ""

class DeclarationDouane(BaseModel):
    id: str = Field(default_factory=lambda: new_id("decl_"))
    dossier_id: str
    date_declaration: str
    organisme_emetteur: str = ""
    reference: str = ""
    autorisation_reqisee: bool = False
    regime_douanier: str = ""
    origine: str = ""
    controle: bool = False
    validite_documentaire: bool = False
    date_application_regle: Optional[str] = None

class PaiementFrais(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pai_"))
    dossier_id: str
    categorie: str = ""  # fret, transport, portuaire, droits, etc.
    fournisseur: str = ""
    montant: float = 0.0
    devise: str = "EUR"
    date: str = ""
    reference_facture: str = ""
    justificatif: str = ""
    statut_paiement: str = "en_attente"  # en_attente, valide, paye, en_retard
    commentaire: str = ""


class ExportRecord(BaseModel):
    format: str
    path: str
    size_bytes: int = 0


class DocumentResult(BaseModel):
    id: str = Field(default_factory=lambda: new_id("doc_"))
    created_at: float = Field(default_factory=time.time)
    info: DocumentInfo = Field(default_factory=DocumentInfo)
    pages: list[PageResult] = Field(default_factory=list)
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    tables: list[Table] = Field(default_factory=list)
    categories: dict[str, list[str]] = Field(default_factory=dict)  # catégorie -> noms de champs
    barcodes: list[dict[str, Any]] = Field(default_factory=list)
    form_zones: list[dict[str, Any]] = Field(default_factory=list)
    quality: QualityReport = Field(default_factory=QualityReport)
    engines_used: list[str] = Field(default_factory=list)
    direction: str = "ltr"            # C3 : direction dominante du document
    profile_used: Optional[str] = None
    classification: Optional[dict[str, Any]] = None   # étape 4 : type deviné + preuves
    timings_ms: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    source_file: str = ""
    source_hash: str = ""
    exports: list[ExportRecord] = Field(default_factory=list)


# ---------------------------------------------------------------- jobs
class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class JobOptions(BaseModel):
    languages: list[str] = Field(default_factory=list)   # vide = auto
    profile: str = "generic"
    quality_mode: str = "accurate"  # fast | accurate
    preprocess: bool = True
    preprocess_mode: str = "standard"   # off | standard | aggressive
    variant_comparison: bool = True     # comparer original vs prétraité (accurate)
    export_formats: list[str] = Field(default_factory=lambda: ["json", "txt"])
    # --- options de traitement ---
    page_range: str = ""            # ex. "1-3, 5" — vide = toutes les pages
    render_dpi: int = 200           # résolution de rendu PDF (100–400)
    engine: str = "auto"            # auto | tesseract | native | indra
    extract_fields: bool = True
    extract_tables: bool = True
    extract_barcodes: bool = True
    min_confidence_review: float = 0.7  # seuil de revue humaine (0–1)
    auto_classify: bool = True   # classer le document avant de choisir le profil


class Job(BaseModel):
    id: str = Field(default_factory=lambda: new_id("job_"))
    filename: str = ""
    status: JobStatus = JobStatus.QUEUED
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    error: Optional[str] = None
    options: JobOptions = Field(default_factory=JobOptions)
    result_id: Optional[str] = None
    progress: float = 0.0
    stage: str = ""
    attempts: int = 0
    file_hash: Optional[str] = None  # empreinte SHA-256 (déduplication)


# ─────────────────────────────────────────────────────────────
# Module 01 : Clients
# Gestion des importateurs, agents, représentants.
# ─────────────────────────────────────────────────────────────

class ClientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Client(BaseModel):
    """Modèle représentant un importateur, agent ou représentant."""

    id: str = Field(default_factory=lambda: new_id("client_"))
    name: str = Body(..., min_length=1, max_length=100, description="Nom du client")
    legal_name: str = Body(..., min_length=1, max_length=100, description="Nom commercial")
    status: ClientStatus = ClientStatus.ACTIVE
    website: str = Body("", max_length=255, description="Site web")
    tax_id: str = Body("", max_length=50, description="ID fiscal / TVA")
    phone: str = Body("", max_length=50, description="Téléphone")
    email: str = Body("", max_length=254, description="Email")
    address: str = Body("", max_length=255, description="Adresse")
    city: str = Body("", max_length=50, description="Ville")
    country: str = Body("DZ", max_length=2, description="Pays (code ISO 3166-1 alpha-2)")
    region: str = Body("", max_length=50, description="Wilaya / Région")
    postal_code: str = Body("", max_length=10, description="Code postal")
    contacts: list[str] = Field(default_factory=list, description="Liste des contacts")
    notes: str = Body("", description="Notes libres")
    # Champs additionnels pour le module transit maritime
    entreprise: str = Body("", max_length=200, description="Raison sociale de l'entreprise")
    wilaya: str = Body("", max_length=100, description="Wilaya de domiciliation")
    telephone_contact: str = Body("", max_length=50, description="Téléphone de contact")
    email_contact: str = Body("", max_length=254, description="Email de contact")
    banque_domiciliataire: str = Body("", max_length=100, description="Banque domiciliataire")
    mandant_representant: str = Body("", max_length=200, description="Mandat ou procuration du représentant")

    def is_active(self) -> bool:
        return self.status == ClientStatus.ACTIVE

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "status": self.status.value,
            "website": self.website,
            "tax_id": self.tax_id,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "city": self.city,
            "country": self.country,
            "region": self.region,
            "postal_code": self.postal_code,
            "contacts": self.contacts,
            "notes": self.notes,
        }

    def __repr__(self) -> str:
        return f"Client(name={self.name!r}, legal_name={self.legal_name!r})"


# ─────────────────────────────────────────────────────────────
# Module 02 : Dossiers de transit maritime
# ─────────────────────────────────────────────────────────────

class Fournisseur(BaseModel):
    """Fournisseur étranger d'une opération d'importation."""
    id: str = Field(default_factory=lambda: new_id("fourn_"))
    nom: str = ""
    nom_commercial: str = ""
    pays: str = ""  # code ISO 3166-1 alpha-2
    adresse: str = ""
    contact: str = ""
    telephone: str = ""
    email: str = ""
    nif: str = ""
    rc: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nom": self.nom,
            "nom_commercial": self.nom_commercial,
            "pays": self.pays,
            "adresse": self.adresse,
            "contact": self.contact,
            "telephone": self.telephone,
            "email": self.email,
            "nif": self.nif,
            "rc": self.rc,
            "notes": self.notes,
        }


class DossierTransit(BaseModel):
    """Dossier central regroupant toutes les informations relatives à une opération."""
    id: str = Field(default_factory=lambda: new_id("dossier_"))
    reference: str = Field(default_factory=lambda: new_id("DOSS-"))
    client_id: str = ""
    fournisseur_id: str = ""
    creation_date: str = Field(default_factory=time.strftime("%Y-%m-%d"))
    statut: str = "ouvert"  # ouvert, en_cours, bloqué, termine, archive
    agent_responsable: str = ""
    date_echeance: Optional[str] = None

    # Informations maritimes
    pays_origine: str = ""
    pays_provenance: str = ""
    port_chargement: str = ""
    port_dechargement: str = ""
    compagnie_maritime: str = ""
    navire: str = ""
    numero_voyage: str = ""
    eta: Optional[str] = None
    etd: Optional[str] = None
    numero_bl: str = ""

    # Conteneurs
    conteneurs: list[dict[str, str]] = Field(default_factory=list)
    type_conteneur: str = ""
    description_marchandises: str = ""
    quantites: int = 0
    poids_brut: Optional[float] = None
    poids_net: Optional[float] = None
    valeur_commerciale: Optional[float] = None
    devise: str = "EUR"
    incoterm: str = ""
    regime_douanier: str = ""
    position_tarifaire: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "reference": self.reference,
            "client_id": self.client_id,
            "fournisseur_id": self.fournisseur_id,
            "creation_date": self.creation_date,
            "statut": self.statut,
            "agent_responsable": self.agent_responsable,
            "date_echeance": self.date_echeance,
            "pays_origine": self.pays_origine,
            "pays_provenance": self.pays_provenance,
            "port_chargement": self.port_chargement,
            "port_dechargement": self.port_dechargement,
            "compagnie_maritime": self.compagnie_maritime,
            "navire": self.navire,
            "numero_voyage": self.numero_voyage,
            "eta": self.eta,
            "etd": self.etd,
            "numero_bl": self.numero_bl,
            "conteneurs": self.conteneurs,
            "type_conteneur": self.type_conteneur,
            "description_marchandises": self.description_marchandises,
            "quantites": self.quantites,
            "poids_brut": self.poids_brut,
            "poids_net": self.poids_net,
            "valeur_commerciale": self.valeur_commerciale,
            "devise": self.devise,
            "incoterm": self.incoterm,
            "regime_douanier": self.regime_douanier,
            "position_tarifaire": self.position_tarifaire,
        }


class TypeDocument(BaseModel):
    """Type de document accepté par le système OCR."""
    id: str = Field(default_factory=lambda: new_id("type_doc_"))
    nom: str = ""
    code: str = ""  # invoice, bill_of_lading, packing_list, etc.
    description: str = ""
    profil_extraction: str = ""


class ExtractionOCR(BaseModel):
    """Résultat d'une extraction OCR sur un document."""
    id: str = Field(default_factory=lambda: new_id("ocr_"))
    document_id: str = ""
    dossier_id: str = ""
    type_document: str = ""
    texte_complet: str = ""
    pages: list[PageResult] = Field(default_factory=list)
    champs_extraits: list["ChampExtrait"] = Field(default_factory=list)
    classification: Optional[dict[str, Any]] = None
    confiance_globale: float = 0.0
    statut: str = "extracted"  # extracted, validated, corrected
    cree_le: str = Field(default_factory=time.strftime("%Y-%m-%d %H:%M:%S"))
    modifie_le: Optional[str] = None


class ChampExtrait(BaseModel):
    """Champ extrait par l'OCR avec traçabilité."""
    id: str = Field(default_factory=lambda: new_id("champ_"))
    extraction_id: str = ""
    nom: str = ""
    valeur_raw: str = ""
    valeur_normale: Optional[str] = None
    valeur_confirmee: Optional[str] = None
    valeur_correctee: Optional[str] = None
    origine: str = "ocr"
    confiance: float = 0.0
    page_num: Optional[int] = None
    bbox: Optional[BBox] = None
    statut: str = "detected"  # detected, validated, corrected, rejected
    anomalies: list[str] = Field(default_factory=list)
    cree_le: str = Field(default_factory=time.strftime("%Y-%m-%d %H:%M:%S"))


class AnomalieDocumentaire(BaseModel):
    """Anomalie détectée entre documents d'un même dossier."""
    id: str = Field(default_factory=lambda: new_id("anomalie_"))
    dossier_id: str = ""
    regle_violée: str = ""
    type_anomalie: str = ""  # incohérence, manquant, expire, inconnu
    document_source: str = ""
    document_reference: str = ""
    valeur_detectée: str = ""
    valeur_reference: str = ""
    gravite: str = "warning"  # info, warning, error, blocking
    responsable: str = ""
    date_detection: str = Field(default_factory=time.strftime("%Y-%m-%d"))
    action_corrective: str = ""
    statut_resolution: str = "ouvert"  # ouvert, en_traitement, résolu, ignoré
    date_resolution: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Module 06 : Suivi maritime
# ─────────────────────────────────────────────────────────────

class Navire(BaseModel):
    """Navire identifié par son nom et IMO."""
    id: str = Field(default_factory=lambda: new_id("navire_"))
    nom: str = ""
    numero_imo: str = ""
    compagnie: str = ""
    pays_immatri: str = ""
    type_navire: str = ""
    notes: str = ""


class Conteneur(BaseModel):
    """Conteneur maritime avec suivi de position."""
    id: str = Field(default_factory=lambda: new_id("cont_"))
    dossier_id: str = ""
    numero_conteneur: str = ""
    type_conteneur: str = ""  # 20', 40', 40HQ, Reefer, etc.
    poids: float = 0.0
    seal_number: str = ""
    statut: str = "reserve"  # reserve, charged, transit, arrived, discharged, available, waiting, picked_up, delivered
    position_actuelle: str = ""
    date_arrivee_port: Optional[str] = None
    date_depart_port: Optional[str] = None
    observations: str = ""


class Expédition(BaseModel):
    """Expédition maritime avec informations complètes."""
    id: str = Field(default_factory=lambda: new_id("exp_"))
    dossier_id: str = ""
    navire_id: str = ""
    numero_voyage: str = ""
    port_depart: str = ""
    port_arrivee: str = ""
    date_depart: Optional[str] = None
    date_arrivee_prevue: Optional[str] = None
    date_arrivee_effective: Optional[str] = None
    numero_bl: str = ""
    type_bl: str = ""
    gestionsnaire: str = ""
    priorite: str = "normale"
    observations: str = ""


class Connaissement(BaseModel):
    """Connaissement maritime (BL) et ses informations."""
    id: str = Field(default_factory=lambda: new_id("bl_"))
    dossier_id: str = ""
    numero_bl: str = ""
    type_bl: str = ""  # original, telex, seaway
    date_emission: Optional[str] = None
    emetteur: str = ""
    emitant: str = ""
    chargeur: str = ""
    destinataire: str = ""
    notify_party: str = ""
    port_charge: str = ""
    port_decharge: str = ""
    marchandise: str = ""
    nombre_colis: int = 0
    poids_brut: float = 0.0
    poids_net: float = 0.0
    incoterm: str = ""
    devise: str = "EUR"
    valeur: float = 0.0
    statut: str = "attendu"  # attendu, reçu, vérification, original_requis, formalites_en_cours, frais_en_attente
    originals_count: int = 0
    originals_received: int = 0
    frais_maritimes: float = 0.0
    frais_payés: float = 0.0
    bad_reçu: bool = False
    bad_date: Optional[str] = None
    observations: str = ""


class BonADelivrer(BaseModel):
    """Bon à délivrer (Delivery Order)."""
    id: str = Field(default_factory=lambda: new_id("bad_"))
    dossier_id: str = ""
    numero_bl: str = ""
    numero_bad: str = ""
    emetteur: str = ""
    date_emission: Optional[str] = None
    valabilite: Optional[str] = None
    statut: str = "demandé"  # demandé, obtenu, archivé
    date_obtention: Optional[str] = None
    observations: str = ""


# ─────────────────────────────────────────────────────────────
# Module 05 : Réglementation et nomenclature tarifaire
# ─────────────────────────────────────────────────────────────

class ClassificationTarifaire(BaseModel):
    """Position tarifaire douanière (SH/Taric)."""
    id: str = Field(default_factory=lambda: new_id("tarif_"))
    code_tarifaire: str = ""  # Code SH à 6, 8 ou 10 chiffres
    désignation: str = ""
    regime_douanier: str = ""
    droits_importation: float = 0.0
    tva: float = 0.0
    tpc: float = 0.0
    taxes_internes: float = 0.0
    documents_exigibles: list[str] = Field(default_factory=list)
    autorisations_préalables: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    certificats_req: list[str] = Field(default_factory=list)
    controle_conformite: bool = False
    source_officielle: str = ""
    référence_juridique: str = ""
    date_vigueur: Optional[str] = None
    date_mise_a_jour: Optional[str] = None
    statut_validité: bool = True
    notes: str = ""


class RegleReglementaire(BaseModel):
    """Règle réglementaire liée à une position tarifaire."""
    id: str = Field(default_factory=lambda: new_id("regle_"))
    code_tarifaire: str = ""
    type_regle: str = ""  # document, autorisation, contrôle, certificat
    libelle: str = ""
    description: str = ""
    obligatoire: bool = True
    source: str = ""
    référence_juridique: str = ""
    date_vigueur: Optional[str] = None
    date_mise_a_jour: Optional[str] = None
    statut_validité: bool = True
    notes: str = ""


class Autorisation(BaseModel):
    """Autorisation préalable requise pour importation."""
    id: str = Field(default_factory=lambda: new_id("autor_"))
    dossier_id: str = ""
    type_autorisation: str = ""
    numero_autorisation: str = ""
    organismes_emetteur: str = ""
    date_demande: Optional[str] = None
    date_obtention: Optional[str] = None
    date_validité: Optional[str] = None
    statut: str = "demandé"  # demandé, en_instruction, obtenu, refusé, expiré
    documents_soutien: list[str] = Field(default_factory=list)
    observations: str = ""


# ─────────────────────────────────────────────────────────────
# Module 08 : Déclaration en douane
# ─────────────────────────────────────────────────────────────

class DeclarationDouaniere(BaseModel):
    """Déclaration en douane (SAD - Single Administrative Document)."""
    id: str = Field(default_factory=lambda: new_id("decl_"))
    dossier_id: str = ""
    numero_declaration: str = ""
    bureau_douane: str = ""
    date_depot: Optional[str] = Field(default=None, validation_alias=AliasChoices("date_depot", "date_depôt"))
    date_validation: Optional[str] = None
    statut: str = "en_preparation"  # en_preparation, prete, validée, déposée, en_controle, en_visite, en_regularisation, liquidée, payée, mainlevee
    agent_declarant: str = Field(default="", validation_alias=AliasChoices("agent_declarant", "agent_declarat"))
    regime_douanier: str = ""
    origines: list[str] = Field(default_factory=list)
    provenances: list[str] = Field(default_factory=list)
    positions_tarifaires: list[str] = Field(default_factory=list)
    valeurs_en_douane: list[float] = Field(default_factory=list)
    droits_calcules: float = 0.0
    taxes_calculees: float = 0.0
    montant_total: float = 0.0
    documents_justificatifs: list[str] = Field(default_factory=list)
    observations_douane: str = ""
    observations_agent: str = ""
    mainlevee_obtenue: bool = False
    date_mainlevee: Optional[str] = None


class Liquidation(BaseModel):
    """Liquidation des droits et taxes."""
    id: str = Field(default_factory=lambda: new_id("liqu_"))
    dossier_id: str = ""
    declaration_id: str = ""
    date_liquidation: Optional[str] = None
    droits_importation: float = 0.0
    tva: float = 0.0
    tpc: float = 0.0
    taxes_internes: float = 0.0
    total_douane: float = 0.0
    majorations: float = 0.0
    total_a_payer: float = 0.0
    statut: str = "en_attente"  # en_attente, liquidée, payée
    documents_liquidation: list[str] = Field(default_factory=list)
    observations: str = ""


# ─────────────────────────────────────────────────────────────
# Module 10 : Frais, finances et facturation
# ─────────────────────────────────────────────────────────────

class CategorieFrais(str, Enum):
    FRET_MARITIME = "fret_maritime"
    FRAIS_DOCUMENTAIRES = "frais_documentaires"
    FRAIS_MANUTENTION = "frais_manutention"
    MAGASINAGE = "magasinage"
    DROITS_DOUANE = "droits_douane"
    TAXES = "taxes"
    FRAIS_CONTROLE = "frais_controle"
    TRANSPORT_TERRESTRE = "transport_terrestre"
    FRAIS_ADMINISTRATIFS = "frais_administratifs"
    HONORAIRES_TRANSITAIRE = "honoraires_transitaire"
    AUTRES = "autres"


class Frais(BaseModel):
    """Frais liés à un dossier de transit."""
    id: str = Field(default_factory=lambda: new_id("frais_"))
    dossier_id: str = ""
    categorie: str = ""
    fournisseur: str = ""
    montant: float = 0.0
    montant_devise: float = 0.0  # montant dans la devise d'origine
    devise: str = "EUR"
    taux_change: float = 1.0  # taux de change vers EUR
    date: str = ""
    reference_facture: str = ""
    justificatif: str = ""
    justificatifs: list[str] = Field(default_factory=list)  # IDs des justificatifs
    statut_paiement: str = "en_attente"  # en_attente, valide, paye, en_retard, annule, rembourse
    commentaire: str = ""
    avance_client: bool = False  # frais avancés pour le compte du client
    date_echeance: Optional[str] = None  # date d'échéance paiement
    date_paiement: Optional[str] = None  # date de paiement effectif
    mode_paiement: str = ""  # virement, cheque, especes, carte, traites
    reference_paiement: str = ""  # référence de paiement
    relance: int = 0  # nombre de relances
    date_derniere_relance: Optional[str] = None


class Justificatif(BaseModel):
    """Justificatif de frais (pièce jointe)."""
    id: str = Field(default_factory=lambda: new_id("just_"))
    frais_id: str = ""
    nom_fichier: str = ""
    chemin_fichier: str = ""
    type_mime: str = ""
    taille_octets: int = 0
    date_upload: float = Field(default_factory=time.time)
    uploaded_by: str = ""
    hash_sha256: str = ""


class Facture(BaseModel):
    """Facture émise au client ou reçue du fournisseur."""
    id: str = Field(default_factory=lambda: new_id("fac_"))
    dossier_id: str = ""
    type_facture: str = ""  # emisee au client, recue fournisseur
    numero_facture: str = ""
    date_facture: Optional[str] = None
    date_echeance: Optional[str] = None
    montant_ht: float = 0.0
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    devise: str = "EUR"
    taux_change: float = 1.0  # taux de change vers EUR
    statut_paiement: str = "en_attente"  # en_attente, envoyee, payee, annulee, en_retard, remboursee
    client_id: str = ""
    fournisseur_id: str = ""
    documents_joint: list[str] = Field(default_factory=list)
    justificatifs: list[str] = Field(default_factory=list)  # IDs des justificatifs
    notes: str = ""
    date_envoi: Optional[str] = None
    date_paiement: Optional[str] = None
    date_relance: Optional[str] = None
    nb_relances: int = 0
    reference_paiement: str = ""
    mode_paiement: str = ""  # virement, cheque, especes, carte, traites


# ─────────────────────────────────────────────────────────────
# Module 11 : Enlèvement terminal
# ─────────────────────────────────────────────────────────────

class TerminalEnlevement(BaseModel):
    """Demande d'enlèvement au terminal portuaire."""
    id: str = Field(default_factory=lambda: new_id("term_"))
    dossier_id: str = ""
    numero_bl: str = ""
    numero_conteneur: str = ""
    date_demande: Optional[str] = None
    date_planifiee: Optional[str] = None
    statut: str = "demande"  # demande, planifie, transporteur_affecte, en_attente_mainlevee, en_attente_bad, sortie_autorisee, sortis
    transporteur_id: str = ""
    camion_id: str = ""
    chauffeur_id: str = ""
    immatriculation: str = ""
    chauffeur_nom: str = ""
    chauffeur_permis: str = ""
    mainlevee_obtenue: bool = False
    bad_obtenu: bool = False
    frais_portuaires_payes: bool = False
    date_sortie: Optional[str] = None
    justificatif_sortie: str = ""
    observations: str = ""


# ─────────────────────────────────────────────────────────────
# Module 12 : Transport et livraison
# ─────────────────────────────────────────────────────────────

class Transporteur(BaseModel):
    """Transporteur routier."""
    id: str = Field(default_factory=lambda: new_id("transp_"))
    nom: str = ""
    raison_sociale: str = ""
    nif: str = ""
    rc: str = ""
    adresse: str = ""
    telephone: str = ""
    email: str = ""
    conducteur_principal: str = ""
    permis_transport: str = ""
    statut: str = "actif"  # actif, inactif
    notes: str = ""


class Camion(BaseModel):
    """Camion affecté à un transport."""
    id: str = Field(default_factory=lambda: new_id("cam_"))
    transporteur_id: str = ""
    immatriculation: str = ""
    marque_modele: str = ""
    capacite: str = ""
    annee: int = 0
    assurance_valide: bool = True
    technique_valide: bool = True
    statut: str = "disponible"  # disponible, affecte, en_maintenance
    chauffeur_id: str = ""


class Livraison(BaseModel):
    """Suivi de livraison."""
    id: str = Field(default_factory=lambda: new_id("liv_"))
    dossier_id: str = ""
    transport_id: str = ""
    client_id: str = ""
    transporteur_id: str = ""
    camion_id: str = ""
    chauffeur_id: str = ""
    lieu_livraison: str = ""
    date_depart: Optional[str] = None
    date_prevue: Optional[str] = None
    date_reelle: Optional[str] = None
    statut: str = "planifie"  # planifie, affecte, enleve, en_route, arrive, reponse, confirme
    reserves_eventuelles: str = ""
    preuve_livraison_signee: bool = False
    date_signature: Optional[str] = None
    observations: str = ""


# ─────────────────────────────────────────────────────────────
# Module 20 : Utilisateurs, rôles et permissions
# ─────────────────────────────────────────────────────────────

class Role(BaseModel):
    """Rôle dans le système UniOCR Transit."""
    id: str = Field(default_factory=lambda: new_id("role_"))
    nom: str = ""  # administrateur, directeur, responsable_transit, agent_transit, responsable_documentaire, declarant_en_douane, responsable_financier, responsable_logistique, responsable_transport, auditeur
    description: str = ""
    niveau_acces: int = 1
    permissions: list[str] = Field(default_factory=list)


class Permission(BaseModel):
    """Permission granulaire pour chaque rôle."""
    id: str = Field(default_factory=lambda: new_id("perm_"))
    nom: str = ""
    ressource: str = ""  # dossier, document, client, etc.
    action: str = ""  # read, write, delete, validate, etc.
    description: str = ""


class Workflow(BaseModel):
    """Workflow configurable pour les étapes du dossier."""
    id: str = Field(default_factory=lambda: new_id("wf_"))
    nom: str = ""
    description: str = ""
    etapes: list[dict[str, Any]] = Field(default_factory=list)
    conditions_entree: dict[str, Any] = Field(default_factory=dict)
    conditions_validation: dict[str, Any] = Field(default_factory=dict)
    actions_automatiques: list[dict[str, Any]] = Field(default_factory=list)
    actif: bool = True


class Notification(BaseModel):
    """Notification interne ou email."""
    id: str = Field(default_factory=lambda: new_id("notif_"))
    dossier_id: str = ""
    type_notification: str = ""  # alerte_document_manquant, alerte_incoherence, alerte_retard, alerte_eta, alerte_franchise, notification_bad, notification_mainlevee, notification_sortie, notification_livraison
    destinataire: str = ""
    message: str = ""
    statut: str = "envoyee"  # envoyee, lue, ignoree
    date_creation: str = Field(default_factory=time.strftime("%Y-%m-%d %H:%M:%S"))
    methode: str = "interne"  # interne, email


class JournalAudit(BaseModel):
    """Journal d'audit pour traçabilité complète."""
    id: str = Field(default_factory=lambda: new_id("audit_"))
    action: str = ""  # create, read, update, delete, validate, export, etc.
    ressource_type: str = ""
    ressource_id: str = ""
    utilisateur: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    date_creation: str = Field(default_factory=time.strftime("%Y-%m-%d %H:%M:%S"))
    ip_address: str = ""
    user_agent: str = ""
