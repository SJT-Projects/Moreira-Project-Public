from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings


class RiskLevel(StrEnum):
    HIGH = "alto"
    MEDIUM = "medio"
    LOW = "bajo"
    UNKNOWN = "indeterminado"


class AnalysisState(StrEnum):
    COMPLETE = "completo"
    PARTIAL = "parcial"
    UNAVAILABLE = "no_disponible"


class CheckStatus(StrEnum):
    OK = "realizada"
    FAILED = "fallida"
    NOT_APPLICABLE = "no_aplica"


class IndicatorType(StrEnum):
    PHONE = "telefono"
    EMAIL = "correo"
    URL = "url"
    DOMAIN = "dominio"


class EvidenceStatus(StrEnum):
    UNVERIFIED = "no_verificado"
    UNDER_REVIEW = "en_revision"
    CONFIRMED = "confirmado"
    DISMISSED = "descartado"


class IndicatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: IndicatorType
    value: str = Field(min_length=1, max_length=2_048)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1, max_length=10_000)

    @field_validator("texto")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Ingresá un mensaje, correo, número o enlace para analizar.")
        maximum = get_settings().max_analysis_chars
        if len(value) > maximum:
            raise ValueError(f"El máximo permitido es de {maximum} caracteres.")
        return value


class Evidence(BaseModel):
    fuente: str
    codigo: str
    descripcion: str


class IndicatorFinding(BaseModel):
    tipo: IndicatorType
    valor: str
    estado: EvidenceStatus | str
    reportes_aprobados: int = Field(ge=0)


class CheckResult(BaseModel):
    estado: CheckStatus
    detalle: str


class AnalysisResponse(BaseModel):
    riesgo: RiskLevel
    estado: AnalysisState
    resumen: str
    motivos: list[Evidence]
    consejo: str
    indicadores: list[IndicatorFinding]
    comprobaciones: dict[str, CheckResult]
    version_motor: str = "1"
