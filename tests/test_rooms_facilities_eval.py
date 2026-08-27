import os
import sys
import json
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from app.ai.rag_pipeline import RAGPipeline
from app.ai.data_processor import get_cached_dataframe

def run_evaluation():
    pipeline = RAGPipeline()

    test_queries = [
        "Where is AR-101?",
        "Where is the Girls Room?",
        "Where is the Reading Room?",
        "Where is the Medical & First Aid Room?",
        "Where is the Training & Placement Cell?",
        "Where is the Main Gate?",
        "Where is the Parking Area?",
        "Where is the Transport Office?",
        "Where is the Central Library?"
    ]

    print("\n=======================================================")
    print("RUNNING ROOMS & FACILITIES SYSTEM EVALUATION")
    print("=======================================================\n")

    for idx, q in enumerate(test_queries, 1):
        print(f"\n[{idx}/9] Testing: '{q}'")
        print("-" * 50)
        try:
            res = pipeline.answer_question(q, session_id=f"test_eval_{idx}")
            print(f"Retrieved Sources: {res.get('sources')}")
            print(f"Map Image: {res.get('image')}")
            print(f"AI Answer:\n{res.get('answer')}")
        except Exception as e:
            print(f"CRASH/ERROR: {e}")

if __name__ == "__main__":
    run_evaluation()
