import unittest

import httpx

from app.detection.virustotal_client import VirusTotalClient


class VirusTotalClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_malicious_engines_are_strong_evidence(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["x-apikey"], "test-key")
            return httpx.Response(
                200,
                json={
                    "data": {
                        "attributes": {
                            "last_analysis_date": 1_700_000_000,
                            "last_analysis_stats": {
                                "malicious": 2,
                                "suspicious": 1,
                                "harmless": 20,
                                "undetected": 40,
                            },
                        }
                    }
                },
            )

        client = VirusTotalClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )

        result = (await client.lookup(["https://example.test/login"]))[
            "https://example.test/login"
        ]

        self.assertEqual(result.estado, "malicioso")
        self.assertEqual(result.malicious, 2)
        self.assertEqual(result.analysed_engines, 63)

    async def test_one_detection_is_treated_as_suspicious_to_reduce_false_positives(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "attributes": {
                            "last_analysis_stats": {
                                "malicious": 1,
                                "suspicious": 0,
                                "harmless": 30,
                                "undetected": 20,
                            }
                        }
                    }
                },
            )

        client = VirusTotalClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )

        result = (await client.lookup(["https://example.test/"]))[
            "https://example.test/"
        ]

        self.assertEqual(result.estado, "sospechoso")

    async def test_unknown_url_is_not_submitted_for_scanning(self):
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(404, json={"error": {"code": "NotFoundError"}})

        client = VirusTotalClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        )

        result = (await client.lookup(["https://unknown.example/"]))[
            "https://unknown.example/"
        ]

        self.assertEqual(result.estado, "sin_informe")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].method, "GET")


if __name__ == "__main__":
    unittest.main()
