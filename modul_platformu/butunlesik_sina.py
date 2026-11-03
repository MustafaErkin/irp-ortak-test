"""Üç modülün gerçek SQL/normal kullanıcı/geçit akışı. Canlı firmaya bağlanmaz."""
from contextlib import contextmanager
from contextlib import redirect_stdout
from io import StringIO
from datetime import date
import functools
import hashlib
import base64
import json
from pathlib import Path
import sys
import shutil
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime/python'),str(ROOT/'istemci/web/test')]
from yerel_api import Database,ApiServer
from istemci.web.sunucu import YerelSunucu,Isleyici
from modul_platformu.gecit import Platform,http,Hata
from modul_platformu.kayit import oku
from modul_platformu.kur import kur,kimlik,kapat
from modul_platformu.isletim import Yetkili


@contextmanager
def ortam():
    import psycopg
    from psycopg import sql
    db=core=web=platform=None
    rows=oku()
    try:
        with redirect_stdout(StringIO()):
            db=Database(empty=True)
        core=ApiServer(db,ROOT/'istemci/web/build',jwt=True)
        threading.Thread(target=core.serve_forever,daemon=True).start()
        env={'IRP_SB_TEST_DB':db.dsn,'IRP_SB_TEST_URL':f'http://127.0.0.1:{core.server_port}',
             'IRP_SB_TEST_ANON':'sb_publishable_yerel_test'}
        _,_,data=http(env['IRP_SB_TEST_URL']+'/auth/v1/token?grant_type=password',value={'email':'k001@calisan.irp','password':'123456'})
        actor=Yetkili(env,json.loads(data)['access_token'],'K001')
        for row in rows.values():
            kur(db.dsn,row,actor.event,actor.modul)
            assert kur(db.dsn,row,actor.event,actor.modul)['zaten_kurulu']
        webdir=tempfile.TemporaryDirectory(prefix='irp-moduller-web-')
        shutil.copytree(ROOT/'istemci/web/build',webdir.name,dirs_exist_ok=True)
        for pattern in ('*.js','*.css','*.html'):
            for source in (ROOT/'istemci/web').glob(pattern):
                if source.name!='service_worker.js':shutil.copyfile(source,Path(webdir.name)/source.name)
        config={'bulut':'SUPABASE','supabase_url':env['IRP_SB_TEST_URL'],'supabase_anon':env['IRP_SB_TEST_ANON'],
                'gosteri_kisileri':[{'kod':k,'etiket':v,'sifre':'123456'} for k,v in core.roles.items() if k in ('K001','K004','K009','K041')]}
        (Path(webdir.name)/'ayar.json').write_text(json.dumps(config))
        web=YerelSunucu(('127.0.0.1',0),functools.partial(Isleyici,directory=webdir.name))
        folder=tempfile.TemporaryDirectory(prefix='irp-modul-dosyalar-')
        env['IRP_MODUL_DOSYA_DIZINI']=folder.name
        platform=Platform(env=env);web.platform=platform
        threading.Thread(target=web.serve_forever,daemon=True).start()
        platform.start(web.server_port)
        base=f'http://127.0.0.1:{web.server_port}'
        def api(code,path,method='GET',value=None,expected=200,token=None):
            status,headers,body=http(base+'/irp/moduller/'+code+'/api'+path,method=method,value=value,
                headers={'Content-Type':'application/json','Authorization':'Bearer '+(token or actor.token)})
            assert status==expected,(code,path,status,body[:1600].decode(errors='replace'))
            if headers.get('Content-Type','').startswith('application/pdf') or body.startswith(b'%PDF'):
                return body
            return json.loads(body)
        yield db,core,web,platform,actor,api
    finally:
        if platform:platform.close()
        if 'folder' in locals():folder.cleanup()
        if web:web.shutdown();web.server_close()
        if 'webdir' in locals():webdir.cleanup()
        if core:core.shutdown();core.server_close()
        if db:
            roles=[kimlik(db.dsn,code)[0] for code in rows]
            db.close()
            with psycopg.connect('postgresql://postgres@localhost:5433/postgres',autocommit=True) as c:
                for role in roles:
                    c.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))
                    c.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role+'_sahibi')))


def main():
    with ortam() as (db,core,web,platform,actor,api):
        customer=api('M10','/musteriler','POST',{'ad':'Sınama Müşterisi','ulke':'TR'},201)
        demand=api('M10','/talepler','POST',{'musteri':customer['kimlik'],'kaynak':'YENI_IS','tur':'KURUMSAL_SARTNAME',
            'konu':'Gerçek Entegrasyon Makinesi','gereksinimler':[{'metin':'İşlevsel deneme'}],
            'kapsam':{'dahil':['Tasarım ve üretim']}},201)
        uploaded=api('M10','/ortak-dosyalar','POST',{'kayit':{'tur':'TALEP','kimlik':str(demand['kimlik'])},
            'ad':'sartname.txt','icerik_base64':base64.b64encode('Gerçek fiziksel dosya'.encode()).decode(),'tur':'text/plain'})
        assert api('M10','/ortak-dosyalar/'+uploaded['kimlik'])['parmak_izi']==uploaded['parmak_izi']
        duplicate=api('M10','/ortak-dosyalar','POST',{'kayit':{'tur':'TALEP','kimlik':str(demand['kimlik'])},
            'ad':'sartname.txt','icerik_base64':base64.b64encode('Gerçek fiziksel dosya'.encode()).decode(),'tur':'text/plain'})
        assert duplicate['kimlik']==uploaded['kimlik']
        api('M10','/ortak-dosyalar','POST',{'kayit':{'tur':'TALEP','kimlik':str(demand['kimlik'])},
            'ad':'buyuk.txt','icerik_base64':base64.b64encode(b'x'*1048577).decode()},expected=413)
        actual_file=Path(platform.env['IRP_MODUL_DOSYA_DIZINI'])/uploaded['kimlik']
        original_bytes=actual_file.read_bytes();actual_file.write_bytes(b'Bozuk icerik')
        try:api('M10','/ortak-dosyalar/'+uploaded['kimlik'],expected=503)
        finally:actual_file.write_bytes(original_bytes)
        api('M10',f'/talepler/{demand["kimlik"]}/dosyalar','POST',
            {'tur':'SARTNAME',**{k:uploaded[k] for k in ('ad','konum','parmak_izi')}},201)
        version=api('M10',f'/talepler/{demand["kimlik"]}/surumler','POST',{'kaynak':'BOS'},201)
        schedule=api('M10',f'/surumler/{version["kimlik"]}/takvim/sablondan','POST',{'toplam_hafta':6})['satirlar']
        version=api('M10',f'/surumler/{version["kimlik"]}','PUT',{'surum':version['surum'],'para_birimi':'TRY',
            'fiyat_girisi':'FIYAT','fiyat':'12000.00','toplam_hafta':6,'teslim_suresi_hafta':6,'gecerlilik_gun':30,
            'kalemler':[{'unsur':'ROBOT','aciklama':'Sınama Malzemesi','adet':'1','birim_fiyat':'10000.00','para_birimi':'TRY'}],
            'takvim':[{k:r[k] for k in ('etap_kodu','ad','paralel_grup','baslangic_hafta','sure_hafta')} for r in schedule]})
        for action,body in [('onaya-gonder',{}),('onayla',{}),('gonderildi',{'gonderim_sekli':'E_POSTA'})]:
            version=api('M10',f'/surumler/{version["kimlik"]}/{action}','POST',dict(body,surum=version['surum']))
            if action=='onaya-gonder':
                notices=actor.rpc('oku',{'veri':'BILDIRIMLER','hedef':'K001','g':{}})['deger']
                assert 'Teklif onayınızı bekliyor' in json.dumps(notices,ensure_ascii=False),notices
        pdf=api('M10',f'/surumler/{version["kimlik"]}/pdf');assert pdf.startswith(b'%PDF')
        api('M10',f'/talepler/{demand["kimlik"]}/sonuc','POST',{'sonuc':'KAZANILDI','kazanan_surum':version['kimlik']})
        options=api('M11A','/donustur/secenekler');assert options['surumler'][0]['surum']==version['kimlik']
        preview=api('M11A',f'/donustur/onizleme?surum={version["kimlik"]}')
        today=actor.rpc('simdi',{})[:10]
        payload={'surum':version['kimlik'],'proje_kodu':'ENTEGRASYON-1',
            'proje_adi':demand['konu'],'sorumlu':'K004','siparis_tarihi':today,'teslim_tarihi':'2026-12-18'}
        original_rpc=platform.rpc
        def lost_response(code,name,body,authorization):
            result=original_rpc(code,name,body,authorization)
            if code=='M11A' and name=='olay_ekle' and body['olay']['girdiler'].get('kod')=='ENTEGRASYON-1':
                raise Hata(503,'IRP|BAGLANTI|Sınama: çekirdek kabulü sonrası yanıt kaybı')
            return result
        platform.rpc=lost_response
        try:
            pending=api('M11A','/donustur','POST',payload,expected=503)
            assert any(p['proje']=='ENTEGRASYON-1' and p['durum']=='ACILIYOR' for p in api('M11A','/projeler')['projeler'])
        finally:platform.rpc=original_rpc
        # Süreci yeniden başlat: dosya/sayaç dışındaki bellek geri alma için yeterli değildir.
        platform.children['M11A'].terminate();platform.children['M11A'].wait(timeout=10)
        platform.start(web.server_port)
        order=api('M11A','/donustur/ENTEGRASYON-1/yeniden-dene','POST',{})
        import psycopg
        with psycopg.connect(db.dsn) as conn:
            assert conn.execute("SELECT count(*) FROM public.olaylar WHERE icerik->>'eylem_kodu'='PROJE.ACTIM' AND icerik->'girdiler'->>'kod'='ENTEGRASYON-1'").fetchone()[0]==1
        api('M11A','/donustur','POST',payload,expected=409)
        print('Yanıt kaybı + modül yeniden başlatma: aynı kalıcı zarfla tek proje/tek olay doğrulandı.',flush=True)
        print('M10 → M11A: gerçek teklif/onay/PDF/kazanım, SDK sağlayıcısı ve proje açılışı geçti.',flush=True)
        print('Sipariş cevabı alanları:',','.join(order),flush=True)
        p=order['proje']
        source=api('M11A',f'/projeler/{p}/baslangic-plani')
        transfer=api('M11B',f'/projeler/{p}/devir','POST',{})
        assert transfer['siparis_kaynagi']['durum']=='AKTARILDI',transfer
        assert api('M11B',f'/projeler/{p}/devir','POST',{})['siparis_kaynagi']['tekrar']
        imported=api('M11B',f'/projeler/{p}/siparis-kaynagi')
        assert imported['plan']==source and imported['girdiler']['gereksinimler'][0]['metin']=='İşlevsel deneme'
        plan=api('M11B',f'/projeler/{p}/plan')
        assert len(plan['satirlar'])==len(source['etaplar'])
        assert plan['satirlar'][0]['bitis']==source['etaplar'][0]['bitis']
        for row in plan['satirlar']:
            row.update(birim='MEK_TASARIM',sorumlu='K004',hedef_saat=20)
        api('M11B',f'/projeler/{p}/plan/taslak','PUT',{'satirlar':plan['satirlar']})
        approved=api('M11B',f'/projeler/{p}/plan/gonder','POST',{})
        assert approved['b0_var'] and len(approved['cekirdek_surumleri'])==1
        print('M11A → M11B: gerçek donmuş plan/girdi devri, tekrar güvenliği ve çekirdek B0 onayı geçti.',flush=True)
        def user(person):
            status,_,body=http(actor.env['IRP_SB_TEST_URL']+'/auth/v1/token?grant_type=password',value={'email':person.lower()+'@calisan.irp','password':'123456'})
            assert status==200
            a=Yetkili.__new__(Yetkili);a.env=actor.env;a.token=json.loads(body)['access_token'];a.person=person;a.last=None
            a.device='WEB-BUTUNLESIK-SINAMA-'+person;a.letter=a.rpc('cihaz_kaydol',{'cihaz':a.device});return a
        manager=user('K004');employee=user('K041')
        folders=api('M11B',f'/projeler/{p}/klasorler')['klasorler']
        files=[d for f in folders for d in f['dosyalar'] if d['tur']=='TASARIM_GIRDISI']
        assert len(files)==1
        downloaded=api('M11B','/ortak-dosyalar/'+files[0]['konum'][10:],token=manager.token)
        assert base64.b64decode(downloaded['icerik_base64']).decode()=='Gerçek fiziksel dosya'
        api('M10','/ortak-dosyalar/'+uploaded['kimlik'],token=employee.token,expected=403)
        status,_,_=http(f'http://127.0.0.1:{web.server_port}/irp/cekirdek/M10/rest/v1/rpc/modul_dosya_oku',
            value={'kimlik':uploaded['kimlik']},headers={'Authorization':'Bearer '+employee.token,'Content-Type':'application/json'})
        assert status==403
        target=api('M11B',f'/projeler/{p}/gorevler')['etaplar'][0]
        assigned=api('M11B',f'/projeler/{p}/gorevler','POST',{'etap':target['kimlik'],'ad':'Gerçek Görev Zinciri',
            'kisiler':['K041'],'teslim_tarihi':'2026-12-10','zaman_degeri':2,'onay_gerekli':True,'onaylayan':'K004','dosya_gerekli':False})
        task=assigned['sonuclar'][0]['gorev']
        def task_event(who,action,identity):
            state=who.rpc('oku',{'veri':'GOREV','hedef':identity,'g':{}})['deger']
            assert who.event(action,{},[{'tur':'GOREV','kimlik':identity,'surum':state['surum']}])['sonuc']=='BASARILI'
        task_event(employee,'GOREV.KABUL_ETTIM',task);task_event(employee,'GOREV.TAMAMLADIM',task)
        task_event(manager,'GOREV.ONAYLADIM',task)
        assert any(g.get('durum')=='BITTI' for stage in api('M11B',f'/projeler/{p}/gantt')['etaplar'] for g in stage.get('gorevler',[]))
        progress=actor.rpc('oku',{'veri':'PROJE_DURUM','hedef':p,'g':{}})['deger']['yuzde']
        assert progress>0 and api('M11A',f'/projeler/{p}/butce')['serit']['ilerleme_yuzde']==float(progress)
        api('M11A',f'/projeler/{p}/devir','POST',{})
        api('M11A',f'/projeler/{p}/devir/aldim','POST',{})
        api('M11A',f'/projeler/{p}/devir/tamamla','POST',{},expected=409)
        contract=api('M11A','/ortak-dosyalar','POST',{'kayit':{'tur':'PROJE','kimlik':p},'ad':'sozlesme.txt',
            'icerik_base64':base64.b64encode(b'Imzali sozlesme sinamasi').decode(),'tur':'text/plain'})
        api('M11A',f'/projeler/{p}/siparis','PUT',{'po_no':'PO-TEST-1',
            'sozlesme_dosyasi':{k:contract[k] for k in ('ad','konum','parmak_izi')}})
        commercial=api('M11A',f'/projeler/{p}/ticari')
        commercial_body={'surum':commercial['surum'],'faturalama_bicimi':'PESIN','teslim_sekli':'Fabrikada',
            'ihracat':False,'tesvik':'YOK','teminat_gerekli':'YOK',
            'odeme_satirlari':[{'kosul':'SIPARIS','tutar':'12000.00','para_birimi':'TRY'}],'teminatlar':[]}
        api('M11A',f'/projeler/{p}/ticari','PUT',commercial_body)
        api('M11A',f'/projeler/{p}/ticari','PUT',commercial_body,expected=409)
        api('M11A',f'/projeler/{p}/vega','PUT',{'vega_cari_kodu':'CARI-TEST','vega_proje_kodu':'PROJE-TEST'})
        assert api('M11A',f'/projeler/{p}/devir/tamamla','POST',{})['devir']['durum']=='TAMAM'
        revision={'yeni_tutar':'13000','butce':{'MALZEME':'11000','ISCILIK':'0','FASON':'0','GENEL_GIDER':'0'},
            'gerekce':'Gerçek bütçe güncelleme sınaması'}
        api('M11A',f'/projeler/{p}/tutar-degisikligi','POST',revision,expected=422)
        revision['belge_dosyasi']={k:contract[k] for k in ('ad','konum','parmak_izi')}
        api('M11A',f'/projeler/{p}/tutar-degisikligi','POST',revision)
        print('M11A: eksik devir reddi, gerçek sözleşme/ödeme, eski form reddi, muhasebe devri ve bütçe güncellemesi geçti.',flush=True)
        recipients=['K041']
        for index in range(12):
            person=f'K{100+index}'
            assert actor.event('KISI.EKLEDIM',{'kod':person,'ad':'Not Sınama Çalışanı '+str(index+1),
                'birim':'MEK_TASARIM','yaka':'BEYAZ','roller':['BEYAZ_YAKA'],'giris_tarihi':today})['sonuc']=='BASARILI'
            recipients.append(person)
        assert actor.event('AYAR.YONLENDIRDIM',{'birim':'MEK_TASARIM','kisiler':recipients})['sonuc']=='BASARILI'
        note=api('M11B',f'/projeler/{p}/notlar','POST',{'kategori':'TASARIM','alici_birim':'MEK_TASARIM','metin':'On üç gerçek alıcıya bilgi notu'})
        detail=api('M11B',f'/projeler/{p}/notlar/'+note['not_kimligi'])
        assert detail['liste_tam'] and len(detail['alicilar'])==13,detail
        note_task=next(r['gorev'] for r in detail['alicilar'] if r['kisi']=='K041')
        task_event(employee,'GOREV.KABUL_ETTIM',note_task)
        detail=api('M11B',f'/projeler/{p}/notlar/'+note['not_kimligi'])
        assert next(r['gordu'] for r in detail['alicilar'] if r['kisi']=='K041')
        print('Gerçek görev teslim/onayı ve Gantt, ortak ilerleme, fiziksel dosya devri/izin reddi, 13 not alıcısı/kabulü geçti.',flush=True)
        if '--tarayici' in sys.argv:
            browser_test(web,api,p)
        closing=api('M11A',f'/projeler/{p}/kapanis','POST',{'kesin_kabul_tarihi':today})
        assert closing['panel']['kapanis']
        api('M11A',f'/projeler/{p}/tutar-degisikligi','POST',revision,expected=409)
        api('M11A',f'/projeler/{p}/kapanis-sonrasi','POST',{'kalem':'MALZEME','tutar':'50',
            'gerekce':'Sonradan gelen fatura sınaması'})
        before=actor.rpc('oku',{'veri':'PROJELER','g':{}})['deger']
        for row in oku().values():
            role,credentials,_=kimlik(db.dsn,row['kod'])
            with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None) as connection:
                assert connection.execute('SELECT session_user').fetchone()[0]==role
                for query in ('CREATE TABLE '+row['kunye']['veritabani']['sema']+'.izinsiz_test(x int)',
                              'SELECT * FROM eklenti.dosyalar','SELECT * FROM public.olaylar'):
                    try:connection.execute(query);raise AssertionError('Dar rol sınırı aşıldı: '+row['kod'])
                    except psycopg.errors.InsufficientPrivilege:pass
            kapat(db.dsn,row,actor.event)
            api(row['kod'],'/ben',expected=403)
        assert actor.rpc('oku',{'veri':'PROJELER','g':{}})['deger']==before
        assert json.loads(http(f'http://127.0.0.1:{web.server_port}/irp/moduller',method='GET',
            headers={'Authorization':'Bearer '+actor.token})[2])['moduller']==[]
        report={'durum':'GECTI','ortam':'ayri_gecici_gercek_PostgreSQL','tarayici':'--tarayici' in sys.argv,
            'moduller':{r['kod']:r['kunye']['surum'] for r in oku().values()},
            'kontroller':['M10_musteri_talep_maliyet_takvim_onay_pdf_kazanim','gercek_ozel_onay_bildirimi',
                'M10_M11A_ayni_kullanici_saglayicisi','gercek_PROJE_ACTIM_donmus_butce',
                'yanit_kaybi_surec_yeniden_baslatma_tek_zarf_tek_proje','ayni_teklif_ikinci_donusum_ret',
                'M11A_M11B_plan_teknik_girdi_fiziksel_dosya_devri','tekrar_devir_cogaltmaz','cekirdek_B0',
                'gorev_kabul_teslim_onay_Gantt','butcede_ortak_cekirdek_ilerlemesi','13_gercek_not_alicisi_kabul','ticari_form_bayat_ret_muhasebe_devri_eksik_engeli',
                'sozlesme_gercek_dosya_odeme_vega_butce_guncelleme_kapanis_duzeltme',
                'dosya_1MB_siniri_butunluk_tekrar_izin_reddi','uc_dar_SQL_rolu_DDL_cekirdek_dosya_tablosu_reddi',
                'uc_modul_pasiflestirme_cekirdek_projelerini_korur'],
            'tarayici_kontrolleri':['yeni_musteri_talep_teklif_onay_gonderim_kazanim','siparis_proje_donusumu',
                'plan_B0','gercek_dosya_yukleme','gorev_atama','not_gonderme_gercek_alicilar',
                'beyaz_ERP_teknik_kod_yok'] if '--tarayici' in sys.argv else [],
            'gocler':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'urun/veritabani').glob('[0-9][0-9][0-9]_*.sql'))},
            'sinirlar':['Kullanıcı kabulü değildir.','Canlı firmaya sınama işi yazılmadı.',
                'MVP dosyaları mevcut sunucunun özel dizininde, en fazla 1 MB.',
                'Malzeme/fason gerçekleşeni için satın alma modülü henüz yok.','Arkadaşla paylaşım hazırlığı bu kapsamda yapılmadı.']}
        (ROOT/'codex/sonuclar/moduller_mvp.json').write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n')
        print('Üç dar SQL rolü ve veriyi koruyan modül kapatma geçti. Bütünleşik sonuç yazıldı.',flush=True)


def browser_test(web,api,project):
    from tarayici import Browser
    browser=Browser()
    try:
        base=f'http://127.0.0.1:{web.server_port}'
        browser.call('Emulation.setEmulatedMedia',features=[{'name':'prefers-color-scheme','value':'dark'}])
        browser.navigate(base+'/?kisi=K001#modules/teklif-yonetimi')
        browser.wait("!!document.querySelector('[data-m10=yeni-talep]')",40)
        browser.js("window.testSet=(selector,value)=>{const el=document.querySelector(selector);if(!el)throw Error(selector);el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}")
        browser.js("document.querySelector('[data-m10=sayfa][data-view=musteriler]').click()")
        browser.wait("!!document.querySelector('[data-m10=musteri-ekle]')")
        browser.js("document.querySelector('[data-m10=musteri-ekle]').click()")
        browser.wait("!!document.querySelector('dialog form [name=ad]')")
        browser.js("testSet('dialog form [name=ad]','Tarayıcı Müşterisi');document.querySelector('dialog form [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelector('#module-workspace').innerText.includes('Tarayıcı Müşterisi')")
        browser.js("document.querySelector('[data-m10=sayfa][data-view=talepler]').click()")
        browser.wait("!!document.querySelector('[data-m10=yeni-talep]')")
        browser.js("document.querySelector('[data-m10=yeni-talep]').click()")
        browser.wait("!!document.querySelector('dialog form [name=musteri]')")
        browser.js("""(()=>{
          const select=document.querySelector('dialog form [name=musteri]');testSet('dialog form [name=musteri]',[...select.options].find(o=>o.text==='Tarayıcı Müşterisi').value);
          testSet('dialog form [name=konu]','Tarayıcıdan Açılan Makine');testSet('dialog form [name=dahil]','Tasarım ve üretim');
          document.querySelector('dialog [data-editor-add=gereksinimler]').click();testSet('dialog [data-editor-table=gereksinimler] [name=metin]','Tarayıcıdan gerçek gereksinim');
          document.querySelector('dialog form [type=submit]').click();
        })()""")
        browser.wait("!document.querySelector('dialog') && !!document.querySelector('[data-m10=yeni-surum]')")
        browser.js("document.querySelector('[data-m10=yeni-surum]').click()")
        browser.wait("!!document.querySelector('dialog form [type=submit]')")
        browser.js("document.querySelector('dialog form [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && !!document.querySelector('[data-version-form]')")
        browser.js("""(()=>{
          const q='[data-version-form] ';for(const [key,value] of Object.entries({para_birimi:'TRY',fiyat_girisi:'FIYAT',fiyat:'15000',toplam_hafta:'6',teslim_suresi_hafta:'6',gecerlilik_gun:'30'}))testSet(q+'[name='+key+']',value);
          document.querySelector('[data-editor-add=kalemler]').click();testSet('[data-editor-table=kalemler] [name=unsur]','ROBOT');testSet('[data-editor-table=kalemler] [name=aciklama]','Gerçek Malzeme');testSet('[data-editor-table=kalemler] [name=birim_fiyat]','10000');testSet('[data-editor-table=kalemler] [name=para_birimi]','TRY');
          document.querySelector('[data-m10=takvim]').click();
        })()""")
        browser.wait("!!document.querySelector('dialog form [name=toplam_hafta]')")
        browser.js("document.querySelector('dialog form [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelectorAll('[data-editor-table=takvim] tbody tr').length===10")
        browser.js("document.querySelector('[data-m10=kaydet]').click()")
        browser.wait("document.querySelector('.metric-strip')?.innerText.includes('15.000')")
        for action in ('onaya-gonder','onayla','gonderildi'):
            browser.wait("!!document.querySelector('[data-m10="+action+"]')")
            browser.js("document.querySelector('[data-m10="+action+"]').click()")
            browser.wait("!!document.querySelector('dialog form [type=submit]')")
            browser.js("document.querySelector('dialog form [type=submit]').click()")
            browser.wait("!document.querySelector('dialog')")
        browser.wait("document.querySelector('#module-workspace').innerText.includes('Gönderildi')")
        print('Tarayıcı: yeni müşteri/talep, maliyet/takvim, kaydetme ve üç teklif geçişi gerçek API ile geçti.',flush=True)
        for view in ('musteriler','onay','ayarlar','gecmis','talepler'):
            browser.js("document.querySelector('[data-m10=sayfa][data-view="+view+"]').click()")
            browser.wait("!!document.querySelector('[data-m10=sayfa][data-view="+view+"].primary')")
            assert not browser.errors,browser.errors
        browser.js("document.querySelector('[data-m10=talep]').click()")
        browser.wait("!!document.querySelector('[data-m10=yeni-surum]')")
        browser.js("document.querySelector('[data-m10=surum]').click()")
        browser.wait("!!document.querySelector('[data-version-form]')")
        assert browser.js("getComputedStyle(document.body).backgroundColor")=='rgb(255, 255, 255)'
        assert browser.js('document.documentElement.scrollWidth<=innerWidth+1')
        browser.screenshot(ROOT/'codex/sonuclar/moduller_mvp_ekranlar/teklif.png')
        browser.js("location.hash='modules/siparis-butce'")
        browser.wait("!!document.querySelector('[data-m11a=proje]')",40)
        browser.js("document.querySelector('[data-m11a=proje]').click()")
        browser.wait("!!document.querySelector('[data-m11a=tab][data-tab=ticari]')")
        for tab,marker in [('ticari','[data-trade-form]'),('butce','[data-m11a=tutar]'),('belgeler','[data-m11a=dosya]'),('plan','[data-m11a=tab][data-tab=plan].primary')]:
            browser.js("document.querySelector('[data-m11a=tab][data-tab="+tab+"]').click()")
            browser.wait('!!document.querySelector('+json.dumps(marker)+')')
        assert browser.js(r"!document.querySelector('#module-workspace').innerText.match(/\bK\d{3}(?:-\d{10}-[A-Z])?\b/)")
        browser.screenshot(ROOT/'codex/sonuclar/moduller_mvp_ekranlar/siparis.png')
        assert not browser.errors,browser.errors
        browser.js("location.hash='modules/teklif-yonetimi'")
        browser.wait("!!document.querySelector('[data-m10=yeni-talep]')",40)
        demand=next(d for d in api('M10','/talepler')['talepler'] if d['konu']=='Tarayıcıdan Açılan Makine')
        browser.js("document.querySelector('[data-m10=talep][data-id=\""+str(demand['kimlik'])+"\"]').click()")
        browser.wait("!!document.querySelector('[data-m10=sonuc]')")
        browser.js("document.querySelector('[data-m10=sonuc]').click()")
        browser.wait("!!document.querySelector('dialog [name=sonuc]')")
        browser.js("testSet('dialog [name=sonuc]','KAZANILDI');const select=document.querySelector('dialog [name=kazanan_surum]');testSet('dialog [name=kazanan_surum]',select.options[1].value);document.querySelector('dialog [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelector('#module-workspace').innerText.includes('Kazanıldı')")
        browser.js("location.hash='modules/siparis-butce'")
        browser.wait("!!document.querySelector('[data-m11a=sayfa][data-view=donustur]')",40)
        browser.js("document.querySelector('[data-m11a=sayfa][data-view=donustur]').click()")
        browser.wait("!!document.querySelector('[data-m11a=onizleme]')")
        browser.js("(()=>{const select=document.querySelector('[data-winner] select');testSet('[data-winner] select',[...select.options].find(o=>o.text.includes('Tarayıcıdan Açılan Makine')).value);document.querySelector('[data-m11a=onizleme]').click();})()")
        browser.wait("!!document.querySelector('[data-convert-form]')")
        browser.js("testSet('[data-convert-form] [name=proje_kodu]','TARAYICI-1');testSet('[data-convert-form] [name=sorumlu]','K004');testSet('[data-convert-form] [name=teslim_tarihi]','2026-12-18');document.querySelector('[data-m11a=donustur]').click()")
        browser.wait("!!document.querySelector('[data-m11a=tab][data-tab=ticari]') && document.querySelector('#module-workspace').innerText.includes('Tarayıcıdan Açılan Makine')",40)
        browser.js("location.hash='modules/proje-planlama'")
        browser.wait("!!document.querySelector('[data-proje]')",40)
        browser.js("testSet('[data-proje]','TARAYICI-1')")
        browser.wait("!!document.querySelector('[data-modul-islem=baslat]')")
        browser.js("document.querySelector('[data-modul-islem=baslat]').click()")
        browser.wait("document.querySelectorAll('[data-plan-sira]').length===10 && !document.querySelector('[data-modul-islem=plan-gonder]').disabled",40)
        browser.js("document.querySelectorAll('[data-plan-sira]').forEach(row=>{for(const [name,val] of Object.entries({birim:'MEK_TASARIM',sorumlu:'K004',hedef_saat:'20'})){const el=row.querySelector('[name='+name+']');el.value=val;el.dispatchEvent(new Event('input',{bubbles:true}));}});document.querySelector('[data-modul-islem=plan-gonder]').click()")
        browser.wait("document.querySelector('#module-workspace').innerText.includes('Onaylı Planlar') && !document.querySelector('[data-modul-islem=plan-gonder]').disabled",50)
        browser.js("document.querySelector('[data-modul-islem=tab][data-tab=belgeler]').click()")
        browser.wait("!!document.querySelector('[data-modul-islem=belge]')")
        browser.js("document.querySelector('[data-modul-islem=belge]').click()")
        browser.wait("!!document.querySelector('dialog [name=dosya]')")
        browser.js("const transfer=new DataTransfer();transfer.items.add(new File(['Tarayıcı gerçek dosya'],'tarayici-girdi.txt',{type:'text/plain'}));document.querySelector('dialog [name=dosya]').files=transfer.files;document.querySelector('dialog [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelector('#module-workspace').innerText.includes('tarayici-girdi.txt') && !document.querySelector('[data-modul-islem=belge]').disabled")
        browser.js("document.querySelector('[data-modul-islem=tab][data-tab=gorevler]').click()")
        browser.wait("!!document.querySelector('[data-modul-islem=gorev]')")
        browser.js("document.querySelector('[data-modul-islem=gorev]').click()")
        browser.wait("!!document.querySelector('dialog [name=ad]')")
        browser.js("testSet('dialog [name=ad]','Tarayıcı Gerçek Görevi');testSet('dialog [name=etap]',document.querySelector('dialog [name=etap]').options[1].value);testSet('dialog [name=kisiler]','K041');document.querySelector('dialog [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelector('#module-workspace').innerText.includes('Tarayıcı Gerçek Görevi')")
        browser.js("document.querySelector('[data-modul-islem=tab][data-tab=notlar]').click()")
        browser.wait("!!document.querySelector('[data-modul-islem=not]')")
        browser.js("document.querySelector('[data-modul-islem=not]').click()")
        browser.wait("!!document.querySelector('dialog [name=metin]')")
        browser.js("testSet('dialog [name=kategori]','TASARIM');testSet('dialog [name=alici_birim]','MEK_TASARIM');testSet('dialog [name=metin]','Tarayıcı bilgi notu');document.querySelector('dialog [type=submit]').click()")
        browser.wait("!document.querySelector('dialog') && document.querySelector('#module-workspace').innerText.includes('Tarayıcı bilgi notu')")
        browser.js("document.querySelector('[data-modul-islem=not-ayrinti]').click()")
        browser.wait("!!document.querySelector('dialog') && document.querySelector('dialog').innerText.includes('Gördü: 0/13')")
        browser.js("document.querySelector('dialog').close()")
        browser.screenshot(ROOT/'codex/sonuclar/moduller_mvp_ekranlar/planlama.png')
        assert not browser.errors,browser.errors
        print('Tarayıcı: kazanım → sipariş/proje → plan B0 → gerçek dosya → görev → 13 alıcılı bilgi notu geçti.',flush=True)
    finally:
        browser.close()


if __name__=='__main__':
    main()
