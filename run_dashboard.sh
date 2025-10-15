#!/bin/bash
# Quick start script for the evaluation dashboard

echo "🚀 Starting Evaluation Dashboard..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if metrics database exists
if [ ! -f "metrics.db" ]; then
    echo "📊 Creating metrics database..."
    python3 -c "from src.metrics import MetricsTracker; MetricsTracker()"
fi

echo "✅ Starting dashboard on http://localhost:8501"
echo ""
echo "💡 Tip: Run 'python src/code_assistant.py' to generate metrics"
echo ""

streamlit run src/dashboard.py
