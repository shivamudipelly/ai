"""Entity resolution for Indian listed equities."""

import re
from typing import Any, Dict, List

import httpx

ALIASES = {
    "tcs": "TCS.NS", "tata consultancy services": "TCS.NS",
    "reliance": "RELIANCE.NS", "reliance industries": "RELIANCE.NS",
    "infosys": "INFY.NS", "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS", "hdfcbank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS", "icicibank": "ICICIBANK.NS",
    "sbi": "SBIN.NS", "state bank of india": "SBIN.NS",
    "itc": "ITC.NS", "wipro": "WIPRO.NS",
    "bharti airtel": "BHARTIARTL.NS", "airtel": "BHARTIARTL.NS",
    "adani enterprises": "ADANIENT.NS", "adani ports": "ADANIPORTS.NS",
}


def _clean(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip().lower()
    return re.sub(r"[^a-z0-9 .&-]", "", value)


def _score(query: str, name: str, symbol: str) -> int:
    q, n, s = _clean(query), _clean(name), _clean(symbol)
    if q == n or q == s:
        return 100
    if q in n or q in s:
        return 80
    words = [w for w in q.split() if len(w) > 2]
    return 60 if words and sum(w in n for w in words) == len(words) else 0


class IndianEquityResolver:
    """Resolve a company name or exchange ticker without guessing."""

    @staticmethod
    async def resolve(query: str) -> Dict[str, Any]:
        cleaned = _clean(query)
        if not cleaned:
            return {"success": False, "error": "A company name or ticker is required."}

        if re.fullmatch(r"[A-Za-z0-9-]+\.(?:NS|BO)", query.strip(), re.I):
            return {"success": True, "ticker": query.strip().upper(), "source": "explicit_ticker"}
        if cleaned in ALIASES:
            return {"success": True, "ticker": ALIASES[cleaned], "source": "verified_alias"}

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                response = await client.get(
                    "https://query1.finance.yahoo.com/v1/finance/search",
                    params={"q": query, "quotesCount": 10, "newsCount": 0},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                response.raise_for_status()
                quotes: List[Dict[str, Any]] = response.json().get("quotes", [])
        except Exception:
            return {"success": False, "error": "Company lookup is temporarily unavailable. Please provide the NSE/BSE ticker (for example, TCS.NS)."}

        candidates = []
        for quote in quotes:
            symbol = str(quote.get("symbol", "")).upper()
            if str(quote.get("quoteType", "")).upper() != "EQUITY":
                continue
            exchange = str(quote.get("exchange", "")).upper()
            if not (symbol.endswith(".NS") or symbol.endswith(".BO") or exchange in {"NSI", "BSE", "BOM"}):
                continue
            if not symbol.endswith((".NS", ".BO")):
                symbol += ".NS"
            name = quote.get("longname") or quote.get("shortname") or symbol
            score = _score(query, name, symbol)
            if score:
                candidates.append({"ticker": symbol, "company_name": name, "score": score})

        candidates.sort(key=lambda x: x["score"], reverse=True)
        if not candidates:
            return {"success": False, "error": f"Could not verify an Indian listed company matching '{query}'."}
        if candidates[0]["score"] < 80:
            return {"success": False, "ambiguous": True, "error": f"I found possible matches for '{query}', but I cannot safely choose one.", "candidates": candidates[:5]}
        best = candidates[0]
        return {"success": True, "ticker": best["ticker"], "company_name": best["company_name"], "source": "Yahoo Finance search"}
