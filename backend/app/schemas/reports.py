from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings
from app.schemas.analysis import EvidenceStatus, IndicatorInput


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=5, max_length=120)
    descripcion: str = Field(min_length=20, max_length=4_000)
    categoria: Literal["whatsapp", "sms", "correo", "llamada", "sitio_web", "compra", "otro"] = "otro"
    indicadores: list[IndicatorInput] = Field(default_factory=list, max_length=20)

    @field_validator("titulo", "descripcion")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El texto no puede estar vacío.")
        maximum = get_settings().max_report_chars
        if len(normalized) > maximum:
            raise ValueError(f"El máximo permitido es de {maximum} caracteres.")
        return normalized


class ReportModeration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accion: Literal["aprobado", "rechazado"]


class IndicatorEvidenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicador: IndicatorInput
    estado: Literal[EvidenceStatus.CONFIRMED, EvidenceStatus.DISMISSED]


class IndicatorLookup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicadores: list[IndicatorInput] = Field(min_length=1, max_length=20)


class ReportPage(BaseModel):
    items: list[dict]
    siguiente_cursor: str | None = None
