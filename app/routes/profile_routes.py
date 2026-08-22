"""
app/routes/profile_routes.py
User Profile Management and First-Time Onboarding Routes with Direct DB Loading,
Program/Course filtering, Edit Profile functionality, and full attribute resolution for RAG personalization.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required

try:
    from app.extensions import db
except ImportError:
    from app import db

# Safe model imports
try:
    from app.database.models import Student
except ImportError:
    try:
        from app.models.student import Student
    except ImportError:
        Student = None

profile_bp = Blueprint('profile', __name__, url_prefix='/student/profile')


def get_fresh_student():
    """Fetches the active student record directly from the database (MongoDB or SQLite) to ensure fresh state."""
    if not current_user.is_authenticated:
        return None

    from app.database.mongo_models import MongoStudent
    
    # 1. Try by ID from MongoDB
    raw_id = getattr(current_user, 'id', None)
    if raw_id:
        int_id = str(raw_id).split('_')[-1]
        mongo_user = MongoStudent.get_by_id(int_id)
        if mongo_user:
            return mongo_user

    # 2. Try by Enrollment Number from MongoDB
    enrollment = getattr(current_user, 'enrollment_no', getattr(current_user, 'enrollment_number', None))
    if enrollment:
        mongo_user = MongoStudent.find_by_identifier(enrollment)
        if mongo_user:
            return mongo_user

    # 3. Try by Email from MongoDB
    email = getattr(current_user, 'email', None)
    if email:
        mongo_user = MongoStudent.find_by_identifier(email)
        if mongo_user:
            return mongo_user

    # SQLite fallback
    if Student:
        if raw_id:
            try:
                int_id = int(str(raw_id).split('_')[-1])
                db_user = Student.query.get(int_id)
                if db_user:
                    return db_user
            except (ValueError, TypeError):
                pass

        if enrollment:
            db_user = Student.query.filter_by(enrollment_no=enrollment).first()
            if db_user:
                return db_user

        if email:
            db_user = Student.query.filter_by(email=email).first()
            if db_user:
                return db_user

    return current_user



# =========================================================
# 1. MY PROFILE PAGE (VIEW & EDIT)
# =========================================================
@profile_bp.route('/', methods=['GET'])
@profile_bp.route('', methods=['GET'])
@login_required
def profile_page():
    """Renders the comprehensive profile view and edit page with all saved student details."""
    student = get_fresh_student()

    full_name = getattr(student, 'full_name', None) or getattr(student, 'name', '') or ''
    email = getattr(student, 'email', '') or ''
    phone = getattr(student, 'phone', None) or getattr(student, 'mobile_no', None) or getattr(student, 'contact', '') or ''
    enrollment = getattr(student, 'enrollment_no', None) or getattr(student, 'enrollment_number', None) or getattr(student, 'student_id', '')
    program = getattr(student, 'program', '') or 'BE'
    department = getattr(student, 'department', '') or 'Computer Engineering'
    semester = getattr(student, 'semester', None) or 3
    division = getattr(student, 'division', '') or 'A'
    batch = getattr(student, 'batch', '') or 'A1'
    gender = getattr(student, 'gender', '') or 'Male'

    return render_template(
        'student/profile.html',
        student=student,
        user=student,
        full_name=full_name,
        email=email,
        phone=phone,
        enrollment=enrollment,
        program=program,
        department=department,
        semester=semester,
        division=division,
        batch=batch,
        gender=gender
    )


# =========================================================
# 2. COMPLETE PROFILE (FIRST-TIME ONBOARDING)
# =========================================================
@profile_bp.route('/complete', methods=['GET', 'POST'])
@login_required
def complete_profile():
    """Handles first-time profile completion right after student login."""
    student = get_fresh_student()

    # If profile is already completed, send student directly to chat
    is_done = getattr(student, 'is_profile_complete', getattr(student, 'is_profile_completed', False))
    if is_done:
        return redirect('/')

    if request.method == 'POST':
        data = request.form or request.get_json() or {}

        full_name = data.get('full_name', '').strip()
        enrollment_no = data.get('enrollment_no', '').strip()
        program = data.get('program', '').strip()
        department = data.get('department', '').strip()
        semester = data.get('semester', '').strip()
        division = data.get('division', '').strip()
        batch = data.get('batch', '').strip()
        phone = data.get('phone', data.get('mobile_no', '')).strip()
        gender = data.get('gender', '').strip()

        try:
            target = student if student is not None else current_user

            if full_name:
                if hasattr(target, 'full_name'):
                    target.full_name = full_name
                if hasattr(target, 'name'):
                    target.name = full_name

            if enrollment_no and hasattr(target, 'enrollment_no'):
                target.enrollment_no = enrollment_no

            if program and hasattr(target, 'program'):
                target.program = program

            if department and hasattr(target, 'department'):
                target.department = department

            if semester:
                try:
                    target.semester = int(semester)
                except (ValueError, TypeError):
                    target.semester = semester

            if division and hasattr(target, 'division'):
                target.division = division.upper()

            if batch and hasattr(target, 'batch'):
                target.batch = batch.upper()

            if phone:
                if hasattr(target, 'phone'):
                    target.phone = phone
                if hasattr(target, 'mobile_no'):
                    target.mobile_no = phone
                if hasattr(target, 'contact'):
                    target.contact = phone

            if gender and hasattr(target, 'gender'):
                target.gender = gender

            if hasattr(target, 'is_profile_completed'):
                target.is_profile_completed = True
            if hasattr(target, 'is_profile_complete'):
                target.is_profile_complete = True

            # Save to MongoDB
            try:
                from app.database.mongo_models import MongoStudent
                profile_dict = {
                    "full_name": getattr(target, 'full_name', getattr(target, 'name', '')),
                    "name": getattr(target, 'full_name', getattr(target, 'name', '')),
                    "enrollment_no": getattr(target, 'enrollment_no', ''),
                    "program": getattr(target, 'program', ''),
                    "department": getattr(target, 'department', ''),
                    "semester": getattr(target, 'semester', 1),
                    "division": getattr(target, 'division', 'A'),
                    "batch": getattr(target, 'batch', 'A1'),
                    "phone": getattr(target, 'phone', getattr(target, 'mobile_no', '')),
                    "gender": getattr(target, 'gender', ''),
                    "is_profile_complete": True,
                    "is_profile_completed": True,
                }
                MongoStudent.save_or_update(profile_dict)
            except Exception as mongo_err:
                pass

            try:
                db.session.add(target)
                db.session.commit()
            except Exception:
                pass

            flash('Profile setup completed successfully! Welcome to SVIT AI Assistant.', 'success')
            return redirect('/')

        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"[Error] Completing student profile: {e}")

            return render_template('student/complete_profile.html', user=student, student=student, error="Failed to save profile. Please try again.")

    return render_template('student/complete_profile.html', user=student, student=student)


# =========================================================
# 3. UPDATE PROFILE API (EDIT PROFILE SAVE)
# =========================================================
@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    """
    Updates student profile in the database and commits changes.
    Subsequent RAG queries immediately reflect the updated details.
    """
    data = request.get_json(silent=True) or request.form or {}

    full_name = str(data.get('full_name', '')).strip()
    program = str(data.get('program', '')).strip()
    department = str(data.get('department', '')).strip()
    semester = str(data.get('semester', '')).strip()
    division = str(data.get('division', '')).strip().upper()
    batch = str(data.get('batch', '')).strip().upper()
    phone = str(data.get('phone', data.get('contact', data.get('mobile_no', '')))).strip()
    gender = str(data.get('gender', '')).strip()

    try:
        target = get_fresh_student()
        if not target:
            return jsonify({"status": "error", "message": "Student record not found."}), 404

        # Update Full Name
        if full_name:
            if hasattr(target, 'full_name'):
                target.full_name = full_name
            if hasattr(target, 'name'):
                target.name = full_name

        # Update Program
        if program and hasattr(target, 'program'):
            target.program = program

        # Update Department
        if department and hasattr(target, 'department'):
            target.department = department

        # Update Semester
        if semester:
            try:
                target.semester = int(semester)
            except (ValueError, TypeError):
                target.semester = semester

        # Update Division & Batch
        if division and hasattr(target, 'division'):
            target.division = division

        if batch and hasattr(target, 'batch'):
            target.batch = batch

        # Update Phone
        if phone:
            if hasattr(target, 'phone'):
                target.phone = phone
            if hasattr(target, 'mobile_no'):
                target.mobile_no = phone
            if hasattr(target, 'contact'):
                target.contact = phone

        # Update Gender
        if gender and hasattr(target, 'gender'):
            target.gender = gender

        # Ensure completion flag remains True
        if hasattr(target, 'is_profile_completed'):
            target.is_profile_completed = True
        if hasattr(target, 'is_profile_complete'):
            target.is_profile_complete = True

        # Save to MongoDB
        try:
            from app.database.mongo_models import MongoStudent
            profile_dict = {
                "full_name": full_name or getattr(target, 'full_name', getattr(target, 'name', '')),
                "name": full_name or getattr(target, 'full_name', getattr(target, 'name', '')),
                "enrollment_no": getattr(target, 'enrollment_no', ''),
                "program": program or getattr(target, 'program', ''),
                "department": department or getattr(target, 'department', ''),
                "semester": int(semester) if str(semester).isdigit() else getattr(target, 'semester', 1),
                "division": division or getattr(target, 'division', 'A'),
                "batch": batch or getattr(target, 'batch', 'A1'),
                "phone": phone or getattr(target, 'phone', getattr(target, 'mobile_no', '')),
                "gender": gender or getattr(target, 'gender', ''),
                "is_profile_complete": True,
                "is_profile_completed": True,
            }
            MongoStudent.save_or_update(profile_dict)
        except Exception:
            pass

        try:
            db.session.add(target)
            db.session.commit()
        except Exception:
            pass

        return jsonify({

            "status": "success",
            "message": "Profile updated successfully.",
            "data": {
                "full_name": full_name,
                "program": getattr(target, 'program', ''),
                "department": department,
                "semester": target.semester,
                "division": target.division,
                "batch": getattr(target, 'batch', ''),
                "phone": phone,
                "gender": gender
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[Error] Updating student profile: {e}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500