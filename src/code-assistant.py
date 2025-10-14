import os
import subprocess
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1" )
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1" ) # Default Ollama API base URL
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "deepseek-coder:latest") # Default Ollama model

class CodeAssistant:
    def __init__(self, model_name=MODEL_NAME, ollama_compatible=False):
        self.ollama_compatible = ollama_compatible
        if ollama_compatible:
            self.client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
            self.model_name = OLLAMA_MODEL_NAME
        else:
            self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
            self.model_name = model_name
        self.retry_limit = 3
        self.scratchpad = []

    def _log_progress(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scratchpad.append(f"[{timestamp}] {message}")
        print(f"[Code Assistant] {message}")

    def _generate_code(self, task_description, existing_code=""):
        self._log_progress("Generating code...")
        messages = [
            {"role": "system", "content": (
                "You are an expert Python programmer. Your task is to write clean, efficient, and well-tested code. "
                "If provided with existing code, improve it based on the feedback. "
                "Respond only with the code block, no conversational text. "
                "Ensure the code is complete and runnable. Include necessary imports." 
                "If tests are provided, ensure the code passes them." 
            )},
            {"role": "user", "content": f"Task: {task_description}\n\nExisting code: {existing_code}"
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                stream=True
            )
            full_code = ""
            print("\n--- Generated Code (Streaming) ---")
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    full_code += chunk.choices[0].delta.content
            print("\n----------------------------------")
            return full_code
        except Exception as e:
            self._log_progress(f"Error during code generation: {e}")
            return None

    def _write_code_to_disk(self, filename, code_content):
        try:
            with open(filename, "w") as f:
                f.write(code_content)
            self._log_progress(f"Code written to {filename}")
            return True
        except Exception as e:
            self._log_progress(f"Error writing code to {filename}: {e}")
            return False

    def _run_tests(self, test_file, code_file):
        self._log_progress(f"Running tests from {test_file} against {code_file}...")
        try:
            # Assuming pytest is installed and tests are written for pytest
            # We need to ensure the code_file is discoverable by pytest, e.g., by being in the same directory
            # or by adjusting PYTHONPATH. For simplicity, we'll run pytest in the directory of the code_file.
            code_dir = os.path.dirname(code_file)
            test_dir = os.path.dirname(test_file)
            # Copy test file to code_dir for pytest to discover it easily
            subprocess.run(["cp", test_file, code_dir], check=True)
            test_filename = os.path.basename(test_file)

            result = subprocess.run(
                ["pytest", test_filename],
                cwd=code_dir,
                capture_output=True,
                text=True,
                check=False # Don't raise exception for non-zero exit code (test failures)
            )
            self._log_progress(f"Test output:\n{result.stdout}\n{result.stderr}")
            if result.returncode == 0:
                self._log_progress("Tests passed successfully.")
                return True, result.stdout + result.stderr
            else:
                self._log_progress("Tests failed.")
                return False, result.stdout + result.stderr
        except FileNotFoundError:
            self._log_progress("Pytest or test file not found. Ensure pytest is installed and test file path is correct.")
            return False, "Pytest or test file not found."
        except Exception as e:
            self._log_progress(f"Error running tests: {e}")
            return False, str(e)

    def self_heal(self, task_description, code_filename, test_filename):
        self._log_progress(f"Starting self-healing process for task: {task_description}")
        generated_code = ""
        for attempt in range(self.retry_limit):
            self._log_progress(f"Attempt {attempt + 1}/{self.retry_limit}")

            # Generate or refine code
            generated_code = self._generate_code(task_description, generated_code)
            if not generated_code:
                self._log_progress("Code generation failed.")
                continue

            # Write code to disk
            if not self._write_code_to_disk(code_filename, generated_code):
                continue

            # Run tests
            tests_passed, test_output = self._run_tests(test_filename, code_filename)

            if tests_passed:
                self._log_progress("Code assistant task completed successfully!")
                return True, generated_code, self.scratchpad
            else:
                self._log_progress("Tests failed. Retrying with feedback...")
                # Provide test output as feedback for the next generation attempt
                task_description += f"\n\nPrevious attempt failed with the following errors/output:\n{test_output}\n\nPlease fix the code."

        self._log_progress("Self-healing failed after multiple attempts.")
        return False, generated_code, self.scratchpad

if __name__ == "__main__":
    # Example Usage:
    # 1. Define a coding task
    coding_task = "Write a Python function `add(a, b)` that returns the sum of two numbers."
    code_file = "./temp_add_function.py"
    test_file = "./temp_test_add_function.py"

    # 2. Create a dummy test file (in a real scenario, this would be provided by the user or generated)
    with open(test_file, "w") as f:
        f.write("""
import pytest
from temp_add_function import add

def test_add_positive_numbers():
    assert add(1, 2) == 3

def test_add_negative_numbers():
    assert add(-1, -1) == -2

def test_add_zero():
    assert add(0, 0) == 0
""")

    assistant = CodeAssistant(ollama_compatible=False) # Set to True to use Ollama
    success, final_code, logs = assistant.self_heal(coding_task, code_file, test_file)

    print("\n--- Final Result ---")
    print(f"Success: {success}")
    print("\n--- Final Code ---")
    print(final_code)
    print("\n--- Assistant Logs ---")
    for log in logs:
        print(log)

    # Clean up generated files
    if os.path.exists(code_file):
        os.remove(code_file)
    if os.path.exists(test_file):
        os.remove(test_file)
    if os.path.exists(os.path.join(os.path.dirname(code_file), os.path.basename(test_file))):
        os.remove(os.path.join(os.path.dirname(code_file), os.path.basename(test_file)))


