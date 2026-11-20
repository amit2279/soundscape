import sys, time, subprocess
from playwright.sync_api import sync_playwright
srv = subprocess.Popen([sys.executable,'-m','http.server','8766','--bind','127.0.0.1'], cwd='/home/claude/mc', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1); logs=[]
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required'])
        pg = b.new_page(viewport={'width':1120,'height':630})
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in ('error',) else None)
        pg.on('pageerror', lambda e: logs.append('PAGEERROR: '+str(e)))
        pg.goto('http://127.0.0.1:8766/test.html?m=coaster'); time.sleep(3)
        print('world after load:', pg.evaluate("document.querySelector('#app').dataset.world"))
        print('popup visible:', pg.evaluate("!document.querySelector('#modePrompt').hidden"))
        print('popup name:', pg.evaluate("document.querySelector('#mpName') && document.querySelector('#mpName').textContent"))
        pg.screenshot(path='test/slug_popup.png')
        pg.evaluate("document.querySelector('#mpDemo').click()")
        pg.wait_for_function("document.querySelector('#app').dataset.state==='riding'", timeout=120000)
        time.sleep(7)
        pg.evaluate("(()=>{const s=document.querySelector('.tourcard:not([hidden]) [data-t=skip]'); if(s) s.click();})()")
        time.sleep(4)
        print('world riding:', pg.evaluate("document.querySelector('#app').dataset.world"), '| state:', pg.evaluate("document.querySelector('#app').dataset.state"))
        print('hash:', pg.evaluate("location.hash"))
        pg.screenshot(path='test/slug_ride.png')
        b.close()
finally:
    srv.terminate()
print('\n'.join(l for l in logs if 'GPU stall' not in l and 'TUNNEL' not in l and 'ERR_' not in l)[:1500] or 'no console errors')
