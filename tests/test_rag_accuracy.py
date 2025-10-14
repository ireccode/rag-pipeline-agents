import asyncio
import os
import json
import time
from collections import defaultdict

from src.rag import rag_qa, crawl_and_ingest, setup_supabase_vector_store, CORPUS_URL

# Placeholder for answer keys. In a real scenario, these would be manually curated.
QA_PAIRS = [
    {
        "question": "What is the capital of France?",
        "answer_keywords": ["Paris"],
        "expected_citations": ["https://en.wikipedia.org/wiki/France"] # Example citation
    },
    {
        "question": "Who developed Python?",
        "answer_keywords": ["Guido van Rossum"],
        "expected_citations": ["https://en.wikipedia.org/wiki/Guido_van_Rossum"] # Example citation
    },
    # Add more QA pairs here (at least 20 )
    {
        "question": "What is the primary function of a CPU?",
        "answer_keywords": ["central processing unit", "executes instructions", "performs calculations"],
        "expected_citations": []
    },
    {
        "question": "Explain the concept of photosynthesis.",
        "answer_keywords": ["plants", "sunlight", "energy", "carbon dioxide", "water", "glucose", "oxygen"],
        "expected_citations": []
    },
    {
        "question": "What are the benefits of exercise?",
        "answer_keywords": ["health", "fitness", "mood", "disease prevention", "weight management"],
        "expected_citations": []
    },
    {
        "question": "Describe the water cycle.",
        "answer_keywords": ["evaporation", "condensation", "precipitation", "collection"],
        "expected_citations": []
    },
    {
        "question": "What is artificial intelligence?",
        "answer_keywords": ["machines", "intelligence", "learning", "problem-solving", "decision-making"],
        "expected_citations": []
    },
    {
        "question": "How does a blockchain work?",
        "answer_keywords": ["distributed ledger", "cryptography", "blocks", "transactions", "decentralized"],
        "expected_citations": []
    },
    {
        "question": "What is the difference between HTTP and HTTPS?",
        "answer_keywords": ["security", "encryption", "SSL/TLS", "port 80", "port 443"],
        "expected_citations": []
    },
    {
        "question": "Name three types of renewable energy sources.",
        "answer_keywords": ["solar", "wind", "hydro", "geothermal", "biomass"],
        "expected_citations": []
    },
    {
        "question": "What is the purpose of a firewall?",
        "answer_keywords": ["network security", "monitor traffic", "block unauthorized access"],
        "expected_citations": []
    },
    {
        "question": "Explain quantum computing in simple terms.",
        "answer_keywords": ["qubits", "superposition", "entanglement", "quantum mechanics"],
        "expected_citations": []
    },
    {
        "question": "What is machine learning?",
        "answer_keywords": ["AI", "data", "algorithms", "patterns", "predictions", "without explicit programming"],
        "expected_citations": []
    },
    {
        "question": "How does GPS work?",
        "answer_keywords": ["satellites", "receivers", "triangulation", "location", "time signals"],
        "expected_citations": []
    },
    {
        "question": "What is the internet of things (IoT)?",
        "answer_keywords": ["interconnected devices", "sensors", "data exchange", "network"],
        "expected_citations": []
    },
    {
        "question": "Describe the process of photosynthesis.",
        "answer_keywords": ["plants", "sunlight", "carbon dioxide", "water", "glucose", "oxygen"],
        "expected_citations": []
    },
    {
        "question": "What is cloud computing?",
        "answer_keywords": ["on-demand services", "internet", "servers", "storage", "networking", "software"],
        "expected_citations": []
    },
    {
        "question": "What is the significance of the Eiffel Tower?",
        "answer_keywords": ["Paris", "landmark", "France", "Gustave Eiffel", "World's Fair"],
        "expected_citations": []
    },
    {
        "question": "How do search engines work?",
        "answer_keywords": ["crawling", "indexing", "ranking", "algorithms", "keywords"],
        "expected_citations": []
    },
    {
        "question": "What is virtual reality?",
        "answer_keywords": ["simulated experience", "computer-generated", "immersive", "headset"],
        "expected_citations": []
    },
    {
        "question": "Explain the concept of supply and demand.",
        "answer_keywords": ["economics", "market", "price", "quantity", "equilibrium"],
        "expected_citations": []
    },
]

async def run_qa_evaluation():
    print("\n--- Starting RAG QA Evaluation ---")
    results = []
    latencies = []
    retrieval_accuracies = defaultdict(lambda: {"total": 0, "correct": 0})

    # Ensure Supabase is set up and data is ingested
    await setup_supabase_vector_store()
    if CORPUS_URL:
        print(f"Ingesting data from {CORPUS_URL} for evaluation...")
        await crawl_and_ingest(CORPUS_URL, max_pages=10, min_content_size_mb=1) # Reduced for quick testing
    else:
        print("WARNING: CORPUS_URL not set. RAG evaluation will rely on pre-existing data in Supabase.")

    for i, qa_pair in enumerate(QA_PAIRS):
        question = qa_pair["question"]
        answer_keywords = [k.lower() for k in qa_pair["answer_keywords"]]
        expected_citations = qa_pair["expected_citations"]

        print(f"\nQuestion {i+1}: {question}")
        rag_answer, citations, latency, _ = await rag_qa(question)
        latencies.append(latency)

        # Evaluate answer correctness (simple keyword matching for now)
        is_answer_correct = any(keyword in rag_answer.lower() for keyword in answer_keywords)
        # Evaluate citation accuracy (simple check if any expected citation is present)
        is_citation_correct = any(exp_cite in citations for exp_cite in expected_citations)

        # Top-5 retrieval accuracy (placeholder - needs actual retrieval context for this)
        # For now, we'll just check if *any* relevant document was retrieved based on citations
        if expected_citations and any(cite in expected_citations for cite in citations):
            retrieval_accuracies["top_5"]["correct"] += 1
        retrieval_accuracies["top_5"]["total"] += 1

        results.append({
            "question": question,
            "rag_answer": rag_answer,
            "citations": citations,
            "is_answer_correct": is_answer_correct,
            "is_citation_correct": is_citation_correct,
            "latency_ms": latency
        })
        print(f"RAG Answer: {rag_answer}")
        print(f"Citations: {citations}")
        print(f"Answer Correct: {is_answer_correct}")
        print(f"Citation Correct: {is_citation_correct}")

    # Calculate metrics
    median_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0
    overall_answer_accuracy = sum(1 for r in results if r["is_answer_correct"]) / len(results) if results else 0
    overall_citation_accuracy = sum(1 for r in results if r["is_citation_correct"]) / len(results) if results else 0
    top_5_retrieval_accuracy = retrieval_accuracies["top_5"]["correct"] / retrieval_accuracies["top_5"]["total"] if retrieval_accuracies["top_5"]["total"] > 0 else 0

    print("\n--- Evaluation Summary ---")
    print(f"Median Retrieval Time: {median_latency:.2f} ms")
    print(f"Overall Answer Accuracy: {overall_answer_accuracy:.2%}")
    print(f"Overall Citation Accuracy: {overall_citation_accuracy:.2%}")
    print(f"Top-5 Retrieval Accuracy: {top_5_retrieval_accuracy:.2%}")

    # Save results to a JSON file
    os.makedirs("reports", exist_ok=True)
    report_filename = f"reports/rag_evaluation_report_{int(time.time())}.json"
    with open(report_filename, "w") as f:
        json.dump({
            "summary": {
                "median_latency_ms": median_latency,
                "overall_answer_accuracy": overall_answer_accuracy,
                "overall_citation_accuracy": overall_citation_accuracy,
                "top_5_retrieval_accuracy": top_5_retrieval_accuracy,
            },
            "individual_results": results
        }, f, indent=4)
    print(f"Detailed report saved to {report_filename}")

    print("--- RAG QA Evaluation Finished ---")

if __name__ == "__main__":
    asyncio.run(run_qa_evaluation())
