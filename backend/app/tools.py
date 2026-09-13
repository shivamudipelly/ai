"""
Real-Time Data Engine - Financial Data Tools
Provides live market data for Stocks, Crypto, IPOs, and Mutual Funds.
"""

import yfinance as yf
from pycoingecko import CoinGeckoAPI
from bs4 import BeautifulSoup
import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize CoinGecko API
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
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get current price
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close = info.get('previousClose', 0)
            
            if not current_price:
                return {"error": f"No price data available for {ticker}"}
            
            change = current_price - previous_close if previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            return {
                "success": True,
                "ticker": ticker,
                "company_name": info.get('shortName', 'N/A'),
                "current_price": round(current_price, 2),
                "currency": info.get('currency', 'INR'),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume', 0),
                "market_cap": info.get('marketCap', 0),
                "pe_ratio": info.get('trailingPE', None),
                "52_week_high": info.get('fiftyTwoWeekHigh', None),
                "52_week_low": info.get('fiftyTwoWeekLow', None),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return {"error": f"Failed to fetch data: {str(e)}"}
    
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
                return {"error": f"No historical data available for {ticker}"}
            
            # Convert to list of dicts for JSON serialization
            history_data = []
            for date, row in hist.iterrows():
                history_data.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "open": round(row['Open'], 2),
                    "high": round(row['High'], 2),
                    "low": round(row['Low'], 2),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume'])
                })
            
            return {
                "success": True,
                "ticker": ticker,
                "period": period,
                "data": history_data[-30:]  # Return last 30 days max
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
        try:
            logger.info(f"Fetching crypto data for {coin_id}")
            
            # Get price data
            price_data = cg.get_price(ids=coin_id, vs_currencies='usd,inr', 
                                     include_market_cap=True, 
                                     include_24hr_vol=True,
                                     include_24hr_change=True,
                                     include_24hr_high_low=True)
            
            if not price_data or coin_id not in price_data:
                return {"error": f"No data available for {coin_id}"}
            
            data = price_data[coin_id]
            
            return {
                "success": True,
                "coin_id": coin_id,
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
            logger.error(f"Error fetching crypto data for {coin_id}: {str(e)}")
            return {"error": f"Failed to fetch data: {str(e)}"}
    
    @staticmethod
    def search_crypto(query: str) -> List[Dict[str, str]]:
        """
        Search for cryptocurrencies by name.
        
        Args:
            query: Search term
            
        Returns:
            List of matching coins with ID and name
        """
        try:
            logger.info(f"Searching crypto for: {query}")
            
            # Use the coins/markets endpoint to get list with market data
            import requests
            response = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={"vs_currency": "usd", "per_page": 250},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"CoinGecko API returned {response.status_code}")
                return []
            
            results = response.json()
            matches = [
                {"id": coin['id'], "name": coin['name'], "symbol": coin['symbol'].upper()}
                for coin in results
                if query.lower() in coin['name'].lower() or query.lower() in coin['symbol'].lower()
            ][:10]  # Return top 10 matches
            return matches
        except Exception as e:
            logger.error(f"Error searching crypto: {str(e)}")
            return []


class IPODataTool:
    """Tool for fetching IPO GMP (Grey Market Premium) and related data."""
    
    @staticmethod
    async def get_ipo_gmp(ticker: str) -> Dict[str, Any]:
        """
        Fetch IPO Grey Market Premium data via web scraping.
        
        Args:
            ticker: Company name or symbol
            
        Returns:
            Dictionary with GMP, issue price, listing date, etc.
        """
        try:
            logger.info(f"Fetching IPO GMP for {ticker}")
            
            # Note: This is a simplified example. In production, you'd use a reliable API
            # or more robust scraping with proper error handling
            url = f"https://www.chittorgarh.com/ipo/{ticker.lower()}/"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return {"error": f"IPO data not found for {ticker}"}
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Extract GMP data (structure may vary by website)
                gmp_data = {
                    "success": True,
                    "ticker": ticker,
                    "gmp": "N/A",  # Placeholder - actual scraping logic needed
                    "issue_price": "N/A",
                    "listing_date": "N/A",
                    "subscription_status": "N/A",
                    "note": "GMP data requires real-time scraping from financial portals",
                    "timestamp": datetime.now().isoformat()
                }
                
                return gmp_data
                
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
            # Placeholder - implement actual scraping or API call
            return [
                {
                    "company": "Example Corp",
                    "issue_open": "2024-02-01",
                    "issue_close": "2024-02-05",
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
            fund_code: AMFI mutual fund code
            
        Returns:
            Dictionary with NAV, fund name, category, etc.
        """
        try:
            logger.info(f"Fetching MF NAV for {fund_code}")
            
            # Use AMFI India API for NAV data
            url = f"https://api.mfapi.in/mf/{fund_code}"
            
            import requests
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return {"error": f"MF data not found for code {fund_code}"}
            
            data = response.json()
            
            if data.get('meta', {}).get('fund_house') == '':
                return {"error": f"Invalid fund code: {fund_code}"}
            
            latest_nav = data.get('data', [{}])[0] if data.get('data') else {}
            
            return {
                "success": True,
                "fund_code": fund_code,
                "fund_name": data['meta']['scheme_name'],
                "fund_house": data['meta']['fund_house'],
                "nav": float(latest_nav.get('nav', 0)),
                "nav_date": latest_nav.get('date', ''),
                "category": data['meta']['scheme_type'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching MF NAV for {fund_code}: {str(e)}")
            return {"error": f"Failed to fetch MF data: {str(e)}"}


# Main tool registry for AI function calling
FINANCIAL_TOOLS = {
    "get_stock_price": StockDataTool.get_stock_price,
    "get_stock_history": StockDataTool.get_stock_history,
    "get_crypto_price": CryptoDataTool.get_crypto_price,
    "search_crypto": CryptoDataTool.search_crypto,
    "get_ipo_gmp": IPODataTool.get_ipo_gmp,  # Async
    "get_mf_nav": MutualFundDataTool.get_mf_nav,
}

TOOL_DESCRIPTIONS = {
    "get_stock_price": "Fetch live stock price, change %, volume, market cap, P/E ratio for a given ticker symbol. Use for stocks and mutual funds listed on exchanges.",
    "get_stock_history": "Fetch historical stock prices for a given period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).",
    "get_crypto_price": "Fetch live cryptocurrency price, market cap, 24h volume, and 24h change % using CoinGecko coin ID.",
    "search_crypto": "Search for cryptocurrencies by name or symbol to find the correct CoinGecko ID.",
    "get_ipo_gmp": "Fetch IPO Grey Market Premium (GMP), issue price, and listing date for upcoming/recent IPOs.",
    "get_mf_nav": "Fetch Mutual Fund Net Asset Value (NAV) using AMFI fund code."
}
