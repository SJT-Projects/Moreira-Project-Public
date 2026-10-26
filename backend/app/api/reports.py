from fastapi import APIRouter, HTTPException, Query

from app.core.auth import AdminUser, AuthenticatedUser
from app.repositories.firestore_repository import (
    FirestoreRepository,
    InvalidPageToken,
    ReportAlreadyModerated,
    ReportLimitReached,
    ReportNotFound,
    RepositoryUnavailable,
)
from app.schemas.analysis import EvidenceStatus
from app.schemas.reports import IndicatorEvidenceUpdate, ReportCreate, ReportModeration
from app.services.report_service import ReportService

router = APIRouter(prefix="/v1/reportes", tags=["Comunidad"])
admin_router = APIRouter(prefix="/v1/admin", tags=["Moderación"])
_repository = FirestoreRepository()
_service = ReportService(_repository)


@router.get("", summary="Lista alertas comunitarias aprobadas")
async def list_reports(
    page_size: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None, max_length=1_024),
) -> dict:
    try:
        return await _repository.list_reports(page_size, cursor)
    except InvalidPageToken as exc:
        raise HTTPException(400, str(exc)) from exc
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/mios", summary="Lista mis reportes comunitarios")
async def list_my_reports(
    user: AuthenticatedUser,
    page_size: int = Query(default=20, ge=1, le=50),
) -> dict:
    try:
        return {"items": await _repository.list_own_reports(user["uid"], page_size)}
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("", status_code=201, summary="Crea un reporte pendiente de moderación")
async def create_report(request: ReportCreate, user: AuthenticatedUser) -> dict:
    try:
        return await _service.create(request, user)
    except ReportLimitReached as exc:
        raise HTTPException(429, "Alcanzaste el límite de cinco reportes por día.") from exc
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@admin_router.get("/reportes-pendientes", summary="Lista los reportes que esperan moderación")
async def list_pending_reports(
    _admin: AdminUser,
    page_size: int = Query(default=30, ge=1, le=50),
) -> dict:
    try:
        return {"items": await _repository.list_pending_reports(page_size)}
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@admin_router.get("/reportes/{report_id}", summary="Carga un reporte privado para revisión administrativa")
async def get_report_for_review(report_id: str, _admin: AdminUser) -> dict:
    if len(report_id) > 128 or "/" in report_id:
        raise HTTPException(422, "Identificador de reporte no válido.")
    try:
        record = await _repository.get_report_for_review(report_id)
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if record is None:
        raise HTTPException(404, "No se encontró el reporte.")
    return record


@admin_router.patch("/reportes/{report_id}/moderacion", summary="Aprueba o rechaza un reporte pendiente")
async def moderate_report(report_id: str, request: ReportModeration, admin: AdminUser) -> dict:
    if len(report_id) > 128 or "/" in report_id:
        raise HTTPException(422, "Identificador de reporte no válido.")
    try:
        return await _repository.moderate_report(report_id, admin["uid"], request.accion)
    except ReportNotFound as exc:
        raise HTTPException(404, "No se encontró el reporte.") from exc
    except ReportAlreadyModerated as exc:
        raise HTTPException(409, "El reporte ya fue moderado.") from exc
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@admin_router.patch("/indicadores/evidencia", summary="Registra la revisión de un indicador")
async def set_indicator_evidence(request: IndicatorEvidenceUpdate, admin: AdminUser) -> dict:
    try:
        result = await _repository.set_indicator_evidence(
            request.indicador,
            admin["uid"],
            EvidenceStatus(request.estado),
        )
        return result
    except ValueError as exc:
        raise HTTPException(422, "El estado de evidencia no es válido.") from exc
    except Exception as exc:
        from app.repositories.firestore_repository import IndicatorNotFound

        if isinstance(exc, IndicatorNotFound):
            raise HTTPException(404, "El indicador no tiene reportes previos.") from exc
        if isinstance(exc, RepositoryUnavailable):
            raise HTTPException(503, str(exc)) from exc
        raise
