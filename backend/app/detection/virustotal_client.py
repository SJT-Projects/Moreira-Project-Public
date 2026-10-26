import asyncio
import base64
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class VirusTotalUrlCheck:
    estado: str
    malicious: int = 0
    suspicious: int = 0
    harmless: int = 0
    undetected: int = 0
    detalle: str = ""
    last_analysis_date: int | None = None

    @property
    def analysed_engines(self) -> int:
        return self.malicious + self.suspicious + self.harmless + self.undetected

    @property
    def last_analysis_label(self) -> str:
        if not self.last_analysis_date:
            return ""
        return datetime.fromtimestamp(self.last_analysis_date, tz=UTC).strftime("%Y-%m-%d")


class VirusTotalUnavailable(Exception):
    pass


class VirusTotalNotConfigured(VirusTotalUnavailable):
    pass


class VirusTotalClient:
    """Consulta reportes existentes sin enviar URLs nuevas a VirusTotal."""

    _ENDPOINT = "https://www.virustotal.com/api/v3/urls/{url_id}"
    _PUBLIC_REQUESTS_PER_MINUTE = 4

    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._transport = transport
        self._cache: dict[str, tuple[float, VirusTotalUrlCheck]] = {}
        self._request_times: deque[float] = deque()
        self._rate_lock = asyncio.Lock()

    async def lookup(self, urls: list[str]) -> dict[str, VirusTotalUrlCheck]:
        if not urls:
            return {}

        settings = get_settings()
        api_key = self._api_key if self._api_key is not None else settings.virustotal_api_key
        if not api_key:
            raise VirusTotalNotConfigured("VIRUSTOTAL_API_KEY no está configurada.")

        unique_urls = list(dict.fromkeys(urls))
        max_urls = max(1, min(settings.virustotal_max_urls_per_analysis, 4))
        selected = unique_urls[:max_urls]
        omitted = unique_urls[max_urls:]
        results: dict[str, VirusTotalUrlCheck] = {}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=4.0),
            transport=self._transport,
            headers={"accept": "application/json", "x-apikey": api_key},
        ) as client:
            for url in selected:
                cached = self._cached(url, settings.virustotal_cache_ttl_seconds)
                if cached is not None:
                    results[url] = cached
                    continue

                if not await self._reserve_request():
                    results[url] = VirusTotalUrlCheck(
                        estado="limite_local",
                        detalle=(
                            "Se alcanzó el límite local de 4 consultas por minuto; "
                            "el resto de las comprobaciones continúa disponible."
                        ),
                    )
                    continue

                results[url] = await self._lookup_one(client, url)
                self._cache[url] = (time.monotonic(), results[url])

        for url in omitted:
            results[url] = VirusTotalUrlCheck(
                estado="omitido",
                detalle=(
                    f"Se consultan como máximo {max_urls} enlace(s) por análisis para "
                    "cuidar la cuota gratuita de VirusTotal."
                ),
            )
        return results

    async def _lookup_one(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> VirusTotalUrlCheck:
        url_id = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
        try:
            response = await client.get(self._ENDPOINT.format(url_id=url_id))
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            raise VirusTotalUnavailable("VirusTotal no respondió a tiempo.") from exc

        if response.status_code == 404:
            return VirusTotalUrlCheck(
                estado="sin_informe",
                detalle="VirusTotal todavía no tiene un informe para este enlace.",
            )
        if response.status_code == 429:
            return VirusTotalUrlCheck(
                estado="limite_cuota",
                detalle="VirusTotal alcanzó temporalmente el límite de su API gratuita.",
            )
        if response.status_code in {401, 403}:
            raise VirusTotalUnavailable("VirusTotal rechazó la clave API configurada.")
        try:
            response.raise_for_status()
            attributes = response.json()["data"]["attributes"]
            stats = attributes.get("last_analysis_stats") or {}
            malicious = _non_negative_int(stats.get("malicious"))
            suspicious = _non_negative_int(stats.get("suspicious"))
            harmless = _non_negative_int(stats.get("harmless"))
            undetected = _non_negative_int(stats.get("undetected"))
            last_analysis_date = attributes.get("last_analysis_date")
            if not isinstance(last_analysis_date, int):
                last_analysis_date = None
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise VirusTotalUnavailable("VirusTotal devolvió una respuesta inválida.") from exc

        # Un único motor puede producir falsos positivos. Exigimos al menos dos
        # detecciones maliciosas para tratar el reporte como evidencia fuerte.
        if malicious >= 2:
            estado = "malicioso"
        elif malicious >= 1 or suspicious >= 2:
            estado = "sospechoso"
        else:
            estado = "sin_detecciones"

        return VirusTotalUrlCheck(
            estado=estado,
            malicious=malicious,
            suspicious=suspicious,
            harmless=harmless,
            undetected=undetected,
            detalle="Reporte de reputación consultado en VirusTotal.",
            last_analysis_date=last_analysis_date,
        )

    def _cached(self, url: str, ttl_seconds: int) -> VirusTotalUrlCheck | None:
        cached = self._cache.get(url)
        if cached is None:
            return None
        stored_at, result = cached
        if time.monotonic() - stored_at >= max(ttl_seconds, 0):
            self._cache.pop(url, None)
            return None
        return result

    async def _reserve_request(self) -> bool:
        async with self._rate_lock:
            now = time.monotonic()
            while self._request_times and now - self._request_times[0] >= 60:
                self._request_times.popleft()
            if len(self._request_times) >= self._PUBLIC_REQUESTS_PER_MINUTE:
                return False
            self._request_times.append(now)
            return True


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
