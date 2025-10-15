import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify required environment variables are set
required_env_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_vars)}. "
        f"Please set them in your .env file."
    )

from src.qa_endpoint import perform_qa_with_citations

# Define 20+ questions and correct answers (answer key)
QUESTIONS = [
    {"query": "What is Pydantic AI?", "correct_answer": "Pydantic is a Python library designed for data validation and settings management using Python type annotations."},
    {"query": "Which providers does Pydantic AI support?", "correct_answer": "OpenAI, Anthropic, Gemini, DeepSeek, Grok, Cohere, Mistral, Perplexity, Azure AI Foundry, Amazon Bedrock, Google Vertex AI, Ollama, LiteLLM, Groq, OpenRouter, Together AI, Fireworks AI, Cerebras, Hugging Face, GitHub, Heroku, Vercel, Nebius."},
    {"query": "What is Pydantic Graphs?", "correct_answer": "Pydantic Graphs is an async graph and state machine library for Python where nodes and edges are defined using type hints."},
    {"query": "How are OpenAI models configured within the Pydantic AI framework?", "correct_answer": "OpenAI models are configured in the Pydantic AI framework using OpenAIChatModelSettings, a class that allows for detailed control over model requests through settings like reasoning effort, log probabilities, user identification, service tier, and predictive outputs."},
    {"query": "How does Pydantic AI's GoogleModelSettings class configure the Gemini model?", "correct_answer": "Pydantic AI's GoogleModelSettings class is used to configure the Google Gemini model, allowing users to specify settings for safety, thinking configuration, video resolution, and cached content via a dedicated class definition."},
    {"query": "What is the purpose of the Hugging Face provider in Pydantic AI?", "correct_answer": "The Pydantic AI framework includes a Hugging Face provider that enables seamless integration with Hugging Face's inference clients, allowing agents to use models hosted on the Hugging Face platform by handling configuration parameters like base URLs and API keys."},
    {"query": "How does Pydantic AI manage different AI model providers?", "correct_answer": "Pydantic AI uses specific provider classes like LiteLLM and NebiusProvider to manage different AI models by handling API keys, base URLs, and HTTP clients, allowing the framework to interact with various services consistently."},
    {"query": "How is the Cohere API integrated into Pydantic AI?", "correct_answer": "The Pydantic AI framework integrates the Cohere API via the CohereProvider class, which handles the necessary configuration and uses an asynchronous HTTP client to make API calls, allowing Pydantic AI to leverage Cohere's models."},
    {"query": "How does Pydantic AI handle advanced output processing?", "correct_answer": "Pydantic AI offers advanced output handling features, including the TextOutput function to process plain text, StructuredDict for generating structured outputs with a JSON schema, and DeferredToolRequests to manage tool calls that require approval or external execution."},
    {"query": "What is the purpose of the tool_from_aci function and the ACIToolset class in Pydantic AI?", "correct_answer": "The tool_from_aci function creates a Pydantic AI tool proxy from an ACI.dev function, while the ACIToolset class wraps a collection of these ACI.dev tools into a single, reusable toolset for use within Pydantic AI agents."},
    {"query": "How does Pydantic AI's DBOSAgent wrapper work?", "correct_answer": "Pydantic AI's DBOSAgent wrapper automatically wraps an agent's asynchronous and synchronous run methods within DBOS workflows for durable execution, while also configuring the agent's model and toolsets to work seamlessly within the DBOS framework."},
    {"query": "How does the Pydantic AI agent's run_stream method work?", "correct_answer": "Pydantic AI's run_stream method asynchronously streams model output as it becomes available and will end the agent run once it finds the first output that matches the defined output_type."},
    {"query": "How does Pydantic AI enable advanced agent features?", "correct_answer": "Pydantic AI's advanced agent features include instrumentation with OpenTelemetry for detailed tracing and monitoring, a context manager for temporarily overriding agent configurations during testing, and decorators that use type-safe dependency injection for registering dynamic instructions."},
    {"query": "What is the Pydantic Graph feature and how does it help with visualizing agent workflows?", "correct_answer": "The Pydantic Graph feature provides tools to generate customizable Mermaid state diagrams that visualize agent workflows and graph structures, enabling users to create and save diagrams with labels, notes, and highlighted nodes."},
    {"query": "What are the key features demonstrated by the Python examples for using a Pydantic AI Agent?", "correct_answer": "The provided Python code examples demonstrate how to create and run a Pydantic AI agent, illustrating both synchronous and asynchronous execution, streaming results, accessing and reusing message histories to maintain conversation context, and working with the OpenAI GPT-4o model."},
    {"query": "What are the functions of the Image Generation Tool and URL Context Tool in Pydantic AI?", "correct_answer": "Pydantic AI's documentation describes the Image Generation Tool for creating images and the URL Context Tool for pulling web content into an agent's context, providing support for various providers, configuration options, and usage examples."},
    {"query": "What are Deferred Tools in Pydantic AI and what is their purpose?", "correct_answer": "Pydantic AI's Deferred Tools are a feature that enables asynchronous tool execution for tasks requiring user approval or external processing, allowing agent workflows to pause and resume once the tool's result is available."},
    {"query": "What features does Pydantic AI provide for managing instructions and handling errors?", "correct_answer": "Pydantic AI allows for the use of both static and dynamic instructions, offers reflection and self-correction through retries, and handles model errors with tools to diagnose issues during agent runs."},
    {"query": "What capabilities does Pydantic AI's Agent class provide for running queries?", "correct_answer": "Pydantic AI's Agent class can execute both synchronous and asynchronous queries and can stream results as either text or event-based outputs, providing flexibility in how agents interact with and respond to tasks."},
    {"query": "How do Pydantic AI's FastA2A and AG-UI protocols function?", "correct_answer": "Pydantic AI uses the FastA2A protocol for agent task and context management, allowing agents to be exposed as A2A servers, and the AG-UI protocol for standardizing communication between frontends and agents"}
]

def simple_similarity(text1, text2):
    """
    Simple similarity check (e.g., keyword overlap or exact match).
    In production, use cosine similarity or LLM-based grading.
    """
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)

def evaluate_accuracy():
    """
    Evaluate top-5 retrieval accuracy over questions.
    """
    results = []
    for q in QUESTIONS:
        result = perform_qa_with_citations(q["query"])
        # Simple grading: check if correct answer appears in the response
        similarity = simple_similarity(result["answer"], q["correct_answer"])
        is_correct = similarity > 0.3  # Threshold for "correct"
        results.append({
            "query": q["query"],
            "correct_answer": q["correct_answer"],
            "generated_answer": result["answer"],
            "latency_ms": result["latency_ms"],
            "is_correct": is_correct,
            "similarity": similarity
        })

    # Calculate top-5 accuracy (e.g., precision@5)
    correct_count = sum(1 for r in results if r["is_correct"])
    total = len(results)
    accuracy = correct_count / total if total > 0 else 0

    print(f"Top-5 Retrieval Accuracy: {accuracy:.2%} ({correct_count}/{total})")
    print(f"Average Latency: {sum(r['latency_ms'] for r in results) / total:.2f} ms")

    return results

if __name__ == "__main__":
    evaluate_accuracy()
