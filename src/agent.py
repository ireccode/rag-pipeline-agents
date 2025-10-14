import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1" )
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini")
EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL", "http://localhost:8080/mock_api" ) # Placeholder for external API

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

class ExternalTool:
    """Mock external tool/API for demonstration."""
    def __init__(self, name, description, api_url):
        self.name = name
        self.description = description
        self.api_url = api_url

    def call(self, params: dict):
        print(f"Calling external tool: {self.name} with params: {params}")
        # In a real scenario, this would make an HTTP request to self.api_url
        # For now, return mock data.
        if self.name == "FlightSearch":
            return {"flights": [{"id": "FL101", "origin": params.get("origin"), "destination": params.get("destination"), "date": params.get("date"), "price": 250}]}
        elif self.name == "HotelBooking":
            return {"hotel": {"id": "HT202", "location": params.get("location"), "check_in": params.get("check_in"), "check_out": params.get("check_out"), "price_per_night": 100}}
        return {"status": "success", "tool_name": self.name, "params": params}

# Define mock external tools
flight_search_tool = ExternalTool(
    name="FlightSearch",
    description="Searches for flights between an origin and destination on a specific date. Parameters: origin (str), destination (str), date (str).",
    api_url=f"{EXTERNAL_API_URL}/flights"
)
hotel_booking_tool = ExternalTool(
    name="HotelBooking",
    description="Books a hotel in a specified location for given check-in and check-out dates. Parameters: location (str), check_in (str), check_out (str).",
    api_url=f"{EXTERNAL_API_URL}/hotels"
)

available_tools = {
    "FlightSearch": flight_search_tool,
    "HotelBooking": hotel_booking_tool,
}

# Tool definitions for LLM function calling
tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "FlightSearch",
            "description": "Searches for flights between an origin and destination on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "The origin city or airport code"},
                    "destination": {"type": "string", "description": "The destination city or airport code"},
                    "date": {"type": "string", "description": "The date of the flight in YYYY-MM-DD format"},
                },
                "required": ["origin", "destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "HotelBooking",
            "description": "Books a hotel in a specified location for given check-in and check-out dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city or area for the hotel booking"},
                    "check_in": {"type": "string", "description": "The check-in date in YYYY-MM-DD format"},
                    "check_out": {"type": "string", "description": "The check-out date in YYYY-MM-DD format"},
                },
                "required": ["location", "check_in", "check_out"],
            },
        },
    },
]

class AutonomousAgent:
    def __init__(self, model_name=MODEL_NAME):
        self.model_name = model_name
        self.scratchpad = []
        self.messages = []

    def _log_reasoning(self, step: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scratchpad.append(f"[{timestamp}] {step}")
        print(f"[Agent Reasoning] {step}")

    def plan_and_execute(self, prompt: str, constraints: list = None):
        self._log_reasoning(f"Received prompt: {prompt}")
        if constraints:
            self._log_reasoning(f"Applying constraints: {constraints}")

        system_message = {"role": "system", "content": (
            "You are an autonomous planning agent. Your goal is to fulfill user requests by planning a sequence of actions, "
            "potentially involving external tools. Think step-by-step. "
            "If external tools are needed, use the provided `tool_code` to call them. "
            "After executing tools, synthesize the results and provide a final answer in JSON format. "
            "The final JSON output should adhere to the following schema: "
            "{\"plan_summary\": \"A summary of the trip plan.\", \"details\": [...], \"cost_estimate\": \"$X.XX\"}. "
            "Details should be a list of objects, each representing a planned activity or booking. "
            "Always consider user constraints. If a constraint cannot be met, state it clearly."
        )}
        self.messages = [system_message, {"role": "user", "content": prompt}]

        max_iterations = 5 # Prevent infinite loops
        for i in range(max_iterations):
            self._log_reasoning(f"Iteration {i+1}/{max_iterations}")
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    tools=tool_definitions,
                    tool_choice="auto",
                )
                response_message = response.choices[0].message
                self.messages.append(response_message)

                if response_message.tool_calls:
                    self._log_reasoning(f"Tool calls detected: {response_message.tool_calls}")
                    tool_outputs = []
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        if function_name in available_tools:
                            tool_instance = available_tools[function_name]
                            tool_output = tool_instance.call(function_args)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": tool_output
                            })
                            self._log_reasoning(f"Tool {function_name} executed. Output: {tool_output}")
                        else:
                            tool_outputs.append({"tool_call_id": tool_call.id, "output": f"Error: Tool {function_name} not found."})
                            self._log_reasoning(f"Error: Tool {function_name} not found.")

                    # Add tool outputs to messages for the next turn
                    for output in tool_outputs:
                        self.messages.append({
                            "tool_call_id": output["tool_call_id"],
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(output["output"]),
                        })

                else:
                    # If no tool calls, it's likely the final response
                    self._log_reasoning("No tool calls. Assuming final response.")
                    try:
                        # Attempt to parse as JSON
                        final_output = json.loads(response_message.content)
                        return final_output, self.scratchpad
                    except json.JSONDecodeError:
                        # If not JSON, try to guide it to produce JSON
                        self._log_reasoning("Final response not in JSON. Guiding agent to produce JSON.")
                        self.messages.append({"role": "user", "content": "Please provide the final plan in the specified JSON format."})

            except Exception as e:
                self._log_reasoning(f"An error occurred during agent execution: {e}")
                return {"error": str(e)}, self.scratchpad

        self._log_reasoning("Max iterations reached without a final JSON output.")
        return {"error": "Agent failed to produce a valid JSON output within max iterations."}, self.scratchpad


if __name__ == "__main__":
    agent = AutonomousAgent()
    user_prompt = "Plan a 2-day trip to Paris for a weekend in July 2026. I need flights from London and a hotel booking."
    constraints = ["Total budget under $1000", "Hotel must be near Eiffel Tower"]

    result, scratchpad = agent.plan_and_execute(user_prompt, constraints)

    print("\n--- Final Result ---")
    print(json.dumps(result, indent=2))
    print("\n--- Scratchpad ---")
    for step in scratchpad:
        print(step)
