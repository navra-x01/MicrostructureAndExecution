"""
Unit tests for OrderBook module.
"""

import pytest
from microstructure.orderbook import OrderBook


class TestOrderBook:
    """Test cases for OrderBook class."""
    
    def test_initialization(self):
        """Test order book initialization."""
        ob = OrderBook(depth=5)
        assert ob.depth == 5
        assert len(ob.bids) == 0
        assert len(ob.asks) == 0
    
    def test_apply_snapshot(self):
        """Test snapshot application."""
        ob = OrderBook(depth=5)
        
        bids = [(100.0, 10), (99.0, 20), (98.0, 30)]
        asks = [(101.0, 10), (102.0, 20), (103.0, 30)]
        
        ob.apply_snapshot(bids, asks)
        
        assert len(ob.bids) == 3
        assert len(ob.asks) == 3
        assert ob.best_bid() == 100.0
        assert ob.best_ask() == 101.0
    
    def test_best_bid_ask(self):
        """Test best bid and ask retrieval."""
        ob = OrderBook()
        
        # Empty book
        assert ob.best_bid() is None
        assert ob.best_ask() is None
        
        # With data
        ob.apply_snapshot(
            [(100.0, 10), (99.0, 20)],
            [(101.0, 10), (102.0, 20)]
        )
        
        assert ob.best_bid() == 100.0
        assert ob.best_ask() == 101.0
    
    def test_mid_price(self):
        """Test mid price calculation."""
        ob = OrderBook()
        
        # Empty book
        assert ob.mid_price() is None
        
        # With data
        ob.apply_snapshot(
            [(100.0, 10)],
            [(102.0, 10)]
        )
        
        assert ob.mid_price() == 101.0
    
    def test_spread(self):
        """Test spread calculation."""
        ob = OrderBook()
        
        # Empty book
        assert ob.spread() is None
        
        # With data
        ob.apply_snapshot(
            [(100.0, 10)],
            [(102.0, 10)]
        )
        
        assert ob.spread() == 2.0
    
    def test_apply_diff_add(self):
        """Test applying a diff to add/update a level."""
        ob = OrderBook()
        ob.apply_snapshot(
            [(100.0, 10)],
            [(101.0, 10)]
        )
        
        # Add new bid level
        ob.apply_diff('bid', 99.0, 15, 'update')
        assert len(ob.bids) == 2
        assert ob.best_bid() == 100.0  # Still best
        
        # Update existing level
        ob.apply_diff('bid', 100.0, 25, 'update')
        assert len(ob.bids) == 2
        # Find the updated level
        bid_prices = [p for p, _ in ob.bids]
        assert 100.0 in bid_prices
    
    def test_apply_diff_remove(self):
        """Test applying a diff to remove a level."""
        ob = OrderBook()
        ob.apply_snapshot(
            [(100.0, 10), (99.0, 20)],
            [(101.0, 10)]
        )
        
        # Remove a level
        ob.apply_diff('bid', 99.0, 0, 'remove')
        assert len(ob.bids) == 1
        assert ob.best_bid() == 100.0
    
    def test_top_depth(self):
        """Test top depth retrieval."""
        ob = OrderBook(depth=5)
        ob.apply_snapshot(
            [(100.0, 10), (99.0, 20), (98.0, 30)],
            [(101.0, 10), (102.0, 20), (103.0, 30)]
        )
        
        bids, asks = ob.top_depth(2)
        assert len(bids) == 2
        assert len(asks) == 2
        assert bids[0][0] == 100.0  # Highest bid first
    
    def test_depth_limit(self):
        """Test that depth limit is enforced."""
        ob = OrderBook(depth=3)
        bids = [(100.0, 10), (99.0, 20), (98.0, 30), (97.0, 40), (96.0, 50)]
        asks = [(101.0, 10), (102.0, 20), (103.0, 30), (104.0, 40), (105.0, 50)]
        
        ob.apply_snapshot(bids, asks)
        
        assert len(ob.bids) == 3
        assert len(ob.asks) == 3
    
    def test_invariant_validation(self):
        """Test that invariant validation works (best_bid < best_ask)."""
        ob = OrderBook()
        
        # Normal case - should work
        ob.apply_snapshot(
            [(100.0, 10)],
            [(101.0, 10)]
        )
        assert ob.best_bid() < ob.best_ask()
        
        # Violation case - should log warning but not crash
        # (In real data, this shouldn't happen, but we handle it gracefully)
        ob.apply_snapshot(
            [(101.0, 10)],  # Bid higher than ask
            [(100.0, 10)]
        )
        # Should still work, just with a warning logged
