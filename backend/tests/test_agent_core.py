import unittest

from app.agent import AIAgent, clean_model_answer


class FinancialAgentCoreTests(unittest.TestCase):
    def setUp(self):
        self.agent = AIAgent()

    def test_internal_control_text_is_removed(self):
        text = "THOUGHT: fetch price\nACTION: get_stock_price\nFINAL_ANSWER: TCS is ₹100."
        self.assertEqual(clean_model_answer(text), "TCS is ₹100.")

    def test_stock_alias_resolution(self):
        self.assertEqual(self.agent._resolve_stock("What is TCS price?"), "TCS.NS")
        self.assertEqual(self.agent._resolve_stock("Analyze Reliance Industries"), "RELIANCE.NS")

    def test_explicit_exchange_ticker_resolution(self):
        self.assertEqual(self.agent._resolve_stock("price of INFY.NS"), "INFY.NS")
        self.assertEqual(self.agent._resolve_stock("price of ABC.BO"), "ABC.BO")

    def test_stock_data_validation_rejects_usd_for_indian_stock(self):
        data = {
            "success": True,
            "ticker": "TCS.NS",
            "current_price": 1000,
            "currency": "USD",
        }
        self.assertIsNone(self.agent._validate_stock(data, "TCS.NS"))

    def test_stock_data_validation_rejects_ticker_mismatch(self):
        data = {
            "success": True,
            "ticker": "RELIANCE.NS",
            "current_price": 1000,
            "currency": "INR",
        }
        self.assertIsNone(self.agent._validate_stock(data, "TCS.NS"))

    def test_stock_data_validation_accepts_valid_indian_quote(self):
        data = {
            "success": True,
            "ticker": "TCS.NS",
            "current_price": 1000,
            "currency": "INR",
        }
        self.assertEqual(self.agent._validate_stock(data, "TCS.NS"), data)


if __name__ == "__main__":
    unittest.main()
