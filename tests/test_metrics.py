import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import tempfile
from pathlib import Path
from metrics import MetricsTracker


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_metrics_tracker_initialization(temp_db):
    """Test metrics tracker initializes correctly."""
    tracker = MetricsTracker(db_path=temp_db)
    assert tracker.db_path == temp_db
    
    # Check tables were created
    stats = tracker.get_summary_stats()
    assert 'overall' in stats
    assert 'by_language' in stats
    assert 'rag_impact' in stats
    assert 'recent_tasks' in stats


def test_start_and_complete_task(temp_db):
    """Test starting and completing a task."""
    tracker = MetricsTracker(db_path=temp_db)
    
    # Start a task
    task_id = tracker.start_task("write quicksort", "python")
    assert task_id > 0
    
    # Complete the task
    tracker.complete_task(
        task_id,
        success=True,
        attempts=2,
        total_time=5.5,
        llm_calls=2,
        tokens_used=1000,
        estimated_cost=0.002,
        rag_used=True,
        rag_examples_found=3
    )
    
    # Verify stats
    stats = tracker.get_summary_stats()
    assert stats['overall']['total_tasks'] == 1
    assert stats['overall']['successful_tasks'] == 1
    assert stats['overall']['avg_attempts'] == 2.0


def test_log_attempt(temp_db):
    """Test logging individual attempts."""
    tracker = MetricsTracker(db_path=temp_db)
    
    task_id = tracker.start_task("write binary search", "rust")
    
    # Log first attempt (failure)
    tracker.log_attempt(
        task_id,
        attempt_number=1,
        time_seconds=2.5,
        tokens_used=500,
        error_type="test_failure",
        error_message="Tests failed",
        code_generated="fn binary_search() {}"
    )
    
    # Log second attempt (success)
    tracker.log_attempt(
        task_id,
        attempt_number=2,
        time_seconds=3.0,
        tokens_used=600,
        code_generated="fn binary_search() { /* working code */ }"
    )
    
    # Complete task
    tracker.complete_task(
        task_id,
        success=True,
        attempts=2,
        total_time=5.5,
        llm_calls=2
    )
    
    stats = tracker.get_summary_stats()
    assert stats['overall']['total_tasks'] == 1


def test_multiple_tasks(temp_db):
    """Test tracking multiple tasks."""
    tracker = MetricsTracker(db_path=temp_db)
    
    # Task 1: Success
    task1 = tracker.start_task("quicksort", "python")
    tracker.complete_task(task1, True, 1, 3.0, 1)
    
    # Task 2: Failure
    task2 = tracker.start_task("complex algorithm", "python")
    tracker.complete_task(task2, False, 3, 10.0, 3, error_message="Max retries")
    
    # Task 3: Success with RAG
    task3 = tracker.start_task("binary search", "rust")
    tracker.complete_task(task3, True, 2, 5.0, 2, rag_used=True, rag_examples_found=2)
    
    stats = tracker.get_summary_stats()
    assert stats['overall']['total_tasks'] == 3
    assert stats['overall']['successful_tasks'] == 2
    assert len(stats['by_language']) == 2  # python and rust


def test_language_breakdown(temp_db):
    """Test language breakdown statistics."""
    tracker = MetricsTracker(db_path=temp_db)
    
    # Add Python tasks
    for i in range(3):
        task_id = tracker.start_task(f"python task {i}", "python")
        tracker.complete_task(task_id, i < 2, 1, 2.0, 1)  # 2 success, 1 failure
    
    # Add Rust tasks
    for i in range(2):
        task_id = tracker.start_task(f"rust task {i}", "rust")
        tracker.complete_task(task_id, True, 1, 3.0, 1)  # 2 success
    
    stats = tracker.get_summary_stats()
    by_lang = {item['language']: item for item in stats['by_language']}
    
    assert by_lang['python']['count'] == 3
    assert by_lang['python']['successful'] == 2
    assert by_lang['rust']['count'] == 2
    assert by_lang['rust']['successful'] == 2


def test_rag_impact(temp_db):
    """Test RAG impact statistics."""
    tracker = MetricsTracker(db_path=temp_db)
    
    # Tasks without RAG
    for i in range(2):
        task_id = tracker.start_task(f"task {i}", "python")
        tracker.complete_task(task_id, i == 0, 2, 4.0, 2, rag_used=False)
    
    # Tasks with RAG
    for i in range(3):
        task_id = tracker.start_task(f"task rag {i}", "python")
        tracker.complete_task(task_id, True, 1, 3.0, 1, rag_used=True, rag_examples_found=2)
    
    stats = tracker.get_summary_stats()
    rag_impact = {item['rag_used']: item for item in stats['rag_impact']}
    
    assert rag_impact[0]['count'] == 2  # Without RAG
    assert rag_impact[1]['count'] == 3  # With RAG
    assert rag_impact[1]['successful'] == 3


def test_time_series(temp_db):
    """Test time series data retrieval."""
    tracker = MetricsTracker(db_path=temp_db)
    
    # Add some tasks
    for i in range(5):
        task_id = tracker.start_task(f"task {i}", "python")
        tracker.complete_task(task_id, True, 1, 2.0, 1)
    
    # Get time series
    time_series = tracker.get_time_series(hours=24)
    assert len(time_series) == 5
    assert all('time' in item for item in time_series)
    assert all('success' in item for item in time_series)


def test_error_breakdown(temp_db):
    """Test error breakdown statistics."""
    tracker = MetricsTracker(db_path=temp_db)
    
    task_id = tracker.start_task("test task", "python")
    
    # Log attempts with different error types
    tracker.log_attempt(task_id, 1, 1.0, error_type="syntax_error", error_message="Syntax error")
    tracker.log_attempt(task_id, 2, 1.5, error_type="test_failure", error_message="Test failed")
    tracker.log_attempt(task_id, 3, 2.0, error_type="test_failure", error_message="Test failed again")
    
    tracker.complete_task(task_id, False, 3, 4.5, 3)
    
    errors = tracker.get_error_breakdown()
    assert len(errors) > 0
    
    # test_failure should appear twice
    test_failures = [e for e in errors if e['error_type'] == 'test_failure']
    if test_failures:
        assert test_failures[0]['count'] == 2


def test_none_handling_in_stats(temp_db):
    """Test that None values in stats are handled correctly."""
    tracker = MetricsTracker(db_path=temp_db)
    
    # Add only successful tasks (no failures)
    for i in range(3):
        task_id = tracker.start_task(f"task {i}", "python")
        tracker.complete_task(task_id, True, 1, 2.0, 1)
    
    stats = tracker.get_summary_stats()
    overall = stats['overall']
    
    # avg_attempts_failure should be None when there are no failures
    # This should not cause errors when formatting
    avg_success = overall.get('avg_attempts_success') or 0
    avg_failure = overall.get('avg_attempts_failure') or 0
    
    assert avg_success > 0
    assert avg_failure == 0  # Should default to 0, not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
