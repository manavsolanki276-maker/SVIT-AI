import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.mongodb import get_collection

notices_coll = get_collection('notices')
events_coll = get_collection('events')
notif_coll = get_collection('notifications')

print("Notices count in MongoDB:", notices_coll.count_documents({}) if notices_coll is not None else "None")
if notices_coll is not None:
    one_notice = notices_coll.find_one({}, {'_id': 0})
    print("Sample notice keys:", list(one_notice.keys()) if one_notice else "Empty")
    if one_notice:
        print("Sample notice:", {k: one_notice[k] for k in list(one_notice.keys())[:8]})

print("Events count in MongoDB:", events_coll.count_documents({}) if events_coll is not None else "None")
if events_coll is not None:
    one_event = events_coll.find_one({}, {'_id': 0})
    print("Sample event keys:", list(one_event.keys()) if one_event else "Empty")
    if one_event:
        print("Sample event:", {k: one_event[k] for k in list(one_event.keys())[:8]})

print("Notifications count in MongoDB:", notif_coll.count_documents({}) if notif_coll is not None else "None")
