"""
Signal Engine Module

This module computes microstructure signals from order book data, including:
- Mid-price returns (log returns)
- Depth imbalance (bid vs ask liquidity)
- Rolling z-scores for mean reversion strategies

These signals are fundamental to market microstructure analysis and can be
used to predict short-term price movements.
"""

import numpy as np
from typing import Dict, Optional, List
from collections import deque
import config
from .orderbook import OrderBook


class SignalEngine:
    """
    Computes microstructure signals from order book data.
    
    This class maintains a rolling window of historical data to compute
    statistical measures like z-scores, which are useful for mean reversion
    strategies.
    
    Attributes:
        window_size: Size of rolling window for z-score calculation
        imbalance_depth: Number of levels to use for depth imbalance
        mid_prices: Rolling window of mid prices
        returns: Rolling window of log returns
        imbalances: Rolling window of depth imbalances
    """
    
    def __init__(self, window_size: int = None, imbalance_depth: int = None):
        """
        Initialize the signal engine.
        
        Args:
            window_size: Size of rolling window for z-score (defaults to config)
            imbalance_depth: Number of levels for imbalance calculation (defaults to config)
        """
        self.window_size = window_size or config.SIGNAL_WINDOW_SIZE
        self.imbalance_depth = imbalance_depth or config.IMBALANCE_DEPTH
        
        # Rolling windows for historical data
        self.mid_prices: deque = deque(maxlen=self.window_size + 1)
        self.returns: deque = deque(maxlen=self.window_size)
        self.imbalances: deque = deque(maxlen=self.window_size)
        
        # Previous mid price for return calculation
        self.prev_mid_price: Optional[float] = None
    
    def update(self, orderbook: OrderBook) -> Dict[str, float]:
        """
        Update signals based on current order book state.
        
        This method should be called whenever the order book is updated.
        It computes all signals and stores them in rolling windows.
        
        Args:
            orderbook: Current OrderBook instance
            
        Returns:
            Dictionary containing all computed signals:
            - mid_price: Current mid price
            - spread: Current spread
            - mid_price_return: Log return from previous mid price
            - depth_imbalance: Imbalance in top k levels
            - imbalance_zscore: Z-score of depth imbalance
            - return_zscore: Z-score of mid-price returns
        """
        # Get current mid price
        mid_price = orderbook.mid_price()
        spread = orderbook.spread()
        
        signals = {
            'mid_price': mid_price,
            'spread': spread,
            'mid_price_return': None,
            'depth_imbalance': None,
            'imbalance_zscore': None,
            'return_zscore': None,
        }
        
        if mid_price is None:
            return signals
        
        # Calculate mid-price return (log return)
        if self.prev_mid_price is not None and self.prev_mid_price > 0:
            log_return = np.log(mid_price / self.prev_mid_price)
            self.returns.append(log_return)
            signals['mid_price_return'] = log_return
        else:
            signals['mid_price_return'] = 0.0
        
        # Store current mid price
        self.mid_prices.append(mid_price)
        self.prev_mid_price = mid_price
        
        # Calculate depth imbalance
        imbalance = self._calculate_depth_imbalance(orderbook)
        if imbalance is not None:
            self.imbalances.append(imbalance)
            signals['depth_imbalance'] = imbalance
        
        # Calculate z-scores if we have enough data
        if len(self.imbalances) >= self.window_size:
            signals['imbalance_zscore'] = self._z_score(
                imbalance, list(self.imbalances)[:-1]  # Exclude current value
            )
        
        if len(self.returns) >= self.window_size:
            signals['return_zscore'] = self._z_score(
                signals['mid_price_return'], list(self.returns)[:-1]  # Exclude current value
            )
        
        return signals
    
    def _calculate_depth_imbalance(self, orderbook: OrderBook) -> Optional[float]:
        """
        Calculate depth imbalance: (bid_size - ask_size) / (bid_size + ask_size).
        
        Depth imbalance measures the relative liquidity on each side of the book.
        Positive values indicate more bid liquidity (bullish), negative values
        indicate more ask liquidity (bearish).
        
        Args:
            orderbook: OrderBook instance
            
        Returns:
            Imbalance value between -1 and 1, or None if insufficient data
        """
        bids, asks = orderbook.top_depth(self.imbalance_depth)
        
        if not bids or not asks:
            return None
        
        # Sum up sizes on each side
        bid_size = sum(size for _, size in bids)
        ask_size = sum(size for _, size in asks)
        
        total_size = bid_size + ask_size
        
        if total_size == 0:
            return None
        
        # Imbalance: (bid - ask) / (bid + ask)
        # Range: [-1, 1]
        # +1 = all bids, -1 = all asks, 0 = balanced
        imbalance = (bid_size - ask_size) / total_size
        
        return imbalance
    
    def _z_score(self, value: float, window: List[float]) -> float:
        """
        Calculate z-score of a value relative to a rolling window.
        
        The z-score measures how many standard deviations a value is from
        the mean. It's useful for identifying outliers and mean reversion
        opportunities.
        
        Args:
            value: Current value to score
            window: Historical values for computing mean and std
            
        Returns:
            Z-score: (value - mean) / std
        """
        if len(window) < 2:
            return 0.0
        
        window_array = np.array(window)
        mean = np.mean(window_array)
        std = np.std(window_array)
        
        if std == 0:
            return 0.0
        
        z_score = (value - mean) / std
        return float(z_score)
    
    def get_current_signals(self) -> Dict[str, float]:
        """
        Get the most recent signals without updating.
        
        Returns:
            Dictionary of current signal values
        """
        signals = {
            'mid_price': self.mid_prices[-1] if self.mid_prices else None,
            'mid_price_return': self.returns[-1] if self.returns else None,
            'depth_imbalance': self.imbalances[-1] if self.imbalances else None,
        }
        
        # Calculate z-scores if we have enough data
        if len(self.imbalances) >= self.window_size:
            signals['imbalance_zscore'] = self._z_score(
                signals['depth_imbalance'],
                list(self.imbalances)[:-1]
            )
        
        if len(self.returns) >= self.window_size:
            signals['return_zscore'] = self._z_score(
                signals['mid_price_return'],
                list(self.returns)[:-1]
            )
        
        return signals
    
    def reset(self) -> None:
        """Reset all rolling windows (useful for new backtests)."""
        self.mid_prices.clear()
        self.returns.clear()
        self.imbalances.clear()
        self.prev_mid_price = None
