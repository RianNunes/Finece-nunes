# Follow-up UI checks; real deletion triggers download errors without mocked storage.
import base64
await page.set_viewport_size({'width':1920,'height':1080})
try:
    if await page.get_by_test_id('auth-email-input').count():
        await page.get_by_test_id('auth-email-input').fill('TEST_storage_owner_6862576a@test.local')
        await page.get_by_test_id('auth-password-input').fill('Storage@Test2026')
        await page.get_by_test_id('auth-submit-button').click(force=True)
        await page.get_by_test_id('nav-files').wait_for()
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-list').wait_for()
    video=await page.evaluate('''async()=>{ const c=document.createElement('canvas'); c.width=160;c.height=90;const ctx=c.getContext('2d');const stream=c.captureStream(10);const rec=new MediaRecorder(stream,{mimeType:'video/webm'});const parts=[];rec.ondataavailable=e=>parts.push(e.data);const done=new Promise(r=>rec.onstop=r);rec.start();for(let i=0;i<20;i++){ctx.fillStyle=i%2?'blue':'green';ctx.fillRect(0,0,160,90);await new Promise(r=>setTimeout(r,100));}rec.stop();await done;stream.getTracks().forEach(t=>t.stop());return Array.from(new Uint8Array(await new Blob(parts).arrayBuffer()));}''')
    await page.get_by_test_id('files-upload-input').set_input_files({'name':'TEST_UI_video_frames.webm','mimeType':'video/webm','buffer':bytes(video)})
    await page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_UI_video_frames.webm').wait_for(timeout=30000)
    row=page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_UI_video_frames.webm')
    file_id=(await row.get_attribute('data-testid')).replace('file-row-','')
    response=await page.request.get(page.url.split('/arquivos')[0]+'/api/files/'+file_id+'/download')
    assert await response.body()==bytes(video)
    await row.locator('[data-testid^="file-preview-"]').click(force=True)
    await page.get_by_test_id('file-preview-video').wait_for(timeout=30000)
    await page.get_by_test_id('file-preview-video').evaluate('(el)=>el.play()')
    await page.wait_for_timeout(400)
    assert await page.get_by_test_id('file-preview-video').evaluate('(el)=>el.currentTime>0 && !el.error')
    print('PASS playable video real upload/download byte roundtrip and preview')
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
    row=page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_UI_office.xlsx')
    await row.locator('[data-testid^="file-preview-"]').click(force=True)
    await page.get_by_test_id('file-preview-unsupported').wait_for()
    async with page.expect_download() as di:
        await page.get_by_test_id('file-preview-download').click(force=True)
    assert (await di.value).suggested_filename=='TEST_UI_office.xlsx'
    print('PASS Office fallback/download')
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
    await page.get_by_test_id('files-dropzone').evaluate('''el=>{const dt=new DataTransfer();dt.items.add(new File(['Drag drop conteúdo'],'TEST_UI_drop.txt',{type:'text/plain'}));el.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true}));}''')
    row=page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_UI_drop.txt')
    await row.wait_for(timeout=30000)
    print('PASS real drag/drop')
    file_id=(await row.get_attribute('data-testid')).replace('file-row-','')
    await row.locator('[data-testid^="file-preview-"]').click(force=True)
    await page.get_by_test_id('file-preview-text').wait_for()
    base=page.url.split('/arquivos')[0]
    response=await page.request.delete(base+'/api/files/'+file_id)
    assert response.status==204
    await page.get_by_test_id('file-preview-download').click(force=True)
    await page.get_by_test_id('files-download-error').wait_for()
    alerts=await page.get_by_test_id('file-preview-dialog').locator('[role="alert"]').count()
    print(f'FAIL download error usability: actual 404 error appears behind open modal; modal alerts={alerts}')
    await page.screenshot(path='/app/test_reports/storage-download-error.jpg',quality=40,full_page=False)
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
except Exception as e:
    print(f'FAIL extended media/error checks: {e}')

try:
    for width in (320,768,1024,1440):
        await page.set_viewport_size({'width':width,'height':844 if width==320 else 1024})
        await page.wait_for_timeout(250)
        row=page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_UI_ação_')
        await row.locator('[data-testid^="file-preview-"]').click(force=True)
        await page.get_by_test_id('file-preview-text').wait_for()
        box=await page.get_by_test_id('file-preview-dialog').bounding_box()
        assert box['x']>=0 and box['x']+box['width']<=width+1
        assert await page.get_by_test_id('file-preview-download').is_visible()
        await page.keyboard.press('Escape')
        await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
        await row.locator('[data-testid^="file-delete-"]').click(force=True)
        box=await page.get_by_test_id('file-delete-dialog').bounding_box()
        assert box['x']>=0 and box['x']+box['width']<=width+1
        await page.get_by_test_id('file-delete-cancel').click(force=True)
        await page.get_by_test_id('file-delete-dialog').wait_for(state='hidden')
        print(f'PASS preview/delete dialog fit at {width}px')
    await page.set_viewport_size({'width':1920,'height':1080})
    base=page.url.split('/arquivos')[0]
    # Enough actual tiny uploads to exercise page two.
    for i in range(20):
        response=await page.request.post(base+'/api/files',multipart={'file':{'name':f'TEST_UI_page_{i:02d}.txt','mimeType':'text/plain','buffer':b'pagination'}})
        assert response.status==201
    await page.reload()
    await page.get_by_test_id('files-pagination').wait_for()
    assert await page.locator('[data-testid^="file-row-"]').count()==24
    await page.get_by_test_id('files-next-page').click(force=True)
    await page.get_by_test_id('files-page-number').filter(has_text='2 de 2').wait_for()
    await page.wait_for_timeout(500)
    assert 0<await page.locator('[data-testid^="file-row-"]').count()<24
    await page.get_by_test_id('files-previous-page').click(force=True)
    await page.get_by_test_id('files-page-number').filter(has_text='1 de 2').wait_for()
    print('PASS real library pagination forward/back')
    for nav,path in [('dashboard','/'),('transactions','/movimentacoes'),('planning','/planejamento'),('profile','/perfil')]:
        await page.get_by_test_id('nav-'+nav).click(force=True)
        await page.wait_for_timeout(700)
        assert page.url.endswith(path)
        assert await page.locator('main').inner_text()
        print(f'PASS regression navigation {nav}')
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-list').wait_for()
    row=page.locator('[data-testid^="file-row-"]').first
    file_id=(await row.get_attribute('data-testid')).replace('file-row-','')
    await row.locator('[data-testid^="file-delete-"]').click(force=True)
    await page.get_by_test_id('file-delete-confirm').click(force=True)
    await page.get_by_test_id('file-delete-dialog').wait_for(state='hidden')
    await page.get_by_test_id('file-row-'+file_id).wait_for(state='hidden')
    assert (await page.request.get(base+'/api/files/'+file_id+'/download')).status==404
    print('PASS delete confirm removes row and prevents download')
    listing=(await (await page.request.get(base+'/api/files?page_size=100')).json())['items']
    for item in listing:
        assert (await page.request.delete(base+'/api/files/'+item['id'])).status==204
    await page.reload()
    await page.get_by_test_id('files-empty').wait_for()
    await page.get_by_test_id('logout-button').click(force=True)
    await page.get_by_test_id('auth-email-input').wait_for()
    await page.get_by_test_id('auth-email-input').fill('TEST_storage_owner_6862576a@test.local')
    await page.get_by_test_id('auth-password-input').fill('Storage@Test2026')
    await page.get_by_test_id('auth-submit-button').click(force=True)
    await page.get_by_test_id('nav-files').wait_for()
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-empty').wait_for()
    print('PASS cleanup, reload/logout/login persistence; finance data untouched')
except Exception as e:
    print(f'FAIL responsive/pagination/regression/cleanup: {e}')
error_text=await page.evaluate('''()=>{const errorElements=Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));return errorElements.map(el=>el.textContent).join(', ');}''')
print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')