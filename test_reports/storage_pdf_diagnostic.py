# Diagnostic-only sandbox A/B test; no application source is modified.
await page.set_viewport_size({'width':1920,'height':1080})
try:
    await page.get_by_test_id('auth-email-input').fill('TEST_storage_owner_6862576a@test.local')
    await page.get_by_test_id('auth-password-input').fill('Storage@Test2026')
    await page.get_by_test_id('auth-submit-button').click(force=True)
    await page.get_by_test_id('nav-files').wait_for()
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-empty').wait_for()
    # Construct a valid PDF with computed xref offsets.
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    stream=b'BT /F1 18 Tf 30 100 Td (TEST arquivo privado) Tj ET'
    objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    pdf=b'%PDF-1.4\n';offsets=[]
    for i,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(pdf);pdf+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{n:010d} 00000 n \n'.encode() for n in offsets)+f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    await page.get_by_test_id('files-upload-input').set_input_files({'name':'TEST_PDF_diagnostic.pdf','mimeType':'application/pdf','buffer':pdf})
    row=page.locator('[data-testid^="file-row-"]').filter(has_text='TEST_PDF_diagnostic.pdf')
    await row.wait_for(timeout=30000)
    file_id=(await row.get_attribute('data-testid')).replace('file-row-','')
    await row.locator('[data-testid^="file-preview-"]').click(force=True)
    iframe=page.get_by_test_id('file-preview-pdf')
    await iframe.wait_for(timeout=30000)
    await page.wait_for_timeout(2000)
    print('SANDBOX PDF FRAME:',await iframe.evaluate('(el)=>({sandbox:el.getAttribute("sandbox"),body:el.contentDocument?.body?.innerHTML})'))
    await iframe.evaluate('(el)=>{const src=el.src;el.removeAttribute("sandbox");el.src="about:blank";setTimeout(()=>el.src=src,50);} ')
    await page.wait_for_timeout(3000)
    print('NO-SANDBOX PDF FRAME:',await iframe.evaluate('(el)=>({sandbox:el.getAttribute("sandbox"),body:el.contentDocument?.body?.innerHTML})'))
    await page.screenshot(path='/app/test_reports/storage-pdf-without-sandbox.jpg',quality=40,full_page=False)
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')
    assert (await page.request.delete(page.url.split('/arquivos')[0]+'/api/files/'+file_id)).status==204
    await page.reload()
    await page.get_by_test_id('files-empty').wait_for()
    print('PASS PDF diagnostic cleanup')
except Exception as e:
    print(f'FAIL PDF diagnostic: {e}')