import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json

# Configuration from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

st.set_page_config(layout="wide", page_title="RAG System Dashboard")

st.title("RAG System Performance Dashboard")

st.markdown("""
This dashboard visualizes the performance metrics of the RAG (Retrieval-Augmented Generation) system.
It includes metrics for conversational core, RAG QA, and evaluation results.
""")

# --- Conversational Core Metrics (Placeholder) ---
st.header("Conversational Core Metrics")
st.info("Metrics for the conversational core (e.g., prompt tokens, completion tokens, cost, latency) would be displayed here. "
        "These would typically be logged to a database (like Supabase) and fetched for visualization.")

# Placeholder for fetching chat metrics
# In a real implementation, you would query your SQLite/Chroma/Supabase for chat logs
chat_metrics_data = {
    "Timestamp": ["2023-10-26 10:00:00", "2023-10-26 10:05:00", "2023-10-26 10:10:00"],
    "Prompt Tokens": [50, 60, 70],
    "Completion Tokens": [100, 120, 150],
    "Cost (USD)": [0.0001, 0.00015, 0.0002],
    "Latency (ms)": [250, 300, 270]
}
chat_df = pd.DataFrame(chat_metrics_data)

if not chat_df.empty:
    st.subheader("Chat Latency Over Time")
    fig_latency = px.line(chat_df, x="Timestamp", y="Latency (ms)", title="Chat Latency")
    st.plotly_chart(fig_latency, use_container_width=True)

    st.subheader("Chat Cost Over Time")
    fig_cost = px.line(chat_df, x="Timestamp", y="Cost (USD)", title="Chat Cost")
    st.plotly_chart(fig_cost, use_container_width=True)
else:
    st.write("No chat metrics data available.")

# --- RAG QA Evaluation Results ---
st.header("RAG QA Evaluation Results")

reports_dir = "/app/reports" # Assuming reports are mounted here in Docker
if os.path.exists(reports_dir):
    report_files = [f for f in os.listdir(reports_dir) if f.startswith("rag_evaluation_report_") and f.endswith(".json")]
    if report_files:
        selected_report = st.selectbox("Select RAG Evaluation Report", sorted(report_files, reverse=True))
        report_path = os.path.join(reports_dir, selected_report)

        with open(report_path, "r") as f:
            report_data = json.load(f)

        st.subheader("Summary Metrics")
        summary_df = pd.DataFrame([report_data["summary"]])
        st.dataframe(summary_df)

        st.subheader("Individual Test Results")
        results_df = pd.DataFrame(report_data["individual_results"])
        st.dataframe(results_df)

        st.subheader("Latency Distribution")
        fig_rag_latency = px.histogram(results_df, x="latency_ms", nbins=20, title="RAG QA Latency Distribution")
        st.plotly_chart(fig_rag_latency, use_container_width=True)

        st.subheader("Accuracy Breakdown")
        accuracy_data = {
            "Metric": ["Overall Answer Accuracy", "Overall Citation Accuracy", "Top-5 Retrieval Accuracy"],
            "Value": [report_data["summary"]["overall_answer_accuracy"],
                      report_data["summary"]["overall_citation_accuracy"],
                      report_data["summary"]["top_5_retrieval_accuracy"]]
        }
        accuracy_df = pd.DataFrame(accuracy_data)
        fig_accuracy = px.bar(accuracy_df, x="Metric", y="Value", title="RAG Accuracy Metrics",
                              range_y=[0, 1], text_auto=True)
        st.plotly_chart(fig_accuracy, use_container_width=True)

    else:
        st.write("No RAG evaluation reports found in the /reports directory.")
else:
    st.write(f"Reports directory {reports_dir} not found. Please ensure reports are generated and mounted.")

# --- Agent Performance (Placeholder) ---
st.header("Autonomous Agent Performance")
st.info("Metrics for the autonomous agent (e.g., success rate, tool call latency, planning steps) would be displayed here.")

# --- Self-Healing Code Assistant (Placeholder) ---
st.header("Self-Healing Code Assistant Performance")
st.info("Metrics for the self-healing code assistant (e.g., success rate, retry count, code quality) would be displayed here.")
