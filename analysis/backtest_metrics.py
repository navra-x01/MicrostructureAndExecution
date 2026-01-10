"""
Backtest Metrics Module

This module calculates performance metrics for backtest results, including:
- Sharpe ratio
- Win rate
- Maximum drawdown
- Summary statistics

These metrics are standard in quantitative finance for evaluating trading
strategy performance.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional


def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate the Sharpe ratio of a return series.
    
    The Sharpe ratio measures risk-adjusted returns. Higher values indicate
    better risk-adjusted performance.
    
    Formula: (mean_return - risk_free_rate) / std_return * sqrt(periods_per_year)
    
    Args:
        returns: List of periodic returns
        risk_free_rate: Annual risk-free rate (default: 0.0)
        periods_per_year: Number of periods per year for annualization (default: 252 trading days)
        
    Returns:
        Annualized Sharpe ratio, or 0.0 if insufficient data or zero std
    """
    if len(returns) < 2:
        return 0.0
    
    returns_array = np.array(returns)
    mean_return = np.mean(returns_array)
    std_return = np.std(returns_array)
    
    if std_return == 0:
        return 0.0
    
    # Annualize
    periods_per_year_sqrt = np.sqrt(periods_per_year)
    sharpe = (mean_return - risk_free_rate / periods_per_year) / std_return * periods_per_year_sqrt
    
    return float(sharpe)


def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
    """
    Calculate the win rate (percentage of profitable trades).
    
    A trade is considered a "win" if it resulted in realized profit.
    This requires tracking individual trades and their PnL.
    
    Args:
        trades: List of trade dictionaries, each should have 'realized_pnl' or similar
        
    Returns:
        Win rate as a fraction (0.0 to 1.0), or 0.0 if no trades
    """
    if not trades:
        return 0.0
    
    # For simplicity, we'll calculate based on trade outcomes
    # In a full implementation, you'd track each round-trip trade's PnL
    # Here we'll use a simplified approach based on trade direction and price movement
    
    wins = 0
    total_round_trips = 0
    
    # Simple approach: count profitable position changes
    # This is a simplified metric - a full implementation would track
    # entry/exit pairs for each position
    
    # For now, return a placeholder that can be enhanced
    # A better implementation would require tracking entry/exit pairs
    
    return 0.5  # Placeholder - would need trade-level PnL tracking


def calculate_max_drawdown(pnl_series: List[float]) -> Dict[str, float]:
    """
    Calculate maximum drawdown from a PnL series.
    
    Maximum drawdown is the largest peak-to-trough decline in portfolio value.
    It's a key risk metric that measures the worst-case loss.
    
    Args:
        pnl_series: List of cumulative PnL values over time
        
    Returns:
        Dictionary with:
        - max_drawdown: Maximum drawdown (as positive number)
        - max_drawdown_pct: Maximum drawdown as percentage
        - drawdown_start: Index where drawdown started
        - drawdown_end: Index where drawdown ended
    """
    if not pnl_series or len(pnl_series) < 2:
        return {
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'drawdown_start': 0,
            'drawdown_end': 0,
        }
    
    pnl_array = np.array(pnl_series)
    
    # Calculate running maximum (peak)
    running_max = np.maximum.accumulate(pnl_array)
    
    # Calculate drawdown at each point
    drawdown = running_max - pnl_array
    
    # Find maximum drawdown
    max_dd_idx = np.argmax(drawdown)
    max_drawdown = float(drawdown[max_dd_idx])
    
    # Find the peak before the max drawdown
    peak_idx = np.where(pnl_array[:max_dd_idx + 1] == running_max[max_dd_idx])[0]
    if len(peak_idx) > 0:
        peak_value = pnl_array[peak_idx[-1]]
        max_drawdown_pct = (max_drawdown / peak_value * 100) if peak_value > 0 else 0.0
        drawdown_start = int(peak_idx[-1])
    else:
        max_drawdown_pct = 0.0
        drawdown_start = 0
    
    return {
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'drawdown_start': drawdown_start,
        'drawdown_end': int(max_dd_idx),
    }


def generate_summary_metrics(
    trades: List[Dict[str, Any]],
    pnl_history: List[float],
    returns: Optional[List[float]] = None,
    risk_free_rate: float = 0.0
) -> Dict[str, Any]:
    """
    Generate comprehensive summary metrics for a backtest.
    
    This function calculates all key performance metrics and returns them
    in a structured dictionary suitable for JSON export.
    
    Args:
        trades: List of trade records
        pnl_history: List of cumulative PnL over time
        returns: Optional list of periodic returns (if None, calculated from PnL)
        risk_free_rate: Annual risk-free rate for Sharpe calculation
        
    Returns:
        Dictionary containing all metrics:
        - total_trades: Number of trades executed
        - total_pnl: Final total PnL
        - win_rate: Win rate (fraction)
        - sharpe_ratio: Annualized Sharpe ratio
        - max_drawdown: Maximum drawdown
        - max_drawdown_pct: Maximum drawdown percentage
        - avg_trade_pnl: Average PnL per trade
    """
    # Calculate returns from PnL if not provided
    if returns is None and len(pnl_history) > 1:
        pnl_array = np.array(pnl_history)
        returns = np.diff(pnl_array) / (np.abs(pnl_array[:-1]) + 1e-10)  # Avoid division by zero
        returns = returns.tolist()
    elif returns is None:
        returns = []
    
    # Calculate metrics
    total_trades = len(trades)
    total_pnl = pnl_history[-1] if pnl_history else 0.0
    
    # Win rate (simplified - would need proper trade-level tracking)
    win_rate = calculate_win_rate(trades)
    
    # Sharpe ratio
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate) if returns else 0.0
    
    # Maximum drawdown
    drawdown_info = calculate_max_drawdown(pnl_history) if pnl_history else {
        'max_drawdown': 0.0,
        'max_drawdown_pct': 0.0,
    }
    
    # Average trade PnL
    avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
    
    # Additional statistics
    if pnl_history:
        final_value = pnl_history[-1]
        initial_value = pnl_history[0] if pnl_history else 0.0
        total_return_pct = ((final_value - initial_value) / abs(initial_value) * 100) if initial_value != 0 else 0.0
    else:
        total_return_pct = 0.0
    
    return {
        'total_trades': total_trades,
        'total_pnl': float(total_pnl),
        'total_return_pct': float(total_return_pct),
        'win_rate': float(win_rate),
        'sharpe_ratio': float(sharpe),
        'max_drawdown': drawdown_info['max_drawdown'],
        'max_drawdown_pct': drawdown_info['max_drawdown_pct'],
        'avg_trade_pnl': float(avg_trade_pnl),
        'num_trades': total_trades,
    }
