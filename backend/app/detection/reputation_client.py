import asyncio
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class UrlCheck:
    estado: str
    threat_types: tuple[str, ...] = ()
    detalle: str = ""


class ReputationUnavailable(Exception):
    pass


class ReputationClient:
    # v5 devuelve Protocol Buffers por defecto. El endpoint Lookup v4 sigue
    # vigente y devuelve JSON, que evita incorporar un decodificador binario
    # solo para esta comprobación del backend.
    _ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

    async def lookup(self, urls: list[str]) -> dict[str, UrlCheck]:
        if not urls:
            return {}
        api_key = get_settings().safe_browsing_api_key
        if not api_key:
            raise ReputationUnavailable("SAFE_BROWSING_API_KEY no está configurada.")

        results: dict[str, UrlCheck] = {}
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0)) as client:
            # Keep the GET query below common URL-size limits even when a message
            # contains several long links.
            for start in range(0, len(urls), 5):
                batch = urls[start : start + 5]
                request_body = {
                    "client": {
                        "clientId": "moreira-anti-estafas",
                        "clientVersion": "1.0",
                    },
                    "threatInfo": {
                        "threatTypes": [
                            "MALWARE",
                            "SOCIAL_ENGINEERING",
                            "UNWANTED_SOFTWARE",
                            "POTENTIALLY_HARMFUL_APPLICATION",
                        ],
                        "platformTypes": ["ANY_PLATFORM"],
                        "threatEntryTypes": ["URL"],
                        "threatEntries": [{"url": value} for value in batch],
                    },
                }
                try:
                    response = await asyncio.wait_for(
                        client.post(
                            self._ENDPOINT,
                            params={"key": api_key},
                            json=request_body,
                        ),
                        timeout=10,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    for url in batch:
                        results[url] = UrlCheck("sin_coincidencias")
                    for threat in payload.get("matches", []):
                        matched_url = threat.get("threat", {}).get("url")
                        if matched_url:
                            previous = results.get(matched_url, UrlCheck("coincidencia"))
                            threat_type = str(threat.get("threatType", "")).strip()
                            threat_types = tuple(
                                dict.fromkeys(
                                    (*previous.threat_types, threat_type)
                                    if threat_type
                                    else previous.threat_types
                                )
                            )
                            results[matched_url] = UrlCheck(
                                "coincidencia",
                                threat_types,
                                "Google Safe Browsing encontró este enlace en una lista de amenazas.",
                            )
                except asyncio.TimeoutError as exc:
                    raise ReputationUnavailable("La consulta de reputación excedió el tiempo permitido.") from exc
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    raise ReputationUnavailable("No se pudo consultar la reputación de los enlaces.") from exc
        return results
