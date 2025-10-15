"""
Pytest configuration and fixtures for RAG pipeline tests.

This file provides shared fixtures and configuration for all tests,
including environment variable loading and mock setup.
"""

import os
import pytest
from dotenv import load_dotenv
from unittest.mock import MagicMock

# Load environment variables from .env file at the start of test session
load_dotenv()


@pytest.fixture(scope="session")
def env_vars():
    """
    Fixture to provide environment variables for tests.
    
    Returns:
        dict: Dictionary of environment variables
    """
    return {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'MODEL_NAME': os.getenv('MODEL_NAME', 'gpt-4o-mini'),
    }


@pytest.fixture
def mock_supabase_client():
    """
    Fixture to provide a mocked Supabase client.
    
    Returns:
        MagicMock: Mocked Supabase client
    """
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.execute.return_value.data = [
        {
            'url': 'https://example.com',
            'content': 'Sample content for testing',
            'similarity': 0.95
        }
    ]
    return mock_client


@pytest.fixture
def mock_openai_client():
    """
    Fixture to provide a mocked OpenAI client.
    
    Returns:
        MagicMock: Mocked OpenAI client
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_qa_response():
    """
    Fixture to provide a sample QA response for testing.
    
    Returns:
        dict: Sample QA response
    """
    return {
        "answer": "Pydantic AI is a Python agent framework for building production-grade applications with Generative AI.",
        "citations": [
            "https://ai.pydantic.dev",
            "https://ai.pydantic.dev/docs"
        ],
        "latency_ms": 150.5,
        "sources": [
            {
                "url": "https://ai.pydantic.dev",
                "content": "Pydantic AI documentation",
                "similarity": 0.95
            }
        ]
    }


def pytest_configure(config):
    """
    Pytest configuration hook.
    
    Adds custom markers for test categorization.
    """
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (requires real API access)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (uses mocks, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test names.
    """
    for item in items:
        # Add integration marker to tests that use real APIs
        if "integration" in item.nodeid or not any(
            marker in item.nodeid for marker in ["mock", "unit"]
        ):
            if "test_qa_with_citations" in item.nodeid and "mocked" not in item.nodeid:
                item.add_marker(pytest.mark.integration)
        
        # Add unit marker to mocked tests
        if "mocked" in item.nodeid or "mock" in item.nodeid:
            item.add_marker(pytest.mark.unit)
