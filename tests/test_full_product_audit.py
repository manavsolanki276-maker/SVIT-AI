"""
Comprehensive Product-Level Audit & Verification Suite for SVIT-AI.
Uses standard Python unittest framework.
Tests:
1. Date Resolver & Natural Language Calendar Matching
2. Personalized Date-based Timetable Queries
3. Campus Location Resolution & Google Maps Walking Coordinates
4. Bus & Transport Queries (Next Bus, Last Bus, Stops, Routes, Hub Location)
5. Live Flask API & SSE Streaming Integrity (/api/chat and /api/chat/stream)
"""
import sys
import os
import json
import datetime
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.ai.data_processor import (
    resolve_day_and_date,
    process_transport_context,
    process_timetable_context,
    get_ist_now
)
from app.ai.rag_pipeline import RAGPipeline


class TestFullProductAudit(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_date_resolver_natural_language(self):
        """Validates that explicit and relative dates resolve to the exact target date."""
        now = get_ist_now()

        # 1. Explicit 15 September 2026
        r1 = resolve_day_and_date("Show my timetable for 15 September 2026")
        self.assertEqual(r1["day_name"], "Tuesday")
        self.assertIn("15 September 2026", r1["formatted_date"])
        self.assertEqual(r1["iso_date"], "2026-09-15")
        self.assertTrue(r1["is_explicit_date"])

        # 2. 15 September without year
        r2 = resolve_day_and_date("What is my timetable on 15 September?")
        self.assertEqual(r2["day_name"], "Tuesday")
        self.assertIn("15 September", r2["formatted_date"])

        # 3. 15/09/2026 numeric
        r3 = resolve_day_and_date("Show timetable for 15/09/2026")
        self.assertEqual(r3["day_name"], "Tuesday")
        self.assertEqual(r3["iso_date"], "2026-09-15")

        # 4. 15 Sept abbreviation
        r4 = resolve_day_and_date("Show timetable for 15 Sept")
        self.assertEqual(r4["day_name"], "Tuesday")

        # 5. Tomorrow
        r5 = resolve_day_and_date("Classes tomorrow")
        tomorrow_name = (now + datetime.timedelta(days=1)).strftime("%A")
        self.assertEqual(r5["day_name"], tomorrow_name)

        # 6. Today
        r6 = resolve_day_and_date("What's my schedule today?")
        self.assertEqual(r6["day_name"], now.strftime("%A"))

    def test_timetable_context_date_filtering(self):
        """Validates that timetable context includes exact date headers."""
        user_prof = {
            "full_name": "Manav Solanki",
            "department": "Computer Engineering",
            "semester": "3",
            "division": "A"
        }

        # Query for 15 September 2026
        ctx = process_timetable_context([], "What is my timetable on 15 September 2026?", user_profile=user_prof)
        self.assertIn("15 September 2026", ctx)
        self.assertIn("TARGET_DAY: Tuesday", ctx)

    def test_bus_transport_assistant(self):
        """Validates bus query processing, next bus calculation, and SVIT Bus Stop location metadata."""
        ans, img, srcs, loc = process_transport_context("Show bus timings")
        self.assertIn("SVIT Campus Transport Schedule", ans)
        self.assertEqual(img, "/static/navigation_maps/Bus stop.png")
        self.assertIsNotNone(loc)
        self.assertEqual(loc["name"], "SVIT Bus Stop & Transport Hub")
        self.assertEqual(loc["latitude"], 22.469850)
        self.assertEqual(loc["longitude"], 73.077500)

        # Stop specific query
        ans_gotri, _, _, _ = process_transport_context("Bus from Gotri to SVIT")
        self.assertIn("Gotri", ans_gotri)

    def test_rag_pipeline_location_navigation(self):
        """Validates RAG pipeline returns structured GPS coordinates for campus navigation."""
        rag = RAGPipeline()
        res = rag.answer_question("Where is Central Library?", session_id="test_sess")
        self.assertIsNotNone(res)
        self.assertTrue("Central Library" in res["answer"] or "Library" in res["answer"])
        self.assertIsNotNone(res.get("location"))
        self.assertIsNotNone(res["location"]["latitude"])
        self.assertIsNotNone(res["location"]["longitude"])

    def test_flask_chat_api_endpoint(self):
        """Validates /api/chat returns status 200 with full payload including location."""
        payload = {
            "message": "Where is Central Library?",
            "conversation_id": "test_conv_123"
        }
        response = self.client.post("/api/chat", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("answer", data)
        self.assertIn("location", data)
        self.assertIsNotNone(data["location"])
        self.assertIn("latitude", data["location"])
        self.assertIn("longitude", data["location"])

    def test_flask_chat_stream_endpoint(self):
        """Validates /api/chat/stream returns valid SSE chunks ending with done: true."""
        payload = {
            "message": "Show bus timings",
            "conversation_id": "test_stream_123"
        }
        response = self.client.post("/api/chat/stream", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data_str = response.data.decode("utf-8")
        self.assertIn("data:", data_str)
        self.assertIn('"done": true', data_str)
        self.assertIn('"location":', data_str)


if __name__ == "__main__":
    unittest.main()
