"""Targeted real storage fixtures, image integrity, download bytes and cache protection."""
import io
import json
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from PIL import Image
from pypdf import PdfReader, PdfWriter

load_dotenv('/app/frontend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'
ROOT = Path('/app/test_reports/iter5_assets')
MANIFEST = Path('/app/test_reports/iter5_fixtures.json')


def tiny_pdf():
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for index in (1, 2):
        if index == 2:
            objects.append(b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>')
        stream = f'BT /F1 18 Tf 20 110 Td (TEST readable page {index}) Tj ET'.encode()
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    data = b'%PDF-1.4\n'; offsets = []
    for n, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += f'{n} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(data)
    data += f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    data += b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets)
    data += f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return data


@pytest.fixture(scope='module')
def fixtures():
    session = requests.Session()
    creds = json.loads(Path('/app/test_reports/storage_user.json').read_text())
    login = session.post(API+'/auth/login', json=creds, timeout=30)
    if login.status_code != 200:
        pytest.skip('Existing disposable owner login unavailable')
    ROOT.mkdir(exist_ok=True)
    pdf = tiny_pdf()
    writer = PdfWriter(); writer.append(PdfReader(io.BytesIO(pdf))); writer.encrypt('TEST_pdf_password')
    encrypted = io.BytesIO(); writer.write(encrypted)
    png = io.BytesIO(); Image.new('RGB', (120, 80), (40, 180, 120)).save(png, format='PNG')
    assets = {'TEST_iter5_readable.pdf': pdf, 'TEST_iter5_password.pdf': encrypted.getvalue(),
              'TEST_iter5_corrupt.pdf': b'%PDF-1.4\nnot a PDF document\n%%EOF',
              'TEST_iter5_image.png': png.getvalue(), 'TEST_iter5_deleted.txt': b'TEST real preview download error'}
    records = []
    for name, data in assets.items():
        (ROOT/name).write_bytes(data)
        result = session.post(API+'/files', files={'file': (name, data)}, timeout=150)
        assert result.status_code == 201, result.text
        records.append(result.json())
        MANIFEST.write_text(json.dumps(records, indent=2))
    # Retain exactly these five fixtures for browser regression; explicitly clean afterward.
    return session, records, assets


def test_valid_image_roundtrip(fixtures):
    session, records, assets = fixtures
    record = next(r for r in records if r['kind'] == 'image')
    result = session.get(API+f"/files/{record['id']}/download", timeout=150)
    assert result.status_code == 200 and result.content == assets[record['original_filename']]
    assert record['content_type'] == 'image/png' and record['size'] == len(result.content)
    listing = session.get(API+'/files', timeout=30).json()
    assert record in listing['items']


def test_pdf_roundtrip_and_cache(fixtures):
    session, records, assets = fixtures
    for record in records:
        result = session.get(API+f"/files/{record['id']}/download", timeout=150)
        assert result.status_code == 200 and result.content == assets[record['original_filename']]
        assert 'no-store' in {s.strip().lower() for s in result.headers['Cache-Control'].split(',')}
        assert result.headers['X-Content-Type-Options'] == 'nosniff'
        assert {'cookie','authorization'} <= {s.strip().lower() for s in result.headers['Vary'].split(',')}
    assert len(PdfReader(io.BytesIO(assets['TEST_iter5_readable.pdf'])).pages) == 2