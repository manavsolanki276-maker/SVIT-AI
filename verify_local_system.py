"""
Local Verification Script for SVIT AI Notification System & UI Integrity.
"""
import os
import sys

os.environ['TESTING'] = 'True'
from app import create_app
from app.database.mongodb import get_mongodb_db, get_mongodb_client
from app.database.mongo_models import MongoNotificationService, MongoStudentService, MongoAdminService
from app.database.admin_crud_service import AdminCRUDService

def run_verifications():
    print("=== STARTING LOCAL SYSTEM VERIFICATION ===")
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        # 1. Verify MongoDB Atlas Connection
        print("[1/6] Testing MongoDB Atlas Connection...")
        db = get_mongodb_db()
        if db is None:
            print("❌ MongoDB connection failed.")
            sys.exit(1)
        print(f"✅ Connected to MongoDB Atlas DB: {db.name}")
        
        # Check students, admins, notifications collections
        student_count = db['students'].count_documents({})
        admin_count = db['admins'].count_documents({})
        notif_count = db['notifications'].count_documents({})
        print(f"📊 Counts in DB -> Students: {student_count}, Admins: {admin_count}, Notifications: {notif_count}")
        
        # 2. Test Real Data Notification Flow
        print("[2/6] Testing Real Data Notification Flow (Admin Action -> MongoDB -> Student API)...")
        test_title = f"Automated Notice Verification"
        
        # Dispatch notification through AdminCRUDService
        AdminCRUDService._dispatch_admin_action_notification(
            module_key="notices",
            item_id="test_notice_1",
            clean_data={
                "title": test_title,
                "description": "Notice created during system verification.",
                "target_audience": "All Students",
                "department": "Computer Engineering"
            },
            is_update=False
        )
        
        # Query MongoDB collection directly to prove real storage
        doc = db['notifications'].find_one({"title": test_title})
        assert doc is not None, "Notification was not saved in MongoDB!"
        notif_id = str(doc["_id"])
        print(f"✅ Notification found in MongoDB Atlas with ID: {notif_id}")
        
        # 3. Test Student Notification Retrieval & Isolation
        print("[3/6] Testing Student Notification Retrieval & Security Isolation...")
        test_student_user = MongoStudentService.find_by_enrollment("220101")
        if not test_student_user:
            # Create a mock object with real student credentials for retrieval test
            class StudentObj:
                id = "student_220101"
                enrollment_no = "220101"
                department = "Computer Engineering"
                semester = 4
                is_admin = False
                status = "active"
                is_authenticated = True
            test_student_user = StudentObj()
            
        res = MongoNotificationService.get_notifications(test_student_user)
        assert res["status"] == "success", "Failed to retrieve student notifications."
        found = any(n["title"] == test_title for n in res["notifications"])
        assert found, "Created notification not returned in student query!"
        print(f"✅ Student successfully retrieved notification with unread count: {res['unread_count']}")
        
        # 4. Test Mark Read & Persistence
        print("[4/6] Testing Mark Read & State Persistence...")
        ok = MongoNotificationService.mark_read(notif_id, test_student_user)
        assert ok, "Failed to mark notification read."
        
        # Verify in DB
        updated_doc = db['notifications'].find_one({"_id": doc["_id"]})
        assert "220101" in updated_doc.get("read_by", []) or updated_doc.get("is_read") == True, "Read state was not persisted in MongoDB!"
        print("✅ Read state persisted in MongoDB Atlas read_by array.")
        
        # Clean up test verification document
        db['notifications'].delete_one({"_id": doc["_id"]})
        print("✅ Test document cleaned up from MongoDB.")
        
        # 5. Test HTTP Endpoints via Test Client
        print("[5/6] Testing HTTP Routes & Role Blocking...")
        client = app.test_client()
        
        # Public routes
        r_home = client.get('/')
        assert r_home.status_code in [200, 302], f"Unexpected / status: {r_home.status_code}"
        
        r_login = client.get('/login')
        assert r_login.status_code == 200, f"Unexpected /login status: {r_login.status_code}"
        
        # Unauthenticated access to protected routes
        r_notif = client.get('/notifications')
        assert r_notif.status_code == 302, "Unauthenticated /notifications not redirected!"
        
        r_admin = client.get('/admin/dashboard')
        assert r_admin.status_code == 302, "Unauthenticated /admin/dashboard not redirected!"
        
        print("✅ Public and protected route security verified.")
        
        # 6. Verify Mobile Sidebar CSS / Structure
        print("[6/6] Checking Mobile Sidebar & CSS Specifications...")
        with open('app/static/css/student/chat.css', 'r', encoding='utf-8') as f:
            chat_css = f.read()
        assert 'height: 100dvh;' in chat_css, "Missing 100dvh in chat.css"
        assert 'safe-area-inset-bottom' in chat_css, "Missing safe-area-inset-bottom in chat.css"
        assert 'drawer-bottom-actions' in chat_css, "Missing drawer-bottom-actions in chat.css"
        print("✅ Mobile CSS layout specifications verified.")
        
    print("\n🎉 ALL LOCAL SYSTEM VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_verifications()
