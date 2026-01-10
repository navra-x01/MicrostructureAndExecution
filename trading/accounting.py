"""
Accounting Module

This module tracks trading positions, cash, and PnL (profit and loss).
It handles both realized PnL (from closed positions) and unrealized PnL
(mark-to-market on open positions).
"""

from typing import Dict, Optional
from datetime import datetime


class Accountant:
    """
    Tracks trading positions, cash, and PnL.
    
    This class maintains:
    - Position size (positive = long, negative = short)
    - Average entry price
    - Cash balance
    - Realized PnL (from closed trades)
    - Unrealized PnL (mark-to-market)
    
    Attributes:
        position: Current position size (positive = long, negative = short)
        avg_entry_price: Average price at which position was entered
        cash: Cash balance
        realized_pnl: Total realized profit/loss
        trade_history: List of all trades executed
    """
    
    def __init__(self, initial_cash: float = 100000.0):
        """
        Initialize the accountant with starting cash.
        
        Args:
            initial_cash: Starting cash balance (default: $100,000)
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0.0  # Positive = long, negative = short
        self.avg_entry_price = 0.0
        self.realized_pnl = 0.0
        self.trade_history = []  # List of trade records
    
    def record_fill(
        self,
        timestamp: datetime,
        side: str,
        fill_price: float,
        fill_size: float,
        fee: float
    ) -> None:
        """
        Record a trade fill and update position/cash.
        
        This method handles both opening new positions and closing/reducing
        existing positions. It calculates realized PnL when positions are closed.
        
        Args:
            timestamp: Trade timestamp
            side: 'buy' or 'sell'
            fill_price: Price at which trade executed
            fill_size: Size of the trade
            fee: Fee paid for this trade
        """
        if side.lower() == 'buy':
            self._record_buy(timestamp, fill_price, fill_size, fee)
        elif side.lower() == 'sell':
            self._record_sell(timestamp, fill_price, fill_size, fee)
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")
        
        # Record trade in history
        self.trade_history.append({
            'timestamp': timestamp,
            'side': side.lower(),
            'price': fill_price,
            'size': fill_size,
            'fee': fee,
            'position_after': self.position,
            'cash_after': self.cash,
        })
    
    def _record_buy(self, timestamp: datetime, price: float, size: float, fee: float) -> None:
        """
        Record a buy trade.
        
        If we have a short position, this reduces it (or reverses it).
        If we have no position or a long position, this increases the long.
        
        Args:
            timestamp: Trade timestamp
            price: Fill price
            size: Fill size
            fee: Fee paid
        """
        cost = size * price + fee
        
        if self.position < 0:
            # We have a short position - this buy reduces it
            if size <= abs(self.position):
                # Partially closing short position
                # Realized PnL = (entry_price - exit_price) * size
                realized = (self.avg_entry_price - price) * size
                self.realized_pnl += realized
                self.position += size  # Moves toward zero
            else:
                # Reversing position (closing short and opening long)
                # Close short: realized PnL
                close_size = abs(self.position)
                realized = (self.avg_entry_price - price) * close_size
                self.realized_pnl += realized
                
                # Open long: remaining size
                open_size = size - close_size
                self.position = open_size
                self.avg_entry_price = price
        else:
            # Opening or increasing long position
            if self.position == 0:
                # New position
                self.position = size
                self.avg_entry_price = price
            else:
                # Increasing position - update average entry price
                # Average entry price should only consider fill prices, not fees
                total_cost = self.position * self.avg_entry_price + size * price
                self.position += size
                self.avg_entry_price = total_cost / self.position
        
        # Update cash
        self.cash -= cost
    
    def _record_sell(self, timestamp: datetime, price: float, size: float, fee: float) -> None:
        """
        Record a sell trade.
        
        If we have a long position, this reduces it (or reverses it).
        If we have no position or a short position, this increases the short.
        
        Args:
            timestamp: Trade timestamp
            price: Fill price
            size: Fill size
            fee: Fee paid
        """
        proceeds = size * price - fee
        
        if self.position > 0:
            # We have a long position - this sell reduces it
            if size <= self.position:
                # Partially closing long position
                # Realized PnL = (exit_price - entry_price) * size
                realized = (price - self.avg_entry_price) * size
                self.realized_pnl += realized
                self.position -= size  # Moves toward zero
            else:
                # Reversing position (closing long and opening short)
                # Close long: realized PnL
                close_size = self.position
                realized = (price - self.avg_entry_price) * close_size
                self.realized_pnl += realized
                
                # Open short: remaining size
                open_size = size - close_size
                self.position = -open_size
                self.avg_entry_price = price
        else:
            # Opening or increasing short position
            if self.position == 0:
                # New position
                self.position = -size
                self.avg_entry_price = price
            else:
                # Increasing short position - update average entry price
                # Average entry price should only consider fill prices, not fees
                total_proceeds = abs(self.position) * self.avg_entry_price + size * price
                self.position -= size
                self.avg_entry_price = total_proceeds / abs(self.position)
        
        # Update cash
        self.cash += proceeds
    
    def update_unrealized_pnl(self, current_mid_price: float) -> float:
        """
        Calculate and return unrealized PnL based on current market price.
        
        Unrealized PnL is the profit/loss on open positions if they were
        closed at the current market price.
        
        Args:
            current_mid_price: Current mid price for mark-to-market
            
        Returns:
            Unrealized PnL
        """
        if self.position == 0:
            return 0.0
        
        if self.position > 0:
            # Long position: profit if price went up
            unrealized = (current_mid_price - self.avg_entry_price) * self.position
        else:
            # Short position: profit if price went down
            unrealized = (self.avg_entry_price - current_mid_price) * abs(self.position)
        
        return unrealized
    
    def get_metrics(self, current_mid_price: Optional[float] = None) -> Dict[str, float]:
        """
        Get current accounting metrics.
        
        Args:
            current_mid_price: Optional current mid price for unrealized PnL
            
        Returns:
            Dictionary with:
            - position: Current position size
            - avg_entry_price: Average entry price
            - cash: Cash balance
            - realized_pnl: Realized profit/loss
            - unrealized_pnl: Unrealized profit/loss (if mid_price provided)
            - total_pnl: Total PnL (realized + unrealized)
            - total_value: Total portfolio value (cash + position value)
        """
        metrics = {
            'position': self.position,
            'avg_entry_price': self.avg_entry_price,
            'cash': self.cash,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': 0.0,
            'total_pnl': self.realized_pnl,
            'total_value': self.cash,
        }
        
        if current_mid_price is not None:
            unrealized = self.update_unrealized_pnl(current_mid_price)
            metrics['unrealized_pnl'] = unrealized
            metrics['total_pnl'] = self.realized_pnl + unrealized
            
            # Total value = cash + position value
            if self.position != 0:
                position_value = self.position * current_mid_price
                metrics['total_value'] = self.cash + position_value
            else:
                metrics['total_value'] = self.cash
        
        return metrics
    
    def reset(self) -> None:
        """Reset all accounting to initial state."""
        self.cash = self.initial_cash
        self.position = 0.0
        self.avg_entry_price = 0.0
        self.realized_pnl = 0.0
        self.trade_history = []
