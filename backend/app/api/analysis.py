from fastapi import APIRouter

from app.core.auth import AuthenticatedUser
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/v1/analisis", tags=["Análisis"])
_service = AnalysisService()


@router.post("", response_model=AnalysisResponse, summary="Analiza un mensaje, correo, teléfono o enlace")
async def analyze_message(request: AnalysisRequest, _user: AuthenticatedUser) -> AnalysisResponse:
    return await _service.analyze(request)
