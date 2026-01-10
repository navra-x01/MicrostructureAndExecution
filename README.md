# Market Microstructure + Execution Simulator

A complete, beginner-friendly Python project for simulating market microstructure, computing trading signals, executing strategies, and visualizing results. This project demonstrates key concepts in quantitative finance including order book management, signal generation, execution simulation, and backtesting.

## Features

- **Order Book Management**: Maintains top-5 bid/ask levels with snapshot and incremental update support
- **Signal Computation**: Calculates mid-price, spread, depth imbalance, and z-scores
- **Mean Reversion Strategy**: Z-score based trading strategy with configurable thresholds
- **Execution Simulation**: Realistic market order fills with book walking and slippage
- **PnL Tracking**: Comprehensive accounting with realized/unrealized PnL
- **Backtesting Engine**: Complete simulation framework with CSV/JSON output
- **Streamlit Dashboard**: Interactive visualization of order book, signals, trades, and metrics
- **Synthetic Data Generation**: Generate realistic L2 order book data for testing

## Project Structure

```
project2/
├── data/                    # Data files (CSV)
├── microstructure/          # Core microstructure modules
│   ├── orderbook.py        # Order book management
│   ├── signals.py          # Signal computation
│   ├── replayer.py         # Data replay engine
│   └── data_generator.py   # Synthetic data generation
├── trading/                 # Trading modules
│   ├── strategy.py         # Mean reversion strategy
│   ├── execution.py        # Execution simulator
│   └── accounting.py       # PnL tracking
├── dashboard/              # Streamlit dashboard
│   └── app.py
├── analysis/               # Analysis modules
│   └── backtest_metrics.py # Performance metrics
├── tests/                  # Unit tests
├── config.py               # Configuration
├── main.py                 # Backtest engine
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Installation

1. **Clone or download this project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import pandas, numpy, streamlit, plotly; print('All dependencies installed!')"
   ```

## Quick Start

### Running a Backtest

Run a backtest from the command line:

```bash
python main.py
```

This will:
- Generate synthetic L2 data if no file is provided
- Run the simulation with default parameters
- Save results to `outputs/` directory:
  - `trades.csv` - All executed trades
  - `pnl.csv` - PnL history over time
  - `signals.csv` - Signal values over time
  - `metrics.json` - Summary performance metrics

**Custom options**:
```bash
python main.py --data data/my_l2_data.csv --cash 200000 --output my_results/
```

### Using the Dashboard

Launch the Streamlit dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard provides:
- **Order Book Display**: Real-time top-5 bid/ask levels
- **Price Chart**: Mid-price with trade markers (green=buy, red=sell)
- **Signal Charts**: Depth imbalance and z-score visualization
- **PnL Metrics**: Position, cash, realized/unrealized PnL
- **Trade Log**: Recent executed trades
- **Controls**: Start/Pause/Reset buttons and replay speed slider

### Running Tests

Run unit tests:

```bash
pytest tests/
```

Run specific test file:

```bash
pytest tests/test_orderbook.py
```

## Configuration

Edit `config.py` to customize:

- **Order Book**: Depth (default: 5 levels)
- **Signals**: Window size for z-score calculation (default: 100)
- **Strategy**: Z-score entry/exit thresholds (default: 2.0 / 0.5)
- **Execution**: Order size, fees (default: 100 shares, 0.1% taker fee)
- **Data**: File paths, synthetic data parameters

## Data Format

The simulator supports flexible CSV formats:

### Snapshot Format
```csv
timestamp,type,bid_price_1,bid_size_1,bid_price_2,bid_size_2,...,ask_price_1,ask_size_1,...
2024-01-01 09:30:00,snapshot,100.0,10,99.0,20,...,101.0,10,102.0,20,...
```

### Update Format
```csv
timestamp,type,side,price,size,action
2024-01-01 09:30:01,update,bid,100.5,15,update
2024-01-01 09:30:02,update,ask,101.5,0,remove
```

If no data file is provided, synthetic data is automatically generated.

## Key Concepts

### Order Book
The order book maintains the top N bid and ask levels. Bids are sorted descending (highest first), asks ascending (lowest first). The fundamental invariant is: `best_bid < best_ask`.

### Signals
- **Mid Price**: `(best_bid + best_ask) / 2`
- **Spread**: `best_ask - best_bid`
- **Depth Imbalance**: `(bid_size - ask_size) / (bid_size + ask_size)`
- **Z-Score**: Standardized measure of how extreme a value is relative to its history

### Strategy
The mean reversion strategy:
- Enters long when z-score < -threshold (price is low)
- Enters short when z-score > +threshold (price is high)
- Exits when z-score returns toward zero (mean reversion occurred)

### Execution
Market orders execute immediately:
- Buy orders: Start at best_ask, walk up if size exceeds top level
- Sell orders: Start at best_bid, walk down if size exceeds top level
- Fees and slippage are calculated and tracked

### Accounting
Tracks:
- Position size (positive=long, negative=short)
- Average entry price
- Cash balance
- Realized PnL (from closed positions)
- Unrealized PnL (mark-to-market on open positions)

## Example Usage

### Python API

```python
from microstructure import OrderBook, SignalEngine, L2Replayer
from trading import MeanReversionStrategy, ExecutionSimulator, Accountant
from main import BacktestEngine

# Create and run backtest
engine = BacktestEngine(data_file="data/sample_l2.csv")
results = engine.run()
engine.save_results()

# Access results
print(f"Total PnL: ${results['final_accounting']['total_pnl']:.2f}")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
```

### Custom Strategy

```python
from trading.strategy import MeanReversionStrategy

# Create strategy with custom parameters
strategy = MeanReversionStrategy(
    z_entry_threshold=2.5,  # More conservative entry
    z_exit_threshold=0.3,    # Earlier exit
    order_size=50            # Smaller position size
)
```

## Performance Metrics

The backtest calculates:
- **Total PnL**: Final profit/loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Win Rate**: Percentage of profitable trades
- **Max Drawdown**: Largest peak-to-trough decline
- **Average Trade PnL**: Average profit per trade

## Limitations & Future Enhancements

Current limitations:
- Single-asset only (no portfolio)
- Market orders only (no limit orders)
- No latency simulation
- Simplified win rate calculation

Potential enhancements:
- Multi-asset support
- Limit order simulation
- Latency modeling
- More sophisticated strategies
- Real-time data feeds

## Contributing

This is an educational project. Feel free to:
- Add new strategies
- Improve signal calculations
- Enhance the dashboard
- Add more tests
- Improve documentation

## License

This project is provided as-is for educational purposes.

## References

- Market Microstructure Theory by Maureen O'Hara
- Algorithmic Trading by Ernest Chan
- Quantitative Trading by Ernie Chan

## Deployment

### Deploy to Streamlit Cloud

This project can be deployed to Streamlit Cloud for free, making it accessible to anyone via a web browser.

**Quick Deployment Steps:**

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**:
   - Go to [https://share.streamlit.io/](https://share.streamlit.io/)
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository and branch
   - Set Main file path to: `streamlit_app.py`
   - Click "Deploy!"

3. **Share your app**:
   - Once deployed, you'll get a public URL like `https://your-app-name.streamlit.app`
   - Share this URL with anyone!

**For detailed deployment instructions**, see [README_DEPLOYMENT.md](README_DEPLOYMENT.md)

**Features available after deployment:**
- Interactive dashboard accessible from any browser
- Upload custom data files
- Run full backtests
- Download results (CSV/JSON)
- Real-time visualization of order book and signals

## Support

For questions or issues:
1. Check the code comments (extensive documentation included)
2. Review the test files for usage examples
3. Examine `main.py` for the complete workflow
4. See [README_DEPLOYMENT.md](README_DEPLOYMENT.md) for deployment help

---

**Built with**: Python 3.8+, pandas, numpy, streamlit, plotly

**Author**: Market Microstructure Simulator Project

**Version**: 1.0.0
