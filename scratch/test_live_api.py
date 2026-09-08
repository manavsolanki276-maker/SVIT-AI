import requests

session = requests.Session()
base_url = 'https://svit-ai.vercel.app'

print("=== STEP 1: TEST ADMIN LOGIN ON LIVE VERCEL ===")
login_res = session.post(f'{base_url}/admin/login', json={
    'identifier': 'superadmin',
    'password': 'Admin@123'
}, headers={'Accept': 'application/json'})

print('Admin Login Status:', login_res.status_code, login_res.text[:120])

print("\n=== STEP 2: TEST NOTICES API ON LIVE VERCEL ===")
notices_res = session.get(f'{base_url}/admin/api/crud/notices?page=1&per_page=5')
print('Notices API Status:', notices_res.status_code)
if notices_res.status_code == 200:
    nd = notices_res.json()
    print(f'Total Notices in Live: {nd.get("total")}, Received: {len(nd.get("items", []))}')
    for it in nd.get('items', [])[:3]:
        print(f'  - [{it.get("id")}] {it.get("title")} ({it.get("priority")})')

print("\n=== STEP 3: TEST EVENTS API ON LIVE VERCEL ===")
events_res = session.get(f'{base_url}/admin/api/crud/events?page=1&per_page=5')
print('Events API Status:', events_res.status_code)
if events_res.status_code == 200:
    ed = events_res.json()
    print(f'Total Events in Live: {ed.get("total")}, Received: {len(ed.get("items", []))}')
    for it in ed.get('items', [])[:3]:
        print(f'  - [{it.get("id")}] {it.get("event_name")} ({it.get("category")})')

print("\n=== STEP 4: TEST STUDENT LOGIN AND NOTIFICATIONS ON LIVE VERCEL ===")
student_session = requests.Session()
stud_login_res = student_session.post(f'{base_url}/auth/login', json={
    'identifier': '210410107001',
    'password': 'Student@123'
}, headers={'Accept': 'application/json'})

print('Student Login Status:', stud_login_res.status_code, stud_login_res.text[:120])

stud_notifs = student_session.get(f'{base_url}/api/notifications')
print('Student Notifications API Status:', stud_notifs.status_code)
if stud_notifs.status_code == 200:
    s_data = stud_notifs.json()
    print(f'Notifications Count: {len(s_data.get("notifications", []))}, Unread: {s_data.get("unread_count")}')
    for n in s_data.get('notifications', [])[:5]:
        print(f'  * [{n.get("category")}] {n.get("title")}')

print("\n=== LIVE TESTING COMPLETED ===")
