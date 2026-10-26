import unittest
from unittest.mock import AsyncMock, patch

from app.detection.groq_client import ContextAssessment
from app.detection.reputation_client import UrlCheck
from app.detection.url_analyzer import UrlAnalyzer
from app.detection.virustotal_client import VirusTotalUrlCheck
from app.schemas.analysis import AnalysisRequest, AnalysisState, RiskLevel
from app.services.analysis_service import AnalysisService


class _Repository:
    async def lookup_many(self, _indicators):
        return []


class _Groq:
    async def assess(self, _text, _signals):
        return ContextAssessment(
            indicios_contextuales=[],
            consejo="Abrí el sitio escribiendo su dirección o desde la aplicación oficial.",
            riesgo_sugerido="bajo",
            confianza="alta",
        )


class _GroqReturningInternalCodes:
    async def assess(self, _text, _signals):
        return ContextAssessment(
            indicios_contextuales=[
                "url_propósito_login",
                "url_dominio_oficial_conocido",
            ],
            consejo="Abrí el sitio desde la aplicación oficial.",
            riesgo_sugerido="bajo",
            confianza="alta",
        )


class _Reputation:
    async def lookup(self, urls):
        return {url: UrlCheck("sin_coincidencias") for url in urls}


class _VirusTotalClean:
    async def lookup(self, urls):
        return {
            url: VirusTotalUrlCheck(
                "sin_detecciones",
                harmless=30,
                undetected=40,
            )
            for url in urls
        }


class _VirusTotalMalicious:
    async def lookup(self, urls):
        return {
            url: VirusTotalUrlCheck(
                "malicioso",
                malicious=4,
                harmless=10,
                undetected=20,
            )
            for url in urls
        }


class AnalysisUrlIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_login_does_not_become_medium_only_for_being_a_login(self):
        analyzer = UrlAnalyzer()
        service = AnalysisService(
            repository=_Repository(),
            groq_client=_Groq(),
            reputation_client=_Reputation(),
            url_analyzer=analyzer,
            virustotal_client=_VirusTotalClean(),
        )
        url = "https://www.santander.com.ar/login"

        with (
            patch("app.services.analysis_service.firebase_status", return_value=(True, "ok")),
            patch.object(analyzer, "_follow_redirects", AsyncMock(return_value=(url, 0))),
        ):
            result = await service.analyze(AnalysisRequest(texto=url))

        self.assertEqual(result.riesgo, RiskLevel.LOW)
        self.assertEqual(result.estado, AnalysisState.COMPLETE)
        self.assertIn(
            "url_dominio_oficial_conocido",
            {item.codigo for item in result.motivos},
        )

    async def test_galicia_login_is_low_and_internal_ai_codes_are_hidden(self):
        analyzer = UrlAnalyzer()
        service = AnalysisService(
            repository=_Repository(),
            groq_client=_GroqReturningInternalCodes(),
            reputation_client=_Reputation(),
            url_analyzer=analyzer,
            virustotal_client=_VirusTotalClean(),
        )
        url = "https://onlinebanking.bancogalicia.com.ar/login"

        with (
            patch("app.services.analysis_service.firebase_status", return_value=(True, "ok")),
            patch.object(analyzer, "_follow_redirects", AsyncMock(return_value=(url, 0))),
        ):
            result = await service.analyze(AnalysisRequest(texto=url))

        self.assertEqual(result.riesgo, RiskLevel.LOW)
        self.assertEqual(result.estado, AnalysisState.COMPLETE)
        self.assertFalse(any(item.fuente == "ia" for item in result.motivos))
        self.assertNotIn(
            "url_posible_suplantacion",
            {item.codigo for item in result.motivos},
        )

    async def test_virustotal_strong_detection_makes_the_result_high_risk(self):
        analyzer = UrlAnalyzer()
        service = AnalysisService(
            repository=_Repository(),
            groq_client=_Groq(),
            reputation_client=_Reputation(),
            url_analyzer=analyzer,
            virustotal_client=_VirusTotalMalicious(),
        )
        url = "https://unknown.example/download"

        with (
            patch("app.services.analysis_service.firebase_status", return_value=(True, "ok")),
            patch.object(analyzer, "_follow_redirects", AsyncMock(return_value=(url, 0))),
        ):
            result = await service.analyze(AnalysisRequest(texto=url))

        self.assertEqual(result.riesgo, RiskLevel.HIGH)
        self.assertIn(
            "url_detectada_virustotal",
            {item.codigo for item in result.motivos},
        )


if __name__ == "__main__":
    unittest.main()
