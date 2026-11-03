"""Tur3: ayrı firmada normal atölye webi ve gerçek SQL, canlı veriye dokunmaz."""
from datetime import date, timedelta
from pathlib import Path
import json, sys, threading, subprocess, time, os
import psycopg
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from tarayici import Browser,page,click,field,submit
from yerel_api import Database,ApiServer
from senaryo1_sina import profile,wait_state
OUT=Path(os.environ.get('IRP_TUR3_OUT',str(HERE.parents[2]/'codex/sonuclar/tur3_atolye_kanit')))
OUT.mkdir(parents=True,exist_ok=True)

def run():
    db=server=b=None;checks=[];complete=False
    try:
        db=Database(empty=True)
        server=ApiServer(db,HERE.parent/'build')
        threading.Thread(target=server.serve_forever,daemon=True).start()
        b=Browser(1440,1000);b.ws.settimeout(60)
        origin=f'http://127.0.0.1:{server.server_port}'
        b.navigate(origin);b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",60)
        def ok(s):checks.append(s);print('GEÇTİ: '+s,flush=True)
        def read(v,h=None):return db.rpc('K004','oku',{'veri':v,'hedef':h})['deger']
        def op(c,scope=''):
            click(b,scope+'[data-code="'+c+'"]');b.wait("!!document.querySelector('dialog[open] form')")
        def refresh():
            click(b,'#refresh');b.wait("!document.querySelector('.loading-line')")
        def job(name):return next(x for x in read('WEB_ISLER') if (x.get('islem') or x.get('is_tanimi'))==name)
        def ready():b.wait("!document.querySelector('.loading-line')")
        def create(name,**extra):
            op('IS.TANIMLADIM')
            for k,v in {'islem':name,'proje':'T3-KONTROL','etap':'@none',**extra}.items():field(b,k,v)
            submit(b);ready();return job(name)
        def move(code,j,person='K017',position=None):
            expected=position or len([r for r in read('LISTE',person)['isler'] if r['kimlik']!=j['kimlik']])+1
            row='[data-job="'+j['kimlik']+'"] '
            if code!='IS.ATADIM':
                click(b,row+'[data-action=job-menu]')
                b.wait("!!document.querySelector('.work-detail')")
            op(code,row if code=='IS.ATADIM' else 'dialog[open] ')
            if code!='IS.SIRALADIM':field(b,'person',person)
            b.wait("!!document.querySelector('[data-path=position] option[value=\""+str(expected)+"\"]')&&!document.querySelector('dialog[open] [type=submit]').disabled")
            if position is None:assert b.js("document.querySelector('[data-path=position]').value")==str(expected)
            else:field(b,'position',position)
            submit(b);ready()
        page(b,'projects');op('PROJE.ACTIM')
        for k,v in {'kod':'T3-KONTROL','ad':'Atölye Akışı Kontrolü','sorumlu':'K004','teslim_tarihi':(date.today()+timedelta(days=14)).strftime('%d.%m.%Y')}.items():field(b,k,v)
        submit(b);profile(b,'K004','Yönetici');page(b,'workshop')
        b.js("(()=>{const e=document.querySelector('[data-filter=unit]');e.value='IMALAT';e.dispatchEvent(new Event('change',{bubbles:true}));})()")
        ready()
        assert b.js("document.querySelectorAll('#main [data-code=\"IS.TANIMLADIM\"]').length")==1
        assert not b.js("document.querySelector('#main').innerText.includes('Seçili Nesne')")
        op('IS.TANIMLADIM');assert b.js("document.querySelector('[data-path=proje]').value") == ''
        field(b,'islem','Birinci İş');field(b,'proje','T3-KONTROL')
        click(b,'dialog[open] [type=submit]');b.wait("document.querySelector('[data-path=etap]')?.getAttribute('aria-invalid')==='true'")
        assert b.js("document.querySelector('[data-path=islem]').value")=='Birinci İş'
        field(b,'etap','@none');assert not b.js("!!document.querySelector('[data-path=etap][aria-invalid=true]')");assert not b.js("!!document.querySelector('dialog[open] [data-path=kisi]')");field(b,'onay_beklet',True)
        b.screenshot(OUT/'01_yeni_is.png');submit(b);ready();a=job('Birinci İş')
        second=create('İkinci İş');third=create('Üçüncü İş')
        assert b.js("[...document.querySelectorAll('.work-pool-item')].every(r=>r.getBoundingClientRect().height<130 && r.querySelector('.row-actions').getBoundingClientRect().top < r.querySelector('.work-meta').getBoundingClientRect().top)")
        b.screenshot(OUT/'00_sik_havuz.png')
        ok('Havuz satırları 130 pikselden kısa; Ayrıntı/Ata ilk satırda sağda')
        ok('Tek Yeni İş, boş proje, açık etap seçimi, alan hatası ve girilen değerlerin korunması')
        move('IS.ATADIM',a);move('IS.ATADIM',second);move('IS.ATADIM',third)
        ok('Ata düğmesinde boş liste 1, dolu liste 2 ve 3: varsayılan en son sıra')
        assert [r['islem'] for r in read('LISTE','K017')['isler']]==['Birinci İş','İkinci İş','Üçüncü İş']
        b.screenshot(OUT/'02_havuz_sirali_isler.png')
        # Gerçek DOM sürükleme: üçüncü iş ikinci satırın önüne bırakılır.
        b.js("""(()=>{const d=new DataTransfer(),s=document.querySelector('[data-job="%s"]'),t=document.querySelector('[data-job="%s"]');s.dispatchEvent(new DragEvent('dragstart',{bubbles:true,dataTransfer:d}));const y=t.getBoundingClientRect().top+2;t.dispatchEvent(new DragEvent('dragover',{bubbles:true,dataTransfer:d,clientY:y}));t.dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:d,clientY:y}));})()"""%(third['kimlik'],second['kimlik']))
        b.wait("!!document.querySelector('dialog[open] [data-path=position] option[value=\"2\"]')&&!document.querySelector('dialog[open] [type=submit]').disabled")
        assert b.js("document.querySelector('[data-path=position]').value")=='2'
        assert b.js("[...document.querySelectorAll('.queue-preview li')].map(x=>x.textContent)")==['Birinci İş','Üçüncü İş','İkinci İş']
        submit(b);ready();assert [r['islem'] for r in read('LISTE','K017')['isler']]==['Birinci İş','Üçüncü İş','İkinci İş']
        ok('Üç gerçek atama ve satır arasına sürükleyerek tam ikinci sıraya yerleştirme')
        # Ayrıntı, sabit hedef ve düzenleme; modal işlemler iç içe açılmamalı.
        click(b,'[data-job="'+third['kimlik']+'"] [data-action=job-menu]')
        b.wait("!!document.querySelector('.work-detail')")
        assert b.js("document.querySelector('dialog[open]').innerText.includes('İş Bilgileri')")
        click(b,'dialog[open] [data-code="IS.DEGISTIRDIM"]');b.wait("!!document.querySelector('[data-path=\"degisenler.islem\"]')")
        assert not b.js("!!document.querySelector('dialog[open] [data-target]')")
        field(b,'degisenler.islem','Üçüncü İş Düzenlendi');field(b,'degisenler.is_tanimi','T3.1 açıklama: ölçüleri tek tek kontrol edin.');submit(b);ready()
        assert read('IS',third['kimlik'])['islem']=='Üçüncü İş Düzenlendi'
        assert read('IS',third['kimlik'])['is_tanimi']=='T3.1 açıklama: ölçüleri tek tek kontrol edin.'
        ok('İş ayrıntısı, sabit hedefle düzenleme; tekrar iş seçimi ve ham kod yok')
        move('IS.DEVRETTIM',third,person='K031',position=1)
        assert read('IS',third['kimlik'])['kisi']=='K031'
        assert third['kimlik'] not in [r['kimlik'] for r in read('LISTE','K017')['isler']]
        assert read('LISTE','K031')['isler'][0]['kimlik']==third['kimlik']
        ok('Yetkili ekipler arası devir; kaynak listeden çıkarma ve hedef sıraya koyma')
        click(b,'[data-action=work-unplanned][data-person=K017]');b.wait("!!document.querySelector('[data-path=is_tanimi]')")
        for k,v in {'is_tanimi':'Plansız Kontrol','proje':'T3-KONTROL','etap':'@none'}.items():field(b,k,v)
        assert not b.js("!!document.querySelector('dialog[open] input[data-path=sira]')")
        assert b.js("document.querySelector('[data-path=position]').value")=='3'
        field(b,'position',2)
        assert b.js("document.querySelector('.queue-preview li:nth-child(2)').innerText")=='Plansız Kontrol'
        b.screenshot(OUT/'05_plansiz_sira.png')
        submit(b);ready();unplanned=job('Plansız Kontrol')
        assert read('LISTE','K017')['isler'][1]['kimlik']==unplanned['kimlik']
        ok('Plansız iş: sabit kişi, tanım ve seçilen sıra tek gerçek olayda')
        instant=create('Anlık Kontrol',tur='ANLIK')
        assert instant['tahmini_sure_dk']==0 and instant['tur']=='ANLIK'
        multiple=create('İki Kişilik Kontrol',kisi_sayisi=2)
        op('IS.ATADIM','[data-job="'+multiple['kimlik']+'"] ')
        for person in ['K017','K031']:click(b,'[data-worker][value='+person+']')
        b.wait("document.querySelectorAll('.queue-preview').length===2&&!document.querySelector('dialog[open] [type=submit]').disabled")
        ends={p:len(read('LISTE',p)['isler'])+1 for p in ['K017','K031']}
        assert len(set(ends.values()))>1,'Farklı uzunlukta listeler sınanmalı'
        assert b.js("document.querySelector('[data-path=position]').value")==str(max(ends.values()))
        assert b.js("document.querySelector('[data-path=position]').selectedOptions[0].textContent")=='Her Listede En Son'
        assert b.js("[...document.querySelectorAll('.queue-preview ol')].every(l=>l.lastElementChild.classList.contains('queue-changed'))")
        submit(b);ready()
        children=[x for x in read('WEB_ISLER') if x.get('ana_is')==multiple['kimlik']]
        assert len(children)==2 and {x['kisi'] for x in children}=={'K017','K031'}
        assert all(x['tahmini_sure_dk']==60 for x in children)
        for child in children:assert read('LISTE',child['kisi'])['isler'][-1]['kimlik']==child['kimlik']
        assert read('IS',multiple['kimlik'])['tahmini_sure_dk']==120
        ok('Anlık işte sıfır süre; çok kişili iş farklı uzunluktaki her listenin sonunda, ayrı çocuk/emek')
        # Gerçek kabul yapıldıktan sonra yalnız yayın yanıtı geciktirilir.
        pending=create('Geciken Sonuç Kontrolü')
        original=db.rpc;gate={'release':False,'id':None,'writes':0}
        def delayed(person,name,params):
            if name=='olay_ekle' and params.get('olay',{}).get('eylem_kodu')=='IS.ATADIM':
                gate['id']=params['olay']['olay_kimligi'];gate['writes']+=1
            if name=='islem_sonucu' and params.get('olay_kimligi')==gate['id'] and not gate['release']:return {'durum':'BEKLIYOR'}
            return original(person,name,params)
        db.rpc=delayed
        op('IS.ATADIM','[data-job="'+pending['kimlik']+'"] ');field(b,'person','K017')
        b.wait("!!document.querySelector('[data-path=position] option[value=\"5\"]')&&!document.querySelector('dialog[open] [type=submit]').disabled")
        field(b,'position',5);click(b,'dialog[open] [type=submit]')
        b.wait("document.querySelector('dialog[open] [type=submit]')?.disabled===true")
        time.sleep(1)
        assert gate['writes']==1 and b.js("!!document.querySelector('dialog[open]')")
        b.js("document.querySelector('dialog[open] [type=submit]').click()")
        assert gate['writes']==1
        gate['release']=True;b.wait("!document.querySelector('dialog[open]')",30);db.rpc=original;ready()
        ok('Gecikmiş yayın: pencere ve pasif düğme sonucu bekler; ikinci tıklama ikinci olay üretmez')
        # İki roldeki çalışan işi telefonun Dart çekirdeğiyle başlatır/tamamlar.
        dart=Path.home()/'development/flutter/bin/cache/dart-sdk/bin/dart'
        packages=HERE.parents[1]/'uygulama/.dart_tool/package_config.json'
        subprocess.run([str(dart),'--packages='+str(packages),str(HERE/'telefon_motor.dart'),origin],check=True)
        wait_state(db,'IS',a['kimlik'],'ONAY_BEKLIYOR','K004')
        wait_state(db,'IS',third['kimlik'],'ONAY_BEKLIYOR','K004')
        page(b,'approvals');op('IS.REDDETTIM')
        click(b,'dialog[open] [type=submit]');b.wait("!!document.querySelector('dialog[open] .form-error').textContent")
        field(b,'not','Montaj kontrolünü düzeltin.');submit(b);ready()
        ok('Telefon çekirdeği gerçek teslimleri; iş onayı listesinde görünme ve gerekçeli ret')
        # İnceleme onayı artık duruştan devam olarak sunulmuyor.
        profile(b,'K009','Ekip Lideri');page(b,'team')
        assert not b.js("!!document.querySelector('tr[data-id=K009]')")
        b.call('Emulation.setEmulatedMedia',features=[{'name':'prefers-color-scheme','value':'dark'}])
        page(b,'workshop')
        assert b.js("getComputedStyle(document.body).backgroundColor") in ['rgb(255, 255, 255)','rgb(246, 248, 250)','rgb(247, 249, 252)']
        for width in [1440,960]:
            b.call('Emulation.setDeviceMetricsOverride',width=width,height=1000,deviceScaleFactor=1,mobile=False)
            assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
        assert not b.js(r"/K\d{3}-\d{10}-[A-Z]|IS\.[A-Z_]+/.test(document.querySelector('#main').innerText)")
        b.screenshot(OUT/'03_lider_dar_pencere.png')
        ok('Lider kendisini ekipte görmez; karanlık sistem ayarında beyaz web, dar pencere, teknik kimliksiz metin')
        complete=True
    finally:
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'sonuc.json').write_text(json.dumps({'tamamlandi':complete,'kontroller':checks},ensure_ascii=False,indent=2))
        if b:
            if not complete:
                try:b.screenshot(OUT/'hata.png');(OUT/'hata.txt').write_text(b.js('document.body.innerText'))
                except Exception:pass
            b.close()
        if server:server.shutdown();server.server_close()
        if db:db.close()
if __name__=='__main__':run()
