"""Ortak modül yolunu ayrı gerçek PostgreSQL firmasında sınar; canlıya bağlanmaz."""
import functools
from datetime import date,timedelta
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime/python'),str(ROOT/'istemci/web/test')]
if __package__ in (None,''):__package__='modul_platformu'

import psycopg
from psycopg import sql
from yerel_api import Database,ApiServer
from .gecit import Platform,http
from .isletim import Yetkili
from .kayit import oku
from .kur import kur,kimlik,kapat
from istemci.web.sunucu import YerelSunucu,Isleyici

def main(browser_test=False,core_test=False):
    db=None;core=None;web=None;platform=None;role=None;roles=[];browser=None
    directory=tempfile.TemporaryDirectory(prefix='irp-modul-web-')
    try:
        db=Database(empty=True)
        shutil.copytree(ROOT/'istemci/web/build',Path(directory.name),dirs_exist_ok=True)
        core=ApiServer(db,ROOT/'istemci/web/build',jwt=True)
        threading.Thread(target=core.serve_forever,daemon=True).start()
        core_url=f'http://127.0.0.1:{core.server_port}'
        env={'IRP_SB_TEST_DB':db.dsn,'IRP_SB_TEST_URL':core_url,'IRP_SB_TEST_ANON':'sb_publishable_yerel_test'}
        status,_,body=http(core_url+'/auth/v1/token?grant_type=password',value={'email':'k001@calisan.irp','password':'123456'})
        assert status==200
        token=json.loads(body)['access_token']
        actor=Yetkili(env,token,'K001')
        row=oku()['M11B'];role,credentials,_=kimlik(db.dsn,'M11B')
        # Sağlayıcılar künyeleriyle kayıtlıdır; bu eski sınama M11A'da siparişi olmayan
        # bir çekirdek projesinin bağımsız planlama akışını sürdürür.
        for dependency in oku().values():
            roles.append(kimlik(db.dsn,dependency['kod'])[0])
            result=kur(db.dsn,dependency,actor.event,actor.modul)
            if dependency['kod']=='M11B':installed=result
        assert installed['goc']==len(list((row['klasor']/'veritabani').glob('*.sql')))
        assert kur(db.dsn,row,actor.event,actor.modul)['zaten_kurulu']
        # Bu örnek proje yalnız ayrı test firmasındadır.
        assert actor.event('PROJE.ACTIM',{'kod':'MODUL-SINAMA','ad':'Planlama Bağlantısı Sınaması','sorumlu':'K004',
            'baslangic_tarihi':db.rpc('K001','simdi',{}).isoformat()[:10],'teslim_tarihi':'2026-12-18'})['sonuc']=='BASARILI'
        projects=db.rpc('K001','oku',{'veri':'PROJELER','hedef':None,'g':{}})['deger']
        project=next(p for p in projects if p['ad']=='Planlama Bağlantısı Sınaması')
        today=db.rpc('K001','simdi',{}).date().isoformat()
        assert actor.event('ETAP.TANIMLADIM',{'proje':project['kimlik'],'ad':'Teknik Hazırlık',
            'birim':'MEK_TASARIM','baslangic':today,'bitis':'2026-12-01','hedef_saat':20,'sorumlu':'K004'})['sonuc']=='BASARILI'
        stage=db.rpc('K001','oku',{'veri':'ETAPLAR','g':{'proje':project['kimlik']}})['deger'][0]
        print('Modül: kurulum, tekrar kurulum ve hazırlık olayları geçti.',flush=True)
        with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None) as c:
            assert c.execute('SELECT session_user').fetchone()[0]==role
            assert c.execute('SELECT count(*) FROM mod_m11b.etap_sablonu').fetchone()[0]==10
            assert c.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='mod_m11b'").fetchone()[0]==role+'_sahibi'
            try:c.execute('CREATE TABLE mod_m11b.izinsiz_tablo(k int)');raise AssertionError('Giriş rolü DDL yapabildi')
            except psycopg.errors.InsufficientPrivilege:pass
            value=c.execute('SELECT public.servis_oku(%s,%s,%s::jsonb)',('PROJE',project['kimlik'],'{}')).fetchone()[0]['deger']
            assert value['ad']==project['ad'] and 'musteri' not in value
            for query,args in [('SELECT * FROM public.olaylar',()),
                ('SELECT public.oku(%s,%s,%s::jsonb)',('MAAS','K001','{}')),
                ('SELECT public.servis_oku(%s,%s,%s::jsonb)',('MAAS','K001','{}')),
                ('SELECT public.servis_oku(%s,%s,%s::jsonb)',('PROJE',project['kimlik'],'{"kim":"K001"}'))]:
                try:c.execute(query,args);raise AssertionError('Dar rol sınırı aşabildi')
                except (psycopg.errors.InsufficientPrivilege,psycopg.errors.RaiseException):pass
        web=YerelSunucu(('127.0.0.1',0),functools.partial(Isleyici,directory=directory.name))
        platform=Platform(env=env);web.platform=platform
        threading.Thread(target=web.serve_forever,daemon=True).start()
        platform.start(web.server_port)
        base=f'http://127.0.0.1:{web.server_port}'
        headers={'Authorization':'Bearer '+token}
        def api(suffix='',method='GET',value=None,auth=headers,expected=200):
            status,_,body=http(base+'/irp/moduller/M11B/api/projeler/'+project['kimlik']+suffix,
                method=method,value=value,headers={'Content-Type':'application/json',**auth})
            assert status==expected,(suffix,status,body.decode()[:400])
            return json.loads(body)
        status,_,body=http(base+'/irp/moduller',method='GET',headers=headers)
        assert status==200 and any(m['kod']=='M11B' for m in json.loads(body)['moduller'])
        status,_,_=http(base+'/irp/moduller',method='GET');assert status==401
        status,_,body=http(base+'/irp/moduller/M11B/api/projeler',method='GET',headers=headers)
        assert status==200 and json.loads(body)['projeler'][0]['devir_basladi'] is False
        api();api('/devir','POST',{})
        plan=api('/plan');rows=[s for s in plan['satirlar'] if s['etap']]
        assert len(rows)==1
        api('/plan/taslak','PUT',{'satirlar':rows})
        approved=api('/plan/gonder','POST',{})
        assert approved['b0_var'] and approved['cekirdek_surumleri'][0]['no']=='B0',approved
        assert approved['bildirim'] and 'K004' in approved['bildirim']['alicilar'],approved.get('bildirim')
        # Bu adım dosya aktarımının kabulü değildir; gelen modülün metadata şartını sınar.
        proof=api('/dosyalar','POST',{'tur':'PLAN_KANITI','ad':'Yerel sınama tutanağı',
            'konum':'test://yalniz-metadata/plan-tutanagi'})['dosya']['kimlik']
        rows=[s for s in api('/plan')['satirlar'] if s['etap']]
        rows[0]['bitis']='2026-12-02'
        api('/plan/taslak','PUT',{'satirlar':rows,'neden':'KARSILIKLI_ANLASMA','gerekce':'Yerel plan revizyonu','kanitlar':[proof]})
        revision=api('/plan/gonder','POST',{})
        assert [r['no'] for r in revision['cekirdek_surumleri']]==['B0','B1']
        stage=db.rpc('K001','oku',{'veri':'ETAP','hedef':stage['kimlik'],'g':{}})['deger']
        assert actor.event('ETAP.DEGISTIRDIM',{'degisenler':{'bitis':'2026-12-03'}},
            [{'tur':'ETAP','kimlik':stage['kimlik'],'surum':stage['surum']}])['sonuc']=='BASARILI'
        assert actor.event('PLAN.ONAYLADIM',{'proje':project['kimlik'],'gerekce':'Modül dışındaki çekirdek onayı'})['sonuc']=='BASARILI'
        history=api('/plan')['cekirdek_surumleri']
        assert [r['no'] for r in history]==['B0','B1','B2'] and history[-1]['gerekce']=='Modül dışındaki çekirdek onayı'
        assert history[0]['etaplar'][stage['kimlik']]['bitis']=='2026-12-01'
        print('Modül: gerçek B0, B1 ve modül dışından B2 onayı / ilk planın korunması geçti.',flush=True)
        assignment=api('/gorevler','POST',{'etap':stage['kimlik'],'kisiler':['K041'],'ad':'Bağlantı Sınaması Görevi',
            'teslim_tarihi':'2026-12-01','zaman_degeri':2,'onay_gerekli':True,'onaylayan':'K004','dosya_gerekli':False})
        task=assignment['sonuclar'][0]['gorev']
        def user(person):
            status,_,data=http(core_url+'/auth/v1/token?grant_type=password',value={'email':person.lower()+'@calisan.irp','password':'123456'})
            assert status==200
            a=Yetkili.__new__(Yetkili);a.env=env;a.token=json.loads(data)['access_token'];a.person=person;a.last=None
            a.device='WEB-MODUL-SINAMA-'+person;a.letter=a.rpc('cihaz_kaydol',{'cihaz':a.device})
            return a
        employee=user('K041');manager=user('K004')
        def task_event(who,action):
            r=who.rpc('oku',{'veri':'GOREV','hedef':task,'g':{}})['deger']
            result=who.event(action,{},[{'tur':'GOREV','kimlik':task,'surum':r['surum']}])
            assert result['sonuc']=='BASARILI',(action,result)
        task_event(employee,'GOREV.KABUL_ETTIM');task_event(employee,'GOREV.TAMAMLADIM')
        task_event(manager,'GOREV.ONAYLADIM')
        assert manager.rpc('oku',{'veri':'GOREV','hedef':task,'g':{}})['deger']['durum']=='BITTI'
        chart=api('/gantt');assert chart['etaplar'][0]['gorevler'][0]['ad']=='Bağlantı Sınaması Görevi'
        assert chart['etaplar'][0]['gerceklesen_bitis']
        visible_task=task
        hidden=api('/gorevler','POST',{'etap':stage['kimlik'],'kisiler':['K004'],'ad':'Yöneticiye Özel Görev',
            'teslim_tarihi':'2026-12-01','zaman_degeri':1,'onay_gerekli':False,'dosya_gerekli':False})
        task=hidden['sonuclar'][0]['gorev']
        task_event(manager,'GOREV.KABUL_ETTIM');task_event(manager,'GOREV.TAMAMLADIM')
        period={'bas':today,'bit':'2026-12-18','adlar':True}
        all_rows=actor.rpc('oku',{'veri':'GANTT','hedef':project['kimlik'],'g':period})['deger']
        restricted=employee.rpc('oku',{'veri':'GANTT','hedef':project['kimlik'],'g':period})['deger']
        assert next(r for r in all_rows if r['tur']=='ETAP')==next(r for r in restricted if r['tur']=='ETAP')
        assert task not in [r['kimlik'] for r in restricted] and visible_task in [r['kimlik'] for r in restricted]
        print('Modül: iki kullanıcıda aynı etap gerçekleşeni / gizli görev ayrıntısının korunması geçti.',flush=True)
        api('',auth={'Authorization':'Bearer '+employee.token},expected=403)
        # Proje sorumlusu etap açma yetkisi kazanmadan mevcut etabı planlar.
        manager_plan=api('/plan',auth={'Authorization':'Bearer '+manager.token})
        assert manager_plan['b0_var']
        # Genel sağlayıcı taşıması: bu, M11A'nın tüketim kodunun kabulü değildir.
        consumer={'kunye':{'bagimliliklar':[{'modul':'M11B','okumalar':['M11B.TASARIM_KAPISI']}]}}
        result=platform.provider(consumer,'M11B.TASARIM_KAPISI',{'hedef':project['kimlik']},'Bearer '+manager.token)
        assert result['deger'] and result['hesap']=='GUNCEL'
        print('Modül: görev atama → çalışanın kabul/teslimi → yöneticinin onayı → Gantt geçti.',flush=True)
        assert http(base+'/moduller/M11B/ekran.js',method='GET')[0]==200
        if browser_test:
            from tarayici import Browser
            config={'bulut':'SUPABASE','supabase_url':core_url,'supabase_anon':env['IRP_SB_TEST_ANON'],
                'gosteri_kisileri':[{'kod':k,'etiket':v,'sifre':'123456'} for k,v in core.roles.items() if k in ('K001','K004','K009','K041')]}
            (Path(directory.name)/'ayar.json').write_text(json.dumps(config))
            browser=Browser();browser.navigate(base+'/?kisi=K001#modules/proje-planlama')
            browser.wait("!!document.querySelector('[data-proje]')",40)
            assert browser.js("document.body.innerText.includes('Proje Planlama')")
            assert not browser.js("!!document.querySelector('iframe')")
            browser.js("document.querySelector('#profile-select').value='K004';document.querySelector('#profile-select').dispatchEvent(new Event('change',{bubbles:true}))")
            browser.wait("document.querySelector('.user-copy strong')?.textContent==='Yönetici' && !!document.querySelector('[data-proje]')",40)
            browser.js("document.querySelector('[data-modul-islem=tab][data-tab=plan]').click()")
            browser.wait("document.body.innerText.includes('Onaylı Planlar')")
            assert browser.js("document.querySelector('#module-workspace').innerText.includes('B2')")
            browser.js("""(()=>{
              const set=(q,value,type='input')=>{const el=document.querySelector(q);if(!el)throw Error(q);el.value=value;el.dispatchEvent(new Event(type,{bubbles:true}));};
              set('[data-plan-sira] [name=bitis]','2026-12-04');
              set('[name=neden]','KARSILIKLI_ANLASMA','change');set('[data-gerekce]','Yönetici web ekranından onayladı');
            })()""")
            browser.js("document.querySelector('[name=kanit]').value="+json.dumps(str(proof))+";document.querySelector('[name=kanit]').dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-modul-islem=plan-gonder]').click()")
            browser.wait("document.querySelector('#module-workspace')?.innerText.includes('B3')",40)
            assert api('/plan')['cekirdek_surumleri'][-1]['gerekce']=='Karşılıklı anlaşma: Yönetici web ekranından onayladı'
            assert browser.js("getComputedStyle(document.body).backgroundColor")=='rgb(255, 255, 255)'
            assert browser.js(r"!document.querySelector('#module-workspace').innerText.match(/\bK\d{3}(?:-\d{10}-[A-Z])?\b/)")
            browser.screenshot(ROOT/'codex/sonuclar/modul_ortak_baglanti_ekranlar/plan.png')
            assert not browser.errors,browser.errors
            print('Modül: tek giriş, HTML ekranı, beyaz ERP ve çekirdek sürüm geçmişi tarayıcıda geçti.',flush=True)
        before=db.rpc('K001','oku',{'veri':'PROJELER','hedef':None,'g':{}})['deger']
        with psycopg.connect(db.dsn,autocommit=True) as c:
            assert c.execute("SELECT count(*) FROM public.modul_bildirimleri WHERE hal->>'kaynak'='M11B' AND (hal->>'gecerli')::boolean").fetchone()[0]>0
        kapat(db.dsn,row,actor.event)
        status,_,body=http(base+'/irp/moduller',method='GET',headers=headers)
        assert status==200 and all(m['kod']!='M11B' for m in json.loads(body)['moduller'])
        if browser:
            browser.wait("!document.querySelector('#module-workspace') && document.body.innerText.includes('Henüz Modül Devrede Değil')",40)
        assert http(base+'/irp/moduller/M11B/api/ben',method='GET',headers=headers)[0]==403
        assert db.rpc('K001','oku',{'veri':'PROJELER','hedef':None,'g':{}})['deger']==before
        with psycopg.connect(db.dsn,autocommit=True) as c:
            assert c.execute("SELECT count(*) FROM public.modul_bildirimleri WHERE hal->>'kaynak'='M11B' AND (hal->>'gecerli')::boolean").fetchone()[0]==0
        # Kapanan modülün kendi servis rolü de yeni okumayı reddeder.
        try:
            with psycopg.connect(**credentials,autocommit=True,prepare_threshold=None):
                raise AssertionError('Pasif giriş rolü bağlanabildi')
        except psycopg.OperationalError:pass
        print('Modül: gerçek SQL kurulum/tekrar, dar rol, ortak giriş/API, gerçek M11B devri/plan okuması ve veriyi koruyan kapatma geçti.',flush=True)
        counts={}
        if core_test:
            if browser:browser.close();browser=None
            platform.close();platform=None
            web.shutdown();web.server_close();web=None
            core.shutdown();core.server_close();core=None
            from test.oynatici.oynat import bir_senaryo
            from test.oynatici.secim import sec
            driver=db.driver()
            try:
                results=[bir_senaryo(s,driver,'tam') for s in sec(katman='K0,A')]
                counts=dict(Counter(r['sonuc'] for r in results))
                assert not [r for r in results if r['sonuc'] not in ('GECTI','ATLANDI')],[(r['ad'],r['sonuc']) for r in results]
                print('Çekirdek K0/A:',counts,flush=True)
            finally:driver.kapat()
        proof_path=ROOT/'codex/sonuclar/modul_ortak_baglanti.json'
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'urun/veritabani').glob('[0-9][0-9][0-9]_*.sql'))}
        if not core_test and proof_path.exists():
            previous=json.loads(proof_path.read_text())
            if previous.get('gocler')==hashes:counts=previous.get('cekirdek_K0_A',{})
        proof_path.write_text(json.dumps({'durum':'GECTI','tarayici':browser_test,'cekirdek_K0_A':counts,
            'kontroller':['kurulum_tekrar','dar_sql_rolu','ortak_oturum_api','B0_B1_dis_B2','gorev_kabul_teslim_onay',
                'ayni_etap_ozeti_gizli_ayrinti','saglayici_tasimasi','pasiflestirme_veriyi_korur']+(['yonetici_web_B3'] if browser_test else []),
            'gocler':hashes,'cekirdek_K0_A_bu_kosuda':core_test,
            'sinirlar':['Yerel Auth taşıması imza doğrulama testi değildir.','Plan kanıtı metadata sınamasıdır; fiziksel dosya yükleme kabulü değildir.',
                'Genel sağlayıcı taşıması M11A tüketim akışının kabulü değildir.']},ensure_ascii=False,indent=1)+'\n')
    finally:
        with ExitStack() as cleanup:
            cleanup.callback(directory.cleanup)
            def drop_role():
                if roles:
                    with psycopg.connect('postgresql://postgres@localhost:5433/postgres',autocommit=True) as c:
                        for installed_role in roles:
                            c.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(installed_role)))
                            c.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(installed_role+'_sahibi')))
            cleanup.callback(drop_role)
            if db:cleanup.callback(db.close)
            if core:cleanup.callback(core.server_close);cleanup.callback(core.shutdown)
            if web:cleanup.callback(web.server_close);cleanup.callback(web.shutdown)
            if platform:cleanup.callback(platform.close)
            if browser:cleanup.callback(browser.close)

if __name__=='__main__':
    main('--tarayici' in sys.argv,'--cekirdek' in sys.argv)
