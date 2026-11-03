"""Tur 1: gerçek web/Dart/SQL; ayrı firma ve yerel dosya taşıması.

Canlı ayar/veri/telefon kullanılmaz. Depo taklidinin yetki kararı gerçek SQL'dir;
bu sınama Supabase Storage'ın canlı politikasının yerine geçmez.
"""
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import threading

from tarayici import Browser, page, click, field, submit
from senaryo1_sina import profile
from yerel_api import Database, ApiServer


def run():
    db = server = browser = None
    try:
        db = Database(empty=True)
        server = ApiServer(db, Path(__file__).resolve().parents[1] / 'build')
        threading.Thread(target=server.serve_forever, daemon=True).start()
        browser = Browser()
        browser.navigate(f'http://127.0.0.1:{server.server_port}/')
        browser.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",45)
        # Sadece test sayfasında gerçek uygulama istemcisine gözlem kancası.
        browser.js("""(async()=>{const {IrpClient}=await import('./client.js');
          const read=IrpClient.prototype.read;IrpClient.prototype.read=function(...args){window.tur1C=this;return read.apply(this,args);};})()""")
        page(browser,'projects')
        browser.wait('!!window.tur1C')

        def read(person, kind, target=None):
            return db.rpc(person,'oku',{'veri':kind,'hedef':target,'g':{}})['deger']

        def open_form(code, record=None, refs=None):
            browser.js("(async()=>{const {openOperation}=await import('./forms.js');await openOperation(tur1C,"+json.dumps(code)+",{record:"+json.dumps(record)+",refs:"+json.dumps(refs or {})+"});})()")

        # Pencere açılırken iki tık, eksik tarih yazımı, odak ve takvim seçimi.
        browser.js("(()=>{const b=document.querySelector('[data-code=\"PROJE.ACTIM\"]');b.click();b.click();})()")
        browser.wait("!!document.querySelector('dialog[open] [data-path=ad]')")
        assert browser.js("document.querySelectorAll('dialog[open]').length")==1
        field(browser,'kod','TUR1');field(browser,'ad','Tur 1 Kabul')
        field(browser,'teslim_tarihi','07.11.2')
        click(browser,'dialog[open] [type=submit]')
        browser.wait("document.querySelector('[data-path=teslim_tarihi]').getAttribute('aria-invalid')==='true'")
        assert read('K001','PROJELER')==[]
        due=(date.today()+timedelta(days=14)).isoformat()
        browser.js("(()=>{const p=document.querySelector('[data-date-picker=teslim_tarihi]');p.value="+json.dumps(due)+";p.dispatchEvent(new Event('change',{bubbles:true}));})()")
        assert browser.js("document.querySelector('[data-path=teslim_tarihi]').value")==date.fromisoformat(due).strftime('%d.%m.%Y')
        # Motor kabul ettikten sonraki okuma hatası ikinci proje doğurmamalı.
        browser.js("window.tur1Refresh=tur1C.refresh;tur1C.refresh=async()=>{throw Error('Test: kabul sonrası okuma kesildi');}")
        submit(browser)
        assert len(read('K001','PROJELER'))==1
        assert browser.js("document.querySelector('.toast')?.textContent.includes('kabul edildi')")
        browser.js("tur1C.refresh=window.tur1Refresh;tur1C.refresh()")
        print('Tur 1 web: tek pencere, kısmi tarih/alan hatası, takvim ve kabul sonrası okuma kesintisi geçti.',flush=True)

        tomorrow=(date.today()+timedelta(days=1)).strftime('%d.%m.%Y')
        profile(browser,'K041','Ofis Çalışanı');page(browser,'leaves')
        click(browser,'[data-code="IZIN.TALEP_ETTIM"]')
        browser.wait("!!document.querySelector('dialog[open] [data-path=tur]')")
        assert not browser.js("!!document.querySelector('dialog[open] [data-path=kisi]')")
        assert browser.js("[...document.querySelector('[data-path=tur]').options].map(x=>x.value).filter(Boolean)")==['YILLIK','SAATLIK','MAZERET']
        field(browser,'tur','SAATLIK');field(browser,'baslangic',tomorrow);field(browser,'bitis',tomorrow)
        field(browser,'baslangic_saati','10:00');field(browser,'bitis_saati','11:00');field(browser,'gerekce','Tur 1 saatlik izin')
        submit(browser)
        leaves=read('K041','IZIN','K041');assert len(leaves)==1 and leaves[0]['kisi']=='K041'
        assert leaves[0]['baslangic'].endswith('10:00:00+03:00')
        profile(browser,'K004','Yönetici');page(browser,'leaves')
        open_form('IZIN.ONAYLADIM',leaves[0],{'IZIN':leaves});submit(browser)
        assert read('K041','IZIN','K041')[0]['durum']=='ONAYLI'
        # Gerçek atanmış görev, ek mesainin hedefi olarak kullanılacak.
        browser.js("""tur1C.write('GOREV.ATADIM',{gorevler:[{ad:'Tur 1 Dosyalı Teslim',nereye:'PROJE',proje:'TUR1',kisi:'K041',teslim_tarihi:"""+json.dumps(due)+""",zaman_degeri:1,zorluk:1,onay_gerekli:true,onaylayan:'K004',dosya_gerekli:true}]})""")
        task=next(x for x in read('K004','WEB_GOREVLER') if x['ad']=='Tur 1 Dosyalı Teslim')
        page(browser,'overtime');open_form('EK_MESAI.PLANLADIM',refs={'GOREV':[task]})
        field(browser,'kisi','K041');field(browser,'tarih',tomorrow);field(browser,'baslangic','21:00');field(browser,'bitis','22:00');field(browser,'aciklama','Ek mesai denemesi')
        browser.js("document.querySelector('#overtime-target').value="+json.dumps('GOREV:'+task['kimlik']))
        submit(browser)
        extras=read('K004','WEB_KAYNAKLAR')['ek_mesai'];assert len(extras)==1
        open_form('EK_MESAI.IPTAL_ETTIM',extras[0],{'EK_MESAI':extras});submit(browser)
        assert read('K004','WEB_KAYNAKLAR')['ek_mesai'][0]['iptal']
        print('Tur 1 web: kendi saatlik izni/onay, gerçek işe bağlı ek mesai planı/iptali geçti.',flush=True)

        profile(browser,'K041','Ofis Çalışanı');page(browser,'tasks')
        click(browser,'tr[data-id="'+task['kimlik']+'"]');click(browser,'[data-code="GOREV.KABUL_ETTIM"]')
        browser.wait("document.querySelector('.task-detail h2')?.textContent==='Görevinizi Seçin'")
        assert browser.js("document.querySelector('.tab.active').dataset.tab")=='waiting'
        click(browser,'[data-action=tab][data-tab=open]');click(browser,'tr[data-id="'+task['kimlik']+'"]')
        click(browser,'[data-code="GOREV.TAMAMLADIM"]')
        browser.wait("!!document.querySelector('#operation-files')")
        click(browser,'dialog[open] [type=submit]')
        browser.wait("document.querySelector('#operation-files').getAttribute('aria-invalid')==='true'")
        contents='Tur 1 gerçek dosya baytları.\n'
        with tempfile.TemporaryDirectory(prefix='irp-tur1-dosya-') as temp:
            file=Path(temp)/'tur1.txt';file.write_text(contents)
            def attach():
                node=browser.call('DOM.querySelector',nodeId=browser.call('DOM.getDocument')['root']['nodeId'],selector='#operation-files')['nodeId']
                browser.call('DOM.setFileInputFiles',nodeId=node,files=[str(file)])
            attach();submit(browser)
            profile(browser,'K004','Yönetici');page(browser,'approvals')
            click(browser,'[data-action=quick-approve][data-id="'+task['kimlik']+'"]')
            browser.wait("!!document.querySelector('dialog[open] [data-action=approval-file]')")
            fileid=browser.js("document.querySelector('[data-action=approval-file]').dataset.id")
            assert browser.js("(async()=>{const url=await tur1C.fileUrl("+json.dumps(fileid)+");return (await fetch(url)).text();})()")==contents
            click(browser,'dialog[open] [data-continue]');browser.wait("!document.querySelector('dialog[open]')")
            assert read('K041','GOREV',task['kimlik'])['durum']=='BITTI'
            # Boş firmadaki temel tür ile belge sürümünün ayrı kişi tarafından onayı.
            profile(browser,'K041','Ofis Çalışanı');page(browser,'objects')
            open_form('NESNE.ACTIM');field(browser,'tur','BELGE');field(browser,'ad','Tur 1 Belgesi');field(browser,'sorumlu','K041');field(browser,'proje','TUR1');submit(browser)
            objects=read('K041','NESNELER','TUR1');obj=next(x for x in objects if x['ad']=='Tur 1 Belgesi')
            open_form('NESNE.SURUM_EKLEDIM',obj,{'NESNE':[obj]});field(browser,'surum_adi','İlk Sürüm');attach();submit(browser)
            versions=read('K041','SURUMLER',obj['kimlik']);assert len(versions)==1
            profile(browser,'K004','Yönetici');page(browser,'objects')
            open_form('NESNE.SURUM_ONAYLADIM',obj,{'NESNE':[obj]});field(browser,'surum_no',1);submit(browser)
            assert read('K004','GECERLI_SURUM',obj['kimlik'])['surum_no']==1
            open_form('NESNE.SURUM_GERI_CEKTIM',obj,{'NESNE':[obj]});field(browser,'surum_no',1);field(browser,'gerekce','Teknik kabul tamamlandı');submit(browser)
            assert not read('K004','GECERLI_SURUM',obj['kimlik'])
        assert not browser.errors,browser.errors
        print('Tur 1 web: zorunlu dosya/alan, onayda gerçek indirme, teslim onayı, temel belge/sürüm/onay/geri çekme geçti.',flush=True)
    finally:
        if browser:browser.close()
        if server:server.shutdown();server.server_close()
        if db:db.close()


if __name__=='__main__':run()
