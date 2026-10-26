from fastapi import APIRouter, HTTPException

from app.core.auth import AuthenticatedUser
from app.repositories.firestore_repository import FirestoreRepository, RepositoryUnavailable
from app.schemas.academy import QuizAttemptCreate
from app.services.academy_service import AcademyService

router = APIRouter(prefix="/v1/academia", tags=["Educación"])
_repository = FirestoreRepository()
_service = AcademyService(_repository)


@router.get("/cuestionarios/{quiz_id}", summary="Obtiene las preguntas sin revelar respuestas")
async def get_quiz(quiz_id: str) -> dict:
    try:
        return _service.get_quiz(quiz_id)
    except KeyError as exc:
        raise HTTPException(404, "No se encontró el cuestionario.") from exc


@router.post("/cuestionarios/{quiz_id}/intentos", summary="Califica y guarda un intento")
async def submit_attempt(quiz_id: str, request: QuizAttemptCreate, user: AuthenticatedUser) -> dict:
    try:
        return await _service.submit_attempt(user["uid"], quiz_id, request)
    except KeyError as exc:
        raise HTTPException(404, "No se encontró el cuestionario.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/progreso", summary="Consulta el progreso educativo propio")
async def get_progress(user: AuthenticatedUser) -> dict:
    try:
        return await _repository.get_quiz_progress(user["uid"])
    except RepositoryUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
