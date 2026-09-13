import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.agent import AIAgent, clean_model_answer
from app.services.entity_resolver import IndianEquityResolver


class FinancialAgentCoreTests(unittest.TestCase):
    def setUp(self):
        self.agent = AIAgent()

    def test_internal_control_text_is_removed(self):
        text = "THOUGHT: fetch price\nACTION: get_stock_price\nFINAL_ANSWER: TCS is ₹100."
        self.assertEqual(clean_model_answer(text), "TCS is ₹100.")

    def test_stock_alias_resolution(self):
        self.assertEqual(self.agent._classify("What is TCS price?"), "stock")
        self.assertEqual(self.agent._classify("Analyze Reliance Industries"), "stock")

    def test_explicit_exchange_ticker_resolution(self):
        self.assertEqual(self.agent._classify("price of INFY.NS"), "stock")

    def test_generic_price_does_not_force_stock_routing(self):
        self.assertEqual(self.agent._classify("What is the price?"), "general")

    def test_classifier_does_not_match_crypto_substrings(self):
        self.assertEqual(self.agent._classify("Explain ethical investing"), "general")

    def test_classifier_does_not_match_nav_inside_another_word(self):
        self.assertEqual(self.agent._classify("How do I navigate a portfolio?"), "general")

    def test_classifier_handles_real_crypto_symbol(self):
        self.assertEqual(self.agent._classify("What is BTC price?"), "crypto")

    def test_stock_data_validation_rejects_usd_for_indian_stock(self):
        data = {"success": True, "ticker": "TCS.NS", "current_price": 1000, "currency": "USD"}
        self.assertIsNone(self.agent._validate_stock(data, "TCS.NS"))

    def test_stock_data_validation_rejects_ticker_mismatch(self):
        data = {"success": True, "ticker": "RELIANCE.NS", "current_price": 1000, "currency": "INR"}
        self.assertIsNone(self.agent._validate_stock(data, "TCS.NS"))

    def test_stock_data_validation_rejects_boolean_price(self):
        data = {"success": True, "ticker": "TCS.NS", "current_price": True, "currency": "INR"}
        self.assertIsNone(self.agent._validate_stock(data, "TCS.NS"))

    def test_stock_data_validation_accepts_valid_indian_quote(self):
        data = {"success": True, "ticker": "TCS.NS", "current_price": 1000, "currency": "INR"}
        self.assertEqual(self.agent._validate_stock(data, "TCS.NS"), data)

    def test_resolver_accepts_explicit_ticker_without_network(self):
        result = asyncio.run(IndianEquityResolver.resolve("INFY.NS"))
        self.assertEqual(result["ticker"], "INFY.NS")

    def test_resolver_uses_alias_without_network(self):
        result = asyncio.run(IndianEquityResolver.resolve("Tata Consultancy Services"))
        self.assertEqual(result["ticker"], "TCS.NS")

    def test_resolver_does_not_guess_on_lookup_failure(self):
        with patch("app.services.entity_resolver.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.get = AsyncMock(side_effect=RuntimeError("network down"))
            result = asyncio.run(IndianEquityResolver.resolve("Unknown Telecom Company"))
        self.assertFalse(result["success"])
        self.assertNotIn("ticker", result)


if __name__ == "__main__":
    unittest.main()
