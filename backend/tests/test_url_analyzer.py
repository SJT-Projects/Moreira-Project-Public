import unittest
from unittest.mock import AsyncMock, patch

from app.detection.decision import decide_risk
from app.detection.extractor import extract_indicators
from app.detection.url_analyzer import UrlAnalyzer
from app.schemas.analysis import RiskLevel


class UrlAnalyzerTests(unittest.IsolatedAsyncioTestCase):
    async def inspect_without_network(self, url: str, final_url: str | None = None):
        analyzer = UrlAnalyzer()
        with patch.object(
            analyzer,
            "_follow_redirects",
            AsyncMock(return_value=(final_url or url, int(final_url is not None))),
        ):
            return await analyzer.inspect(url)

    async def test_official_bank_login_is_recognized_without_risk_signal(self):
        result = await self.inspect_without_network("https://www.santander.com.ar/login")

        self.assertEqual(result.service, "Santander Argentina")
        self.assertTrue(result.official_domain)
        self.assertIn("url_login_en_dominio_oficial", result.context_tags)
        self.assertNotIn("url_login_dominio_no_confirmado", {item.code for item in result.signals})

    async def test_official_galicia_login_alias_is_recognized(self):
        result = await self.inspect_without_network(
            "https://onlinebanking.bancogalicia.com.ar/login"
        )

        self.assertEqual(result.service, "Banco Galicia")
        self.assertTrue(result.official_domain)
        codes = {item.code for item in result.signals}
        self.assertNotIn("url_posible_suplantacion", codes)
        self.assertNotIn("url_login_dominio_no_confirmado", codes)

    async def test_brand_in_fake_domain_is_flagged(self):
        result = await self.inspect_without_network("https://santander-seguridad.example.com/login")
        codes = {item.code for item in result.signals}

        self.assertIn("url_posible_suplantacion", codes)
        self.assertIn("url_login_dominio_no_confirmado", codes)
        categories = {item.category for item in result.signals if item.category}
        self.assertEqual(
            decide_risk(
                categories=categories,
                evidence=[],
                indicators=[],
                malicious_urls=0,
            ),
            RiskLevel.HIGH,
        )

    async def test_financial_operation_path_is_contextual_signal(self):
        result = await self.inspect_without_network("https://www.bbva.com.ar/transferir")

        self.assertIn("url_operacion_financiera", {item.code for item in result.signals})

    async def test_shortener_to_sensitive_destination_is_flagged(self):
        result = await self.inspect_without_network(
            "https://bit.ly/example",
            "https://unknown.example/login",
        )

        self.assertIn("url_destino_sensible_oculto", {item.code for item in result.signals})

    async def test_private_destination_is_never_requested(self):
        extracted = extract_indicators("revisá http://127.0.0.1/login")
        self.assertIn("http://127.0.0.1/login", {item.value for item in extracted})

        result = await UrlAnalyzer().inspect("http://127.0.0.1/login")

        self.assertIn("url_destino_no_publico", {item.code for item in result.signals})


if __name__ == "__main__":
    unittest.main()
