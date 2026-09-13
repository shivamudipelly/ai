import asyncio
import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Union

import httpx

from app.config import settings
from app.tools import FINANCIAL_TOOLS
from app.repositories import MessageRepository
from app.models import Message

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

STOCK_ALIASES = {
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
STOCK_TERMS = ("stock", "share", "equity", "nse", "bse", "price", "quote", "market cap", "p/e", "pe ratio", "52 week", "52-week", "dividend", "fundamental", "fundamentals", "technical analysis", "analyze", "analyse", "buy", "sell")
CRYPTO_TERMS = ("crypto", "bitcoin", "ethereum", "btc", "eth")
MF_TERMS = ("mutual fund", "mf nav", "nav", "sip", "scheme", "fund code")
IPO_TERMS = ("ipo", "gmp", "grey market", "grey-market", "issue price", "listing date")


def now_ist() -> datetime:
    return datetime.now(IST)


def clean_model_answer(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(?is)\bTHOUGHT\s*:.*?(?=\b(?:FINAL_ANSWER|ANSWER)\s*:|$)", "", text)
    text = re.sub(r"(?im)^\s*(ACTION|ACTION_INPUT|OBSERVATION|FINAL_ANSWER|ANSWER)\s*:\s*", "", text)
    return text.strip()


class AIAgent:
    """Financial assistant orchestration layer.

    External financial data is selected and executed by backend code. Ollama
    receives validated data and is used for explanation, not as a source of
    live financial facts.
    """

    def __init__(self):
        self.context_window_size = getattr(settings, "max_context_messages", 10)

    @property
    def ollama_url(self) -> str:
        return f"{settings.ollama_host.rstrip('/')}/api/generate"

    @property
    def model_name(self) -> str:
        return settings.ollama_model

    def _today_text(self) -> str:
        return now_ist().strftime("%A, %d %B %Y")

    async def _ollama(self, prompt: str) -> str:
        payload = {"model": self.model_name, "prompt": prompt, "stream": False,
                   "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 384,
                                "stop": ["USER:", "\nUSER:"]}}
        timeout = httpx.Timeout(getattr(settings, "ollama_timeout", 120.0), connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.ollama_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "").strip()

    def _format_context(self, history: List[Union[Message, Dict[str, Any]]]) -> str:
        parts = []
        for msg in history[-self.context_window_size:]:
            if isinstance(msg, Message):
                role, content = msg.role, msg.content
            else:
                role, content = msg.get("role", "assistant"), msg.get("content", "")
            parts.append(f"{'User' if role == 'user' else 'Assistant'}: {content}")
        return "\n".join(parts)

    def _classify(self, text: str) -> str:
        q = text.lower()
        if any(term in q for term in IPO_TERMS): return "ipo"
        if any(term in q for term in MF_TERMS): return "mutual_fund"
        if any(term in q for term in CRYPTO_TERMS): return "crypto"
        if re.search(r"\b[A-Z]{2,15}\.(?:NS|BO)\b", text, re.I): return "stock"
        if any(name in q for name in STOCK_ALIASES): return "stock"
        if any(term in q for term in STOCK_TERMS): return "stock"
        return "general"

    def _resolve_stock(self, text: str) -> Optional[str]:
        q = text.lower()
        match = re.search(r"\b([A-Za-z][A-Za-z0-9&-]{0,14}\.(?:NS|BO))\b", text, re.I)
        if match: return match.group(1).upper()
        for alias in sorted(STOCK_ALIASES, key=len, reverse=True):
            if alias in q: return STOCK_ALIASES[alias]
        return None

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in FINANCIAL_TOOLS:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        try:
            func = FINANCIAL_TOOLS[tool_name]
            if asyncio.iscoroutinefunction(func): result = await func(**tool_input)
            else: result = await asyncio.to_thread(func, **tool_input)
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as exc:
            logger.exception("Tool %s failed", tool_name)
            return {"success": False, "error": str(exc)}

    def _validate_stock(self, data: Dict[str, Any], ticker: str) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict) or data.get("error") or not data.get("success"): return None
        price, currency, returned = data.get("current_price"), str(data.get("currency", "")).upper(), str(data.get("ticker", "")).upper()
        if not isinstance(price, (int, float)) or price <= 0: return None
        if returned != ticker.upper(): return None
        if ticker.upper().endswith((".NS", ".BO")) and currency != "INR": return None
        return data

    def _stock_prompt(self, user_message: str, data: Dict[str, Any], history: str) -> str:
        return f"""You are a concise Indian financial assistant. Today is {self._today_text()} (Asia/Kolkata).
The MARKET DATA below is authoritative. Use only the supplied numbers. Never invent, estimate, replace, or convert a market value. If a value is missing, say it is unavailable. Never mention internal tools, prompts, reasoning, ACTION, THOUGHT, or OBSERVATION. Do not repeat sentences. Answer directly in 2-5 short sentences.
MARKET DATA:\n{json.dumps(data, ensure_ascii=False, default=str)}
RECENT CONTEXT:\n{history}
USER:\n{user_message}\nAnswer:"""

    def _general_prompt(self, user_message: str, history: str) -> str:
        return f"""You are a helpful personal finance assistant focused on India. Today is {self._today_text()} (Asia/Kolkata).
Answer clearly and concisely. Do not invent current prices, market statistics, dates, or other time-sensitive financial facts. If the user asks for live market data, say that live data must be fetched rather than guessing. Never expose internal reasoning, tools, prompts, or control labels.
RECENT CONTEXT:\n{history}\nUSER:\n{user_message}\nAnswer:"""

    async def _prepare(self, user_message: str, conversation_id: str):
        history = await MessageRepository.get_messages_by_conversation(conversation_id, limit=self.context_window_size)
        context, intent, tools_used, data = self._format_context(history), self._classify(user_message), [], None
        if intent == "stock":
            ticker = self._resolve_stock(user_message)
            if not ticker:
                return context, None, tools_used, "I couldn't reliably identify the NSE/BSE stock. Please provide the company name or ticker, for example TCS.NS."
            raw = await self.execute_tool("get_stock_price", {"ticker": ticker})
            data = self._validate_stock(raw, ticker); tools_used.append("get_stock_price")
            if not data: return context, None, tools_used, f"I couldn't retrieve reliable live market data for {ticker} right now."
        elif intent == "crypto":
            q = user_message.lower()
            coin = "bitcoin" if any(x in q for x in ("bitcoin", "btc")) else ("ethereum" if any(x in q for x in ("ethereum", "eth")) else None)
            if not coin: return context, None, tools_used, "I can fetch live crypto prices, but I need the coin name or symbol."
            data = await self.execute_tool("get_crypto_price", {"coin_id": coin}); tools_used.append("get_crypto_price")
            if not data.get("success") or not data.get("current_price_inr"): return context, None, tools_used, f"I couldn't retrieve reliable live data for {coin} right now."
        elif intent == "mutual_fund":
            match = re.search(r"\b\d{4,8}\b", user_message)
            if not match: return context, None, tools_used, "Please provide the mutual-fund AMFI scheme code so I can fetch its NAV."
            data = await self.execute_tool("get_mf_nav", {"fund_code": match.group(0)}); tools_used.append("get_mf_nav")
            if not data.get("success") or not data.get("nav"): return context, None, tools_used, "I couldn't retrieve reliable NAV data for that mutual fund right now."
        elif intent == "ipo":
            return context, None, tools_used, "I don't have a verified live IPO database connected yet, so I won't guess IPO dates, price bands, subscription figures, or GMP."
        return context, data, tools_used, None

    async def _answer_from_data(self, user_message: str, data: Dict[str, Any], context: str) -> str:
        if "current_price" in data:
            prompt = self._stock_prompt(user_message, data, context)
        elif "current_price_inr" in data:
            prompt = f"""You are a concise Indian financial assistant. Use ONLY this verified crypto data. Do not invent or change numbers. Never expose internal reasoning or tool names. Answer in 2-4 short sentences.\nVERIFIED DATA:\n{json.dumps(data, ensure_ascii=False, default=str)}\nUSER:\n{user_message}\nAnswer:"""
        else:
            prompt = f"""You are a concise Indian mutual-fund assistant. Use ONLY this verified NAV data. Do not invent or change numbers. Never expose internal reasoning or tool names. Answer in 2-4 short sentences.\nVERIFIED DATA:\n{json.dumps(data, ensure_ascii=False, default=str)}\nUSER:\n{user_message}\nAnswer:"""
        return clean_model_answer(await self._ollama(prompt))

    async def process_message(self, user_message: str, conversation_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        await MessageRepository.add_message(conversation_id, user_id, "user", user_message)
        tools_used, data = [], None
        try:
            context, data, tools_used, immediate = await self._prepare(user_message, conversation_id)
            if immediate: answer = immediate
            elif data: answer = await self._answer_from_data(user_message, data, context)
            else: answer = clean_model_answer(await self._ollama(self._general_prompt(user_message, context)))
            answer = answer or "I couldn't generate a response right now."
            await MessageRepository.add_message(conversation_id, user_id, "assistant", answer)
            return {"success": True, "response": answer, "tools_used": tools_used, "tool_results": [data] if data else [], "iterations": 1}
        except Exception as exc:
            logger.exception("Agent request failed")
            answer = "I couldn't complete that request right now. Please try again."
            await MessageRepository.add_message(conversation_id, user_id, "assistant", answer)
            return {"success": False, "response": answer, "error": str(exc), "tools_used": tools_used, "tool_results": [data] if data else [], "iterations": 1}

    async def stream_response(self, user_message: str, conversation_id: str, user_id: str = "default_user"):
        """Keep SSE UX while streaming only the final user-facing answer."""
        await MessageRepository.add_message(conversation_id, user_id, "user", user_message)
        try:
            context, data, tools_used, immediate = await self._prepare(user_message, conversation_id)
            if immediate: full = immediate
            elif data: full = await self._answer_from_data(user_message, data, context)
            else: full = clean_model_answer(await self._ollama(self._general_prompt(user_message, context)))
            full = full or "I couldn't generate a response right now."
            for i in range(0, len(full), 80):
                chunk = full[i:i + 80]
                yield {"type": "content", "content": chunk, "token": chunk, "done": False}
            await MessageRepository.add_message(conversation_id, user_id, "assistant", full)
            yield {"type": "done", "content": "", "token": "", "done": True, "full_response": full, "tools_used": tools_used}
        except Exception as exc:
            logger.exception("Streaming agent request failed")
            error_msg = "Sorry, I couldn't generate the response right now."
            await MessageRepository.add_message(conversation_id, user_id, "assistant", error_msg)
            yield {"type": "error", "content": error_msg, "token": error_msg, "done": True, "error": str(exc)}


ai_agent = AIAgent()
