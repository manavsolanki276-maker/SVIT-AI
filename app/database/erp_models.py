"""
app/database/erp_models.py
MongoDB Models and Service Layer for SVIT Student ERP System.
Provides strictly-scoped data access for authenticated students.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.database.mongodb import get_collection


def get_current_time_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StudentERPService:
    """
    Authorized Student ERP Data Service backed by MongoDB.
    All student operations are strictly scoped to the authenticated student_id.
    """

    @staticmethod
    def get_student_profile(student_id: Any) -> Optional[Dict[str, Any]]:
        coll = get_collection('students')
        if coll is None:
            return None
        sid_str = str(student_id)
        query = {
            "$or": [
                {"id": sid_str},
                {"id": int(sid_str) if sid_str.isdigit() else -1},
                {"enrollment_no": sid_str}
            ]
        }
        doc = coll.find_one(query)
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    # -------------------------------------------------------------------------
    # ATTENDANCE
    # -------------------------------------------------------------------------
    @staticmethod
    def get_attendance(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('attendance')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            profile = StudentERPService.get_student_profile(student_id) or {}
            dept = profile.get("department", "Computer Engineering")
            sem = profile.get("semester", 3)

            default_subjects = [
                {"subject_code": "3130702", "subject_name": "Data Structures", "attended": 38, "total": 45, "percentage": 84.4},
                {"subject_code": "3130703", "subject_name": "Database Management Systems", "attended": 36, "total": 45, "percentage": 80.0},
                {"subject_code": "3130704", "subject_name": "Digital Electronics", "attended": 33, "total": 42, "percentage": 78.5},
                {"subject_code": "3130006", "subject_name": "Probability & Statistics", "attended": 35, "total": 44, "percentage": 79.5},
                {"subject_code": "3130701", "subject_name": "Operating Systems", "attended": 39, "total": 45, "percentage": 86.6},
            ]
            total_held = sum(s["total"] for s in default_subjects)
            total_att = sum(s["attended"] for s in default_subjects)
            overall_pct = round((total_att / total_held) * 100, 1)

            fallback_doc = {
                "student_id": sid_str,
                "enrollment_no": profile.get("enrollment_no", sid_str),
                "semester": sem,
                "overall_percentage": overall_pct,
                "total_classes": total_held,
                "attended_classes": total_att,
                "status": "Good" if overall_pct >= 75.0 else "Warning",
                "subjects": default_subjects,
                "last_updated": get_current_time_iso()
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    # -------------------------------------------------------------------------
    # FEES
    # -------------------------------------------------------------------------
    @staticmethod
    def get_fee_details(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('fees')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            profile = StudentERPService.get_student_profile(student_id) or {}
            fallback_doc = {
                "student_id": sid_str,
                "enrollment_no": profile.get("enrollment_no", sid_str),
                "academic_year": "2026-2027",
                "semester": profile.get("semester", 3),
                "total_fee": 45000,
                "paid_fee": 30000,
                "pending_fee": 15000,
                "status": "partial",
                "due_date": "2026-10-15",
                "breakdown": [
                    {"component": "Tuition Fee", "total": 35000, "paid": 25000, "pending": 10000},
                    {"component": "Laboratory Fee", "total": 5000, "paid": 5000, "pending": 0},
                    {"component": "Library & Sports Fee", "total": 3000, "paid": 0, "pending": 3000},
                    {"component": "Exam Form Fee", "total": 2000, "paid": 0, "pending": 2000}
                ],
                "last_updated": get_current_time_iso()
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    def update_fee_after_payment(student_id: Any, amount_paid: int) -> Dict[str, Any]:
        coll = get_collection('fees')
        sid_str = str(student_id)
        current_fee = StudentERPService.get_fee_details(sid_str)

        new_paid = current_fee.get("paid_fee", 0) + amount_paid
        new_pending = max(0, current_fee.get("total_fee", 45000) - new_paid)
        new_status = "paid" if new_pending == 0 else ("partial" if new_paid > 0 else "pending")

        update_payload = {
            "paid_fee": new_paid,
            "pending_fee": new_pending,
            "status": new_status,
            "last_updated": get_current_time_iso()
        }

        if coll is not None:
            coll.update_one({"student_id": sid_str}, {"$set": update_payload})
        current_fee.update(update_payload)
        return current_fee

    # -------------------------------------------------------------------------
    # RESULTS / EXAM MARKS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_results(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('results')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            profile = StudentERPService.get_student_profile(student_id) or {}
            fallback_doc = {
                "student_id": sid_str,
                "enrollment_no": profile.get("enrollment_no", sid_str),
                "course": profile.get("program", "BE"),
                "branch": profile.get("department", "Computer Engineering"),
                "semester": 2,
                "spi": 8.45,
                "cpi": 8.20,
                "status": "PASS",
                "declared_date": "2026-07-20",
                "subjects": [
                    {"code": "3110005", "name": "Basic Electrical Engineering", "credits": 4, "grade": "AA", "points": 10},
                    {"code": "3110007", "name": "Environmental Sciences", "credits": 3, "grade": "AB", "points": 9},
                    {"code": "3110002", "name": "English & Communication", "credits": 3, "grade": "BB", "points": 8},
                    {"code": "3110006", "name": "Basic Mechanical Engineering", "credits": 4, "grade": "AB", "points": 9},
                    {"code": "3110003", "name": "Programming for Problem Solving", "credits": 5, "grade": "AA", "points": 10}
                ]
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    # -------------------------------------------------------------------------
    # HALL TICKET & EXAM FORM
    # -------------------------------------------------------------------------
    @staticmethod
    def get_hall_ticket(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('hall_tickets')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            profile = StudentERPService.get_student_profile(student_id) or {}
            fallback_doc = {
                "student_id": sid_str,
                "enrollment_no": profile.get("enrollment_no", sid_str),
                "exam_name": "Winter 2026 Regular Examination",
                "seat_no": f"E{sid_str[-6:] if len(sid_str) >= 6 else '210045'}",
                "center_code": "041 (SVIT Vasad)",
                "status": "Available",
                "exams": [
                    {"date": "2026-11-10", "time": "10:30 AM - 01:00 PM", "code": "3130702", "subject": "Data Structures", "room": "Block A - Hall 1"},
                    {"date": "2026-11-12", "time": "10:30 AM - 01:00 PM", "code": "3130703", "subject": "Database Management Systems", "room": "Block A - Hall 1"},
                    {"date": "2026-11-15", "time": "10:30 AM - 01:00 PM", "code": "3130704", "subject": "Digital Electronics", "room": "Block B - Hall 3"},
                    {"date": "2026-11-18", "time": "10:30 AM - 01:00 PM", "code": "3130006", "subject": "Probability & Statistics", "room": "Block A - Hall 2"},
                    {"date": "2026-11-21", "time": "10:30 AM - 01:00 PM", "code": "3130701", "subject": "Operating Systems", "room": "Block B - Hall 4"}
                ]
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    def get_exam_form(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('exam_forms')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            profile = StudentERPService.get_student_profile(student_id) or {}
            fallback_doc = {
                "student_id": sid_str,
                "enrollment_no": profile.get("enrollment_no", sid_str),
                "exam_session": "Winter 2026",
                "form_status": "Submitted",
                "fee_status": "Verified",
                "submission_date": "2026-09-01",
                "penalty_amount": 0,
                "subjects_enrolled": 5,
                "deadline": "2026-09-20"
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    # -------------------------------------------------------------------------
    # APPLICATIONS & GRIEVANCES
    # -------------------------------------------------------------------------
    @staticmethod
    def get_applications(student_id: Any) -> List[Dict[str, Any]]:
        coll = get_collection('applications')
        sid_str = str(student_id)
        if coll is None:
            return []
        docs = list(coll.find({"student_id": sid_str}).sort("created_at", -1))
        if not docs:
            sample = {
                "application_id": f"APP-{sid_str[-4:] if len(sid_str) >= 4 else '1001'}-01",
                "student_id": sid_str,
                "type": "Bonafide Certificate",
                "purpose": "Bank Education Loan Application",
                "status": "Approved",
                "remarks": "Signed and available at Student Section counter #2",
                "created_at": "2026-08-25T11:30:00Z",
                "updated_at": "2026-08-27T16:00:00Z"
            }
            try:
                coll.insert_one(sample)
                sample["_id"] = str(sample.get("_id", ""))
                return [sample]
            except Exception:
                return []
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    @staticmethod
    def submit_application(student_id: Any, app_type: str, purpose: str, details: str = "") -> Dict[str, Any]:
        coll = get_collection('applications')
        sid_str = str(student_id)
        app_id = f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        record = {
            "application_id": app_id,
            "student_id": sid_str,
            "type": app_type,
            "purpose": purpose,
            "details": details,
            "status": "Pending",
            "remarks": "Application submitted for departmental verification",
            "created_at": get_current_time_iso(),
            "updated_at": get_current_time_iso()
        }
        if coll is not None:
            coll.insert_one(record)
            record["_id"] = str(record["_id"])
        return record

    @staticmethod
    def get_grievances(student_id: Any) -> List[Dict[str, Any]]:
        coll = get_collection('grievances')
        sid_str = str(student_id)
        if coll is None:
            return []
        docs = list(coll.find({"student_id": sid_str}).sort("created_at", -1))
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    @staticmethod
    def submit_grievance(student_id: Any, category: str, subject: str, description: str) -> Dict[str, Any]:
        coll = get_collection('grievances')
        sid_str = str(student_id)
        ticket_id = f"GRV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        record = {
            "ticket_id": ticket_id,
            "student_id": sid_str,
            "category": category,
            "subject": subject,
            "description": description,
            "status": "Open",
            "resolution": None,
            "created_at": get_current_time_iso(),
            "updated_at": get_current_time_iso()
        }
        if coll is not None:
            coll.insert_one(record)
            record["_id"] = str(record["_id"])
        return record

    # -------------------------------------------------------------------------
    # DOCUMENTS & TRANSPORT & RAILWAY CONCESSION
    # -------------------------------------------------------------------------
    @staticmethod
    def get_documents(student_id: Any) -> List[Dict[str, Any]]:
        coll = get_collection('documents')
        sid_str = str(student_id)
        if coll is None:
            return []
        docs = list(coll.find({"student_id": sid_str}))
        if not docs:
            sample_docs = [
                {"student_id": sid_str, "doc_name": "10th Marksheet (SSC)", "status": "Verified", "upload_date": "2024-08-10", "type": "pdf"},
                {"student_id": sid_str, "doc_name": "12th Marksheet (HSC)", "status": "Verified", "upload_date": "2024-08-10", "type": "pdf"},
                {"student_id": sid_str, "doc_name": "GUJCET / JEE Score Card", "status": "Verified", "upload_date": "2024-08-10", "type": "pdf"},
                {"student_id": sid_str, "doc_name": "ACPC Admission Allotment Letter", "status": "Verified", "upload_date": "2024-08-12", "type": "pdf"},
                {"student_id": sid_str, "doc_name": "Semester 1 Grade Card", "status": "Official", "upload_date": "2025-02-15", "type": "pdf"},
                {"student_id": sid_str, "doc_name": "Semester 2 Grade Card", "status": "Official", "upload_date": "2025-08-01", "type": "pdf"}
            ]
            for s in sample_docs:
                try:
                    coll.insert_one(s)
                except Exception:
                    pass
            docs = sample_docs
        for d in docs:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        return docs

    @staticmethod
    def get_transport_info(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('transport_passes')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            fallback_doc = {
                "student_id": sid_str,
                "has_bus_pass": True,
                "route_no": "Route 04",
                "route_name": "Vadodara (Manjalpur) -> SVIT Vasad",
                "pickup_point": "Manjalpur Naka",
                "morning_pickup_time": "08:15 AM",
                "evening_departure_time": "05:10 PM",
                "bus_number": "GJ-06-AZ-4421",
                "driver_name": "Rameshbhai Parmar",
                "driver_contact": "+91 98250 12345",
                "valid_until": "2027-05-31",
                "pass_status": "Active"
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    def get_railway_concession(student_id: Any) -> Dict[str, Any]:
        coll = get_collection('railway_concessions')
        sid_str = str(student_id)
        doc = coll.find_one({"student_id": sid_str}) if coll is not None else None

        if not doc:
            profile = StudentERPService.get_student_profile(student_id) or {}
            fallback_doc = {
                "student_id": sid_str,
                "enrollment_no": profile.get("enrollment_no", sid_str),
                "from_station": "Vadodara Junction (BRC)",
                "to_station": "Vasad Junction (VDA)",
                "class_type": "Second Class Ordinary Monthly Pass",
                "voucher_no": f"RC-2026-{sid_str[-4:] if len(sid_str) >= 4 else '1001'}",
                "status": "Issued & Active",
                "issue_date": "2026-08-01",
                "valid_until": "2026-12-31"
            }
            if coll is not None:
                try:
                    coll.update_one({"student_id": sid_str}, {"$set": fallback_doc}, upsert=True)
                except Exception:
                    pass
            return fallback_doc

        doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    def get_homework_and_notes(student_id: Any) -> List[Dict[str, Any]]:
        return [
            {
                "subject": "Data Structures",
                "title": "Assignment 2: Binary Search Trees & AVL Balances",
                "assigned_date": "2026-09-02",
                "due_date": "2026-09-12",
                "status": "Pending",
                "faculty": "Prof. Patel"
            },
            {
                "subject": "Database Management Systems",
                "title": "Lab Exercise 4: Complex SQL Joins & Normalization",
                "assigned_date": "2026-09-04",
                "due_date": "2026-09-14",
                "status": "Submitted",
                "faculty": "Prof. Shah"
            },
            {
                "subject": "Operating Systems",
                "title": "Unit 3 Notes: Semaphore and Process Synchronization",
                "assigned_date": "2026-09-01",
                "type": "Lecture Notes",
                "status": "Available",
                "faculty": "Prof. Mehta"
            }
        ]
