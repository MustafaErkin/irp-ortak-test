"""Mevcut bulutta giriş, okuma ve sinyal. İş olayı, sıfırlama, hesap değişikliği yok.

Ayrı ve geçici Chrome profili. Sınama cihazı anahtarı sabit; tekrar sınamada
gereksiz yeni cihaz harfi alınmaz. Ayar, jeton ve şifre yazdırılmaz.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).parent))
from tarayici import Browser,page


def run(modules=False):
    for person,title,pages in [('K001','CEO',['overview','projects','people','settings','dayclose','notifications']),
                              ('K004','Yönetici',['overview','projects','assign','approvals','dayclose','notifications']),
                              ('K009','Ekip Lideri',['overview','workshop','approvals','notifications']),
                              ('K041','Ofis Çalışanı',['overview','tasks','performance','notifications'])]:
        browser=Browser()
        writes=[]
        try:
            browser.call('Network.enable')
            browser.navigate('http://localhost:8080/?kip=gosterim')
            browser.wait("document.querySelector('#main h1') && !document.querySelector('.loading-line')",30)
            browser.js("""(async()=>{const {BrowserStore}=await import('./client.js');
                const config=await (await fetch('ayar.json')).json();
                const s=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');
                await s.put('installation','T20-READ-CHECK');})()""")
            browser.navigate('http://localhost:8080/?kisi='+person)
            browser.wait("document.querySelector('.user-copy strong')?.textContent==="+json.dumps(title)+" && !document.querySelector('.loading-line')",60)
            for name in pages:
                page(browser,name)
                assert not browser.js("document.querySelector('.notice.warn')?.textContent"),name+': okuma uyarısı'
                assert not browser.js(r"/K[0-9]{3}|[A-Z_]+\.[A-Z_]+|[Bb]ulut/.test(document.body.innerText)"),name+': teknik kod göründü'
                assert not browser.js("!!document.querySelector('.avatar')")
                if name=='dayclose':
                    browser.js("(()=>{const e=document.querySelector('[data-filter=day]');e.value='2026-10-30';e.dispatchEvent(new Event('change',{bubbles:true}));})()")
                    browser.wait("!document.querySelector('.loading-line')",30)
                    assert not browser.js(r"/K[0-9]{3}|[A-Z_]+\.[A-Z_]+/.test(document.body.innerText)"),'Önceki günün özetinde teknik kod var'
                browser.js("window.scrollTo(0,300)")
                assert browser.js("(()=>{const h=document.querySelector('.topbar'),r=h.getBoundingClientRect();return getComputedStyle(h).backgroundColor==='rgb(255, 255, 255)' && !!document.elementFromPoint(r.x+20,30)?.closest('.topbar')})()"),'Sabit başlık içerikle örtüştü'
                browser.js("window.scrollTo(0,0)")
            if modules:
                visible=browser.js("""(async()=>{const {BrowserStore}=await import('./client.js');
                  const config=await (await fetch('ayar.json')).json();
                  const store=await BrowserStore.open(config.senaryo?'irp-is-web-v1:'+config.senaryo:'irp-is-web-v1');
                  const saved=await store.get('session');
                  const r=await fetch('/irp/moduller',{headers:{Authorization:'Bearer '+saved.session.access_token}});
                  if(!r.ok)throw Error('Modül oturumu doğrulanamadı');return (await r.json()).moduller.map(m=>m.yol);})()""")
                if person in ('K001','K004'):
                    assert 'proje-planlama' in visible,'Proje Planlama devrede olmalı'
                    browser.js("location.hash='modules/proje-planlama'")
                    browser.wait("!!document.querySelector('[data-proje]') || document.body.innerText.includes('Önce Bir Proje Oluşturun')",45)
                    assert not browser.js("!!document.querySelector('iframe') || !!document.querySelector('#module-workspace .notice.warn')")
                else:assert 'proje-planlama' not in visible,'Menü yetkisi dışarıya açılmamalı'
                if person=='K001':
                    assert {'teklif-yonetimi','siparis-butce','proje-planlama'}<=set(visible)
                    for slug,marker in [('teklif-yonetimi','[data-m10=yeni-talep]'),
                                        ('siparis-butce','[data-m11a=sayfa][data-view=donustur]')]:
                        browser.js('location.hash='+json.dumps('modules/'+slug))
                        browser.wait('!!document.querySelector('+json.dumps(marker)+')',45)
                        assert not browser.js("!!document.querySelector('#module-workspace .notice.warn') || !!document.querySelector('iframe')")
                    assert browser.js("getComputedStyle(document.body).backgroundColor")=='rgb(255, 255, 255)'
                else:
                    assert 'teklif-yonetimi' not in visible and 'siparis-butce' not in visible,'Ticari menü yetkisi dışarıya açılmamalı'
                print('Canlı modül: '+title+' / ortak oturum ve menü yetkisi geçti.',flush=True)
            assert not browser.errors,'Canlı tarayıcı hatası'
            print('Canlı okuma: '+title+' / '+', '.join(pages)+' geçti.',flush=True)
        finally:
            browser.close()
    observer=Browser()
    try:
        observer.navigate('http://localhost:8080/olaylar.html')
        observer.wait("document.querySelector('#connection-label')?.textContent==='Canlı Bağlantı'",45)
        assert observer.js("document.querySelector('#event-count').textContent")=='0'
        assert not observer.errors,'Canlı izleyici tarayıcı hatası'
        print('Canlı okuma: bağımsız olay izleyicisi bağlandı; geçmiş olaylar başlangıç ekranına taşınmadı.',flush=True)
    finally:observer.close()


if __name__=='__main__':
    run('--moduller' in sys.argv)
