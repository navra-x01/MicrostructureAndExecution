"""
Unit tests for ExecutionSimulator module.
"""

import pytest
from trading.execution import ExecutionSimulator
from microstructure.orderbook import OrderBook


class TestExecutionSimulator:
    """Test cases for ExecutionSimulator class."""
    
    def test_initialization(self):
        """Test execution simulator initialization."""
        executor = ExecutionSimulator(taker_fee=0.001)
        assert executor.taker_fee == 0.001
    
    def test_execute_buy_small_order(self):
        """Test executing a small buy order (fits in top level)."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        ob.apply_snapshot(
            [(100.0, 100)],
            [(101.0, 50)]  # 50 shares at 101.0
        )
        
        fill_price, fill_size, fee, slippage = executor.execute_market_order(
            ob, 'buy', 10
        )
        
        assert fill_price == 101.0
        assert fill_size == 10
        assert fee == 10 * 101.0 * executor.taker_fee
        assert slippage == 0.0  # No slippage for small order
    
    def test_execute_buy_large_order(self):
        """Test executing a large buy order (walks the book)."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        ob.apply_snapshot(
            [(100.0, 100)],
            [
                (101.0, 30),  # 30 shares at 101.0
                (102.0, 40),  # 40 shares at 102.0
                (103.0, 50),  # 50 shares at 103.0
            ]
        )
        
        # Order size 80 - will walk the book
        fill_price, fill_size, fee, slippage = executor.execute_market_order(
            ob, 'buy', 80
        )
        
        assert fill_size == 80
        # Weighted average: (30*101 + 40*102 + 10*103) / 80
        expected_avg = (30*101.0 + 40*102.0 + 10*103.0) / 80.0
        assert abs(fill_price - expected_avg) < 0.01
        assert slippage > 0  # Should have slippage
    
    def test_execute_sell_small_order(self):
        """Test executing a small sell order."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        ob.apply_snapshot(
            [(100.0, 50)],
            [(101.0, 100)]
        )
        
        fill_price, fill_size, fee, slippage = executor.execute_market_order(
            ob, 'sell', 10
        )
        
        assert fill_price == 100.0
        assert fill_size == 10
        assert slippage == 0.0
    
    def test_execute_sell_large_order(self):
        """Test executing a large sell order (walks the book)."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        ob.apply_snapshot(
            [
                (100.0, 30),
                (99.0, 40),
                (98.0, 50),
            ],
            [(101.0, 100)]
        )
        
        fill_price, fill_size, fee, slippage = executor.execute_market_order(
            ob, 'sell', 80
        )
        
        assert fill_size == 80
        assert slippage > 0  # Should have slippage
    
    def test_execute_empty_book(self):
        """Test execution against empty book."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        fill_price, fill_size, fee, slippage = executor.execute_market_order(
            ob, 'buy', 10
        )
        
        assert fill_price == 0.0
        assert fill_size == 0.0
        assert fee == 0.0
        assert slippage == 0.0
    
    def test_execute_zero_quantity(self):
        """Test execution with zero quantity."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        ob.apply_snapshot([(100.0, 10)], [(101.0, 10)])
        
        fill_price, fill_size, fee, slippage = executor.execute_market_order(
            ob, 'buy', 0
        )
        
        assert fill_size == 0.0
    
    def test_fee_calculation(self):
        """Test that fees are calculated correctly."""
        executor = ExecutionSimulator(taker_fee=0.001)
        ob = OrderBook()
        
        ob.apply_snapshot([(100.0, 100)], [(101.0, 100)])
        
        fill_price, fill_size, fee, _ = executor.execute_market_order(
            ob, 'buy', 50
        )
        
        expected_fee = 50 * 101.0 * 0.001
        assert abs(fee - expected_fee) < 0.01
    
    def test_get_best_execution_price(self):
        """Test getting best execution price."""
        executor = ExecutionSimulator()
        ob = OrderBook()
        
        ob.apply_snapshot([(100.0, 10)], [(101.0, 10)])
        
        assert executor.get_best_execution_price(ob, 'buy') == 101.0
        assert executor.get_best_execution_price(ob, 'sell') == 100.0
