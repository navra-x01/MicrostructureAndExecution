"""
Trading Strategy Module

This module implements a simple mean reversion strategy based on z-scores.
The strategy enters positions when z-scores are extreme (indicating potential
mean reversion) and exits when they return toward the mean.
"""

from typing import Optional, Tuple
import config


class MeanReversionStrategy:
    """
    Mean reversion strategy based on z-score signals.
    
    This strategy assumes that extreme z-scores (either positive or negative)
    will revert to the mean. It enters positions when z-scores exceed thresholds
    and exits when they return toward zero.
    
    Strategy logic:
    - Buy when z-score < -Z_ENTRY (price is low relative to history)
    - Sell when z-score > +Z_ENTRY (price is high relative to history)
    - Exit when z-score returns toward 0 (mean reversion occurred)
    
    Attributes:
        z_entry_threshold: Z-score threshold for entering positions
        z_exit_threshold: Z-score threshold for exiting positions
        order_size: Fixed order size
        current_position: Current position side ('long', 'short', or None)
    """
    
    def __init__(
        self,
        z_entry_threshold: float = None,
        z_exit_threshold: float = None,
        order_size: float = None
    ):
        """
        Initialize the mean reversion strategy.
        
        Args:
            z_entry_threshold: Z-score threshold for entry (defaults to config)
            z_exit_threshold: Z-score threshold for exit (defaults to config)
            order_size: Fixed order size (defaults to config)
        """
        self.z_entry_threshold = z_entry_threshold or config.Z_ENTRY_THRESHOLD
        self.z_exit_threshold = z_exit_threshold or config.Z_EXIT_THRESHOLD
        self.order_size = order_size or config.ORDER_SIZE
        
        # Track current position state
        self.current_position = None  # 'long', 'short', or None
        self.entry_z_score = None  # Z-score when position was entered
    
    def generate_signal(
        self,
        signals: dict,
        current_position: float
    ) -> Optional[Tuple[str, float]]:
        """
        Generate a trading signal based on current signals and position.
        
        The strategy uses z-score of imbalance or returns to determine
        entry and exit points. It prefers imbalance z-score if available,
        otherwise falls back to return z-score.
        
        Args:
            signals: Dictionary of current signals (from SignalEngine)
            current_position: Current position size (positive = long, negative = short)
            
        Returns:
            Tuple of (side, quantity) if signal exists, None otherwise:
            - side: 'buy' or 'sell'
            - quantity: Order size
        """
        # Prefer imbalance z-score, fall back to return z-score
        z_score = signals.get('imbalance_zscore')
        if z_score is None:
            z_score = signals.get('return_zscore')
        
        if z_score is None:
            return None
        
        # Determine current position state
        if current_position > 0:
            position_state = 'long'
        elif current_position < 0:
            position_state = 'short'
        else:
            position_state = None
        
        # Entry logic: enter when z-score is extreme
        if position_state is None:
            # No position - look for entry
            if z_score < -self.z_entry_threshold:
                # Z-score is very negative - buy (mean reversion up)
                self.current_position = 'long'
                self.entry_z_score = z_score
                return ('buy', self.order_size)
            elif z_score > self.z_entry_threshold:
                # Z-score is very positive - sell (mean reversion down)
                self.current_position = 'short'
                self.entry_z_score = z_score
                return ('sell', self.order_size)
        
        # Exit logic: exit when z-score returns toward mean
        elif position_state == 'long':
            # We're long - exit if z-score has reverted
            if z_score >= -self.z_exit_threshold:
                # Z-score has moved back toward zero - exit long
                self.current_position = None
                self.entry_z_score = None
                return ('sell', abs(current_position))  # Close position
        
        elif position_state == 'short':
            # We're short - exit if z-score has reverted
            if z_score <= self.z_exit_threshold:
                # Z-score has moved back toward zero - exit short
                self.current_position = None
                self.entry_z_score = None
                return ('buy', abs(current_position))  # Close position
        
        # No signal
        return None
    
    def reset(self) -> None:
        """Reset strategy state (useful for new backtests)."""
        self.current_position = None
        self.entry_z_score = None
