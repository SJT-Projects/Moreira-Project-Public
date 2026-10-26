import asyncio

from app.core.firebase import firebase_status
from app.detection.decision import build_advice, decide_risk
from app.detection.extractor import extract_indicators, mask_for_model, normalize_indicator
from app.detection.groq_client import ContextAssessment, GroqClient, GroqUnavailable
from app.detection.reputation_client import ReputationClient, ReputationUnavailable, UrlCheck
from app.detection.rules import analyze_rules
from app.detection.url_analyzer import UrlAnalyzer, UrlInspection
from app.detection.virustotal_client import (
    VirusTotalClient,
    VirusTotalNotConfigured,
    VirusTotalUnavailable,
    VirusTotalUrlCheck,
)
from app.repositories.firestore_repository import FirestoreRepository, RepositoryUnavailable
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisState,
    CheckResult,
    CheckStatus,
    Evidence,
    IndicatorType,
    RiskLevel,
)


class AnalysisService:
    def __init__(
        self,
        *,
        repository: FirestoreRepository | None = None,
        groq_client: GroqClient | None = None,
        reputation_client: ReputationClient | None = None,
        url_analyzer: UrlAnalyzer | None = None,
        virustotal_client: VirusTotalClient | None = None,
    ) -> None:
        self.repository = repository or FirestoreRepository()
        self.groq_client = groq_client or GroqClient()
        self.reputation_client = reputation_client or ReputationClient()
        self.url_analyzer = url_analyzer or UrlAnalyzer()
        self.virustotal_client = virustotal_client or VirusTotalClient()

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        text = request.texto
        indicators = extract_indicators(text)
        evidence, matched_categories = analyze_rules(text)
        categories = set(matched_categories)
        ai_signals = set(matched_categories)
        checks: dict[str, CheckResult] = {}
        gathered: list[Evidence] = []
        findings = []
        context: ContextAssessment | None = None
        url_results: dict[str, UrlCheck] = {}
        url_inspections: dict[str, UrlInspection] = {}
        virustotal_results: dict[str, VirusTotalUrlCheck] = {}

        cloud_configured, cloud_detail = await asyncio.to_thread(firebase_status)
        if cloud_configured:
            try:
                findings = await self.repository.lookup_many(indicators)
                checks["firestore"] = CheckResult(estado=CheckStatus.OK, detalle="Antecedentes consultados.")
                for finding in findings:
                    if finding.estado == "confirmado":
                        gathered.append(Evidence(
                            fuente="firestore",
                            codigo="indicador_confirmado",
                            descripcion=f"El indicador {finding.valor} fue confirmado durante una revisión.",
                        ))
                    elif finding.estado == "en_revision" or finding.reportes_aprobados:
                        gathered.append(Evidence(
                            fuente="firestore",
                            codigo="indicador_reportado",
                            descripcion=f"El indicador {finding.valor} figura en {finding.reportes_aprobados} reporte(s) comunitario(s) aprobado(s); no está confirmado solo por ese dato.",
                        ))
            except RepositoryUnavailable as exc:
                checks["firestore"] = CheckResult(estado=CheckStatus.FAILED, detalle=str(exc))
        else:
            checks["firestore"] = CheckResult(estado=CheckStatus.FAILED, detalle=cloud_detail)

        urls = [item.value for item in indicators if item.type == IndicatorType.URL]
        explicit_hosts = {
            normalize_indicator(IndicatorType.DOMAIN, item.value)
            for item in indicators
            if item.type == IndicatorType.URL
        }
        urls.extend(
            f"https://{item.value}/"
            for item in indicators
            if item.type == IndicatorType.DOMAIN
            and item.value not in explicit_hosts
        )
        urls = list(dict.fromkeys(urls))
        if not urls:
            checks["reputacion_url"] = CheckResult(estado=CheckStatus.NOT_APPLICABLE, detalle="El mensaje no contiene enlaces.")
            checks["virustotal"] = CheckResult(
                estado=CheckStatus.NOT_APPLICABLE,
                detalle="El mensaje no contiene enlaces.",
            )
        else:
            url_inspections = await self.url_analyzer.inspect_many(urls)
            redirects = sum(item.redirect_count for item in url_inspections.values())
            for inspection in url_inspections.values():
                for tag in inspection.context_tags:
                    ai_signals.add(tag)
                for signal in inspection.signals:
                    if signal.category:
                        categories.add(signal.category)
                        ai_signals.add(signal.category)
                    gathered.append(Evidence(
                        fuente="url",
                        codigo=signal.code,
                        descripcion=signal.description,
                    ))

                if inspection.service:
                    purpose = (
                        " La ruta corresponde a un acceso y el dominio coincide exactamente con uno oficial conocido."
                        if "url_login_en_dominio_oficial" in inspection.context_tags
                        else ""
                    )
                    gathered.append(Evidence(
                        fuente="url",
                        codigo="url_dominio_oficial_conocido",
                        descripcion=f"Destino identificado: {inspection.service} ({inspection.final_host}).{purpose}",
                    ))
                elif inspection.redirect_count or inspection.final_host != inspection.original_host:
                    gathered.append(Evidence(
                        fuente="url",
                        codigo="url_destino_final",
                        descripcion=f"El destino final del enlace es {inspection.final_host}.",
                    ))
                if inspection.resolution_detail:
                    gathered.append(Evidence(
                        fuente="url",
                        codigo="url_destino_no_comprobado",
                        descripcion=inspection.resolution_detail,
                    ))

            inspected_urls = list(urls)
            inspected_urls.extend(
                inspection.final_url
                for inspection in url_inspections.values()
                if inspection.final_url not in inspected_urls
            )
            try:
                url_results = await self.reputation_client.lookup(inspected_urls)
                checks["reputacion_url"] = CheckResult(
                    estado=CheckStatus.OK,
                    detalle=(
                        f"Se verificaron {len(urls)} enlace(s), su dominio, destino final y reputación"
                        + (f"; se siguieron {redirects} redirección(es)." if redirects else ".")
                    ),
                )
                for url, result in url_results.items():
                    if result.estado == "coincidencia":
                        gathered.append(Evidence(
                            fuente="safe_browsing",
                            codigo="url_en_lista_de_amenazas",
                            descripcion=f"El enlace fue reportado como peligroso ({', '.join(result.threat_types) or 'amenaza web'}).",
                        ))
            except ReputationUnavailable as exc:
                checks["reputacion_url"] = CheckResult(estado=CheckStatus.FAILED, detalle=str(exc))

            try:
                virustotal_results = await self.virustotal_client.lookup(inspected_urls)
                checked = sum(
                    item.estado
                    in {"malicioso", "sospechoso", "sin_detecciones", "sin_informe"}
                    for item in virustotal_results.values()
                )
                limited = sum(
                    item.estado in {"limite_local", "limite_cuota", "omitido"}
                    for item in virustotal_results.values()
                )
                checks["virustotal"] = CheckResult(
                    estado=CheckStatus.OK if checked else CheckStatus.NOT_APPLICABLE,
                    detalle=(
                        f"VirusTotal consultó {checked} enlace(s) mediante reportes existentes."
                        + (
                            f" {limited} enlace(s) no se consultaron para cuidar la cuota gratuita."
                            if limited
                            else ""
                        )
                    ),
                )
                for result in virustotal_results.values():
                    if result.estado == "malicioso":
                        categories.add("url_reputacion_virustotal_maliciosa")
                        ai_signals.add("url_reputacion_virustotal_maliciosa")
                        gathered.append(Evidence(
                            fuente="virustotal",
                            codigo="url_detectada_virustotal",
                            descripcion=_virustotal_evidence(result, strong=True),
                        ))
                    elif result.estado == "sospechoso":
                        categories.add("url_reputacion_virustotal_sospechosa")
                        ai_signals.add("url_reputacion_virustotal_sospechosa")
                        gathered.append(Evidence(
                            fuente="virustotal",
                            codigo="url_sospechosa_virustotal",
                            descripcion=_virustotal_evidence(result, strong=False),
                        ))
            except VirusTotalNotConfigured as exc:
                checks["virustotal"] = CheckResult(
                    estado=CheckStatus.NOT_APPLICABLE,
                    detalle=str(exc),
                )
            except VirusTotalUnavailable as exc:
                checks["virustotal"] = CheckResult(
                    estado=CheckStatus.FAILED,
                    detalle=str(exc),
                )

        try:
            context = await self.groq_client.assess(
                mask_for_model(text),
                sorted(ai_signals),
            )
            checks["groq"] = CheckResult(estado=CheckStatus.OK, detalle="Análisis de contexto completo.")
            internal_codes = {item.casefold() for item in ai_signals}
            for index, reason in enumerate(context.indicios_contextuales[:6], start=1):
                reason = reason.strip()[:350]
                if reason and not _is_internal_signal(reason, internal_codes):
                    gathered.append(Evidence(
                        fuente="ia",
                        codigo=f"contexto_{index}",
                        descripcion=reason,
                    ))
        except GroqUnavailable as exc:
            checks["groq"] = CheckResult(estado=CheckStatus.FAILED, detalle=str(exc))

        all_evidence = evidence + gathered
        malicious_url_count = len(
            {
                url
                for url, result in url_results.items()
                if result.estado == "coincidencia"
            }
            | {
                url
                for url, result in virustotal_results.items()
                if result.estado == "malicioso"
            }
        )
        risk = decide_risk(
            categories=categories,
            evidence=all_evidence,
            indicators=findings,
            malicious_urls=malicious_url_count,
            ai_risk=context.riesgo_sugerido if context else None,
            ai_confidence=context.confianza if context else None,
        )
        required_check_failed = any(
            name != "virustotal" and check.estado == CheckStatus.FAILED
            for name, check in checks.items()
        )
        state = AnalysisState.PARTIAL if required_check_failed else AnalysisState.COMPLETE
        if required_check_failed and risk == RiskLevel.LOW:
            risk = RiskLevel.UNKNOWN
            state = AnalysisState.UNAVAILABLE if not gathered and not evidence else AnalysisState.PARTIAL

        advice = context.consejo.strip()[:500] if context and risk in {RiskLevel.LOW, RiskLevel.MEDIUM} else ""
        if risk == RiskLevel.UNKNOWN or not advice:
            advice = build_advice(risk)

        if risk == RiskLevel.LOW:
            summary = "No se detectaron señales suficientes en las comprobaciones que finalizaron."
        elif risk == RiskLevel.MEDIUM:
            summary = "Se detectaron señales que conviene verificar antes de responder."
        elif risk == RiskLevel.HIGH:
            summary = "Se encontró evidencia o una combinación de señales de riesgo elevado."
        else:
            summary = "No se pudo completar el análisis con las comprobaciones disponibles."

        return AnalysisResponse(
            riesgo=risk,
            estado=state,
            resumen=summary,
            motivos=all_evidence,
            consejo=advice,
            indicadores=findings,
            comprobaciones=checks,
        )


def _is_internal_signal(reason: str, internal_codes: set[str]) -> bool:
    normalized = reason.strip().casefold()
    return normalized in internal_codes or normalized.startswith("url_")


def _virustotal_evidence(result: VirusTotalUrlCheck, *, strong: bool) -> str:
    classification = "malicioso" if strong else "sospechoso"
    date_detail = (
        f" Último análisis registrado: {result.last_analysis_label}."
        if result.last_analysis_label
        else ""
    )
    return (
        f"VirusTotal marcó el enlace como {classification}: "
        f"{result.malicious} detección(es) maliciosa(s) y "
        f"{result.suspicious} sospechosa(s) entre "
        f"{result.analysed_engines} resultado(s) de motores."
        f"{date_detail}"
    )
