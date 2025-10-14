import os
import asyncio
from deepeval import evaluate
from deepeval.metrics import (AnswerRelevancyMetric, ContextRelevancyMetric, FaithfulnessMetric, BiasMetric, ToxicityMetric)
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset
from deepeval.models import DeepEvalBaseLLM
from dotenv import load_dotenv

from src.rag import rag_qa, crawl_and_ingest, setup_supabase_vector_store, CORPUS_URL

load_dotenv()

# Configuration from environment variables
LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "ollama/deepseek-coder:8b") # Default to Ollama model

# Placeholder for answer keys. In a real scenario, these would be manually curated.
QA_PAIRS_FOR_DEEPEVAL = [
    {
        "question": "What is the capital of France?",
        "expected_answer": "Paris",
        "expected_context": ["France is a country in Western Europe. Its capital is Paris."],
        "expected_citations": ["https://en.wikipedia.org/wiki/France"]
    },
    {
        "question": "Who developed Python?",
        "expected_answer": "Guido van Rossum",
        "expected_context": ["Python was created by Guido van Rossum."],
        "expected_citations": ["https://en.wikipedia.org/wiki/Guido_van_Rossum"]
    },
    {
        "question": "What is the primary function of a CPU?",
        "expected_answer": "The primary function of a CPU is to execute instructions and perform calculations.",
        "expected_context": ["A Central Processing Unit (CPU ) is the electronic circuitry within a computer that carries out the instructions of a computer program by performing the basic arithmetic, logic, controlling, and input/output (I/O) operations specified by the instructions."],
        "expected_citations": []
    },
    {
        "question": "Explain the concept of photosynthesis.",
        "expected_answer": "Photosynthesis is the process used by plants, algae, and certain bacteria to turn light energy into chemical energy.",
        "expected_context": ["Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy that can later be released to fuel the organisms' activities."],
        "expected_citations": []
    },
    {
        "question": "What are the benefits of exercise?",
        "expected_answer": "Exercise offers numerous benefits including improved cardiovascular health, weight management, mood enhancement, and reduced risk of chronic diseases.",
        "expected_context": ["Regular physical activity can improve your muscle strength and boost your endurance. Exercise delivers oxygen and nutrients to your tissues and helps your cardiovascular system work more efficiently."],
        "expected_citations": []
    },
    {
        "question": "Describe the water cycle.",
        "expected_answer": "The water cycle describes the continuous movement of water on, above, and below the surface of the Earth, involving processes like evaporation, condensation, precipitation, and collection.",
        "expected_context": ["The water cycle, also known as the hydrologic cycle, describes the continuous movement of water on, above, and below the surface of the Earth. The mass of water on Earth remains fairly constant over time but the way it is distributed changes."],
        "expected_citations": []
    },
    {
        "question": "What is artificial intelligence?",
        "expected_answer": "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals and humans.",
        "expected_context": ["Artificial intelligence (AI) is a broad branch of computer science concerned with building smart machines capable of performing tasks that typically require human intelligence."],
        "expected_citations": []
    },
    {
        "question": "How does a blockchain work?",
        "expected_answer": "A blockchain is a decentralized, distributed ledger technology that records transactions across many computers so that any involved block cannot be altered retroactively, without the alteration of all subsequent blocks.",
        "expected_context": ["A blockchain is a distributed database that is shared among the nodes of a computer network. As a database, a blockchain stores information electronically in digital format."],
        "expected_citations": []
    },
    {
        "question": "What is the difference between HTTP and HTTPS?",
        "expected_answer": "HTTPS is the secure version of HTTP, which means all communications between your browser and the website are encrypted. HTTPS uses SSL/TLS for encryption.",
        "expected_context": ["HTTPS (Hypertext Transfer Protocol Secure) is an extension of the Hypertext Transfer Protocol (HTTP). It is used for secure communication over a computer network, and is widely used on the Internet."],
        "expected_citations": []
    },
    {
        "question": "Name three types of renewable energy sources.",
        "expected_answer": "Three types of renewable energy sources are solar, wind, and hydropower.",
        "expected_context": ["Renewable energy is energy from sources that are naturally replenishing but flow-limited; renewable resources are virtually inexhaustible in duration but limited in the amount of energy that is available per unit of time."],
        "expected_citations": []
    },
    {
        "question": "What is the purpose of a firewall?",
        "expected_answer": "A firewall is a network security system that monitors and controls incoming and outgoing network traffic based on predetermined security rules.",
        "expected_context": ["In computing, a firewall is a network security system that monitors and controls incoming and outgoing network traffic based on predetermined security rules."],
        "expected_citations": []
    },
    {
        "question": "Explain quantum computing in simple terms.",
        "expected_answer": "Quantum computing uses quantum-mechanical phenomena such as superposition and entanglement to perform computations.",
        "expected_context": ["Quantum computing is a type of computation whose operations can harness phenomena typical of quantum mechanics, such as superposition, interference, and entanglement."],
        "expected_citations": []
    },
    {
        "question": "What is machine learning?",
        "expected_answer": "Machine learning is a branch of artificial intelligence (AI) and computer science that focuses on the use of data and algorithms to enable AI to imitate the way that humans learn, gradually improving its accuracy.",
        "expected_context": ["Machine learning (ML) is a field of inquiry devoted to understanding and building methods that 'learn', that is, methods that leverage data to improve performance on some set of tasks."],
        "expected_citations": []
    },
    {
        "question": "How does GPS work?",
        "expected_answer": "GPS works by using a network of satellites orbiting Earth that send precise timing and orbital information to GPS receivers, which then use this data to calculate their exact location.",
        "expected_context": ["The Global Positioning System (GPS) is a satellite-based radionavigation system owned by the United States government and operated by the United States Space Force."],
        "expected_citations": []
    },
    {
        "question": "What is the internet of things (IoT)?",
        "expected_answer": "The Internet of Things (IoT) describes the network of physical objects—'things'—that are embedded with sensors, software, and other technologies for the purpose of connecting and exchanging data with other devices and systems over the internet.",
        "expected_context": ["The Internet of Things (IoT) is a system of interrelated computing devices, mechanical and digital machines, objects, animals or people that are provided with unique identifiers and the ability to transfer data over a network without requiring human-to-human or human-to-computer interaction."],
        "expected_citations": []
    },
    {
        "question": "Describe the process of photosynthesis.",
        "expected_answer": "Photosynthesis is the process used by plants, algae, and certain bacteria to convert light energy into chemical energy that can later be released to fuel the organisms' activities.",
        "expected_context": ["Photosynthesis is a process used by plants and other organisms to convert light energy into chemical energy that can later be released to fuel the organisms' activities."],
        "expected_citations": []
    },
    {
        "question": "What is cloud computing?",
        "expected_answer": "Cloud computing is the on-demand availability of computer system resources, especially data storage (cloud storage) and computing power, without direct active management by the user.",
        "expected_context": ["Cloud computing is the on-demand availability of computer system resources, especially data storage (cloud storage) and computing power, without direct active management by the user."],
        "expected_citations": []
    },
    {
        "question": "What is the significance of the Eiffel Tower?",
        "expected_answer": "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It is a global cultural icon of France and one of the most recognisable structures in the world.",
        "expected_context": ["The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It is named after the engineer Gustave Eiffel, whose company designed and built the tower."],
        "expected_citations": []
    },
    {
        "question": "How do search engines work?",
        "expected_answer": "Search engines work by crawling the internet to discover content, indexing that content, and then ranking it based on relevance to user queries.",
        "expected_context": ["A web search engine is a software system that is designed to carry out web search (Internet search), which means to search the World Wide Web in a systematic way for particular information specified in a textual web search query."],
        "expected_citations": []
    },
    {
        "question": "What is virtual reality?",
        "expected_answer": "Virtual reality (VR) is a simulated experience that can be similar to or completely different from the real world.",
        "expected_context": ["Virtual reality (VR) is a simulated experience that can be similar to or completely different from the real world. Applications of virtual reality include entertainment (particularly video games), education (such as medical or military training) and business (such as virtual meetings)."]
    },
    {
        "question": "Explain the concept of supply and demand.",
        "expected_answer": "Supply and demand is an economic model of price determination in a market. It postulates that in a competitive market, the unit price for a particular good, or other traded item such as labor or liquid financial assets, will vary until it settles at a point where the quantity demanded will equal the quantity supplied, resulting in an economic equilibrium for price and quantity.",
        "expected_context": ["Supply and demand is an economic model of price determination in a market. It concludes that in a competitive market, the unit price for a particular good, or other traded item such as labor or liquid financial assets, will vary until it settles at a point where the quantity demanded will equal the quantity supplied, resulting in an economic equilibrium for price and quantity."],
        "expected_citations": []
    },
]

class OllamaDeepEvalLLM(DeepEvalBaseLLM):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.client = OpenAI(api_key="ollama", base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1" ))

    @property
    def model_name(self):
        return self._model_name

    @model_name.setter
    def model_name(self, value):
        self._model_name = value

    def load_model(self):
        # Ollama models are typically loaded when the server starts
        # No explicit loading needed here, but can add a check if model exists
        pass

    def _call(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0
        )
        return response.choices[0].message.content

    async def a_call(self, prompt: str) -> str:
        # Asynchronous call for compatibility, can use sync _call for simplicity if not critical
        return self._call(prompt)

    @property
    def get_model_name(self):
        return self.model_name

async def run_deepeval_rag_evaluation():
    print("\n--- Starting DeepEval RAG Evaluation ---")

    # Ensure Supabase is set up and data is ingested
    await setup_supabase_vector_store()
    if CORPUS_URL:
        print(f"Ingesting data from {CORPUS_URL} for evaluation...")
        # Use a smaller max_pages and min_content_size_mb for quick testing
        await crawl_and_ingest(CORPUS_URL, max_pages=10, min_content_size_mb=1)
    else:
        print("WARNING: CORPUS_URL not set. DeepEval RAG evaluation will rely on pre-existing data in Supabase.")

    test_cases = []
    for qa_pair in QA_PAIRS_FOR_DEEPEVAL:
        # Perform RAG query to get actual answer and context
        rag_answer, citations, _, retrieved_contents = await rag_qa(qa_pair["question"])
        
        # DeepEval expects context as a list of strings
        # For simplicity, we'll use the expected context for now, but ideally this should come from RAG output
        # For a more robust evaluation, you'd capture the actual context used by rag_qa
        # and pass it here. For now, we'll pass the retrieved docs as context.
        # This requires modifying rag_qa to return the raw retrieved documents.
        # For this example, we'll use the expected_context as a proxy.
        
        # A more accurate way would be to modify rag_qa to return the context it used
        # For now, we'll use the expected_context as a placeholder for what the RAG *should* have retrieved.
        # In a real scenario, you'd extract the `context` string from `rag_qa` and split it into chunks.
        
        # For DeepEval, the `retrieval_context` should be the actual chunks retrieved by the RAG system.
        # Since `rag_qa` currently returns a single `context` string, we'll simulate splitting it.
        # A better `rag_qa` would return `retrieved_docs` directly.
        
        # For the purpose of this evaluation, we'll use the `expected_context` as the `retrieval_context`
        # and the `rag_answer` as the `actual_output`.
        
        test_cases.append(LLMTestCase(
            input=qa_pair["question"],
            actual_output=rag_answer,
            expected_output=qa_pair["expected_answer"],
            retrieval_context=retrieved_contents, # Actual context retrieved by RAG
            # You can also add `context` and `retrieval_statements` if your RAG provides them separately
        ))

    # Initialize DeepEval metrics
    metrics = [
        AnswerRelevancyMetric(threshold=0.7, model=LLM_JUDGE_MODEL, include_reason=True),
        ContextRelevancyMetric(threshold=0.7, model=LLM_JUDGE_MODEL, include_reason=True),
        FaithfulnessMetric(threshold=0.7, model=LLM_JUDGE_MODEL, include_reason=True),
        BiasMetric(threshold=0.5, model=LLM_JUDGE_MODEL, include_reason=True),
        ToxicityMetric(threshold=0.5, model=LLM_JUDGE_MODEL, include_reason=True)
    ]

    # Run evaluation
    # DeepEval will automatically generate a report in the /reports/ directory
    # You can specify a custom directory using `output_dir`
    await evaluate(
        test_cases=test_cases,
        metrics=metrics,
        llm=OllamaDeepEvalLLM(model_name=LLM_JUDGE_MODEL) if "ollama" in LLM_JUDGE_MODEL else None,
        # If using OpenAI compatible API, DeepEval will use the default client configured with env vars
        # For Ollama, we need to pass a custom LLM class.
        # This part needs careful handling based on how DeepEval expects LLM configuration.
        # For simplicity, we'll assume DeepEval can pick up OpenAI client from env vars or use our custom Ollama class.
        # DeepEval's `evaluate` function can take an `llm` argument for the judge model.
        # We'll pass our custom OllamaDeepEvalLLM if LLM_JUDGE_MODEL indicates Ollama.
        # Otherwise, DeepEval will use its default LLM setup, which should pick up OpenAI env vars.
        # output_dir="reports/deepeval_reports"
    )

    print("--- DeepEval RAG Evaluation Finished. Check /reports/ for detailed reports. ---")

if __name__ == "__main__":
    asyncio.run(run_deepeval_rag_evaluation())
