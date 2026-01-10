"""
L2 Data Replayer Module

This module loads and replays Level 2 order book data from CSV files.
It supports both snapshot and incremental update formats, and can generate
synthetic data if no file is provided.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Iterator, Tuple, Optional, Dict, Any
from datetime import datetime
import config
from .orderbook import OrderBook
from .data_generator import generate_synthetic_l2_data


class L2Replayer:
    """
    Replays Level 2 order book data from CSV files.
    
    This class loads order book data and emits events in chronological order.
    It supports flexible CSV formats including both snapshots and incremental
    updates.
    
    Attributes:
        data: DataFrame containing the loaded data
        current_index: Current position in the data
        orderbook: OrderBook instance (optional, for validation)
    """
    
    def __init__(self, data_file: Path = None, orderbook: OrderBook = None):
        """
        Initialize the replayer.
        
        Args:
            data_file: Path to CSV file (if None, generates synthetic data)
            orderbook: Optional OrderBook instance for validation
        """
        self.orderbook = orderbook
        self.current_index = 0
        
        if data_file is None or not Path(data_file).exists():
            # Generate synthetic data if file doesn't exist
            print(f"Data file not found. Generating synthetic data...")
            data_file = config.SYNTHETIC_DATA_FILE
            generate_synthetic_l2_data(output_file=data_file)
        
        # Load data
        self.data = pd.read_csv(data_file)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data = self.data.sort_values('timestamp').reset_index(drop=True)
        
        print(f"Loaded {len(self.data)} order book events from {data_file}")
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Make the replayer iterable."""
        return self
    
    def __next__(self) -> Dict[str, Any]:
        """
        Get the next order book event.
        
        Returns:
            Dictionary with event data:
            - timestamp: Event timestamp
            - type: 'snapshot' or 'update'
            - data: Order book data (bids/asks or update details)
            
        Raises:
            StopIteration: When all events have been replayed
        """
        if self.current_index >= len(self.data):
            raise StopIteration
        
        row = self.data.iloc[self.current_index]
        self.current_index += 1
        
        event_type = row.get('type', 'snapshot').lower()
        
        if event_type == 'snapshot':
            return self._parse_snapshot(row)
        elif event_type == 'update':
            return self._parse_update(row)
        else:
            # Try to infer type from columns
            if 'bid_price_1' in row.index or 'ask_price_1' in row.index:
                return self._parse_snapshot(row)
            else:
                return self._parse_update(row)
    
    def _parse_snapshot(self, row: pd.Series) -> Dict[str, Any]:
        """
        Parse a snapshot row into bids and asks.
        
        Args:
            row: DataFrame row containing snapshot data
            
        Returns:
            Dictionary with timestamp, type='snapshot', bids, and asks
        """
        bids = []
        asks = []
        
        # Extract bid levels
        level = 1
        while f'bid_price_{level}' in row.index:
            price = row[f'bid_price_{level}']
            size = row[f'bid_size_{level}']
            if pd.notna(price) and pd.notna(size) and price > 0 and size > 0:
                bids.append((float(price), float(size)))
            level += 1
        
        # Extract ask levels
        level = 1
        while f'ask_price_{level}' in row.index:
            price = row[f'ask_price_{level}']
            size = row[f'ask_size_{level}']
            if pd.notna(price) and pd.notna(size) and price > 0 and size > 0:
                asks.append((float(price), float(size)))
            level += 1
        
        return {
            'timestamp': row['timestamp'],
            'type': 'snapshot',
            'bids': bids,
            'asks': asks,
        }
    
    def _parse_update(self, row: pd.Series) -> Dict[str, Any]:
        """
        Parse an update row.
        
        Args:
            row: DataFrame row containing update data
            
        Returns:
            Dictionary with timestamp, type='update', side, price, size, action
        """
        return {
            'timestamp': row['timestamp'],
            'type': 'update',
            'side': row.get('side', 'bid').lower(),
            'price': float(row.get('price', 0)),
            'size': float(row.get('size', 0)),
            'action': row.get('action', 'update').lower(),
        }
    
    def reset(self) -> None:
        """Reset the replayer to the beginning."""
        self.current_index = 0
    
    def has_next(self) -> bool:
        """Check if there are more events to replay."""
        return self.current_index < len(self.data)
    
    def get_progress(self) -> float:
        """
        Get replay progress as a fraction (0.0 to 1.0).
        
        Returns:
            Progress fraction
        """
        if len(self.data) == 0:
            return 0.0
        return self.current_index / len(self.data)
    
    def get_total_events(self) -> int:
        """Get total number of events."""
        return len(self.data)
