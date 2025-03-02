from datetime import datetime, timedelta
import argparse
import pandas as pd
import os
import logging
import json
from typing import Dict, Any, Optional
from agents.valuation import valuation_agent
from agents.state import AgentState
from agents.sentiment import sentiment_agent
from agents.risk_manager import risk_management_agent
from agents.technicals import technical_analyst_agent
from agents.portfolio_manager import portfolio_management_agent
from agents.market_data import market_data_agent
from agents.fundamentals import fundamentals_agent
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file

def validate_dates(start_date: str, end_date: str) -> None:
    """Validate date strings and ranges"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start > end:
            raise ValueError("Start date cannot be after end date")
            
        if end > datetime.now():
            raise ValueError("End date cannot be in the future")
            
        if (end - start).days > 365:
            raise ValueError("Date range cannot exceed 1 year")
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError("Dates must be in YYYY-MM-DD format")
        raise

def validate_ticker(ticker: str) -> str:
    """Validate and normalize ticker symbol"""
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    return ticker.upper()

def validate_portfolio(portfolio: Dict[str, float]) -> None:
    """Validate portfolio structure and values"""
    if not isinstance(portfolio, dict):
        raise ValueError("Portfolio must be a dictionary")
        
    required_keys = {"cash", "stock"}
    if not all(key in portfolio for key in required_keys):
        raise ValueError(f"Portfolio must contain all required keys: {required_keys}")
        
    if portfolio["cash"] < 0:
        raise ValueError("Portfolio cash cannot be negative")
        
    if not isinstance(portfolio["stock"], (int, float)):
        raise ValueError("Portfolio stock must be a number")

def run_hedge_fund(
    ticker: str,
    start_date: str,
    end_date: str,
    portfolio: Dict[str, float],
    show_reasoning: bool = False,
    num_of_news: int = 5
) -> str:
    """
    Run the hedge fund trading system with error handling and validation
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        portfolio: Dictionary containing cash and stock positions
        show_reasoning: Whether to show agent reasoning
        num_of_news: Number of news articles to analyze
        
    Returns:
        Trading decision and analysis result as a string
    
    Raises:
        ValueError: For invalid input parameters
        Exception: For workflow execution errors
    """
    logger.info(f"Starting hedge fund execution for {ticker}")
    
    try:
        # Validate inputs
        ticker = validate_ticker(ticker)
        validate_dates(start_date, end_date)
        validate_portfolio(portfolio)
        
        if not 1 <= num_of_news <= 100:
            raise ValueError("Number of news articles must be between 1 and 100")
            
        # Prepare workflow input
        workflow_input = {
            "messages": [
                HumanMessage(
                    content="Make a trading decision based on the provided data.",
                )
            ],
            "data": {
                "ticker": ticker,
                "portfolio": portfolio,
                "start_date": start_date,
                "end_date": end_date,
                "num_of_news": num_of_news,
            },
            "metadata": {
                "show_reasoning": show_reasoning,
            }
        }
        
        logger.info("Executing workflow...")
        final_state = app.invoke(workflow_input)
        
        # Validate and format result
        result = final_state["messages"][-1].content
        if isinstance(result, str):
            try:
                # Try to parse as JSON for better formatting
                result_data = json.loads(result)
                result = json.dumps(result_data, indent=2)
            except json.JSONDecodeError:
                # If not JSON, return as is
                pass
                
        logger.info("Hedge fund execution completed successfully")
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in hedge fund execution: {str(e)}")
        raise

# Define the workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("market_data_agent", market_data_agent)
workflow.add_node("technical_analyst_agent", technical_analyst_agent)
workflow.add_node("fundamentals_agent", fundamentals_agent)
workflow.add_node("sentiment_agent", sentiment_agent)
workflow.add_node("risk_management_agent", risk_management_agent)
workflow.add_node("portfolio_management_agent", portfolio_management_agent)
workflow.add_node("valuation_agent", valuation_agent)

# Define the workflow
workflow.set_entry_point("market_data_agent")
workflow.add_edge("market_data_agent", "technical_analyst_agent")
workflow.add_edge("market_data_agent", "fundamentals_agent")
workflow.add_edge("market_data_agent", "sentiment_agent")
workflow.add_edge("market_data_agent", "valuation_agent")
workflow.add_edge("technical_analyst_agent", "risk_management_agent")
workflow.add_edge("fundamentals_agent", "risk_management_agent")
workflow.add_edge("sentiment_agent", "risk_management_agent")
workflow.add_edge("valuation_agent", "risk_management_agent")
workflow.add_edge("risk_management_agent", "portfolio_management_agent")
workflow.add_edge("portfolio_management_agent", END)

app = workflow.compile()

def process_tickers_from_file(
    file_path: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    show_reasoning: bool = False,
    initial_capital: float = 100000.0,
    num_of_news: int = 5
) -> pd.DataFrame:
    """
    Process multiple tickers from a file and return results as a DataFrame
    
    Args:
        file_path: Path to file containing tickers
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        show_reasoning: Whether to show agent reasoning
        initial_capital: Initial cash amount
        num_of_news: Number of news articles to analyze
        
    Returns:
        DataFrame containing analysis results
    """
    logger.info(f"Processing tickers from file: {file_path}")
    
    # Validate file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Tickers file not found: {file_path}")
    
    # Read tickers from file
    with open(file_path, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    
    if not tickers:
        raise ValueError("No valid tickers found in file")
    
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        start_date_obj = end_date_obj - timedelta(days=90)
        start_date = start_date_obj.strftime('%Y-%m-%d')
    
    # Validate dates once
    validate_dates(start_date, end_date)
    
    # Process each ticker
    results = []
    for ticker in tickers:
        logger.info(f"Processing ticker: {ticker}")
        try:
            portfolio = {
                "cash": initial_capital,
                "stock": 0
            }
            result = run_hedge_fund(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                portfolio=portfolio,
                show_reasoning=show_reasoning,
                num_of_news=num_of_news
            )
            results.append({
                'ticker': ticker,
                'analysis_date': end_date,
                'result': result,
                'status': 'success'
            })
            logger.info(f"Successfully processed {ticker}")
        except Exception as e:
            logger.error(f"Error processing {ticker}: {str(e)}")
            results.append({
                'ticker': ticker,
                'analysis_date': end_date,
                'result': f"Error: {str(e)}",
                'status': 'error'
            })
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run the hedge fund trading system')
    parser.add_argument('--ticker', type=str,
                        help='Stock ticker symbol')
    parser.add_argument('--tickers-file', type=str,
                        help='Path to file containing list of tickers (one per line)')
    parser.add_argument('--start-date', type=str,
                        help='Start date (YYYY-MM-DD). Defaults to 3 months before end date')
    parser.add_argument('--end-date', type=str,
                        help='End date (YYYY-MM-DD). Defaults to today')
    parser.add_argument('--show-reasoning', action='store_true',
                        help='Show reasoning from each agent')
    parser.add_argument('--initial-capital', type=float, default=100000.0,
                        help='Initial cash amount (default: 100,000)')
    parser.add_argument('--num-of-news', type=int, default=5,
                        help='Number of news articles to analyze for sentiment (default: 5)')

    args = parser.parse_args()

    try:
        # Set default dates if not provided
        if not args.end_date:
            args.end_date = datetime.now().strftime('%Y-%m-%d')

        if not args.start_date:
            end_date_obj = datetime.strptime(args.end_date, '%Y-%m-%d')
            start_date_obj = end_date_obj - timedelta(days=90)
            args.start_date = start_date_obj.strftime('%Y-%m-%d')

        # Validate inputs
        if args.ticker and args.tickers_file:
            raise ValueError("Cannot specify both --ticker and --tickers-file")
        if not args.ticker and not args.tickers_file:
            raise ValueError("Must specify either --ticker or --tickers-file")

        # Configure portfolio
        portfolio = {
            "cash": args.initial_capital,
            "stock": 0
        }

        if args.tickers_file:
            # Process multiple tickers
            results_df = process_tickers_from_file(
                file_path=args.tickers_file,
                start_date=args.start_date,
                end_date=args.end_date,
                show_reasoning=args.show_reasoning,
                initial_capital=args.initial_capital,
                num_of_news=args.num_of_news
            )
            
            # Create output directory
            os.makedirs('analysis_results', exist_ok=True)
            
            # Export to Excel
            output_file = f'analysis_results/hedge_fund_analysis_{datetime.now().strftime("%Y%m%d")}.xlsx'
            results_df.to_excel(output_file, index=False)
            logger.info(f"Results exported to: {output_file}")
            print(f"\nResults exported to: {output_file}")
        else:
            # Process single ticker
            result = run_hedge_fund(
                ticker=args.ticker,
                start_date=args.start_date,
                end_date=args.end_date,
                portfolio=portfolio,
                show_reasoning=args.show_reasoning,
                num_of_news=args.num_of_news
            )
            print("\nFinal Result:")
            print(result)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"\nError: {str(e)}")
        exit(1)
