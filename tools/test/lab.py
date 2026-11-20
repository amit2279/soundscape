import sys, time, subprocess
from playwright.sync_api import sync_playwright
srv = subprocess.Popen([sys.executable,'-m','http.server','8771','--bind','127.0.0.1'], cwd='/home/claude/mc', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1); logs=[]
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required'])
        pg = b.new_page(viewport={'width':1120,'height':630})
        pg.on('console', lambda m: logs.append(m.type+': '+m.text) if m.type in ('error','warning') else None)
        pg.on('pageerror', lambda e: logs.append('PAGEERROR: '+str(e)))
        pg.goto('http://127.0.0.1:8771/lab.html'); time.sleep(2)
        pg.click('#demo'); pg.wait_for_function("window.__lab", timeout=120000)
        for s in sys.argv[1:]:
            if s.startswith('shot:'): time.sleep(1.2); pg.screenshot(path='test/'+s[5:]+'.png')
            else: print('eval:', pg.evaluate(s))
        b.close()
finally:
    srv.terminate()
print('\n'.join(l for l in logs if 'GPU stall' not in l)[:2500] or 'no console output')
