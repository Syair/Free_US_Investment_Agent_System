from langchain_core.messages import HumanMessage
from agents.state import AgentState, show_agent_reasoning
from tools.news_crawler import get_stock_news, get_news_sentiment
from tools.openrouter_config import get_chat_completion
from tools.api import get_market_data, get_options_data, get_price_history
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any


def calculate_fear_greed_index(price_history, market_data) -> float:
    """Calculate Fear & Greed index based on multiple market indicators"""
    scores = []
    
    # 1. Market Momentum (Price vs 125-day MA)
    prices_df = pd.DataFrame(price_history)
    current_price = prices_df['close'].iloc[-1]
    ma_125 = prices_df['close'].rolling(window=125).mean().iloc[-1]
    momentum_score = min(100, max(0, ((current_price / ma_125 - 1) * 100 + 50)))
    scores.append(momentum_score)
    
    # 2. Market Volatility (VIX)
    current_vix = market_data['vix']
    vix_50d_avg = market_data['vix_50d_avg']
    if current_vix and vix_50d_avg:
        vix_score = min(100, max(0, (1 - current_vix / vix_50d_avg) * 100))
        scores.append(vix_score)
    
    # 3. Market Volume
    current_volume = market_data['volume']
    avg_volume = market_data['average_volume']
    if avg_volume > 0:
        volume_ratio = current_volume / avg_volume
        volume_score = min(100, max(0, (volume_ratio - 0.5) * 100))
        scores.append(volume_score)
    
    # 4. Safe Haven Demand (Treasury Yield)
    treasury_yield = market_data['treasury_yield']
    if treasury_yield:
        # Higher yields generally indicate less fear
        treasury_score = min(100, max(0, treasury_yield * 10))
        scores.append(treasury_score)
    
    # Calculate final score (0-100)
    if scores:
        return float(np.mean(scores))
    return 50.0  # Default neutral score

def analyze_options_sentiment(options_data) -> Dict[str, Any]:
    """Analyze options market sentiment"""
    if not options_data or "error" in options_data:
        return {"signal": "neutral", "confidence": 0.5}
        
    # Analyze put/call ratio
    put_call_ratio = options_data['put_call_ratio']
    
    # Analyze implied volatility skew
    iv_skew = options_data['avg_put_iv'] / options_data['avg_call_iv'] if options_data['avg_call_iv'] > 0 else 1
    
    # Calculate sentiment score
    if put_call_ratio > 1.5 or iv_skew > 1.2:
        signal = "bearish"
        confidence = min(0.9, max(put_call_ratio / 3, iv_skew / 2))
    elif put_call_ratio < 0.7 or iv_skew < 0.8:
        signal = "bullish"
        confidence = min(0.9, max(1 - put_call_ratio, 1 - iv_skew))
    else:
        signal = "neutral"
        confidence = 0.5
        
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "put_call_ratio": put_call_ratio,
            "iv_skew": iv_skew
        }
    }

def analyze_insider_sentiment(insider_trades) -> Dict[str, Any]:
    """Analyze insider trading sentiment"""
    if not insider_trades:
        return {"signal": "neutral", "confidence": 0.5}
    
    # Calculate net buying vs selling
    total_buy_value = sum(trade['value'] for trade in insider_trades 
                         if trade['transaction_type'] == 'BUY')
    total_sell_value = sum(trade['value'] for trade in insider_trades 
                          if trade['transaction_type'] == 'SELL')
    
    if total_buy_value == 0 and total_sell_value == 0:
        return {"signal": "neutral", "confidence": 0.5}
    
    # Calculate ratio and determine sentiment
    ratio = total_buy_value / (total_buy_value + total_sell_value)
    
    if ratio > 0.7:
        signal = "bullish"
        confidence = min(0.9, ratio)
    elif ratio < 0.3:
        signal = "bearish"
        confidence = min(0.9, 1 - ratio)
    else:
        signal = "neutral"
        confidence = 0.5
        
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "buy_value": total_buy_value,
            "sell_value": total_sell_value,
            "buy_ratio": ratio
        }
    }

def sentiment_agent(state: AgentState):
    """Analyzes market sentiment and generates trading signals using multiple indicators"""
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    symbol = data["ticker"]
    current_date = data["end_date"]  # 使用回测的当前日期

    # Get number of news from command line args, default to 5
    num_of_news = data.get("num_of_news", 5)

    # Get news sentiment
    news_list = get_stock_news(symbol, date=current_date, max_news=num_of_news)
    cutoff_date = datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=7)
    recent_news = [news for news in news_list
                   if datetime.strptime(news['publish_time'], '%Y-%m-%d %H:%M:%S') > cutoff_date]
    news_sentiment = get_news_sentiment(recent_news, date=current_date, num_of_news=num_of_news)

    # Get market data and calculate Fear & Greed index
    market_data = get_market_data(symbol)
    price_history = get_price_history(symbol, 
                                    (datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=180)).strftime("%Y-%m-%d"),
                                    current_date)
    fear_greed_score = calculate_fear_greed_index(price_history, market_data)
    
    # Get options sentiment
    options_data = get_options_data(symbol)
    options_sentiment = analyze_options_sentiment(options_data)
    
    # Get insider trading sentiment
    insider_trades = data.get("insider_trades", [])
    insider_sentiment = analyze_insider_sentiment(insider_trades)
    
    # Combine all sentiment signals
    sentiment_signals = {
        "news": {
            "score": news_sentiment,
            "weight": 0.3
        },
        "fear_greed": {
            "score": fear_greed_score / 100,  # Normalize to 0-1
            "weight": 0.3
        },
        "options": {
            "score": options_sentiment["confidence"],
            "weight": 0.2
        },
        "insider": {
            "score": insider_sentiment["confidence"],
            "weight": 0.2
        }
    }
    
    # Calculate weighted average sentiment
    total_weight = sum(s["weight"] for s in sentiment_signals.values())
    weighted_sentiment = sum(s["score"] * s["weight"] for s in sentiment_signals.values()) / total_weight
    
    # Generate trading signal and confidence
    if weighted_sentiment >= 0.6:
        signal = "bullish"
        confidence = str(round(weighted_sentiment * 100)) + "%"
    elif weighted_sentiment <= 0.4:
        signal = "bearish"
        confidence = str(round((1 - weighted_sentiment) * 100)) + "%"
    else:
        signal = "neutral"
        confidence = str(round((1 - abs(weighted_sentiment - 0.5) * 2) * 100)) + "%"
    
    # Generate detailed analysis results
    message_content = {
        "signal": signal,
        "confidence": confidence,
        "reasoning": f"""Combined sentiment analysis for {symbol} as of {current_date}:
- News Sentiment: {news_sentiment:.2f} (based on {len(recent_news)} recent articles)
- Fear & Greed Index: {fear_greed_score:.1f}/100
- Options Sentiment: {options_sentiment['signal']} (Put/Call Ratio: {options_sentiment['metrics']['put_call_ratio']:.2f})
- Insider Trading: {insider_sentiment['signal']} (Buy Ratio: {insider_sentiment['metrics']['buy_ratio']:.2f})
Overall weighted sentiment score: {weighted_sentiment:.2f}"""
    }

    # Show reasoning if flag is set
    if show_reasoning:
        show_agent_reasoning(message_content, "Sentiment Analysis Agent")

    # Create message
    message = HumanMessage(
        content=json.dumps(message_content),
        name="sentiment_agent",
    )

    return {
        "messages": [message],
        "data": data,
    }
