# Browser-tool async snippet: targeted REAL preview regression, no mocked routes.
from pathlib import Path
from urllib.parse import urlsplit
await page.set_viewport_size({'width':1920,'height':1080})
browser_errors = []
page.on('pageerror', lambda error: browser_errors.append(str(error)))
base = urlsplit(page.url).scheme + '://' + urlsplit(page.url).netloc
try:
    await page.get_by_test_id('auth-email-input').fill('TEST_storage_owner_6862576a@test.local')
    await page.get_by_test_id('auth-password-input').fill('Storage@Test2026')
    await page.get_by_test_id('auth-submit-button').click(force=True)
    await page.get_by_test_id('nav-files').wait_for()
    await page.get_by_test_id('nav-files').click(force=True)
    await page.get_by_test_id('files-list').wait_for()
    print('PASS login and fixture library')
except Exception as e:
    print(f'FAIL setup: {e}')

async def open_file(name):
    row = page.locator('[data-testid^="file-row-"]').filter(has_text=name)
    await row.locator('[data-testid^="file-preview-"]').click(force=True)
    await page.get_by_test_id('file-preview-dialog').wait_for()
    return (await row.get_attribute('data-testid')).removeprefix('file-row-')

async def close_preview():
    await page.keyboard.press('Escape')
    await page.get_by_test_id('file-preview-dialog').wait_for(state='hidden')

async def assert_pixels(expected):
    await page.get_by_test_id('file-pdf-canvas').wait_for(state='visible', timeout=30000)
    await page.wait_for_function('(expected) => document.querySelector("[data-testid=file-pdf-text]")?.textContent.includes(expected)', arg=expected, timeout=30000)
    pixels = await page.get_by_test_id('file-pdf-canvas').evaluate('''c => {
        const bytes=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
        let dark=0,white=0;
        for(let i=0;i<bytes.length;i+=4){if(bytes[i+3]>0 && bytes[i]<100 && bytes[i+1]<100 && bytes[i+2]<100)dark++;if(bytes[i]>245 && bytes[i+1]>245 && bytes[i+2]>245)white++;}
        return {dark,white,width:c.width,height:c.height};
    }''')
    assert pixels['dark'] > 100 and pixels['white'] > pixels['dark'], pixels
    print(f'PASS real canvas text="{expected}" pixels={pixels}')

try:
    pdf_id = await open_file('TEST_iter5_readable.pdf')
    await assert_pixels('TEST readable page 1')
    assert await page.get_by_test_id('file-pdf-page').inner_text() == '1 / 2'
    assert await page.get_by_test_id('file-pdf-previous').is_disabled()
    await page.get_by_test_id('file-pdf-next').click(force=True)
    await assert_pixels('TEST readable page 2')
    assert await page.get_by_test_id('file-pdf-page').inner_text() == '2 / 2'
    assert await page.get_by_test_id('file-pdf-next').is_disabled()
    await page.get_by_test_id('file-pdf-previous').click(force=True)
    await assert_pixels('TEST readable page 1')
    print('PASS multipage next/previous and disabled boundaries')
    for width in (320,768,1440):
        await page.set_viewport_size({'width':width,'height':844 if width==320 else 1024})
        await page.wait_for_timeout(350)
        await assert_pixels('TEST readable page 1')
        fit = await page.evaluate('''() => {
            const d=document.querySelector('[data-testid=file-preview-dialog]').getBoundingClientRect();
            const c=document.querySelector('[data-testid=file-pdf-canvas]').getBoundingClientRect();
            return d.left>=0 && d.right<=innerWidth+1 && d.top>=0 && d.bottom<=innerHeight+1 && c.left>=d.left && c.right<=d.right+1 && document.documentElement.scrollWidth<=innerWidth;
        }''')
        assert fit, f'preview overflow at {width}'
        print(f'PASS responsive PDF canvas/dialog {width}px')
    await page.screenshot(path='/tmp/iter5-rendered-pdf.jpg',quality=40,full_page=False)
    async with page.expect_download() as info:
        await page.get_by_test_id('file-preview-download').click(force=True)
    download = await info.value
    original = await page.request.get(base+'/api/files/'+pdf_id+'/download')
    assert Path(await download.path()).read_bytes() == await original.body()
    assert download.suggested_filename == 'TEST_iter5_readable.pdf'
    print('PASS real PDF browser download byte equality')
    await close_preview()
    print('PASS Escape closes PDF')
except Exception as e:
    print(f'FAIL PDF: {e}')
    if await page.get_by_test_id('file-preview-dialog').count():
        await close_preview()

for name, expected in [('TEST_iter5_corrupt.pdf','Não foi possível visualizar'),('TEST_iter5_password.pdf','protegido por senha')]:
    try:
        file_id = await open_file(name)
        await page.get_by_test_id('file-pdf-error').wait_for(timeout=30000)
        assert expected in await page.get_by_test_id('file-pdf-error').inner_text()
        assert await page.get_by_test_id('file-preview-dialog').get_by_test_id('file-pdf-error').is_visible()
        assert await page.get_by_test_id('file-preview-download').is_enabled()
        async with page.expect_download() as info:
            await page.get_by_test_id('file-preview-download').click(force=True)
        download = await info.value
        original = await page.request.get(base+'/api/files/'+file_id+'/download')
        assert Path(await download.path()).read_bytes() == await original.body()
        print(f'PASS {name}: in-dialog fallback and real downloadable bytes')
    except Exception as e:
        print(f'FAIL {name}: {e}')
    finally:
        if await page.get_by_test_id('file-preview-dialog').count():
            await close_preview()

try:
    txt_id = await open_file('TEST_iter5_deleted.txt')
    await page.get_by_test_id('file-preview-text').wait_for(timeout=30000)
    assert await page.get_by_test_id('file-preview-text').inner_text() == 'TEST real preview download error'
    deleted = await page.request.delete(base+'/api/files/'+txt_id)
    assert deleted.status == 204
    await page.get_by_test_id('file-preview-download').click(force=True)
    alert = page.get_by_test_id('file-preview-dialog').get_by_test_id('file-preview-download-error')
    await alert.wait_for()
    assert 'Arquivo não encontrado.' in await alert.inner_text()
    missing = await page.request.get(base+'/api/files/'+txt_id+'/download')
    assert missing.status == 404
    assert await alert.is_visible()
    print('PASS REAL 404 download failure visible inside dialog')
    await close_preview()
    image_id = await open_file('TEST_iter5_image.png')
    assert await page.get_by_test_id('file-preview-download-error').count() == 0
    await page.get_by_test_id('file-preview-image').wait_for(timeout=30000)
    assert await page.get_by_test_id('file-preview-image').evaluate('e => e.complete && e.naturalWidth===120 && e.naturalHeight===80')
    async with page.expect_download() as info:
        await page.get_by_test_id('file-preview-download').click(force=True)
    download = await info.value
    original = await page.request.get(base+'/api/files/'+image_id+'/download')
    assert Path(await download.path()).read_bytes() == await original.body()
    print('PASS image preview/download and previous download error cleared')
    await close_preview()
except Exception as e:
    print(f'FAIL download error/image regression: {e}')

print(f'Browser page errors: {browser_errors}')
error_text = await page.evaluate('''() => {
 const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
 return errorElements.map(el => el.textContent).join(', ');
}''')
print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')