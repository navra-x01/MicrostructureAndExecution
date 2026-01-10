"""
Streamlit App Entry Point for Streamlit Cloud Deployment

This file serves as the main entry point for Streamlit Cloud.
It imports and runs the dashboard application.
"""

import sys
from pathlib import Path
import json
import traceback

# #region agent log
log_path = Path(__file__).parent / ".cursor" / "debug.log"
try:
    with open(log_path, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "startup", "hypothesisId": "A", "location": "streamlit_app.py:12", "message": "Starting streamlit_app.py", "data": {"parent": str(Path(__file__).parent)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
except: pass
# #endregion

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# #region agent log
try:
    with open(log_path, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "startup", "hypothesisId": "A", "location": "streamlit_app.py:18", "message": "Path added to sys.path", "data": {"project_root": str(project_root), "sys_path_0": sys.path[0] if sys.path else "empty"}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
except: pass
# #endregion

# Import and run the dashboard
try:
    # #region agent log
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "startup", "hypothesisId": "B", "location": "streamlit_app.py:23", "message": "About to import dashboard.app", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    
    from dashboard.app import *
    
    # #region agent log
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "startup", "hypothesisId": "B", "location": "streamlit_app.py:30", "message": "Successfully imported dashboard.app", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "startup", "hypothesisId": "B", "location": "streamlit_app.py:35", "message": "Import failed", "data": {"error": str(e), "traceback": traceback.format_exc()}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    # Display error in Streamlit UI
    import streamlit as st
    st.error("❌ **Application Startup Error**")
    st.exception(e)
    st.code(traceback.format_exc(), language="python")
    st.stop()
