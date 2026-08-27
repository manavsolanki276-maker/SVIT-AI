"""
tests/test_campus_facility_explore_queries.py
Tests that campus facility overview and campus exploration queries
return real admin data from campus_info.csv / facilities.csv,
NOT svit_handbook.pdf or general_faq.csv.
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ['TESTING'] = 'True'
os.environ['VERCEL'] = '1'


class TestCampusFacilityExploreQueries(unittest.TestCase):
    """Verify that campus facility and explore campus queries use correct admin data sources."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    # ----------------------------------------------------------------
    # 1. process_campus_navigation_context must catch these queries
    # ----------------------------------------------------------------
    def test_01_what_facilities_available(self):
        """'What facilities are available on the campus?' must return combined campus + facility data."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, map_url, sources = process_campus_navigation_context("What facilities are available on the campus?")
        self.assertTrue(ctx, "Context must not be empty for 'What facilities are available on the campus?'")
        self.assertGreater(len(sources), 0, "Must return at least one source")
        # Must contain real admin data — not handbook
        ctx_lower = ctx.lower()
        self.assertTrue(
            "campus_info.csv" in ctx or "facilities.csv" in ctx,
            f"Sources must include campus_info.csv or facilities.csv. Got: {sources}"
        )
        self.assertNotIn("svit_handbook", ctx_lower, "Must NOT reference svit_handbook.pdf")
        self.assertNotIn("general_faq", ctx_lower, "Must NOT reference general_faq.csv in context blocks")

    def test_02_explore_campus(self):
        """'Explore the campus and show me the main buildings, rooms, facilities, and landmarks.' must return campus data."""
        from app.ai.data_processor import process_campus_navigation_context
        query = "Explore the campus and show me the main buildings, rooms, facilities, and landmarks."
        ctx, map_url, sources = process_campus_navigation_context(query)
        self.assertTrue(ctx, "Context must not be empty for explore campus query")
        self.assertGreater(len(sources), 0, "Must return at least one source")
        ctx_lower = ctx.lower()
        self.assertTrue(
            "campus_info.csv" in ctx or "facilities.csv" in ctx,
            f"Sources must include campus_info.csv or facilities.csv. Got: {sources}"
        )
        self.assertNotIn("svit_handbook", ctx_lower, "Must NOT reference svit_handbook.pdf")

    def test_03_campus_facility_short(self):
        """'Campus Facility' must return campus/facility data."""
        from app.ai.data_processor import process_campus_navigation_context
        ctx, map_url, sources = process_campus_navigation_context("Campus Facility")
        self.assertTrue(ctx, "Context must not be empty for 'Campus Facility'")
        self.assertGreater(len(sources), 0, "Must return at least one source")
        ctx_lower = ctx.lower()
        self.assertTrue(
            "campus_info.csv" in ctx or "facilities.csv" in ctx,
            f"Sources must include campus_info.csv or facilities.csv. Got: {sources}"
        )
        self.assertNotIn("svit_handbook", ctx_lower, "Must NOT reference svit_handbook.pdf")

    # ----------------------------------------------------------------
    # 2. Content must contain real admin data, not generic answers
    # ----------------------------------------------------------------
    def test_04_facilities_query_contains_real_data(self):
        """'What facilities are available on the campus?' must include real facility names from the admin dataset."""
        from app.ai.data_processor import process_campus_navigation_context, get_cached_dataframe
        ctx, _, _ = process_campus_navigation_context("What facilities are available on the campus?")
        # Get real facility names from the CSV
        df_fac = get_cached_dataframe("facilities.csv")
        self.assertIsNotNone(df_fac, "facilities.csv must be loadable")
        # At least 3 real facility names must appear in the context
        facility_names = df_fac['facility_name'].str.lower().tolist()
        matches = sum(1 for name in facility_names if name in ctx.lower())
        self.assertGreaterEqual(matches, 3,
            f"At least 3 real facility names must appear in context. Found {matches}: {ctx[:300]}")

    def test_05_explore_campus_contains_real_buildings(self):
        """'Explore the campus...' must include real place names from campus_info.csv."""
        from app.ai.data_processor import process_campus_navigation_context, get_cached_dataframe
        ctx, _, _ = process_campus_navigation_context(
            "Explore the campus and show me the main buildings, rooms, facilities, and landmarks."
        )
        df_campus = get_cached_dataframe("campus_info.csv")
        self.assertIsNotNone(df_campus, "campus_info.csv must be loadable")
        place_names = df_campus['place_name'].str.lower().tolist()
        matches = sum(1 for name in place_names if name in ctx.lower())
        self.assertGreaterEqual(matches, 3,
            f"At least 3 real place names must appear in context. Found {matches}")

    # ----------------------------------------------------------------
    # 3. route_query_sources must route correctly for these queries
    # ----------------------------------------------------------------
    def test_06_route_facilities_overview(self):
        """route_query_sources must route 'What facilities are available?' to campus_info/facilities."""
        from app.ai.rag_pipeline import route_query_sources
        sources = route_query_sources("What facilities are available on the campus?")
        source_names = [s[0] for s in sources]
        self.assertIn("facilities.csv", source_names,
            f"facilities.csv must be in sources. Got: {source_names}")
        self.assertIn("campus_info.csv", source_names,
            f"campus_info.csv must be in sources. Got: {source_names}")

    def test_07_route_explore_campus(self):
        """route_query_sources must route 'Explore the campus...' to campus_info/facilities."""
        from app.ai.rag_pipeline import route_query_sources
        sources = route_query_sources("Explore the campus and show me the main buildings, rooms, facilities, and landmarks.")
        source_names = [s[0] for s in sources]
        self.assertIn("campus_info.csv", source_names,
            f"campus_info.csv must be in sources. Got: {source_names}")

    def test_08_route_campus_facility(self):
        """route_query_sources must route 'Campus Facility' to facilities."""
        from app.ai.rag_pipeline import route_query_sources
        sources = route_query_sources("Campus Facility")
        source_names = [s[0] for s in sources]
        self.assertIn("facilities.csv", source_names,
            f"facilities.csv must be in sources. Got: {source_names}")

    # ----------------------------------------------------------------
    # 4. Verify Rooms & Facilities (AR-101) still works (no regression)
    # ----------------------------------------------------------------
    def test_09_ar101_still_resolves(self):
        """Where is AR-101? must still resolve via navigation."""
        from app.ai.navigation import find_location
        result = find_location("Where is AR-101?")
        self.assertIsNotNone(result, "AR-101 must still resolve after campus facility fix")
        self.assertIn("ar-101", result["formatted_text"].lower(),
            "Response must mention AR-101")

    def test_10_girls_room_still_resolves(self):
        """Where is the Girls Room? must still resolve."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Girls Room?")
        self.assertIsNotNone(result, "Girls Room must still resolve after campus facility fix")

    # ----------------------------------------------------------------
    # 5. All 9 original location queries still pass
    # ----------------------------------------------------------------
    def test_11_all_location_queries_resolve(self):
        """All 9 original location queries must still produce non-empty navigation results."""
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
        for query, expected_keyword in queries:
            result = find_location(query)
            self.assertIsNotNone(result, f"Navigation must resolve: {query}")
            self.assertIn(expected_keyword, result["formatted_text"].lower(),
                f"Response for '{query}' must contain '{expected_keyword}'")


if __name__ == '__main__':
    unittest.main()
