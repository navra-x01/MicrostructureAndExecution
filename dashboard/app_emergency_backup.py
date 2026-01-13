"""
Ultra-minimal Streamlit Dashboard - Emergency Fix
"""

import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from microstructure import OrderBook, SignalEngine, L2Replayer
from trading import MeanReversionStrategy, ExecutionSimulator, Accountant

# Page configuration
st.set_page_config(
    page_title="Market Microstructure Simulator",
    page_icon="📈",
    layout="wide"
)

# Initialize session state with minimal variables
def init_minimal_state():
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'replayer' not in st.session_state:
        st.session_state.replayer = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'error' not in st.session_state:
        st.session_state.error = None

init_minimal_state()

# Main title
st.title("📈 Market Microstructure Simulator")

# Show error if any
if st.session_state.error:
    st.error(st.session_state.error)
    if st.button("Clear Error"):
        st.session_state.error = None
        st.rerun()

# Sidebar
st.sidebar.header("Data Upload")

# File upload
data_file = st.sidebar.file_uploader(
    "Upload L2 Data CSV",
    type=['csv']
)

# Load data button
if st.sidebar.button("Load Data", type="primary"):
    try:
        st.session_state.error = None
        
        if data_file is not None:
            # Basic validation
            if data_file.size == 0:
                st.session_state.error = "File is empty!"
                st.rerun()
                return
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                tmp_file.write(data_file.getbuffer())
                temp_path = Path(tmp_file.name)
            
            try:
                # Test CSV
                df = pd.read_csv(temp_path)
                if 'timestamp' not in df.columns:
                    st.session_state.error = "CSV must have 'timestamp' column!"
                    temp_path.unlink()
                    st.rerun()
                    return
                
                # Create replayer
                orderbook = OrderBook()
                st.session_state.replayer = L2Replayer(data_file=temp_path, orderbook=orderbook)
                temp_path.unlink()
                
                st.session_state.data_loaded = True
                st.session_state.current_index = 0
                st.sidebar.success("Data loaded successfully!")
                
            except Exception as e:
                temp_path.unlink()
                st.session_state.error = f"Error processing CSV: {str(e)}"
                st.rerun()
                
        else:
            # Use synthetic data
            orderbook = OrderBook()
            st.session_state.replayer = L2Replayer(orderbook=orderbook)
            st.session_state.data_loaded = True
            st.session_state.current_index = 0
            st.sidebar.success("Synthetic data loaded!")
            
    except Exception as e:
        st.session_state.error = f"Upload failed: {str(e)}"
        st.rerun()

# Main content
if not st.session_state.data_loaded:
    st.info("👆 Upload a CSV file to get started")
else:
    st.success(f"✅ Data loaded! Total events: {st.session_state.replayer.get_total_events()}")
    
    # Simple controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Process 1 Event"):
            try:
                if st.session_state.replayer:
                    event = next(st.session_state.replayer)
                    st.session_state.current_index += 1
                    st.success(f"Processed event {st.session_state.current_index}")
                    st.json(event)
            except StopIteration:
                st.warning("No more events!")
    
    with col2:
        if st.button("Process 10 Events"):
            try:
                for i in range(10):
                    if st.session_state.replayer:
                        next(st.session_state.replayer)
                        st.session_state.current_index += 1
                st.success(f"Processed 10 events (total: {st.session_state.current_index})")
            except StopIteration:
                st.warning("Reached end of data!")
    
    with col3:
        if st.button("Reset"):
            if st.session_state.replayer:
                st.session_state.replayer.reset()
            st.session_state.current_index = 0
            st.success("Reset to beginning")
    
    # Progress
    if st.session_state.replayer:
        progress = st.session_state.replayer.get_progress()
        st.progress(progress)
        st.caption(f"Progress: {progress*100:.1f}% ({st.session_state.current_index}/{st.session_state.replayer.get_total_events()})")

# Footer
st.markdown("---")
st.markdown("Emergency fix version - minimal functionality to prevent blank screens")
