"""
Unit tests for SignalEngine module.
"""

import pytest
import numpy as np
from microstructure.signals import SignalEngine
from microstructure.orderbook import OrderBook


class TestSignalEngine:
    """Test cases for SignalEngine class."""
    
    def test_initialization(self):
        """Test signal engine initialization."""
        engine = SignalEngine(window_size=100)
        assert engine.window_size == 100
        assert len(engine.mid_prices) == 0
    
    def test_depth_imbalance(self):
        """Test depth imbalance calculation."""
        engine = SignalEngine()
        ob = OrderBook()
        
        # Balanced book
        ob.apply_snapshot(
            [(100.0, 10), (99.0, 10)],
            [(101.0, 10), (102.0, 10)]
        )
        
        imbalance = engine._calculate_depth_imbalance(ob)
        assert imbalance == 0.0  # Balanced
        
        # More bids
        ob.apply_snapshot(
            [(100.0, 20), (99.0, 20)],
            [(101.0, 10), (102.0, 10)]
        )
        
        imbalance = engine._calculate_depth_imbalance(ob)
        assert imbalance > 0  # More bid liquidity
        
        # More asks
        ob.apply_snapshot(
            [(100.0, 10), (99.0, 10)],
            [(101.0, 20), (102.0, 20)]
        )
        
        imbalance = engine._calculate_depth_imbalance(ob)
        assert imbalance < 0  # More ask liquidity
    
    def test_z_score(self):
        """Test z-score calculation."""
        engine = SignalEngine()
        
        # Create a window with known mean and std
        window = [1.0, 2.0, 3.0, 4.0, 5.0]
        mean = np.mean(window)
        std = np.std(window)
        
        # Test z-score of mean value (should be ~0)
        z = engine._z_score(mean, window)
        assert abs(z) < 0.1  # Should be close to 0
        
        # Test z-score of value 1 std above mean
        value_above = mean + std
        z = engine._z_score(value_above, window)
        assert abs(z - 1.0) < 0.1  # Should be close to 1
    
    def test_update_signals(self):
        """Test signal update."""
        engine = SignalEngine(window_size=10)
        ob = OrderBook()
        
        # First update
        ob.apply_snapshot(
            [(100.0, 10)],
            [(102.0, 10)]
        )
        
        signals = engine.update(ob)
        assert signals['mid_price'] == 101.0
        assert signals['spread'] == 2.0
        assert signals['mid_price_return'] == 0.0  # First update, no return
    
    def test_mid_price_return(self):
        """Test mid-price return calculation."""
        engine = SignalEngine()
        ob = OrderBook()
        
        # First update
        ob.apply_snapshot(
            [(100.0, 10)],
            [(102.0, 10)]
        )
        engine.update(ob)
        
        # Second update - price increased
        ob.apply_snapshot(
            [(101.0, 10)],
            [(103.0, 10)]
        )
        signals = engine.update(ob)
        
        # Mid price went from 101 to 102
        expected_return = np.log(102.0 / 101.0)
        assert abs(signals['mid_price_return'] - expected_return) < 0.001
    
    def test_rolling_window(self):
        """Test that rolling window maintains correct size."""
        engine = SignalEngine(window_size=5)
        ob = OrderBook()
        
        # Add more updates than window size
        for i in range(10):
            ob.apply_snapshot(
                [(100.0 + i * 0.1, 10)],
                [(102.0 + i * 0.1, 10)]
            )
            engine.update(ob)
        
        # Window should be limited to window_size
        assert len(engine.mid_prices) <= engine.window_size + 1
        assert len(engine.returns) <= engine.window_size
    
    def test_reset(self):
        """Test reset functionality."""
        engine = SignalEngine()
        ob = OrderBook()
        
        # Add some data
        ob.apply_snapshot([(100.0, 10)], [(102.0, 10)])
        engine.update(ob)
        
        assert len(engine.mid_prices) > 0
        
        # Reset
        engine.reset()
        assert len(engine.mid_prices) == 0
        assert len(engine.returns) == 0
        assert engine.prev_mid_price is None
