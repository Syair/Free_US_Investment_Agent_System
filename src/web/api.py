from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
import os
import logging
import traceback
import json
from json.decoder import JSONDecodeError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import run_hedge_fund

app = FastAPI(title="Investment Agent System API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TradingRequest(BaseModel):
    ticker: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0
    show_reasoning: bool = False
    num_of_news: int = 5

    @validator('ticker')
    def validate_ticker(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('Ticker must be a non-empty string')
        return v.upper()

    @validator('initial_capital')
    def validate_capital(cls, v):
        if v <= 0:
            raise ValueError('Initial capital must be greater than 0')
        return v

    @validator('num_of_news')
    def validate_news_count(cls, v):
        if not 1 <= v <= 100:
            raise ValueError('Number of news articles must be between 1 and 100')
        return v

class AgentData(BaseModel):
    agent_name: str
    analysis: str
    decision: str
    confidence: float
    metrics: Optional[Dict[str, float]] = None

class PortfolioData(BaseModel):
    timestamp: str
    portfolio_value: float
    cash: float
    stock_value: float

# Store current trading state
current_trading_state = {
    "is_trading": False,
    "portfolio": None,
    "last_update": None,
    "agent_data": [],
    "portfolio_history": []
}

def format_error_response(error: Exception, status_code: int) -> Dict:
    """Format error response with additional details"""
    error_type = type(error).__name__
    error_details = {
        "error_type": error_type,
        "message": str(error),
        "status_code": status_code
    }
    
    if hasattr(error, 'detail'):
        error_details["detail"] = error.detail
        
    return error_details

@app.post("/api/start-trading")
async def start_trading(request: TradingRequest, raw_request: Request):
    logger.info(f"Received trading request: {request.dict()}")
    logger.info(f"Request headers: {dict(raw_request.headers)}")
    
    try:
        # Set default dates if not provided
        if not request.end_date:
            request.end_date = datetime.now().strftime('%Y-%m-%d')

        if not request.start_date:
            end_date_obj = datetime.strptime(request.end_date, '%Y-%m-%d')
            start_date_obj = end_date_obj - timedelta(days=90)
            request.start_date = start_date_obj.strftime('%Y-%m-%d')

        # Validate dates
        try:
            start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
            
            # Check if dates are in the future
            if start_date > datetime.now() or end_date > datetime.now():
                raise HTTPException(
                    status_code=400,
                    detail="Dates cannot be in the future"
                )
                
            # Check if start date is after end date
            if start_date > end_date:
                raise HTTPException(
                    status_code=400,
                    detail="Start date cannot be after end date"
                )
                
            # Check if date range is too large
            if (end_date - start_date).days > 365:
                raise HTTPException(
                    status_code=400,
                    detail="Date range cannot exceed 1 year"
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        # Configure portfolio
        portfolio = {
            "cash": request.initial_capital,
            "stock": 0
        }

        logger.info("Starting hedge fund execution...")
        try:
            # Run the hedge fund
            result = run_hedge_fund(
                ticker=request.ticker,
                start_date=request.start_date,
                end_date=request.end_date,
                portfolio=portfolio,
                show_reasoning=request.show_reasoning,
                num_of_news=request.num_of_news
            )
            logger.info(f"Hedge fund execution completed. Result: {result}")
        except Exception as e:
            error_msg = str(e)
            status_code = 500
            
            # Handle specific error types
            if "Too Many Requests" in error_msg:
                status_code = 429
                error_msg = "Rate limit exceeded. Please try again later."
            elif "JSONDecodeError" in error_msg or "Expecting value" in error_msg:
                status_code = 502
                error_msg = "Unable to fetch market data. Please try again later."
            elif "possibly delisted" in error_msg:
                status_code = 404
                error_msg = f"Stock {request.ticker} not found or possibly delisted."
                
            logger.error(f"Error in run_hedge_fund: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status_code,
                detail=error_msg
            )

        logger.info("Parsing result...")
        try:
            if isinstance(result, str):
                result_data = json.loads(result)
            else:
                result_data = result
                
            logger.info(f"Parsed result data: {result_data}")
            if not isinstance(result_data, dict):
                raise ValueError("Result is not a dictionary")
        except (JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing result: {e}")
            result_data = {
                "decision": str(result),
                "reasoning": "",
                "portfolio": portfolio,
                "current_price": 0,
                "agents": []
            }

        # Update trading state
        current_trading_state["is_trading"] = True
        current_trading_state["portfolio"] = result_data
        current_trading_state["last_update"] = datetime.now().isoformat()
        
        # Update agent data if available
        if "agents" in result_data:
            current_trading_state["agent_data"] = result_data["agents"]
        
        # Add to portfolio history
        portfolio_value = result_data["portfolio"]["cash"] + (
            result_data["portfolio"]["stock"] * result_data.get("current_price", 0)
        )
        current_trading_state["portfolio_history"].append({
            "timestamp": datetime.now().isoformat(),
            "portfolio_value": portfolio_value,
            "cash": result_data["portfolio"]["cash"],
            "stock_value": result_data["portfolio"]["stock"] * result_data.get("current_price", 0)
        })

        return {
            "status": "success",
            "result": result_data,
            "parameters": {
                "ticker": request.ticker,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "initial_capital": request.initial_capital,
                "show_reasoning": request.show_reasoning,
                "num_of_news": request.num_of_news
            }
        }

    except HTTPException as e:
        error_response = format_error_response(e, e.status_code)
        logger.error(f"HTTP Exception: {error_response}")
        raise HTTPException(status_code=e.status_code, detail=error_response)
    except Exception as e:
        error_response = format_error_response(e, 500)
        logger.error(f"Unexpected error: {error_response}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_response)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/trading-status")
async def get_trading_status():
    default_portfolio = {
        "decision": "No trading decision yet",
        "reasoning": "Trading session has not started",
        "portfolio": {
            "cash": 0,
            "stock": 0
        }
    }
    
    default_parameters = {
        "ticker": "",
        "start_date": datetime.now().strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d'),
        "initial_capital": 0
    }

    return {
        "status": "inactive" if not current_trading_state["is_trading"] else "active",
        "result": current_trading_state["portfolio"] or default_portfolio,
        "parameters": default_parameters,
        "last_update": current_trading_state["last_update"] or datetime.now().isoformat()
    }

@app.get("/api/trading-results", response_model=List[PortfolioData])
async def get_trading_results():
    if not current_trading_state["portfolio_history"]:
        # Return initial sample data points
        now = datetime.now()
        initial_data = [
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "portfolio_value": 100000.0,
                "cash": 100000.0,
                "stock_value": 0.0
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "portfolio_value": 100000.0,
                "cash": 100000.0,
                "stock_value": 0.0
            },
            {
                "timestamp": now.isoformat(),
                "portfolio_value": 100000.0,
                "cash": 100000.0,
                "stock_value": 0.0
            }
        ]
        return initial_data
    
    return current_trading_state["portfolio_history"]

@app.get("/api/agent-data", response_model=List[AgentData])
async def get_agent_data():
    if not current_trading_state["agent_data"]:
        # Return initial sample data
        initial_agents = [
            {
                "agent_name": "market_data_agent",
                "analysis": "Waiting for market data analysis",
                "decision": "No decision yet",
                "confidence": 0.0,
                "metrics": {
                    "volume": 0,
                    "price_change": 0.0,
                    "volatility": 0.0
                }
            },
            {
                "agent_name": "technical_agent",
                "analysis": "Waiting for technical analysis",
                "decision": "No decision yet",
                "confidence": 0.0,
                "metrics": {
                    "rsi": 0.0,
                    "macd": 0.0,
                    "moving_average": 0.0
                }
            },
            {
                "agent_name": "sentiment_agent",
                "analysis": "Waiting for sentiment analysis",
                "decision": "No decision yet",
                "confidence": 0.0,
                "metrics": {
                    "sentiment_score": 0.0,
                    "news_count": 0,
                    "market_sentiment": 0.0
                }
            }
        ]
        return initial_agents
    
    return current_trading_state["agent_data"]
