import os
import time
import sqlite3
from openai import OpenAI
from collections import deque
from dotenv import load_dotenv
import tiktoken

load_dotenv() # Load environment variables from .env file

# Configuration from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1" )
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini") # Default to a placeholder model

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# Message persistence (SQLite)
DB_NAME = "chat_history.db"
MAX_MESSAGES = 10

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_message(role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    # Enforce MAX_MESSAGES by deleting oldest if count exceeds
    cursor.execute("DELETE FROM messages WHERE id NOT IN (SELECT id FROM messages ORDER BY timestamp DESC LIMIT ?)", (MAX_MESSAGES,))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages ORDER BY timestamp ASC")
    messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
    conn.close()
    return messages

# Token and cost estimation (simplified, placeholder values)
# These are approximate and should be updated with actual model pricing
TOKEN_COST_INPUT_PER_1K = 0.0005  # Example for a cheap model
TOKEN_COST_OUTPUT_PER_1K = 0.0015 # Example for a cheap model

def estimate_cost(prompt_tokens, completion_tokens):
    input_cost = (prompt_tokens / 1000) * TOKEN_COST_INPUT_PER_1K
    output_cost = (completion_tokens / 1000) * TOKEN_COST_OUTPUT_PER_1K
    return input_cost + output_cost

def count_tokens(text, model_name=MODEL_NAME):
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base") # Fallback for unknown models
    return len(encoding.encode(text))

def chat_cli():
    init_db()
    print("\nWelcome to the Streaming Chat CLI! Type 'exit' to quit.")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break

        add_message("user", user_input)
        messages = get_messages()

        start_time = time.time()
        full_response_content = ""
        prompt_tokens = sum(count_tokens(m["content"]) for m in messages)

        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                stream=True,
            )

            print("Assistant: ", end="", flush=True)
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    full_response_content += chunk.choices[0].delta.content
            print()

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            completion_tokens = count_tokens(full_response_content)
            total_cost = estimate_cost(prompt_tokens, completion_tokens)

            add_message("assistant", full_response_content)

            print(f"\n--- Metrics ---")
            print(f"Prompt Tokens: {prompt_tokens}")
            print(f"Completion Tokens: {completion_tokens}")
            print(f"Estimated Cost: ${total_cost:.6f} USD")
            print(f"Latency: {latency_ms:.2f} ms")
            print(f"---------------")

        except Exception as e:
            print(f"Error: {e}")
            # Remove the last user message if the API call fails to avoid polluting history
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE role = 'user' ORDER BY timestamp DESC LIMIT 1")
            conn.commit()
            conn.close()

if __name__ == "__main__":
    chat_cli()
