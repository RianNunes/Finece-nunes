"""Verify disposable storage uploads are soft-deleted; never touch admin or finance data."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv('/app/backend/.env')
with MongoClient(os.environ['MONGO_URL']) as client:
    db = client[os.environ['DB_NAME']]
    users = list(db.users.find({'email': {'$regex':'^test_storage_(owner|other)_'}}, {'_id':1,'email':1}))
    ids = [str(u['_id']) for u in users]
    docs = list(db.files.find({'user_id': {'$in': ids}}, {'_id':0,'storage_path':0,'user_id':0}))
    active = [d for d in docs if not d['is_deleted']]
    inventory = {'disposable_accounts':len(users), 'provider_objects_retained':len(docs), 'active_test_uploads':len(active),
                 'test_files': [{'id':d['id'],'name':d['original_filename'],'is_deleted':d['is_deleted']} for d in docs]}
    Path('/app/test_reports/storage_cleanup_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2))
    print({k:v for k,v in inventory.items() if k!='test_files'})
    assert not active, 'Cleanup incomplete'