"""Reject signature-only corrupt images, using real storage and a disposable authenticated user."""
import json
import os
from pathlib import Path
import pytest
import requests
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'


def test_corrupt_png_with_signature():
    s = requests.Session()
    creds = json.loads(Path('/app/test_reports/storage_user.json').read_text())
    r = s.post(API+'/auth/login',json=creds,timeout=30)
    if r.status_code != 200:
        pytest.skip('Disposable storage account unavailable')
    r = s.post(API+'/files',files={'file':('TEST_corrupt_signature.png',b'\x89PNG\r\n\x1a\nthis is not an image')},timeout=150)
    try:
        assert r.status_code == 415, f'Corrupt PNG accepted: status {r.status_code}, {r.text}'
        assert isinstance(r.json()['detail'],str)
    finally:
        if r.status_code == 201:
            assert s.delete(API+'/files/'+r.json()['id']).status_code == 204