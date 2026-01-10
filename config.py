"""
Configuration module for the Market Microstructure Simulator.

This module contains all configurable parameters for the simulation,
including order book settings, strategy parameters, execution settings,
and data paths.
"""

from pathlib import Path
from typing import Dict, Any

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Ensure output directory exists
try:
    OUTPUT_DIR.mkdir(exist_ok=True)
except Exception as e:
    # In Streamlit Cloud, directory creation might fail due to permissions
    # This is not critical for the app to run
    import warnings
    warnings.warn(f"Could not create output directory: {e}")

# Order Book Configuration
ORDER_BOOK_DEPTH = 5  # Number of levels to maintain (top 5 bids and asks)

# Signal Configuration
SIGNAL_WINDOW_SIZE = 100  # Rolling window size for z-score calculation
IMBALANCE_DEPTH = 5  # Depth to use for imbalance calculation

# Strategy Configuration
Z_ENTRY_THRESHOLD = 2.0  # Z-score threshold for entering positions
Z_EXIT_THRESHOLD = 0.5  # Z-score threshold for exiting positions (mean reversion)
ORDER_SIZE = 100  # Fixed order size (number of shares/contracts)

# Execution Configuration
MAKER_FEE = 0.001  # Maker fee rate (0.1%)
TAKER_FEE = 0.001  # Taker fee rate (0.1%) - we use market orders, so taker fee applies

# Data Configuration
DEFAULT_DATA_FILE = DATA_DIR / "sample_l2.csv"
SYNTHETIC_DATA_FILE = DATA_DIR / "synthetic_l2.csv"

# Synthetic Data Generation Parameters
SYNTHETIC_BASE_PRICE = 100.0  # Starting price for synthetic data
SYNTHETIC_NUM_SNAPSHOTS = 1000  # Number of snapshots to generate
SYNTHETIC_INTERVAL_MS = 150  # Milliseconds between snapshots
SYNTHETIC_PRICE_VOLATILITY = 0.5  # Standard deviation for price random walk
SYNTHETIC_SIZE_MIN = 10  # Minimum order size
SYNTHETIC_SIZE_MAX = 1000  # Maximum order size
SYNTHETIC_SPREAD_BPS = 5  # Spread in basis points (0.05%)

# Backtest Configuration
RISK_FREE_RATE = 0.0  # Risk-free rate for Sharpe ratio calculation (annualized)

# Dashboard Configuration
DASHBOARD_UPDATE_INTERVAL = 0.1  # Seconds between dashboard updates
DASHBOARD_MAX_POINTS = 1000  # Maximum data points to display in charts


def get_config() -> Dict[str, Any]:
    """
    Get all configuration parameters as a dictionary.
    
    Returns:
        Dictionary containing all configuration parameters
    """
    return {
        'order_book_depth': ORDER_BOOK_DEPTH,
        'signal_window_size': SIGNAL_WINDOW_SIZE,
        'imbalance_depth': IMBALANCE_DEPTH,
        'z_entry_threshold': Z_ENTRY_THRESHOLD,
        'z_exit_threshold': Z_EXIT_THRESHOLD,
        'order_size': ORDER_SIZE,
        'maker_fee': MAKER_FEE,
        'taker_fee': TAKER_FEE,
        'default_data_file': str(DEFAULT_DATA_FILE),
        'synthetic_data_file': str(SYNTHETIC_DATA_FILE),
        'risk_free_rate': RISK_FREE_RATE,
    }
