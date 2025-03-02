from langchain_core.messages import HumanMessage
from tools.openrouter_config import get_chat_completion
from agents.state import AgentState
from tools.api import get_financial_metrics, get_financial_statements, get_insider_trades, get_market_data, get_price_history
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def market_data_agent(state: AgentState):
    """Responsible for gathering and preprocessing market data"""
    messages = state["messages"]
    data = state["data"]

    # Get current_date from state
    current_date = data.get("current_date") or data["end_date"]

    # Ensure at least one year of historical data for technical analysis
    current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
    min_start_date = (current_date_obj - timedelta(days=365)).strftime('%Y-%m-%d')

    # Use earlier of original_start_date and min_start_date
    original_start_date = data["start_date"]
    start_date = min(original_start_date, min_start_date) if original_start_date else min_start_date
    logger.info(f"Original start date: {original_start_date}, Min start date: {min_start_date}, Start date: {start_date}")
    
    ticker = data["ticker"]
    logger.info(f"Fetching market data for {ticker} from {start_date} to {current_date}")

    try:
        # Get price history
        prices = get_price_history(ticker, start_date, current_date)
        if not prices:
            logger.warning(f"No price history found for {ticker}")
            prices = []
    except Exception as e:
        logger.error(f"Error getting price history for {ticker}: {str(e)}")
        prices = []

    try:
        # Get financial metrics
        financial_metrics = get_financial_metrics(ticker)
        if not financial_metrics:
            logger.warning(f"No financial metrics found for {ticker}")
            financial_metrics = [{
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
        logger.error(f"Error getting financial metrics for {ticker}: {str(e)}")
        financial_metrics = [{
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

    try:
        # Get financial statements
        financial_line_items = get_financial_statements(ticker)
        if not financial_line_items:
            logger.warning(f"No financial statements found for {ticker}")
            default_item = {
                "free_cash_flow": 0,
                "net_income": 0,
                "depreciation_and_amortization": 0,
                "capital_expenditure": 0,
                "working_capital": 0
            }
            financial_line_items = [default_item, default_item]
    except Exception as e:
        logger.error(f"Error getting financial statements for {ticker}: {str(e)}")
        default_item = {
            "free_cash_flow": 0,
            "net_income": 0,
            "depreciation_and_amortization": 0,
            "capital_expenditure": 0,
            "working_capital": 0
        }
        financial_line_items = [default_item, default_item]

    try:
        # Get insider trades
        insider_trades = get_insider_trades(ticker)
        if not insider_trades:
            logger.warning(f"No insider trades found for {ticker}")
            insider_trades = []
    except Exception as e:
        logger.error(f"Error getting insider trades for {ticker}: {str(e)}")
        insider_trades = []

    try:
        # Get market data
        market_data = get_market_data(ticker)
        if not market_data:
            logger.warning(f"No market data found for {ticker}")
            market_data = {
                "market_cap": 0,
                "volume": 0,
                "average_volume": 0,
                "fifty_two_week_high": 0,
                "fifty_two_week_low": 0,
                "vix": 0,
                "vix_50d_avg": 0,
                "treasury_yield": 0
            }
    except Exception as e:
        logger.error(f"Error getting market data for {ticker}: {str(e)}")
        market_data = {
            "market_cap": 0,
            "volume": 0,
            "average_volume": 0,
            "fifty_two_week_high": 0,
            "fifty_two_week_low": 0,
            "vix": 0,
            "vix_50d_avg": 0,
            "treasury_yield": 0
        }

    return {
        "messages": messages,
        "data": {
            **data,
            "prices": prices,
            "start_date": start_date,
            "end_date": current_date,
            "current_date": current_date,
            "financial_metrics": financial_metrics,
            "financial_line_items": financial_line_items,
            "insider_trades": insider_trades,
            "market_cap": market_data.get("market_cap", 0),
            "market_data": market_data,
        }
    }
