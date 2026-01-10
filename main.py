"""
Main Backtest Engine

This module orchestrates the complete backtest simulation:
1. Loads order book data
2. Updates order book with each event
3. Computes signals
4. Generates strategy signals
5. Executes trades
6. Tracks PnL and accounting
7. Saves results to CSV and JSON

Run this script from the command line to execute a backtest.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import config

from microstructure import OrderBook, SignalEngine, L2Replayer
from trading import MeanReversionStrategy, ExecutionSimulator, Accountant
from analysis.backtest_metrics import generate_summary_metrics


class BacktestEngine:
    """
    Main backtest engine that orchestrates the simulation.
    
    This class ties together all components:
    - Order book management
    - Signal computation
    - Strategy execution
    - Trade execution
    - Accounting and PnL tracking
    
    Attributes:
        orderbook: OrderBook instance
        signal_engine: SignalEngine instance
        strategy: MeanReversionStrategy instance
        execution: ExecutionSimulator instance
        accountant: Accountant instance
        replayer: L2Replayer instance
        trade_log: List of executed trades
        pnl_history: List of cumulative PnL over time
        signal_history: List of signal values over time
    """
    
    def __init__(
        self,
        data_file: Path = None,
        initial_cash: float = 100000.0
    ):
        """
        Initialize the backtest engine.
        
        Args:
            data_file: Path to L2 data file (None = use default/generate synthetic)
            initial_cash: Starting cash balance
        """
        # Initialize components
        self.orderbook = OrderBook()
        self.signal_engine = SignalEngine()
        self.strategy = MeanReversionStrategy()
        self.execution = ExecutionSimulator()
        self.accountant = Accountant(initial_cash=initial_cash)
        
        # Initialize data replayer
        self.replayer = L2Replayer(data_file=data_file, orderbook=self.orderbook)
        
        # History tracking
        self.trade_log: List[Dict[str, Any]] = []
        self.pnl_history: List[float] = []
        self.signal_history: List[Dict[str, Any]] = []
        self.timestamps: List[datetime] = []
        
        print("Backtest engine initialized")
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete backtest simulation.
        
        This method iterates through all order book events, updates the book,
        computes signals, generates strategy signals, executes trades, and
        tracks results.
        
        Returns:
            Dictionary with backtest results and metrics
        """
        print(f"Starting backtest with {self.replayer.get_total_events()} events...")
        
        event_count = 0
        
        # Process each order book event
        for event in self.replayer:
            event_count += 1
            
            # Update order book
            if event['type'] == 'snapshot':
                self.orderbook.apply_snapshot(event['bids'], event['asks'])
            elif event['type'] == 'update':
                self.orderbook.apply_diff(
                    event['side'],
                    event['price'],
                    event['size'],
                    event.get('action', 'update')
                )
            
            # Compute signals
            signals = self.signal_engine.update(self.orderbook)
            
            # Store signal history
            signal_record = signals.copy()
            signal_record['timestamp'] = event['timestamp']
            self.signal_history.append(signal_record)
            self.timestamps.append(event['timestamp'])
            
            # Get current position
            current_position = self.accountant.position
            
            # Generate strategy signal
            strategy_signal = self.strategy.generate_signal(signals, current_position)
            
            # Execute trade if signal exists
            if strategy_signal is not None:
                side, quantity = strategy_signal
                
                # Execute market order
                fill_price, fill_size, fee, slippage = self.execution.execute_market_order(
                    self.orderbook,
                    side,
                    quantity
                )
                
                if fill_size > 0:
                    # Record fill in accounting
                    self.accountant.record_fill(
                        timestamp=event['timestamp'],
                        side=side,
                        fill_price=fill_price,
                        fill_size=fill_size,
                        fee=fee
                    )
                    
                    # Log trade
                    trade_record = {
                        'timestamp': event['timestamp'],
                        'side': side,
                        'price': fill_price,
                        'size': fill_size,
                        'fee': fee,
                        'slippage': slippage,
                        'position_after': self.accountant.position,
                        'cash_after': self.accountant.cash,
                    }
                    self.trade_log.append(trade_record)
            
            # Update PnL history
            mid_price = self.orderbook.mid_price()
            if mid_price is not None:
                metrics = self.accountant.get_metrics(current_mid_price=mid_price)
                self.pnl_history.append(metrics['total_pnl'])
            else:
                self.pnl_history.append(self.accountant.realized_pnl)
            
            # Progress update
            if event_count % 100 == 0:
                progress = self.replayer.get_progress() * 100
                print(f"Progress: {progress:.1f}% ({event_count}/{self.replayer.get_total_events()})")
        
        print("Backtest completed!")
        
        # Calculate final metrics
        results = self._calculate_results()
        
        return results
    
    def _calculate_results(self) -> Dict[str, Any]:
        """
        Calculate final backtest results and metrics.
        
        Returns:
            Dictionary with all results and metrics
        """
        # Calculate returns from PnL history
        returns = []
        if len(self.pnl_history) > 1:
            pnl_array = pd.Series(self.pnl_history)
            returns = pnl_array.diff().fillna(0).tolist()
        
        # Generate summary metrics
        metrics = generate_summary_metrics(
            trades=self.trade_log,
            pnl_history=self.pnl_history,
            returns=returns,
            risk_free_rate=config.RISK_FREE_RATE
        )
        
        # Add final accounting metrics
        final_mid_price = self.signal_history[-1]['mid_price'] if self.signal_history else None
        final_accounting = self.accountant.get_metrics(current_mid_price=final_mid_price)
        
        results = {
            'metrics': metrics,
            'final_accounting': final_accounting,
            'num_trades': len(self.trade_log),
            'num_events': len(self.signal_history),
        }
        
        return results
    
    def save_results(self, output_dir: Path = None) -> None:
        """
        Save backtest results to CSV and JSON files.
        
        Args:
            output_dir: Directory to save outputs (defaults to config OUTPUT_DIR)
        """
        output_dir = output_dir or config.OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save trades
        if self.trade_log:
            trades_df = pd.DataFrame(self.trade_log)
            trades_file = output_dir / "trades.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"Saved trades to {trades_file}")
        
        # Save PnL history
        if self.pnl_history and self.timestamps:
            pnl_df = pd.DataFrame({
                'timestamp': self.timestamps[:len(self.pnl_history)],
                'pnl': self.pnl_history,
            })
            pnl_file = output_dir / "pnl.csv"
            pnl_df.to_csv(pnl_file, index=False)
            print(f"Saved PnL history to {pnl_file}")
        
        # Save signal history
        if self.signal_history:
            signals_df = pd.DataFrame(self.signal_history)
            signals_file = output_dir / "signals.csv"
            signals_df.to_csv(signals_file, index=False)
            print(f"Saved signal history to {signals_file}")
        
        # Save metrics
        results = self._calculate_results()
        metrics_file = output_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Saved metrics to {metrics_file}")
        
        # Print summary
        print("\n" + "="*50)
        print("BACKTEST SUMMARY")
        print("="*50)
        print(f"Total Trades: {results['num_trades']}")
        print(f"Total PnL: ${results['final_accounting']['total_pnl']:.2f}")
        print(f"Realized PnL: ${results['final_accounting']['realized_pnl']:.2f}")
        print(f"Unrealized PnL: ${results['final_accounting']['unrealized_pnl']:.2f}")
        print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: ${results['metrics']['max_drawdown']:.2f} ({results['metrics']['max_drawdown_pct']:.2f}%)")
        print("="*50)


def main():
    """Main entry point for command-line backtest execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run market microstructure backtest')
    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='Path to L2 data CSV file (default: generate synthetic)'
    )
    parser.add_argument(
        '--cash',
        type=float,
        default=100000.0,
        help='Initial cash balance (default: 100000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory (default: outputs/)'
    )
    
    args = parser.parse_args()
    
    # Create backtest engine
    engine = BacktestEngine(
        data_file=Path(args.data) if args.data else None,
        initial_cash=args.cash
    )
    
    # Run backtest
    results = engine.run()
    
    # Save results
    output_dir = Path(args.output) if args.output else None
    engine.save_results(output_dir=output_dir)


if __name__ == '__main__':
    main()
