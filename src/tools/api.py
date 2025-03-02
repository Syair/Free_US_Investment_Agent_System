from typing import Dict, Any, List, Optional
import pandas as pd
import yfinance as yf
import datetime
import random
import json
import os
import pathlib
import logging
import time
from functools import wraps

logger = logging.getLogger('api')
logger.setLevel(logging.DEBUG)

# Cache directory setup
CACHE_DIR = pathlib.Path("cache")
CACHE_DIRS = {
    "financial_metrics": CACHE_DIR / "financial_metrics",
    "financial_statements": CACHE_DIR / "financial_statements",
    "insider_trades": CACHE_DIR / "insider_trades",
    "market_data": CACHE_DIR / "market_data",
    "options_data": CACHE_DIR / "options_data",
    "price_history": CACHE_DIR / "price_history"
}

# Create cache directories if they don't exist
for dir_path in CACHE_DIRS.values():
    dir_path.mkdir(parents=True, exist_ok=True)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        raise e
                    wait = (backoff_in_seconds * 2 ** x + 
                           random.uniform(0, 1))
                    time.sleep(wait)
                    x += 1
                    logger.warning(f"Retrying {func.__name__} after error: {str(e)}")
        return wrapper
    return decorator

def read_cache(cache_type: str, ticker: str, date: Optional[str] = None) -> Optional[Dict]:
    """Read data from cache"""
    cache_dir = CACHE_DIRS[cache_type]
    if date:
        cache_file = cache_dir / ticker / f"{date}.json"
    else:
        cache_file = cache_dir / f"{ticker}.json"
    
    try:
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading cache for {ticker}: {e}")
    return None

def write_cache(cache_type: str, ticker: str, data: Any, date: Optional[str] = None):
    """Write data to cache"""
    cache_dir = CACHE_DIRS[cache_type]
    if date:
        ticker_dir = cache_dir / ticker
        ticker_dir.mkdir(exist_ok=True)
        cache_file = ticker_dir / f"{date}.json"
    else:
        cache_file = cache_dir / f"{ticker}.json"
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error writing cache for {ticker}: {e}")

@retry_with_backoff(retries=3)
def get_financial_metrics(ticker: str) -> Dict[str, Any]:
    logger.info(f"Getting financial metrics for {ticker}")

    # Check cache first
    cached_data = read_cache("financial_metrics", ticker)
    if cached_data:
        return cached_data

    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        financials = stock.financials

        if financials.empty:
            raise ValueError("No financial data available")

        # Get latest financial data date
        latest_date = financials.columns[0]
        days_since_update = (datetime.now() - latest_date).days

        # Get latest financials
        latest_financials = financials.iloc[:, 0]

        # Calculate growth rates
        revenue_growth = 0
        earnings_growth = 0
        if len(financials.columns) > 1:
            prev_financials = financials.iloc[:, 1]
            revenue_growth = (latest_financials.get("Total Revenue", 0) - prev_financials.get(
                "Total Revenue", 0)) / prev_financials.get("Total Revenue", 1)
            earnings_growth = (latest_financials.get("Net Income", 0) - prev_financials.get(
                "Net Income", 0)) / prev_financials.get("Net Income", 1)

        # Build metrics
        metrics = {
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("forwardPE", 0),
            "price_to_book": info.get("priceToBook", 0),
            "dividend_yield": info.get("dividendYield", 0),
            "revenue": latest_financials.get("Total Revenue", 0),
            "net_income": latest_financials.get("Net Income", 0),
            "return_on_equity": info.get("returnOnEquity", 0),
            "net_margin": info.get("profitMargins", 0),
            "operating_margin": info.get("operatingMargins", 0),
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "book_value_growth": 0,  # Not provided by yfinance
            "current_ratio": info.get("currentRatio", 0),
            "debt_to_equity": info.get("debtToEquity", 0),
            "free_cash_flow_per_share": info.get("freeCashflow", 0) / info.get("sharesOutstanding", 1) if info.get("sharesOutstanding", 0) > 0 else 0,
            "earnings_per_share": info.get("trailingEps", 0),
            "price_to_earnings_ratio": info.get("forwardPE", 0),
            "price_to_book_ratio": info.get("priceToBook", 0),
            "price_to_sales_ratio": info.get("priceToSalesTrailing12Months", 0),
            "data_timestamp": latest_date.strftime("%Y-%m-%d"),
            "days_since_update": days_since_update,
            "is_data_recent": days_since_update <= 100
        }

        result = [metrics]
        # Save to cache
        write_cache("financial_metrics", ticker, result)
        return result

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Data error for {ticker}: {str(e)}")
        return [{
            "market_cap": 0,
            "pe_ratio": 0,
            "price_to_book": 0,
            "dividend_yield": 0,
            "revenue": 0,
            "net_income": 0,
            "return_on_equity": 0,
            "net_margin": 0,
            "operating_margin": 0,
            "revenue_growth": 0,
            "earnings_growth": 0,
            "book_value_growth": 0,
            "current_ratio": 0,
            "debt_to_equity": 0,
            "free_cash_flow_per_share": 0,
            "earnings_per_share": 0,
            "price_to_earnings_ratio": 0,
            "price_to_book_ratio": 0,
            "price_to_sales_ratio": 0,
            "data_timestamp": None,
            "days_since_update": None,
            "is_data_recent": False
        }]
    except Exception as e:
        logger.error(f"Unexpected error getting financial metrics for {ticker}: {str(e)}")
        raise

@retry_with_backoff(retries=3)
def get_financial_statements(ticker: str) -> Dict[str, Any]:
    logger.info(f"Getting financial statements for {ticker}")

    # Check cache first
    cached_data = read_cache("financial_statements", ticker)
    if cached_data:
        return cached_data

    stock = yf.Ticker(ticker)

    try:
        financials = stock.financials
        cash_flow = stock.cashflow
        balance = stock.balance_sheet

        # Prepare last two quarters data
        line_items = []
        for i in range(min(2, len(financials.columns))):
            current_financials = financials.iloc[:, i]
            current_cash_flow = cash_flow.iloc[:, i]
            current_balance = balance.iloc[:, i]

            line_item = {
                "free_cash_flow": current_cash_flow.get("Free Cash Flow", 0),
                "net_income": current_financials.get("Net Income", 0),
                "depreciation_and_amortization": current_cash_flow.get("Depreciation", 0),
                "capital_expenditure": current_cash_flow.get("Capital Expenditure", 0),
                "working_capital": (
                    current_balance.get("Total Current Assets", 0) -
                    current_balance.get("Total Current Liabilities", 0)
                )
            }
            line_items.append(line_item)

        # If only one quarter, duplicate it
        if len(line_items) == 1:
            line_items.append(line_items[0])

        # Save to cache
        write_cache("financial_statements", ticker, line_items)
        return line_items

    except Exception as e:
        logger.warning(f"Error getting financial statements: {e}")
        default_item = {
            "free_cash_flow": 0,
            "net_income": 0,
            "depreciation_and_amortization": 0,
            "capital_expenditure": 0,
            "working_capital": 0
        }
        return [default_item, default_item]

@retry_with_backoff(retries=3)
def get_insider_trades(ticker: str) -> List[Dict[str, Any]]:
    logger.info(f"Getting insider trades for {ticker}")

    # Check cache first
    cached_data = read_cache("insider_trades", ticker)
    if cached_data:
        return cached_data

    stock = yf.Ticker(ticker)
    try:
        insider_trades = stock.insider_trades
        if insider_trades is None or insider_trades.empty:
            return []

        trades = []
        for _, trade in insider_trades.iterrows():
            trades.append({
                "transaction_shares": int(trade.get("Shares", 0)),
                "transaction_type": "BUY" if trade.get("Shares", 0) > 0 else "SELL",
                "value": float(trade.get("Value", 0)),
                "date": trade.name.strftime("%Y-%m-%d") if hasattr(trade.name, "strftime") else str(trade.name)
            })

        trades = sorted(trades, key=lambda x: x["date"], reverse=True)
        # Save to cache
        write_cache("insider_trades", ticker, trades)
        return trades
    except Exception as e:
        logger.warning(f"Error getting insider trades: {e}")
        return []

@retry_with_backoff(retries=3)
def get_market_data(ticker: str) -> Dict[str, Any]:
    logger.info(f"Getting market data for {ticker}")

    # Check cache first
    cached_data = read_cache("market_data", ticker)
    if cached_data:
        return cached_data

    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Get VIX data
    try:
        vix = yf.Ticker("^VIX")
        vix_info = vix.history(period="5d")
        current_vix = float(vix_info['Close'].iloc[-1])
        vix_50d_avg = float(vix_info['Close'].rolling(window=50).mean().iloc[-1])
    except Exception as e:
        logger.warning(f"Error getting VIX data: {e}")
        current_vix = 0
        vix_50d_avg = 0
    
    # Get Treasury yield
    try:
        treasury = yf.Ticker("^TNX")
        treasury_info = treasury.history(period="5d")
        treasury_yield = float(treasury_info['Close'].iloc[-1])
    except Exception as e:
        logger.warning(f"Error getting Treasury data: {e}")
        treasury_yield = 0

    result = {
        "market_cap": info.get("marketCap", 0),
        "volume": info.get("volume", 0),
        "average_volume": info.get("averageVolume", 0),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
        "vix": current_vix,
        "vix_50d_avg": vix_50d_avg,
        "treasury_yield": treasury_yield
    }
    # Save to cache
    write_cache("market_data", ticker, result)
    return result

@retry_with_backoff(retries=3)
def get_options_data(ticker: str) -> Dict[str, Any]:
    logger.info(f"Getting options data for {ticker}")

    # Check cache first
    cached_data = read_cache("options_data", ticker)
    if cached_data:
        return cached_data

    stock = yf.Ticker(ticker)
    
    try:
        # Get options chain for nearest expiration
        expirations = stock.options
        if not expirations:
            return {"error": "No options data available"}
            
        nearest_expiry = expirations[0]
        opt = stock.option_chain(nearest_expiry)
        
        # Calculate put/call ratio
        total_call_volume = opt.calls['volume'].sum()
        total_put_volume = opt.puts['volume'].sum()
        put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        
        # Calculate average implied volatility
        avg_call_iv = opt.calls['impliedVolatility'].mean()
        avg_put_iv = opt.puts['impliedVolatility'].mean()
        
        # Get volume and open interest
        call_oi = opt.calls['openInterest'].sum()
        put_oi = opt.puts['openInterest'].sum()
        
        result = {
            "expiration_date": nearest_expiry,
            "put_call_ratio": put_call_ratio,
            "avg_call_iv": float(avg_call_iv),
            "avg_put_iv": float(avg_put_iv),
            "total_call_volume": int(total_call_volume),
            "total_put_volume": int(total_put_volume),
            "call_open_interest": int(call_oi),
            "put_open_interest": int(put_oi)
        }
        # Save to cache
        write_cache("options_data", ticker, result)
        return result
    except Exception as e:
        logger.warning(f"Error getting options data: {e}")
        return {
            "expiration_date": None,
            "put_call_ratio": 0,
            "avg_call_iv": 0,
            "avg_put_iv": 0,
            "total_call_volume": 0,
            "total_put_volume": 0,
            "call_open_interest": 0,
            "put_open_interest": 0
        }

@retry_with_backoff(retries=3)
def get_price_history(ticker: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    logger.info(f"Getting price history for {ticker} with start date {start_date} and end date {end_date}")

    # Default to last 3 months if no dates provided
    if not end_date:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    if not start_date:
        start_date = end_date - datetime.timedelta(days=90)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")

    # Format dates for cache key
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    cache_key = f"{start_str}_{end_str}"

    # Check cache first
    cached_data = read_cache("price_history", ticker, cache_key)
    if cached_data:
        return cached_data

    stock = yf.Ticker(ticker)
    # Get historical data
    df = stock.history(period=start_date, end=end_date, interval="1d")

    # Convert to list format
    prices = []
    for date, row in df.iterrows():
        price_dict = {
            "time": date.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"])
        }
        prices.append(price_dict)

    # Save to cache
    write_cache("price_history", ticker, prices, cache_key)
    return prices

def prices_to_df(prices: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert price list to DataFrame"""
    df = pd.DataFrame(prices)
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df

@retry_with_backoff(retries=3)
def get_price_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    logger.info(f"Getting price data for {ticker}")
    
    try:
        # Check cache first
        cache_key = f"{start_date}_{end_date}"
        cached_data = read_cache("price_history", ticker, cache_key)
        if cached_data:
            return pd.DataFrame(cached_data).set_index("time")

        # Convert date strings to datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Extend end date if single day query
        if start == end:
            end = start + datetime.timedelta(days=1)

        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)

        if df.empty:
            logger.warning(
                f"No price data found for {ticker} between {start_date} and {end_date}")
            return pd.DataFrame(columns=["Date", "open", "high", "low", "close", "volume"])

        # Reset index to make date a column
        df = df.reset_index()

        # Ensure date has no timezone and format as string
        df["Date"] = df["Date"].dt.tz_localize(None).dt.strftime("%Y-%m-%d")

        # Rename columns to match expected format
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })

        # Select needed columns and set index
        df = df[["Date", "open", "high", "low", "close", "volume"]]
        df = df.set_index("Date")

        # Convert to list format for caching
        prices = []
        for date, row in df.iterrows():
            price_dict = {
                "time": date,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"])
            }
            prices.append(price_dict)

        # Save to cache
        write_cache("price_history", ticker, prices, cache_key)

        # Return DataFrame
        return pd.DataFrame(prices).set_index("time")

    except Exception as e:
        logger.error(f"Error in get_price_data for {ticker}: {str(e)}")
        return pd.DataFrame(columns=["Date", "open", "high", "low", "close", "volume"])
