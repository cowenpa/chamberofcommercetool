import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from typing import Dict, List, Any

# File to store analytics data
ANALYTICS_FILE = "analytics_data.json"

def log_view(company_name: str) -> None:
    """
    Log a company page view for analytics
    
    Args:
        company_name: Name of the company being viewed
    """
    # Create analytics data
    analytics_data = {
        "company": company_name,
        "timestamp": datetime.now().isoformat(),
        "user_agent": st.session_state.get("_client_user_agent", "Unknown")
    }
    
    # Load existing analytics
    all_analytics = []
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, "r") as f:
                all_analytics = json.load(f)
        except json.JSONDecodeError:
            all_analytics = []
    
    # Add new entry
    all_analytics.append(analytics_data)
    
    # Save updated analytics
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(all_analytics, f)

def get_analytics_data() -> List[Dict[str, Any]]:
    """
    Get all analytics data
    
    Returns:
        List of analytics data records
    """
    if not os.path.exists(ANALYTICS_FILE):
        return []
    
    try:
        with open(ANALYTICS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def display_analytics() -> None:
    """Display analytics dashboard"""
    
    # Get analytics data
    analytics_data = get_analytics_data()
    
    if not analytics_data:
        st.info("No analytics data available yet.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(analytics_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Display total views
    st.subheader("Total Page Views")
    st.metric("Total Views", len(df))
    
    # Display views by company
    st.subheader("Views by Company")
    company_counts = df["company"].value_counts().reset_index()
    company_counts.columns = ["Company", "Views"]
    st.bar_chart(company_counts.set_index("Company"))
    
    # Display views over time
    st.subheader("Views Over Time")
    df["date"] = df["timestamp"].dt.date
    date_counts = df.groupby("date").size().reset_index(name="Views")
    st.line_chart(date_counts.set_index("date"))
    
    # Display recent views
    st.subheader("Recent Views")
    recent_df = df.sort_values("timestamp", ascending=False).head(10)
    recent_df["time"] = recent_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.table(recent_df[["company", "time", "user_agent"]])
