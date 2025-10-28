#!/usr/bin/env python3
"""Test script to check app dependencies."""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing imports...")
    
    # Test basic imports
    import streamlit as st
    print("✓ Streamlit imported successfully")
    
    # Test project imports
    from src.models.session import Session
    print("✓ Session model imported successfully")
    
    from src.models.speaker import Speaker
    print("✓ Speaker model imported successfully")
    
    from src.services.session_service import get_all_sessions
    print("✓ Session service imported successfully")
    
    from src.ui.dashboard import render_dashboard
    print("✓ Dashboard UI imported successfully")
    
    from src.ui.session_detail import render_session_detail
    print("✓ Session detail UI imported successfully")
    
    # Test data loading
    sessions = get_all_sessions()
    print(f"✓ Loaded {len(sessions)} sessions from data")
    
    print("\nAll imports successful! App should work.")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

