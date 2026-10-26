from app.schemas.analysis import Evidence, EvidenceStatus, IndicatorFinding, RiskLevel

_HIGH_SIGNAL_COMBINATIONS = (
    frozenset({"solicitud_credenciales", "suplantacion_entidad"}),
    frozenset({"solicitud_credenciales", "urgencia"}),
    frozenset({"solicitud_credenciales", "amenaza"}),
    frozenset({"amenaza", "solicitud_pago"}),
    frozenset({"solicitud_datos_financieros", "suplantacion_personal"}),
    frozenset({"solicitud_datos_financieros", "urgencia"}),
    frozenset({"url_posible_suplantacion", "url_login_dominio_no_confirmado"}),
    frozenset({"url_posible_suplantacion", "solicitud_credenciales"}),
    frozenset({"url_posible_suplantacion", "suplantacion_entidad"}),
    frozenset({"url_operacion_financiera", "urgencia"}),
    frozenset({"url_operacion_financiera", "suplantacion_personal"}),
    frozenset({"url_destino_sensible_oculto", "suplantacion_entidad"}),
)


def decide_risk(
    *,
    categories: set[str],
    evidence: list[Evidence],
    indicators: list[IndicatorFinding],
    malicious_urls: int,
    ai_risk: str | None = None,
    ai_confidence: str | None = None,
) -> RiskLevel:
    if malicious_urls:
        return RiskLevel.HIGH
    if any(item.estado == EvidenceStatus.CONFIRMED for item in indicators):
        return RiskLevel.HIGH
    if any(pair <= categories for pair in _HIGH_SIGNAL_COMBINATIONS):
        return RiskLevel.HIGH

    contextual_signals = {
        evidence_item.descripcion.strip().casefold()
        for evidence_item in evidence
        if evidence_item.fuente == "ia" and evidence_item.descripcion.strip()
    }
    if ai_risk == RiskLevel.HIGH.value and ai_confidence == "alta" and len(contextual_signals) >= 2:
        return RiskLevel.HIGH

    if any(item.estado == EvidenceStatus.UNDER_REVIEW for item in indicators):
        return RiskLevel.MEDIUM
    if any(item.reportes_aprobados >= 2 for item in indicators):
        return RiskLevel.MEDIUM
    if categories & {
        "solicitud_credenciales",
        "solicitud_datos_financieros",
        "amenaza",
        "url_posible_suplantacion",
        "url_login_dominio_no_confirmado",
        "url_operacion_financiera",
        "url_destino_sensible_oculto",
        "url_destino_no_publico",
        "url_dominio_punycode",
        "url_reputacion_virustotal_sospechosa",
    }:
        return RiskLevel.MEDIUM

    if ai_risk in {RiskLevel.MEDIUM.value, RiskLevel.HIGH.value} and contextual_signals:
        return RiskLevel.MEDIUM
    if len(categories) >= 2 or len(contextual_signals) >= 2:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def build_advice(risk: RiskLevel) -> str:
    if risk == RiskLevel.HIGH:
        return (
            "No abras el enlace ni compartas claves o códigos. Contactá a la entidad "
            "desde su aplicación o teléfono oficial."
        )
    if risk == RiskLevel.MEDIUM:
        return (
            "Verificá la solicitud por otro canal oficial y no envíes dinero ni "
            "compartas claves o códigos hasta confirmarla."
        )
    if risk == RiskLevel.UNKNOWN:
        return "No se pudo completar el análisis. Por precaución, no abras enlaces ni compartas datos."
    return "No se detectaron indicios en las comprobaciones realizadas. Verificá siempre antes de compartir datos."
