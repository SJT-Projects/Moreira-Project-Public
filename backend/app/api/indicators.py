from fastapi import APIRouter, HTTPException

from app.core.auth import AuthenticatedUser
from app.detection.extractor import normalize_indicator
from app.repositories.firestore_repository import FirestoreRepository, RepositoryUnavailable
from app.schemas.analysis import IndicatorInput
from app.schemas.reports import IndicatorLookup

router = APIRouter(prefix="/v1/indicadores", tags=["Indicadores"])
_repository = FirestoreRepository()


@router.post("/consultar", summary="Consulta antecedentes de indicadores comunitarios")
async def lookup_indicators(request: IndicatorLookup, _user: AuthenticatedUser) -> dict:
    normalized: dict[tuple[str, str], IndicatorInput] = {}
    for item in request.indicadores:
        value = normalize_indicator(item.type, item.value)
        if not value:
            raise HTTPException(422, f"No se pudo validar el indicador de tipo {item.type.value}.")
        normalized.setdefault((item.type.value, value), IndicatorInput(type=item.type, value=value))
    try:
        findings = await _repository.lookup_many(list(normalized.values()))
        return {"indicadores": [finding.model_dump(mode="json") for finding in findings]}
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
