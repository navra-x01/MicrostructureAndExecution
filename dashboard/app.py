"""
Streamlit Dashboard for Market Microstructure Simulator - FIXED VERSION

This dashboard provides a safe, stable interface for:
- Top-5 order book display
- Mid-price chart with trade markers
- Signal charts (imbalance, z-score)
- PnL table and metrics summary
- Manual step-by-step controls only (no auto-play to prevent issues)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from pathlib import Path
import sys
import tempfile
import json
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from microstructure import OrderBook, SignalEngine, L2Replayer
from trading import MeanReversionStrategy, ExecutionSimulator, Accountant
from analysis.backtest_metrics import generate_summary_metrics
from main import BacktestEngine
import config


# Page configuration
st.set_page_config(
    page_title="Market Microstructure Simulator",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
def init_session_state():
    """Initialize all session state variables safely."""
    defaults = {
        'orderbook': OrderBook(),
        'signal_engine': SignalEngine(),
        'strategy': MeanReversionStrategy(),
        'execution': ExecutionSimulator(),
        'accountant': Accountant(),
        'replayer': None,
        'is_running': False,
        'is_paused': False,
        'replay_speed': 1.0,
        'trade_log': [],
        'pnl_history': [],
        'signal_history': [],
        'timestamps': [],
        'mid_prices': [],
        'current_event_index': 0,
        'data_loaded': False,
        'error_message': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
init_session_state()


def reset_simulation():
    """Reset the simulation to initial state."""
    st.session_state.orderbook = OrderBook()
    st.session_state.signal_engine = SignalEngine()
    st.session_state.strategy = MeanReversionStrategy()
    st.session_state.execution = ExecutionSimulator()
    st.session_state.accountant = Accountant()
    st.session_state.is_running = False
    st.session_state.is_paused = False
    st.session_state.trade_log = []
    st.session_state.pnl_history = []
    st.session_state.signal_history = []
    st.session_state.timestamps = []
    st.session_state.mid_prices = []
    st.session_state.current_event_index = 0
    st.session_state.error_message = None


def process_event(event):
    """Process a single order book event safely."""
    try:
        # Update order book
        if event['type'] == 'snapshot':
            st.session_state.orderbook.apply_snapshot(event['bids'], event['asks'])
        elif event['type'] == 'update':
            st.session_state.orderbook.apply_diff(
                event['side'],
                event['price'],
                event['size'],
                event.get('action', 'update')
            )
        
        # Compute signals
        signals = st.session_state.signal_engine.update(st.session_state.orderbook)
        
        # Store history
        signal_record = signals.copy()
        signal_record['timestamp'] = event['timestamp']
        st.session_state.signal_history.append(signal_record)
        st.session_state.timestamps.append(event['timestamp'])
        
        mid_price = signals.get('mid_price')
        if mid_price is not None:
            st.session_state.mid_prices.append(mid_price)
        else:
            if st.session_state.mid_prices:
                st.session_state.mid_prices.append(st.session_state.mid_prices[-1])
            else:
                st.session_state.mid_prices.append(0)
        
        # Generate strategy signal
        current_position = st.session_state.accountant.position
        strategy_signal = st.session_state.strategy.generate_signal(signals, current_position)
        
        # Execute trade if signal exists
        if strategy_signal is not None:
            side, quantity = strategy_signal
            
            fill_price, fill_size, fee, slippage = st.session_state.execution.execute_market_order(
                st.session_state.orderbook,
                side,
                quantity
            )
            
            if fill_size > 0:
                st.session_state.accountant.record_fill(
                    timestamp=event['timestamp'],
                    side=side,
                    fill_price=fill_price,
                    fill_size=fill_size,
                    fee=fee
                )
                
                trade_record = {
                    'timestamp': event['timestamp'],
                    'side': side,
                    'price': fill_price,
                    'size': fill_size,
                    'fee': fee,
                    'slippage': slippage,
                }
                st.session_state.trade_log.append(trade_record)
        
        # Update PnL history
        mid_price = st.session_state.orderbook.mid_price()
        if mid_price is not None:
            metrics = st.session_state.accountant.get_metrics(current_mid_price=mid_price)
            st.session_state.pnl_history.append(metrics['total_pnl'])
        else:
            st.session_state.pnl_history.append(st.session_state.accountant.realized_pnl)
            
    except Exception as e:
        st.session_state.error_message = f"Error processing event: {str(e)}"
        st.session_state.is_running = False


def safe_load_data(data_file):
    """Safely load and validate data."""
    try:
        if data_file is not None:
            # Validate file
            if data_file.size == 0:
                return "Uploaded file is empty!"
            
            # Check if it's actually a CSV
            if not data_file.name.lower().endswith('.csv'):
                return "Please upload a CSV file!"
            
            # Save temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                tmp_file.write(data_file.getbuffer())
                temp_path = Path(tmp_file.name)
            
            try:
                # Test read CSV first
                test_df = pd.read_csv(temp_path)
                
                # Check for required columns
                if 'timestamp' not in test_df.columns:
                    temp_path.unlink()
                    return "CSV must have a 'timestamp' column!"
                
                # Try to create replayer
                st.session_state.replayer = L2Replayer(data_file=temp_path, orderbook=st.session_state.orderbook)
                temp_path.unlink()  # Clean up
                
            except pd.errors.EmptyDataError:
                temp_path.unlink()
                return "CSV file is empty or invalid!"
            except pd.errors.ParserError as e:
                temp_path.unlink()
                return f"CSV parsing error: {str(e)}"
            except Exception as e:
                temp_path.unlink()
                return f"Error reading CSV: {str(e)}"
        else:
            # Use synthetic data
            st.session_state.replayer = L2Replayer(orderbook=st.session_state.orderbook)
        
        reset_simulation()
        st.session_state.data_loaded = True
        st.session_state.error_message = None
        return None
        
    except Exception as e:
        return f"Error loading data: {str(e)}"


# Main dashboard
st.title("📈 Market Microstructure Simulator")

# Display any error messages
if st.session_state.error_message:
    st.error(st.session_state.error_message)
    if st.button("Clear Error"):
        st.session_state.error_message = None
        st.rerun()

# Sidebar controls
st.sidebar.header("Controls")

# Data file selection
data_file = st.sidebar.file_uploader(
    "Upload L2 Data CSV",
    type=['csv'],
    help="Upload a CSV file with order book data, or use synthetic data"
)

if st.sidebar.button("Load Data", type="primary"):
    with st.sidebar.spinner("Loading data..."):
        error = safe_load_data(data_file)
        if error:
            st.sidebar.error(error)
            st.session_state.data_loaded = False
        else:
            st.sidebar.success("Data loaded successfully!")

# Manual controls only (no auto-play to prevent issues)
if st.session_state.data_loaded and st.session_state.replayer:
    st.sidebar.subheader("Manual Controls")
    
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        if st.button("▶️ Start", help="Begin simulation"):
            st.session_state.is_running = True
            st.session_state.is_paused = False
    
    with col2:
        if st.button("⏸️ Pause", help="Pause simulation"):
            st.session_state.is_paused = True
    
    with col3:
        if st.button("⏹️ Reset", help="Reset simulation"):
            reset_simulation()
            if st.session_state.replayer:
                st.session_state.replayer.reset()
    
    # Step button
    if st.sidebar.button("⏭️ Step Forward", help="Process one event"):
        if st.session_state.replayer is not None:
            try:
                event = next(st.session_state.replayer)
                process_event(event)
                st.session_state.current_event_index += 1
            except StopIteration:
                st.session_state.is_running = False
                st.sidebar.success("Simulation completed!")
    
    # Speed control
    st.session_state.replay_speed = st.sidebar.slider(
        "Display Speed",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="Speed for batch processing (not used in manual mode)"
    )

# Main content area
if not st.session_state.data_loaded:
    st.info("👆 Please load data using the sidebar controls to begin.")
else:
    # Process one event if running and not paused (manual mode only)
    if st.session_state.is_running and not st.session_state.is_paused:
        if st.session_state.replayer is not None:
            try:
                event = next(st.session_state.replayer)
                process_event(event)
                st.session_state.current_event_index += 1
                
                # Check if completed
                if st.session_state.current_event_index >= st.session_state.replayer.get_total_events():
                    st.session_state.is_running = False
                    st.sidebar.success("Simulation completed!")
                    
            except StopIteration:
                st.session_state.is_running = False
                st.sidebar.success("Simulation completed!")
    
    # Display current state
    if st.session_state.replayer:
        progress = st.session_state.replayer.get_progress()
        st.progress(progress)
        st.caption(f"Progress: {progress*100:.1f}% ({st.session_state.current_event_index}/{st.session_state.replayer.get_total_events()})")
    
    # Layout: Two columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📊 Order Book (Top 5)")
        
        # Display order book
        try:
            bids, asks = st.session_state.orderbook.top_depth(5)
            
            if bids or asks:
                # Create order book table
                ob_data = {
                    'Bid Size': [f"{size:.0f}" for _, size in bids] + [''] * max(0, 5 - len(bids)),
                    'Bid Price': [f"{price:.2f}" for price, _ in bids] + [''] * max(0, 5 - len(bids)),
                    'Ask Price': [f"{price:.2f}" for price, _ in asks] + [''] * max(0, 5 - len(asks)),
                    'Ask Size': [f"{size:.0f}" for _, size in asks] + [''] * max(0, 5 - len(asks)),
                }
                ob_df = pd.DataFrame(ob_data)
                st.dataframe(ob_df, use_container_width=True, hide_index=True)
                
                # Best bid/ask display
                best_bid = st.session_state.orderbook.best_bid()
                best_ask = st.session_state.orderbook.best_ask()
                mid_price = st.session_state.orderbook.mid_price()
                spread = st.session_state.orderbook.spread()
                
                st.metric("Best Bid", f"${best_bid:.2f}" if best_bid else "N/A")
                st.metric("Best Ask", f"${best_ask:.2f}" if best_ask else "N/A")
                st.metric("Mid Price", f"${mid_price:.2f}" if mid_price else "N/A")
                st.metric("Spread", f"${spread:.4f}" if spread else "N/A")
            else:
                st.info("Order book is empty. Start the simulation to see data.")
        except Exception as e:
            st.error(f"Error displaying order book: {str(e)}")
        
        # PnL Metrics
        st.subheader("💰 PnL Metrics")
        if st.session_state.mid_prices:
            try:
                current_mid = st.session_state.mid_prices[-1]
                metrics = st.session_state.accountant.get_metrics(current_mid_price=current_mid)
                
                st.metric("Position", f"{metrics['position']:.0f}")
                st.metric("Cash", f"${metrics['cash']:.2f}")
                st.metric("Realized PnL", f"${metrics['realized_pnl']:.2f}")
                st.metric("Unrealized PnL", f"${metrics['unrealized_pnl']:.2f}")
                st.metric("Total PnL", f"${metrics['total_pnl']:.2f}")
                st.metric("Total Value", f"${metrics['total_value']:.2f}")
            except Exception as e:
                st.error(f"Error calculating metrics: {str(e)}")
    
    with col2:
        # Mid-price chart with trades
        if st.session_state.mid_prices:
            try:
                fig = go.Figure()
                
                # Mid price line
                fig.add_trace(go.Scatter(
                    x=list(range(len(st.session_state.mid_prices))),
                    y=st.session_state.mid_prices,
                    mode='lines',
                    name='Mid Price',
                    line=dict(color='blue', width=2)
                ))
                
                # Trade markers
                if st.session_state.trade_log:
                    trade_indices = []
                    trade_prices = []
                    trade_colors = []
                    
                    for trade in st.session_state.trade_log:
                        # Find closest timestamp index
                        trade_ts = trade['timestamp']
                        if isinstance(trade_ts, str):
                            trade_ts = pd.to_datetime(trade_ts)
                        
                        # Find index in timestamps
                        try:
                            idx = st.session_state.timestamps.index(trade_ts)
                            if idx < len(st.session_state.mid_prices):
                                trade_indices.append(idx)
                                trade_prices.append(st.session_state.mid_prices[idx])
                                trade_colors.append('green' if trade['side'] == 'buy' else 'red')
                        except (ValueError, IndexError):
                            pass
                    
                    if trade_indices:
                        fig.add_trace(go.Scatter(
                            x=trade_indices,
                            y=trade_prices,
                            mode='markers',
                            name='Trades',
                            marker=dict(
                                size=10,
                                color=trade_colors,
                                symbol='triangle-up',
                                line=dict(width=2, color='black')
                            )
                        ))
                
                fig.update_layout(
                    title="Mid Price with Trade Markers",
                    xaxis_title="Event Index",
                    yaxis_title="Price ($)",
                    height=300,
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating price chart: {str(e)}")
        
        # Signal chart
        if st.session_state.signal_history:
            try:
                signal_df = pd.DataFrame(st.session_state.signal_history)
                
                # Create subplots
                fig = make_subplots(
                    rows=2,
                    cols=1,
                    subplot_titles=('Depth Imbalance', 'Z-Score'),
                    vertical_spacing=0.1
                )
                
                # Imbalance
                if 'depth_imbalance' in signal_df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=list(range(len(signal_df))),
                            y=signal_df['depth_imbalance'],
                            mode='lines',
                            name='Imbalance',
                            line=dict(color='purple')
                        ),
                        row=1, col=1
                    )
                
                # Z-score
                z_score_col = None
                if 'imbalance_zscore' in signal_df.columns:
                    z_score_col = 'imbalance_zscore'
                elif 'return_zscore' in signal_df.columns:
                    z_score_col = 'return_zscore'
                
                if z_score_col:
                    fig.add_trace(
                        go.Scatter(
                            x=list(range(len(signal_df))),
                            y=signal_df[z_score_col],
                            mode='lines',
                            name='Z-Score',
                            line=dict(color='orange')
                        ),
                        row=2, col=1
                    )
                    
                    # Add threshold lines
                    fig.add_hline(
                        y=config.Z_ENTRY_THRESHOLD,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Entry Threshold",
                        row=2, col=1
                    )
                    fig.add_hline(
                        y=-config.Z_ENTRY_THRESHOLD,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Entry Threshold",
                        row=2, col=1
                    )
                
                fig.update_layout(height=400, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating signal chart: {str(e)}")
        
        # Trade log table
        if st.session_state.trade_log:
            st.subheader("📋 Recent Trades")
            try:
                recent_trades = st.session_state.trade_log[-10:]  # Last 10 trades
                trades_df = pd.DataFrame(recent_trades)
                st.dataframe(trades_df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error displaying trades: {str(e)}")

# Full Backtest Runner Section (safe version)
st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Full Backtest Runner")

backtest_data_file = st.sidebar.file_uploader(
    "Upload Data for Full Backtest",
    type=['csv'],
    key="backtest_data",
    help="Run a complete backtest and download all results"
)

initial_cash = st.sidebar.number_input(
    "Initial Cash",
    min_value=1000.0,
    max_value=10000000.0,
    value=100000.0,
    step=10000.0
)

if st.sidebar.button("Run Full Backtest", type="primary", key="run_backtest"):
    if backtest_data_file is not None or True:  # Allow synthetic data
        try:
            with st.spinner("Running backtest... This may take a moment."):
                # Save uploaded file temporarily
                if backtest_data_file is not None:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                        tmp_file.write(backtest_data_file.getbuffer())
                        data_path = Path(tmp_file.name)
                else:
                    data_path = None
                
                # Create and run backtest engine
                engine = BacktestEngine(
                    data_file=data_path,
                    initial_cash=initial_cash
                )
                
                # Run backtest
                results = engine.run()
                
                # Store results in session state for download
                st.session_state.backtest_results = results
                st.session_state.backtest_trades = engine.trade_log
                st.session_state.backtest_pnl = engine.pnl_history
                st.session_state.backtest_signals = engine.signal_history
                st.session_state.backtest_timestamps = engine.timestamps
                
                # Clean up temp file
                if data_path and data_path.exists():
                    data_path.unlink()
                
                st.sidebar.success("Backtest completed!")
                st.balloons()
                
        except Exception as e:
            st.sidebar.error(f"Backtest failed: {str(e)}")
            st.exception(e)

# Display backtest results if available
if 'backtest_results' in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Backtest Summary")
    results = st.session_state.backtest_results
    st.sidebar.metric("Total Trades", results['num_trades'])
    st.sidebar.metric("Total PnL", f"${results['final_accounting']['total_pnl']:.2f}")
    st.sidebar.metric("Sharpe Ratio", f"{results['metrics']['sharpe_ratio']:.2f}")
    
    # Download buttons for full backtest results
    if st.session_state.backtest_trades:
        trades_df = pd.DataFrame(st.session_state.backtest_trades)
        csv_trades = trades_df.to_csv(index=False)
        st.sidebar.download_button(
            label="📥 Download All Trades",
            data=csv_trades,
            file_name="backtest_trades.csv",
            mime="text/csv",
            key="dl_trades"
        )
    
    if st.session_state.backtest_signals:
        signals_df = pd.DataFrame(st.session_state.backtest_signals)
        csv_signals = signals_df.to_csv(index=False)
        st.sidebar.download_button(
            label="📥 Download All Signals",
            data=csv_signals,
            file_name="backtest_signals.csv",
            mime="text/csv",
            key="dl_signals"
        )
    
    if st.session_state.backtest_pnl and st.session_state.backtest_timestamps:
        pnl_df = pd.DataFrame({
            'timestamp': st.session_state.backtest_timestamps[:len(st.session_state.backtest_pnl)],
            'pnl': st.session_state.backtest_pnl,
        })
        csv_pnl = pnl_df.to_csv(index=False)
        st.sidebar.download_button(
            label="📥 Download PnL History",
            data=csv_pnl,
            file_name="backtest_pnl.csv",
            mime="text/csv",
            key="dl_pnl"
        )
    
    json_results = json.dumps(results, indent=2, default=str)
    st.sidebar.download_button(
        label="📥 Download Metrics JSON",
        data=json_results,
        file_name="backtest_metrics.json",
        mime="application/json",
        key="dl_metrics"
    )
