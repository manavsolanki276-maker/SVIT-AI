"""
tests/test_campus_facilities_explore_campus.py
Comprehensive verification for Campus Facilities and Explore Campus features.
Uses ONLY real admin-provided datasets (facilities.csv, campus_info.csv, rooms_facilities.csv).
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ['TESTING'] = 'True'
os.environ['VERCEL'] = '1'


class TestCampusFacilities(unittest.TestCase):
    """Test Campus Facilities: every facility resolves to the correct admin dataset."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def _find(self, query):
        from app.ai.navigation import find_location
        return find_location(query)

    def _route(self, query):
        from app.ai.rag_pipeline import route_query_sources
        return route_query_sources(query)

    def _load_fac(self):
        from app.ai.data_processor import get_cached_dataframe
        return get_cached_dataframe("facilities.csv")

    def _load_campus(self):
        from app.ai.data_processor import get_cached_dataframe
        return get_cached_dataframe("campus_info.csv")

    # ----------------------------------------------------------------
    # FAC-001: Girls Room
    # ----------------------------------------------------------------
    def test_fac_001_girls_room_resolves(self):
        r = self._find("Where is the Girls Room?")
        self.assertIsNotNone(r, "Girls Room must resolve via navigation")
        self.assertIn("girls", r["formatted_text"].lower())
        # Verify CSV data
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'girls room'].iloc[0]
        self.assertEqual(row['category'], 'Student Facility')
        print(f"  ✅ FAC-001 Girls Room → {row['category']} | {row['location']}")

    # ----------------------------------------------------------------
    # FAC-002: Reading Room
    # ----------------------------------------------------------------
    def test_fac_002_reading_room_resolves(self):
        r = self._find("Where is the Reading Room?")
        self.assertIsNotNone(r, "Reading Room must resolve via navigation")
        self.assertIn("reading", r["formatted_text"].lower())
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'reading room'].iloc[0]
        self.assertEqual(row['category'], 'Academic / Study Facility')
        print(f"  ✅ FAC-002 Reading Room → {row['category']} | {row['location']}")

    # ----------------------------------------------------------------
    # FAC-003: Central Library
    # ----------------------------------------------------------------
    def test_fac_003_central_library_resolves(self):
        r = self._find("Where is the Central Library?")
        self.assertIsNotNone(r, "Central Library must resolve via navigation")
        self.assertIn("library", r["formatted_text"].lower())
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'central library'].iloc[0]
        self.assertEqual(row['building'], 'Central Academic Block')
        self.assertEqual(row['floor'], 'Ground Floor')
        print(f"  ✅ FAC-003 Central Library → {row['building']} | {row['floor']}")

    # ----------------------------------------------------------------
    # FAC-004: College Auditorium
    # ----------------------------------------------------------------
    def test_fac_004_auditorium_resolves(self):
        r = self._find("Where is the College Auditorium?")
        self.assertIsNotNone(r, "College Auditorium must resolve via navigation fallback")
        self.assertIn("auditorium", r["formatted_text"].lower())
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'college auditorium'].iloc[0]
        self.assertEqual(row['building'], 'Main Auditorium Complex')
        self.assertEqual(row['capacity'], '600')
        print(f"  ✅ FAC-004 Auditorium → {row['building']} | Capacity: {row['capacity']}")

    # ----------------------------------------------------------------
    # FAC-005: Central Seminar Hall
    # ----------------------------------------------------------------
    def test_fac_005_seminar_hall_resolves(self):
        r = self._find("Where is the Central Seminar Hall?")
        self.assertIsNotNone(r, "Central Seminar Hall must resolve via navigation fallback")
        self.assertIn("seminar", r["formatted_text"].lower())
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'central seminar hall'].iloc[0]
        self.assertEqual(row['building'], 'Central Academic Block')
        self.assertEqual(row['floor'], 'First Floor')
        print(f"  ✅ FAC-005 Seminar Hall → {row['building']} | {row['floor']}")

    # ----------------------------------------------------------------
    # FAC-006: Medical & First Aid Room
    # ----------------------------------------------------------------
    def test_fac_006_medical_room_resolves(self):
        r = self._find("Where is the Medical & First Aid Room?")
        self.assertIsNotNone(r, "Medical & First Aid Room must resolve via navigation fallback")
        text = r["formatted_text"].lower()
        self.assertTrue("medical" in text or "first aid" in text)
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'medical & first aid room'].iloc[0]
        self.assertEqual(row['building'], 'Administration Block')
        self.assertEqual(row['floor'], 'Ground Floor')
        print(f"  ✅ FAC-006 Medical Room → {row['building']} | {row['floor']}")

    # ----------------------------------------------------------------
    # FAC-007: Administration Office & Accounts
    # ----------------------------------------------------------------
    def test_fac_007_admin_office_resolves(self):
        r = self._find("Where is the Administration Office?")
        self.assertIsNotNone(r, "Administration Office must resolve")
        text = r["formatted_text"].lower()
        self.assertTrue("admin" in text or "accounts" in text or "administration" in text)
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'administration office & accounts'].iloc[0]
        self.assertEqual(row['building'], 'Administration Block')
        print(f"  ✅ FAC-007 Admin Office → {row['building']} | {row['location']}")

    # ----------------------------------------------------------------
    # FAC-008: Training & Placement Cell
    # ----------------------------------------------------------------
    def test_fac_008_placement_cell_resolves(self):
        r = self._find("Where is the Training & Placement Cell?")
        self.assertIsNotNone(r, "Training & Placement Cell must resolve via navigation fallback")
        text = r["formatted_text"].lower()
        self.assertTrue("placement" in text or "training" in text)
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'training & placement cell'].iloc[0]
        self.assertEqual(row['building'], 'Administration Block')
        self.assertEqual(row['floor'], 'First Floor')
        print(f"  ✅ FAC-008 Placement Cell → {row['building']} | {row['floor']}")

    # ----------------------------------------------------------------
    # FAC-009: Sports Complex & Gymnasium
    # ----------------------------------------------------------------
    def test_fac_009_sports_complex_resolves(self):
        r = self._find("Where is the Sports Complex & Gymnasium?")
        self.assertIsNotNone(r, "Sports Complex must resolve via navigation")
        self.assertIn("sports", r["formatted_text"].lower())
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'sports complex & gymnasium'].iloc[0]
        self.assertEqual(row['building'], 'Sports Block')
        self.assertEqual(row['capacity'], '120')
        print(f"  ✅ FAC-009 Sports Complex → {row['building']} | Capacity: {row['capacity']}")

    # ----------------------------------------------------------------
    # FAC-010: Open Air Amphitheatre
    # ----------------------------------------------------------------
    def test_fac_010_amphitheatre_resolves(self):
        r = self._find("Where is the Open Air Amphitheatre?")
        self.assertIsNotNone(r, "Open Air Amphitheatre must resolve via navigation fallback")
        self.assertIn("amphitheatre", r["formatted_text"].lower())
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'open air amphitheatre'].iloc[0]
        self.assertEqual(row['building'], 'Central Garden')
        self.assertEqual(row['capacity'], '300')
        print(f"  ✅ FAC-010 Amphitheatre → {row['building']} | Capacity: {row['capacity']}")

    # ----------------------------------------------------------------
    # FAC-011: Central Food Court & Canteen
    # ----------------------------------------------------------------
    def test_fac_011_food_court_resolves(self):
        r = self._find("Where is the Central Food Court?")
        self.assertIsNotNone(r, "Central Food Court must resolve")
        # Resolves via navigation as Central Canteen (food court alias)
        text = r["formatted_text"].lower()
        self.assertTrue("canteen" in text or "food" in text,
                        f"Response must mention canteen/food. Got: {text[:100]}")
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'central food court & canteen'].iloc[0]
        self.assertEqual(row['building'], 'Food Court Block')
        self.assertEqual(row['capacity'], '200')
        print(f"  ✅ FAC-011 Food Court → {row['building']} | Capacity: {row['capacity']}")

    # ----------------------------------------------------------------
    # FAC-012: Campus Main Entrance Gate
    # ----------------------------------------------------------------
    def test_fac_012_main_gate_resolves(self):
        r = self._find("Where is the Campus Main Entrance Gate?")
        self.assertIsNotNone(r, "Campus Main Entrance Gate must resolve via navigation fallback")
        text = r["formatted_text"].lower()
        self.assertTrue("gate" in text or "entrance" in text or "main" in text)
        df = self._load_fac()
        row = df[df['facility_name'].str.lower() == 'campus main entrance gate'].iloc[0]
        self.assertEqual(row['building'], 'Main Entry Gate')
        print(f"  ✅ FAC-012 Main Gate → {row['building']} | {row['location']}")


class TestExploreCampus(unittest.TestCase):
    """Test Explore Campus: every campus place resolves to the correct admin dataset."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def _find(self, query):
        from app.ai.navigation import find_location
        return find_location(query)

    def _route(self, query):
        from app.ai.rag_pipeline import route_query_sources
        return route_query_sources(query)

    def _load_campus(self):
        from app.ai.data_processor import get_cached_dataframe
        return get_cached_dataframe("campus_info.csv")

    # ----------------------------------------------------------------
    # P001: Main Gate
    # ----------------------------------------------------------------
    def test_p001_main_gate_resolves(self):
        r = self._find("Where is the Main Gate?")
        self.assertIsNotNone(r, "Main Gate must resolve via navigation fallback")
        text = r["formatted_text"].lower()
        self.assertTrue("main gate" in text or "entrance" in text or "gate" in text)
        df = self._load_campus()
        row = df[df['place_name'] == 'Main Gate'].iloc[0]
        self.assertEqual(row['category'], 'Entrance')
        self.assertEqual(row['zone'], 'Campus Entry')
        print(f"  ✅ P001 Main Gate → {row['category']} | {row['zone']} | {row['landmark']}")

    # ----------------------------------------------------------------
    # P002: Administration Block
    # ----------------------------------------------------------------
    def test_p002_admin_block_resolves(self):
        r = self._find("Where is the Administration Block?")
        self.assertIsNotNone(r, "Administration Block must resolve")
        self.assertIn("admin", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Administration Block'].iloc[0]
        self.assertEqual(row['category'], 'Office')
        print(f"  ✅ P002 Admin Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P003: Computer Engineering Block
    # ----------------------------------------------------------------
    def test_p003_computer_block_resolves(self):
        r = self._find("Where is the Computer Engineering Block?")
        self.assertIsNotNone(r, "Computer Engineering Block must resolve")
        self.assertIn("computer", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Computer Engineering Block'].iloc[0]
        self.assertEqual(row['category'], 'Academic')
        self.assertEqual(row['zone'], 'North Wing')
        print(f"  ✅ P003 Computer Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P004: Information Technology Block
    # ----------------------------------------------------------------
    def test_p004_it_block_resolves(self):
        r = self._find("Where is the Information Technology Block?")
        self.assertIsNotNone(r, "IT Block must resolve")
        self.assertIn("information technology", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Information Technology Block'].iloc[0]
        self.assertEqual(row['zone'], 'North-East Wing')
        print(f"  ✅ P004 IT Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P005: Civil Engineering Block
    # ----------------------------------------------------------------
    def test_p005_civil_block_resolves(self):
        r = self._find("Where is the Civil Engineering Block?")
        self.assertIsNotNone(r, "Civil Engineering Block must resolve")
        self.assertIn("civil", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Civil Engineering Block'].iloc[0]
        self.assertEqual(row['zone'], 'North-West Wing')
        print(f"  ✅ P005 Civil Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P006: Mechanical Engineering Block
    # ----------------------------------------------------------------
    def test_p006_mechanical_block_resolves(self):
        r = self._find("Where is the Mechanical Engineering Block?")
        self.assertIsNotNone(r, "Mechanical Engineering Block must resolve")
        self.assertIn("mechanical", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Mechanical Engineering Block'].iloc[0]
        self.assertEqual(row['zone'], 'West Wing')
        print(f"  ✅ P006 Mechanical Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P007: Electrical Engineering Block
    # ----------------------------------------------------------------
    def test_p007_electrical_block_resolves(self):
        r = self._find("Where is the Electrical Engineering Block?")
        self.assertIsNotNone(r, "Electrical Engineering Block must resolve")
        self.assertIn("electrical", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Electrical Engineering Block'].iloc[0]
        self.assertEqual(row['zone'], 'South-West Wing')
        print(f"  ✅ P007 Electrical Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P008: Electronics & Communication Block
    # ----------------------------------------------------------------
    def test_p008_ec_block_resolves(self):
        r = self._find("Where is the Electronics & Communication Block?")
        self.assertIsNotNone(r, "EC Block must resolve")
        text = r["formatted_text"].lower()
        self.assertTrue("electronics" in text or "communication" in text or "e&c" in text)
        df = self._load_campus()
        row = df[df['place_name'] == 'Electronics & Communication Block'].iloc[0]
        self.assertEqual(row['zone'], 'East Wing')
        print(f"  ✅ P008 EC Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P009: AI & ML Department
    # ----------------------------------------------------------------
    def test_p009_ai_ml_resolves(self):
        r = self._find("Where is the AI & ML Department?")
        self.assertIsNotNone(r, "AI & ML Department must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'AI & ML Department'].iloc[0]
        self.assertEqual(row['zone'], 'Computer Block')
        self.assertEqual(row['landmark'], '2nd Floor')
        print(f"  ✅ P009 AI & ML → {row['category']} | {row['zone']} | {row['landmark']}")

    # ----------------------------------------------------------------
    # P010: Data Science Department
    # ----------------------------------------------------------------
    def test_p010_data_science_resolves(self):
        r = self._find("Where is the Data Science Department?")
        self.assertIsNotNone(r, "Data Science Department must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Data Science Department'].iloc[0]
        self.assertEqual(row['zone'], 'Computer Block')
        self.assertEqual(row['landmark'], '3rd Floor')
        print(f"  ✅ P010 Data Science → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P011: MCA Department
    # ----------------------------------------------------------------
    def test_p011_mca_resolves(self):
        r = self._find("Where is the MCA Department?")
        self.assertIsNotNone(r, "MCA Department must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'MCA Department'].iloc[0]
        self.assertEqual(row['zone'], 'LCMCA Block')
        print(f"  ✅ P011 MCA → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P012: BCA Department
    # ----------------------------------------------------------------
    def test_p012_bca_resolves(self):
        r = self._find("Where is the BCA Department?")
        self.assertIsNotNone(r, "BCA Department must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'BCA Department'].iloc[0]
        self.assertEqual(row['zone'], 'LCMCA Block')
        self.assertEqual(row['landmark'], 'Ground Floor')
        print(f"  ✅ P012 BCA → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P013: Central Library
    # ----------------------------------------------------------------
    def test_p013_library_resolves(self):
        r = self._find("Where is the Central Library?")
        self.assertIsNotNone(r, "Central Library must resolve via navigation")
        df = self._load_campus()
        row = df[df['place_name'] == 'Central Library'].iloc[0]
        self.assertEqual(row['category'], 'Library')
        self.assertEqual(row['zone'], 'Central Campus')
        print(f"  ✅ P013 Central Library → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P014: Seminar Hall
    # ----------------------------------------------------------------
    def test_p014_seminar_hall_resolves(self):
        r = self._find("Where is the Seminar Hall?")
        self.assertIsNotNone(r, "Seminar Hall must resolve via navigation fallback")
        df = self._load_campus()
        row = df[df['place_name'] == 'Seminar Hall'].iloc[0]
        self.assertEqual(row['category'], 'Facility')
        self.assertEqual(row['zone'], 'Central Campus')
        print(f"  ✅ P014 Seminar Hall → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P015: Auditorium
    # ----------------------------------------------------------------
    def test_p015_auditorium_resolves(self):
        r = self._find("Where is the Auditorium?")
        self.assertIsNotNone(r, "Auditorium must resolve via navigation fallback")
        df = self._load_campus()
        row = df[df['place_name'] == 'Auditorium'].iloc[0]
        self.assertEqual(row['category'], 'Facility')
        self.assertEqual(row['zone'], 'Central Campus')
        print(f"  ✅ P015 Auditorium → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P016: Innovation & AI Lab
    # ----------------------------------------------------------------
    def test_p016_innovation_lab_resolves(self):
        r = self._find("Where is the Innovation & AI Lab?")
        self.assertIsNotNone(r, "Innovation & AI Lab must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Innovation & AI Lab'].iloc[0]
        self.assertEqual(row['category'], 'Laboratory')
        self.assertEqual(row['zone'], 'Computer Block')
        print(f"  ✅ P016 Innovation Lab → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P017: Computer Lab
    # ----------------------------------------------------------------
    def test_p017_computer_lab_resolves(self):
        r = self._find("Where is the Computer Lab?")
        self.assertIsNotNone(r, "Computer Lab must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Computer Lab'].iloc[0]
        self.assertEqual(row['category'], 'Laboratory')
        self.assertEqual(row['landmark'], 'All Floors')
        print(f"  ✅ P017 Computer Lab → {row['category']} | {row['landmark']}")

    # ----------------------------------------------------------------
    # P018: Civil Lab
    # ----------------------------------------------------------------
    def test_p018_civil_lab_resolves(self):
        r = self._find("Where is the Civil Lab?")
        self.assertIsNotNone(r, "Civil Lab must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Civil Lab'].iloc[0]
        self.assertEqual(row['category'], 'Laboratory')
        self.assertEqual(row['zone'], 'Civil Block')
        print(f"  ✅ P018 Civil Lab → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P019: Mechanical Workshop
    # ----------------------------------------------------------------
    def test_p019_mechanical_workshop_resolves(self):
        r = self._find("Where is the Mechanical Workshop?")
        self.assertIsNotNone(r, "Mechanical Workshop must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Mechanical Workshop'].iloc[0]
        self.assertEqual(row['category'], 'Laboratory')
        self.assertEqual(row['zone'], 'Mechanical Block')
        print(f"  ✅ P019 Mech Workshop → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P020: Electrical Lab
    # ----------------------------------------------------------------
    def test_p020_electrical_lab_resolves(self):
        r = self._find("Where is the Electrical Lab?")
        self.assertIsNotNone(r, "Electrical Lab must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Electrical Lab'].iloc[0]
        self.assertEqual(row['category'], 'Laboratory')
        self.assertEqual(row['zone'], 'Electrical Block')
        print(f"  ✅ P020 Electrical Lab → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P021: EC Lab
    # ----------------------------------------------------------------
    def test_p021_ec_lab_resolves(self):
        r = self._find("Where is the EC Lab?")
        self.assertIsNotNone(r, "EC Lab must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'EC Lab'].iloc[0]
        self.assertEqual(row['category'], 'Laboratory')
        self.assertEqual(row['zone'], 'EC Block')
        print(f"  ✅ P021 EC Lab → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P022: Training & Placement Cell
    # ----------------------------------------------------------------
    def test_p022_placement_cell_resolves(self):
        r = self._find("Where is the Training & Placement Cell?")
        self.assertIsNotNone(r, "Training & Placement Cell must resolve via navigation fallback")
        text = r["formatted_text"].lower()
        self.assertTrue("placement" in text or "training" in text)
        df = self._load_campus()
        row = df[df['place_name'] == 'Training & Placement Cell'].iloc[0]
        self.assertEqual(row['category'], 'Office')
        self.assertEqual(row['zone'], 'Administration Block')
        print(f"  ✅ P022 Placement Cell → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P023: Sports Complex
    # ----------------------------------------------------------------
    def test_p023_sports_complex_resolves(self):
        r = self._find("Where is the Sports Complex?")
        self.assertIsNotNone(r, "Sports Complex must resolve")
        self.assertIn("sports", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Sports Complex'].iloc[0]
        self.assertEqual(row['category'], 'Sports')
        self.assertEqual(row['zone'], 'South Campus')
        print(f"  ✅ P023 Sports Complex → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P024: Cricket Ground
    # ----------------------------------------------------------------
    def test_p024_cricket_ground_resolves(self):
        r = self._find("Where is the Cricket Ground?")
        self.assertIsNotNone(r, "Cricket Ground must resolve via navigation")
        # Resolves via navigation as Sports Complex (cricket ground alias)
        text = r["formatted_text"].lower()
        self.assertTrue("sports" in text or "cricket" in text or "pavilion" in text,
                        f"Response must mention sports/cricket. Got: {text[:100]}")
        df = self._load_campus()
        row = df[df['place_name'] == 'Cricket Ground'].iloc[0]
        self.assertEqual(row['category'], 'Sports')
        print(f"  ✅ P024 Cricket Ground → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P025: Bus Parking
    # ----------------------------------------------------------------
    def test_p025_bus_parking_resolves(self):
        r = self._find("Where is the Bus Parking?")
        self.assertIsNotNone(r, "Bus Parking must resolve")
        self.assertIn("bus", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Bus Parking'].iloc[0]
        self.assertEqual(row['category'], 'Transport')
        self.assertEqual(row['zone'], 'North Entrance')
        print(f"  ✅ P025 Bus Parking → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P026: Transport Office
    # ----------------------------------------------------------------
    def test_p026_transport_office_resolves(self):
        r = self._find("Where is the Transport Office?")
        self.assertIsNotNone(r, "Transport Office must resolve via navigation fallback")
        self.assertIn("transport", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Transport Office'].iloc[0]
        self.assertEqual(row['category'], 'Transport')
        self.assertEqual(row['zone'], 'Near Bus Parking')
        print(f"  ✅ P026 Transport Office → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P027: Central Canteen
    # ----------------------------------------------------------------
    def test_p027_central_canteen_resolves(self):
        r = self._find("Where is the Central Canteen?")
        self.assertIsNotNone(r, "Central Canteen must resolve")
        self.assertIn("canteen", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Central Canteen'].iloc[0]
        self.assertEqual(row['category'], 'Food')
        self.assertEqual(row['zone'], 'Central Campus')
        print(f"  ✅ P027 Central Canteen → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P028: Diploma Canteen
    # ----------------------------------------------------------------
    def test_p028_diploma_canteen_resolves(self):
        r = self._find("Where is the Diploma Canteen?")
        self.assertIsNotNone(r, "Diploma Canteen must resolve via navigation fallback")
        df = self._load_campus()
        row = df[df['place_name'] == 'Diploma Canteen'].iloc[0]
        self.assertEqual(row['category'], 'Food')
        self.assertEqual(row['zone'], 'Last Campus')
        print(f"  ✅ P028 Diploma Canteen → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P029: Architecture Block
    # ----------------------------------------------------------------
    def test_p029_architecture_block_resolves(self):
        r = self._find("Where is the Architecture Block?")
        self.assertIsNotNone(r, "Architecture Block must resolve")
        self.assertIn("architecture", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Architecture Block'].iloc[0]
        self.assertEqual(row['category'], 'Academic')
        self.assertEqual(row['zone'], 'South-East Wing')
        print(f"  ✅ P029 Architecture Block → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P030: Diploma Computer Engineering
    # ----------------------------------------------------------------
    def test_p030_diploma_ce_resolves(self):
        r = self._find("Where is the Diploma Computer Engineering?")
        self.assertIsNotNone(r, "Diploma CE must resolve")
        df = self._load_campus()
        row = df[df['place_name'] == 'Diploma Computer Engineering'].iloc[0]
        self.assertEqual(row['category'], 'Academic')
        self.assertEqual(row['zone'], 'Diploma Block A')
        print(f"  ✅ P030 Diploma CE → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P037: Medical Room
    # ----------------------------------------------------------------
    def test_p037_medical_room_resolves(self):
        r = self._find("Where is the Medical Room?")
        self.assertIsNotNone(r, "Medical Room must resolve via navigation fallback")
        text = r["formatted_text"].lower()
        self.assertTrue("medical" in text or "first aid" in text)
        df = self._load_campus()
        row = df[df['place_name'] == 'Medical Room'].iloc[0]
        self.assertEqual(row['category'], 'Facility')
        self.assertEqual(row['zone'], 'Central Campus')
        print(f"  ✅ P037 Medical Room → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P038: Hostel
    # ----------------------------------------------------------------
    def test_p038_hostel_resolves(self):
        r = self._find("Where is the Hostel?")
        self.assertIsNotNone(r, "Hostel must resolve via navigation fallback")
        df = self._load_campus()
        row = df[df['place_name'] == 'Hostel'].iloc[0]
        self.assertEqual(row['category'], 'Residence')
        self.assertEqual(row['zone'], 'East Campus')
        print(f"  ✅ P038 Hostel → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P039: Parking Area
    # ----------------------------------------------------------------
    def test_p039_parking_area_resolves(self):
        r = self._find("Where is the Parking Area?")
        self.assertIsNotNone(r, "Parking Area must resolve via navigation fallback")
        self.assertIn("parking", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Parking Area'].iloc[0]
        self.assertEqual(row['category'], 'Facility')
        self.assertEqual(row['zone'], 'Main Gate')
        print(f"  ✅ P039 Parking Area → {row['category']} | {row['zone']}")

    # ----------------------------------------------------------------
    # P040: Open Amphitheatre
    # ----------------------------------------------------------------
    def test_p040_open_amphitheatre_resolves(self):
        r = self._find("Where is the Open Amphitheatre?")
        self.assertIsNotNone(r, "Open Amphitheatre must resolve via navigation fallback")
        self.assertIn("amphitheatre", r["formatted_text"].lower())
        df = self._load_campus()
        row = df[df['place_name'] == 'Open Amphitheatre'].iloc[0]
        self.assertEqual(row['category'], 'Facility')
        self.assertEqual(row['zone'], 'Central Garden')
        print(f"  ✅ P040 Open Amphitheatre → {row['category']} | {row['zone']}")


class TestRoomCodeRouting(unittest.TestCase):
    """Test room code routing: verify rooms_facilities.csv is the primary source."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def _find(self, query):
        from app.ai.navigation import find_location
        return find_location(query)

    def _route(self, query):
        from app.ai.rag_pipeline import route_query_sources
        return route_query_sources(query)

    def _load_rooms(self):
        from app.ai.data_processor import get_cached_dataframe
        return get_cached_dataframe("rooms_facilities.csv")

    # ----------------------------------------------------------------
    # AR-101 (AI & ML)
    # ----------------------------------------------------------------
    def test_ar101_resolves_and_routes(self):
        r = self._find("Where is AR-101?")
        self.assertIsNotNone(r, "AR-101 must resolve via room code pattern")
        self.assertIn("ar-101", r["formatted_text"].lower())
        self.assertIn("artificial intelligence", r["formatted_text"].lower())
        sources = self._route("Where is AR-101?")
        self.assertEqual(sources[0][0], "rooms_facilities.csv")
        df = self._load_rooms()
        row = df[df['room_name'] == 'AR-101'].iloc[0]
        self.assertEqual(row['department'], 'Artificial Intelligence & Machine Learning')
        self.assertEqual(row['status'], 'Active')
        print(f"  ✅ AR-101 → {row['department']} | Status: {row['status']}")

    # ----------------------------------------------------------------
    # CO-101 (Computer Engineering)
    # ----------------------------------------------------------------
    def test_co101_resolves_and_routes(self):
        r = self._find("Where is CO-101?")
        self.assertIsNotNone(r, "CO-101 must resolve via room code pattern")
        self.assertIn("co-101", r["formatted_text"].lower())
        sources = self._route("Where is CO-101?")
        self.assertEqual(sources[0][0], "rooms_facilities.csv")
        df = self._load_rooms()
        row = df[df['room_name'] == 'CO-101'].iloc[0]
        self.assertIn("computer", row['department'].lower())
        print(f"  ✅ CO-101 → {row['department']} | Status: {row['status']}")

    # ----------------------------------------------------------------
    # CI-101 (Civil Engineering)
    # ----------------------------------------------------------------
    def test_ci101_resolves_and_routes(self):
        r = self._find("Where is CI-101?")
        self.assertIsNotNone(r, "CI-101 must resolve via room code pattern")
        self.assertIn("ci-101", r["formatted_text"].lower())
        self.assertIn("civil", r["formatted_text"].lower())
        sources = self._route("Where is CI-101?")
        self.assertEqual(sources[0][0], "rooms_facilities.csv")
        df = self._load_rooms()
        row = df[df['room_name'] == 'CI-101'].iloc[0]
        self.assertEqual(row['department'], 'Civil Engineering')
        print(f"  ✅ CI-101 → {row['department']} | Status: {row['status']}")

    # ----------------------------------------------------------------
    # AU-101 (Automobile Engineering)
    # ----------------------------------------------------------------
    def test_au101_resolves_and_routes(self):
        r = self._find("Where is AU-101?")
        self.assertIsNotNone(r, "AU-101 must resolve via room code pattern")
        self.assertIn("au-101", r["formatted_text"].lower())
        self.assertIn("automobile", r["formatted_text"].lower())
        sources = self._route("Where is AU-101?")
        self.assertEqual(sources[0][0], "rooms_facilities.csv")
        df = self._load_rooms()
        row = df[df['room_name'] == 'AU-101'].iloc[0]
        self.assertEqual(row['department'], 'Automobile Engineering')
        print(f"  ✅ AU-101 → {row['department']} | Status: {row['status']}")

    # ----------------------------------------------------------------
    # ME-101 (Mechanical Engineering) — verify it exists
    # ----------------------------------------------------------------
    def test_me101_in_dataset(self):
        df = self._load_rooms()
        # Check if ME rooms exist
        me_rooms = df[df['room_name'].str.startswith('ME-')]
        self.assertGreater(len(me_rooms), 0, "ME- prefix rooms must exist in dataset")
        first_me = me_rooms.iloc[0]
        self.assertEqual(first_me['department'], 'Mechanical Engineering')
        print(f"  ✅ ME rooms exist: {len(me_rooms)} rooms | First: {first_me['room_name']}")

    # ----------------------------------------------------------------
    # Verify no general_faq.csv in room code routing
    # ----------------------------------------------------------------
    def test_room_code_never_returns_general_faq_as_primary(self):
        """Room code queries must NEVER return general_faq.csv as primary source."""
        for code in ['AR-101', 'CO-101', 'CI-101', 'AU-101']:
            sources = self._route(f"Where is {code}?")
            self.assertEqual(sources[0][0], "rooms_facilities.csv",
                             f"{code}: primary source must be rooms_facilities.csv, got {sources[0][0]}")
        print(f"  ✅ All room codes route to rooms_facilities.csv as primary source")


class TestSourceIsolation(unittest.TestCase):
    """Verify that general_faq.csv is NEVER the primary source for facility/campus queries."""

    @classmethod
    def setUpClass(cls):
        from app import create_app
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def _route(self, query):
        from app.ai.rag_pipeline import route_query_sources
        return route_query_sources(query)

    def _find(self, query):
        from app.ai.navigation import find_location
        return find_location(query)

    def test_facility_queries_never_primary_general_faq(self):
        """All facility queries must resolve via navigation, not general_faq."""
        queries = [
            "Where is the Girls Room?",
            "Where is the Reading Room?",
            "Where is the Central Library?",
            "Where is the Medical & First Aid Room?",
            "Where is the Training & Placement Cell?",
            "Where is the Sports Complex & Gymnasium?",
        ]
        for q in queries:
            r = self._find(q)
            self.assertIsNotNone(r, f"'{q}' must resolve via navigation, not fall through to general_faq")
        print(f"  ✅ All {len(queries)} facility queries resolve via navigation (not general_faq)")

    def test_campus_queries_never_primary_general_faq(self):
        """All campus location queries must resolve via navigation, not general_faq."""
        queries = [
            "Where is the Main Gate?",
            "Where is the Parking Area?",
            "Where is the Transport Office?",
            "Where is the Central Canteen?",
            "Where is the Cricket Ground?",
            "Where is the Bus Parking?",
            "Where is the Architecture Block?",
            "Where is the Hostel?",
        ]
        for q in queries:
            r = self._find(q)
            self.assertIsNotNone(r, f"'{q}' must resolve via navigation, not fall through to general_faq")
        print(f"  ✅ All {len(queries)} campus queries resolve via navigation (not general_faq)")

    def test_room_codes_never_primary_general_faq(self):
        """All room code queries must route to rooms_facilities.csv, not general_faq."""
        queries = ["AR-101", "CO-101", "CI-101", "AU-101"]
        for code in queries:
            sources = self._route(f"Where is {code}?")
            self.assertEqual(sources[0][0], "rooms_facilities.csv",
                             f"{code} must route to rooms_facilities.csv, got {sources[0][0]}")
        print(f"  ✅ All {len(queries)} room codes route to rooms_facilities.csv")


if __name__ == '__main__':
    unittest.main(verbosity=2)
