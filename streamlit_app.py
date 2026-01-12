"""
Streamlit App Entry Point for Streamlit Cloud Deployment

This file serves as the main entry point for Streamlit Cloud.
It imports and runs the dashboard application.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the dashboard
import dashboard.app
