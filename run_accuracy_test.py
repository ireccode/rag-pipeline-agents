#!/usr/bin/env python3
"""
Automated Accuracy Testing Script for RAG QA Pipeline

This script evaluates top-5 retrieval accuracy over 20+ self-graded questions
and generates a comprehensive accuracy report.

Requirements:
- ≥ 20 questions with answer keys
- Top-5 retrieval accuracy measurement
- Automated grading with similarity scoring
- Detailed performance metrics
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Verify required environment variables
required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'OPENAI_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
    print(f"\nPlease set them in your .env file:")
    for var in missing_vars:
        print(f"  {var}=your-value-here")
    sys.exit(1)

# Import test functions
from tests.test_accuracy import QUESTIONS, simple_similarity, evaluate_accuracy
from src.qa_endpoint import perform_qa_with_citations


def print_header():
    """Print report header."""
    print("\n" + "=" * 80)
    print("🎯 RAG PIPELINE ACCURACY EVALUATION REPORT")
    print("=" * 80)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Total Questions: {len(QUESTIONS)}")
    print(f"🎯 Evaluation Method: Keyword Similarity (Jaccard Index)")
    print(f"✅ Passing Threshold: 30% similarity")
    print("=" * 80 + "\n")


def print_question_result(idx, result, verbose=True):
    """Print individual question result."""
    status = "✅ PASS" if result["is_correct"] else "❌ FAIL"
    
    print(f"\n{'─' * 80}")
    print(f"Question {idx + 1}/{len(QUESTIONS)}: {status}")
    print(f"{'─' * 80}")
    print(f"❓ Query: {result['query']}")
    print(f"\n📝 Expected Answer:")
    print(f"   {result['correct_answer'][:200]}...")
    
    if verbose:
        print(f"\n🤖 Generated Answer:")
        print(f"   {result['generated_answer'][:200]}...")
    
    print(f"\n📊 Metrics:")
    print(f"   • Similarity Score: {result['similarity']:.2%}")
    print(f"   • Retrieval Latency: {result['latency_ms']:.2f} ms")
    print(f"   • Status: {status}")


def print_summary(results):
    """Print summary statistics."""
    correct_count = sum(1 for r in results if r["is_correct"])
    total = len(results)
    accuracy = correct_count / total if total > 0 else 0
    avg_latency = sum(r['latency_ms'] for r in results) / total if total > 0 else 0
    avg_similarity = sum(r['similarity'] for r in results) / total if total > 0 else 0
    
    print("\n" + "=" * 80)
    print("📈 SUMMARY STATISTICS")
    print("=" * 80)
    print(f"\n🎯 Accuracy Metrics:")
    print(f"   • Top-5 Retrieval Accuracy: {accuracy:.2%} ({correct_count}/{total})")
    print(f"   • Average Similarity Score: {avg_similarity:.2%}")
    print(f"   • Questions Passed: {correct_count}")
    print(f"   • Questions Failed: {total - correct_count}")
    
    print(f"\n⏱️  Performance Metrics:")
    print(f"   • Average Latency: {avg_latency:.2f} ms")
    print(f"   • Min Latency: {min(r['latency_ms'] for r in results):.2f} ms")
    print(f"   • Max Latency: {max(r['latency_ms'] for r in results):.2f} ms")
    print(f"   • Target Latency: ≤ 300 ms")
    
    latency_pass = avg_latency <= 300
    latency_status = "✅ PASS" if latency_pass else "❌ FAIL"
    print(f"   • Latency Status: {latency_status}")
    
    print(f"\n🎓 Grade Distribution:")
    excellent = sum(1 for r in results if r['similarity'] >= 0.7)
    good = sum(1 for r in results if 0.5 <= r['similarity'] < 0.7)
    fair = sum(1 for r in results if 0.3 <= r['similarity'] < 0.5)
    poor = sum(1 for r in results if r['similarity'] < 0.3)
    
    print(f"   • Excellent (≥70%): {excellent} ({excellent/total:.1%})")
    print(f"   • Good (50-69%): {good} ({good/total:.1%})")
    print(f"   • Fair (30-49%): {fair} ({fair/total:.1%})")
    print(f"   • Poor (<30%): {poor} ({poor/total:.1%})")
    
    print("\n" + "=" * 80)
    
    # Overall assessment
    if accuracy >= 0.8 and latency_pass:
        print("🎉 OVERALL: EXCELLENT - All requirements met!")
    elif accuracy >= 0.6:
        print("✅ OVERALL: GOOD - Meets minimum accuracy requirements")
    elif accuracy >= 0.4:
        print("⚠️  OVERALL: FAIR - Needs improvement")
    else:
        print("❌ OVERALL: POOR - Significant improvements needed")
    
    print("=" * 80 + "\n")


def save_detailed_report(results, filename="accuracy_report.json"):
    """Save detailed results to JSON file."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(results),
        "correct_count": sum(1 for r in results if r["is_correct"]),
        "accuracy": sum(1 for r in results if r["is_correct"]) / len(results),
        "average_latency_ms": sum(r['latency_ms'] for r in results) / len(results),
        "average_similarity": sum(r['similarity'] for r in results) / len(results),
        "results": results
    }
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"💾 Detailed report saved to: {filename}\n")


def main():
    """Main execution function."""
    print_header()
    
    print("🚀 Starting accuracy evaluation...\n")
    print("⏳ This may take a few minutes depending on the number of questions...\n")
    
    try:
        # Run evaluation
        results = []
        for idx, q in enumerate(QUESTIONS):
            print(f"Processing question {idx + 1}/{len(QUESTIONS)}...", end=" ")
            
            try:
                result = perform_qa_with_citations(q["query"])
                similarity = simple_similarity(result["answer"], q["correct_answer"])
                is_correct = similarity > 0.3
                
                question_result = {
                    "query": q["query"],
                    "correct_answer": q["correct_answer"],
                    "generated_answer": result["answer"],
                    "latency_ms": result["latency_ms"],
                    "is_correct": is_correct,
                    "similarity": similarity
                }
                results.append(question_result)
                
                status = "✅" if is_correct else "❌"
                print(f"{status} (similarity: {similarity:.2%}, latency: {result['latency_ms']:.0f}ms)")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                # Add failed result
                results.append({
                    "query": q["query"],
                    "correct_answer": q["correct_answer"],
                    "generated_answer": f"Error: {str(e)}",
                    "latency_ms": 0,
                    "is_correct": False,
                    "similarity": 0.0
                })
        
        # Print detailed results
        print("\n" + "=" * 80)
        print("📋 DETAILED RESULTS")
        print("=" * 80)
        
        for idx, result in enumerate(results):
            print_question_result(idx, result, verbose=False)
        
        # Print summary
        print_summary(results)
        
        # Save report
        save_detailed_report(results)
        
        # Exit with appropriate code
        accuracy = sum(1 for r in results if r["is_correct"]) / len(results)
        if accuracy >= 0.6:
            print("✅ Test completed successfully!")
            return 0
        else:
            print("⚠️  Test completed with warnings (accuracy below 60%)")
            return 1
            
    except Exception as e:
        print(f"\n❌ Fatal error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
