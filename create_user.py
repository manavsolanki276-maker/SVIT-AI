from app import create_app, db
from app.database.models import Student

app = create_app()

with app.app_context():
    db.create_all()

    enrollment = '210010116001'
    email = 'manav@svit.ac.in'
    password = 'student123'

    # 1. Query for existing student record
    student = Student.query.filter(
        (Student.enrollment_no == enrollment) | (Student.email == email)
    ).first()

    if not student:
        # Create fresh student record
        student = Student()
        if hasattr(student, 'enrollment_no'):
            student.enrollment_no = enrollment
        if hasattr(student, 'email'):
            student.email = email
        if hasattr(student, 'full_name'):
            student.full_name = 'Manav Solanki'
        if hasattr(student, 'name'):
            student.name = 'Manav Solanki'
        if hasattr(student, 'department'):
            student.department = 'Computer Engineering'
        if hasattr(student, 'semester'):
            student.semester = 1

        if hasattr(student, 'set_password'):
            student.set_password(password)
        else:
            student.password = password

        if hasattr(student, 'is_profile_completed'):
            student.is_profile_completed = True

        db.session.add(student)
        print("\n✅ New student created successfully!")
    else:
        # Overwrite and reset password for existing record
        print(f"\n🔄 Updating existing student record for '{email}'...")
        if hasattr(student, 'enrollment_no'):
            student.enrollment_no = enrollment
        if hasattr(student, 'email'):
            student.email = email
        if hasattr(student, 'full_name'):
            student.full_name = 'Manav Solanki'
        if hasattr(student, 'name'):
            student.name = 'Manav Solanki'
        if hasattr(student, 'department'):
            student.department = 'Computer Engineering'
        if hasattr(student, 'is_profile_completed'):
            student.is_profile_completed = True

        # Refresh password hash
        if hasattr(student, 'set_password'):
            student.set_password(password)
        else:
            student.password = password

    db.session.commit()

    print("------------------------------------")
    print(f"Enrollment No : {enrollment}")
    print(f"Email         : {email}")
    print(f"Password      : {password}")
    print("------------------------------------\n")