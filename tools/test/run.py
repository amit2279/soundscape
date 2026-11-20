import sys, time, subprocess, os
from playwright.sync_api import sync_playwright
srv = subprocess.Popen([sys.executable,'-m','http.server','8765','--bind','127.0.0.1'], cwd='/home/claude/mc', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
logs=[]
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required'])
        pg = b.new_page(viewport={'width':int(os.environ.get('VW','1120')),'height':int(os.environ.get('VH','630'))})
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in ('error','warning') else None)
        pg.on('pageerror', lambda e: logs.append('PAGEERROR: '+str(e)))
        pg.goto('http://127.0.0.1:8765/test.html')
        try:
            pg.wait_for_function("document.querySelector('#btnDemo') && !document.querySelector('#btnDemo').disabled", timeout=int(os.environ.get('WAITMS','60000')))
        except Exception as e:
            logs.append('WAIT TIMEOUT; btn text: '+pg.inner_text('#btnDemo')+' | toast: '+pg.inner_text('#toast'))
        time.sleep(float(sys.argv[1]) if len(sys.argv)>1 else 6)
        pg.screenshot(path='test/landing.png')
        steps = sys.argv[2:] 
        for s in steps:
            pg.evaluate(s) if not s.startswith('shot:') else (time.sleep(2.5), pg.screenshot(path='test/'+s[5:]+'.png'))
        b.close()
finally:
    srv.terminate()
print('\n'.join(logs[:40]) or 'no console errors')
