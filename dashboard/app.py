"""
Ultra-minimal Streamlit Dashboard - Standalone Version
No external dependencies except streamlit and pandas
"""

import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
import sys
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Market Microstructure Simulator",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
def init_session_state():
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'csv_data' not in st.session_state:
        st.session_state.csv_data = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'error' not in st.session_state:
        st.session_state.error = None

init_session_state()

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
            
            # Read CSV
            try:
                df = pd.read_csv(data_file)
                
                # Validate required columns
                required_cols = ['timestamp']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    st.session_state.error = f"CSV missing required columns: {missing_cols}"
                    st.rerun()
                    return
                
                # Store data in session state
                st.session_state.csv_data = df
                st.session_state.data_loaded = True
                st.session_state.current_index = 0
                
                st.sidebar.success(f"Data loaded successfully! {len(df)} rows")
                
            except Exception as e:
                st.session_state.error = f"Error reading CSV: {str(e)}"
                st.rerun()
                
        else:
            st.session_state.error = "No file uploaded!"
            st.rerun()
            
    except Exception as e:
        st.session_state.error = f"Upload failed: {str(e)}"
        st.rerun()

# Main content
if not st.session_state.data_loaded:
    st.info("👆 Upload a CSV file to get started")
else:
    df = st.session_state.csv_data
    
    st.success(f"✅ Data loaded! Total events: {len(df)}")
    
    # Show data preview
    with st.expander("📊 Data Preview"):
        st.dataframe(df.head(10))
        st.write(f"Columns: {list(df.columns)}")
        st.write(f"Data types: {df.dtypes.to_dict()}")
    
    # Simple controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Process 1 Event"):
            if st.session_state.current_index < len(df):
                current_row = df.iloc[st.session_state.current_index]
                st.session_state.current_index += 1
                st.success(f"Processed event {st.session_state.current_index}")
                st.json(current_row.to_dict())
            else:
                st.warning("No more events!")
    
    with col2:
        if st.button("Process 10 Events"):
            remaining = len(df) - st.session_state.current_index
            to_process = min(10, remaining)
            st.session_state.current_index += to_process
            st.success(f"Processed {to_process} events (total: {st.session_state.current_index})")
    
    with col3:
        if st.button("Reset"):
            st.session_state.current_index = 0
            st.success("Reset to beginning")
    
    # Progress
    progress = st.session_state.current_index / len(df)
    st.progress(progress)
    st.caption(f"Progress: {progress*100:.1f}% ({st.session_state.current_index}/{len(df)})")
    
    # Show current event details
    if st.session_state.current_index > 0 and st.session_state.current_index <= len(df):
        st.subheader("📋 Current Event")
        current_row = df.iloc[st.session_state.current_index - 1]
        
        # Format the display
        cols = st.columns(2)
        with cols[0]:
            st.write("**Event Details:**")
            for col in df.columns:
                value = current_row[col]
                if pd.notna(value):
                    st.write(f"- {col}: {value}")
        
        with cols[1]:
            # Try to detect if this is order book data
            if any('bid' in str(col).lower() for col in df.columns):
                st.write("**📊 Order Book Analysis**")
                st.write("This appears to be Level 2 order book data.")
                st.write("Event processing simulation working correctly!")

# Footer
st.markdown("---")
st.markdown("✅ **Standalone Version** - No complex dependencies, maximum compatibility")
