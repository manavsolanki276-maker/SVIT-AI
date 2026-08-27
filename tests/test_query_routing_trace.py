"""
tests/test_query_routing_trace.py
Direct trace test: shows exact flow, source routing, and answer for all 9
Rooms & Facilities / Explore Campus queries against real admin data.
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ['TESTING'] = 'True'
os.environ['VERCEL'] = '1'


class TestQueryRoutingTrace(unittest.TestCase):
    """Trace every query through the full pipeline and verify source + answer."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    # ----------------------------------------------------------------
    # Helper: trace a query through navigation → route → retrieval
    # ----------------------------------------------------------------
    def _trace(self, query):
        """Returns (nav_result_or_None, route_sources, context_snippet, sources_list)."""
        from app.ai.navigation import find_location
        from app.ai.rag_pipeline import route_query_sources

        nav = find_location(query)
        if nav is not None:
            return {
                "resolved_by": "navigation.py",
                "nav_result": nav,
                "sources": ["navigation_config / navigation.py data fallback"],
                "answer_snippet": nav["formatted_text"][:200],
            }

        sources = route_query_sources(query)
        return {
            "resolved_by": "route_query_sources → vector search",
            "nav_result": None,
            "sources": sources,
            "answer_snippet": None,
        }

    def _get_expected_room(self, room_code):
        """Look up room_code in rooms_facilities.csv and return expected data."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("rooms_facilities.csv")
        if df is None:
            return None
        matched = df[df['room_name'].str.upper() == room_code.upper()]
        if matched.empty:
            return None
        row = matched.iloc[0]
        return {
            "room_name": str(row.get('room_name', '')).strip(),
            "department": str(row.get('department', '')).strip(),
            "status": str(row.get('status', '')).strip(),
        }

    def _get_expected_facility(self, name_fragment):
        """Look up facility by name fragment in facilities.csv."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("facilities.csv")
        if df is None:
            return None
        for _, row in df.iterrows():
            fname = str(row.get('facility_name', '')).strip().lower()
            if name_fragment.lower() in fname:
                return {
                    "facility_name": str(row.get('facility_name', '')).strip(),
                    "building": str(row.get('building', '')).strip(),
                    "floor": str(row.get('floor', '')).strip(),
                    "location": str(row.get('location', '')).strip(),
                }
        return None

    def _get_expected_campus(self, name_fragment):
        """Look up campus place by name fragment in campus_info.csv."""
        from app.ai.data_processor import get_cached_dataframe
        df = get_cached_dataframe("campus_info.csv")
        if df is None:
            return None
        for _, row in df.iterrows():
            pname = str(row.get('place_name', '')).strip().lower()
            if name_fragment.lower() in pname:
                return {
                    "place_name": str(row.get('place_name', '')).strip(),
                    "category": str(row.get('category', '')).strip(),
                    "zone": str(row.get('zone', '')).strip(),
                    "landmark": str(row.get('landmark', '')).strip(),
                }
        return None

    # ================================================================
    # QUERY 1: Where is AR-101?
    # ================================================================
    def test_01_ar101_route_and_source(self):
        """AR-101 must resolve via navigation room code pattern, returning AI & ML department."""
        trace = self._trace("Where is AR-101?")
        print(f"\n  [AR-101] resolved_by: {trace['resolved_by']}")
        print(f"  [AR-101] sources: {trace['sources']}")
        print(f"  [AR-101] answer: {trace['answer_snippet'][:150]}...")

        # Must resolve via navigation (new room code pattern)
        self.assertIsNotNone(trace["nav_result"],
                             "AR-101 must resolve via navigation room code pattern")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertIn("ar-101", text,
                       f"Response must mention AR-101. Got: {text[:150]}")
        self.assertIn("artificial intelligence", text,
                       f"Response must mention AI dept. Got: {text[:150]}")

        # Verify actual CSV data matches
        expected = self._get_expected_room("AR-101")
        self.assertIsNotNone(expected, "AR-101 must exist in rooms_facilities.csv")
        self.assertIn("artificial intelligence", expected["department"].lower(),
                       f"AR-101 department must be AI & ML, got: {expected['department']}")
        print(f"  [AR-101] ✅ CSV data: room={expected['room_name']}, dept={expected['department']}")

    def test_02_ar101_navigation_resolves(self):
        """AR-101 must now resolve through the new room code pattern in navigation.py."""
        from app.ai.navigation import find_location
        result = find_location("Where is AR-101?")
        self.assertIsNotNone(result, "AR-101 must resolve via navigation room code pattern")
        text = result["formatted_text"].lower()
        self.assertIn("ar-101", text, f"Response must mention AR-101. Got: {result['formatted_text'][:150]}")
        self.assertIn("artificial intelligence", text,
                       f"Response must mention AI dept. Got: {result['formatted_text'][:150]}")
        print(f"  [AR-101 nav] ✅ Resolved: {result['formatted_text'][:120]}...")

    # ================================================================
    # QUERY 2: Where is the Girls Room?
    # ================================================================
    def test_03_girls_room_route_and_source(self):
        """Girls Room must resolve via navigation (admin facilities)."""
        trace = self._trace("Where is the Girls Room?")
        print(f"\n  [Girls Room] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Girls Room must resolve via navigation")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertIn("girls", text)
        print(f"  [Girls Room] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_04_girls_room_csv_match(self):
        """Girls Room must exist in facilities.csv with correct data."""
        expected = self._get_expected_facility("girls room")
        self.assertIsNotNone(expected, "Girls Room must exist in facilities.csv")
        self.assertIn("girls room", expected["facility_name"].lower())
        print(f"  [Girls Room CSV] ✅ {expected['facility_name']} @ {expected['building']}")

    # ================================================================
    # QUERY 3: Where is the Reading Room?
    # ================================================================
    def test_05_reading_room_route_and_source(self):
        """Reading Room must resolve via navigation (admin facilities)."""
        trace = self._trace("Where is the Reading Room?")
        print(f"\n  [Reading Room] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Reading Room must resolve via navigation")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertIn("reading", text)
        print(f"  [Reading Room] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_06_reading_room_csv_match(self):
        """Reading Room must exist in facilities.csv."""
        expected = self._get_expected_facility("reading room")
        self.assertIsNotNone(expected, "Reading Room must exist in facilities.csv")
        print(f"  [Reading Room CSV] ✅ {expected['facility_name']} @ {expected['building']}")

    # ================================================================
    # QUERY 4: Where is the Medical & First Aid Room?
    # ================================================================
    def test_07_medical_room_route_and_source(self):
        """Medical & First Aid Room must resolve via navigation data fallback."""
        trace = self._trace("Where is the Medical & First Aid Room?")
        print(f"\n  [Medical Room] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Medical & First Aid Room must resolve via navigation fallback")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertTrue("medical" in text or "first aid" in text,
                        f"Response must mention medical/first aid. Got: {text[:150]}")
        print(f"  [Medical Room] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_08_medical_room_csv_match(self):
        """Medical & First Aid Room must exist in facilities.csv."""
        expected = self._get_expected_facility("medical")
        self.assertIsNotNone(expected, "Medical & First Aid Room must exist in facilities.csv")
        print(f"  [Medical CSV] ✅ {expected['facility_name']} @ {expected['building']}")

    # ================================================================
    # QUERY 5: Where is the Training & Placement Cell?
    # ================================================================
    def test_09_placement_cell_route_and_source(self):
        """Training & Placement Cell must resolve via navigation data fallback."""
        trace = self._trace("Where is the Training & Placement Cell?")
        print(f"\n  [Placement Cell] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Training & Placement Cell must resolve via navigation fallback")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertTrue("placement" in text or "training" in text,
                        f"Response must mention placement/training. Got: {text[:150]}")
        print(f"  [Placement Cell] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_10_placement_cell_csv_match(self):
        """Training & Placement Cell must exist in facilities.csv."""
        expected = self._get_expected_facility("placement cell")
        self.assertIsNotNone(expected, "Training & Placement Cell must exist in facilities.csv")
        print(f"  [Placement Cell CSV] ✅ {expected['facility_name']} @ {expected['building']}")

    # ================================================================
    # QUERY 6: Where is the Main Gate?
    # ================================================================
    def test_11_main_gate_route_and_source(self):
        """Main Gate must resolve via navigation data fallback (campus_info.csv)."""
        trace = self._trace("Where is the Main Gate?")
        print(f"\n  [Main Gate] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Main Gate must resolve via navigation fallback")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertTrue("main gate" in text or "gate" in text or "entrance" in text,
                        f"Response must mention gate/entrance. Got: {text[:150]}")
        print(f"  [Main Gate] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_12_main_gate_csv_match(self):
        """Main Gate must exist in campus_info.csv."""
        expected = self._get_expected_campus("main gate")
        self.assertIsNotNone(expected, "Main Gate must exist in campus_info.csv")
        self.assertIn("entrance", expected["category"].lower())
        print(f"  [Main Gate CSV] ✅ {expected['place_name']} @ {expected['zone']}")

    # ================================================================
    # QUERY 7: Where is the Parking Area?
    # ================================================================
    def test_13_parking_area_route_and_source(self):
        """Parking Area must resolve via navigation data fallback (campus_info.csv)."""
        trace = self._trace("Where is the Parking Area?")
        print(f"\n  [Parking] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Parking Area must resolve via navigation fallback")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertIn("parking", text,
                       f"Response must mention parking. Got: {text[:150]}")
        print(f"  [Parking] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_14_parking_csv_match(self):
        """Parking must exist in campus_info.csv."""
        expected = self._get_expected_campus("parking")
        self.assertIsNotNone(expected, "Parking must exist in campus_info.csv")
        print(f"  [Parking CSV] ✅ {expected['place_name']} @ {expected['zone']}")

    # ================================================================
    # QUERY 8: Where is the Transport Office?
    # ================================================================
    def test_15_transport_office_route_and_source(self):
        """Transport Office must resolve via navigation data fallback."""
        trace = self._trace("Where is the Transport Office?")
        print(f"\n  [Transport] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Transport Office must resolve via navigation fallback")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertIn("transport", text,
                       f"Response must mention transport. Got: {text[:150]}")
        print(f"  [Transport] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_16_transport_office_csv_match(self):
        """Transport Office must exist in campus_info.csv."""
        expected = self._get_expected_campus("transport")
        self.assertIsNotNone(expected, "Transport Office must exist in campus_info.csv")
        print(f"  [Transport CSV] ✅ {expected['place_name']} @ {expected['zone']}")

    # ================================================================
    # QUERY 9: Where is the Central Library?
    # ================================================================
    def test_17_central_library_route_and_source(self):
        """Central Library must resolve via navigation (admin facilities)."""
        trace = self._trace("Where is the Central Library?")
        print(f"\n  [Library] resolved_by: {trace['resolved_by']}")

        self.assertIsNotNone(trace["nav_result"],
                             "Central Library must resolve via navigation")
        text = trace["nav_result"]["formatted_text"].lower()
        self.assertTrue("library" in text or "central" in text,
                        f"Response must mention library. Got: {text[:150]}")
        print(f"  [Library] ✅ Answer: {trace['answer_snippet'][:120]}...")

    def test_18_central_library_csv_match(self):
        """Central Library must exist in campus_info.csv and facilities.csv."""
        expected_campus = self._get_expected_campus("central library")
        self.assertIsNotNone(expected_campus, "Central Library must exist in campus_info.csv")
        expected_fac = self._get_expected_facility("central library")
        self.assertIsNotNone(expected_fac, "Central Library must exist in facilities.csv")
        print(f"  [Library CSV] ✅ campus_info: {expected_campus['place_name']}, facilities: {expected_fac['facility_name']}")

    # ================================================================
    # Verify room code routing returns ONLY rooms_facilities.csv
    # ================================================================
    def test_19_route_ar101_returns_only_room_sources(self):
        """route_query_sources('Where is AR-101?') must return rooms_facilities.csv first."""
        from app.ai.rag_pipeline import route_query_sources
        sources = route_query_sources("Where is AR-101?")
        source_names = [s[0] for s in sources]
        self.assertEqual(source_names[0], "rooms_facilities.csv",
                         f"First source must be rooms_facilities.csv, got: {source_names}")
        self.assertNotIn("general_faq.csv", source_names[:1],
                          "general_faq.csv must NOT be the primary source for room codes")
        print(f"  [AR-101 routing] ✅ Sources: {source_names}")

    def test_20_route_medical_returns_facilities(self):
        """route_query_sources for Medical must return facilities.csv first."""
        from app.ai.rag_pipeline import route_query_sources
        sources = route_query_sources("Where is the Medical & First Aid Room?")
        source_names = [s[0] for s in sources]
        self.assertEqual(source_names[0], "facilities.csv",
                         f"First source must be facilities.csv, got: {source_names}")
        print(f"  [Medical routing] ✅ Sources: {source_names}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
