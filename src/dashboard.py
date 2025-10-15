"""
Evaluation Dashboard for Code Assistant - Task 5

Streamlit dashboard to visualize:
- Latency and cost metrics
- Retrieval accuracy curves  
- Agent success/failure breakdown
- RAG impact analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from metrics import MetricsTracker


def format_time(seconds: float) -> str:
    """Format seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


def create_success_rate_chart(stats: dict) -> go.Figure:
    """Create success rate pie chart."""
    overall = stats['overall']
    total = overall.get('total_tasks', 0)
    successful = overall.get('successful_tasks', 0)
    failed = total - successful
    
    fig = go.Figure(data=[go.Pie(
        labels=['Successful', 'Failed'],
        values=[successful, failed],
        marker=dict(colors=['#00CC96', '#EF553B']),
        hole=0.4
    )])
    
    fig.update_layout(
        title="Overall Success Rate",
        annotations=[dict(text=f'{successful}/{total}', x=0.5, y=0.5, font_size=20, showarrow=False)]
    )
    
    return fig


def create_language_breakdown(stats: dict) -> go.Figure:
    """Create language breakdown bar chart."""
    by_lang = stats['by_language']
    
    if not by_lang:
        return None
    
    df = pd.DataFrame(by_lang)
    df['success_rate'] = (df['successful'] / df['count'] * 100).round(1)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Successful',
        x=df['language'],
        y=df['successful'],
        marker_color='#00CC96'
    ))
    
    fig.add_trace(go.Bar(
        name='Failed',
        x=df['language'],
        y=df['count'] - df['successful'],
        marker_color='#EF553B'
    ))
    
    fig.update_layout(
        title="Tasks by Language",
        barmode='stack',
        xaxis_title="Language",
        yaxis_title="Number of Tasks"
    )
    
    return fig


def create_rag_impact_chart(stats: dict) -> go.Figure:
    """Create RAG impact comparison chart."""
    rag_stats = stats['rag_impact']
    
    if not rag_stats or len(rag_stats) < 2:
        return None
    
    df = pd.DataFrame(rag_stats)
    df['rag_label'] = df['rag_used'].apply(lambda x: 'With RAG' if x else 'Without RAG')
    df['success_rate'] = (df['successful'] / df['count'] * 100).round(1)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Success Rate (%)',
        x=df['rag_label'],
        y=df['success_rate'],
        marker_color=['#636EFA', '#00CC96'],
        text=df['success_rate'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside'
    ))
    
    fig.update_layout(
        title="RAG Impact on Success Rate",
        yaxis_title="Success Rate (%)",
        yaxis_range=[0, 100]
    )
    
    return fig


def create_attempts_distribution(stats: dict) -> go.Figure:
    """Create attempts distribution chart."""
    overall = stats['overall']
    avg_success = overall.get('avg_attempts_success') or 0
    avg_failure = overall.get('avg_attempts_failure') or 0
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Average Attempts',
        x=['Successful Tasks', 'Failed Tasks'],
        y=[avg_success, avg_failure],
        marker_color=['#00CC96', '#EF553B'],
        text=[f'{avg_success:.1f}', f'{avg_failure:.1f}'],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Average Attempts Until Success/Failure",
        yaxis_title="Average Attempts",
        yaxis_range=[0, 3.5]
    )
    
    return fig


def create_time_series_chart(time_series: list) -> go.Figure:
    """Create time series chart of task completions."""
    if not time_series:
        return None
    
    df = pd.DataFrame(time_series)
    df['time'] = pd.to_datetime(df['time'])
    df['status'] = df['success'].apply(lambda x: 'Success' if x else 'Failure')
    
    fig = px.scatter(
        df,
        x='time',
        y='total_time_seconds',
        color='status',
        size='attempts',
        hover_data=['language', 'attempts'],
        color_discrete_map={'Success': '#00CC96', 'Failure': '#EF553B'},
        title="Task Completion Timeline"
    )
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Duration (seconds)"
    )
    
    return fig


def main():
    st.set_page_config(
        page_title="Code Assistant Evaluation Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Code Assistant Evaluation Dashboard")
    st.markdown("Real-time metrics for the Self-Healing Code Assistant")
    
    # Initialize metrics tracker
    try:
        tracker = MetricsTracker()
        stats = tracker.get_summary_stats()
        overall = stats['overall']
    except Exception as e:
        st.error(f"Failed to load metrics: {e}")
        st.info("Run some code generation tasks first to see metrics!")
        return
    
    # Check if we have data
    if overall.get('total_tasks', 0) == 0:
        st.info("📝 No tasks have been run yet. Run the code assistant to generate metrics!")
        st.code("python src/code_assistant.py", language="bash")
        return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    time_range = st.sidebar.selectbox(
        "Time Range",
        ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
        index=3
    )
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.sidebar.info("Dashboard will refresh every 30 seconds")
        import time
        time.sleep(30)
        st.rerun()
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = overall.get('total_tasks', 0)
        st.metric("Total Tasks", total)
    
    with col2:
        successful = overall.get('successful_tasks', 0)
        success_rate = (successful / total * 100) if total > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    with col3:
        avg_time = overall.get('avg_time') or 0
        st.metric("Avg Duration", format_time(avg_time))
    
    with col4:
        avg_attempts = overall.get('avg_attempts') or 0
        st.metric("Avg Attempts", f"{avg_attempts:.1f}")
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        fig = create_success_rate_chart(stats)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = create_attempts_distribution(stats)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # Charts row 2
    col1, col2 = st.columns(2)
    
    with col1:
        fig = create_language_breakdown(stats)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No language data available yet")
    
    with col2:
        fig = create_rag_impact_chart(stats)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough RAG data for comparison")
    
    # Time series
    hours_map = {
        "Last 24 Hours": 24,
        "Last 7 Days": 168,
        "Last 30 Days": 720,
        "All Time": 8760
    }
    time_series = tracker.get_time_series(hours=hours_map[time_range])
    
    if time_series:
        fig = create_time_series_chart(time_series)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # Cost metrics (if available)
    if overall.get('total_cost'):
        st.subheader("💰 Cost Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_cost = overall.get('total_cost', 0)
            st.metric("Total Cost", f"${total_cost:.4f}")
        
        with col2:
            total_tokens = overall.get('total_tokens', 0)
            st.metric("Total Tokens", f"{total_tokens:,}")
        
        with col3:
            avg_cost = total_cost / total if total > 0 else 0
            st.metric("Avg Cost/Task", f"${avg_cost:.4f}")
    
    # Recent tasks table
    st.subheader("📋 Recent Tasks")
    recent = stats['recent_tasks']
    
    if recent:
        df = pd.DataFrame(recent)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['status'] = df['success'].apply(lambda x: '✅ Success' if x else '❌ Failed')
        df['duration'] = df['total_time_seconds'].apply(format_time)
        
        display_df = df[['timestamp', 'task', 'language', 'status', 'attempts', 'duration']]
        display_df.columns = ['Time', 'Task', 'Language', 'Status', 'Attempts', 'Duration']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent tasks")
    
    # Error breakdown
    error_breakdown = tracker.get_error_breakdown()
    if error_breakdown:
        st.subheader("🐛 Error Breakdown")
        df = pd.DataFrame(error_breakdown)
        st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
