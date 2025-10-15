import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from agent import AutonomousAgent, ExternalTool, available_tools

def test_external_tool_flight_search():
    """Test FlightSearch tool returns expected mock data."""
    tool = ExternalTool("FlightSearch", "Test description", "http://test.com")
    result = tool.call({"origin": "NYC", "destination": "LAX", "date": "2026-07-01"})
    
    assert "flights" in result
    assert len(result["flights"]) > 0
    assert result["flights"][0]["origin"] == "NYC"
    assert result["flights"][0]["destination"] == "LAX"

def test_external_tool_hotel_booking():
    """Test HotelBooking tool returns expected mock data."""
    tool = ExternalTool("HotelBooking", "Test description", "http://test.com")
    result = tool.call({"location": "Auckland", "check_in": "2026-07-01", "check_out": "2026-07-03"})
    
    assert "hotel" in result
    assert result["hotel"]["location"] == "Auckland"
    assert result["hotel"]["check_in"] == "2026-07-01"

def test_agent_initialization():
    """Test agent initializes correctly."""
    agent = AutonomousAgent()
    assert agent.model_name == "gpt-4o-mini"
    assert agent.scratchpad == []
    assert agent.messages == []

def test_agent_log_reasoning():
    """Test agent logs reasoning steps."""
    agent = AutonomousAgent()
    agent._log_reasoning("Test step")
    
    assert len(agent.scratchpad) == 1
    assert "Test step" in agent.scratchpad[0]

@patch('agent.client')
def test_agent_plan_and_execute_with_tools(mock_client):
    """Test agent executes with tool calls."""
    # Mock the OpenAI response with tool calls
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.tool_calls = [
        MagicMock(
            id="call_1",
            function=MagicMock(
                name="FlightSearch",
                arguments='{"origin": "NYC", "destination": "Auckland", "date": "2026-07-01"}'
            )
        )
    ]
    
    # Second call returns final JSON
    mock_final_response = MagicMock()
    mock_final_response.choices = [MagicMock()]
    mock_final_response.choices[0].message = MagicMock()
    mock_final_response.choices[0].message.tool_calls = None
    mock_final_response.choices[0].message.content = '{"plan_summary": "Test plan", "itinerary": [], "cost_breakdown": {"total": 500}, "constraints_met": true}'
    
    mock_client.chat.completions.create.side_effect = [mock_response, mock_final_response]
    
    agent = AutonomousAgent()
    result, scratchpad = agent.plan_and_execute(
        "Plan a 2-day trip to Auckland",
        constraints=["Budget: under NZ$500"]
    )
    
    assert "plan_summary" in result
    assert len(scratchpad) > 0
    assert any("FlightSearch" in step for step in scratchpad)

def test_available_tools():
    """Test that required tools are available."""
    assert "FlightSearch" in available_tools
    assert "HotelBooking" in available_tools
    assert len(available_tools) >= 2  # At least 2 external APIs

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
