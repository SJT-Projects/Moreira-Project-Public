import re

from app.detection.extractor import extract_indicators
from app.schemas.analysis import Evidence

_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "solicitud_credenciales",
        re.compile(r"\b(?:mand(?:a|ame|á|áme)|pas(?:a|ame|á|áme)|compart(?:i|í)|dict(?:a|ame|á))\b.{0,55}\b(?:clave|contrase(?:ñ|n)a|token|pin|codigo|código)\b|\b(?:clave|contrase(?:ñ|n)a|token|pin|codigo|código)\b.{0,55}\b(?:mand(?:a|ame|á|áme)|pas(?:a|ame|á|áme)|compart(?:i|í))\b", re.IGNORECASE),
        "El mensaje pide compartir una contraseña, un token o un código de verificación.",
    ),
    (
        "urgencia",
        re.compile(r"\b(?:urgente|urgencia|ahora|inmediatamente|inmediato|hoy|última oportunidad|ultimo aviso|último aviso|cuenta\s+(?:suspendida|bloqueada)|se\s+bloquear[aá])\b", re.IGNORECASE),
        "El mensaje presiona para actuar de inmediato.",
    ),
    (
        "solicitud_pago",
        re.compile(r"\b(?:transfer(?:encia|ime|ir)?|deposit(?:á|a|ame|ar)|pagar|pago|dinero|plata|cbu|alias)\b", re.IGNORECASE),
        "El mensaje solicita o menciona una transferencia o un pago.",
    ),
    (
        "solicitud_datos_financieros",
        re.compile(
            r"\b(?:mand(?:a|ame|á|áme)|pas(?:a|as|ame|á|áme)|compart(?:i|í)|dict(?:a|ame|á))\b.{0,55}"
            r"\b(?:tarjeta(?:\s+de\s+(?:cr[eé]dito|d[eé]bito))?|n[uú]mero\s+de\s+tarjeta|cvv|cvc|"
            r"fecha\s+de\s+vencimiento|datos\s+(?:bancarios|de\s+la\s+tarjeta))\b|"
            r"\b(?:tarjeta(?:\s+de\s+(?:cr[eé]dito|d[eé]bito))?|n[uú]mero\s+de\s+tarjeta|cvv|cvc|"
            r"fecha\s+de\s+vencimiento|datos\s+(?:bancarios|de\s+la\s+tarjeta))\b.{0,55}"
            r"\b(?:mand(?:a|ame|á|áme)|pas(?:a|as|ame|á|áme)|compart(?:i|í)|dict(?:a|ame|á))\b",
            re.IGNORECASE,
        ),
        "El mensaje pide datos de una tarjeta o información financiera sensible.",
    ),
    (
        "suplantacion_personal",
        re.compile(
            r"\b(?:soy|hola[, ]+soy)\s+(?:tu|su)\s+(?:hij[oa]|niet[oa]|sobrin[oa]|herman[oa]|"
            r"mam[aá]|pap[aá]|familiar|amig[oa])\b",
            re.IGNORECASE,
        ),
        "El mensaje dice ser un familiar o persona cercana sin una forma independiente de comprobarlo.",
    ),
    (
        "suplantacion_entidad",
        re.compile(r"\b(?:banco|banc[oa]\s+(?:nación|nacion)|soporte|seguridad|anses|afip|arca|mercado\s+pago|correo\s+argentino)\b", re.IGNORECASE),
        "El mensaje se presenta como una entidad, un banco o un servicio.",
    ),
    (
        "amenaza",
        re.compile(r"\b(?:bloquearemos|bloqueada|suspendida|embargo|denuncia|multa|secuestro|accidente)\b", re.IGNORECASE),
        "El mensaje usa una amenaza o consecuencia negativa para presionar.",
    ),
)


def analyze_rules(text: str) -> tuple[list[Evidence], list[str]]:
    evidence: list[Evidence] = []
    categories: list[str] = []
    for code, pattern, description in _PATTERNS:
        if pattern.search(text):
            categories.append(code)
            evidence.append(Evidence(fuente="reglas", codigo=code, descripcion=description))

    for item in extract_indicators(text):
        if item.type.value == "url":
            evidence.append(Evidence(
                fuente="url",
                codigo="enlace_incluido",
                descripcion="El mensaje contiene un enlace; esto solo no confirma que sea peligroso.",
            ))
        elif item.type.value == "email":
            evidence.append(Evidence(
                fuente="formato",
                codigo="correo_detectado",
                descripcion="Se detectó un correo para buscar reportes coincidentes.",
            ))
        elif item.type.value == "telefono":
            evidence.append(Evidence(
                fuente="formato",
                codigo="telefono_detectado",
                descripcion="Se detectó un número para buscar reportes coincidentes.",
            ))
    return evidence, categories
