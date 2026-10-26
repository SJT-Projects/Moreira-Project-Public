import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import parse_qsl, urljoin, urlsplit, urlunsplit

import httpx


@dataclass(frozen=True)
class UrlSignal:
    code: str
    description: str
    category: str | None = None


@dataclass(frozen=True)
class UrlInspection:
    original_url: str
    final_url: str
    original_host: str
    final_host: str
    redirect_count: int
    service: str | None
    official_domain: bool
    signals: tuple[UrlSignal, ...]
    context_tags: tuple[str, ...]
    resolution_detail: str = ""


@dataclass(frozen=True)
class _OfficialService:
    name: str
    domains: tuple[str, ...]
    brand_tokens: tuple[str, ...]


# Lista deliberadamente acotada. Un dominio desconocido no se considera falso por
# sí solo; esta tabla únicamente permite confirmar algunos destinos muy usados.
_OFFICIAL_SERVICES = (
    _OfficialService("Banco Nación", ("bna.com.ar",), ("bna", "banconacion")),
    _OfficialService("Red Link", ("redlink.com.ar",), ("redlink",)),
    _OfficialService("Santander Argentina", ("santander.com.ar",), ("santander",)),
    _OfficialService("BBVA Argentina", ("bbva.com.ar",), ("bbva",)),
    _OfficialService(
        "Banco Galicia",
        ("galicia.ar", "bancogalicia.com.ar"),
        ("galicia", "bancogalicia"),
    ),
    _OfficialService("Banco Macro", ("macro.com.ar",), ("bancomacro",)),
    _OfficialService("Banco Provincia", ("bancoprovincia.com.ar",), ("bancoprovincia",)),
    _OfficialService("Mercado Pago", ("mercadopago.com", "mercadopago.com.ar"), ("mercadopago",)),
    _OfficialService("Mercado Libre", ("mercadolibre.com", "mercadolibre.com.ar"), ("mercadolibre",)),
    _OfficialService("ARCA", ("arca.gob.ar",), ("arca", "afip")),
    _OfficialService("ANSES", ("anses.gob.ar",), ("anses",)),
    _OfficialService("Argentina.gob.ar", ("argentina.gob.ar",), ("argentina",)),
    _OfficialService("Google", ("google.com", "google.com.ar"), ("google",)),
    _OfficialService("YouTube", ("youtube.com", "youtu.be"), ("youtube", "youtu")),
)

_MULTI_LABEL_SUFFIXES = {
    "com.ar", "net.ar", "org.ar", "gob.ar", "gov.ar", "edu.ar", "mil.ar",
    "com.br", "com.mx", "com.co", "com.uy", "co.uk", "com.au", "co.nz",
}
_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly",
    "shorturl.at", "rebrand.ly", "buff.ly",
}
_LOGIN_TOKENS = {
    "login", "log-in", "signin", "sign-in", "auth", "acceso", "ingresar",
    "iniciar-sesion", "iniciarsesion", "homebanking", "online-banking",
}
_FINANCIAL_ACTION_TOKENS = {
    "transferir", "transferencia", "transfers", "pagar", "pago", "payments",
    "enviar-dinero", "solicitar-pago", "cobrar", "cbu", "alias", "wallet",
}
_CREDENTIAL_QUERY_KEYS = {
    "login", "signin", "auth", "password", "passwd", "token", "pin", "verify",
    "verification", "usuario", "clave",
}
_REDIRECT_CODES = {301, 302, 303, 307, 308}


class UrlAnalyzer:
    def __init__(self, *, max_redirects: int = 5) -> None:
        self._max_redirects = max_redirects

    async def inspect_many(self, urls: list[str]) -> dict[str, UrlInspection]:
        unique_urls = list(dict.fromkeys(urls))[:10]
        inspections = await asyncio.gather(*(self.inspect(url) for url in unique_urls))
        return {item.original_url: item for item in inspections}

    async def inspect(self, url: str) -> UrlInspection:
        parsed = _parse_public_url(url)
        original_host = parsed.hostname or ""
        signals, tags = _classify_url(parsed)
        final_url = url
        final_host = original_host
        redirects = 0
        detail = ""

        try:
            final_url, redirects = await self._follow_redirects(url)
            final_parsed = _parse_public_url(final_url)
            final_host = final_parsed.hostname or original_host
            final_signals, final_tags = _classify_url(final_parsed)
            signals.extend(final_signals)
            tags.extend(final_tags)

            if final_host != original_host:
                tags.append("url_redireccion_otro_dominio")
                if _is_shortener(original_host) and _has_sensitive_purpose(final_parsed):
                    signals.append(UrlSignal(
                        "url_destino_sensible_oculto",
                        "El enlace acortado oculta un destino que solicita acceso o permite una operación financiera.",
                        "url_destino_sensible_oculto",
                    ))
        except ValueError as exc:
            detail = str(exc)
            if "privada o local" in detail:
                signals.append(UrlSignal(
                    "url_destino_no_publico",
                    "El enlace intenta dirigir a una dirección privada o local y no se abrió desde el servidor.",
                    "url_destino_no_publico",
                ))
        except (httpx.HTTPError, OSError, asyncio.TimeoutError):
            detail = "No se pudo contactar el destino para comprobar sus redirecciones."

        service = _official_service(final_host)
        official = service is not None
        if official:
            tags.append("url_dominio_oficial_conocido")
            if _has_login_purpose(urlsplit(final_url)):
                tags.append("url_login_en_dominio_oficial")

        signals = _deduplicate_signals(signals)
        tags = list(dict.fromkeys(tags))
        return UrlInspection(
            original_url=url,
            final_url=final_url,
            original_host=original_host,
            final_host=final_host,
            redirect_count=redirects,
            service=service.name if service else None,
            official_domain=official,
            signals=tuple(signals),
            context_tags=tuple(tags),
            resolution_detail=detail,
        )

    async def _follow_redirects(self, url: str) -> tuple[str, int]:
        current = url
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(7.0, connect=4.0),
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "Moreira-AntiEstafas/1.0 URL-checker"},
        ) as client:
            for redirect_count in range(self._max_redirects + 1):
                parsed = _parse_public_url(current)
                ip = await _resolve_public_ip(parsed.hostname or "", parsed.port)
                response = await _request_pinned(client, parsed, ip)
                if response.status_code not in _REDIRECT_CODES:
                    return current, redirect_count
                location = response.headers.get("location", "").strip()
                if not location:
                    return current, redirect_count
                if redirect_count == self._max_redirects:
                    raise ValueError("El enlace supera el límite de redirecciones permitido.")
                current = _normalize_redirect(urljoin(current, location))
        return current, self._max_redirects


def _parse_public_url(url: str):
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("El enlace no usa una dirección web HTTP o HTTPS válida.")
        if parsed.username or parsed.password:
            raise ValueError("El enlace oculta credenciales o un dominio detrás del carácter @.")
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if not host or len(host) > 253:
            raise ValueError("El dominio del enlace no es válido.")
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        if port not in {80, 443}:
            raise ValueError("El enlace usa un puerto no habitual y no se abrió desde el servidor.")
        return parsed._replace(netloc=_netloc(host, parsed.port, parsed.scheme.lower()))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("El enlace"):
            raise
        raise ValueError("El enlace no tiene un formato válido.") from exc


def _normalize_redirect(url: str) -> str:
    parsed = _parse_public_url(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, ""))


def _netloc(host: str, explicit_port: int | None, scheme: str) -> str:
    default_port = 443 if scheme == "https" else 80
    display_host = f"[{host}]" if ":" in host else host
    return display_host if explicit_port in {None, default_port} else f"{display_host}:{explicit_port}"


async def _resolve_public_ip(host: str, explicit_port: int | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        port = explicit_port or 443
        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                port,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise OSError("No se pudo resolver el dominio.") from exc
        addresses = []
        for record in records:
            try:
                address = ipaddress.ip_address(record[4][0])
            except ValueError:
                continue
            if address not in addresses:
                addresses.append(address)

    public = [address for address in addresses if _is_public_address(address)]
    if not public or len(public) != len(addresses):
        raise ValueError("El enlace resuelve a una dirección privada o local y fue bloqueado.")
    # IPv4 suele ser alcanzable incluso en redes sin salida IPv6. La validación
    # sigue incluyendo todos los registros para bloquear respuestas DNS mixtas.
    public.sort(key=lambda address: address.version != 4)
    return public[0]


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


async def _request_pinned(client: httpx.AsyncClient, parsed, ip) -> httpx.Response:
    ip_text = f"[{ip}]" if ip.version == 6 else str(ip)
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    port_suffix = "" if port == (443 if parsed.scheme.lower() == "https" else 80) else f":{port}"
    pinned_url = urlunsplit((parsed.scheme, f"{ip_text}{port_suffix}", parsed.path or "/", parsed.query, ""))
    host_header = parsed.hostname or ""
    if port_suffix:
        host_header += port_suffix
    return await client.request(
        "HEAD",
        pinned_url,
        headers={"Host": host_header},
        extensions={"sni_hostname": parsed.hostname},
    )


def _classify_url(parsed) -> tuple[list[UrlSignal], list[str]]:
    host = (parsed.hostname or "").lower()
    path = parsed.path.casefold()
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    signals: list[UrlSignal] = []
    tags: list[str] = []
    service = _official_service(host)

    if parsed.scheme.lower() == "http":
        signals.append(UrlSignal(
            "url_sin_https",
            "El enlace usa HTTP sin cifrado en lugar de HTTPS.",
            "url_sin_https",
        ))
    if "xn--" in host:
        signals.append(UrlSignal(
            "url_dominio_punycode",
            "El dominio usa una representación internacionalizada que puede ocultar caracteres parecidos.",
            "url_dominio_punycode",
        ))
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        signals.append(UrlSignal(
            "url_dominio_es_ip",
            "El enlace usa una dirección IP en vez de un nombre de sitio reconocible.",
            "url_dominio_es_ip",
        ))

    impersonated = _impersonated_service(host)
    if impersonated and not service:
        signals.append(UrlSignal(
            "url_posible_suplantacion",
            f"El dominio parece mencionar a {impersonated.name}, pero no pertenece a sus dominios oficiales conocidos.",
            "url_posible_suplantacion",
        ))

    login = _has_login_purpose(parsed) or bool(query_keys & _CREDENTIAL_QUERY_KEYS)
    financial_action = _contains_token(path, _FINANCIAL_ACTION_TOKENS)
    if login:
        tags.append("url_propósito_login")
        if not service:
            signals.append(UrlSignal(
                "url_login_dominio_no_confirmado",
                "El enlace abre una pantalla de acceso en un dominio que la aplicación no puede confirmar como oficial.",
                "url_login_dominio_no_confirmado",
            ))
    if financial_action:
        tags.append("url_operacion_financiera")
        signals.append(UrlSignal(
            "url_operacion_financiera",
            "La ruta del enlace parece llevar a una transferencia, pago o solicitud de dinero.",
            "url_operacion_financiera",
        ))
    if _is_shortener(host):
        tags.append("url_acortado")
    if len(host.split(".")) >= 5 and not service:
        signals.append(UrlSignal(
            "url_subdominios_excesivos",
            "El dominio usa muchos subdominios; revisá con cuidado cuál es el dominio principal.",
            "url_subdominios_excesivos",
        ))
    return signals, tags


def _official_service(host: str) -> _OfficialService | None:
    for service in _OFFICIAL_SERVICES:
        if any(host == domain or host.endswith(f".{domain}") for domain in service.domains):
            return service
    return None


def _impersonated_service(host: str) -> _OfficialService | None:
    registered = _registrable_domain(host)
    # También se revisan subdominios: "banco.ejemplo.com" sigue perteneciendo
    # a ejemplo.com, aunque el nombre de la entidad aparezca a la izquierda.
    compact = re.sub(r"[^a-z0-9]", "", host)
    stem = registered.split(".", 1)[0]
    for service in _OFFICIAL_SERVICES:
        for token in service.brand_tokens:
            if token in compact:
                return service
        for domain in service.domains:
            official_stem = domain.split(".", 1)[0]
            if len(official_stem) >= 5 and _edit_distance(stem, official_stem) <= 1:
                return service
    return None


def _registrable_domain(host: str) -> str:
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    suffix = ".".join(labels[-2:])
    return ".".join(labels[-3:]) if suffix in _MULTI_LABEL_SUFFIXES else suffix


def _has_login_purpose(parsed) -> bool:
    return _contains_token(parsed.path.casefold(), _LOGIN_TOKENS)


def _has_sensitive_purpose(parsed) -> bool:
    return _has_login_purpose(parsed) or _contains_token(parsed.path.casefold(), _FINANCIAL_ACTION_TOKENS)


def _contains_token(value: str, tokens: set[str]) -> bool:
    normalized = re.sub(r"[^a-z0-9áéíóúñ]+", "-", value.casefold()).strip("-")
    padded = f"-{normalized}-"
    return any(f"-{token}-" in padded for token in tokens)


def _is_shortener(host: str) -> bool:
    return host in _SHORTENERS or any(host.endswith(f".{item}") for item in _SHORTENERS)


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(min(
                current[-1] + 1,
                previous[right_index] + 1,
                previous[right_index - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def _deduplicate_signals(signals: list[UrlSignal]) -> list[UrlSignal]:
    unique: dict[tuple[str, str], UrlSignal] = {}
    for signal in signals:
        unique.setdefault((signal.code, signal.description), signal)
    return list(unique.values())
