# Executed by browser automation; public URL comes from frontend/.env.
import base64
import io
import wave

await page.set_viewport_size({'width':1920,'height':1080})
browser_errors = []
page.on('pageerror', lambda error: browser_errors.append(str(error)))
try:
    await page.get_by_test_id('auth-email-input').fill('TEST_storage_owner_6862576a@test.local')
    await page.get_by_test_id('auth-password-input').fill('Storage@Test2026')
    await page.get_by_test_id('auth-submit-button').click(force=True)
    await page.get_by_test_id('nav-files').wait_for()
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-empty').wait_for()
    print('PASS isolated login, navigation, empty library')
    long_name = 'TEST_UI_ação_' + 'nome_muito_longo_' * 8 + '.txt'
    await page.get_by_test_id('files-upload-input').set_input_files([
        {'name':long_name,'mimeType':'text/plain','buffer':'Olá, arquivo privado!'.encode()},
        {'name':'TEST_UI_rejected.html','mimeType':'text/html','buffer':b'<html>invalid</html>'},
        {'name':'TEST_UI_fake.png','mimeType':'image/png','buffer':b'invalid PNG'}])
    await page.get_by_test_id('files-upload-errors').wait_for(timeout=30000)
    await page.get_by_test_id('files-count').filter(has_text='1 arquivo').wait_for()
    assert await page.get_by_test_id('files-upload-errors').locator('li').count() == 2
    print('PASS multi-file upload with partial validation failures')
    await page.locator('[data-testid^="file-preview-"]').filter(has=page.locator('svg')).first.click(force=True)
    await page.get_by_test_id('file-preview-text').wait_for(timeout=30000)
    assert await page.get_by_test_id('file-preview-text').inner_text() == 'Olá, arquivo privado!'
    async with page.expect_download() as download_info:
        await page.get_by_test_id('file-preview-download').click(force=True)
    download = await download_info.value
    assert download.suggested_filename == long_name
    from pathlib import Path
    assert Path(await download.path()).read_bytes() == 'Olá, arquivo privado!'.encode()
    print('PASS text preview and real download name/content')
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
    print('PASS keyboard closes preview')
    await page.reload()
    await page.get_by_test_id('files-count').filter(has_text='1 arquivo').wait_for()
    await page.get_by_test_id('files-search-input').fill('missing')
    await page.get_by_test_id('files-empty').wait_for()
    await page.get_by_test_id('files-search-input').fill('AÇÃO')
    await page.get_by_test_id('files-list').wait_for()
    await page.get_by_test_id('files-search-input').fill('')
    await page.get_by_test_id('files-filter-type').select_option('image')
    await page.get_by_test_id('files-empty').wait_for()
    await page.get_by_test_id('files-filter-type').select_option('all')
    await page.get_by_test_id('files-list').wait_for()
    print('PASS reload persistence, literal search, filtering, manual filter clear')
    for width in (320,768,1024,1440):
        await page.set_viewport_size({'width':width,'height':844 if width==320 else 1024})
        await page.wait_for_timeout(300)
        overflow = await page.evaluate('document.documentElement.scrollWidth > innerWidth')
        assert not overflow, f'overflow at {width}'
        if width == 320:
            assert await page.get_by_test_id('bottom-nav').locator('a').count() == 6
            await page.screenshot(path='/app/test_reports/storage-mobile.jpg',quality=40,full_page=False)
        print(f'PASS no horizontal overflow at {width}px')
    await page.set_viewport_size({'width':1920,'height':1080})
    await page.locator('[data-testid^="file-delete-"]').filter(has=page.locator('svg')).first.click(force=True)
    await page.get_by_test_id('file-delete-cancel').click(force=True)
    await page.get_by_test_id('file-delete-dialog').wait_for(state='hidden')
    assert await page.get_by_test_id('files-list').is_visible()
    print('PASS delete cancellation')
except Exception as e:
    print(f'FAIL core UI: {e}')

try:
    # Actual browser canvas recording produces a playable, non-mocked video.
    video = await page.evaluate('''async () => {
      const canvas = document.createElement('canvas'); canvas.width=160; canvas.height=90;
      const ctx=canvas.getContext('2d'); ctx.fillStyle='green'; ctx.fillRect(0,0,160,90);
      const recorder=new MediaRecorder(canvas.captureStream(10), {mimeType:'video/webm'});
      const parts=[]; recorder.ondataavailable=e=>parts.push(e.data);
      const done=new Promise(resolve=>recorder.onstop=resolve); recorder.start();
      await new Promise(r=>setTimeout(r,600)); recorder.stop(); await done;
      const arr=new Uint8Array(await new Blob(parts).arrayBuffer()); return Array.from(arr);
    }''')
    wav=io.BytesIO()
    with wave.open(wav,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\0\0'*8000)
    response=await page.request.get(page.url.split('/arquivos')[0]+'/api/export/year?year=2026')
    xlsx=await response.body()
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=')
    await page.get_by_test_id('files-upload-input').set_input_files([
        {'name':'TEST_UI_image.png','mimeType':'image/png','buffer':png},
        {'name':'TEST_UI_audio.wav','mimeType':'audio/wav','buffer':wav.getvalue()},
        {'name':'TEST_UI_video.webm','mimeType':'video/webm','buffer':bytes(video)},
        {'name':'TEST_UI_office.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':xlsx}])
    await page.get_by_test_id('files-count').filter(has_text='5 arquivos').wait_for(timeout=60000)
    for name, testid in [('TEST_UI_image.png','file-preview-image'),('TEST_UI_audio.wav','file-preview-audio'),('TEST_UI_video.webm','file-preview-video'),('TEST_UI_office.xlsx','file-preview-unsupported')]:
        row=page.locator('[data-testid^="file-row-"]').filter(has_text=name)
        await row.locator('[data-testid^="file-preview-"]').click(force=True)
        await page.get_by_test_id(testid).wait_for(timeout=30000)
        if testid == 'file-preview-image':
            assert await page.get_by_test_id(testid).evaluate('(el)=>el.complete && el.naturalWidth > 0')
        if testid in ('file-preview-audio','file-preview-video'):
            await page.get_by_test_id(testid).evaluate('(el)=>el.play()')
            await page.wait_for_timeout(200)
            assert await page.get_by_test_id(testid).evaluate('(el)=>el.currentTime > 0 && !el.error')
        print(f'PASS {name} preview/playback')
        await page.keyboard.press('Escape')
        await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
    # Drop a genuine File via DataTransfer.
    await page.get_by_test_id('files-dropzone').evaluate('''el=>{ const dt=new DataTransfer(); dt.items.add(new File(['Drag drop conteúdo'],'TEST_UI_drop.txt',{type:'text/plain'})); el.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true})); }''')
    await page.get_by_test_id('files-count').filter(has_text='6 arquivos').wait_for(timeout=30000)
    print('PASS real drag-drop upload')
except Exception as e:
    print(f'FAIL media/drag-drop: {e}')

try:
    row=page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_UI_drop.txt')
    await row.locator('[data-testid^="file-preview-"]').click(force=True)
    await page.get_by_test_id('file-preview-text').wait_for(timeout=30000)
    await page.route('**/api/files/*/download',lambda route: route.fulfill(status=503,content_type='application/json',body='{"detail":"Armazenamento indisponível. Tente novamente."}'))
    await page.get_by_test_id('file-preview-download').click(force=True)
    await page.get_by_test_id('files-download-error').wait_for()
    modal_error = await page.get_by_test_id('file-preview-dialog').locator('[role="alert"]').count()
    print(f'DOWNLOAD FAILURE: modal alerts={modal_error}; message location outside modal={await page.get_by_test_id("files-download-error").inner_text()}')
    await page.screenshot(path='/app/test_reports/storage-download-error.jpg',quality=40,full_page=False)
    await page.unroute('**/api/files/*/download')
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
    for nav,path in [('dashboard','/'),('transactions','/movimentacoes'),('planning','/planejamento'),('profile','/perfil')]:
        await page.get_by_test_id('nav-'+nav).click(force=True)
        await page.wait_for_timeout(600)
        assert page.url.endswith(path)
        print(f'PASS regression navigation {nav}')
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-list').wait_for()
    while await page.locator('[data-testid^="file-row-"]').count():
        await page.locator('[data-testid^="file-row-"]').first.locator('[data-testid^="file-delete-"]').click(force=True)
        await page.get_by_test_id('file-delete-confirm').click(force=True)
        await page.get_by_test_id('file-delete-dialog').wait_for(state='hidden')
        await page.wait_for_timeout(500)
    await page.reload()
    await page.get_by_test_id('files-empty').wait_for()
    print('PASS all UI uploads soft deleted, empty library persists')
except Exception as e:
    print(f'FAIL error/regression/cleanup: {e}')
error_text = await page.evaluate('''() => {
 const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
 return errorElements.map(el => el.textContent).join(', ');
}''')
print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')
print(f'Browser page errors: {browser_errors}')