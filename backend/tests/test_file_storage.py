"""Real private file storage roundtrips, security, validation, and metadata regression tests."""
import io
import json
import os
import uuid
import wave
from pathlib import Path
from urllib.parse import quote

import pytest
import requests
from dotenv import load_dotenv
from PIL import Image
from openpyxl import Workbook
from pymongo import MongoClient

load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = BASE + '/api'
ASSETS = Path('/app/test_reports/storage_assets')


def make_assets():
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / 'TEST_ação [2026].txt').write_text('Olá, biblioteca privada!\n€ R$ 123,45', encoding='utf-8')
    (ASSETS / 'TEST_dados.csv').write_text('nome,valor\nNunes,123\n', encoding='utf-8')
    Image.new('RGB', (120, 80), (40, 180, 120)).save(ASSETS / 'TEST_imagem.png')
    wb = Workbook(); wb.active.append(['TEST_', 123]); wb.save(ASSETS / 'TEST_planilha.xlsx')
    with wave.open(str(ASSETS / 'TEST_audio.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\x00\x00' * 8000)
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    stream = b'BT /F1 18 Tf 30 100 Td (TEST arquivo privado) Tj ET'
    objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    data = b'%PDF-1.4\n'; offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(data); data += b'xref\n0 6\n0000000000 65535 f \n'
    data += b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets[1:])
    data += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    (ASSETS / 'TEST_documento.pdf').write_bytes(data)


@pytest.fixture(scope='module')
def users():
    sessions = []
    for tag in ('owner', 'other'):
        email = f'TEST_storage_{tag}_{uuid.uuid4().hex[:8]}@test.local'
        password = 'Storage@Test2026'
        s = requests.Session()
        r = s.post(API + '/auth/register', json={'email': email, 'password': password, 'name': 'TEST storage'}, timeout=30)
        assert r.status_code == 200, r.text
        with Path('/app/memory/test_credentials.md').open('a') as out:
            out.write(f'\n## Disposable storage {tag}\n- Email: {email}\n- Password: {password}\n')
        sessions.append(s)
        if tag == 'owner':
            Path('/app/test_reports/storage_user.json').write_text(json.dumps({'email': email, 'password': password, 'id': r.json()['id']}))
    make_assets()
    yield sessions
    for s in sessions:
        r = s.get(API + '/files', params={'page_size':100}, timeout=30)
        if r.status_code == 200:
            for item in r.json()['items']:
                s.delete(API + '/files/' + item['id'], timeout=30)


@pytest.fixture(scope='module')
def uploaded(users):
    records = []
    for path in sorted(ASSETS.iterdir()):
        if not path.is_file(): continue
        r = users[0].post(API + '/files', files={'file': (path.name, path.read_bytes())}, timeout=150)
        assert r.status_code == 201, r.text
        records.append((r.json(), path.read_bytes()))
    return records


def test_real_roundtrip_and_headers(uploaded, users):
    for record, data in uploaded:
        assert set(record) == {'id','original_filename','content_type','kind','size','created_at'}
        assert record['size'] == len(data)
        r = users[0].get(API + f"/files/{record['id']}/download", timeout=150)
        assert r.status_code == 200, r.text
        assert r.content == data
        assert r.headers['X-Content-Type-Options'] == 'nosniff'
        assert r.headers['Content-Disposition'] == "attachment; filename*=UTF-8''" + quote(record['original_filename'], safe='')
    listing = users[0].get(API + '/files').json()
    assert listing['total'] == len(uploaded)
    assert listing['total_size'] == sum(len(data) for _, data in uploaded)
    assert {i['id'] for i in listing['items']} == {r['id'] for r, _ in uploaded}


def test_private_cache_header(uploaded, users):
    r = users[0].get(API + f"/files/{uploaded[0][0]['id']}/download", timeout=150)
    # The preview edge normalizes Cache-Control to no-store, no-cache,
    # must-revalidate. no-store forbids both private and shared caching;
    # requiring the redundant "private" directive would reject a safe response.
    directives = {value.strip().lower() for value in r.headers['Cache-Control'].split(',')}
    assert 'no-store' in directives


def test_unauthenticated_endpoints():
    s = requests.Session()
    for method, path, kwargs in [('GET','',{}), ('GET','/config',{}), ('POST','',{'files':{'file':('TEST.txt',b'ok')}}), ('GET','/missing/download',{}), ('DELETE','/missing',{})]:
        r = s.request(method, API + '/files' + path, timeout=30, **kwargs)
        assert r.status_code == 401, (path, r.text)
        assert r.json()['detail'] == 'Não autenticado'


def test_cross_user_isolation(uploaded, users):
    listing = users[1].get(API + '/files').json()
    assert listing['items'] == [] and listing['total_size'] == 0
    for record, _ in uploaded:
        for method, tail in [('GET','/download'), ('DELETE','')]:
            r = users[1].request(method, API + '/files/' + record['id'] + tail, timeout=30)
            assert r.status_code == 404 and r.json()['detail'] == 'Arquivo não encontrado.'


def test_origin_mutations(uploaded, users):
    for method, path, kwargs in [('POST','',{'files':{'file':('TEST.txt',b'ok')}}), ('DELETE','/' + uploaded[0][0]['id'],{})]:
        r = users[0].request(method, API + '/files' + path, headers={'Origin':'https://hostile.invalid'}, timeout=30, **kwargs)
        assert r.status_code == 403 and r.json()['detail'] == 'Origem não permitida.'


def test_rejected_uploads(users):
    cases = [('TEST_empty.txt',b'',400), ('TEST.html',b'<html>',415), ('TEST.svg',b'<svg/>',415), ('TEST.exe',b'MZ',415), ('TEST_fake.png',b'not an image',415), ('TEST_big.txt',b'a' * (25*1024*1024+1),413)]
    for name, data, code in cases:
        r = users[0].post(API + '/files', files={'file': (name,data)}, timeout=60)
        assert r.status_code == code, (name,r.text)
        assert isinstance(r.json()['detail'],str)


def test_literal_search_kind_pagination(uploaded, users):
    s = users[0]
    for query, expected in [('[2026]',1),('AÇÃO',1),('.*',0),('TEST_',len(uploaded))]:
        r = s.get(API + '/files',params={'q':query},timeout=30)
        assert r.status_code == 200 and r.json()['total'] == expected
    image = s.get(API + '/files',params={'kind':'image'}).json()
    assert image['total'] == 1 and image['items'][0]['kind'] == 'image'
    first = s.get(API + '/files',params={'page_size':2,'page':1}).json()
    second = s.get(API + '/files',params={'page_size':2,'page':2}).json()
    assert len(first['items']) == len(second['items']) == 2
    assert first['total_size'] == sum(len(d) for _,d in uploaded)
    assert not {i['id'] for i in first['items']} & {i['id'] for i in second['items']}
    for params in [{'page':0},{'page_size':101},{'kind':'invalid'},{'q':'a'*181}]:
        r = s.get(API + '/files',params=params)
        assert r.status_code == 422 and isinstance(r.json()['detail'],list)


def test_sanitization_and_soft_delete(users):
    r = users[0].post(API + '/files',files={'file':('../folder/TEST_ação\x01.txt',b'hello')},timeout=150)
    assert r.status_code == 201,r.text
    record = r.json(); assert record['original_filename'] == 'TEST_ação.txt'
    assert any(x['id'] == record['id'] for x in users[0].get(API+'/files').json()['items'])
    r = users[0].delete(API+'/files/'+record['id']); assert r.status_code == 204 and not r.content
    assert not any(x['id'] == record['id'] for x in users[0].get(API+'/files').json()['items'])
    r = users[0].get(API+'/files/'+record['id']+'/download')
    assert r.status_code == 404 and r.json()['detail'] == 'Arquivo não encontrado.'


def test_metadata_only_and_persistence(uploaded, users):
    load_dotenv('/app/backend/.env')
    with MongoClient(os.environ['MONGO_URL']) as client:
        doc = client[os.environ['DB_NAME']].files.find_one({'id': uploaded[0][0]['id']})
        assert set(doc) == {'_id','id','original_filename','content_type','kind','size','created_at','user_id','storage_path','is_deleted'}
        assert isinstance(doc['storage_path'],str) and doc['is_deleted'] is False
    creds = json.loads(Path('/app/test_reports/storage_user.json').read_text())
    fresh = requests.Session(); r = fresh.post(API+'/auth/login',json=creds,timeout=30)
    assert r.status_code == 200 and r.json()['email'] == creds['email'].lower()
    assert fresh.get(API+'/files').json()['total'] == len(uploaded)


def test_config(users):
    r = users[0].get(API+'/files/config')
    assert r.status_code == 200
    assert r.json()['max_file_size'] == 25*1024*1024 and '.xlsx' in r.json()['extensions']