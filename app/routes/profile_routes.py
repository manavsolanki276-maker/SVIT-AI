"""
app/routes/profile_routes.py
User Profile Management and First-Time Onboarding Routes with Direct DB Loading and Attribute Resolution.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
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
    """Fetches the active student record directly from the database."""
    if not current_user.is_authenticated:
        return None

    if Student:
        # 1. By ID
        if hasattr(current_user, 'id') and current_user.id:
            db_user = Student.query.get(current_user.id)
            if db_user:
                return db_user

        # 2. By Enrollment Number
        enrollment = getattr(current_user, 'enrollment_no', getattr(current_user, 'enrollment_number', None))
        if enrollment:
            db_user = Student.query.filter_by(enrollment_no=enrollment).first()
            if db_user:
                return db_user

        # 3. By Email
        email = getattr(current_user, 'email', None)
        if email:
            db_user = Student.query.filter_by(email=email).first()
            if db_user:
                return db_user

    return current_user


# =========================================================
# 1. MY PROFILE PAGE (VIEW)
# =========================================================
@profile_bp.route('/', methods=['GET'])
@profile_bp.route('', methods=['GET'])
@login_required
def profile_page():
    """Renders profile view with resolved attributes."""
    student = get_fresh_student()

    full_name = getattr(student, 'full_name', None) or getattr(student, 'name', '') or ''
    phone = getattr(student, 'phone', None) or getattr(student, 'mobile_no', None) or getattr(student, 'contact', '') or ''
    enrollment = getattr(student, 'enrollment_no', None) or getattr(student, 'enrollment_number', None) or getattr(student, 'student_id', '210010116001')
    department = getattr(student, 'department', 'Computer Engineering')
    semester = getattr(student, 'semester', 1)
    division = getattr(student, 'division', '')
    gender = getattr(student, 'gender', 'Male')

    return render_template(
        'student/profile.html',
        student=student,
        user=student,
        full_name=full_name,
        phone=phone,
        enrollment=enrollment,
        department=department,
        semester=semester,
        division=division,
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

    if request.method == 'POST':
        data = request.form or request.get_json() or {}

        full_name = data.get('full_name', '').strip()
        enrollment_no = data.get('enrollment_no', '').strip()
        department = data.get('department', '').strip()
        semester = data.get('semester', '').strip()
        division = data.get('division', '').strip()
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
            if department and hasattr(target, 'department'):
                target.department = department

            if semester:
                try:
                    target.semester = int(semester)
                except (ValueError, TypeError):
                    target.semester = semester

            if division and hasattr(target, 'division'):
                target.division = division

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

            db.session.add(target)
            db.session.commit()

            return redirect('/')
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error completing profile: {e}")
            return render_template('student/complete_profile.html', user=student, student=student, error="Failed to save profile.")

    return render_template('student/complete_profile.html', user=student, student=student)


# =========================================================
# 3. UPDATE PROFILE API (AJAX FROM PROFILE FORM)
# =========================================================
@profile_bp.route('/update', methods=['POST'])
@login_required
def update_profile():
    """Updates student fields and commits changes to the database."""
    data = request.get_json(silent=True) or request.form or {}

    full_name = str(data.get('full_name', '')).strip()
    phone = str(data.get('phone', data.get('contact', data.get('mobile_no', '')))).strip()
    semester = str(data.get('semester', '')).strip()
    division = str(data.get('division', '')).strip()
    gender = str(data.get('gender', '')).strip()

    try:
        target = get_fresh_student()
        if not target:
            return jsonify({"status": "error", "message": "User record not found."}), 404

        # Save Name
        if full_name:
            if hasattr(target, 'full_name'):
                target.full_name = full_name
            if hasattr(target, 'name'):
                target.name = full_name

        # Save Phone
        if phone:
            if hasattr(target, 'phone'):
                target.phone = phone
            if hasattr(target, 'mobile_no'):
                target.mobile_no = phone
            if hasattr(target, 'contact'):
                target.contact = phone

        # Save Semester
        if semester:
            try:
                target.semester = int(semester)
            except (ValueError, TypeError):
                target.semester = semester

        # Save Division & Gender
        if division and hasattr(target, 'division'):
            target.division = division

        if gender and hasattr(target, 'gender'):
            target.gender = gender

        # Mark profile as completed
        if hasattr(target, 'is_profile_completed'):
            target.is_profile_completed = True
        if hasattr(target, 'is_profile_complete'):
            target.is_profile_complete = True

        db.session.add(target)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Profile updated successfully.",
            "data": {
                "full_name": full_name,
                "phone": phone,
                "semester": semester,
                "gender": gender
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error updating profile: {e}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500