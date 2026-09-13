import unittest
from unittest.mock import AsyncMock, patch

from app.services.entity_resolver import IndianEquityResolver


class TestIndianEquityResolver(unittest.IsolatedAsyncioTestCase):
    async def test_known_alias(self):
        result = await IndianEquityResolver.resolve("TCS")
        self.assertTrue(result["success"])
        self.assertEqual(result["ticker"], "TCS.NS")

    async def test_explicit_ticker(self):
        result = await IndianEquityResolver.resolve("INFY.NS")
        self.assertTrue(result["success"])
        self.assertEqual(result["ticker"], "INFY.NS")

    async def test_unknown_company_uses_search(self):
        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"quotes": [{
                    "symbol": "SURANAT&P.NS",
                    "quoteType": "EQUITY",
                    "exchange": "NSI",
                    "longname": "Surana Telecom and Power Limited",
                }]}

        client = AsyncMock()
        client.get.return_value = Response()
        client_cm = AsyncMock()
        client_cm.__aenter__.return_value = client
        client_cm.__aexit__.return_value = False

        with patch("app.services.entity_resolver.httpx.AsyncClient", return_value=client_cm):
            result = await IndianEquityResolver.resolve("Surana Telecom and Power")

        self.assertTrue(result["success"])
        self.assertEqual(result["ticker"], "SURANAT&P.NS")

    async def test_lookup_failure_does_not_guess(self):
        client_cm = AsyncMock()
        client_cm.__aenter__.side_effect = RuntimeError("network unavailable")
        client_cm.__aexit__.return_value = False

        with patch("app.services.entity_resolver.httpx.AsyncClient", return_value=client_cm):
            result = await IndianEquityResolver.resolve("Some Unknown Company")

        self.assertFalse(result["success"])
        self.assertIn("temporarily unavailable", result["error"])


if __name__ == "__main__":
    unittest.main()
