"""Temiz altı kişilik firmayla kullanıcının Senaryo 1 akışını gerçek SQL'de yürütür."""
from datetime import date,timedelta
from pathlib import Path
import json
import sys
import subprocess
import threading
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from tarayici import Browser,page,click,field,submit
from yerel_api import Database,ApiServer


def profile(browser,code,name):
    browser.wait("!!document.querySelector('#profile-select') && !document.querySelector('.loading-line')",30)
    browser.js("(()=>{const s=document.querySelector('#profile-select');s.value='"+code+"';s.dispatchEvent(new Event('change',{bubbles:true}));})()")
    browser.wait("document.querySelector('.user-copy strong')?.textContent==='"+name+"' && !document.querySelector('.loading-line')",45)


def record(db,kind,identifier,person='K001'):
    return db.rpc(person,'oku',{'veri':kind,'hedef':identifier,'g':{}})['deger']


def wait_state(db,kind,identifier,status,person='K001'):
    until=time.monotonic()+25
    while time.monotonic()<until:
        result=record(db,kind,identifier,person)
        if result and result.get('durum')==status:return result
        time.sleep(.15)
    raise AssertionError((kind,status,result))


def assign(browser):
    click(browser,'[data-action=assign-review]')
    browser.wait("!!document.querySelector('dialog[open] [data-assign]')",30)
    click(browser,'dialog[open] [data-assign]')
    browser.wait("!document.querySelector('dialog[open]') || !!document.querySelector('dialog[open] .form-error')?.textContent",30)
    assert not browser.js("document.querySelector('dialog[open] .form-error')?.textContent")


def selector(browser,query,timeout=20):
    browser.wait('!!document.querySelector('+json.dumps(query)+')',timeout)


def backdrop(browser):
    browser.call('Input.dispatchMouseEvent',type='mousePressed',x=3,y=3,button='left',clickCount=1)
    browser.call('Input.dispatchMouseEvent',type='mouseReleased',x=3,y=3,button='left',clickCount=1)
    browser.wait("!document.querySelector('dialog[open]')",10)


def approve(browser,db,kind,identifier,person='K004',cancel_first=False,follow=False):
    query='[data-action=quick-approve][data-id="'+identifier+'"]'
    click(browser,query)
    selector(browser,'dialog[open] [data-continue]')
    assert not browser.js("!!document.querySelector('dialog[open] [data-skip]')")
    assert record(db,kind,identifier,person)['durum']=='ONAY_BEKLIYOR'
    if cancel_first:
        backdrop(browser)
        assert record(db,kind,identifier,person)['durum']=='ONAY_BEKLIYOR'
        click(browser,query)
        selector(browser,'dialog[open] [data-continue]')
    if follow:click(browser,'dialog[open] [data-follow]')
    click(browser,'dialog[open] [data-continue]')
    browser.wait("!document.querySelector('dialog[open]') || !!document.querySelector('dialog[open] .form-error')?.textContent",40)
    assert not browser.js("document.querySelector('dialog[open] .form-error')?.textContent")
    wait_state(db,kind,identifier,'BITTI',person)


def usage_checks(browser,db):
    # CEO sees the actual defined monthly amount; a manager gets no salary field.
    ceo=db.rpc('K001','oku',{'veri':'WEB_KISI','hedef':'K017','g':{}})['deger']
    assert float(ceo['brut_maas'])==63000
    assert 'brut_maas' not in db.rpc('K004','oku',{'veri':'WEB_KISI','hedef':'K017','g':{}})['deger']
    page(browser,'people');click(browser,'[data-action=inspect][data-id=K017]')
    selector(browser,'dialog[open] .salary-amount')
    assert browser.js("document.querySelector('.salary-amount').textContent.includes('63.000')")
    click(browser,'dialog[open] [data-close]')
    page(browser,'assign')
    assert not browser.js("!!document.querySelector('#task-editor')")
    click(browser,'[data-action=assign-add]')
    click(browser,'[data-action=assign-review]')
    browser.wait("document.querySelector('#task-editor [data-path=ad]')?.getAttribute('aria-invalid')==='true'",20)
    assert not browser.js("!!document.querySelector('dialog[open]')")
    field(browser,'ad','Elle Hazırlanan Görev');field(browser,'is_tanimi','Görev açıklaması.')
    assert browser.js("document.querySelector('.assignment-item strong').textContent")=='Elle Hazırlanan Görev'
    assert not browser.js("!!document.querySelector('[data-action=template-save],[data-template-select],.nav-link[data-page=templates]')")
    click(browser,'[data-action=assign-add]');field(browser,'ad','İkinci Taslak')
    assert not browser.js("!!document.querySelector('[data-multi-path=on_kosul][value=\"@row:1\"]')")
    click(browser,'[data-multi-path=on_kosul][value="@row:0"]')
    click(browser,'[data-action=assign-select][data-index="0"]');click(browser,'[data-action=assign-remove]')
    assert browser.js("document.querySelector('[data-path=ad]').value")=='İkinci Taslak'
    assert not browser.js("!!document.querySelector('[data-multi-path=on_kosul]:checked')")
    click(browser,'[data-action=assign-remove]');assert not browser.js("!!document.querySelector('#task-editor')")
    profile(browser,'K004','Yönetici');page(browser,'people');click(browser,'[data-action=inspect][data-id=K017]')
    browser.wait("!!document.querySelector('dialog[open]')",20)
    assert not browser.js("!!document.querySelector('.salary-amount')")
    click(browser,'dialog[open] [data-close]');profile(browser,'K001','CEO')
    page(browser,'overview')
    assert get_count(db,'WEB_GOREVLER')==0 and get_count(db,'WEB_ISLER')==0
    print('Kullanım: maaş yetkisi, alan hatası, şablonsuz elle görev, çoklu taslak/silme/ön koşul geçti.',flush=True)


def notifications_check(browser,db):
    page(browser,'notifications')
    rows=db.rpc('K004','oku',{'veri':'BILDIRIMLER','hedef':'K004','g':{}})['deger']
    row=next(r for r in rows if not r.get('gorulme_ani'))
    identifier=row.get('kimlik') or '/'.join([row['doguran_olay'],row['kural'],row['alici']])
    query='[data-action=seen][data-id='+json.dumps(identifier)+']'
    selector(browser,query)
    content=browser.js("[...document.querySelectorAll('.notification-copy p')].map(p=>p.textContent)")
    assert content and all(len(p)>20 for p in content),repr(content)
    assert not browser.js(r"/K[0-9]{3}|[A-Z_]+\.[A-Z_]+/.test(document.querySelector('#page-body').innerText)")
    click(browser,query)
    browser.wait('!document.querySelector('+json.dumps(query)+')',30)
    updated=db.rpc('K004','oku',{'veri':'BILDIRIMLER','hedef':'K004','g':{}})['deger']
    assert next(r for r in updated if (r.get('kimlik') or '/'.join([r['doguran_olay'],r['kural'],r['alici']]))==identifier)['gorulme_ani']
    assert not browser.js("document.querySelector('.toast.bad')?.textContent")
    print('Bildirim: içerik okunuyor, gerçek kimlikle Görüldü kabul edildi ve okunmamış listesinden çıktı.',flush=True)


def run():
    db=server=browser=observer=None
    try:
        db=Database(empty=True)
        server=ApiServer(db,HERE.parent/'build')
        threading.Thread(target=server.serve_forever,daemon=True).start()
        origin='http://127.0.0.1:'+str(server.server_port)
        browser=Browser(1512,1080)
        browser.call('Emulation.setEmulatedMedia',features=[{'name':'prefers-color-scheme','value':'dark'}])
        browser.navigate(origin+'/?kisi=K001')
        browser.wait("document.querySelector('#main h1') && !document.querySelector('.loading-line')",45)
        assert browser.js("document.querySelector('.user-copy strong').textContent")=='CEO'
        assert browser.js("[...document.querySelector('#profile-select').options].map(x=>x.textContent)")==['CEO','Yönetici','Ekip Lideri','Ofis Çalışanı']
        assert db.rpc('K001','oku',{'veri':'PROJELER','g':{}})['deger']==[]
        assert get_count(db,'WEB_GOREVLER')==0 and get_count(db,'WEB_ISLER')==0
        observer=Browser(1512,950)
        observer.navigate(origin+'/olaylar.html')
        observer.wait("document.querySelector('#connection-label')?.textContent==='Canlı Bağlantı'",30)
        assert observer.js("document.querySelector('#event-count').textContent")=='0'
        capture(browser,'01_bos_ceo')
        usage_checks(browser,db)
        # CEO opens a project and its three stages using normal business forms.
        click(browser,'[data-code="PROJE.ACTIM"]')
        browser.wait("!!document.querySelector('dialog[open] [data-path=ad]')",20)
        field(browser,'ad','Montaj İstasyonu')
        field(browser,'kod','2611001')
        field(browser,'musteri','Örnek Müşteri')
        field(browser,'teslim_tarihi',(date.today()+timedelta(days=14)).isoformat())
        submit(browser)
        page(browser,'projects')
        click(browser,'[data-menu-toggle]')
        assert browser.js("document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded')")=='true'
        browser.js("document.body.dispatchEvent(new Event('pointerdown',{bubbles:true}))")
        assert not browser.js("!!document.querySelector('.overflow-menu.is-open')")
        stages=[]
        for name,unit in [('Ofis Çalışmaları','MEK_TASARIM'),('Atölye İmalatı','IMALAT'),('Saha Kurulumu','KURULUM')]:
            click(browser,'#page-body [data-code="ETAP.TANIMLADIM"]')
            browser.wait("!!document.querySelector('dialog[open] [data-path=ad]')",20)
            field(browser,'ad',name);field(browser,'birim',unit);field(browser,'sorumlu','K004')
            submit(browser)
            stages=db.rpc('K001','oku',{'veri':'ETAPLAR','hedef':'2611001','g':{}})['deger']
        assert len(stages)==3
        office=next(s for s in stages if s['birim']=='MEK_TASARIM')
        capture(browser,'02_proje_etaplar')
        click(browser,'[data-action=plan-task]')
        browser.wait("!!document.querySelector('#task-editor [data-path=ad]') && !document.querySelector('.loading-line')",20)
        assert browser.js("document.querySelector('#task-editor [data-path=ad]').value")=='Etapları Planla'
        field(browser,'teslim_tarihi',(date.today()+timedelta(days=7)).isoformat())
        assert browser.js("document.querySelector('#task-editor [data-path=kisi]').value")=='K004'
        assign(browser)
        print('Senaryo 1: CEO boş firmada proje, üç etap ve yönetici görevi oluşturdu.',flush=True)
        # The single manager plans stages with ordinary permissions.
        profile(browser,'K004','Yönetici');page(browser,'tasks')
        task=find(db,'WEB_GOREVLER','ad','Etapları Planla')
        click(browser,'tr[data-id="'+task['kimlik']+'"]')
        click(browser,'.task-detail [data-code="GOREV.KABUL_ETTIM"]')
        wait_state(db,'GOREV',task['kimlik'],'ACIK','K004')
        browser.wait("document.querySelector('.task-detail h2')?.textContent==='Görevinizi Seçin'",25)
        assert browser.js("document.querySelector('.tab.active').dataset.tab")=="waiting"
        click(browser,'[data-action=tab][data-tab=open]')
        click(browser,'tr[data-id="'+task['kimlik']+'"]')
        browser.wait("!!document.querySelector('.task-detail [data-code=\"GOREV.TAMAMLADIM\"]')",25)
        assert not browser.js("!!document.querySelector('dialog[open]')")
        page(browser,'projects')
        click(browser,'[data-code="ETAP.DEGISTIRDIM"][data-id="'+office['kimlik']+'"]')
        selector(browser,'dialog[open] [data-path="degisenler.hedef_saat"]')
        field(browser,'degisenler.hedef_saat',80);submit(browser)
        assert record(db,'ETAP',office['kimlik'],'K004')['hedef_saat']==80
        page(browser,'tasks')
        click(browser,'tr[data-id="'+task['kimlik']+'"]')
        click(browser,'.task-detail [data-code="GOREV.TAMAMLADIM"]');submit(browser)
        wait_state(db,'GOREV',task['kimlik'],'ONAY_BEKLIYOR','K004')
        # Office work: optional files remain genuinely optional, with a real delivery.
        page(browser,'assign')
        click(browser,'[data-action=assign-add]')
        field(browser,'ad','Teknik Resmi Hazırlayın');field(browser,'is_tanimi','Montaj istasyonunun teknik resmini hazırlayın.')
        field(browser,'kisi','K041');field(browser,'etap',office['kimlik'])
        field(browser,'teslim_tarihi',(date.today()+timedelta(days=5)).isoformat())
        click(browser,'[data-action=assign-add]');field(browser,'ad','Geçici Ön Koşul Denemesi')
        assert browser.js("document.querySelector('[data-choice-group=on_kosul] input').value")=='@row:0'
        assert browser.js("!!document.querySelector('[data-choice-group=on_kosul] .choice-divider')")
        assert browser.js("document.querySelector('[data-choice-group=on_kosul] .choice-note').textContent.startsWith('*')")
        click(browser,'[data-action=assign-remove]')
        # The review displays actual job and dependency names, without creating a dependency.
        browser.js("document.querySelectorAll('details.advanced-fields').forEach(d=>d.open=true)")
        click(browser,'[data-multi-path=on_kosul][value="'+task['kimlik']+'"]')
        click(browser,'[data-action=assign-review]');selector(browser,'dialog[open] [data-assign]')
        assert browser.js("document.querySelector('dialog[open]').textContent.includes('Ön Koşullar')")
        assert browser.js("document.querySelector('dialog[open]').textContent.includes('Teknik Resmi Hazırlayın')")
        assert browser.js("document.querySelector('dialog[open]').textContent.includes('Etapları Planla')")
        click(browser,'dialog[open] [data-back]')
        click(browser,'[data-multi-path=on_kosul][value="'+task['kimlik']+'"]')
        capture(browser,'03_gorev_atama');assign(browser)
        assert not browser.js("!!document.querySelector('.assignment-item')")
        assert not browser.js("!!document.querySelector('#task-editor')")
        office_task=find(db,'WEB_GOREVLER','ad','Teknik Resmi Hazırlayın')
        assert office_task['dosya_gerekli'] is False
        profile(browser,'K041','Ofis Çalışanı');page(browser,'tasks')
        click(browser,'tr[data-id="'+office_task['kimlik']+'"]')
        capture(browser,'04_ofis_gorev')
        click(browser,'.task-detail [data-code="GOREV.KABUL_ETTIM"]')
        wait_state(db,'GOREV',office_task['kimlik'],'ACIK','K041')
        browser.wait("document.querySelector('.task-detail h2')?.textContent==='Görevinizi Seçin'",25)
        assert browser.js("document.querySelector('.tab.active').dataset.tab")=="waiting"
        click(browser,'[data-action=tab][data-tab=open]')
        click(browser,'tr[data-id="'+office_task['kimlik']+'"]')
        browser.wait("!!document.querySelector('.task-detail .btn.deliver')",25)
        click(browser,'.task-detail [data-code="GOREV.TAMAMLADIM"]')
        browser.wait("!!document.querySelector('#operation-files')",20)
        assert browser.js("document.querySelector('#operation-files').files.length")==0
        submit(browser)
        wait_state(db,'GOREV',office_task['kimlik'],'ONAY_BEKLIYOR','K041')
        # @ produces an actual department request, not a decorative text label.
        click(browser,'.task-detail [data-code="NOT.YAZDIM"]')
        browser.wait("!!document.querySelector('dialog[open] [data-path=metin]')",20)
        field(browser,'metin','İmalat hazırlığını değerlendirin @')
        click(browser,'[data-mention=IMALAT]')
        submit(browser)
        observer.wait("Number(document.querySelector('#event-count').textContent)>=10",30)
        profile(browser,'K004','Yönetici')
        assert browser.js("document.querySelector('[data-nav-title=approvals]').textContent.includes('(1)')")
        page(browser,'approvals')
        click(browser,'[data-action=inspect][data-id="'+office_task['kimlik']+'"]')
        selector(browser,'.detail-primary-actions')
        browser.js("document.querySelector('dialog[open] .dialog-body').scrollTop=10000")
        assert browser.js("(()=>{const e=document.querySelector('dialog[open] [data-close]'),r=e.getBoundingClientRect();return e===document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)})()")
        click(browser,'dialog[open] [data-close]')
        approve(browser,db,'GOREV',office_task['kimlik'],cancel_first=True)
        browser.wait("!document.querySelector('[data-nav-title=approvals]').textContent.includes('(')",15)
        notifications_check(browser,db)
        page(browser,'dayclose')
        assert browser.js("document.querySelector('[data-nav-title=dayclose]').textContent==='Gün Sonu'")
        assert browser.js("document.querySelector('.daily-task-table').textContent.includes('Teknik Resmi Hazırlayın')")
        assert not browser.js("/K[0-9]{3}-[0-9]{10}-[A-Z]/.test(document.querySelector('.daily-summary').textContent)")
        capture(browser,'07_yonetici_gun_ozeti')
        browser.js("(()=>{const s=document.querySelector('[data-filter=person]');s.value='K041';s.dispatchEvent(new Event('change',{bubbles:true}));})()")
        browser.wait("document.querySelector('[data-summary-person=K041]')&&!document.querySelector('.loading-line')",30)
        assert browser.js("document.querySelector('.daily-task-table').textContent.includes('Teknik Resmi Hazırlayın')")
        capture(browser,'08_ofis_gun_ozeti')
        print('Senaryo 1: yönetici planladı, ofis çalışanı kabul/dosyasız teslim/@ isteği yaptı; yönetici onayladı.',flush=True)
        # Create one workshop and one field job, then drag to the right employees.
        for unit,title in [('IMALAT','Gövde Montajı'),('KURULUM','Sahada Kurulum')]:
            page(browser,'assign')
            click(browser,'[data-action=assign-add]')
            field(browser,'olcum','SAAT');field(browser,'ad',title);field(browser,'birim',unit)
            field(browser,'etap',next(s for s in stages if s['birim']==unit)['kimlik'])
            assert browser.js("document.querySelector('#task-editor [data-path=zaman_degeri]').closest('label').textContent.includes('Tahmini Süre')")
            assign(browser)
        profile(browser,'K009','Ekip Lideri');page(browser,'workshop')
        for unit,title,person in [('IMALAT','Gövde Montajı','K017'),('KURULUM','Sahada Kurulum','K031')]:
            browser.js("(()=>{const s=document.querySelector('[data-filter=unit]');s.value='"+unit+"';s.dispatchEvent(new Event('change',{bubbles:true}));})()")
            browser.wait("!document.querySelector('.loading-line')",20)
            job=find(db,'WEB_ISLER','islem',title)
            query='[data-drop-person="'+person+'"]'
            selector(browser,query)
            browser.js("(()=>{const dt=new DataTransfer();dt.setData('application/irp-job',JSON.stringify({id:"+json.dumps(job['kimlik'])+"}));document.querySelector("+json.dumps(query)+").dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}));})()")
            assert set(browser.js("[...document.querySelector('dialog[open] [data-path=kisi]').options].map(e=>e.value).filter(Boolean)"))<=set(['K009','K017','K031'])
            submit(browser)
            assert record(db,'IS',job['kimlik'],'K009')['kisi']==person
        capture(browser,'05_ekip_is_atama')
        dart=Path.home()/'development/flutter/bin/cache/dart-sdk/bin/dart'
        packages=HERE.parents[1]/'uygulama/.dart_tool/package_config.json'
        subprocess.run([str(dart),'--packages='+str(packages),str(HERE/'telefon_motor.dart'),origin],check=True)
        for title in ['Gövde Montajı','Sahada Kurulum']:
            job=find(db,'WEB_ISLER','islem',title)
            wait_state(db,'IS',job['kimlik'],'ONAY_BEKLIYOR')
        observer.wait("document.querySelector('#event-rows').textContent.includes('Telefon')",25)
        print('Senaryo 1: telefonun Dart çekirdeğiyle atölye ve saha işi dosyasız teslim edildi; gerçek motor onay bekliyor.',flush=True)
        profile(browser,'K004','Yönetici');page(browser,'approvals')
        for title in ['Gövde Montajı','Sahada Kurulum']:
            job=find(db,'WEB_ISLER','islem',title)
            approve(browser,db,'IS',job['kimlik'])
        profile(browser,'K001','CEO');page(browser,'approvals')
        count_before=get_count(db,'WEB_GOREVLER')
        approve(browser,db,'GOREV',task['kimlik'],'K001',follow=True)
        page(browser,'assign')
        assert browser.js("document.querySelector('#task-editor [data-path=ad]').value")=='Devam: Etapları Planla'
        assert browser.js("document.querySelectorAll('.assignment-item').length")==1
        assert get_count(db,'WEB_GOREVLER')==count_before,'Devam işi yalnız taslak doldurmalı'
        print('Senaryo 1: telefon teslimleri yönetici, planlama görevi CEO tarafından onaylandı.',flush=True)
        page(browser,'modules')
        browser.wait("document.body.innerText.includes('Henüz Modül Devrede Değil')",20)
        observer.wait("document.querySelector('#event-rows').textContent.includes('İş Ata')",25)
        capture(observer,'06_bagimsiz_olaylar')
        assert not browser.errors,browser.errors
        assert not observer.errors,observer.errors
        print('Senaryo 1: lider sürükle/bırakla atölye ve sahaya atadı; bağımsız izleyicide gerçek olaylar görüldü.',flush=True)
    finally:
        if observer:observer.close()
        if browser:browser.close()
        if server:server.shutdown();server.server_close()
        if db:db.close()


def get_count(db,view):return len(db.rpc('K001','oku',{'veri':view,'g':{}})['deger'])
def find(db,view,key,value):
    until=time.monotonic()+20
    while time.monotonic()<until:
        rows=db.rpc('K001','oku',{'veri':view,'g':{}})['deger']
        found=next((r for r in rows if r.get(key)==value),None)
        if found:return found
        time.sleep(.2)
    raise AssertionError((view,key,value))
def capture(browser,name):
    assert browser.js('document.documentElement.scrollWidth<=innerWidth+1'),name
    assert browser.js("getComputedStyle(document.body).backgroundColor")=='rgb(255, 255, 255)'
    browser.screenshot(HERE.parents[2]/'codex/sonuclar/web_son_duzeltmeler_ekranlar'/(name+'.png'))


if __name__=='__main__':run()
