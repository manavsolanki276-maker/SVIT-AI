"""
tests/test_rooms_facilities_explore_campus.py
End-to-End Verification Test for Rooms & Facilities + Explore Campus Data Flow.
Validates that admin-provided data from rooms_facilities.csv, facilities.csv, and campus_info.csv
is correctly returned when students ask location-related questions.
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ['TESTING'] = 'True'
os.environ['VERCEL'] = '1'


class TestRoomsFacilitiesExploreCampus(unittest.TestCase):
    """Verify that navigation and RAG pipeline correctly resolve campus locations from admin data."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    # ----------------------------------------------------------------
    # 1. Verify that campus_info.csv and facilities.csv are loadable
    # ----------------------------------------------------------------
    def test_01_campus_info_csv_loadable(self):
        """Verify campus_info.csv loads and contains expected entries."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("campus_info.csv")
        self.assertIsNotNone(df, "campus_info.csv must be loadable")
        self.assertGreater(len(df), 0, "campus_info.csv must not be empty")
        # Check expected places exist
        place_names = df['place_name'].str.lower().tolist()
        self.assertTrue(any('main gate' in p for p in place_names), "Main Gate must exist in campus_info.csv")
        self.assertTrue(any('parking' in p for p in place_names), "Parking must exist in campus_info.csv")
        self.assertTrue(any('transport' in p for p in place_names), "Transport Office must exist in campus_info.csv")
        self.assertTrue(any('central library' in p for p in place_names), "Central Library must exist in campus_info.csv")
        self.assertTrue(any('medical' in p for p in place_names), "Medical Room must exist in campus_info.csv")

    def test_02_facilities_csv_loadable(self):
        """Verify facilities.csv loads and contains expected entries."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("facilities.csv")
        self.assertIsNotNone(df, "facilities.csv must be loadable")
        self.assertGreater(len(df), 0, "facilities.csv must not be empty")
        # Check expected facilities exist
        facility_names = df['facility_name'].str.lower().tolist()
        self.assertTrue(any('girls room' in f for f in facility_names), "Girls Room must exist in facilities.csv")
        self.assertTrue(any('reading room' in f for f in facility_names), "Reading Room must exist in facilities.csv")
        self.assertTrue(any('medical' in f for f in facility_names), "Medical & First Aid Room must exist in facilities.csv")
        self.assertTrue(any('placement cell' in f for f in facility_names), "Training & Placement Cell must exist in facilities.csv")
        self.assertTrue(any('library' in f for f in facility_names), "Central Library must exist in facilities.csv")

    def test_03_rooms_facilities_csv_loadable(self):
        """Verify rooms_facilities.csv loads and contains AR-101."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("rooms_facilities.csv")
        self.assertIsNotNone(df, "rooms_facilities.csv must be loadable")
        self.assertGreater(len(df), 0, "rooms_facilities.csv must not be empty")
        # Check AR-101 exists
        room_names = df['room_name'].str.lower().tolist()
        self.assertTrue(any('ar-101' in r for r in room_names), "AR-101 must exist in rooms_facilities.csv")

    # ----------------------------------------------------------------
    # 2. Verify navigation.py data-driven fallback resolves locations
    # ----------------------------------------------------------------
    def test_04_nav_girls_room(self):
        """Where is the Girls Room? -> Should resolve via navigation_config admin facilities."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Girls Room?")
        self.assertIsNotNone(result, "Girls Room must be resolved by navigation system")
        self.assertIn("girls", result["formatted_text"].lower(), "Response must mention 'girls'")

    def test_05_nav_reading_room(self):
        """Where is the Reading Room? -> Should resolve via navigation_config admin facilities."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Reading Room?")
        self.assertIsNotNone(result, "Reading Room must be resolved by navigation system")
        self.assertIn("reading", result["formatted_text"].lower(), "Response must mention 'reading'")

    def test_06_nav_medical_first_aid_room(self):
        """Where is the Medical & First Aid Room? -> Should resolve via facilities.csv fallback."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Medical & First Aid Room?")
        self.assertIsNotNone(result, "Medical & First Aid Room must be resolved by navigation system")
        text = result["formatted_text"].lower()
        self.assertTrue(
            "medical" in text or "first aid" in text,
            f"Response must mention medical/first aid. Got: {result['formatted_text']}"
        )

    def test_07_nav_training_placement_cell(self):
        """Where is the Training & Placement Cell? -> Should resolve via facilities.csv fallback."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Training & Placement Cell?")
        self.assertIsNotNone(result, "Training & Placement Cell must be resolved by navigation system")
        text = result["formatted_text"].lower()
        self.assertTrue(
            "placement" in text or "training" in text,
            f"Response must mention placement/training. Got: {result['formatted_text']}"
        )

    def test_08_nav_main_gate(self):
        """Where is the Main Gate? -> Should resolve via campus_info.csv or facilities.csv fallback."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Main Gate?")
        self.assertIsNotNone(result, "Main Gate must be resolved by navigation system")
        text = result["formatted_text"].lower()
        self.assertTrue(
            "main gate" in text or "gate" in text or "entrance" in text,
            f"Response must mention gate/entrance. Got: {result['formatted_text']}"
        )

    def test_09_nav_parking_area(self):
        """Where is the Parking Area? -> Should resolve via campus_info.csv fallback."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Parking Area?")
        self.assertIsNotNone(result, "Parking Area must be resolved by navigation system")
        text = result["formatted_text"].lower()
        self.assertTrue(
            "parking" in text,
            f"Response must mention parking. Got: {result['formatted_text']}"
        )

    def test_10_nav_transport_office(self):
        """Where is the Transport Office? -> Should resolve via campus_info.csv fallback."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Transport Office?")
        self.assertIsNotNone(result, "Transport Office must be resolved by navigation system")
        text = result["formatted_text"].lower()
        self.assertTrue(
            "transport" in text,
            f"Response must mention transport. Got: {result['formatted_text']}"
        )

    def test_11_nav_central_library(self):
        """Where is the Central Library? -> Should resolve via navigation_config admin facilities."""
        from app.ai.navigation import find_location
        result = find_location("Where is the Central Library?")
        self.assertIsNotNone(result, "Central Library must be resolved by navigation system")
        text = result["formatted_text"].lower()
        self.assertTrue(
            "library" in text or "central" in text,
            f"Response must mention library. Got: {result['formatted_text']}"
        )

    # ----------------------------------------------------------------
    # 3. Verify INTENT_CONFIG now includes campus_info and facilities
    # ----------------------------------------------------------------
    def test_12_intent_config_has_campus_info(self):
        """INTENT_CONFIG must include campus_info with campus_info.csv source."""
        from app.ai.config import INTENT_CONFIG
        self.assertIn("campus_info", INTENT_CONFIG, "campus_info must be in INTENT_CONFIG")
        sources = [s[0] for s in INTENT_CONFIG["campus_info"]["sources"]]
        self.assertIn("campus_info.csv", sources, "campus_info.csv must be in campus_info sources")

    def test_13_intent_config_has_facilities(self):
        """INTENT_CONFIG must include facilities with facilities.csv source."""
        from app.ai.config import INTENT_CONFIG
        self.assertIn("facilities", INTENT_CONFIG, "facilities must be in INTENT_CONFIG")
        sources = [s[0] for s in INTENT_CONFIG["facilities"]["sources"]]
        self.assertIn("facilities.csv", sources, "facilities.csv must be in facilities sources")

    # ----------------------------------------------------------------
    # 4. Verify route_query_sources finds campus_info/facilities
    # ----------------------------------------------------------------
    def test_14_route_query_medical(self):
        """route_query_sources should route medical queries to facilities.csv."""
        from app.ai.rag_pipeline import route_query_sources
        result = route_query_sources("Where is the Medical & First Aid Room?")
        source_names = [s[0] for s in result]
        self.assertIn("facilities.csv", source_names, "Medical query should route to facilities.csv")

    def test_15_route_query_placement_cell(self):
        """route_query_sources should route placement cell queries to facilities.csv."""
        from app.ai.rag_pipeline import route_query_sources
        result = route_query_sources("Where is the Training & Placement Cell?")
        source_names = [s[0] for s in result]
        self.assertIn("facilities.csv", source_names, "Placement cell query should route to facilities.csv")

    def test_16_route_query_main_gate(self):
        """route_query_sources should route gate queries to campus_info.csv."""
        from app.ai.rag_pipeline import route_query_sources
        result = route_query_sources("Where is the Main Gate?")
        source_names = [s[0] for s in result]
        self.assertIn("campus_info.csv", source_names, "Main Gate query should route to campus_info.csv")

    def test_17_route_query_parking(self):
        """route_query_sources should route parking queries to campus_info.csv."""
        from app.ai.rag_pipeline import route_query_sources
        result = route_query_sources("Where is the Parking Area?")
        source_names = [s[0] for s in result]
        self.assertIn("campus_info.csv", source_names, "Parking query should route to campus_info.csv")

    # ----------------------------------------------------------------
    # 5. Verify rooms_facilities.csv AR-101 exists and has department
    # ----------------------------------------------------------------
    def test_18_ar101_department_match(self):
        """AR-101 should be associated with AI & ML department in rooms_facilities.csv."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("rooms_facilities.csv")
        self.assertIsNotNone(df)
        ar101_rows = df[df['room_name'].str.lower() == 'ar-101']
        self.assertGreater(len(ar101_rows), 0, "AR-101 must exist in rooms_facilities.csv")
        dept = ar101_rows.iloc[0].get('department', '')
        self.assertIn("artificial intelligence", dept.lower(),
                       f"AR-101 department should be AI & ML, got: {dept}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
