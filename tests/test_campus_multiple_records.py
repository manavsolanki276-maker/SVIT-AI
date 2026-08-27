"""
tests/test_campus_multiple_records.py
Tests that campus facility and explore campus queries return MULTIPLE records
from the real admin datasets, not just a single Main Gate record.
Validates the full flow: context generation → formatter → display.
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ['TESTING'] = 'True'
os.environ['VERCEL'] = '1'


class TestCampusMultipleRecords(unittest.TestCase):
    """Verify that campus overview queries return multiple records, not just one."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    # ----------------------------------------------------------------
    # 1. Context generation returns multiple records
    # ----------------------------------------------------------------
    def test_01_what_facilities_returns_multiple_context_records(self):
        """'What facilities...' context must contain multiple place/facility names."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, _, sources = process_campus_navigation_context(
            "What facilities are available on the campus?"
        )
        self.assertTrue(ctx, "Context must not be empty")
        # Count Place Name and Facility Name occurrences
        import re
        place_names = re.findall(r'Place Name:\s*([^\n|]+)', ctx)
        facility_names = re.findall(r'Facility Name:\s*([^\n|]+)', ctx)
        total = len(place_names) + len(facility_names)
        self.assertGreater(total, 1,
            f"Must return multiple records (>1). Got {total} place names + facility names. "
            f"place_names={place_names[:5]}, facility_names={facility_names[:5]}")

    def test_02_explore_campus_returns_multiple_context_records(self):
        """'Explore the campus...' context must contain multiple records."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, _, sources = process_campus_navigation_context(
            "Explore the campus and show me the main buildings, rooms, facilities, and landmarks."
        )
        import re
        place_names = re.findall(r'Place Name:\s*([^\n|]+)', ctx)
        facility_names = re.findall(r'Facility Name:\s*([^\n|]+)', ctx)
        total = len(place_names) + len(facility_names)
        self.assertGreater(total, 1,
            f"Explore campus must return multiple records. Got {total}")

    def test_03_campus_facility_returns_multiple_context_records(self):
        """'Campus Facility' context must contain multiple records."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, _, sources = process_campus_navigation_context("Campus Facility")
        import re
        place_names = re.findall(r'Place Name:\s*([^\n|]+)', ctx)
        facility_names = re.findall(r'Facility Name:\s*([^\n|]+)', ctx)
        total = len(place_names) + len(facility_names)
        self.assertGreater(total, 1,
            f"Campus Facility must return multiple records. Got {total}")

    # ----------------------------------------------------------------
    # 2. Main Gate is NOT the only result
    # ----------------------------------------------------------------
    def test_04_main_gate_not_only_result_facilities(self):
        """'What facilities...' must NOT return only Main Gate."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, _, _ = process_campus_navigation_context("What facilities are available on the campus?")
        import re
        place_names = re.findall(r'Place Name:\s*([^\n|]+)', ctx)
        facility_names = re.findall(r'Facility Name:\s*([^\n|]+)', ctx)
        all_names = place_names + facility_names
        # Must have more than just Main Gate
        non_gate = [n for n in all_names if 'main gate' not in n.lower()]
        self.assertGreater(len(non_gate), 0,
            f"Main Gate must not be the only result. Got: {all_names}")

    def test_05_main_gate_not_only_result_explore(self):
        """'Explore the campus...' must NOT return only Main Gate."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, _, _ = process_campus_navigation_context(
            "Explore the campus and show me the main buildings, rooms, facilities, and landmarks."
        )
        import re
        place_names = re.findall(r'Place Name:\s*([^\n|]+)', ctx)
        facility_names = re.findall(r'Facility Name:\s*([^\n|]+)', ctx)
        all_names = place_names + facility_names
        non_gate = [n for n in all_names if 'main gate' not in n.lower()]
        self.assertGreater(len(non_gate), 0,
            f"Main Gate must not be the only result. Got: {all_names}")

    # ----------------------------------------------------------------
    # 3. Correct datasets are used
    # ----------------------------------------------------------------
    def test_06_uses_both_campus_info_and_facilities(self):
        """'What facilities...' must include records from BOTH campus_info.csv and facilities.csv."""
        from app.ai.data_processor import process_campus_navigation_context
        _, _, sources = process_campus_navigation_context("What facilities are available on the campus?")
        campus_sources = [s for s in sources if 'campus_info.csv' in s]
        fac_sources = [s for s in sources if 'facilities.csv' in s]
        self.assertGreater(len(campus_sources), 0,
            f"Must include campus_info.csv sources. Got: {sources[:5]}")
        self.assertGreater(len(fac_sources), 0,
            f"Must include facilities.csv sources. Got: {sources[:5]}")

    def test_07_no_handbook_in_context(self):
        """Context must NOT reference svit_handbook.pdf."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, _, _ = process_campus_navigation_context("What facilities are available on the campus?")
        self.assertNotIn("svit_handbook", ctx.lower(),
            "Context must NOT reference svit_handbook.pdf")

    # ----------------------------------------------------------------
    # 4. Formatter produces multiple display entries
    # ----------------------------------------------------------------
    def test_08_formatter_produces_multiple_entries(self):
        """The formatter must produce multiple card entries, not just one."""
        from app.ai.data_processor import process_campus_navigation_context
        from app.ai.rag_pipeline import RAGPipeline
        ctx, _, sources = process_campus_navigation_context("What facilities are available on the campus?")
        # Simulate the formatter
        pipeline = RAGPipeline.__new__(RAGPipeline)
        formatted = pipeline._format_context_as_direct_answer(
            "What facilities are available on the campus?",
            ctx,
            "facilities"
        )
        # Count location cards (📍 emoji entries)
        card_count = formatted.count('📍')
        self.assertGreater(card_count, 1,
            f"Formatter must produce multiple location cards (got {card_count}). "
            f"First 500 chars: {formatted[:500]}")

    def test_09_formatter_explore_campus_multiple_entries(self):
        """The formatter for 'Explore the campus...' must produce multiple cards."""
        from app.ai.data_processor import process_campus_navigation_context
        from app.ai.rag_pipeline import RAGPipeline
        ctx, _, sources = process_campus_navigation_context(
            "Explore the campus and show me the main buildings, rooms, facilities, and landmarks."
        )
        pipeline = RAGPipeline.__new__(RAGPipeline)
        formatted = pipeline._format_context_as_direct_answer(
            "Explore the campus and show me the main buildings, rooms, facilities, and landmarks.",
            ctx,
            "facilities"
        )
        card_count = formatted.count('📍')
        self.assertGreater(card_count, 1,
            f"Explore formatter must produce multiple cards (got {card_count})")

    def test_10_formatter_shows_facility_names(self):
        """Formatted output must show real facility names from the dataset."""
        from app.ai.data_processor import process_campus_navigation_context, get_cached_dataframe
        from app.ai.rag_pipeline import RAGPipeline
        ctx, _, _ = process_campus_navigation_context("What facilities are available on the campus?")
        pipeline = RAGPipeline.__new__(RAGPipeline)
        formatted = pipeline._format_context_as_direct_answer(
            "What facilities are available on the campus?",
            ctx,
            "facilities"
        )
        # Get real names from dataset
        df_fac = get_cached_dataframe("facilities.csv")
        self.assertIsNotNone(df_fac)
        facility_names = df_fac['facility_name'].tolist()
        matches = sum(1 for name in facility_names if name in formatted)
        self.assertGreaterEqual(matches, 3,
            f"At least 3 facility names must appear in formatted output. Found {matches}: {facility_names[:10]}")

    # ----------------------------------------------------------------
    # 5. Existing Rooms & Facilities tests still pass (no regression)
    # ----------------------------------------------------------------
    def test_11_ar101_still_resolves(self):
        """Where is AR-101? must still resolve."""
        from app.ai.navigation import find_location
        result = find_location("Where is AR-101?")
        self.assertIsNotNone(result, "AR-101 must still resolve")
        self.assertIn("ar-101", result["formatted_text"].lower())

    def test_12_girls_room_still_resolves(self):
        """Where is the Girls Room? must still resolve."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Girls Room?")
        self.assertIsNotNone(result, "Girls Room must still resolve")

    def test_13_all_9_location_queries_still_resolve(self):
        """All 9 original location queries must still produce results."""
        from app.ai.navigation import find_location
        queries = [
            ("Where is AR-101?", "ar-101"),
            ("Where is the Girls Room?", "girls"),
            ("Where is the Reading Room?", "reading"),
            ("Where is the Medical & First Aid Room?", "medical"),
            ("Where is the Training & Placement Cell?", "placement"),
            ("Where is the Main Gate?", "gate"),
            ("Where is the Parking Area?", "parking"),
            ("Where is the Transport Office?", "transport"),
            ("Where is the Central Library?", "library"),
        ]
        for query, keyword in queries:
            result = find_location(query)
            self.assertIsNotNone(result, f"Navigation must resolve: {query}")
            self.assertIn(keyword, result["formatted_text"].lower(),
                f"Response for '{query}' must contain '{keyword}'")

    # ----------------------------------------------------------------
    # 6. Sources count verification
    # ----------------------------------------------------------------
    def test_14_facilities_sources_include_many_records(self):
        """sources list for 'What facilities...' must have many entries."""
        from app.ai.data_processor import process_campus_navigation_context
        _, _, sources = process_campus_navigation_context("What facilities are available on the campus?")
        self.assertGreater(len(sources), 10,
            f"Must return >10 source entries. Got {len(sources)}")

    def test_15_explore_sources_include_many_records(self):
        """sources list for 'Explore the campus...' must have many entries."""
        from app.ai.data_processor import process_campus_navigation_context
        _, _, sources = process_campus_navigation_context(
            "Explore the campus and show me the main buildings, rooms, facilities, and landmarks."
        )
        self.assertGreater(len(sources), 10,
            f"Must return >10 source entries. Got {len(sources)}")


if __name__ == '__main__':
    unittest.main()
