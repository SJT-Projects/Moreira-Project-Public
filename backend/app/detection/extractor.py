import ipaddress
import re
from urllib.parse import urlsplit

import phonenumbers

from app.core.config import get_settings
from app.schemas.analysis import IndicatorInput, IndicatorType

_EMAIL = re.compile(r"(?i)(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+")
_URL = re.compile(r"""(?i)\b(?:https?://|www\.)[^\s<>"']{1,2048}""")
_DOMAIN = re.compile(
    r"(?i)(?<![\w@])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?:/[^\s<>\"']*)?"
)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{7,}\d)(?!\w)")
_TRAILING_URL = ".,;:!?)]}»'\""


def normalize_indicator(kind: IndicatorType, value: str) -> str | None:
    raw = value.strip()
    if kind == IndicatorType.EMAIL:
        if raw.count("@") != 1:
            return None
        local, domain = raw.rsplit("@", 1)
        if not local or not domain or "." not in domain:
            return None
        try:
            return f"{local.casefold()}@{domain.encode('idna').decode('ascii').lower()}"
        except UnicodeError:
            return None

    if kind in (IndicatorType.URL, IndicatorType.DOMAIN):
        candidate = raw if "://" in raw else f"https://{raw}"
        try:
            parsed = urlsplit(candidate)
            if not parsed.hostname or parsed.username or parsed.password:
                return None
            hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
            try:
                address = ipaddress.ip_address(hostname)
            except ValueError:
                address = None
                labels = hostname.split(".")
                if len(labels) < 2 or any(not label or len(label) > 63 for label in labels):
                    return None
            if kind == IndicatorType.DOMAIN:
                if address is not None:
                    return None
                return hostname
            scheme = parsed.scheme.lower()
            if scheme not in {"http", "https"}:
                return None
            default_port = 443 if scheme == "https" else 80
            port = f":{parsed.port}" if parsed.port and parsed.port != default_port else ""
            display_host = f"[{hostname}]" if address and address.version == 6 else hostname
            normalized = f"{scheme}://{display_host}{port}{parsed.path or '/'}"
            return normalized + (f"?{parsed.query}" if parsed.query else "")
        except (UnicodeError, ValueError):
            return None

    if kind == IndicatorType.PHONE:
        try:
            number = phonenumbers.parse(raw, get_settings().default_phone_region)
            if not phonenumbers.is_possible_number(number) or not phonenumbers.is_valid_number(number):
                return None
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return None
    return None


def extract_indicators(text: str) -> list[IndicatorInput]:
    found: dict[tuple[IndicatorType, str], IndicatorInput] = {}

    for match in _EMAIL.finditer(text):
        _add(found, IndicatorType.EMAIL, match.group().rstrip(".,;:!?)]}»\""))

    for match in _URL.finditer(text):
        raw = match.group().rstrip(_TRAILING_URL)
        if raw.lower().startswith("www."):
            raw = f"https://{raw}"
        _add(found, IndicatorType.URL, raw)
        normalized = normalize_indicator(IndicatorType.URL, raw)
        if normalized:
            host = urlsplit(normalized).hostname
            if host:
                _add(found, IndicatorType.DOMAIN, host)

    for match in _DOMAIN.finditer(text):
        raw = match.group().rstrip(_TRAILING_URL)
        _add(found, IndicatorType.DOMAIN, raw.split("/", 1)[0])

    for match in _PHONE.finditer(_URL.sub(" ", text)):
        _add(found, IndicatorType.PHONE, match.group())

    return list(found.values())[:50]


def _add(
    found: dict[tuple[IndicatorType, str], IndicatorInput], kind: IndicatorType, raw: str
) -> None:
    normalized = normalize_indicator(kind, raw)
    if normalized:
        found.setdefault((kind, normalized), IndicatorInput(type=kind, value=normalized))


def mask_for_model(text: str) -> str:
    """Elimina datos de contacto de la IA y no comparte rutas ni queries."""
    text = _EMAIL.sub("[correo oculto]", text)
    text = _URL.sub("[enlace]", text)
    text = _DOMAIN.sub("[dominio oculto]", text)
    return _PHONE.sub("[teléfono oculto]", text)


def mask_for_publication(text: str) -> str:
    text = _EMAIL.sub("[correo oculto]", text)
    text = _URL.sub("[enlace reportado]", text)
    text = _DOMAIN.sub("[dominio reportado]", text)
    return _PHONE.sub("[teléfono oculto]", text)
