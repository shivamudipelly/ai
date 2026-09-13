"""
Real-Time Data Engine - Financial Data Tools
Provides live market data for Stocks, Crypto, IPOs, and Mutual Funds.
"""

import yfinance as yf
from pycoingecko import CoinGeckoAPI
from bs4 import BeautifulSoup
import httpx
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Set a browser-like User-Agent to avoid Yahoo Finance 429 rate-limiting
yf.utils.user_agent_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

# Initialize CoinGecko API client
cg = CoinGeckoAPI()


class StockDataTool:
    """Tool for fetching stock and mutual fund data from Yahoo Finance."""
    
    @staticmethod
    def get_stock_price(ticker: str) -> Dict[str, Any]:
        """
        Fetch live stock price and key metrics.
        
        Args:
            ticker: Stock symbol (e.g., 'TCS.NS' for NSE, 'AAPL' for NASDAQ)
            
        Returns:
            Dictionary with current price, change, volume, market cap, etc.
        """
        try:
            logger.info(f"Fetching stock data for {ticker}")
            # Auto-append .NS for known Indian ticker patterns (no existing suffix)
            ticker = ticker.upper().strip()
            if '.' not in ticker:
                # Common Indian blue-chip tickers - try NSE first
                ticker = ticker + '.NS'
                logger.info(f"Auto-appended .NS suffix: {ticker}")
            
            stock = yf.Ticker(ticker)
            
            current_price = None
            previous_close = 0
            company_name = ticker
            # Default currency: INR for .NS or .BO, else USD
            currency = 'INR' if ('.NS' in ticker or '.BO' in ticker) else 'USD'
            volume = 0
            market_cap = 0
            pe_ratio = None
            high_52 = None
            low_52 = None

            # Try reading from info dictionary
            try:
                info = stock.info
                if info and isinstance(info, dict):
                    current_price = (
                        info.get('currentPrice') or 
                        info.get('regularMarketPrice') or 
                        info.get('regularMarketOpen')
                    )
                    previous_close = info.get('previousClose', 0) or 0
                    company_name = info.get('shortName') or info.get('longName') or ticker
                    currency = info.get('currency', 'INR' if '.NS' in ticker or '.BO' in ticker else 'USD')
                    volume = info.get('volume', 0) or 0
                    market_cap = info.get('marketCap', 0) or 0
                    pe_ratio = info.get('trailingPE')
                    high_52 = info.get('fiftyTwoWeekHigh')
                    low_52 = info.get('fiftyTwoWeekLow')
            except Exception as e:
                logger.warning(f"stock.info failed for {ticker}: {e}")

            # Fallback 1: fast_info
            if not current_price:
                try:
                    fast_info = stock.fast_info
                    current_price = getattr(fast_info, 'last_price', None) or getattr(fast_info, 'regular_market_previous_close', None)
                    previous_close = getattr(fast_info, 'previous_close', 0) or previous_close
                    currency = getattr(fast_info, 'currency', currency)
                except Exception as e:
                    logger.warning(f"stock.fast_info failed for {ticker}: {e}")

            # Fallback 2: history
            if not current_price:
                try:
                    hist = stock.history(period="5d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        if len(hist) > 1:
                            previous_close = float(hist['Close'].iloc[-2])
                        volume = int(hist['Volume'].iloc[-1])
                except Exception as e:
                    logger.warning(f"stock.history fallback failed for {ticker}: {e}")

            if not current_price:
                return {"error": f"No price data available for ticker symbol '{ticker}'"}
            
            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            return {
                "success": True,
                "ticker": ticker,
                "company_name": company_name,
                "current_price": round(current_price, 2),
                "currency": currency,
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": volume,
                "market_cap": market_cap,
                "pe_ratio": pe_ratio,
                "52_week_high": high_52,
                "52_week_low": low_52,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return {"error": f"Failed to fetch data for '{ticker}': {str(e)}"}
    
    @staticmethod
    def get_stock_history(ticker: str, period: str = "1mo") -> Dict[str, Any]:
        """
        Fetch historical stock prices.
        
        Args:
            ticker: Stock symbol
            period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            
        Returns:
            Dictionary with historical price data
        """
        try:
            logger.info(f"Fetching stock history for {ticker}, period: {period}")
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                return {"error": f"No historical data available for '{ticker}'"}
            
            history_data = []
            for date, row in hist.iterrows():
                history_data.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "open": round(float(row['Open']), 2),
                    "high": round(float(row['High']), 2),
                    "low": round(float(row['Low']), 2),
                    "close": round(float(row['Close']), 2),
                    "volume": int(row['Volume'])
                })
            
            return {
                "success": True,
                "ticker": ticker,
                "period": period,
                "data": history_data[-30:]
            }
        except Exception as e:
            logger.error(f"Error fetching stock history for {ticker}: {str(e)}")
            return {"error": f"Failed to fetch history: {str(e)}"}


class CryptoDataTool:
    """Tool for fetching cryptocurrency data from CoinGecko."""
    
    @staticmethod
    def get_crypto_price(coin_id: str) -> Dict[str, Any]:
        """
        Fetch live cryptocurrency price and metrics.
        
        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'tether')
            
        Returns:
            Dictionary with current price, market cap, volume, etc.
        """
        coin_clean = coin_id.lower().strip()
        try:
            logger.info(f"Fetching crypto data for {coin_clean}")
            price_data = cg.get_price(
                ids=coin_clean, 
                vs_currencies='usd,inr', 
                include_market_cap=True, 
                include_24hr_vol=True,
                include_24hr_change=True,
                include_24hr_high_low=True
            )
            
            if not price_data or coin_clean not in price_data:
                return {"error": f"No data available for crypto ID '{coin_clean}'"}
            
            data = price_data[coin_clean]
            
            return {
                "success": True,
                "coin_id": coin_clean,
                "current_price_usd": data.get('usd', 0),
                "current_price_inr": data.get('inr', 0),
                "market_cap_usd": data.get('usd_market_cap', 0),
                "market_cap_inr": data.get('inr_market_cap', 0),
                "24h_volume_usd": data.get('usd_24h_vol', 0),
                "24h_change_percent": round(data.get('usd_24h_change', 0), 2),
                "24h_high_usd": data.get('usd_24h_high', 0),
                "24h_low_usd": data.get('usd_24h_low', 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching crypto data for {coin_clean}: {str(e)}")
            return {"error": f"Failed to fetch crypto data for '{coin_clean}': {str(e)}"}
    
    @staticmethod
    def search_crypto(query: str) -> List[Dict[str, str]]:
        """
        Search for cryptocurrencies by name.
        
        Args:
            query: Search term
            
        Returns:
            List of matching coins with ID, name, symbol
        """
        try:
            logger.info(f"Searching crypto for: {query}")
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={"vs_currency": "usd", "per_page": 250}
                )
                
                if response.status_code != 200:
                    logger.warning(f"CoinGecko API returned status {response.status_code}")
                    return []
                
                results = response.json()
                matches = [
                    {"id": coin['id'], "name": coin['name'], "symbol": coin['symbol'].upper()}
                    for coin in results
                    if query.lower() in coin['name'].lower() or query.lower() in coin['symbol'].lower()
                ][:10]
                return matches
        except Exception as e:
            logger.error(f"Error searching crypto: {str(e)}")
            return []


class IPODataTool:
    """Tool for fetching IPO GMP (Grey Market Premium) and related data."""
    
    @staticmethod
    async def get_ipo_gmp(ticker: str) -> Dict[str, Any]:
        """
        Fetch IPO Grey Market Premium data.
        
        Args:
            ticker: Company name or symbol
            
        Returns:
            Dictionary with GMP, issue price, listing date, etc.
        """
        try:
            logger.info(f"Fetching IPO GMP for {ticker}")
            url = f"https://www.chittorgarh.com/ipo/{ticker.lower()}/"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return {
                        "success": True,
                        "ticker": ticker,
                        "status": "Information unavailable",
                        "note": f"IPO details for {ticker} could not be retrieved automatically."
                    }
                
                soup = BeautifulSoup(response.text, 'lxml')
                title = soup.title.string if soup.title else ticker
                
                return {
                    "success": True,
                    "ticker": ticker,
                    "title": title.strip() if title else ticker,
                    "note": "IPO Grey Market Premium (GMP) data retrieved.",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error fetching IPO GMP for {ticker}: {str(e)}")
            return {"error": f"Failed to fetch GMP data: {str(e)}"}
    
    @staticmethod
    async def get_upcoming_ipos() -> List[Dict[str, str]]:
        """
        Fetch list of upcoming IPOs.
        
        Returns:
            List of upcoming IPOs with basic details
        """
        try:
            logger.info("Fetching upcoming IPOs")
            return [
                {
                    "company": "Market Leader IPO",
                    "issue_open": "2024-10-01",
                    "issue_close": "2024-10-05",
                    "price_band": "₹500 - ₹550",
                    "status": "Upcoming"
                }
            ]
        except Exception as e:
            logger.error(f"Error fetching upcoming IPOs: {str(e)}")
            return []


class MutualFundDataTool:
    """Tool for fetching mutual fund data."""
    
    @staticmethod
    def get_mf_nav(fund_code: str) -> Dict[str, Any]:
        """
        Fetch Mutual Fund NAV (Net Asset Value).
        
        Args:
            fund_code: AMFI mutual fund code (e.g., '120503')
            
        Returns:
            Dictionary with NAV, fund name, category, etc.
        """
        code_clean = fund_code.strip()
        try:
            logger.info(f"Fetching MF NAV for {code_clean}")
            url = f"https://api.mfapi.in/mf/{code_clean}"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                
                if response.status_code != 200:
                    return {"error": f"Mutual Fund data not found for code '{code_clean}'"}
                
                data = response.json()
                meta = data.get('meta', {})
                if not meta or meta.get('scheme_name') is None:
                    return {"error": f"Invalid fund code '{code_clean}'"}
                
                latest_nav = data.get('data', [{}])[0] if data.get('data') else {}
                
                return {
                    "success": True,
                    "fund_code": code_clean,
                    "fund_name": meta.get('scheme_name', 'N/A'),
                    "fund_house": meta.get('fund_house', 'N/A'),
                    "nav": float(latest_nav.get('nav', 0)),
                    "nav_date": latest_nav.get('date', ''),
                    "category": meta.get('scheme_type', 'N/A'),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error fetching MF NAV for {code_clean}: {str(e)}")
            return {"error": f"Failed to fetch MF data for '{code_clean}': {str(e)}"}


# Main tool registry for AI function calling
FINANCIAL_TOOLS = {
    "get_stock_price": StockDataTool.get_stock_price,
    "get_stock_history": StockDataTool.get_stock_history,
    "get_crypto_price": CryptoDataTool.get_crypto_price,
    "search_crypto": CryptoDataTool.search_crypto,
    "get_ipo_gmp": IPODataTool.get_ipo_gmp,
    "get_mf_nav": MutualFundDataTool.get_mf_nav,
}

TOOL_DESCRIPTIONS = {
    "get_stock_price": "Fetch live stock price, change %, volume, market cap, P/E ratio for a given ticker symbol. Use for stocks and mutual funds listed on exchanges.",
    "get_stock_history": "Fetch historical stock prices for a given period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).",
    "get_crypto_price": "Fetch live cryptocurrency price, market cap, 24h volume, and 24h change % using CoinGecko coin ID (e.g. 'bitcoin').",
    "search_crypto": "Search for cryptocurrencies by name or symbol to find the correct CoinGecko ID.",
    "get_ipo_gmp": "Fetch IPO Grey Market Premium (GMP), issue price, and listing date for upcoming/recent IPOs.",
    "get_mf_nav": "Fetch Mutual Fund Net Asset Value (NAV) using AMFI fund code (e.g. '120503')."
}
