"""
Execution Simulator Module

This module simulates the execution of market orders against an order book.
It handles order fills, book walking (when size exceeds top level), fee
calculation, and slippage tracking.

Market orders execute immediately at the best available price, walking
through the book if necessary to fill the entire order size.
"""

from typing import Tuple, Optional
from microstructure.orderbook import OrderBook
import config


class ExecutionSimulator:
    """
    Simulates market order execution against an order book.
    
    Market orders are executed immediately at the best available price.
    If the order size exceeds the top level, the order "walks the book"
    to fill at progressively worse prices.
    
    Attributes:
        taker_fee: Fee rate for market orders (taker fee)
    """
    
    def __init__(self, taker_fee: float = None):
        """
        Initialize the execution simulator.
        
        Args:
            taker_fee: Taker fee rate (defaults to config)
        """
        self.taker_fee = taker_fee or config.TAKER_FEE
    
    def execute_market_order(
        self,
        orderbook: OrderBook,
        side: str,
        quantity: float
    ) -> Tuple[float, float, float, float]:
        """
        Execute a market order against the order book.
        
        Market orders execute immediately:
        - Buy orders: start at best_ask and walk up if needed
        - Sell orders: start at best_bid and walk down if needed
        
        Args:
            orderbook: OrderBook instance to execute against
            side: 'buy' or 'sell'
            quantity: Order size (number of shares/contracts)
            
        Returns:
            Tuple of (fill_price, fill_size, fee, slippage):
            - fill_price: Weighted average fill price
            - fill_size: Actual filled size (may be less than quantity if insufficient liquidity)
            - fee: Total fee paid
            - slippage: Slippage cost vs best price
            
        Raises:
            ValueError: If side is invalid or orderbook has no liquidity
        """
        if side.lower() not in ['buy', 'sell']:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        
        if quantity <= 0:
            return (0.0, 0.0, 0.0, 0.0)
        
        if side.lower() == 'buy':
            return self._execute_buy(orderbook, quantity)
        else:
            return self._execute_sell(orderbook, quantity)
    
    def _execute_buy(self, orderbook: OrderBook, quantity: float) -> Tuple[float, float, float, float]:
        """
        Execute a buy (market) order.
        
        Buy orders execute at ask prices, starting from best_ask and
        walking up the book if necessary.
        
        Args:
            orderbook: OrderBook instance
            quantity: Order size
            
        Returns:
            Tuple of (fill_price, fill_size, fee, slippage)
        """
        asks = orderbook.asks.copy()
        
        if not asks:
            return (0.0, 0.0, 0.0, 0.0)
        
        best_ask_price = asks[0][0]
        remaining_qty = quantity
        total_cost = 0.0
        filled_size = 0.0
        
        # Walk the book
        for price, size in asks:
            if remaining_qty <= 0:
                break
            
            fill_at_level = min(remaining_qty, size)
            total_cost += fill_at_level * price
            filled_size += fill_at_level
            remaining_qty -= fill_at_level
        
        if filled_size == 0:
            return (0.0, 0.0, 0.0, 0.0)
        
        # Weighted average fill price
        fill_price = total_cost / filled_size
        
        # Calculate fee
        fee = filled_size * fill_price * self.taker_fee
        
        # Calculate slippage (difference from best price)
        slippage = (fill_price - best_ask_price) * filled_size
        
        return (fill_price, filled_size, fee, slippage)
    
    def _execute_sell(self, orderbook: OrderBook, quantity: float) -> Tuple[float, float, float, float]:
        """
        Execute a sell (market) order.
        
        Sell orders execute at bid prices, starting from best_bid and
        walking down the book if necessary.
        
        Args:
            orderbook: OrderBook instance
            quantity: Order size
            
        Returns:
            Tuple of (fill_price, fill_size, fee, slippage)
        """
        bids = orderbook.bids.copy()
        
        if not bids:
            return (0.0, 0.0, 0.0, 0.0)
        
        best_bid_price = bids[0][0]
        remaining_qty = quantity
        total_proceeds = 0.0
        filled_size = 0.0
        
        # Walk the book
        for price, size in bids:
            if remaining_qty <= 0:
                break
            
            fill_at_level = min(remaining_qty, size)
            total_proceeds += fill_at_level * price
            filled_size += fill_at_level
            remaining_qty -= fill_at_level
        
        if filled_size == 0:
            return (0.0, 0.0, 0.0, 0.0)
        
        # Weighted average fill price
        fill_price = total_proceeds / filled_size
        
        # Calculate fee
        fee = filled_size * fill_price * self.taker_fee
        
        # Calculate slippage (difference from best price)
        slippage = (best_bid_price - fill_price) * filled_size
        
        return (fill_price, filled_size, fee, slippage)
    
    def get_best_execution_price(self, orderbook: OrderBook, side: str) -> Optional[float]:
        """
        Get the best available execution price for a market order.
        
        This is the price at which a small order would execute (best bid/ask).
        
        Args:
            orderbook: OrderBook instance
            side: 'buy' or 'sell'
            
        Returns:
            Best execution price, or None if no liquidity
        """
        if side.lower() == 'buy':
            return orderbook.best_ask()
        elif side.lower() == 'sell':
            return orderbook.best_bid()
        else:
            raise ValueError(f"Invalid side: {side}")
