import os
os.environ['OPENAI_API_KEY'] = 'test_key'
os.environ['OPENAI_BASE_URL'] = 'test_base_url'

import pytest
from src.chat import chat_cli, count_tokens, estimate_cost

def test_count_tokens():
    """Test token counting."""
    text = "Hello world"
    tokens = count_tokens(text)
    assert tokens > 0

def test_estimate_cost():
    """Test cost estimation."""
    cost = estimate_cost(10, 20)
    assert cost > 0

# Note: chat_cli is interactive, so manual testing is required for full functionality
