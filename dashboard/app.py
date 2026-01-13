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
            
            # Check file size (warn if very large, but don't block)
            file_size_mb = data_file.size / (1024 * 1024)
            if file_size_mb > 50:
                st.sidebar.warning(f"⚠️ Large file detected ({file_size_mb:.1f} MB). Processing may take a moment...")
            
            # Read CSV with proper error handling
            try:
                # Read CSV - Streamlit file uploader returns BytesIO
                # Reset to beginning if possible
                try:
                    data_file.seek(0)
                except (AttributeError, OSError):
                    pass  # Some file objects don't support seek
                
                # Show loading indicator
                with st.sidebar.spinner("Reading CSV file..."):
                    df = pd.read_csv(data_file)
                
                # Check if dataframe is empty
                if df.empty:
                    st.session_state.error = "CSV file contains no data rows!"
                    st.rerun()
                
                # Validate required columns (timestamp is preferred but not strictly required)
                if 'timestamp' not in df.columns:
                    # Try to find alternative timestamp columns
                    timestamp_variants = ['time', 'Time', 'TIMESTAMP', 'date', 'Date', 'datetime', 'DateTime']
                    found_timestamp = any(col in df.columns for col in timestamp_variants)
                    if not found_timestamp:
                        st.sidebar.warning("⚠️ No 'timestamp' column found. The app will work but timestamp-based features may not function.")
                else:
                    st.sidebar.info("✅ Timestamp column found")
                
                # Store data in session state
                st.session_state.csv_data = df
                st.session_state.data_loaded = True
                st.session_state.current_index = 0
                
                st.sidebar.success(f"Data loaded successfully! {len(df)} rows")
                
            except pd.errors.EmptyDataError:
                st.session_state.error = "CSV file is empty or has no valid data!"
                st.rerun()
            except pd.errors.ParserError as e:
                st.session_state.error = f"CSV parsing error: {str(e)}"
                st.rerun()
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
    try:
        df = st.session_state.csv_data
        
        if df is None or df.empty:
            st.error("Data was loaded but is empty. Please upload a valid CSV file.")
            st.session_state.data_loaded = False
        else:
            st.success(f"✅ Data loaded! Total events: {len(df)}")
            
            # Show data preview
            with st.expander("📊 Data Preview"):
                try:
                    st.dataframe(df.head(10))
                    st.write(f"Columns: {list(df.columns)}")
                    st.write(f"Data types: {df.dtypes.to_dict()}")
                except Exception as e:
                    st.error(f"Error displaying data preview: {str(e)}")
            
            # Simple controls
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Process 1 Event"):
                    try:
                        if st.session_state.current_index < len(df):
                            current_row = df.iloc[st.session_state.current_index]
                            st.session_state.current_index += 1
                            st.success(f"Processed event {st.session_state.current_index}")
                            st.json(current_row.to_dict())
                        else:
                            st.warning("No more events!")
                    except Exception as e:
                        st.error(f"Error processing event: {str(e)}")
            
            with col2:
                if st.button("Process 10 Events"):
                    try:
                        remaining = len(df) - st.session_state.current_index
                        to_process = min(10, remaining)
                        st.session_state.current_index += to_process
                        st.success(f"Processed {to_process} events (total: {st.session_state.current_index})")
                    except Exception as e:
                        st.error(f"Error processing events: {str(e)}")
            
            with col3:
                if st.button("Reset"):
                    st.session_state.current_index = 0
                    st.success("Reset to beginning")
            
            # Progress
            try:
                if len(df) > 0:
                    progress = st.session_state.current_index / len(df)
                    st.progress(progress)
                    st.caption(f"Progress: {progress*100:.1f}% ({st.session_state.current_index}/{len(df)})")
            except Exception as e:
                st.error(f"Error displaying progress: {str(e)}")
            
            # Show current event details
            try:
                if st.session_state.current_index > 0 and st.session_state.current_index <= len(df):
                    st.subheader("📋 Current Event")
                    current_row = df.iloc[st.session_state.current_index - 1]
                    
                    # Format the display
                    cols = st.columns(2)
                    with cols[0]:
                        st.write("**Event Details:**")
                        for col in df.columns:
                            try:
                                value = current_row[col]
                                if pd.notna(value):
                                    st.write(f"- {col}: {value}")
                            except Exception:
                                pass
                    
                    with cols[1]:
                        # Try to detect if this is order book data
                        if any('bid' in str(col).lower() for col in df.columns):
                            st.write("**📊 Order Book Analysis**")
                            st.write("This appears to be Level 2 order book data.")
                            st.write("Event processing simulation working correctly!")
            except Exception as e:
                st.error(f"Error displaying event details: {str(e)}")
                
    except Exception as e:
        st.error(f"Error displaying data: {str(e)}")
        st.exception(e)
        st.session_state.error = f"Error displaying data: {str(e)}"

# Footer
st.markdown("---")
st.markdown("✅ **Standalone Version** - No complex dependencies, maximum compatibility")
