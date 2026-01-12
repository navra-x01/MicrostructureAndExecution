"""
Streamlit Dashboard for Market Microstructure Simulator

This dashboard provides a real-time visualization of:
- Top-5 order book display
- Mid-price chart with trade markers
- Signal charts (imbalance, z-score)
- PnL table and metrics summary
- Controls for start/pause/replay speed
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
if 'orderbook' not in st.session_state:
    st.session_state.orderbook = OrderBook()
    st.session_state.signal_engine = SignalEngine()
    st.session_state.strategy = MeanReversionStrategy()
    st.session_state.execution = ExecutionSimulator()
    st.session_state.accountant = Accountant()
    st.session_state.replayer = None
    st.session_state.is_running = False
    st.session_state.is_paused = False
    st.session_state.replay_speed = 1.0
    st.session_state.trade_log = []
    st.session_state.pnl_history = []
    st.session_state.signal_history = []
    st.session_state.timestamps = []
    st.session_state.mid_prices = []
    st.session_state.current_event_index = 0


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


def process_event(event):
    """Process a single order book event."""
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
        st.session_state.mid_prices.append(st.session_state.mid_prices[-1] if st.session_state.mid_prices else 0)
    
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


# Main dashboard
st.title("📈 Market Microstructure Simulator")

# Sidebar controls
st.sidebar.header("Controls")

# Data file selection
data_file = st.sidebar.file_uploader(
    "Upload L2 Data CSV",
    type=['csv'],
    help="Upload a CSV file with order book data, or use synthetic data"
)

if st.sidebar.button("Load Data", type="primary"):
    try:
        if data_file is not None:
            # Validate file content before processing
            if data_file.size == 0:
                st.sidebar.error("Uploaded file is empty!")
                st.session_state.replayer = None
                return
                
            # Save uploaded file temporarily using tempfile (cloud-compatible)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                tmp_file.write(data_file.getbuffer())
                temp_path = Path(tmp_file.name)
            
            # Validate CSV format before creating replayer
            try:
                test_df = pd.read_csv(temp_path)
                required_columns = ['timestamp']
                missing_cols = [col for col in required_columns if col not in test_df.columns]
                if missing_cols:
                    st.sidebar.error(f"CSV missing required columns: {missing_cols}")
                    st.session_state.replayer = None
                    temp_path.unlink()  # Clean up
                    return
                    
                st.session_state.replayer = L2Replayer(data_file=temp_path, orderbook=st.session_state.orderbook)
                
            except pd.errors.EmptyDataError:
                st.sidebar.error("CSV file is empty or invalid!")
                st.session_state.replayer = None
                temp_path.unlink()  # Clean up
                return
            except pd.errors.ParserError as e:
                st.sidebar.error(f"CSV parsing error: {str(e)}")
                st.session_state.replayer = None
                temp_path.unlink()  # Clean up
                return
            except Exception as e:
                st.sidebar.error(f"Error reading CSV: {str(e)}")
                st.session_state.replayer = None
                temp_path.unlink()  # Clean up
                return
        else:
            st.session_state.replayer = L2Replayer(orderbook=st.session_state.orderbook)
        
        reset_simulation()
        st.sidebar.success("Data loaded!")
        
    except Exception as e:
        st.sidebar.error(f"Error loading data: {str(e)}")
        st.session_state.replayer = None

# Replay controls
col1, col2, col3, col4 = st.sidebar.columns(4)

with col1:
    if st.button("▶️ Start"):
        if st.session_state.replayer is None:
            st.session_state.replayer = L2Replayer()
            reset_simulation()
        st.session_state.is_running = True
        st.session_state.is_paused = False

with col2:
    if st.button("⏸️ Pause"):
        st.session_state.is_paused = True

with col3:
    if st.button("⏹️ Reset"):
        reset_simulation()
        if st.session_state.replayer:
            st.session_state.replayer.reset()

with col4:
    if st.button("⏭️ Step"):
        if st.session_state.replayer is not None:
            try:
                event = next(st.session_state.replayer)
                process_event(event)
                st.session_state.current_event_index += 1
            except StopIteration:
                st.session_state.is_running = False
                st.sidebar.success("Replay completed!")

# Replay speed
st.session_state.replay_speed = st.sidebar.slider(
    "Replay Speed",
    min_value=0.1,
    max_value=10.0,
    value=1.0,
    step=0.1,
    help="Speed multiplier for replay (1.0 = normal speed)"
)

# Auto-play option
auto_play = st.sidebar.checkbox(
    "Auto-play (experimental)",
    value=False,
    help="Automatically step through events (may cause rapid updates)"
)

# Main content area
if st.session_state.replayer is None:
    st.info("👆 Please load data using the sidebar controls to begin.")
else:
    # Auto-play logic (safe implementation)
    if auto_play and st.session_state.is_running and not st.session_state.is_paused:
        try:
            # Process one event
            event = next(st.session_state.replayer)
            process_event(event)
            st.session_state.current_event_index += 1
            
            # Check if we've reached the end
            if st.session_state.current_event_index >= st.session_state.replayer.get_total_events():
                st.session_state.is_running = False
                st.sidebar.success("Replay completed!")
                auto_play = False
            else:
                # Schedule next update with delay
                time.sleep(0.1 / st.session_state.replay_speed)
                st.rerun()
                
        except StopIteration:
            st.session_state.is_running = False
            st.sidebar.success("Replay completed!")
            auto_play = False
    
    # Layout: Two columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📊 Order Book (Top 5)")
        
        # Display order book
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
        
        # PnL Metrics
        st.subheader("💰 PnL Metrics")
        if st.session_state.mid_prices:
            current_mid = st.session_state.mid_prices[-1]
            metrics = st.session_state.accountant.get_metrics(current_mid_price=current_mid)
            
            st.metric("Position", f"{metrics['position']:.0f}")
            st.metric("Cash", f"${metrics['cash']:.2f}")
            st.metric("Realized PnL", f"${metrics['realized_pnl']:.2f}")
            st.metric("Unrealized PnL", f"${metrics['unrealized_pnl']:.2f}")
            st.metric("Total PnL", f"${metrics['total_pnl']:.2f}")
            st.metric("Total Value", f"${metrics['total_value']:.2f}")
    
    with col2:
        # Mid-price chart with trades
        if st.session_state.mid_prices:
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
        
        # Signal chart
        if st.session_state.signal_history:
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
        
        # Trade log table
        if st.session_state.trade_log:
            st.subheader("📋 Recent Trades")
            recent_trades = st.session_state.trade_log[-10:]  # Last 10 trades
            trades_df = pd.DataFrame(recent_trades)
            st.dataframe(trades_df, use_container_width=True, hide_index=True)
    
    # Progress bar
    if st.session_state.replayer:
        progress = st.session_state.replayer.get_progress()
        st.progress(progress)
        st.caption(f"Progress: {progress*100:.1f}% ({st.session_state.current_event_index}/{st.session_state.replayer.get_total_events()})")
    
    # Download section for results
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Download Results")
    
    if st.session_state.trade_log or st.session_state.signal_history or st.session_state.pnl_history:
        # Download trades CSV
        if st.session_state.trade_log:
            trades_df = pd.DataFrame(st.session_state.trade_log)
            csv_trades = trades_df.to_csv(index=False)
            st.sidebar.download_button(
                label="Download Trades CSV",
                data=csv_trades,
                file_name="trades.csv",
                mime="text/csv"
            )
        
        # Download signals CSV
        if st.session_state.signal_history:
            signals_df = pd.DataFrame(st.session_state.signal_history)
            csv_signals = signals_df.to_csv(index=False)
            st.sidebar.download_button(
                label="Download Signals CSV",
                data=csv_signals,
                file_name="signals.csv",
                mime="text/csv"
            )
        
        # Download PnL CSV
        if st.session_state.pnl_history and st.session_state.timestamps:
            pnl_df = pd.DataFrame({
                'timestamp': st.session_state.timestamps[:len(st.session_state.pnl_history)],
                'pnl': st.session_state.pnl_history,
            })
            csv_pnl = pnl_df.to_csv(index=False)
            st.sidebar.download_button(
                label="Download PnL CSV",
                data=csv_pnl,
                file_name="pnl.csv",
                mime="text/csv"
            )
        
        # Download metrics JSON
        if st.session_state.mid_prices and st.session_state.trade_log:
            try:
                current_mid = st.session_state.mid_prices[-1]
                metrics = st.session_state.accountant.get_metrics(current_mid_price=current_mid)
                
                # Calculate summary metrics
                returns = []
                if len(st.session_state.pnl_history) > 1:
                    pnl_array = pd.Series(st.session_state.pnl_history)
                    returns = pnl_array.diff().fillna(0).tolist()
                
                summary_metrics = generate_summary_metrics(
                    trades=st.session_state.trade_log,
                    pnl_history=st.session_state.pnl_history,
                    returns=returns,
                    risk_free_rate=config.RISK_FREE_RATE
                )
                
                results = {
                    'metrics': summary_metrics,
                    'final_accounting': metrics,
                    'num_trades': len(st.session_state.trade_log),
                    'num_events': len(st.session_state.signal_history),
                }
                
                json_metrics = json.dumps(results, indent=2, default=str)
                st.sidebar.download_button(
                    label="Download Metrics JSON",
                    data=json_metrics,
                    file_name="metrics.json",
                    mime="application/json"
                )
            except Exception as e:
                st.sidebar.warning(f"Could not generate metrics: {str(e)}")
    
    # Full Backtest Runner Section
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