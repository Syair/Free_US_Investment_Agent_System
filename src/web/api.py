from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
import os

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

@app.post("/api/start-trading")
async def start_trading(request: TradingRequest):
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
            datetime.strptime(request.start_date, '%Y-%m-%d')
            datetime.strptime(request.end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Validate num_of_news
        if request.num_of_news < 1 or request.num_of_news > 100:
            raise HTTPException(
                status_code=400, 
                detail="Number of news articles must be between 1 and 100"
            )

        # Configure portfolio
        portfolio = {
            "cash": request.initial_capital,
            "stock": 0
        }

        # Run the hedge fund
        result = run_hedge_fund(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            portfolio=portfolio,
            show_reasoning=request.show_reasoning,
            num_of_news=request.num_of_news
        )

        # Update trading state
        current_trading_state["is_trading"] = True
        current_trading_state["portfolio"] = result
        current_trading_state["last_update"] = datetime.now().isoformat()
        
        # Add to portfolio history
        current_trading_state["portfolio_history"].append({
            "timestamp": datetime.now().isoformat(),
            "portfolio_value": portfolio["cash"] + (portfolio["stock"] * result.get("current_price", 0)),
            "cash": portfolio["cash"],
            "stock_value": portfolio["stock"] * result.get("current_price", 0)
        })

        return {
            "status": "success",
            "result": result,
            "parameters": {
                "ticker": request.ticker,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "initial_capital": request.initial_capital,
                "show_reasoning": request.show_reasoning,
                "num_of_news": request.num_of_news
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/trading-status")
async def get_trading_status():
    if not current_trading_state["is_trading"]:
        raise HTTPException(status_code=404, detail="No active trading session")
    
    return {
        "status": "active" if current_trading_state["is_trading"] else "inactive",
        "result": current_trading_state["portfolio"],
        "last_update": current_trading_state["last_update"]
    }

@app.get("/api/trading-results", response_model=List[PortfolioData])
async def get_trading_results():
    if not current_trading_state["portfolio_history"]:
        raise HTTPException(status_code=404, detail="No trading history available")
    
    return current_trading_state["portfolio_history"]

@app.get("/api/agent-data", response_model=List[AgentData])
async def get_agent_data():
    if not current_trading_state["agent_data"]:
        raise HTTPException(status_code=404, detail="No agent data available")
    
    return current_trading_state["agent_data"]
