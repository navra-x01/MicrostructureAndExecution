"""
Unit tests for Accountant module.
"""

import pytest
from datetime import datetime
from trading.accounting import Accountant


class TestAccountant:
    """Test cases for Accountant class."""
    
    def test_initialization(self):
        """Test accountant initialization."""
        acc = Accountant(initial_cash=100000.0)
        assert acc.cash == 100000.0
        assert acc.position == 0.0
        assert acc.realized_pnl == 0.0
    
    def test_record_buy_new_position(self):
        """Test recording a buy that opens a new long position."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        acc.record_fill(timestamp, 'buy', 100.0, 10, 1.0)
        
        assert acc.position == 10.0
        assert acc.avg_entry_price == 100.0
        assert acc.cash == 100000.0 - (10 * 100.0 + 1.0)
    
    def test_record_sell_new_position(self):
        """Test recording a sell that opens a new short position."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        acc.record_fill(timestamp, 'sell', 100.0, 10, 1.0)
        
        assert acc.position == -10.0
        assert acc.avg_entry_price == 100.0
        assert acc.cash == 100000.0 + (10 * 100.0 - 1.0)
    
    def test_record_buy_increase_position(self):
        """Test recording a buy that increases an existing long position."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        # Open position
        acc.record_fill(timestamp, 'buy', 100.0, 10, 1.0)
        initial_cash = acc.cash
        
        # Increase position at different price
        acc.record_fill(timestamp, 'buy', 110.0, 10, 1.1)
        
        assert acc.position == 20.0
        # Average should be weighted: (10*100 + 10*110) / 20 = 105
        assert abs(acc.avg_entry_price - 105.0) < 0.01
    
    def test_record_sell_close_long(self):
        """Test recording a sell that closes a long position."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        # Open long position
        acc.record_fill(timestamp, 'buy', 100.0, 10, 1.0)
        initial_cash = acc.cash
        
        # Close position at profit
        acc.record_fill(timestamp, 'sell', 110.0, 10, 1.1)
        
        assert acc.position == 0.0
        # Realized PnL: (110 - 100) * 10 = 100
        assert abs(acc.realized_pnl - 100.0) < 0.1
    
    def test_record_buy_close_short(self):
        """Test recording a buy that closes a short position."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        # Open short position
        acc.record_fill(timestamp, 'sell', 100.0, 10, 1.0)
        initial_cash = acc.cash
        
        # Close position at profit (price went down)
        acc.record_fill(timestamp, 'buy', 90.0, 10, 0.9)
        
        assert acc.position == 0.0
        # Realized PnL: (100 - 90) * 10 = 100
        assert abs(acc.realized_pnl - 100.0) < 0.1
    
    def test_unrealized_pnl_long(self):
        """Test unrealized PnL calculation for long position."""
        acc = Accountant()
        timestamp = datetime.now()
        
        # Open long at 100
        acc.record_fill(timestamp, 'buy', 100.0, 10, 1.0)
        
        # Price goes to 110
        unrealized = acc.update_unrealized_pnl(110.0)
        assert abs(unrealized - 100.0) < 0.1  # (110 - 100) * 10
    
    def test_unrealized_pnl_short(self):
        """Test unrealized PnL calculation for short position."""
        acc = Accountant()
        timestamp = datetime.now()
        
        # Open short at 100
        acc.record_fill(timestamp, 'sell', 100.0, 10, 1.0)
        
        # Price goes to 90
        unrealized = acc.update_unrealized_pnl(90.0)
        assert abs(unrealized - 100.0) < 0.1  # (100 - 90) * 10
    
    def test_get_metrics(self):
        """Test getting accounting metrics."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        acc.record_fill(timestamp, 'buy', 100.0, 10, 1.0)
        
        metrics = acc.get_metrics(current_mid_price=110.0)
        
        assert metrics['position'] == 10.0
        assert metrics['cash'] < 100000.0
        assert metrics['unrealized_pnl'] > 0
        assert 'total_pnl' in metrics
        assert 'total_value' in metrics
    
    def test_reset(self):
        """Test reset functionality."""
        acc = Accountant(initial_cash=100000.0)
        timestamp = datetime.now()
        
        acc.record_fill(timestamp, 'buy', 100.0, 10, 1.0)
        
        assert acc.position != 0
        
        acc.reset()
        
        assert acc.position == 0.0
        assert acc.cash == 100000.0
        assert acc.realized_pnl == 0.0
        assert len(acc.trade_history) == 0
