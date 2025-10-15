import os
import json
import time
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1" )
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
FLIGHTS_API_URL = os.getenv("FLIGHTS_API_URL", "https://api.skypicker.com")  # Kiwi / Skypicker flights search
HOTELS_API_URL = os.getenv("HOTELS_API_URL", "https://api.opentripmap.com/0.1/en/places")  # OpenTripMap provides POI/place data (useful for hotel location info)



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

# Define available tools
flight_search_tool = ExternalTool(
    name="FlightSearch",
    description="Searches for flights between an origin and destination on a specific date. Parameters: origin (str), destination (str), date (str).",
    api_url=f"{FLIGHTS_API_URL}/flights"
)
hotel_booking_tool = ExternalTool(
    name="HotelBooking",
    description="Books a hotel in a specified location for given check-in and check-out dates. Parameters: location (str), check_in (str), check_out (str).",
    api_url=f"{HOTELS_API_URL}"
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
            constraint_text = "\n".join([f"- {c}" for c in constraints])
        else:
            constraint_text = "No specific constraints provided."

        system_message = {"role": "system", "content": (
            "You are an autonomous planning agent. Your goal is to fulfill user requests by planning a sequence of actions, "
            "potentially involving external tools. Think step-by-step. "
            "If external tools are needed, use the provided tools to call them. "
            "After executing tools, synthesize the results and provide a final answer in JSON format. "
            "The final JSON output should adhere to the following schema: "
            "{\"plan_summary\": \"A summary of the trip plan.\", \"itinerary\": [{\"day\": 1, \"activities\": [...]}, ...], \"cost_breakdown\": {\"flights\": X, \"hotels\": Y, \"total\": Z}, \"constraints_met\": true/false}. "
            "Always consider user constraints. If a constraint cannot be met, state it clearly in the response."
        )}
        user_message_content = f"{prompt}\n\nConstraints:\n{constraint_text}"
        self.messages = [system_message, {"role": "user", "content": user_message_content}]

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
                    self._log_reasoning(f"Tool calls detected: {len(response_message.tool_calls)} tool(s)")
                    
                    # Execute all tool calls
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        if function_name in available_tools:
                            tool_instance = available_tools[function_name]
                            tool_output = tool_instance.call(function_args)
                            self._log_reasoning(f"Tool {function_name} executed. Output: {tool_output}")
                        else:
                            tool_output = {"error": f"Tool {function_name} not found."}
                            self._log_reasoning(f"Error: Tool {function_name} not found.")

                        # Add tool output to messages immediately
                        self.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_output),
                        })

                else:
                    # If no tool calls, it's likely the final response
                    self._log_reasoning("No tool calls. Checking for final response.")
                    
                    if response_message.content:
                        content = response_message.content.strip()
                        self._log_reasoning(f"Response content: {content[:200]}...")
                        
                        # Try to extract JSON from the response
                        try:
                            # First, try direct JSON parsing
                            final_output = json.loads(content)
                            self._log_reasoning("Successfully parsed JSON response.")
                            return final_output, self.scratchpad
                        except json.JSONDecodeError:
                            # Try to extract JSON from markdown code blocks
                            import re
                            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
                            if json_match:
                                try:
                                    final_output = json.loads(json_match.group(1))
                                    self._log_reasoning("Successfully extracted JSON from code block.")
                                    return final_output, self.scratchpad
                                except json.JSONDecodeError:
                                    pass
                            
                            # If still not JSON, guide the agent
                            self._log_reasoning("Response not in valid JSON format. Requesting JSON output.")
                            self.messages.append({
                                "role": "user", 
                                "content": "Please provide ONLY the final trip plan as a valid JSON object with the following structure: {\"plan_summary\": \"...\", \"itinerary\": [{\"day\": 1, \"activities\": [...]}], \"cost_breakdown\": {\"flights\": X, \"hotels\": Y, \"total\": Z}, \"constraints_met\": true/false}. Do not include any markdown formatting or explanatory text."
                            })
                    else:
                        self._log_reasoning("Empty response received.")

            except Exception as e:
                self._log_reasoning(f"An error occurred during agent execution: {e}")
                return {"error": str(e)}, self.scratchpad

        self._log_reasoning("Max iterations reached without a final JSON output.")
        return {"error": "Agent failed to produce a valid JSON output within max iterations."}, self.scratchpad


if __name__ == "__main__":
    agent = AutonomousAgent()
    # Example: Plan a 2-day trip to Auckland for under NZ$500
    user_prompt = "Plan a 2-day trip to Auckland for under NZ$500"
    constraints = [
        "Budget: under NZ$500",
        "Duration: 2 days",
        "Include flights and accommodation"
    ]

    print("=" * 60)
    print("AUTONOMOUS AGENT - TASK 3: Trip Planning")
    print("=" * 60)
    print(f"Prompt: {user_prompt}")
    print(f"Constraints: {constraints}")
    print("=" * 60)
    print()

    result, scratchpad = agent.plan_and_execute(user_prompt, constraints)

    print("\n" + "=" * 60)
    print("--- Final Itinerary (JSON) ---")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("\n" + "=" * 60)
    print("--- Agent Scratchpad (Reasoning Log) ---")
    print("=" * 60)
    for step in scratchpad:
        print(step)
    print("=" * 60)
