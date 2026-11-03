"""Web iş uygulamasını ayrı Chrome profili ve yalnız yerel sunucuda doğrular.

--ornek: internetsiz örnek veri ekranları, yerleşim ve sabit açık tema.
Canlı ayar dosyası veya kişisel tarayıcı profili kullanılmaz.
"""
import argparse
import base64
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import urllib.request
import sys

import websocket

HERE = Path(__file__).resolve().parent
WEB = HERE.parent
ROOT = WEB.parents[1]


class StaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class StaticServer(ThreadingHTTPServer):
    request_queue_size = 64


class Browser:
    def __init__(self, width=1440, height=1000):
        self.profile = tempfile.TemporaryDirectory(prefix='irp-web-chrome-',ignore_cleanup_errors=True)
        self.proc = subprocess.Popen([
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '--headless=new', '--no-first-run', '--no-default-browser-check',
            '--remote-allow-origins=*', '--remote-debugging-port=0',
            '--user-data-dir=' + self.profile.name,
            '--window-size=' + str(width) + ',' + str(height), 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(self.profile.name) / 'DevToolsActivePort'
        end = time.monotonic() + 20
        while not port_file.exists() and time.monotonic() < end:
            time.sleep(.1)
        if not port_file.exists():
            raise RuntimeError('Ayrı sınama tarayıcısı açılamadı')
        port = port_file.read_text().splitlines()[0]
        pages = json.load(urllib.request.urlopen('http://127.0.0.1:' + port + '/json'))
        self.ws = websocket.create_connection(next(x for x in pages if x['type'] == 'page')['webSocketDebuggerUrl'], timeout=15, suppress_origin=True)
        self.count = 0
        self.errors = []
        self.network_errors = []
        self.call('Network.enable')
        self.call('Runtime.enable')
        self.call('Page.enable')
        self.call('Emulation.setDeviceMetricsOverride', width=width, height=height, deviceScaleFactor=1, mobile=False)

    def call(self, method, **params):
        self.count += 1
        identifier = self.count
        self.ws.send(json.dumps({'id': identifier, 'method': method, 'params': params}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get('method') == 'Runtime.exceptionThrown':
                self.errors.append(r['params']['exceptionDetails'].get('exception', {}).get('description', 'Tarayıcı hatası'))
            if r.get('method') == 'Network.loadingFailed':
                self.network_errors.append((r['params'].get('type'), r['params'].get('errorText')))
            if r.get('id') == identifier:
                if r.get('error'):
                    raise RuntimeError(r['error']['message'])
                return r.get('result', {})

    def js(self, source):
        r = self.call('Runtime.evaluate', expression=source, returnByValue=True, awaitPromise=True)
        if 'exceptionDetails' in r:
            raise RuntimeError(r['exceptionDetails'].get('exception', {}).get('description', 'JavaScript hatası'))
        return r.get('result', {}).get('value')

    def wait(self, source, timeout=20):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.js(source):
                return
            time.sleep(.1)
        raise AssertionError('Tarayıcı bekleme süresi doldu: ' + source[:180] + ' | ' + str(self.js('document.body.innerText.slice(-600)')) + ' | JS: ' + str([x.splitlines()[0] for x in self.errors[-3:]])+' | Ağ: '+str(self.network_errors[-5:]))

    def navigate(self, url):
        self.call('Page.navigate', url=url)

    def screenshot(self, path):
        r = self.call('Page.captureScreenshot', format='png', captureBeyondViewport=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(r['data']))

    def close(self):
        self.ws.close()
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.profile.cleanup()


def sample_test():
    handler = functools.partial(StaticHandler, directory=str(WEB / 'build'))
    server = StaticServer(('127.0.0.1', 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    browser = None
    try:
        browser = Browser()
        browser.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}])
        browser.navigate('http://127.0.0.1:' + str(server.server_port) + '/?kip=gosterim')
        browser.wait("document.querySelector('#main h1') && !document.querySelector('.loading-line')",45)
        assert browser.js("getComputedStyle(document.body).backgroundColor") == 'rgb(255, 255, 255)'
        assert browser.js("getComputedStyle(document.documentElement).colorScheme") == 'light'
        for page, title in [('overview', 'Genel Bakış'), ('projects', 'Projeler ve Plan'),
                            ('staffing', 'Personel Dağılımı'), ('reports', 'İşçilik ve Maliyet'),
                            ('performance', 'Adil Performans')]:
            browser.js('location.hash=' + json.dumps(page))
            browser.wait('document.querySelector("#main h1")?.textContent===' + json.dumps(title) + ' && !document.querySelector(".loading-line")')
            assert browser.js('document.documentElement.scrollWidth<=innerWidth+1'), page + ': sayfa yatay taşıyor'
            assert browser.js("document.body.innerText.includes('Örnek veri')"), page
            assert browser.js("!document.querySelector('canvas')"), 'Web iş arayüzü canvas olmamalı'
            browser.screenshot(ROOT / 'codex/sonuclar/web_son_duzeltmeler_ekranlar' / ('ornek_' + page + '.png'))
            print('Tarayıcı: örnek veri / ' + page + ' geçti', flush=True)
        assert not browser.errors, '\n'.join(browser.errors)
        # Köprü gerçekten aynı Dart istemci sınıfını kullanıyor.
        bridge = browser.js("""(async()=>{
          const schemas=await (await fetch('assets/eylem_semalari.json')).json();
          const call=async q=>JSON.parse(await irpCoreCall(JSON.stringify(q)));
          await call({op:'init',kisi:'K017',harf:'T',semalar:schemas});
          return await call({op:'prepare',kod:'NOT.YAZDIM',girdiler:{metin:'Yerel köprü sınaması'},hedefler:[{tur:'PROJE',kimlik:'TEST'}],hal:{},kanit:[]});
        })()""")
        assert bridge['ok'], bridge
        assert bridge['value']['eylem_kodu'] == 'NOT.YAZDIM'
        assert bridge['state']['gunluk'][bridge['value']['olay_kimligi']]['durum'] == 'BEKLIYOR'
        print('Tarayıcı: Dart köprüsü ve tanıklık günlüğü geçti', flush=True)
        browser.wait("!!navigator.serviceWorker.controller",20)
        browser.call('Network.enable')
        browser.call('Network.emulateNetworkConditions',offline=True,latency=0,downloadThroughput=-1,uploadThroughput=-1)
        browser.call('Page.reload')
        browser.wait("document.querySelector('#main h1') && !document.querySelector('.loading-line')",20)
        assert browser.js("document.body.innerText.includes('Örnek veri')")
        browser.call('Network.emulateNetworkConditions',offline=False,latency=0,downloadThroughput=-1,uploadThroughput=-1)
        print('Tarayıcı: bağlantısız yeniden açılış geçti.',flush=True)
    finally:
        if browser:
            browser.close()
        server.shutdown()
        server.server_close()


def full_test():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from yerel_api import Database, ApiServer
    database = None
    server = None
    browser = None
    try:
        database = Database()
        server = ApiServer(database, WEB / 'build')
        threading.Thread(target=server.serve_forever, daemon=True).start()
        browser = Browser(1440, 1000)
        browser.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}])
        browser.navigate('http://127.0.0.1:' + str(server.server_port) + '/?kisi=K001')
        browser.wait("document.querySelector('#main h1') && !document.querySelector('.loading-line')", 45)
        assert browser.js('document.querySelector(".user-copy strong").textContent') == 'Yetkili'
        assert browser.js('getComputedStyle(document.body).backgroundColor') == 'rgb(255, 255, 255)'
        nav = browser.js(r"[...document.querySelectorAll('.nav-link')].map(x=>({page:x.dataset.page,title:x.querySelector('span:not(.nav-icon)').textContent.trim().replace(/\s*\(\d+\)$/,'')}))")
        assert len(nav) >= 23, 'Bütün çekirdek sayfaları menüde olmalı'
        for item in nav:
            browser.js('location.hash=' + json.dumps(item['page']))
            browser.wait('document.querySelector("#main h1")?.textContent===' + json.dumps(item['title']) + ' && !document.querySelector(".loading-line")', 30)
            assert browser.js('document.documentElement.scrollWidth<=innerWidth+1'), item['page'] + ': sayfa taşıyor'
            assert not browser.errors, '\n'.join(browser.errors)
            if item['page'] in ['overview', 'assign', 'workshop', 'projects', 'leaves', 'calendar']:
                browser.screenshot(ROOT / 'codex/sonuclar/web_son_duzeltmeler_ekranlar' / ('canli_' + item['page'] + '.png'))
            print('Tarayıcı: gerçek motor / ' + item['page'] + ' geçti', flush=True)
        # Formlar gerçek tarayıcıda da açılır; motoru kopyalayan sahte iş kuralları yok.
        browser.js("""(async()=>{
          const {openOperation}=await import('./forms.js');
          const {OPERATIONS}=await import('./actions.js');
          const schemas=await (await fetch('assets/eylem_semalari.json')).json();
          const c={schemas,today:'2026-10-30',person:'K001',people:[{kimlik:'K001',ad:'Yetkili'}],projects:[],units:[],context:{nesne_turleri:[{kod:'BELGE'}]},cached:()=>[]};
          for(const code of Object.keys(OPERATIONS)){
            const d=await openOperation(c,code,{refs:{}});
            if(!d.querySelector('form')||d.textContent.includes('undefined'))throw Error(code);
            d.close();
          }
        })()""")
        print('Tarayıcı: 89 iş formu açıldı.', flush=True)
        business_flow(browser,database,server)
        assert not [x for x in database.errors if x[1] != 'olay_akisi'], database.errors[:6]
        print('Tarayıcı: çekirdeğin bütün sayfaları gerçek SQL okumalarıyla açıldı.', flush=True)
        if str(ROOT) not in sys.path:
            sys.path.insert(0,str(ROOT))
        from modul_kiti.yetenek_denetle import denetle
        denetle(database)
    finally:
        if browser:
            browser.close()
        if server:
            server.shutdown()
            server.server_close()
        if database:
            database.close()


def page(browser,name):
    browser.js('location.hash='+json.dumps(name))
    browser.wait("document.querySelector('.nav-link.active')?.dataset.page==="+json.dumps(name)+r" && document.querySelector('#main h1')?.textContent===document.querySelector('.nav-link.active [data-nav-title]')?.textContent.replace(/\s*\(\d+\)$/,'') && !document.querySelector('.loading-line')",30)


def click(browser,selector):
    browser.wait('(()=>{const e=document.querySelector('+json.dumps(selector)+');return e&&!e.disabled;})()',30)
    browser.js('document.querySelector('+json.dumps(selector)+').click()')


def field(browser,path,value,selector='[data-path]'):
    browser.js("""((path,value)=>{
      const el=[...document.querySelectorAll('dialog[open] [data-path],#task-editor [data-path]')].find(x=>x.dataset.path===path);
      if(!el)throw Error('Alan yok: '+path);
      if(el.type==='checkbox')el.checked=value;else el.value=String(value);
      el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));
    })("""+json.dumps(path)+','+json.dumps(value)+')')


def submit(browser):
    click(browser,'dialog[open] button[type=submit]')
    browser.wait("!document.querySelector('dialog[open]') || !!document.querySelector('dialog[open] .form-error')?.textContent",35)
    error=browser.js("document.querySelector('dialog[open] .form-error')?.textContent")
    assert not error,error


def switch_person(browser,person,title):
    # Başlangıçtaki gönderim taraması bitmeden aktör değiştirilemez.
    for _ in range(30):
        click(browser,'#user-menu')
        click(browser,'#switch-account')
        click(browser,'dialog[open] [data-person='+person+']')
        time.sleep(.2)
        if not browser.js("document.querySelector('dialog[open] .form-error')?.textContent"):
            break
        click(browser,'dialog[open] [data-close]')
    browser.wait("document.querySelector('.user-copy strong')?.textContent==="+json.dumps(title)+" && !document.querySelector('.loading-line')",45)
    assert not browser.js("document.querySelector('dialog[open] .form-error')?.textContent")


def business_flow(browser,database,server):
    from datetime import datetime,timedelta
    page(browser,'assign')
    click(browser,'[data-action=assign-add]')
    field(browser,'ad','Web sınaması: teknik resim')
    field(browser,'is_tanimi','Yalnız yerel test firmasında uçtan uca görev.')
    field(browser,'kisi','K041')
    field(browser,'onaylayan','K012')
    field(browser,'zaman_degeri',2)
    field(browser,'teslim_tarihi',(datetime.now()+timedelta(days=3)).date().isoformat())
    etap=browser.js("[...document.querySelector('[data-path=etap]').options].find(x=>x.value)?.value")
    assert etap,'Atama için etap bulunmalı'
    field(browser,'etap',etap)
    field(browser,'dosya_gerekli',True)
    click(browser,'[data-action=assign-review]')
    browser.wait("!!document.querySelector('dialog[open] [data-assign]')",30)
    assert browser.js("document.querySelector('dialog[open]').textContent.includes('Teslim Tarihi')")
    click(browser,'dialog[open] [data-assign]')
    browser.wait("!document.querySelector('dialog[open]') || !!document.querySelector('dialog[open] .form-error')?.textContent",35)
    error=browser.js("document.querySelector('dialog[open] .form-error')?.textContent")
    assert not error,error
    end=time.monotonic()+30
    task=None
    while time.monotonic()<end:
        tasks=database.rpc('K001','oku',{'veri':'WEB_GOREVLER','g':{}})['deger']
        task=next((x for x in tasks if x['ad']=='Web sınaması: teknik resim'),None)
        if task:break
        time.sleep(.3)
    assert task,database.events[-3:]
    task_id=task['kimlik']
    print('Akış: webden görev atandı.',flush=True)
    switch_person(browser,'K041','Tasarımcı')
    assert not browser.js("!!document.querySelector('.nav-link[data-page=payroll]')"),'Çalışanın maaş menüsü olmamalı'
    page(browser,'tasks')
    click(browser,'tr[data-id="'+task_id+'"]')
    click(browser,'.action-strip [data-code="GOREV.KABUL_ETTIM"]')
    browser.wait("document.querySelector('.task-detail h2')?.textContent==='Görevinizi Seçin'",30)
    assert browser.js("document.querySelector('.tab.active').dataset.tab")=='waiting'
    click(browser,'[data-action=tab][data-tab=open]')
    click(browser,'tr[data-id="'+task_id+'"]')
    browser.wait("!!document.querySelector('.task-detail .btn.deliver')",30)
    assert not browser.js("!!document.querySelector('dialog[open]')")
    # Tanıklık kuyruğu gerçekten SQL'e ulaşmalı.
    end=time.monotonic()+30
    while time.monotonic()<end:
        task=database.rpc('K041','oku',{'veri':'GOREV','hedef':task_id,'g':{}})['deger']
        if task['durum']=='ACIK':break
        time.sleep(.2)
    assert task['durum'] == 'ACIK',task['durum']
    click(browser,'.action-strip [data-code="GOREV.TAMAMLADIM"]')
    with tempfile.TemporaryDirectory(prefix='irp-web-belge-') as tmp:
        file=Path(tmp)/'teknik-resim.txt';file.write_text('Yalnız yerel test belgesi.\n')
        browser.wait("!!document.querySelector('#operation-files')",30)
        node=browser.call('DOM.querySelector',nodeId=browser.call('DOM.getDocument')['root']['nodeId'],selector='#operation-files')['nodeId']
        browser.call('DOM.setFileInputFiles',nodeId=node,files=[str(file)])
        submit(browser)
    end=time.monotonic()+30
    while time.monotonic()<end:
        task=database.rpc('K041','oku',{'veri':'GOREV','hedef':task_id,'g':{}})['deger']
        if task['durum']=='ONAY_BEKLIYOR' and server.uploads:break
        time.sleep(.2)
    assert task['durum']=='ONAY_BEKLIYOR',task['durum']
    assert any(v=='Yalnız yerel test belgesi.\n'.encode() for v in server.uploads.values()),'Teslim dosyası yüklenmeli'
    print('Akış: çalışan kabul etti, belgeyle teslim etti.',flush=True)
    switch_person(browser,'K012','Tasarım Yöneticisi')
    page(browser,'approvals')
    click(browser,'[data-action=quick-approve][data-id="'+task_id+'"]')
    click(browser,'dialog[open] [data-continue]')
    browser.wait("!document.querySelector('dialog[open]') || !!document.querySelector('dialog[open] .form-error')?.textContent",35)
    assert not browser.js("document.querySelector('dialog[open] .form-error')?.textContent")
    task=database.rpc('K012','oku',{'veri':'GOREV','hedef':task_id,'g':{}})['deger']
    assert task['durum']=='BITTI',task['durum']
    print('Akış: yönetici teslimi onayladı; motor BITTI yayımladı.',flush=True)
    files=database.rpc('K012','oku',{'veri':'WEB_DOSYALAR','hedef':task_id,'g':{'tur':'GOREV'}})['deger']
    assert len(files)==1 and files[0]['ad']=='teknik-resim.txt',files
    assert database.rpc('K012','oku',{'veri':'WEB_NOTLAR','hedef':task_id,'g':{'tur':'GOREV'}})['deger']==[]
    offline_flow(browser,database,task_id)
    workshop_flow(browser,database)
    document_flow(browser,database)


def offline_flow(browser,database,task_id):
    page(browser,'projects')
    click(browser,'[data-action=tab][data-tab=jobs]')
    click(browser,'[data-action=inspect][data-id="'+task_id+'"]')
    browser.wait("!!document.querySelector('dialog[open] [data-code=\"NOT.YAZDIM\"]')",30)
    click(browser,'dialog[open] [data-code="NOT.YAZDIM"]')
    browser.wait("!!document.querySelector('dialog[open] [data-path=metin]')",30)
    field(browser,'metin','Bağlantı kesikken yazılan yerel test notu.')
    browser.call('Network.enable')
    browser.call('Network.emulateNetworkConditions',offline=True,latency=0,downloadThroughput=-1,uploadThroughput=-1)
    browser.wait("document.body.innerText.includes('Çevrimdışı')",10)
    submit(browser)
    browser.wait("document.body.innerText.includes('işlem bekliyor')",10)
    # Kalıcı günlük ve oturum: uygulama bağlantısız yeniden açılır.
    browser.call('Page.reload')
    browser.wait("document.querySelector('#main h1') && !document.querySelector('.loading-line')",30)
    assert browser.js("document.body.innerText.includes('Çevrimdışı')")
    browser.call('Network.emulateNetworkConditions',offline=False,latency=0,downloadThroughput=-1,uploadThroughput=-1)
    end=time.monotonic()+35
    notes=[]
    while time.monotonic()<end:
        notes=database.rpc('K012','oku',{'veri':'WEB_NOTLAR','hedef':task_id,'g':{'tur':'GOREV'}})['deger']
        if notes:break
        time.sleep(.3)
    assert len(notes)==1,notes
    print('Akış: çevrimdışı not yeniden açılıştan sonra tek kez gönderildi.',flush=True)


def workshop_flow(browser,database):
    switch_person(browser,'K009','İmalat Ekip Lideri')
    page(browser,'workshop')
    selector='tr[data-kind=IS][data-id]'
    browser.wait('(()=>{const e=document.querySelector('+json.dumps(selector)+');return e&&!e.disabled;})()',30)
    job_id=browser.js('document.querySelector('+json.dumps(selector)+').dataset.id')
    browser.js('document.querySelector('+json.dumps(selector)+").dispatchEvent(new MouseEvent('dblclick',{bubbles:true}))")
    browser.wait("!!document.querySelector('dialog[open] [data-path=kisi]')",30)
    field(browser,'kisi','K017')
    field(browser,'sira',1)
    submit(browser)
    job=database.rpc('K009','oku',{'veri':'IS','hedef':job_id,'g':{}})['deger']
    assert job['kisi']=='K017' and job['durum']=='SIRADA',job
    print('Akış: havuz işi gerçek liste sürümüyle çalışana atandı.',flush=True)


def document_flow(browser,database):
    switch_person(browser,'K001','Yetkili')
    page(browser,'objects')
    browser.wait("!!document.querySelector('[data-action=inspect][data-kind=NESNE]')",30)
    object_id=browser.js("document.querySelector('[data-action=inspect][data-kind=NESNE]').dataset.id")
    before=database.rpc('K001','oku',{'veri':'SURUMLER','hedef':object_id,'g':{}})['deger']
    click(browser,'[data-action=inspect][data-kind=NESNE]')
    click(browser,'dialog[open] [data-code="NESNE.SURUM_EKLEDIM"]')
    browser.wait("!!document.querySelector('#operation-files')",30)
    field(browser,'surum_adi','Web doğrulama sürümü')
    with tempfile.TemporaryDirectory(prefix='irp-web-surum-') as tmp:
        file=Path(tmp)/'belge.txt';file.write_text('Yerel belge sürümü.\n')
        node=browser.call('DOM.querySelector',nodeId=browser.call('DOM.getDocument')['root']['nodeId'],selector='#operation-files')['nodeId']
        browser.call('DOM.setFileInputFiles',nodeId=node,files=[str(file)])
        submit(browser)
    versions=database.rpc('K001','oku',{'veri':'SURUMLER','hedef':object_id,'g':{}})['deger']
    assert len(versions)==len(before)+1,versions
    version=next(v for v in versions if v['surum_adi']=='Web doğrulama sürümü')
    assert version['dosyalar'] and version['dosyalar'][0].startswith('F-')
    switch_person(browser,'K004','Planlama Yöneticisi')
    page(browser,'objects')
    click(browser,'[data-action=inspect][data-kind=NESNE]')
    click(browser,'dialog[open] [data-code="NESNE.SURUM_ONAYLADIM"]')
    browser.wait("!!document.querySelector('dialog[open] [data-path=surum_no]')",30)
    field(browser,'surum_no',version['surum_no'])
    submit(browser)
    current=database.rpc('K004','oku',{'veri':'GECERLI_SURUM','hedef':object_id,'g':{}})['deger']
    assert current['surum_no']==version['surum_no'],current
    print('Akış: belge dosyasıyla sürüm eklendi ve geçerli sürüm onaylandı.',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ornek', action='store_true')
    parser.add_argument('--tam', action='store_true')
    args = parser.parse_args()
    sample_test()
    if args.tam:
        full_test()
