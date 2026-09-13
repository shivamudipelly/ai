"""Financial data tools with conservative validation and no placeholder data."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
import yfinance as yf
from pycoingecko import CoinGeckoAPI

logger = logging.getLogger(__name__)
yf.utils.user_agent_headers = {"User-Agent": "Mozilla/5.0"}
cg = CoinGeckoAPI()


def _number(value: Any):
    try:
        value = float(value)
        return value if value == value and value > 0 else None
    except (TypeError, ValueError):
        return None


class StockDataTool:
    @staticmethod
    def get_stock_price(ticker: str) -> Dict[str, Any]:
        ticker = ticker.strip().upper()
        if not ticker:
            return {"success": False, "error": "Ticker is required."}
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            price = _number(info.get("currentPrice") or info.get("regularMarketPrice"))
            previous = _number(info.get("previousClose"))
            if price is None:
                try:
                    hist = stock.history(period="5d", auto_adjust=False)
                    if not hist.empty:
                        price = _number(hist["Close"].iloc[-1])
                        if len(hist) > 1:
                            previous = _number(hist["Close"].iloc[-2]) or previous
                except Exception as exc:
                    logger.warning("History fallback failed for %s: %s", ticker, exc)
            if price is None:
                return {"success": False, "error": f"No reliable price data available for '{ticker}'."}
            currency = str(info.get("currency") or ("INR" if ticker.endswith((".NS", ".BO")) else "USD")).upper()
            if ticker.endswith((".NS", ".BO")) and currency != "INR":
                return {"success": False, "error": f"Currency validation failed for '{ticker}'."}
            change = price - previous if previous else None
            return {
                "success": True, "ticker": ticker,
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "current_price": round(price, 2), "currency": currency,
                "change": round(change, 2) if change is not None else None,
                "change_percent": round(change / previous * 100, 2) if change is not None and previous else None,
                "volume": info.get("volume"), "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"), "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "timestamp": datetime.now(timezone.utc).isoformat(), "source": "Yahoo Finance"
            }
        except Exception:
            logger.exception("Stock quote failed for %s", ticker)
            return {"success": False, "error": f"Failed to fetch data for '{ticker}'."}

    @staticmethod
    def get_stock_history(ticker: str, period: str = "1mo") -> Dict[str, Any]:
        ticker = ticker.strip().upper()
        try:
            hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
            if hist.empty:
                return {"success": False, "error": f"No historical data available for '{ticker}'."}
            rows = []
            for date, row in hist.iterrows():
                rows.append({"date": date.strftime("%Y-%m-%d"), "open": round(float(row["Open"]), 2), "high": round(float(row["High"]), 2), "low": round(float(row["Low"]), 2), "close": round(float(row["Close"]), 2), "volume": int(row["Volume"])})
            return {"success": True, "ticker": ticker, "period": period, "data": rows[-30:], "source": "Yahoo Finance"}
        except Exception:
            logger.exception("Stock history failed for %s", ticker)
            return {"success": False, "error": f"Failed to fetch history for '{ticker}'."}


class CryptoDataTool:
    @staticmethod
    def get_crypto_price(coin_id: str) -> Dict[str, Any]:
        coin = coin_id.lower().strip()
        try:
            data = cg.get_price(ids=coin, vs_currencies="usd,inr", include_market_cap=True, include_24hr_vol=True, include_24hr_change=True, include_24hr_high_low=True)
            item = data.get(coin) if isinstance(data, dict) else None
            if not item or _number(item.get("inr")) is None:
                return {"success": False, "error": f"No reliable data available for '{coin}'."}
            return {"success": True, "coin_id": coin, "current_price_usd": item.get("usd"), "current_price_inr": item.get("inr"), "market_cap_usd": item.get("usd_market_cap"), "market_cap_inr": item.get("inr_market_cap"), "24h_volume_usd": item.get("usd_24h_vol"), "24h_change_percent": item.get("usd_24h_change"), "24h_high_usd": item.get("usd_24h_high"), "24h_low_usd": item.get("usd_24h_low"), "timestamp": datetime.now(timezone.utc).isoformat(), "source": "CoinGecko"}
        except Exception:
            logger.exception("Crypto quote failed for %s", coin)
            return {"success": False, "error": f"Failed to fetch crypto data for '{coin}'."}

    @staticmethod
    def search_crypto(query: str) -> List[Dict[str, str]]:
        try:
            response = httpx.get("https://api.coingecko.com/api/v3/search", params={"query": query.strip()}, timeout=10.0)
            response.raise_for_status()
            return [{"id": x.get("id", ""), "name": x.get("name", ""), "symbol": str(x.get("symbol", "")).upper()} for x in response.json().get("coins", [])[:10]]
        except Exception:
            logger.exception("Crypto search failed")
            return []


class IPODataTool:
    """IPO interface intentionally returns no fabricated data until a verified source is integrated."""
    @staticmethod
    async def get_ipo_gmp(ticker: str) -> Dict[str, Any]:
        return {"success": False, "error": "Verified live IPO/GMP data source is not configured."}

    @staticmethod
    async def get_upcoming_ipos() -> List[Dict[str, str]]:
        return []


class MutualFundDataTool:
    @staticmethod
    def get_mf_nav(fund_code: str) -> Dict[str, Any]:
        code = fund_code.strip()
        try:
            response = httpx.get(f"https://api.mfapi.in/mf/{code}", timeout=10.0)
            if response.status_code != 200:
                return {"success": False, "error": f"Mutual Fund data not found for code '{code}'."}
            data = response.json(); meta = data.get("meta", {}); latest = (data.get("data") or [{}])[0]
            nav = _number(latest.get("nav"))
            if not meta.get("scheme_name") or nav is None:
                return {"success": False, "error": f"Invalid fund code '{code}'."}
            return {"success": True, "fund_code": code, "fund_name": meta.get("scheme_name"), "fund_house": meta.get("fund_house"), "nav": nav, "nav_date": latest.get("date", ""), "category": meta.get("scheme_type", "N/A"), "timestamp": datetime.now(timezone.utc).isoformat(), "source": "MFAPI"}
        except Exception:
            logger.exception("MF NAV failed for %s", code)
            return {"success": False, "error": f"Failed to fetch MF data for '{code}'."}


FINANCIAL_TOOLS = {
    "get_stock_price": StockDataTool.get_stock_price,
    "get_stock_history": StockDataTool.get_stock_history,
    "get_crypto_price": CryptoDataTool.get_crypto_price,
    "search_crypto": CryptoDataTool.search_crypto,
    "get_ipo_gmp": IPODataTool.get_ipo_gmp,
    "get_mf_nav": MutualFundDataTool.get_mf_nav,
}

TOOL_DESCRIPTIONS = {
    "get_stock_price": "Fetch a validated equity quote.",
    "get_stock_history": "Fetch historical equity prices.",
    "get_crypto_price": "Fetch cryptocurrency market data.",
    "search_crypto": "Resolve a cryptocurrency name or symbol.",
    "get_ipo_gmp": "IPO data is unavailable until a verified live source is configured.",
    "get_mf_nav": "Fetch mutual-fund NAV using an AMFI scheme code.",
}
