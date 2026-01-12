"""
Streamlit App Entry Point for Streamlit Cloud Deployment

This file serves as the main entry point for Streamlit Cloud.
It imports and runs the dashboard application.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the dashboard with error handling
try:
    import streamlit as st
    # Import the dashboard module and execute it
    import dashboard.app
except ImportError as e:
    import streamlit as st
    st.error(f"Import error: {e}")
    st.error("Please check the dashboard module dependencies")
    st.stop()
except Exception as e:
    import streamlit as st
    st.error(f"Runtime error: {e}")
    st.error("An error occurred while running the dashboard")
    st.stop()
