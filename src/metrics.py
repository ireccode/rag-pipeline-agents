"""
Metrics tracking for the code assistant evaluation dashboard.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sqlite3
from contextlib import contextmanager


class MetricsTracker:
    """Track and persist metrics for code generation tasks."""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize the metrics database."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    language TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    attempts INTEGER NOT NULL,
                    total_time_seconds REAL NOT NULL,
                    llm_calls INTEGER NOT NULL,
                    tokens_used INTEGER,
                    estimated_cost REAL,
                    rag_used BOOLEAN DEFAULT FALSE,
                    rag_examples_found INTEGER DEFAULT 0,
                    error_message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attempt_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_run_id INTEGER NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    time_seconds REAL NOT NULL,
                    tokens_used INTEGER,
                    error_type TEXT,
                    error_message TEXT,
                    code_generated TEXT,
                    FOREIGN KEY (task_run_id) REFERENCES task_runs(id)
                )
            """)
    
    def start_task(self, task: str, language: str) -> int:
        """
        Start tracking a new task.
        
        Returns:
            task_run_id for tracking this task
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO task_runs (task, language, success, attempts, total_time_seconds, llm_calls)
                VALUES (?, ?, 0, 0, 0.0, 0)
            """, (task, language))
            return cursor.lastrowid
    
    def log_attempt(
        self,
        task_run_id: int,
        attempt_number: int,
        time_seconds: float,
        tokens_used: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        code_generated: Optional[str] = None
    ):
        """Log details for a single attempt."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO attempt_details 
                (task_run_id, attempt_number, time_seconds, tokens_used, error_type, error_message, code_generated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_run_id, attempt_number, time_seconds, tokens_used, error_type, error_message, code_generated))
    
    def complete_task(
        self,
        task_run_id: int,
        success: bool,
        attempts: int,
        total_time: float,
        llm_calls: int,
        tokens_used: Optional[int] = None,
        estimated_cost: Optional[float] = None,
        rag_used: bool = False,
        rag_examples_found: int = 0,
        error_message: Optional[str] = None
    ):
        """Mark a task as complete and update final metrics."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE task_runs
                SET success = ?, attempts = ?, total_time_seconds = ?, llm_calls = ?,
                    tokens_used = ?, estimated_cost = ?, rag_used = ?, rag_examples_found = ?,
                    error_message = ?
                WHERE id = ?
            """, (success, attempts, total_time, llm_calls, tokens_used, estimated_cost,
                  rag_used, rag_examples_found, error_message, task_run_id))
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the dashboard."""
        with self._get_connection() as conn:
            # Overall stats
            overall = conn.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_tasks,
                    AVG(attempts) as avg_attempts,
                    AVG(total_time_seconds) as avg_time,
                    AVG(CASE WHEN success = 1 THEN attempts END) as avg_attempts_success,
                    AVG(CASE WHEN success = 0 THEN attempts END) as avg_attempts_failure,
                    SUM(tokens_used) as total_tokens,
                    SUM(estimated_cost) as total_cost
                FROM task_runs
            """).fetchone()
            
            # Language breakdown
            by_language = conn.execute("""
                SELECT 
                    language,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    AVG(total_time_seconds) as avg_time
                FROM task_runs
                GROUP BY language
            """).fetchall()
            
            # RAG impact
            rag_stats = conn.execute("""
                SELECT 
                    rag_used,
                    COUNT(*) as count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    AVG(attempts) as avg_attempts
                FROM task_runs
                GROUP BY rag_used
            """).fetchall()
            
            # Recent tasks
            recent = conn.execute("""
                SELECT task, language, success, attempts, total_time_seconds, timestamp
                FROM task_runs
                ORDER BY timestamp DESC
                LIMIT 10
            """).fetchall()
            
            return {
                "overall": dict(overall) if overall else {},
                "by_language": [dict(row) for row in by_language],
                "rag_impact": [dict(row) for row in rag_stats],
                "recent_tasks": [dict(row) for row in recent]
            }
    
    def get_time_series(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get time series data for charts."""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT 
                    datetime(timestamp) as time,
                    success,
                    attempts,
                    total_time_seconds,
                    language
                FROM task_runs
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp
            """, (hours,)).fetchall()
            
            return [dict(row) for row in results]
    
    def get_error_breakdown(self) -> List[Dict[str, Any]]:
        """Get breakdown of error types."""
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT 
                    error_type,
                    COUNT(*) as count,
                    AVG(time_seconds) as avg_time
                FROM attempt_details
                WHERE error_type IS NOT NULL
                GROUP BY error_type
                ORDER BY count DESC
            """).fetchall()
            
            return [dict(row) for row in results]
