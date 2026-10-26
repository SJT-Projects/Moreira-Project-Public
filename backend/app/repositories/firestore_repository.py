from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud.firestore_v1.field_path import FieldPath
from google.api_core.exceptions import FailedPrecondition

from app.core.config import get_settings
from app.core.firebase import firebase_status, get_firestore_client
from app.detection.extractor import normalize_indicator
from app.schemas.analysis import (
    EvidenceStatus,
    IndicatorFinding,
    IndicatorInput,
    IndicatorType,
)

_INDICATOR_COLLECTION = "indicadores"
_REPORT_COLLECTION = "reportes"
_PRIVATE_REPORT_COLLECTION = "reportes_privados"
_DAILY_REPORT_LIMIT = 5


class RepositoryUnavailable(Exception):
    pass


class InvalidPageToken(Exception):
    pass


class FirestoreRepository:
    def status(self) -> tuple[bool, str]:
        return firebase_status()

    def _client(self) -> Any:
        try:
            return get_firestore_client()
        except Exception as exc:
            raise RepositoryUnavailable(
                "Firestore no está configurado. Seguí los pasos de configuración del README."
            ) from exc

    async def save_quiz_attempt(
        self, *, uid: str, quiz_id: str, score: int,
        correct_answers: int, total_questions: int, feedback: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._save_quiz_attempt_sync, uid, quiz_id, score,
            correct_answers, total_questions, feedback,
        )

    def _save_quiz_attempt_sync(
        self, uid: str, quiz_id: str, score: int,
        correct_answers: int, total_questions: int, feedback: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from google.cloud.firestore_v1 import transactional

        db = self._client()
        now = datetime.now(timezone.utc)
        attempt_ref = db.collection("intentos_educativos").document()
        progress_ref = db.collection("progreso_educativo").document(uid)
        transaction = db.transaction(max_attempts=5)

        @transactional
        def save(tx: Any) -> dict[str, Any]:
            progress_snapshot = progress_ref.get(transaction=tx)
            progress = progress_snapshot.to_dict() if progress_snapshot.exists else {}
            current = progress.get(quiz_id, {})
            completed = int(current.get("intentos", 0)) + 1
            best = max(int(current.get("mejor_puntaje", 0)), score)
            result = {
                "quiz_id": quiz_id,
                "score": score,
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "completed_at": now.isoformat(),
                "feedback": feedback,
            }
            tx.set(attempt_ref, {
                "usuario_uid": uid,
                "cuestionario_id": quiz_id,
                "puntaje": score,
                "respuestas_correctas": correct_answers,
                "total_preguntas": total_questions,
                "creado_en": now,
            })
            tx.set(progress_ref, {
                quiz_id: {
                    "intentos": completed,
                    "mejor_puntaje": best,
                    "ultimo_puntaje": score,
                    "actualizado_en": now,
                }
            }, merge=True)
            return result

        try:
            return save(transaction)
        except Exception as exc:
            raise RepositoryUnavailable("No se pudo guardar el progreso en Firestore.") from exc

    async def get_quiz_progress(self, uid: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_quiz_progress_sync, uid)

    def _get_quiz_progress_sync(self, uid: str) -> dict[str, Any]:
        try:
            snapshot = self._client().collection("progreso_educativo").document(uid).get()
            progress = snapshot.to_dict() if snapshot.exists else {}
            data = progress.get("anti-estafas", {})
            updated = data.get("actualizado_en")
            return {
                "completed_attempts": int(data.get("intentos", 0)),
                "best_score": int(data.get("mejor_puntaje", 0)),
                "last_score": data.get("ultimo_puntaje"),
                "last_completed_at": updated.isoformat() if hasattr(updated, "isoformat") else None,
            }
        except Exception as exc:
            raise RepositoryUnavailable("No se pudo consultar el progreso en Firestore.") from exc

    @staticmethod
    def _indicator_id(item: IndicatorInput) -> str:
        settings = get_settings()
        if not settings.indicator_hmac_secret:
            raise RepositoryUnavailable("INDICATOR_HMAC_SECRET no está configurado.")
        payload = f"v1\0{item.type.value}\0{item.value}".encode("utf-8")
        return hmac.new(
            settings.indicator_hmac_secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

    async def lookup_many(self, indicators: list[IndicatorInput]) -> list[IndicatorFinding]:
        if not indicators:
            return []
        return await asyncio.to_thread(self._lookup_many_sync, indicators)

    def _lookup_many_sync(self, indicators: list[IndicatorInput]) -> list[IndicatorFinding]:
        db = self._client()
        unique: dict[str, IndicatorInput] = {}
        for item in indicators:
            unique.setdefault(self._indicator_id(item), item)
        references = {key: db.collection(_INDICATOR_COLLECTION).document(key) for key in unique}
        try:
            documents = {
                snapshot.id: snapshot
                for snapshot in db.get_all(list(references.values()))
            }
        except Exception as exc:
            raise RepositoryUnavailable("No se pudieron consultar antecedentes en Firestore.") from exc

        results: list[IndicatorFinding] = []
        for document_id, item in unique.items():
            snapshot = documents.get(document_id)
            data = snapshot.to_dict() if snapshot and snapshot.exists else {}
            state = data.get("estado_evidencia", "sin_antecedentes")
            try:
                state = EvidenceStatus(state) if state != "sin_antecedentes" else state
            except ValueError:
                state = EvidenceStatus.UNVERIFIED
            results.append(
                IndicatorFinding(
                    tipo=item.type,
                    valor=self._mask_indicator(item.type, item.value),
                    estado=state,
                    reportes_aprobados=max(0, int(data.get("reportes_aprobados", 0))),
                )
            )
        return results

    async def create_report(
        self,
        *,
        uid: str,
        autor: str,
        titulo: str,
        descripcion: str,
        categoria: str,
        indicators: list[IndicatorInput],
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._create_report_sync,
            uid,
            autor,
            titulo,
            descripcion,
            categoria,
            indicators,
        )

    def _create_report_sync(
        self,
        uid: str,
        autor: str,
        titulo: str,
        descripcion: str,
        categoria: str,
        indicators: list[IndicatorInput],
    ) -> dict[str, Any]:
        from app.detection.extractor import mask_for_publication

        db = self._client()
        report_ref = db.collection(_REPORT_COLLECTION).document()
        private_ref = db.collection(_PRIVATE_REPORT_COLLECTION).document(report_ref.id)
        report_day = date.today().isoformat()
        day_ref = db.collection("cuotas_reportes").document(f"{uid}_{report_day}")

        indicator_references: dict[str, tuple[Any, IndicatorInput]] = {}
        for item in indicators:
            key = self._indicator_id(item)
            indicator_references.setdefault(
                key,
                (db.collection(_INDICATOR_COLLECTION).document(key), item),
            )

        public_report = {
            "autor_uid": uid,
            "autor_publico": (autor.strip()[:60] or "Usuario"),
            "titulo": mask_for_publication(titulo)[:120],
            "descripcion": mask_for_publication(descripcion)[:2_000],
            "categoria": categoria,
            "estado_moderacion": "pendiente",
            "indicadores_ids": list(indicator_references),
            "creado_en": datetime.now(timezone.utc),
        }
        private_report = {
            "autor_uid": uid,
            "texto_original": f"{titulo}\n{descripcion}",
            "indicadores": [
                {"tipo": item.type.value, "valor": item.value}
                for item in indicators
            ],
            "creado_en": datetime.now(timezone.utc),
        }

        from google.cloud.firestore_v1 import transactional

        transaction = db.transaction(max_attempts=5)

        @transactional
        def write_report(tx: Any) -> None:
            quota_snapshot = next(iter(tx.get(day_ref)), None)
            quota = quota_snapshot.to_dict() if quota_snapshot and quota_snapshot.exists else {}
            if int(quota.get("cantidad", 0)) >= _DAILY_REPORT_LIMIT:
                raise ReportLimitReached
            indicator_snapshots = {
                key: next(iter(tx.get(reference)), None)
                for key, (reference, _item) in indicator_references.items()
            }
            tx.set(report_ref, public_report)
            tx.set(private_ref, private_report)
            tx.set(
                day_ref,
                {
                    "autor_uid": uid,
                    "fecha": report_day,
                    "cantidad": int(quota.get("cantidad", 0)) + 1,
                    "actualizado_en": datetime.now(timezone.utc),
                },
            )
            for key, (reference, item) in indicator_references.items():
                snapshot = indicator_snapshots[key]
                if not snapshot or not snapshot.exists:
                    tx.set(
                        reference,
                        {
                            "tipo": item.type.value,
                            "valor_mostrado": self._mask_indicator(item.type, item.value),
                            "estado_evidencia": EvidenceStatus.UNVERIFIED.value,
                            "reportes_aprobados": 0,
                            "creado_en": datetime.now(timezone.utc),
                        },
                    )

        try:
            write_report(transaction)
        except ReportLimitReached:
            raise
        except Exception as exc:
            raise RepositoryUnavailable("No se pudo guardar el reporte en Firestore.") from exc

        return self._serialize_report(report_ref.id, public_report)

    async def list_reports(self, page_size: int, page_token: str | None) -> dict[str, Any]:
        return await asyncio.to_thread(self._list_reports_sync, page_size, page_token)

    def _list_reports_sync(self, page_size: int, page_token: str | None) -> dict[str, Any]:
        db = self._client()
        collection = db.collection(_REPORT_COLLECTION)
        query = (
            collection.where("estado_moderacion", "==", "aprobado")
            .order_by("creado_en", direction="DESCENDING")
            .order_by(FieldPath.document_id(), direction="DESCENDING")
        )
        if page_token:
            try:
                cursor_time, cursor_id = self._decode_page_token(page_token)
                cursor_ref = collection.document(cursor_id)
                query = query.start_after([cursor_time, cursor_ref])
            except (InvalidPageToken, ValueError, TypeError):
                raise InvalidPageToken("El cursor de paginación no es válido.") from None

        try:
            snapshots = list(query.limit(page_size + 1).stream())
        except FailedPrecondition:
            # Mientras Firestore construye el índice compuesto, mantenemos la
            # comunidad disponible con una lectura acotada al estado y orden local.
            try:
                snapshots = list(
                    collection.where("estado_moderacion", "==", "aprobado").stream()
                )
                snapshots.sort(
                    key=lambda item: (item.get("creado_en") or datetime.min.replace(tzinfo=timezone.utc), item.id),
                    reverse=True,
                )
                if page_token:
                    cursor_time, cursor_id = self._decode_page_token(page_token)
                    snapshots = [
                        item for item in snapshots
                        if (item.get("creado_en") or datetime.min.replace(tzinfo=timezone.utc), item.id)
                        < (cursor_time, cursor_id)
                    ]
                snapshots = snapshots[: page_size + 1]
            except Exception as exc:
                raise RepositoryUnavailable("No se pudieron cargar los reportes publicados.") from exc
        except Exception as exc:
            raise RepositoryUnavailable("No se pudieron cargar los reportes publicados.") from exc

        page = snapshots[:page_size]
        token = None
        if len(snapshots) > page_size and page:
            last = page[-1]
            token = self._encode_page_token(last.get("creado_en"), last.id)
        return {
            "items": [self._serialize_report(snapshot.id, snapshot.to_dict() or {}) for snapshot in page],
            "siguiente_cursor": token,
        }

    async def list_own_reports(self, uid: str, page_size: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_own_reports_sync, uid, page_size)

    def _list_own_reports_sync(self, uid: str, page_size: int) -> list[dict[str, Any]]:
        db = self._client()
        try:
            documents = (
                db.collection(_REPORT_COLLECTION)
                .where("autor_uid", "==", uid)
                .order_by("creado_en", direction="DESCENDING")
                .limit(page_size)
                .stream()
            )
            return [self._serialize_report(item.id, item.to_dict() or {}) for item in documents]
        except Exception as exc:
            raise RepositoryUnavailable("No se pudieron cargar tus reportes.") from exc

    async def list_pending_reports(self, page_size: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._list_pending_reports_sync, page_size)

    def _list_pending_reports_sync(self, page_size: int) -> list[dict[str, Any]]:
        db = self._client()
        try:
            documents = (
                db.collection(_REPORT_COLLECTION)
                .where("estado_moderacion", "==", "pendiente")
                .order_by("creado_en", direction="DESCENDING")
                .limit(page_size)
                .stream()
            )
            return [self._serialize_report(item.id, item.to_dict() or {}) for item in documents]
        except Exception as exc:
            raise RepositoryUnavailable("No se pudieron cargar los reportes pendientes.") from exc

    async def get_report_for_review(self, report_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_report_for_review_sync, report_id)

    def _get_report_for_review_sync(self, report_id: str) -> dict[str, Any] | None:
        db = self._client()
        try:
            public = db.collection(_REPORT_COLLECTION).document(report_id).get()
            private = db.collection(_PRIVATE_REPORT_COLLECTION).document(report_id).get()
            if not public.exists or not private.exists:
                return None
            return {
                "reporte": self._serialize_report(report_id, public.to_dict() or {}),
                "evidencia_privada": private.to_dict() or {},
            }
        except Exception as exc:
            raise RepositoryUnavailable("No se pudo cargar el reporte para revisión.") from exc

    async def moderate_report(self, report_id: str, admin_uid: str, action: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._moderate_report_sync, report_id, admin_uid, action)

    def _moderate_report_sync(self, report_id: str, admin_uid: str, action: str) -> dict[str, Any]:
        db = self._client()
        report_ref = db.collection(_REPORT_COLLECTION).document(report_id)
        audit_ref = db.collection("moderaciones").document(str(uuid4()))
        from google.cloud.firestore_v1 import transactional

        transaction = db.transaction(max_attempts=5)

        @transactional
        def moderate(tx: Any) -> dict[str, Any]:
            report_snapshot = report_ref.get(transaction=tx)
            if not report_snapshot.exists:
                raise ReportNotFound
            report = report_snapshot.to_dict() or {}
            if report.get("estado_moderacion") != "pendiente":
                raise ReportAlreadyModerated
            approved = action == "aprobado"
            indicator_references = [
                db.collection(_INDICATOR_COLLECTION).document(key)
                for key in report.get("indicadores_ids", [])
            ]
            indicator_snapshots = [ref.get(transaction=tx) for ref in indicator_references]
            tx.update(
                report_ref,
                {
                    "estado_moderacion": action,
                    "moderado_por": admin_uid,
                    "moderado_en": datetime.now(timezone.utc),
                },
            )
            if approved:
                for reference, snapshot in zip(indicator_references, indicator_snapshots, strict=True):
                    if snapshot.exists:
                        current = snapshot.to_dict() or {}
                        tx.update(
                            reference,
                            {
                                "reportes_aprobados": int(current.get("reportes_aprobados", 0)) + 1,
                                "actualizado_en": datetime.now(timezone.utc),
                            },
                        )
            tx.set(
                audit_ref,
                {
                    "reporte_id": report_id,
                    "administrador_uid": admin_uid,
                    "accion": action,
                    "creado_en": datetime.now(timezone.utc),
                },
            )
            report.update({"estado_moderacion": action, "moderado_por": admin_uid})
            report["moderado_en"] = datetime.now(timezone.utc)
            return self._serialize_report(report_id, report)

        try:
            return moderate(transaction)
        except (ReportNotFound, ReportAlreadyModerated):
            raise
        except Exception as exc:
            raise RepositoryUnavailable("No se pudo completar la moderación.") from exc

    async def set_indicator_evidence(
        self, item: IndicatorInput, admin_uid: str, action: EvidenceStatus
    ) -> dict[str, str]:
        return await asyncio.to_thread(self._set_indicator_evidence_sync, item, admin_uid, action)

    def _set_indicator_evidence_sync(
        self, item: IndicatorInput, admin_uid: str, action: EvidenceStatus
    ) -> dict[str, str]:
        db = self._client()
        reference = db.collection(_INDICATOR_COLLECTION).document(self._indicator_id(item))
        current = reference.get()
        if not current.exists:
            raise IndicatorNotFound
        reference.update(
            {
                "estado_evidencia": action.value,
                "revisado_por": admin_uid,
                "revisado_en": datetime.now(timezone.utc),
            }
        )
        return {"tipo": item.type.value, "estado": action.value}

    @classmethod
    def _encode_page_token(cls, timestamp: Any, document_id: str) -> str:
        if isinstance(timestamp, datetime):
            iso_timestamp = timestamp.isoformat()
        else:
            iso_timestamp = str(timestamp)
        payload = json.dumps({"ts": iso_timestamp, "id": document_id}, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")

    @classmethod
    def _decode_page_token(cls, token: str) -> tuple[datetime, str]:
        try:
            raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
            payload = json.loads(raw)
            timestamp = datetime.fromisoformat(payload["ts"])
            document_id = payload["id"]
            if not isinstance(document_id, str) or not document_id or "/" in document_id:
                raise ValueError("invalid document id")
            return timestamp, document_id
        except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidPageToken from exc

    @staticmethod
    def _mask_indicator(kind: IndicatorType, value: str) -> str:
        if kind == IndicatorType.EMAIL:
            local, domain = value.rsplit("@", 1)
            return f"{local[:1]}•••@{domain}"
        if kind == IndicatorType.PHONE:
            return f"•••{value[-4:]}"
        if kind == IndicatorType.URL:
            try:
                from urllib.parse import urlsplit

                parsed = urlsplit(value)
                return f"{parsed.scheme}://{parsed.hostname}/…"
            except ValueError:
                return "Enlace reportado"
        return value

    @staticmethod
    def _serialize_report(report_id: str, data: dict[str, Any]) -> dict[str, Any]:
        created_at = data.get("creado_en")
        moderated_at = data.get("moderado_en")
        return {
            "id": report_id,
            "autor": data.get("autor_publico", "Usuario"),
            "titulo": data.get("titulo", "Alerta comunitaria"),
            "descripcion": data.get("descripcion", ""),
            "categoria": data.get("categoria", "otros"),
            "estado_moderacion": data.get("estado_moderacion", "pendiente"),
            "creado_en": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
            "moderado_en": moderated_at.isoformat() if hasattr(moderated_at, "isoformat") else None,
        }


class ReportLimitReached(Exception):
    pass


class ReportNotFound(Exception):
    pass


class ReportAlreadyModerated(Exception):
    pass


class IndicatorNotFound(Exception):
    pass
