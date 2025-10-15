"""
Self-Healing Code Assistant - Task 4

A code assistant that:
1. Receives natural-language coding tasks
2. Generates code with LLM
3. Writes to disk and executes tests
4. Captures errors and retries with LLM feedback (max 3 attempts)
5. Uses RAG to search for similar code examples after first failure
6. Streams progress to console
"""

import os
import json
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Import RAG utilities
try:
    from utils import get_supabase_client, search_code_examples
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️  RAG utilities not available. Code examples search will be disabled.")

# Import metrics tracking
try:
    from metrics import MetricsTracker
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    print("⚠️  Metrics tracking not available.")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
USE_CODE_EXAMPLES = os.getenv("USE_CODE_EXAMPLES", "true").lower() == "true"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

class CodeAssistant:
    """Self-healing code assistant with retry logic."""
    
    def __init__(self, model_name: str = MODEL_NAME, max_retries: int = 3, enable_metrics: bool = True):
        self.model_name = model_name
        self.max_retries = max_retries
        self.conversation_history = []
        self.supabase_client = None
        self.metrics_tracker = None
        
        # Initialize metrics tracker
        if METRICS_AVAILABLE and enable_metrics:
            try:
                self.metrics_tracker = MetricsTracker()
            except Exception as e:
                print(f"⚠️  Failed to initialize metrics: {e}")
        
        # Initialize Supabase client for RAG if available
        if RAG_AVAILABLE and USE_CODE_EXAMPLES:
            try:
                # Verify environment variables are set
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
                
                if not supabase_url or not supabase_key:
                    print("⚠️  SUPABASE_URL or SUPABASE_SERVICE_KEY not set in environment")
                    print("RAG code examples search will be disabled")
                else:
                    self.supabase_client = get_supabase_client()
                    print("✓ RAG code examples search enabled")
            except Exception as e:
                print(f"❌ Failed to initialize RAG: {e}")
                self.supabase_client = None
        
    def _log(self, message: str, level: str = "INFO"):
        """Log progress to console with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "RETRY": "🔄",
            "CODE": "💻"
        }.get(level, "•")
        print(f"[{timestamp}] {prefix} {message}")
    
    def _detect_language(self, task: str) -> Tuple[str, str, str]:
        """
        Detect programming language from task description.
        
        Returns:
            Tuple of (language, file_extension, test_command)
        """
        task_lower = task.lower()
        
        if "rust" in task_lower or "cargo" in task_lower:
            return "rust", "rs", "cargo test"
        elif "python" in task_lower or "pytest" in task_lower:
            return "python", "py", "pytest"
        elif "javascript" in task_lower or "js" in task_lower or "node" in task_lower:
            return "javascript", "js", "npm test"
        elif "typescript" in task_lower or "ts" in task_lower:
            return "typescript", "ts", "npm test"
        elif "go" in task_lower or "golang" in task_lower:
            return "go", "go", "go test"
        else:
            # Default to Python
            return "python", "py", "pytest"
    
    def _search_code_examples(self, task: str, language: str) -> List[Dict[str, Any]]:
        """
        Search for similar code examples using RAG.
        
        Args:
            task: The coding task description
            language: Programming language
            
        Returns:
            List of code examples with content and summaries
        """
        if not self.supabase_client:
            return []
        
        try:
            self._log(f"🔍 Searching for similar {language} code examples...", "INFO")
            
            # Extract key terms from task for better search
            search_query = f"{language} {task}"
            
            # Try using search_code_examples first
            try:
                results = search_code_examples(
                    client=self.supabase_client,
                    query=search_query,
                    match_count=3
                )
                
                if results and len(results) > 0:
                    self._log(f"Found {len(results)} similar code examples via RPC", "SUCCESS")
                    return results
                else:
                    self._log("RPC returned 0 results, using fallback...", "INFO")
            except Exception as rpc_error:
                self._log(f"RPC search failed: {rpc_error}, using fallback...", "INFO")
                
            # Fallback: Get all code examples directly
            all_examples = self.supabase_client.table('code_examples').select('*').execute()
            
            if all_examples.data and len(all_examples.data) > 0:
                # Simple fallback: return all examples (they're relevant since we only have a few)
                self._log(f"Found {len(all_examples.data)} code examples (fallback mode)", "SUCCESS")
                return all_examples.data[:3]  # Return first 3
            
            self._log("No code examples found in database", "INFO")
            return []
                
        except Exception as e:
            self._log(f"Error searching code examples: {e}", "ERROR")
            return []
    
    def _generate_code(self, task: str, language: str, error_feedback: Optional[str] = None, code_examples: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate code using LLM.
        
        Args:
            task: Natural language description of the coding task
            language: Programming language to use
            error_feedback: Optional error message from previous attempt
            code_examples: Optional list of similar code examples from RAG
            
        Returns:
            Generated code as string
        """
        # Build examples context if available
        examples_context = ""
        if code_examples:
            self._log(f"Including {len(code_examples)} code examples as context", "INFO")
            examples_context = "\n\nHere are some similar working code examples for reference:\n\n"
            for i, example in enumerate(code_examples, 1):
                examples_context += f"Example {i}:\n"
                examples_context += f"Summary: {example.get('summary', 'N/A')}\n"
                examples_context += f"```{language}\n{example.get('content', '')[:500]}...\n```\n\n"
        
        if error_feedback:
            self._log(f"Regenerating code with error feedback", "RETRY")
            prompt = f"""The previous code attempt failed with the following error:

{error_feedback}

Please fix the code and provide a corrected version. Original task: {task}
{examples_context}
Provide ONLY the corrected code without any explanations or markdown formatting."""
        else:
            self._log(f"Generating code for: {task}", "CODE")
            prompt = f"""Write {language} code for the following task: {task}

Requirements:
1. Include all necessary imports
2. Write complete, runnable code
3. Include appropriate test cases (using pytest for Python, cargo test for Rust, etc.)
4. Follow best practices for {language}
5. Add helpful comments
{examples_context}
Provide ONLY the code without any explanations or markdown formatting."""
        
        # Add to conversation history
        if not self.conversation_history:
            self.conversation_history.append({
                "role": "system",
                "content": f"You are an expert {language} programmer. Generate clean, tested, production-ready code."
            })
        
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Stream the response
        self._log("Streaming code generation...", "INFO")
        response = client.chat.completions.create(
            model=self.model_name,
            messages=self.conversation_history,
            stream=True
        )
        
        generated_code = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                generated_code += content
        
        print()  # New line after streaming
        
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": generated_code})
        
        # Clean up markdown code blocks if present
        generated_code = generated_code.strip()
        if generated_code.startswith("```"):
            lines = generated_code.split("\n")
            # Remove first line (```language) and last line (```)
            generated_code = "\n".join(lines[1:-1]) if len(lines) > 2 else generated_code
        
        return generated_code
    
    def _write_code_to_file(self, code: str, file_path: Path) -> None:
        """Write generated code to file."""
        self._log(f"Writing code to: {file_path}", "INFO")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(code)
    
    def _execute_tests(self, test_command: str, working_dir: Path) -> Tuple[bool, str]:
        """
        Execute tests and capture output.
        
        Returns:
            Tuple of (success: bool, output: str)
        """
        self._log(f"Executing: {test_command}", "INFO")
        
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            success = result.returncode == 0
            
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Test execution timed out after 30 seconds"
        except Exception as e:
            return False, f"Test execution failed: {str(e)}"
    
    def generate_and_test(self, task: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Main method: Generate code, test it, and retry on failure.
        
        Args:
            task: Natural language description of the coding task
            output_dir: Optional directory to write code (uses temp dir if not provided)
            
        Returns:
            Dictionary with results including success status, code, and test output
        """
        self._log("=" * 60, "INFO")
        self._log("SELF-HEALING CODE ASSISTANT - TASK 4", "INFO")
        self._log("=" * 60, "INFO")
        self._log(f"Task: {task}", "INFO")
        
        # Detect language
        language, extension, test_command = self._detect_language(task)
        self._log(f"Detected language: {language}", "INFO")
        self._log(f"Test command: {test_command}", "INFO")
        
        # Setup output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="code_assistant_"))
        else:
            output_dir = Path(output_dir)
        
        self._log(f"Output directory: {output_dir}", "INFO")
        
        # Start metrics tracking
        task_run_id = None
        start_time = time.time()
        if self.metrics_tracker:
            task_run_id = self.metrics_tracker.start_task(task, language)
        
        # Main retry loop
        code_examples = None  # Will be populated after first failure
        rag_examples_found = 0
        
        for attempt in range(1, self.max_retries + 1):
            self._log(f"\n--- Attempt {attempt}/{self.max_retries} ---", "INFO")
            
            # After first failure, search for code examples to help with retry
            if attempt == 2 and self.supabase_client:
                self._log("First attempt failed. Searching for similar code examples...", "RETRY")
                code_examples = self._search_code_examples(task, language)
                rag_examples_found = len(code_examples) if code_examples else 0
            
            # Generate code
            attempt_start = time.time()
            if attempt == 1:
                code = self._generate_code(task, language)
            else:
                code = self._generate_code(task, language, error_feedback=last_error, code_examples=code_examples)
            
            # Write to file
            if language == "python":
                file_path = output_dir / f"solution.{extension}"
            elif language == "rust":
                # Create Cargo project structure
                file_path = output_dir / "src" / f"lib.{extension}"
                # Create Cargo.toml
                cargo_toml = output_dir / "Cargo.toml"
                cargo_toml.parent.mkdir(parents=True, exist_ok=True)
                with open(cargo_toml, 'w') as f:
                    f.write('[package]\nname = "solution"\nversion = "0.1.0"\n')
            else:
                file_path = output_dir / f"solution.{extension}"
            
            self._write_code_to_file(code, file_path)
            
            # Execute tests
            success, test_output = self._execute_tests(test_command, output_dir)
            attempt_time = time.time() - attempt_start
            
            # Log attempt metrics
            if self.metrics_tracker and task_run_id:
                error_type = None if success else "test_failure"
                self.metrics_tracker.log_attempt(
                    task_run_id, attempt, attempt_time,
                    error_type=error_type,
                    error_message=test_output if not success else None,
                    code_generated=code
                )
            
            if success:
                self._log("Tests passed! ✨", "SUCCESS")
                total_time = time.time() - start_time
                
                # Complete metrics tracking
                if self.metrics_tracker and task_run_id:
                    self.metrics_tracker.complete_task(
                        task_run_id, True, attempt, total_time, attempt,
                        rag_used=rag_examples_found > 0,
                        rag_examples_found=rag_examples_found
                    )
                
                return {
                    "success": True,
                    "task": task,
                    "language": language,
                    "attempts": attempt,
                    "code": code,
                    "file_path": str(file_path),
                    "test_output": test_output,
                    "output_dir": str(output_dir)
                }
            else:
                self._log(f"Tests failed on attempt {attempt}", "ERROR")
                self._log(f"Error output:\n{test_output}", "ERROR")
                last_error = test_output
                
                if attempt < self.max_retries:
                    self._log(f"Retrying with error feedback...", "RETRY")
        
        # All attempts failed
        self._log(f"Failed after {self.max_retries} attempts", "ERROR")
        total_time = time.time() - start_time
        
        # Complete metrics tracking for failure
        if self.metrics_tracker and task_run_id:
            self.metrics_tracker.complete_task(
                task_run_id, False, self.max_retries, total_time, self.max_retries,
                rag_used=rag_examples_found > 0,
                rag_examples_found=rag_examples_found,
                error_message="Maximum retry attempts reached"
            )
        
        return {
            "success": False,
            "task": task,
            "language": language,
            "attempts": self.max_retries,
            "code": code,
            "file_path": str(file_path),
            "test_output": test_output,
            "error": "Maximum retry attempts reached",
            "output_dir": str(output_dir)
        }


def main():
    """Example usage of the code assistant."""
    assistant = CodeAssistant()
    
    # Example tasks
    tasks = [
        # "Write a Python function to implement quicksort with unit tests using pytest",
        "Write a Rust function to implement binary search with tests",
    ]
    
    for task in tasks:
        result = assistant.generate_and_test(task)
        
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(f"Success: {result['success']}")
        print(f"Attempts: {result['attempts']}")
        print(f"Language: {result['language']}")
        print(f"File: {result['file_path']}")
        if result['success']:
            print(f"\n✅ Code successfully generated and tested!")
        else:
            print(f"\n❌ Failed to generate working code")
        print("=" * 60)


if __name__ == "__main__":
    main()
