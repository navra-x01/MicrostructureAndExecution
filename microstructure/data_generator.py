"""
Synthetic L2 Data Generator

This module generates realistic Level 2 order book data for testing and
demonstration purposes. It creates order book snapshots with realistic
price movements and liquidity patterns.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
import config


def generate_synthetic_l2_data(
    output_file: Path = None,
    base_price: float = None,
    num_snapshots: int = None,
    interval_ms: int = None,
    price_volatility: float = None,
    size_min: int = None,
    size_max: int = None,
    spread_bps: int = None,
    depth: int = None
) -> pd.DataFrame:
    """
    Generate synthetic Level 2 order book data.
    
    This function creates realistic order book snapshots with:
    - Random walk price movements
    - Realistic bid-ask spreads
    - Varying order sizes
    - Multiple price levels on each side
    
    Args:
        output_file: Path to save CSV file (defaults to config)
        base_price: Starting price (defaults to config)
        num_snapshots: Number of snapshots to generate (defaults to config)
        interval_ms: Milliseconds between snapshots (defaults to config)
        price_volatility: Price volatility (std dev) (defaults to config)
        size_min: Minimum order size (defaults to config)
        size_max: Maximum order size (defaults to config)
        spread_bps: Spread in basis points (defaults to config)
        depth: Number of levels per side (defaults to config)
        
    Returns:
        DataFrame with columns: timestamp, type, and order book data
    """
    # Use config defaults if not provided
    output_file = output_file or config.SYNTHETIC_DATA_FILE
    base_price = base_price or config.SYNTHETIC_BASE_PRICE
    num_snapshots = num_snapshots or config.SYNTHETIC_NUM_SNAPSHOTS
    interval_ms = interval_ms or config.SYNTHETIC_INTERVAL_MS
    price_volatility = price_volatility or config.SYNTHETIC_PRICE_VOLATILITY
    size_min = size_min or config.SYNTHETIC_SIZE_MIN
    size_max = size_max or config.SYNTHETIC_SIZE_MAX
    spread_bps = spread_bps or config.SYNTHETIC_SPREAD_BPS
    depth = depth or config.ORDER_BOOK_DEPTH
    
    # Initialize price with random walk
    current_price = base_price
    
    # Generate timestamps
    timestamps = pd.date_range(
        start='2024-01-01 09:30:00',
        periods=num_snapshots,
        freq=f'{interval_ms}ms'
    )
    
    rows = []
    
    for i, timestamp in enumerate(timestamps):
        # Random walk for price
        price_change = np.random.normal(0, price_volatility)
        current_price = max(0.01, current_price + price_change)  # Ensure positive price
        
        # Calculate spread
        spread = current_price * (spread_bps / 10000)
        
        # Generate bid levels (below mid price)
        mid_price = current_price
        bids = []
        for level in range(depth):
            # Price decreases as we go deeper
            price_offset = (level + 1) * spread / depth
            bid_price = mid_price - spread/2 - price_offset
            bid_size = np.random.uniform(size_min, size_max)
            bids.append((bid_price, bid_size))
        
        # Generate ask levels (above mid price)
        asks = []
        for level in range(depth):
            # Price increases as we go deeper
            price_offset = (level + 1) * spread / depth
            ask_price = mid_price + spread/2 + price_offset
            ask_size = np.random.uniform(size_min, size_max)
            asks.append((ask_price, ask_size))
        
        # Create snapshot row
        row = {
            'timestamp': timestamp,
            'type': 'snapshot',
        }
        
        # Add bid columns
        for level, (price, size) in enumerate(bids, 1):
            row[f'bid_price_{level}'] = round(price, 2)
            row[f'bid_size_{level}'] = round(size, 0)
        
        # Add ask columns
        for level, (price, size) in enumerate(asks, 1):
            row[f'ask_price_{level}'] = round(price, 2)
            row[f'ask_size_{level}'] = round(size, 0)
        
        rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Save to CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f"Generated {num_snapshots} synthetic L2 snapshots saved to {output_file}")
    
    return df
