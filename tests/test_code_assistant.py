import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

os.environ['OPENAI_API_KEY'] = 'test_key'
os.environ['OPENAI_BASE_URL'] = 'https://api.openai.com/v1'
os.environ['USE_CODE_EXAMPLES'] = 'false'  # Disable RAG for tests

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from code_assistant import CodeAssistant

def test_code_assistant_initialization():
    """Test code assistant initializes correctly."""
    assistant = CodeAssistant()
    assert assistant.model_name == "gpt-4o-mini"
    assert assistant.max_retries == 3
    assert assistant.conversation_history == []

def test_detect_language_python():
    """Test language detection for Python."""
    assistant = CodeAssistant()
    lang, ext, cmd = assistant._detect_language("write quicksort in Python")
    assert lang == "python"
    assert ext == "py"
    assert cmd == "pytest"

def test_detect_language_rust():
    """Test language detection for Rust."""
    assistant = CodeAssistant()
    lang, ext, cmd = assistant._detect_language("write quicksort in Rust")
    assert lang == "rust"
    assert ext == "rs"
    assert cmd == "cargo test"

def test_detect_language_default():
    """Test language detection defaults to Python."""
    assistant = CodeAssistant()
    lang, ext, cmd = assistant._detect_language("write a function")
    assert lang == "python"
    assert ext == "py"
    assert cmd == "pytest"

def test_write_code_to_file():
    """Test writing code to file."""
    assistant = CodeAssistant()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.py"
        code = "def hello():\n    return 'world'"
        
        assistant._write_code_to_file(code, file_path)
        
        assert file_path.exists()
        with open(file_path, 'r') as f:
            assert f.read() == code

@patch('code_assistant.subprocess.run')
def test_execute_tests_success(mock_run):
    """Test successful test execution."""
    assistant = CodeAssistant()
    
    # Mock successful test run
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="All tests passed",
        stderr=""
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        success, output = assistant._execute_tests("pytest", Path(tmpdir))
        
        assert success is True
        assert "All tests passed" in output

@patch('code_assistant.subprocess.run')
def test_execute_tests_failure(mock_run):
    """Test failed test execution."""
    assistant = CodeAssistant()
    
    # Mock failed test run
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Test failed: assertion error"
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        success, output = assistant._execute_tests("pytest", Path(tmpdir))
        
        assert success is False
        assert "Test failed" in output

@patch('code_assistant.client')
def test_generate_code(mock_client):
    """Test code generation."""
    assistant = CodeAssistant()
    
    # Mock streaming response
    mock_chunk1 = MagicMock()
    mock_chunk1.choices = [MagicMock()]
    mock_chunk1.choices[0].delta.content = "def quicksort"
    
    mock_chunk2 = MagicMock()
    mock_chunk2.choices = [MagicMock()]
    mock_chunk2.choices[0].delta.content = "(arr):\n    pass"
    
    mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]
    
    code = assistant._generate_code("write quicksort", "python")
    
    assert "def quicksort" in code
    assert len(assistant.conversation_history) > 0

@patch('code_assistant.client')
@patch('code_assistant.subprocess.run')
def test_generate_and_test_success(mock_run, mock_client):
    """Test full generate and test cycle with success."""
    assistant = CodeAssistant()
    
    # Mock code generation
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "def quicksort(arr):\n    return sorted(arr)\n\ndef test_quicksort():\n    assert quicksort([3,1,2]) == [1,2,3]"
    
    mock_client.chat.completions.create.return_value = [mock_chunk]
    
    # Mock successful test
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="1 passed",
        stderr=""
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = assistant.generate_and_test(
            "write quicksort in Python",
            output_dir=Path(tmpdir)
        )
        
        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["language"] == "python"
        assert "quicksort" in result["code"]

@patch('code_assistant.client')
@patch('code_assistant.subprocess.run')
def test_generate_and_test_retry(mock_run, mock_client):
    """Test retry logic on test failure."""
    assistant = CodeAssistant(max_retries=2)
    
    # Mock code generation (will be called twice)
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "def quicksort(arr):\n    return arr"
    
    mock_client.chat.completions.create.return_value = [mock_chunk]
    
    # First test fails, second succeeds
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout="", stderr="Test failed"),
        MagicMock(returncode=0, stdout="1 passed", stderr="")
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = assistant.generate_and_test(
            "write quicksort in Python",
            output_dir=Path(tmpdir)
        )
        
        assert result["success"] is True
        assert result["attempts"] == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
