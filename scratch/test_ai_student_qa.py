import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding='utf-8')

from app.ai.rag_pipeline import get_rag_pipeline

rag = get_rag_pipeline()
mock_student = {
    "full_name": "Manav Solanki",
    "program": "BE",
    "department": "Computer Engineering",
    "semester": 5,
    "division": "A",
    "batch": "A1",
    "enrollment_no": "210410107001"
}

print("=== QUESTION 1: Mid-Semester exam notice ===")
res1 = rag.answer_question(
    question="What is the schedule for mid semester examination?",
    session_id="test_student_sess",
    user_profile=mock_student
)
print("Answer 1:\n", res1.get("answer"))
print("Sources 1:", res1.get("sources"))

print("\n=== QUESTION 2: Prakarsh Tech Fest Event ===")
res2 = rag.answer_question(
    question="Tell me about Prakarsh 2026 tech fest event details",
    session_id="test_student_sess",
    user_profile=mock_student
)
print("Answer 2:\n", res2.get("answer"))
print("Sources 2:", res2.get("sources"))

print("\n=== QUESTION 3: Rain alert / holiday notice ===")
res3 = rag.answer_question(
    question="Is there any emergency weather alert or rain notice?",
    session_id="test_student_sess",
    user_profile=mock_student
)
print("Answer 3:\n", res3.get("answer"))
print("Sources 3:", res3.get("sources"))
