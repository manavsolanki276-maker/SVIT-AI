"""
app/database/admin_crud_service.py
Universal CRUD and Dataset Service for SVIT Admin Panel.
Seamlessly interfaces with MongoDB Atlas with intelligent local caching/fallback.
Auto-seeds existing datasets from CSV files and initial records on first startup.
Tracks audit metadata (created_by, updated_by, created_at, updated_at).
"""
import os
import re
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from app.database.mongodb import get_collection, is_mongodb_connected

logger = logging.getLogger(__name__)

# =========================================================================
# 1. MODULE CONFIGURATIONS & SCHEMAS
# =========================================================================
MODULE_CONFIGS: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------
    # ACADEMIC ADMIN MODULES
    # -------------------------------------------------------------
    "students": {
        "title": "Students",
        "description": "Manage registered students, enrollment details, and academic profiles.",
        "icon": "users",
        "required_permission": "academic",
        "id_field": "enrollment_no",
        "search_fields": ["enrollment_no", "full_name", "name", "email", "department", "program", "status"],
        "filter_fields": ["department", "program", "semester", "division", "gender", "status"],
        "sort_fields": ["enrollment_no", "full_name", "semester", "created_at", "status"],
        "default_sort": ("created_at", -1),
        "source_csv": None,
        "fields": [
            {"key": "enrollment_no", "label": "Enrollment No", "type": "text", "required": True, "table": True},
            {"key": "full_name", "label": "Full Name", "type": "text", "required": True, "table": True},
            {"key": "email", "label": "Email Address", "type": "email", "required": True, "table": True},
            {"key": "program", "label": "Program", "type": "select", "options": ["BE", "BTech", "ME", "MTech", "MCA", "BCA", "Diploma"], "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "Aeronautical Eng."], "required": True, "table": True},
            {"key": "semester", "label": "Semester", "type": "number", "min": 1, "max": 8, "required": True, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["active", "pending", "rejected"], "required": False, "table": True},
            {"key": "division", "label": "Division", "type": "text", "required": False, "table": False},
            {"key": "batch", "label": "Batch", "type": "text", "required": False, "table": False},
            {"key": "phone", "label": "Phone", "type": "text", "required": False, "table": False},
            {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"], "required": False, "table": False},
            {"key": "dob", "label": "Date of Birth", "type": "date", "required": False, "table": False},
            {"key": "address", "label": "Address", "type": "textarea", "required": False, "table": False},
            {"key": "is_profile_complete", "label": "Profile Completed", "type": "checkbox", "required": False, "table": True}
        ]
    },
    "faculty": {
        "title": "Faculty",
        "description": "Manage professors, lecturers, cabin locations, and office hours.",
        "icon": "user-check",
        "required_permission": "academic",
        "id_field": "faculty_id",
        "search_fields": ["faculty_id", "full_name", "designation", "department", "subject", "email"],
        "filter_fields": ["department", "program", "designation"],
        "sort_fields": ["faculty_id", "full_name", "department", "designation"],
        "default_sort": ("faculty_id", 1),
        "source_csv": "faculty.csv",
        "fields": [
            {"key": "faculty_id", "label": "Faculty ID", "type": "text", "required": True, "table": True},
            {"key": "full_name", "label": "Full Name", "type": "text", "required": True, "table": True},
            {"key": "designation", "label": "Designation", "type": "select", "options": ["Professor & Head", "Professor", "Associate Professor", "Assistant Professor", "Visiting Lecturer"], "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "Aeronautical Eng.", "Applied Sciences & Humanities"], "required": True, "table": True},
            {"key": "program", "label": "Program", "type": "select", "options": ["BE", "BTech", "ME", "MCA", "Diploma"], "required": False, "table": False},
            {"key": "subject", "label": "Primary Subject(s)", "type": "text", "required": False, "table": True},
            {"key": "email", "label": "Email", "type": "email", "required": True, "table": True},
            {"key": "phone", "label": "Contact Number", "type": "text", "required": False, "table": False},
            {"key": "cabin", "label": "Cabin Location", "type": "text", "required": False, "table": True},
            {"key": "qualification", "label": "Highest Qualification", "type": "text", "required": False, "table": False},
            {"key": "experience", "label": "Experience", "type": "text", "required": False, "table": False},
            {"key": "specialization", "label": "Area of Specialization", "type": "text", "required": False, "table": False},
            {"key": "office_hours", "label": "Office Hours", "type": "text", "required": False, "table": False},
            {"key": "image_url", "label": "Profile Image", "type": "image_upload", "required": False, "table": False}
        ]
    },
    "timetable": {
        "title": "Timetable",
        "description": "Manage class schedules, lecture timings, faculties, and classroom allocations.",
        "icon": "calendar",
        "required_permission": "academic",
        "id_field": "id",
        "search_fields": ["subject", "faculty", "room", "department", "day", "program", "division"],
        "filter_fields": ["department", "program", "year", "semester", "division", "day", "faculty", "room"],
        "sort_fields": ["day", "start_time", "department", "semester"],
        "default_sort": ("day", 1),
        "source_csv": "timetable.csv",
        "fields": [
            {"key": "id", "label": "Schedule ID", "type": "text", "required": True, "table": True},
            {"key": "program", "label": "Program", "type": "select", "options": ["Diploma", "BE", "BCA", "MCA", "ME"], "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Artificial Intelligence & Machine Learning", "Data Science", "Electronics & Communication", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering", "Automobile Engineering", "Computer Applications"], "required": True, "table": True},
            {"key": "year", "label": "Year", "type": "select", "options": ["FY", "SY", "TY", "LY"], "required": False, "table": True},
            {"key": "semester", "label": "Semester", "type": "number", "min": 1, "max": 8, "required": True, "table": True},
            {"key": "division", "label": "Division", "type": "text", "required": True, "table": True},
            {"key": "day", "label": "Day of Week", "type": "select", "options": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], "required": True, "table": True},
            {"key": "start_time", "label": "Start Time", "type": "time", "required": True, "table": True},
            {"key": "end_time", "label": "End Time", "type": "time", "required": True, "table": True},
            {"key": "subject", "label": "Subject Name", "type": "text", "required": True, "table": True},
            {"key": "faculty", "label": "Faculty In-Charge", "type": "text", "required": True, "table": True},
            {"key": "room", "label": "Room / Lab No.", "type": "text", "required": True, "table": True}
        ]
    },
    "rooms": {
        "title": "Academic Rooms & Classrooms",
        "description": "Manage academic classrooms, lecture halls, computer laboratories, and room allocations.",
        "icon": "door-closed",
        "required_permission": "academic",
        "id_field": "room_id",
        "search_fields": ["room_id", "room_name", "department", "building", "room_type", "status"],
        "filter_fields": ["department", "status", "room_type", "building", "floor"],
        "sort_fields": ["room_name", "room_id", "department", "status"],
        "default_sort": ("room_name", 1),
        "source_csv": "rooms_facilities.csv",
        "fields": [
            {"key": "room_id", "label": "Room ID", "type": "text", "required": True, "table": True},
            {"key": "room_name", "label": "Room / Lab No.", "type": "text", "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "text", "required": False, "table": True},
            {"key": "building", "label": "Building / Block", "type": "text", "required": False, "table": True},
            {"key": "floor", "label": "Floor", "type": "text", "required": False, "table": True},
            {"key": "room_type", "label": "Room Type", "type": "select", "options": ["Classroom", "Laboratory", "Seminar Hall", "Tutorial Room", "Workshop", "Other"], "required": False, "table": True},
            {"key": "capacity", "label": "Capacity", "type": "number", "required": False, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["Active", "Available", "Occupied", "Maintenance", "Inactive"], "required": True, "table": True},
            {"key": "facilities", "label": "Equipment / Amenities", "type": "textarea", "required": False, "table": False}
        ]
    },
    "rooms_facilities": {
        "title": "Academic Rooms & Classrooms",
        "description": "Manage academic classrooms, lecture halls, computer laboratories, and room allocations.",
        "icon": "door-closed",
        "required_permission": "academic",
        "id_field": "room_id",
        "search_fields": ["room_id", "room_name", "department", "building", "room_type", "status"],
        "filter_fields": ["department", "status", "room_type", "building", "floor"],
        "sort_fields": ["room_name", "room_id", "department", "status"],
        "default_sort": ("room_name", 1),
        "source_csv": "rooms_facilities.csv",
        "fields": [
            {"key": "room_id", "label": "Room ID", "type": "text", "required": True, "table": True},
            {"key": "room_name", "label": "Room / Lab No.", "type": "text", "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "text", "required": False, "table": True},
            {"key": "building", "label": "Building / Block", "type": "text", "required": False, "table": True},
            {"key": "floor", "label": "Floor", "type": "text", "required": False, "table": True},
            {"key": "room_type", "label": "Room Type", "type": "select", "options": ["Classroom", "Laboratory", "Seminar Hall", "Tutorial Room", "Workshop", "Other"], "required": False, "table": True},
            {"key": "capacity", "label": "Capacity", "type": "number", "required": False, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["Active", "Available", "Occupied", "Maintenance", "Inactive"], "required": True, "table": True},
            {"key": "facilities", "label": "Equipment / Amenities", "type": "textarea", "required": False, "table": False}
        ]
    },
    "facilities": {
        "title": "Campus Facilities & Resources",
        "description": "Manage student common rooms, reading rooms, libraries, admin offices, and campus resources.",
        "icon": "building-2",
        "required_permission": "academic",
        "id_field": "facility_id",
        "search_fields": ["facility_id", "facility_name", "category", "building", "location", "description"],
        "filter_fields": ["category", "status", "building", "floor"],
        "sort_fields": ["facility_name", "category", "status"],
        "default_sort": ("facility_name", 1),
        "source_csv": "facilities.csv",
        "fields": [
            {"key": "facility_id", "label": "Facility ID", "type": "text", "required": True, "table": True},
            {"key": "facility_name", "label": "Facility Name", "type": "text", "required": True, "table": True},
            {"key": "category", "label": "Category", "type": "select", "options": ["Student Facility", "Academic / Study Facility", "Administrative", "Library / Study", "Health", "Sports", "Campus Landmark / Entry", "Other"], "required": True, "table": True},
            {"key": "building", "label": "Building / Block", "type": "text", "required": False, "table": True},
            {"key": "floor", "label": "Floor", "type": "text", "required": False, "table": True},
            {"key": "location", "label": "Location / Landmark", "type": "text", "required": False, "table": True},
            {"key": "description", "label": "Description & Accessibility", "type": "textarea", "required": False, "table": False},
            {"key": "capacity", "label": "Capacity", "type": "number", "required": False, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["Active", "Available", "Occupied", "Maintenance", "Inactive"], "required": True, "table": True},
            {"key": "facilities", "label": "Amenities / Features", "type": "textarea", "required": False, "table": False}
        ]
    },
    "campus_info": {
        "title": "Campus Landmarks & Places",
        "description": "Manage campus navigation landmarks, gates, zones, and building coordinates.",
        "icon": "map-pin",
        "required_permission": "academic",
        "id_field": "place_id",
        "search_fields": ["place_id", "place_name", "category", "zone", "landmark", "description"],
        "filter_fields": ["category", "zone"],
        "sort_fields": ["place_id", "place_name", "category", "zone"],
        "default_sort": ("place_name", 1),
        "source_csv": "campus_info.csv",
        "fields": [
            {"key": "place_id", "label": "Place ID", "type": "text", "required": True, "table": True},
            {"key": "place_name", "label": "Place Name", "type": "text", "required": True, "table": True},
            {"key": "category", "label": "Category", "type": "select", "options": ["Department", "Classroom", "Laboratory", "Library", "Administrative", "Auditorium", "Sports", "Cafeteria", "Facility"], "required": True, "table": True},
            {"key": "zone", "label": "Campus Zone", "type": "select", "options": ["East Wing", "West Wing", "Main Block", "Ground Floor", "First Floor", "Second Floor", "Sports Complex", "Outer Campus"], "required": False, "table": True},
            {"key": "landmark", "label": "Nearest Landmark", "type": "text", "required": False, "table": True},
            {"key": "description", "label": "Description & Accessibility", "type": "textarea", "required": False, "table": False},
            {"key": "image_url", "label": "Location / Room Image", "type": "image_upload", "required": False, "table": False}
        ]
    },
    "subjects": {
        "title": "Subjects & Curriculum",
        "description": "Manage academic programs, courses, semesters, subjects, syllabus codes, and credit schemes.",
        "icon": "book",
        "required_permission": "academic",
        "id_field": "subject_id",
        "search_fields": ["subject_id", "subject_code", "subject_name", "department", "program", "faculty", "year", "semester"],
        "filter_fields": ["department", "program", "year", "semester", "subject_type", "credits", "faculty"],
        "sort_fields": ["subject_code", "subject_name", "semester", "credits", "department", "program"],
        "default_sort": ("subject_code", 1),
        "source_csv": "subjects.csv",
        "fields": [
            {"key": "subject_id", "label": "Subject ID", "type": "text", "required": True, "table": True},
            {"key": "subject_code", "label": "Subject Code", "type": "text", "required": True, "table": True},
            {"key": "subject_name", "label": "Subject Name", "type": "text", "required": True, "table": True},
            {"key": "program", "label": "Program", "type": "select", "options": ["Diploma", "BE", "BCA", "MCA", "ME"], "required": True, "table": True},
            {"key": "department", "label": "Course / Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Artificial Intelligence & Machine Learning", "Data Science", "Electronics & Communication", "Mechanical Engineering", "Civil Engineering", "Electrical Engineering", "Automobile Engineering", "Computer Applications"], "required": True, "table": True},
            {"key": "year", "label": "Academic Year", "type": "select", "options": ["FY", "SY", "TY", "LY"], "required": False, "table": True},
            {"key": "semester", "label": "Semester", "type": "number", "min": 1, "max": 8, "required": True, "table": True},
            {"key": "subject_type", "label": "Subject Type", "type": "select", "options": ["Theory", "Practical", "Elective", "Core Theory", "Project / Seminar"], "required": True, "table": True},
            {"key": "credits", "label": "Credits", "type": "number", "min": 1, "max": 10, "required": True, "table": True},
            {"key": "faculty", "label": "Assigned Faculty", "type": "text", "required": False, "table": True},
            {"key": "description", "label": "Syllabus / Course Description", "type": "textarea", "required": False, "table": False}
        ]
    },
    "placements": {
        "title": "Placement Drives & Companies",
        "description": "Manage on-campus placement drives, visiting companies, packages, and eligibility criteria.",
        "icon": "briefcase",
        "required_permission": "academic",
        "id_field": "placement_id",
        "search_fields": ["placement_id", "company_name", "job_role", "department", "skills_required"],
        "filter_fields": ["department", "program", "status"],
        "sort_fields": ["company_name", "drive_date", "package_lpa", "registration_deadline"],
        "default_sort": ("drive_date", -1),
        "source_csv": "placements.csv",
        "fields": [
            {"key": "placement_id", "label": "Placement ID", "type": "text", "required": True, "table": True},
            {"key": "company_name", "label": "Company Name", "type": "text", "required": True, "table": True},
            {"key": "job_role", "label": "Job Role / Designation", "type": "text", "required": True, "table": True},
            {"key": "package_lpa", "label": "Package (LPA)", "type": "text", "required": True, "table": True},
            {"key": "program", "label": "Eligible Program", "type": "select", "options": ["BE / BTech", "ME / MTech", "MCA", "All Programs"], "required": True, "table": False},
            {"key": "department", "label": "Eligible Department(s)", "type": "text", "required": True, "table": True},
            {"key": "drive_date", "label": "Drive Date", "type": "date", "required": True, "table": True},
            {"key": "location", "label": "Job Location", "type": "text", "required": False, "table": False},
            {"key": "eligibility", "label": "Eligibility Criteria (CGPA/Backlogs)", "type": "textarea", "required": False, "table": False},
            {"key": "vacancies", "label": "Estimated Vacancies", "type": "text", "required": False, "table": False},
            {"key": "skills_required", "label": "Required Skills & Technologies", "type": "text", "required": False, "table": False},
            {"key": "registration_deadline", "label": "Registration Deadline", "type": "date", "required": True, "table": True},
            {"key": "contact_email", "label": "TPO Contact Email", "type": "email", "required": False, "table": False},
            {"key": "status", "label": "Drive Status", "type": "select", "options": ["Upcoming", "Registration Open", "In Progress", "Completed", "Cancelled"], "required": True, "table": True},
            {"key": "company_logo", "label": "Company Logo", "type": "image_upload", "required": False, "table": False}
        ]
    },
    "academic_documents": {
        "title": "Academic Documents (PDF)",
        "description": "Upload, preview, download, and manage official syllabus, calendars, and academic PDFs.",
        "icon": "file-text",
        "required_permission": "academic",
        "id_field": "document_id",
        "search_fields": ["document_id", "title", "department", "category", "file_name", "description"],
        "filter_fields": ["department", "category"],
        "sort_fields": ["title", "department", "upload_date", "file_size"],
        "default_sort": ("upload_date", -1),
        "source_csv": None,
        "fields": [
            {"key": "document_id", "label": "Document ID", "type": "text", "required": True, "table": True},
            {"key": "title", "label": "Document Title", "type": "text", "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["All Departments", "Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng."], "required": True, "table": True},
            {"key": "category", "label": "Category", "type": "select", "options": ["Syllabus", "Academic Calendar", "Exam Regulations", "Circular", "Study Material", "Lab Manual", "Question Bank"], "required": True, "table": True},
            {"key": "description", "label": "Description & Overview", "type": "textarea", "required": False, "table": False},
            {"key": "document_file", "label": "Document File (PDF / DOCX)", "type": "pdf_upload", "required": True, "table": False},
            {"key": "file_name", "label": "File Name", "type": "text", "required": False, "table": True},
            {"key": "file_url", "label": "File Link", "type": "text", "required": False, "table": False},
            {"key": "file_size_formatted", "label": "Size", "type": "text", "required": False, "table": True},
            {"key": "uploaded_by", "label": "Uploaded By", "type": "text", "required": False, "table": True},
            {"key": "upload_date_formatted", "label": "Upload Date", "type": "text", "required": False, "table": True}
        ]
    },

    # -------------------------------------------------------------
    # ADMISSION ADMIN MODULES
    # -------------------------------------------------------------
    "admission_info": {
        "title": "Admission Information",
        "description": "Manage seat intake, eligibility criteria, fee structures, and application guidelines.",
        "icon": "info",
        "required_permission": "admission",
        "id_field": "info_id",
        "search_fields": ["info_id", "title", "program", "department", "category"],
        "filter_fields": ["program", "department", "category", "status"],
        "sort_fields": ["title", "program", "created_at"],
        "default_sort": ("title", 1),
        "source_csv": None,
        "fields": [
            {"key": "info_id", "label": "Info ID", "type": "text", "required": True, "table": True},
            {"key": "title", "label": "Program / Course Title", "type": "text", "required": True, "table": True},
            {"key": "program", "label": "Degree Level", "type": "select", "options": ["Undergraduate (BE/BTech)", "Postgraduate (ME/MTech)", "MCA", "Diploma"], "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "All Disciplines"], "required": True, "table": True},
            {"key": "category", "label": "Admission Quota / Category", "type": "select", "options": ["ACPC Merit Quota", "Management / NRI Quota", "Direct Second Year (D2D)", "General Inquiries"], "required": True, "table": True},
            {"key": "total_seats", "label": "Sanctioned Seats", "type": "number", "required": False, "table": True},
            {"key": "fees_per_year", "label": "Fees / Year (INR)", "type": "text", "required": False, "table": True},
            {"key": "eligibility", "label": "Eligibility Requirements", "type": "textarea", "required": True, "table": False},
            {"key": "admission_process", "label": "Application Procedure & Steps", "type": "textarea", "required": False, "table": False},
            {"key": "key_dates", "label": "Important Dates / Deadlines", "type": "text", "required": False, "table": False},
            {"key": "contact_person", "label": "Admission In-Charge", "type": "text", "required": False, "table": False},
            {"key": "contact_phone", "label": "Helpline Phone", "type": "text", "required": False, "table": False},
            {"key": "status", "label": "Admission Status", "type": "select", "options": ["Admissions Open", "Round 1 Counseling", "Round 2 Counseling", "Admissions Closed", "Upcoming"], "required": True, "table": True}
        ]
    },
    "admission_documents": {
        "title": "Admission Documents (PDF)",
        "description": "Upload cutoff merit lists, admission brochures, forms, and fee charts.",
        "icon": "file-check",
        "required_permission": "admission",
        "id_field": "document_id",
        "search_fields": ["document_id", "title", "program", "document_type", "file_name"],
        "filter_fields": ["program", "document_type"],
        "sort_fields": ["title", "upload_date"],
        "default_sort": ("upload_date", -1),
        "source_csv": None,
        "fields": [
            {"key": "document_id", "label": "Doc ID", "type": "text", "required": True, "table": True},
            {"key": "title", "label": "Document Name", "type": "text", "required": True, "table": True},
            {"key": "program", "label": "Applicable Program", "type": "select", "options": ["BE / BTech", "ME / MTech", "MCA", "Diploma", "All Admissions"], "required": True, "table": True},
            {"key": "document_type", "label": "Document Type", "type": "select", "options": ["Cutoff Merit List", "Admission Brochure", "Fee Structure", "Application Form", "Verification Checklist", "Seat Matrix"], "required": True, "table": True},
            {"key": "description", "label": "Details / Summary", "type": "textarea", "required": False, "table": False},
            {"key": "document_file", "label": "PDF Document", "type": "pdf_upload", "required": True, "table": False},
            {"key": "file_name", "label": "File Name", "type": "text", "required": False, "table": True},
            {"key": "file_url", "label": "File Link", "type": "text", "required": False, "table": False},
            {"key": "file_size_formatted", "label": "Size", "type": "text", "required": False, "table": True},
            {"key": "uploaded_by", "label": "Uploaded By", "type": "text", "required": False, "table": True},
            {"key": "upload_date_formatted", "label": "Upload Date", "type": "text", "required": False, "table": True}
        ]
    },
    "admission_notices": {
        "title": "Admission Notices & Updates",
        "description": "Publish counseling schedules, merit announcement alerts, and deadline notices.",
        "icon": "bell-ring",
        "required_permission": "admission",
        "id_field": "notice_id",
        "search_fields": ["notice_id", "title", "description", "target_audience"],
        "filter_fields": ["target_audience", "priority", "status"],
        "sort_fields": ["publish_date", "priority", "title"],
        "default_sort": ("publish_date", -1),
        "source_csv": None,
        "fields": [
            {"key": "notice_id", "label": "Notice ID", "type": "text", "required": True, "table": True},
            {"key": "title", "label": "Notice Title", "type": "text", "required": True, "table": True},
            {"key": "target_audience", "label": "Target Applicants", "type": "select", "options": ["All Prospective Students", "ACPC Applicants", "Management Quota Applicants", "D2D Applicants", "Parents"], "required": True, "table": True},
            {"key": "priority", "label": "Priority Level", "type": "select", "options": ["Emergency", "High Priority", "Normal", "Low"], "required": True, "table": True},
            {"key": "publish_date", "label": "Publish Date", "type": "date", "required": True, "table": True},
            {"key": "expiry_date", "label": "Expiry Date", "type": "date", "required": False, "table": False},
            {"key": "description", "label": "Notice Content", "type": "textarea", "required": True, "table": False},
            {"key": "is_urgent", "label": "Mark as Urgent Alert", "type": "checkbox", "required": False, "table": True},
            {"key": "status", "label": "Publication Status", "type": "select", "options": ["Published", "Draft", "Archived"], "required": True, "table": True},
            {"key": "image_url", "label": "Notice Poster / Image", "type": "image_upload", "required": False, "table": False}
        ]
    },

    # -------------------------------------------------------------
    # NOTICE / ANNOUNCEMENT ADMIN MODULE
    # -------------------------------------------------------------
    "notices": {
        "title": "Notices & Emergency Announcements",
        "description": "Publish campus-wide emergency alerts, holiday announcements, weather updates, and cancellations.",
        "icon": "megaphone",
        "required_permission": "notices",
        "id_field": "notice_id",
        "search_fields": ["notice_id", "title", "category", "department", "description"],
        "filter_fields": ["category", "priority", "department", "target_audience", "status"],
        "sort_fields": ["is_urgent", "publish_date", "priority", "title"],
        "default_sort": ("publish_date", -1),
        "source_csv": "notices.csv",
        "fields": [
            {"key": "notice_id", "label": "Notice ID", "type": "text", "required": True, "table": True},
            {"key": "title", "label": "Notice Title", "type": "text", "required": True, "table": True},
            {"key": "category", "label": "Notice Type", "type": "select", "options": [
                "Urgent Notices",
                "General Updates",
                "Emergency Announcements",
                "Holiday Announcements",
                "College Closed/Open Updates",
                "Rain/Weather Notices",
                "Class/Lecture Cancellations",
                "Important Alerts",
                "Examination",
                "Academic",
                "Placement",
                "Events"
            ], "required": True, "table": True},
            {"key": "priority", "label": "Priority", "type": "select", "options": ["Emergency", "High", "Medium", "Low"], "required": True, "table": True},
            {"key": "target_audience", "label": "Target Audience", "type": "select", "options": ["All Students", "All Faculty", "All Students & Faculty", "Computer Engineering", "IT Department", "Mechanical Dept", "First Year Only", "Final Year Only"], "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["All Departments", "Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "Administration"], "required": False, "table": True},
            {"key": "publish_date", "label": "Publish Date", "type": "date", "required": True, "table": True},
            {"key": "expiry_date", "label": "Expiry Date", "type": "date", "required": False, "table": False},
            {"key": "description", "label": "Notice Body / Message", "type": "textarea", "required": True, "table": False},
            {"key": "is_urgent", "label": "Is Urgent Alert (Prominent Banner)", "type": "checkbox", "required": False, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["Published", "Draft", "Archived"], "required": True, "table": True},
            {"key": "image_url", "label": "Notice Banner / Image", "type": "image_upload", "required": False, "table": False},
            {"key": "attachment", "label": "Attachment URL", "type": "text", "required": False, "table": False}
        ]
    },

    # -------------------------------------------------------------
    # EVENT ADMIN MODULE (EXPLICITLY NO SPORTS)
    # -------------------------------------------------------------
    "events": {
        "title": "College Events & Programs",
        "description": "Manage cultural festivals, technical hackathons, seminars, workshops, and college programs.",
        "icon": "party-popper",
        "required_permission": "events",
        "id_field": "event_id",
        "search_fields": ["event_id", "event_name", "category", "department", "venue", "organizer"],
        "filter_fields": ["category", "department", "status"],
        "sort_fields": ["event_date", "event_name", "category"],
        "default_sort": ("event_date", -1),
        "source_csv": "events.csv",
        "fields": [
            {"key": "event_id", "label": "Event ID", "type": "text", "required": True, "table": True},
            {"key": "event_name", "label": "Event Name", "type": "text", "required": True, "table": True},
            {"key": "category", "label": "Event Category", "type": "select", "options": [
                "Cultural Events",
                "Technical Events",
                "Hackathons",
                "Seminars",
                "Workshops",
                "Festivals",
                "Other College Programs"
            ], "required": True, "table": True},
            {"key": "department", "label": "Organizing Department", "type": "select", "options": ["All Departments", "Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "Cultural Committee", "Student Activity Council"], "required": True, "table": True},
            {"key": "program", "label": "Eligible Program", "type": "select", "options": ["All Programs", "BE / BTech", "ME", "MCA", "Diploma"], "required": False, "table": False},
            {"key": "event_date", "label": "Event Date", "type": "date", "required": True, "table": True},
            {"key": "start_time", "label": "Start Time", "type": "time", "required": False, "table": False},
            {"key": "end_time", "label": "End Time", "type": "time", "required": False, "table": False},
            {"key": "venue", "label": "Venue / Auditorium", "type": "text", "required": True, "table": True},
            {"key": "organizer", "label": "Event Coordinator / Club", "type": "text", "required": True, "table": False},
            {"key": "speaker_or_guest", "label": "Keynote Speaker / Chief Guest", "type": "text", "required": False, "table": False},
            {"key": "registration_required", "label": "Registration Required?", "type": "select", "options": ["Yes", "No"], "required": True, "table": False},
            {"key": "capacity", "label": "Seat Capacity", "type": "number", "required": False, "table": False},
            {"key": "description", "label": "Event Description & Agenda", "type": "textarea", "required": False, "table": False},
            {"key": "status", "label": "Status", "type": "select", "options": ["Upcoming", "Ongoing", "Completed", "Postponed", "Cancelled"], "required": True, "table": True},
            {"key": "image_url", "label": "Event Poster / Banner", "type": "image_upload", "required": False, "table": False}
        ]
    },

    # -------------------------------------------------------------
    # BUS ADMIN MODULE
    # -------------------------------------------------------------
    "transport": {
        "title": "Bus Routes & Transport",
        "description": "Manage college buses, pickup routes, stop points, departure timings, and drivers.",
        "icon": "bus",
        "required_permission": "bus",
        "id_field": "route_id",
        "search_fields": ["route_id", "route_name", "bus_no", "starting_point", "destination", "driver_name", "stops"],
        "filter_fields": ["starting_point", "destination", "status"],
        "sort_fields": ["bus_no", "route_name", "departure_time", "starting_point"],
        "default_sort": ("bus_no", 1),
        "source_csv": "transport.csv",
        "fields": [
            {"key": "route_id", "label": "Route ID", "type": "text", "required": True, "table": True},
            {"key": "bus_no", "label": "Bus No.", "type": "text", "required": True, "table": True},
            {"key": "route_name", "label": "Route Name / Area", "type": "text", "required": True, "table": True},
            {"key": "starting_point", "label": "Starting Point (City / Stop)", "type": "select", "options": ["Vadodara (Amit Nagar)", "Vadodara (Manjalpur)", "Vadodara (Gotri)", "Vadodara (Waghodia)", "Anand (Bus Stand)", "Anand (Vidyanagar)", "Nadiad", "Bharuch"], "required": True, "table": True},
            {"key": "destination", "label": "Destination", "type": "text", "required": True, "table": False, "default": "SVIT Campus, Vasad"},
            {"key": "stops", "label": "Intermediate Stops (Comma separated)", "type": "textarea", "required": True, "table": True},
            {"key": "departure_time", "label": "Departure Time", "type": "time", "required": True, "table": True},
            {"key": "arrival_time", "label": "Arrival at College", "type": "time", "required": True, "table": True},
            {"key": "driver_name", "label": "Driver Name", "type": "text", "required": True, "table": True},
            {"key": "contact_number", "label": "Driver Contact No", "type": "text", "required": True, "table": True},
            {"key": "capacity", "label": "Seating Capacity", "type": "number", "required": False, "table": False},
            {"key": "status", "label": "Bus Status", "type": "select", "options": ["Active", "On Route", "Maintenance", "Inactive"], "required": True, "table": True},
            {"key": "image_url", "label": "Bus Image / Route Map", "type": "image_upload", "required": False, "table": False}
        ]
    },

    # -------------------------------------------------------------
    # LIBRARY ADMIN MODULES
    # -------------------------------------------------------------
    "library_books": {
        "title": "Library Books & Catalog",
        "description": "Manage catalogued textbooks, reference volumes, authors, ISBNs, and shelf locations.",
        "icon": "book-open",
        "required_permission": "library",
        "id_field": "book_id",
        "search_fields": ["book_id", "book_title", "author", "publisher", "isbn", "subject", "department"],
        "filter_fields": ["department", "program", "semester", "shelf"],
        "sort_fields": ["book_title", "author", "available_copies", "created_at"],
        "default_sort": ("book_title", 1),
        "source_csv": "library_books.csv",
        "fields": [
            {"key": "book_id", "label": "Book ID / Accession No", "type": "text", "required": True, "table": True},
            {"key": "book_title", "label": "Book Title", "type": "text", "required": True, "table": True},
            {"key": "author", "label": "Author(s)", "type": "text", "required": True, "table": True},
            {"key": "publisher", "label": "Publisher", "type": "text", "required": False, "table": False},
            {"key": "edition", "label": "Edition / Year", "type": "text", "required": False, "table": False},
            {"key": "isbn", "label": "ISBN Code", "type": "text", "required": False, "table": True},
            {"key": "program", "label": "Program", "type": "select", "options": ["BE", "BTech", "ME", "MCA", "General"], "required": False, "table": False},
            {"key": "department", "label": "Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "Applied Sciences", "General"], "required": True, "table": True},
            {"key": "semester", "label": "Semester", "type": "number", "min": 1, "max": 8, "required": False, "table": False},
            {"key": "subject", "label": "Subject Name", "type": "text", "required": False, "table": False},
            {"key": "available_copies", "label": "Available Copies", "type": "number", "min": 0, "required": True, "table": True},
            {"key": "shelf", "label": "Shelf / Rack Location", "type": "text", "required": True, "table": True},
            {"key": "image_url", "label": "Book Cover Image", "type": "image_upload", "required": False, "table": False}
        ]
    },
    "library_members": {
        "title": "Library Members",
        "description": "Manage registered student and faculty library memberships and issue limits.",
        "icon": "id-card",
        "required_permission": "library",
        "id_field": "member_id",
        "search_fields": ["member_id", "name", "email", "card_number", "department"],
        "filter_fields": ["member_type", "department", "status"],
        "sort_fields": ["name", "member_id", "created_at"],
        "default_sort": ("name", 1),
        "source_csv": None,
        "fields": [
            {"key": "member_id", "label": "Member ID", "type": "text", "required": True, "table": True},
            {"key": "name", "label": "Member Name", "type": "text", "required": True, "table": True},
            {"key": "member_type", "label": "Member Type", "type": "select", "options": ["Student", "Faculty", "Staff"], "required": True, "table": True},
            {"key": "email", "label": "Email Address", "type": "email", "required": True, "table": True},
            {"key": "department", "label": "Department", "type": "select", "options": ["Computer Engineering", "Information Technology", "Electronics & Comm.", "Mechanical Eng.", "Civil Eng.", "Electrical Eng.", "Applied Sciences"], "required": True, "table": True},
            {"key": "card_number", "label": "Library Card No", "type": "text", "required": True, "table": True},
            {"key": "max_books_allowed", "label": "Max Books Limit", "type": "number", "min": 1, "max": 10, "required": True, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["Active", "Suspended", "Expired"], "required": True, "table": True}
        ]
    },
    "library_issue_return": {
        "title": "Book Issue & Return Records",
        "description": "Track active book loans, due dates, returns, and overdue penalties.",
        "icon": "arrow-left-right",
        "required_permission": "library",
        "id_field": "transaction_id",
        "search_fields": ["transaction_id", "book_title", "book_id", "member_name", "member_id"],
        "filter_fields": ["status"],
        "sort_fields": ["issue_date", "due_date", "status"],
        "default_sort": ("issue_date", -1),
        "source_csv": None,
        "fields": [
            {"key": "transaction_id", "label": "Transaction ID", "type": "text", "required": True, "table": True},
            {"key": "book_id", "label": "Book ID", "type": "text", "required": True, "table": False},
            {"key": "book_title", "label": "Book Title", "type": "text", "required": True, "table": True},
            {"key": "member_id", "label": "Member ID", "type": "text", "required": True, "table": False},
            {"key": "member_name", "label": "Member Name", "type": "text", "required": True, "table": True},
            {"key": "issue_date", "label": "Issue Date", "type": "date", "required": True, "table": True},
            {"key": "due_date", "label": "Due Date", "type": "date", "required": True, "table": True},
            {"key": "return_date", "label": "Return Date", "type": "date", "required": False, "table": True},
            {"key": "fine_amount", "label": "Fine (INR)", "type": "number", "min": 0, "required": False, "table": True},
            {"key": "status", "label": "Status", "type": "select", "options": ["Issued", "Returned", "Overdue", "Lost"], "required": True, "table": True}
        ]
    },
    "library_info": {
        "title": "Library Rules & Information",
        "description": "Manage central library rules, opening hours, reading hall access, and digital subscriptions.",
        "icon": "info",
        "required_permission": "library",
        "id_field": "section_id",
        "search_fields": ["section_id", "section_name", "location", "rules_and_guidelines"],
        "filter_fields": [],
        "sort_fields": ["section_name"],
        "default_sort": ("section_name", 1),
        "source_csv": None,
        "fields": [
            {"key": "section_id", "label": "Section ID", "type": "text", "required": True, "table": True},
            {"key": "section_name", "label": "Library Section / Wing", "type": "text", "required": True, "table": True},
            {"key": "timings", "label": "Operating Hours", "type": "text", "required": True, "table": True},
            {"key": "location", "label": "Floor / Room", "type": "text", "required": True, "table": True},
            {"key": "contact_person", "label": "Librarian In-Charge", "type": "text", "required": False, "table": True},
            {"key": "facilities", "label": "Available Facilities", "type": "text", "required": False, "table": False},
            {"key": "rules_and_guidelines", "label": "Rules & Borrowing Guidelines", "type": "textarea", "required": True, "table": False}
        ]
    },

    # -------------------------------------------------------------
    # CANTEEN ADMIN MODULE
    # -------------------------------------------------------------
    "canteen": {
        "title": "Canteen Menu & Pricing",
        "description": "Manage cafeteria food items, daily menus, pricing, availability, and timings.",
        "icon": "utensils",
        "required_permission": "canteen",
        "id_field": "item_id",
        "search_fields": ["item_id", "shop_name", "item_name", "category", "timing"],
        "filter_fields": ["category", "is_vegetarian", "availability", "timing", "shop_name"],
        "sort_fields": ["item_name", "price_inr", "category", "rating"],
        "default_sort": ("item_name", 1),
        "source_csv": "canteen.csv",
        "fields": [
            {"key": "item_id", "label": "Item ID", "type": "text", "required": True, "table": True},
            {"key": "item_name", "label": "Food / Beverage Name", "type": "text", "required": True, "table": True},
            {"key": "category", "label": "Food Category", "type": "select", "options": [
                "Snacks & Chaat",
                "South Indian",
                "Punjabi / Meals",
                "Gujarati Thali",
                "Fast Food & Sandwiches",
                "Hot & Cold Beverages",
                "Desserts & Ice Cream",
                "Bakery Items"
            ], "required": True, "table": True},
            {"key": "shop_name", "label": "Canteen / Stall Name", "type": "select", "options": ["Main SVIT Canteen", "Nescafe Kiosk", "Amul Parlour", "Juice Center", "Food Court"], "required": True, "table": True},
            {"key": "price_inr", "label": "Price (₹)", "type": "number", "min": 1, "required": True, "table": True},
            {"key": "is_vegetarian", "label": "Vegetarian Diet", "type": "select", "options": ["Yes (Pure Veg)", "Egg Item", "No"], "required": True, "table": True},
            {"key": "availability", "label": "Availability", "type": "select", "options": ["Available", "Out of Stock", "Seasonal", "Special (Fri/Sat Only)"], "required": True, "table": True},
            {"key": "timing", "label": "Serving Timings", "type": "select", "options": ["All Day (8:00 AM - 5:00 PM)", "Morning Breakfast", "Lunch Hours (11:30 AM - 2:30 PM)", "Evening Snacks (3:00 PM - 5:00 PM)"], "required": True, "table": True},
            {"key": "location", "label": "Counter Location", "type": "text", "required": False, "table": False},
            {"key": "rating", "label": "Student Rating (1-5)", "type": "text", "required": False, "table": False},
            {"key": "image_url", "label": "Food Item Photo", "type": "image_upload", "required": False, "table": False}
        ]
    },

    # -------------------------------------------------------------
    # SPORTS ADMIN MODULE (EXPLICITLY NO GENERAL EVENTS)
    # -------------------------------------------------------------
    "sports": {
        "title": "Sports & Athletics",
        "description": "Manage college sports disciplines, coaches, team captains, and equipment.",
        "icon": "trophy",
        "required_permission": "sports",
        "id_field": "sport_id",
        "search_fields": ["sport_id", "sport_name", "category", "captain_name", "coach_name"],
        "filter_fields": ["category", "equipment_available"],
        "sort_fields": ["sport_name", "category"],
        "default_sort": ("sport_name", 1),
        "source_csv": None,
        "fields": [
            {"key": "sport_id", "label": "Sport ID", "type": "text", "required": True, "table": True},
            {"key": "sport_name", "label": "Sport / Discipline Name", "type": "text", "required": True, "table": True},
            {"key": "category", "label": "Sport Type", "type": "select", "options": ["Outdoor", "Indoor", "Athletics & Track", "Martial Arts & Fitness"], "required": True, "table": True},
            {"key": "captain_name", "label": "Team Captain", "type": "text", "required": False, "table": True},
            {"key": "coach_name", "label": "Sports Instructor / Coach", "type": "text", "required": True, "table": True},
            {"key": "equipment_available", "label": "Equipment Status", "type": "select", "options": ["Available for Issue", "Limited Stock", "Needs Restocking"], "required": True, "table": True},
            {"key": "practice_timings", "label": "Regular Practice Hours", "type": "text", "required": False, "table": False},
            {"key": "ground_assigned", "label": "Assigned Ground / Court", "type": "text", "required": False, "table": True},
            {"key": "image_url", "label": "Sport Banner / Image", "type": "image_upload", "required": False, "table": False}
        ]
    },
    "sports_events": {
        "title": "Sports Tournaments & Matches",
        "description": "Manage inter-departmental tournaments, GTU sports meets, cricket matches, and athletic events.",
        "icon": "medal",
        "required_permission": "sports",
        "id_field": "event_id",
        "search_fields": ["event_id", "event_name", "sport_name", "venue", "organizer"],
        "filter_fields": ["sport_name", "status"],
        "sort_fields": ["event_date", "event_name", "status"],
        "default_sort": ("event_date", -1),
        "source_csv": None,
        "fields": [
            {"key": "event_id", "label": "Tournament ID", "type": "text", "required": True, "table": True},
            {"key": "event_name", "label": "Tournament / Match Name", "type": "text", "required": True, "table": True},
            {"key": "sport_name", "label": "Sport Discipline", "type": "select", "options": ["Cricket", "Football", "Volleyball", "Basketball", "Badminton", "Table Tennis", "Chess", "Kabaddi", "Athletics Meet"], "required": True, "table": True},
            {"key": "event_date", "label": "Match / Event Date", "type": "date", "required": True, "table": True},
            {"key": "venue", "label": "Ground / Court Venue", "type": "text", "required": True, "table": True},
            {"key": "registration_deadline", "label": "Team Registration Deadline", "type": "date", "required": False, "table": False},
            {"key": "prize_details", "label": "Trophies & Prize Details", "type": "text", "required": False, "table": False},
            {"key": "organizer", "label": "Sports Committee Coordinator", "type": "text", "required": True, "table": True},
            {"key": "status", "label": "Tournament Status", "type": "select", "options": ["Upcoming", "Ongoing", "Completed", "Postponed", "Rain Delayed"], "required": True, "table": True},
            {"key": "image_url", "label": "Sports Event Poster", "type": "image_upload", "required": False, "table": False}
        ]
    },
    "grounds": {
        "title": "Grounds & Athletic Facilities",
        "description": "Manage college cricket ground, football pitch, indoor badminton court, and gym facilities.",
        "icon": "flag",
        "required_permission": "sports",
        "id_field": "ground_id",
        "search_fields": ["ground_id", "ground_name", "sport_type", "location", "in_charge"],
        "filter_fields": ["sport_type", "availability_status", "floodlights_available"],
        "sort_fields": ["ground_name", "sport_type", "availability_status"],
        "default_sort": ("ground_name", 1),
        "source_csv": None,
        "fields": [
            {"key": "ground_id", "label": "Ground ID", "type": "text", "required": True, "table": True},
            {"key": "ground_name", "label": "Ground / Court Facility Name", "type": "text", "required": True, "table": True},
            {"key": "sport_type", "label": "Designated Sport", "type": "select", "options": ["Cricket Ground", "Football Turf", "Basketball Court", "Badminton Indoor Court", "Volleyball Court", "Athletic Track", "Gymnasium"], "required": True, "table": True},
            {"key": "location", "label": "Location on Campus", "type": "text", "required": True, "table": True},
            {"key": "floodlights_available", "label": "Floodlights Installed", "type": "select", "options": ["Yes (Night Matches Allowed)", "No (Daylight Only)"], "required": True, "table": True},
            {"key": "availability_status", "label": "Availability Status", "type": "select", "options": ["Open for Practice", "Reserved for Tournament", "Under Turf Maintenance", "Closed"], "required": True, "table": True},
            {"key": "timings", "label": "Operating Hours", "type": "text", "required": True, "table": True},
            {"key": "in_charge", "label": "Ground In-Charge", "type": "text", "required": False, "table": False},
            {"key": "image_url", "label": "Ground Photo", "type": "image_upload", "required": False, "table": False}
        ]
    }
}

# Mapping of friendly URL / route aliases to canonical module keys
MODULE_ALIASES: Dict[str, str] = {
    "admission": "admission_info",
    "admission-info": "admission_info",
    "buses": "transport",
    "bus-routes": "transport",
    "bus_routes": "transport",
    "bus-stops": "transport",
    "bus_stops": "transport",
    "bus-timings": "transport",
    "bus_timings": "transport",
    "library": "library_info",
    "library-info": "library_info",
    "books": "library_books",
    "library-books": "library_books",
    "members": "library_members",
    "library-members": "library_members",
    "issue-return": "library_issue_return",
    "issue_return": "library_issue_return",
    "canteen-menu": "canteen",
    "canteen_menu": "canteen",
    "food-items": "canteen",
    "food_items": "canteen",
    "sports-disciplines": "sports",
    "sports_disciplines": "sports",
    "rooms": "rooms_facilities",
    "rooms-facilities": "rooms_facilities",
    "rooms_facilities": "rooms_facilities",
    "facility": "facilities",
    "facilities": "facilities",
    "campus-info": "campus_info",
    "campus_info": "campus_info",
    "campus-landmarks": "campus_info",
    "campus_landmarks": "campus_info",
    "navigation": "campus_info",
    "campus-navigation": "campus_info",
    "campus_navigation": "campus_info"
}


# In-memory local fallback store when MongoDB is not connected
_LOCAL_DATA_STORE: Dict[str, Dict[str, Any]] = {}
_IS_INITIALIZED = False


# =========================================================================
# 2. INITIAL SEEDING & DATA INITIALIZATION
# =========================================================================
def initialize_datasets_if_needed(project_root: Optional[str] = None):
    """
    Seeds MongoDB collections (or local store) from existing CSV knowledge base files
    and provides realistic initial sample data for empty modules.
    """
    global _IS_INITIALIZED
    if _IS_INITIALIZED:
        return

    # Fast-path check: If MongoDB is connected and already has seeded collections, skip expensive scans
    try:
        notices_coll = get_collection("notices")
        if notices_coll is not None:
            try:
                if notices_coll.estimated_document_count() > 0:
                    _IS_INITIALIZED = True
                    return
            except Exception:
                pass
    except Exception:
        pass

    if not project_root:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    kb_dir = os.path.join(project_root, "knowledge_base")

    for module_key, config in MODULE_CONFIGS.items():
        src_csv = config.get("source_csv")
        coll = AdminCRUDService._resolve_coll(module_key)
        count = coll.count_documents({}) if coll is not None else len(_LOCAL_DATA_STORE.get(module_key, {}))

        if count > 0:
            continue

        records_to_seed = []

        # 1. Try reading from CSV file if configured
        target_csv = src_csv
        if target_csv and not os.path.exists(os.path.join(kb_dir, target_csv)):
            if target_csv == "subjects.csv" and os.path.exists(os.path.join(kb_dir, "subject.csv")):
                target_csv = "subject.csv"
            elif target_csv == "subject.csv" and os.path.exists(os.path.join(kb_dir, "subjects.csv")):
                target_csv = "subjects.csv"

        if target_csv and os.path.exists(os.path.join(kb_dir, target_csv)):
            try:
                csv_path = os.path.join(kb_dir, target_csv)
                df = pd.read_csv(csv_path, sep=None, engine='python', dtype=str).fillna("")
                for idx, r in enumerate(df.to_dict(orient="records")):
                    clean = {str(k).strip().lower(): str(v).strip() for k, v in r.items()}
                    id_field = config["id_field"]
                    if id_field not in clean or not clean[id_field]:
                        clean[id_field] = f"{module_key[:3].upper()}_{idx+1:04d}"
                    clean["id"] = clean[id_field]
                    clean["created_at"] = datetime.utcnow().isoformat()
                    clean["created_by"] = "system_dataset"
                    records_to_seed.append(clean)
            except Exception as e:
                logger.warning(f"Error loading {module_key} from {target_csv}: {e}")

        # 2. For students: sync genuine registered students if present in SQLite/MongoDB
        elif module_key == "students":
            try:
                from app.database.models.student import Student
                if Student:
                    db_students = Student.query.all()
                    for s in db_students:
                        records_to_seed.append({
                            "id": str(s.enrollment_no or s.id),
                            "enrollment_no": s.enrollment_no or f"STU_{s.id:04d}",
                            "full_name": s.full_name or "Student",
                            "name": s.full_name or "Student",
                            "email": s.email or "",
                            "program": s.program or "BE",
                            "department": s.department or "Computer Engineering",
                            "semester": s.semester or 1,
                            "division": s.division or "A",
                            "batch": s.batch or "A1",
                            "phone": s.phone or "",
                            "gender": s.gender or "Other",
                            "dob": s.dob or "",
                            "address": s.address or "",
                            "is_profile_complete": bool(s.is_profile_complete),
                            "created_at": datetime.utcnow().isoformat(),
                            "created_by": "student_registration"
                        })
            except Exception as e:
                logger.debug(f"Student sync note: {e}")

        # 3. Insert genuine records into MongoDB or local store
        # NOTE: If no CSV exists and no records exist, collection remains EMPTY (0 records)
        if coll is not None and records_to_seed:
            try:
                for r in records_to_seed:
                    coll.update_one({"id": r["id"]}, {"$set": r}, upsert=True)
            except Exception as e:
                logger.warning(f"MongoDB seed error for {module_key}: {e}")
        elif records_to_seed:
            if module_key not in _LOCAL_DATA_STORE:
                _LOCAL_DATA_STORE[module_key] = {}
            for r in records_to_seed:
                _LOCAL_DATA_STORE[module_key][str(r["id"])] = r
        else:
            if module_key not in _LOCAL_DATA_STORE:
                _LOCAL_DATA_STORE[module_key] = {}

    _IS_INITIALIZED = True


# =========================================================================
# 3. UNIVERSAL CRUD SERVICE CLASS
# =========================================================================
class AdminCRUDService:
    """
    Unified CRUD Service powering all 28 Admin Modules.
    Provides complete pagination, robust text search, multifaceted filtering,
    dynamic sorting, validation, audit trailing, and RAG document sync.
    """

    @classmethod
    def resolve_module_key(cls, module_key: str) -> str:
        """Resolves friendly or plural alias names to canonical module keys."""
        if not module_key:
            return ""
        clean_key = str(module_key).strip().lower().replace("-", "_")
        return MODULE_ALIASES.get(clean_key, clean_key)

    @classmethod
    def _resolve_coll(cls, module_key: str):
        """Resolves the physical MongoDB collection for a given module key."""
        canonical = cls.resolve_module_key(module_key)
        if canonical in ("rooms", "rooms_facilities"):
            return get_collection("rooms_facilities")
        elif canonical in ("subjects", "subject"):
            return get_collection("subjects")
        elif canonical == "facilities":
            return get_collection("facilities")
        elif canonical == "campus_info":
            return get_collection("rooms")
        return get_collection(canonical)

    @staticmethod
    def list_items(
        module_key: str,
        search: str = "",
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: int = 1,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieves a paginated, filtered, searched, and sorted list of items for any module.
        """
        initialize_datasets_if_needed()
        module_key = AdminCRUDService.resolve_module_key(module_key)
        config = MODULE_CONFIGS.get(module_key)
        if not config:
            return {"status": "error", "message": f"Unknown module '{module_key}'", "items": [], "total": 0}

        coll = AdminCRUDService._resolve_coll(module_key)
        if coll is not None:
            # -------------------------------------------------------------
            # MONGODB BACKEND
            # -------------------------------------------------------------
            query: Dict[str, Any] = {}

            # 1. Search Query
            if search and search.strip():
                clean_search = search.strip()
                search_fields = config.get("search_fields", [])
                if search_fields:
                    query["$or"] = [
                        {f: {"$regex": re.escape(clean_search), "$options": "i"}}
                        for f in search_fields
                    ]

            # 2. Filters
            if filters:
                for k, v in filters.items():
                    if v is not None and str(v).strip() != "" and str(v).lower() != "all":
                        if k == "status" and str(v).lower() == "active":
                            # Active includes documents where status='active' OR status is missing
                            status_clause = {"$or": [{"status": "active"}, {"status": {"$exists": False}}]}
                            if "$and" not in query:
                                query["$and"] = []
                            query["$and"].append(status_clause)
                        elif str(v).lower() in ("true", "false"):
                            query[k] = (str(v).lower() == "true")
                        elif k in ("semester", "sem"):
                            try:
                                val_int = int(v)
                                query[k] = {"$in": [str(v), val_int]}
                            except (ValueError, TypeError):
                                query[k] = v
                        elif isinstance(v, str) and not v.isdigit() and k not in ("id", "place_id", "faculty_id", "enrollment_no", "_id"):
                            query[k] = {"$regex": f"^{re.escape(v.strip())}$", "$options": "i"}
                        else:
                            query[k] = v

            # 3. Sorting
            if not sort_by:
                sort_by, sort_order = config.get("default_sort", ("created_at", -1))

            total = coll.count_documents(query)
            if limit is None or limit <= 0 or limit >= 10000:
                effective_limit = max(1, total) if total > 0 else 1
                skip = 0
                pages = 1
            else:
                effective_limit = limit
                skip = max(0, (page - 1) * effective_limit)
                pages = max(1, (total + effective_limit - 1) // effective_limit)

            cursor = coll.find(query).sort(sort_by, sort_order).skip(skip).limit(effective_limit)
            id_field = config.get("id_field", "id")
            items = []
            for doc in cursor:
                doc_dict = dict(doc)
                if "_id" in doc_dict:
                    doc_dict["_id"] = str(doc_dict["_id"])
                for k, v in list(doc_dict.items()):
                    if isinstance(v, datetime):
                        doc_dict[k] = v.isoformat()
                if "id" not in doc_dict or not doc_dict["id"]:
                    doc_dict["id"] = doc_dict.get(id_field) or str(doc_dict.get("_id", ""))
                # Default status to active if missing
                if module_key == "students" and "status" not in doc_dict:
                    doc_dict["status"] = "active"
                items.append(doc_dict)

            return {
                "status": "success",
                "module": module_key,
                "config": {
                    "title": config["title"],
                    "description": config["description"],
                    "icon": config["icon"],
                    "id_field": config["id_field"],
                    "fields": config["fields"]
                },
                "items": items,
                "total": total,
                "page": page,
                "limit": effective_limit,
                "pages": pages
            }

        else:
            # -------------------------------------------------------------
            # IN-MEMORY / LOCAL STORE FALLBACK
            # -------------------------------------------------------------
            module_data = _LOCAL_DATA_STORE.get(module_key, {})
            all_items = list(module_data.values())

            # 1. Search Filter
            if search and search.strip():
                clean_search = search.strip().lower()
                search_fields = config.get("search_fields", [])
                filtered = []
                for item in all_items:
                    match = any(clean_search in str(item.get(f, '')).lower() for f in search_fields)
                    if match:
                        filtered.append(item)
                all_items = filtered

            # 2. Filters
            if filters:
                for k, v in filters.items():
                    if v is not None and str(v).strip() != "" and str(v).lower() != "all":
                        if k == "status" and str(v).lower() == "active":
                            all_items = [i for i in all_items if i.get("status", "active") == "active"]
                        elif str(v).lower() in ("true", "false"):
                            bool_val = (str(v).lower() == "true")
                            all_items = [i for i in all_items if bool(i.get(k)) == bool_val]
                        else:
                            all_items = [i for i in all_items if str(i.get(k, '')).lower() == str(v).lower()]

            # 3. Sort
            if not sort_by:
                sort_by, sort_order = config.get("default_sort", ("created_at", -1))
            
            try:
                all_items.sort(key=lambda x: str(x.get(sort_by, '')), reverse=(sort_order == -1))
            except Exception:
                pass

            total = len(all_items)
            if limit is None or limit <= 0 or limit >= 10000:
                effective_limit = max(1, total) if total > 0 else 1
                skip = 0
                pages = 1
                paged_items = all_items
            else:
                effective_limit = limit
                skip = max(0, (page - 1) * effective_limit)
                pages = max(1, (total + effective_limit - 1) // effective_limit)
                paged_items = all_items[skip:skip + effective_limit]

            return {
                "status": "success",
                "module": module_key,
                "config": {
                    "title": config["title"],
                    "description": config["description"],
                    "icon": config["icon"],
                    "id_field": config["id_field"],
                    "fields": config["fields"]
                },
                "items": paged_items,
                "total": total,
                "page": page,
                "limit": effective_limit,
                "pages": pages
            }

    @staticmethod
    def get_item(module_key: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single record by its primary ID."""
        initialize_datasets_if_needed()
        module_key = AdminCRUDService.resolve_module_key(module_key)
        config = MODULE_CONFIGS.get(module_key)
        if not config:
            return None

        id_field = config["id_field"]
        coll = AdminCRUDService._resolve_coll(module_key)
        if coll is not None:
            from bson import ObjectId
            query = {
                "$or": [
                    {"id": item_id},
                    {id_field: item_id},
                    {"_id": ObjectId(item_id) if ObjectId.is_valid(item_id) else None}
                ]
            }
            doc = coll.find_one(query)
            if doc:
                doc_dict = dict(doc)
                if "_id" in doc_dict:
                    doc_dict["_id"] = str(doc_dict["_id"])
                for k, v in list(doc_dict.items()):
                    if isinstance(v, datetime):
                        doc_dict[k] = v.isoformat()
                if "id" not in doc_dict or not doc_dict["id"]:
                    doc_dict["id"] = doc_dict.get(id_field) or str(doc_dict.get("_id", ""))
                return doc_dict
            return None
        else:
            module_data = _LOCAL_DATA_STORE.get(module_key, {})
            # Check by key, id, or id_field
            if item_id in module_data:
                return module_data[item_id]
            for item in module_data.values():
                if str(item.get("id")) == str(item_id) or str(item.get(id_field)) == str(item_id):
                    return item
            return None

    @staticmethod
    def create_item(module_key: str, data: Dict[str, Any], admin_user: Any = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Creates a new record with audit fields (created_by, created_at) and validations.
        """
        initialize_datasets_if_needed()
        module_key = AdminCRUDService.resolve_module_key(module_key)
        config = MODULE_CONFIGS.get(module_key)
        if not config:
            return False, f"Unknown module '{module_key}'", None

        clean_data = dict(data)
        clean_data.pop("_id", None)
        id_field = config["id_field"]

        # Validate required fields
        for field in config["fields"]:
            if field.get("required") and field["key"] not in ("id", id_field):
                val = clean_data.get(field["key"])
                if field.get("type") in ("pdf_upload", "image_upload"):
                    if not val and not clean_data.get("file_url") and not clean_data.get("image_url"):
                        return False, f"Field '{field['label']}' is required.", None
                else:
                    if val is None or str(val).strip() == "":
                        return False, f"Field '{field['label']}' is required.", None

        # Generate ID if not provided
        if id_field not in clean_data or not clean_data[id_field]:
            rand_code = uuid.uuid4().hex[:6].upper()
            clean_data[id_field] = f"{module_key[:3].upper()}_{rand_code}"

        item_id = str(clean_data[id_field]).strip()
        clean_data[id_field] = item_id
        clean_data["id"] = item_id

        # Check for duplicate ID
        existing = AdminCRUDService.get_item(module_key, item_id)
        if existing:
            return False, f"A record with {config['id_field']} '{item_id}' already exists.", None

        # Add Audit Fields
        now = datetime.utcnow()
        clean_data["created_at"] = now.isoformat()
        clean_data["updated_at"] = now.isoformat()
        username = getattr(admin_user, "username", "admin") if admin_user else "admin"
        clean_data["created_by"] = username
        clean_data["updated_by"] = username

        # RAG Document Processing Integration
        if module_key in ("academic_documents", "admission_documents") or clean_data.get("file_url"):
            clean_data.setdefault("version", 1)
            clean_data.setdefault("is_active", True)
            clean_data.setdefault("rag_status", "PROCESSING")
            
            file_url = clean_data.get("file_url")
            file_path = AdminCRUDService._resolve_file_path_from_url(file_url)
            
            if file_path and os.path.exists(file_path):
                try:
                    from app.ai.document_processor import process_and_index_document
                    rag_ok, rag_msg, chunk_count, stats = process_and_index_document(
                        document_id=item_id,
                        file_path=file_path,
                        doc_metadata=clean_data
                    )
                    if rag_ok:
                        clean_data["rag_status"] = "INDEXED"
                        clean_data["chunk_count"] = chunk_count
                        clean_data["page_count"] = stats.get("page_count", 1)
                        clean_data["indexed_at"] = stats.get("indexed_at")
                        clean_data["file_hash"] = stats.get("file_hash")
                        clean_data["error_message"] = ""
                    else:
                        clean_data["rag_status"] = "FAILED"
                        clean_data["error_message"] = rag_msg
                except Exception as rag_err:
                    clean_data["rag_status"] = "FAILED"
                    clean_data["error_message"] = str(rag_err)

        # Save to DB or local store
        coll = AdminCRUDService._resolve_coll(module_key)
        if coll is not None:
            try:
                coll.insert_one(clean_data)
                # Dispatch student notification if applicable for this admin action
                AdminCRUDService._dispatch_admin_action_notification(module_key, item_id, clean_data, is_update=False)
                # Read back clean doc
                created = AdminCRUDService.get_item(module_key, item_id)
                return True, "Record created successfully.", created
            except Exception as e:
                return False, f"Database error creating item: {str(e)}", None
        else:
            if module_key not in _LOCAL_DATA_STORE:
                _LOCAL_DATA_STORE[module_key] = {}
            _LOCAL_DATA_STORE[module_key][item_id] = clean_data
            AdminCRUDService._dispatch_admin_action_notification(module_key, item_id, clean_data, is_update=False)
            return True, "Record created successfully.", clean_data

    @staticmethod
    def _resolve_file_path_from_url(file_url: Optional[str]) -> Optional[str]:
        """Resolves physical file path from public URL reference."""
        if not file_url:
            return None
        clean_url = file_url.split('/static/')[-1]
        static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
        local_path = os.path.join(static_root, clean_url.replace('/', os.sep))
        if os.path.exists(local_path):
            return local_path
        if os.path.exists(file_url):
            return file_url
        return None

    @staticmethod
    def _dispatch_admin_action_notification(module_key: str, item_id: str, clean_data: Dict[str, Any], is_update: bool = False):
        """
        Creates real MongoDB student notifications when applicable Admin actions take place.
        Avoids spamming for unrelated CRUD ops, and targets applicable student audiences.
        """
        try:
            from app.database.mongo_models import MongoNotificationService
            
            # 1. Notices & Emergency Announcements
            if module_key in ("notices", "admission_notices"):
                status = str(clean_data.get("status", "Published")).strip()
                if status.lower() in ("published", "active", ""):
                    title = clean_data.get("title") or "New Campus Notice"
                    prefix = "Update: " if is_update else ""
                    MongoNotificationService.notify_audience(
                        title=f"{prefix}{title}",
                        message=clean_data.get("description", title),
                        category="notice",
                        target_audience=clean_data.get("target_audience", "All Students"),
                        department=clean_data.get("department"),
                        data={
                            "notice_id": item_id,
                            "module": module_key,
                            "priority": clean_data.get("priority", "Normal"),
                            "is_urgent": bool(clean_data.get("is_urgent", False))
                        },
                        link="/student/chat"
                    )
                    MongoNotificationService.notify_admins(
                        title=f"{'Notice Updated' if is_update else 'Notice Published'}: {title}",
                        message=clean_data.get("description", title),
                        category="notice",
                        data={"notice_id": item_id, "module": module_key},
                        link="/admin/notices"
                    )

            # 2. College & Sports Events
            elif module_key in ("events", "sports_events"):
                status = str(clean_data.get("status", "Upcoming")).strip().lower()
                if status in ("upcoming", "ongoing", "active", ""):
                    ev_name = clean_data.get("event_name") or clean_data.get("title") or "College Event"
                    ev_date = clean_data.get("event_date", "")
                    ev_venue = clean_data.get("venue", "Campus")
                    prefix = "Event Update: " if is_update else "New Event: "
                    MongoNotificationService.notify_audience(
                        title=f"{prefix}{ev_name}",
                        message=f"{clean_data.get('category', 'College Event')} on {ev_date} at {ev_venue}." if ev_date else f"Event scheduled at {ev_venue}.",
                        category="event",
                        target_audience="All Students",
                        department=clean_data.get("department"),
                        data={
                            "event_id": item_id,
                            "module": module_key,
                            "event_date": ev_date,
                            "venue": ev_venue
                        },
                        link="/student/chat"
                    )
                    MongoNotificationService.notify_admins(
                        title=f"{'Event Updated' if is_update else 'Event Published'}: {ev_name}",
                        message=f"{clean_data.get('category', 'College Event')} on {ev_date} at {ev_venue}." if ev_date else f"Event scheduled at {ev_venue}.",
                        category="event",
                        data={"event_id": item_id, "module": module_key},
                        link="/admin/events"
                    )

            # 3. Timetable Schedules
            elif module_key == "timetable":
                subj = clean_data.get("subject", "Class Schedule")
                sem = clean_data.get("semester", "")
                div = clean_data.get("division", "")
                day = clean_data.get("day", "")
                time_str = clean_data.get("start_time", "")
                room = clean_data.get("room", "")
                prefix = "Timetable Update: " if is_update else "Timetable Schedule: "
                MongoNotificationService.notify_audience(
                    title=f"{prefix}{subj}",
                    message=f"{subj} on {day} at {time_str} in Room {room} (Sem {sem} Div {div}).",
                    category="academic",
                    target_audience=clean_data.get("department", "All Students"),
                    department=clean_data.get("department"),
                    semester=sem,
                    data={
                        "schedule_id": item_id,
                        "subject": subj,
                        "room": room,
                        "day": day,
                        "time": time_str
                    },
                    link="/student/chat"
                )

            # 4. Academic Documents
            elif module_key in ("academic_documents", "admission_documents"):
                doc_title = clean_data.get("title", "Academic Document")
                cat = clean_data.get("category", clean_data.get("document_type", "Document"))
                dept = clean_data.get("department")
                prefix = "Updated Document: " if is_update else "New Document: "
                MongoNotificationService.notify_audience(
                    title=f"{prefix}{doc_title}",
                    message=f"{cat} has been published for {dept or 'all students'}.",
                    category="academic",
                    target_audience="All Students",
                    department=dept,
                    data={
                        "document_id": item_id,
                        "file_url": clean_data.get("file_url")
                    },
                    link=clean_data.get("file_url") or "/student/chat"
                )

            # 5. Placement Drives
            elif module_key == "placements":
                status = str(clean_data.get("status", "Upcoming")).strip().lower()
                if status in ("upcoming", "registration open", "in progress", ""):
                    company = clean_data.get("company_name", "Placement Drive")
                    role = clean_data.get("job_role", "Position")
                    pkg = clean_data.get("package_lpa", "")
                    date_str = clean_data.get("drive_date", "")
                    prefix = "Placement Update: " if is_update else "Placement Drive: "
                    MongoNotificationService.notify_audience(
                        title=f"{prefix}{company}",
                        message=f"{role} (Package: {pkg} LPA). Date: {date_str}.",
                        category="placement",
                        target_audience="All Students",
                        department=clean_data.get("department"),
                        data={
                            "placement_id": item_id,
                            "company_name": company,
                            "package_lpa": pkg
                        },
                        link="/student/chat"
                    )
        except Exception as notif_err:
            logger.warning(f"Notice/Notification dispatch notice: {notif_err}")

    @staticmethod
    def update_item(module_key: str, item_id: str, data: Dict[str, Any], admin_user: Any = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Updates an existing record with audit fields (updated_by, updated_at).
        Handles document version incrementing and RAG re-indexing on file change.
        """
        initialize_datasets_if_needed()
        module_key = AdminCRUDService.resolve_module_key(module_key)
        config = MODULE_CONFIGS.get(module_key)
        if not config:
            return False, f"Unknown module '{module_key}'", None

        existing = AdminCRUDService.get_item(module_key, item_id)
        if not existing:
            return False, f"Record with ID '{item_id}' not found.", None

        clean_data = dict(data)
        clean_data.pop("_id", None)
        id_field = config["id_field"]

        # Prevent altering primary keys if not allowed
        clean_data["id"] = existing["id"]
        clean_data[id_field] = existing.get(id_field, item_id)

        # Preserve created_at and created_by
        clean_data["created_at"] = existing.get("created_at", datetime.utcnow().isoformat())
        clean_data["created_by"] = existing.get("created_by", "admin")

        # Update audit
        now = datetime.utcnow()
        clean_data["updated_at"] = now.isoformat()
        username = getattr(admin_user, "username", "admin") if admin_user else "admin"
        clean_data["updated_by"] = username

        # Handle File Replacement & RAG Re-indexing if file_url changed
        old_file_url = existing.get("file_url")
        new_file_url = clean_data.get("file_url")

        if (module_key in ("academic_documents", "admission_documents") or new_file_url) and new_file_url:
            full_metadata = dict(existing)
            full_metadata.update(clean_data)

            if old_file_url and old_file_url != new_file_url:
                # Document was replaced with a new file
                full_metadata["version"] = int(existing.get("version", 1)) + 1
                clean_data["version"] = full_metadata["version"]
                try:
                    from app.ai.document_processor import remove_document_from_rag
                    remove_document_from_rag(item_id)
                except Exception:
                    pass

            file_path = AdminCRUDService._resolve_file_path_from_url(new_file_url)
            if file_path and os.path.exists(file_path):
                try:
                    from app.ai.document_processor import process_and_index_document
                    rag_ok, rag_msg, chunk_count, stats = process_and_index_document(
                        document_id=item_id,
                        file_path=file_path,
                        doc_metadata=full_metadata
                    )
                    if rag_ok:
                        clean_data["rag_status"] = "INDEXED"
                        clean_data["chunk_count"] = chunk_count
                        clean_data["page_count"] = stats.get("page_count", 1)
                        clean_data["indexed_at"] = stats.get("indexed_at")
                        clean_data["file_hash"] = stats.get("file_hash")
                        clean_data["error_message"] = ""
                    else:
                        clean_data["rag_status"] = "FAILED"
                        clean_data["error_message"] = rag_msg
                except Exception as rag_err:
                    clean_data["rag_status"] = "FAILED"
                    clean_data["error_message"] = str(rag_err)

        # Update in MongoDB or local store
        coll = AdminCRUDService._resolve_coll(module_key)
        if coll is not None:
            try:
                from bson import ObjectId
                coll.update_one(
                    {"$or": [{"id": item_id}, {id_field: item_id}, {"_id": ObjectId(item_id) if ObjectId.is_valid(item_id) else None}]},
                    {"$set": clean_data}
                )
                AdminCRUDService._dispatch_admin_action_notification(module_key, item_id, clean_data, is_update=True)
                updated = AdminCRUDService.get_item(module_key, item_id)
                return True, "Record updated successfully.", updated
            except Exception as e:
                return False, f"Database error updating item: {str(e)}", None
        else:
            if module_key in _LOCAL_DATA_STORE and item_id in _LOCAL_DATA_STORE[module_key]:
                _LOCAL_DATA_STORE[module_key][item_id].update(clean_data)
            else:
                _LOCAL_DATA_STORE.setdefault(module_key, {})[item_id] = clean_data
            AdminCRUDService._dispatch_admin_action_notification(module_key, item_id, clean_data, is_update=True)
            return True, "Record updated successfully.", clean_data

    @staticmethod
    def delete_item(module_key: str, item_id: str) -> Tuple[bool, str]:
        """Deletes a record by its primary ID and cleans up RAG vectors and files."""
        initialize_datasets_if_needed()
        module_key = AdminCRUDService.resolve_module_key(module_key)
        config = MODULE_CONFIGS.get(module_key)
        if not config:
            return False, f"Unknown module '{module_key}'"

        existing = AdminCRUDService.get_item(module_key, item_id)
        if not existing:
            return False, f"Record with ID '{item_id}' not found."

        # 1. Clean up RAG vector index
        if module_key in ("academic_documents", "admission_documents") or existing.get("file_url"):
            try:
                from app.ai.document_processor import remove_document_from_rag
                remove_document_from_rag(item_id)
            except Exception:
                pass

        # 2. Clean up uploaded physical file
        if existing.get("file_url"):
            try:
                from app.utils.file_upload import delete_uploaded_file
                delete_uploaded_file(existing.get("file_url"))
            except Exception:
                pass

        id_field = config["id_field"]
        coll = AdminCRUDService._resolve_coll(module_key)
        if coll is not None:
            from bson import ObjectId
            res = coll.delete_one({
                "$or": [
                    {"id": item_id},
                    {id_field: item_id},
                    {"_id": ObjectId(item_id) if ObjectId.is_valid(item_id) else None}
                ]
            })
            if res.deleted_count > 0:
                return True, "Record deleted successfully."
            return False, f"Record with ID '{item_id}' not found."
        else:
            module_data = _LOCAL_DATA_STORE.get(module_key, {})
            if item_id in module_data:
                del module_data[item_id]
                return True, "Record deleted successfully."
            return False, f"Record with ID '{item_id}' not found."

    @staticmethod
    def reindex_document(module_key: str, item_id: str, admin_user: Any = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Re-indexes an existing document: flushes old chunks, extracts text,
        chunks, generates embeddings, stores new vectors, and updates metadata.
        """
        existing = AdminCRUDService.get_item(module_key, item_id)
        if not existing:
            return False, f"Document '{item_id}' not found.", None

        file_url = existing.get("file_url")
        file_path = AdminCRUDService._resolve_file_path_from_url(file_url)

        if not file_path or not os.path.exists(file_path):
            existing["rag_status"] = "FAILED"
            existing["error_message"] = "Physical document file not found on server."
            AdminCRUDService.update_item(module_key, item_id, existing, admin_user=admin_user)
            return False, "Physical document file not found on server.", existing

        try:
            from app.ai.document_processor import process_and_index_document
            rag_ok, rag_msg, chunk_count, stats = process_and_index_document(
                document_id=item_id,
                file_path=file_path,
                doc_metadata=existing
            )

            if rag_ok:
                existing["rag_status"] = "INDEXED"
                existing["chunk_count"] = chunk_count
                existing["page_count"] = stats.get("page_count", 1)
                existing["indexed_at"] = stats.get("indexed_at")
                existing["file_hash"] = stats.get("file_hash")
                existing["error_message"] = ""
                AdminCRUDService.update_item(module_key, item_id, existing, admin_user=admin_user)
                return True, f"Document re-indexed successfully with {chunk_count} chunks.", existing
            else:
                existing["rag_status"] = "FAILED"
                existing["error_message"] = rag_msg
                AdminCRUDService.update_item(module_key, item_id, existing, admin_user=admin_user)
                return False, rag_msg, existing

        except Exception as e:
            existing["rag_status"] = "FAILED"
            existing["error_message"] = str(e)
            AdminCRUDService.update_item(module_key, item_id, existing, admin_user=admin_user)
            return False, f"Re-indexing failed: {str(e)}", existing

    @staticmethod
    def get_stats_for_admin(admin_user: Any) -> Dict[str, Any]:
        """
        Aggregates dashboard counts and metrics customized strictly for the logged-in admin role.
        """
        initialize_datasets_if_needed()
        from app.auth.rbac import ROLE_SUPER_ADMIN, normalize_role

        user_role = normalize_role(getattr(admin_user, "role", ""))
        stats: Dict[str, Any] = {
            "role": user_role,
            "role_display": getattr(admin_user, "role_display", "Admin"),
            "counters": {},
            "urgent_notices": [],
            "recent_items": []
        }

        # Helper to get collection count
        def get_count(coll_name: str) -> int:
            coll = get_collection(coll_name)
            if coll is not None:
                try:
                    return coll.count_documents({})
                except Exception:
                    pass
            if coll_name == "students":
                try:
                    from app.database.models.student import Student
                    if Student:
                        return Student.query.count()
                except Exception:
                    pass
            return len(_LOCAL_DATA_STORE.get(coll_name, {}))

        # Always fetch urgent notices for alert banner and recent notices table
        notices_res = AdminCRUDService.list_items("notices", filters={"is_urgent": True, "status": "Published"}, limit=5)
        stats["urgent_notices"] = notices_res.get("items", [])
        
        recent_notices_res = AdminCRUDService.list_items("notices", limit=5)
        stats["recent_notices"] = recent_notices_res.get("items", [])

        def get_pending_count():
            coll = get_collection("students")
            if coll is not None:
                try:
                    return coll.count_documents({"status": "pending"})
                except Exception:
                    pass
            try:
                from app.database.models.student import Student
                if Student and hasattr(Student, 'status'):
                    return Student.query.filter_by(status="pending").count()
            except Exception:
                pass
            return sum(1 for s in _LOCAL_DATA_STORE.get("students", {}).values() if s.get("status") == "pending")

        pending_count = get_pending_count()
        stats["pending_registrations"] = pending_count

        # 1. Bus Admin stats
        if user_role == "bus_admin":
            transport_count = get_count("transport")
            stats["counters"] = {
                "total_routes": transport_count,
                "active_buses": transport_count,
                "total_stops": transport_count,
                "daily_departures": transport_count
            }

        # 2. Sports Admin stats
        elif user_role == "sports_admin":
            stats["counters"] = {
                "total_sports": get_count("sports"),
                "tournaments": get_count("sports_events"),
                "grounds_courts": get_count("grounds"),
                "active_coaches": 0
            }

        # 3. Event Admin stats
        elif user_role == "event_admin":
            events_count = get_count("events")
            stats["counters"] = {
                "total_events": events_count,
                "upcoming_events": events_count,
                "workshops_seminars": events_count,
                "hackathons": 0
            }

        # 4. Library Admin stats
        elif user_role == "library_admin":
            stats["counters"] = {
                "total_books": get_count("library_books"),
                "registered_members": get_count("library_members"),
                "active_loans": get_count("library_issue_return"),
                "e_resources": 0
            }

        # 5. Canteen Admin stats
        elif user_role == "canteen_admin":
            canteen_count = get_count("canteen")
            stats["counters"] = {
                "menu_items": canteen_count,
                "available_items": canteen_count,
                "food_stalls": 1 if canteen_count > 0 else 0,
                "daily_orders": 0
            }

        # 6. Academic Admin stats
        elif user_role == "academic_admin":
            stats["counters"] = {
                "total_students": get_count("students"),
                "pending_registrations": pending_count,
                "faculty_members": get_count("faculty"),
                "subjects": get_count("subjects"),
                "academic_documents": get_count("academic_documents")
            }

        # 7. Admission Admin stats
        elif user_role == "admission_admin":
            stats["counters"] = {
                "programs_offered": get_count("admission_info"),
                "admission_docs": get_count("admission_documents"),
                "admission_notices": get_count("admission_notices"),
                "applications": 0
            }

        # 8. Notice Admin stats
        elif user_role == "notice_admin":
            stats["counters"] = {
                "total_notices": get_count("notices"),
                "urgent_alerts": len(stats["urgent_notices"]),
                "departments": 7,
                "published_today": len(stats["urgent_notices"])
            }

        # 9. Super Admin stats
        else:
            stats["counters"] = {
                "total_students": get_count("students"),
                "pending_registrations": pending_count,
                "faculty_members": get_count("faculty"),
                "active_notices": get_count("notices"),
                "library_books": get_count("library_books"),
                "bus_routes": get_count("transport"),
                "events_count": get_count("events")
            }

        return stats
