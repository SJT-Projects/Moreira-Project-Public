from app.detection.extractor import extract_indicators, normalize_indicator
from app.repositories.firestore_repository import FirestoreRepository
from app.schemas.analysis import IndicatorInput
from app.schemas.reports import ReportCreate


class ReportService:
    def __init__(self, repository: FirestoreRepository | None = None) -> None:
        self.repository = repository or FirestoreRepository()

    async def create(self, request: ReportCreate, user: dict) -> dict:
        text_indicators = extract_indicators(f"{request.titulo}\n{request.descripcion}")
        submitted_indicators: dict[tuple[str, str], IndicatorInput] = {}
        for item in [*text_indicators, *request.indicadores]:
            normalized = normalize_indicator(item.type, item.value)
            if normalized:
                submitted_indicators.setdefault(
                    (item.type.value, normalized),
                    IndicatorInput(type=item.type, value=normalized),
                )

        display_name = str(user.get("name", "Vecino"))[:60]
        return await self.repository.create_report(
            uid=user["uid"],
            autor=display_name,
            titulo=request.titulo,
            descripcion=request.descripcion,
            categoria=request.categoria,
            indicators=list(submitted_indicators.values()),
        )
