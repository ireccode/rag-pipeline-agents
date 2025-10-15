#!/usr/bin/env python3
"""
Verification script for the dashboard.
Tests all components before starting.
"""
import sys
from pathlib import Path

sys.path.insert(0, 'src')

def verify_imports():
    """Verify all required imports."""
    print("🔍 Checking imports...")
    try:
        import streamlit
        import pandas
        import plotly
        print("  ✓ streamlit")
        print("  ✓ pandas")
        print("  ✓ plotly")
        return True
    except ImportError as e:
        print(f"  ✗ Missing dependency: {e}")
        print("\n💡 Install with: pip install -r requirements.txt")
        return False

def verify_metrics_module():
    """Verify metrics module works."""
    print("\n🔍 Checking metrics module...")
    try:
        from metrics import MetricsTracker
        import tempfile
        import os
        
        # Use temporary file for test
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            test_db = f.name
        
        try:
            tracker = MetricsTracker(test_db)
            print("  ✓ MetricsTracker initialized")
            
            # Test basic operations
            task_id = tracker.start_task("test", "python")
            tracker.complete_task(task_id, True, 1, 1.0, 1)
            stats = tracker.get_summary_stats()
            
            assert stats['overall']['total_tasks'] == 1
            print("  ✓ Metrics operations working")
            return True
        finally:
            # Cleanup
            if os.path.exists(test_db):
                os.unlink(test_db)
    except Exception as e:
        print(f"  ✗ Metrics error: {e}")
        return False

def verify_dashboard_module():
    """Verify dashboard module loads."""
    print("\n🔍 Checking dashboard module...")
    try:
        import dashboard
        print("  ✓ Dashboard module loads")
        return True
    except Exception as e:
        print(f"  ✗ Dashboard error: {e}")
        return False

def check_database():
    """Check if metrics database exists."""
    print("\n🔍 Checking metrics database...")
    db_path = Path('metrics.db')
    if db_path.exists():
        print(f"  ✓ Database exists: {db_path}")
        
        # Check if it has data
        from metrics import MetricsTracker
        tracker = MetricsTracker('metrics.db')
        stats = tracker.get_summary_stats()
        total = stats['overall'].get('total_tasks', 0)
        
        if total > 0:
            print(f"  ✓ Database has {total} tasks")
        else:
            print("  ⚠️  Database is empty")
            print("     Run 'python src/code_assistant.py' to generate metrics")
    else:
        print("  ⚠️  Database doesn't exist yet")
        print("     Will be created automatically")
        print("     Run 'python src/code_assistant.py' to generate metrics")

def main():
    print("=" * 60)
    print("Dashboard Verification")
    print("=" * 60)
    
    all_ok = True
    
    if not verify_imports():
        all_ok = False
    
    if not verify_metrics_module():
        all_ok = False
    
    if not verify_dashboard_module():
        all_ok = False
    
    check_database()
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All checks passed!")
        print("\n🚀 Start dashboard with:")
        print("   streamlit run src/dashboard.py")
        print("\n   Or use: ./run_dashboard.sh")
        return 0
    else:
        print("❌ Some checks failed")
        print("\n💡 Fix the issues above before starting the dashboard")
        return 1

if __name__ == "__main__":
    sys.exit(main())
