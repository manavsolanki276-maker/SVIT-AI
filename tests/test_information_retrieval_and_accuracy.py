"""
Unit and Integration Test Suite for SVIT-AI Library-First Information Retrieval & Accuracy Engine.

Validates:
1. Library-First & Admin Data as Source of Truth
2. Exact Entity Matching & Abbreviations (CE, IT, HOD, TPO, etc.)
3. Bus Routes & Timings (Bus 5, Anand, Nadiad, departure times)
4. Classroom & Laboratory resolution (A-204, CO-201, CE Lab, floor, building)
5. Canteen Menu & Pricing (Cold Coffee, Vadapav, unavailable dishes)
6. Library Books & Circulation (Timings, returns, book lookup, privacy guard)
7. Faculty, Notices & Events
8. Zero-Hallucination Fallback ("I couldn't find this information in the available SVIT records.")
9. Admin-to-Student Live Cache Invalidation & Synchronization
"""

import unittest
import os
import sys
import pandas as pd

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.data_processor import (
    normalize_entity_abbreviations,
    process_transport_context,
    process_canteen_context,
    process_library_context,
    process_classroom_lab_context,
    process_events_context,
    invalidate_ai_caches,
    get_cached_dataframe,
    _DATAFRAME_CACHE
)
from app.ai.rag_pipeline import get_rag_pipeline


class TestInformationRetrievalAndAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = get_rag_pipeline()
        # Mock student profile
        cls.student_profile = {
            "id": "210410107001",
            "enrollment_no": "210410107001",
            "full_name": "Manav Solanki",
            "program": "BE",
            "department": "Computer Engineering",
            "semester": "6",
            "division": "A",
            "batch": "B1"
        }

    # =========================================================================
    # 1. ABBREVIATION EXPANSION TESTS
    # =========================================================================
    def test_01_abbreviation_expansion_ce_hod(self):
        query = "Where is the CE HOD cabin?"
        expanded = normalize_entity_abbreviations(query)
        self.assertIn("Computer Engineering", expanded)
        self.assertIn("Head of Department", expanded)

    def test_02_abbreviation_expansion_tpo(self):
        query = "Contact TPO for placements"
        expanded = normalize_entity_abbreviations(query)
        self.assertIn("Training and Placement Officer", expanded)

    def test_03_abbreviation_expansion_it_and_ec(self):
        query = "Syllabus for IT and EC semester 4"
        expanded = normalize_entity_abbreviations(query)
        self.assertIn("Information Technology", expanded)
        self.assertIn("Electronics & Communication", expanded)

    # =========================================================================
    # 2. BUS ROUTE & TRANSPORT RETRIEVAL TESTS
    # =========================================================================
    def test_04_bus_number_5_matching(self):
        ctx, img, srcs, loc = process_transport_context("Bus 5 route and stops")
        self.assertIn("GJ06-BUS-105", ctx)
        self.assertIn("Route 5", ctx)
        self.assertIn("07:00 AM", ctx)
        self.assertIn("transport.csv", srcs[0])

    def test_05_bus_anand_route_retrieval(self):
        ctx, img, srcs, loc = process_transport_context("What bus goes to Anand?")
        self.assertIn("Anand Route 1", ctx)
        self.assertIn("GJ23-BUS-201", ctx)
        self.assertIn("Anand Bus Stand", ctx)

    def test_06_bus_nadiad_route_retrieval(self):
        ctx, img, srcs, loc = process_transport_context("Show bus timings for Nadiad")
        self.assertIn("Nadiad Route 1", ctx)
        self.assertIn("GJ07-BUS-301", ctx)
        self.assertIn("Nadiad Santram", ctx)

    def test_07_bus_departure_time_query(self):
        ctx, img, srcs, loc = process_transport_context("What is the departure time of bus 5?")
        self.assertIn("GJ06-BUS-105", ctx)
        self.assertIn("07:00 AM", ctx)

    def test_08_bus_unserved_city_zero_hallucination(self):
        ctx, img, srcs, loc = process_transport_context("Bus route to New York City")
        self.assertIn("STATUS: NOT_FOUND_IN_SVIT_RECORDS", ctx)
        self.assertIn("I couldn't find this information in the available SVIT records", ctx)

    # =========================================================================
    # 3. CLASSROOM & LABORATORY ACCURACY TESTS
    # =========================================================================
    def test_09_room_a204_matching(self):
        ctx, img, srcs, loc = process_classroom_lab_context("Where is room A-204?")
        self.assertIn("AR-204", ctx)
        self.assertIn("2nd Floor", ctx)
        self.assertIn("AI & ML / Aeronautical", ctx)

    def test_10_room_co201_matching(self):
        ctx, img, srcs, loc = process_classroom_lab_context("Find room CO-201")
        self.assertIn("CO-201", ctx)
        self.assertIn("Computer Engineering Block", ctx)
        self.assertIn("2nd Floor", ctx)

    def test_11_computer_lab_facilities_and_hours(self):
        ctx, img, srcs, loc = process_classroom_lab_context("Where is Computer Lab 1?")
        self.assertIn("Computer Engineering Lab 1", ctx)
        self.assertIn("09:00 AM - 05:00 PM", ctx)
        self.assertIn("workstations", ctx.lower())

    def test_12_nonexistent_room_zero_hallucination(self):
        ctx, img, srcs, loc = process_classroom_lab_context("Where is room Z-9999?")
        self.assertIn("STATUS: NOT_FOUND_IN_SVIT_RECORDS", ctx)
        self.assertIn("I couldn't find this information in the available SVIT records", ctx)

    # =========================================================================
    # 4. CANTEEN MENU & PRICING ACCURACY TESTS
    # =========================================================================
    def test_13_canteen_full_menu(self):
        ctx, srcs = process_canteen_context("What is on the canteen menu today?")
        self.assertIn("SVIT Campus Canteen Menu", ctx)
        self.assertIn("Operating Hours", ctx)
        self.assertIn("canteen.csv", srcs)

    def test_14_canteen_cold_coffee_price(self):
        ctx, srcs = process_canteen_context("What is the price of Cold Coffee?")
        self.assertIn("Cold Coffee", ctx)
        self.assertIn("₹70", ctx)

    def test_15_canteen_vadapav_price(self):
        ctx, srcs = process_canteen_context("How much does Vadapav cost?")
        self.assertIn("Vadapav", ctx)
        self.assertIn("₹25", ctx)

    def test_16_canteen_unavailable_item_zero_hallucination(self):
        ctx, srcs = process_canteen_context("Do you have Grilled Lobster in canteen?")
        self.assertIn("STATUS: NOT_FOUND_IN_SVIT_RECORDS", ctx)
        self.assertIn("I couldn't find this information in the available SVIT records", ctx)

    # =========================================================================
    # 5. LIBRARY & BOOKS ACCURACY TESTS
    # =========================================================================
    def test_17_library_timings_and_reading_room(self):
        ctx, srcs = process_library_context("What are the library timings and reading room hours?")
        self.assertIn("08:30 AM to 05:30 PM", ctx)
        self.assertIn("Silent Reading Room", ctx)
        self.assertIn("08:00 AM to 07:00 PM", ctx)

    def test_18_library_return_and_borrowing_rules(self):
        ctx, srcs = process_library_context("How do I return a library book?")
        self.assertIn("14 days", ctx)
        self.assertIn("₹2 per day", ctx)
        self.assertIn("3 books", ctx)

    def test_19_library_borrower_privacy_protection(self):
        ctx, srcs = process_library_context("Who has issued book B00001 right now?")
        self.assertIn("Data Privacy Policy", ctx)
        self.assertIn("confidentiality", ctx.lower())

    def test_20_library_book_accession_lookup(self):
        ctx, srcs = process_library_context("Where can I find book B00001?")
        self.assertIn("B00001", ctx)
        self.assertIn("Shelf Location", ctx)
        self.assertIn("Copies Available", ctx)

    def test_21_library_book_title_search(self):
        ctx, srcs = process_library_context("Is Data Structures book available in library?")
        self.assertIn("Data Structures", ctx)
        self.assertIn("Copies Available", ctx)
        self.assertIn("Shelf Location", ctx)

    def test_22_library_nonexistent_book_zero_hallucination(self):
        ctx, srcs = process_library_context("Where is book B99999?")
        self.assertIn("STATUS: NOT_FOUND_IN_SVIT_RECORDS", ctx)
        self.assertIn("I couldn't find this information in the available SVIT records", ctx)

    # =========================================================================
    # 6. EVENTS RETRIEVAL TESTS
    # =========================================================================
    def test_23_events_date_sorting(self):
        ctx = process_events_context("What are the upcoming events and workshops?")
        self.assertTrue("Event:" in ctx or "Upcoming" in ctx)
        self.assertIn("events.csv", ctx)

    # =========================================================================
    # 7. PIPELINE END-TO-END ZERO-HALLUCINATION GUARANTEE
    # =========================================================================
    def test_24_pipeline_answer_canteen_unserved_item(self):
        res = self.pipeline.answer_question(
            "What is the price of French Escargot in SVIT canteen?",
            session_id="test_zero_hallucination_canteen",
            user_profile=self.student_profile
        )
        self.assertEqual(res["answer"], "I couldn't find this information in the available SVIT records.")

    def test_25_pipeline_answer_nonexistent_room(self):
        res = self.pipeline.answer_question(
            "Where is classroom Q-888?",
            session_id="test_zero_hallucination_room",
            user_profile=self.student_profile
        )
        self.assertEqual(res["answer"], "I couldn't find this information in the available SVIT records.")

    def test_26_pipeline_answer_unserved_bus(self):
        res = self.pipeline.answer_question(
            "Show me the schedule of Bus 999 to Mumbai",
            session_id="test_zero_hallucination_bus",
            user_profile=self.student_profile
        )
        self.assertEqual(res["answer"], "I couldn't find this information in the available SVIT records.")

    # =========================================================================
    # 8. LIVE ADMIN SYNCHRONIZATION & CACHE INVALIDATION
    # =========================================================================
    # 8. LIVE ADMIN SYNCHRONIZATION & CACHE INVALIDATION
    # =========================================================================
    def test_27_live_admin_canteen_sync(self):
        from app.database.mongodb import get_collection
        test_dish = "Special Dragon Fruit Shake"
        
        # 1. Verify a new test dish is currently NOT in records
        ctx, _ = process_canteen_context(f"Price of {test_dish}")
        self.assertIn("STATUS: NOT_FOUND_IN_SVIT_RECORDS", ctx)

        # 2. Simulate Admin adding this item to the live MongoDB collection
        coll = get_collection("canteen")
        coll.insert_one({
            "item_id": "C999",
            "item_name": test_dish,
            "category": "Beverages",
            "price_inr": "55",
            "shop_name": "Juice Bar",
            "is_vegetarian": "Yes",
            "availability": "Available"
        })

        # 3. Invalidate caches for canteen
        invalidate_ai_caches("canteen")

        try:
            # 4. Student queries for the newly added dish
            ctx_new, _ = process_canteen_context(f"Price of {test_dish}")
            self.assertIn("Special Dragon Fruit Shake", ctx_new)
            self.assertIn("55", ctx_new)
        finally:
            # Clean up
            coll.delete_one({"item_id": "C999"})
            invalidate_ai_caches("canteen")

    def test_28_live_admin_library_book_sync(self):
        from app.database.mongodb import get_collection
        test_isbn = "BK_TEST_9999"
        
        # 1. Verify test book is not found
        ctx, _ = process_library_context(f"Book {test_isbn}")
        self.assertIn("STATUS: NOT_FOUND_IN_SVIT_RECORDS", ctx)

        # 2. Simulate Admin adding a new book to the live MongoDB collection
        coll = get_collection("library_books")
        coll.insert_one({
            "book_id": test_isbn,
            "title": "Quantum Computing Fundamentals",
            "author": "Dr. A. Scientist",
            "department": "Computer Engineering",
            "total_copies": 5,
            "available_copies": 4,
            "shelf_rack": "Rack Q-1",
            "edition": "1st Edition"
        })

        # 3. Invalidate caches
        invalidate_ai_caches("library")

        try:
            # 4. Student queries for the new book
            ctx_new, _ = process_library_context(f"Where is book {test_isbn}?")
            self.assertIn("Quantum Computing Fundamentals", ctx_new)
            self.assertIn("Rack Q-1", ctx_new)
        finally:
            # Clean up
            coll.delete_one({"book_id": test_isbn})
            invalidate_ai_caches("library")


if __name__ == '__main__':
    unittest.main()
