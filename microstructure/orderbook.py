"""
Order Book Module

This module implements a simple order book that maintains the top N levels
of bids and asks. It supports both snapshot initialization and incremental
updates (diffs).

The order book enforces the invariant that best_bid < best_ask, which is
fundamental to market microstructure.
"""

import logging
from typing import List, Tuple, Optional
import config

logger = logging.getLogger(__name__)


class OrderBook:
    """
    A simple order book that maintains the top N bid and ask levels.
    
    The order book stores price-size pairs as tuples, sorted by price:
    - Bids: sorted in descending order (highest bid first)
    - Asks: sorted in ascending order (lowest ask first)
    
    Attributes:
        depth: Maximum number of levels to maintain
        bids: List of (price, size) tuples for bids, sorted descending
        asks: List of (price, size) tuples for asks, sorted ascending
    """
    
    def __init__(self, depth: int = None):
        """
        Initialize an empty order book.
        
        Args:
            depth: Maximum number of levels to maintain (defaults to config value)
        """
        self.depth = depth or config.ORDER_BOOK_DEPTH
        self.bids: List[Tuple[float, float]] = []  # (price, size), sorted descending
        self.asks: List[Tuple[float, float]] = []  # (price, size), sorted ascending
    
    def apply_snapshot(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> None:
        """
        Initialize or reset the order book from a snapshot.
        
        This method replaces the entire order book with new data. It's typically
        used at the start of a session or when receiving a full order book snapshot.
        
        Args:
            bids: List of (price, size) tuples for bids
            asks: List of (price, size) tuples for asks
            
        Note:
            The input lists should be sorted appropriately:
            - Bids: descending by price (highest first)
            - Asks: ascending by price (lowest first)
        """
        # Sort bids descending (highest price first)
        self.bids = sorted(bids, key=lambda x: x[0], reverse=True)[:self.depth]
        
        # Sort asks ascending (lowest price first)
        self.asks = sorted(asks, key=lambda x: x[0])[:self.depth]
        
        # Validate invariant
        self._validate_invariant()
    
    def apply_diff(self, side: str, price: float, size: float, action: str = 'update') -> None:
        """
        Apply an incremental update (diff) to the order book.
        
        This method handles individual order book updates, which is more efficient
        than applying full snapshots for every change.
        
        Args:
            side: 'bid' or 'ask'
            price: Price level to update
            size: New size at this price level (0 means remove)
            action: 'update' (default) or 'remove'
            
        Note:
            If size is 0 or action is 'remove', the level is removed from the book.
            Otherwise, the level is added or updated.
        """
        if action == 'remove' or size == 0:
            self._remove_level(side, price)
        else:
            self._update_level(side, price, size)
        
        # Validate invariant after update
        self._validate_invariant()
    
    def _update_level(self, side: str, price: float, size: float) -> None:
        """
        Update or add a price level.
        
        Args:
            side: 'bid' or 'ask'
            price: Price level
            size: Size at this level
        """
        if side.lower() == 'bid':
            # Remove existing level if present
            self.bids = [(p, s) for p, s in self.bids if p != price]
            # Add new level
            self.bids.append((price, size))
            # Sort descending and keep top N
            self.bids = sorted(self.bids, key=lambda x: x[0], reverse=True)[:self.depth]
        elif side.lower() == 'ask':
            # Remove existing level if present
            self.asks = [(p, s) for p, s in self.asks if p != price]
            # Add new level
            self.asks.append((price, size))
            # Sort ascending and keep top N
            self.asks = sorted(self.asks, key=lambda x: x[0])[:self.depth]
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'bid' or 'ask'")
    
    def _remove_level(self, side: str, price: float) -> None:
        """
        Remove a price level from the book.
        
        Args:
            side: 'bid' or 'ask'
            price: Price level to remove
        """
        if side.lower() == 'bid':
            self.bids = [(p, s) for p, s in self.bids if p != price]
        elif side.lower() == 'ask':
            self.asks = [(p, s) for p, s in self.asks if p != price]
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'bid' or 'ask'")
    
    def best_bid(self) -> Optional[float]:
        """
        Get the best (highest) bid price.
        
        Returns:
            Best bid price, or None if no bids exist
        """
        return self.bids[0][0] if self.bids else None
    
    def best_ask(self) -> Optional[float]:
        """
        Get the best (lowest) ask price.
        
        Returns:
            Best ask price, or None if no asks exist
        """
        return self.asks[0][0] if self.asks else None
    
    def mid_price(self) -> Optional[float]:
        """
        Calculate the mid price: (best_bid + best_ask) / 2.
        
        Returns:
            Mid price, or None if either side is empty
        """
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return (best_bid + best_ask) / 2.0
    
    def spread(self) -> Optional[float]:
        """
        Calculate the spread: best_ask - best_bid.
        
        Returns:
            Spread, or None if either side is empty
        """
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return best_ask - best_bid
    
    def top_depth(self, k: int = None) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Get the top k levels for both bids and asks.
        
        Args:
            k: Number of levels to return (defaults to book depth)
            
        Returns:
            Tuple of (bids, asks) where each is a list of (price, size) tuples
        """
        k = k or self.depth
        return (self.bids[:k], self.asks[:k])
    
    def _validate_invariant(self) -> None:
        """
        Validate that best_bid < best_ask (fundamental market microstructure invariant).
        
        Logs a warning if the invariant is violated, which can happen during
        data issues or rapid market movements.
        """
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        
        if best_bid is not None and best_ask is not None:
            if best_bid >= best_ask:
                logger.warning(
                    f"Order book invariant violated: best_bid ({best_bid}) >= best_ask ({best_ask})"
                )
    
    def __repr__(self) -> str:
        """String representation of the order book."""
        return f"OrderBook(depth={self.depth}, bids={len(self.bids)}, asks={len(self.asks)})"
