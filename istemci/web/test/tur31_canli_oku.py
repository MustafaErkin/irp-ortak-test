"""222: kurulu webde salt okuma ve form kontrolü; iş olayları engellenir."""
from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).parent))
from tarayici import Browser, page, click, field
from senaryo1_sina import profile

OUT = Path(__file__).resolve().parents[3] / 'codex/sonuclar/tur31_kanit'
b = Browser()
checks = []
try:
    b.call('Page.addScriptToEvaluateOnNewDocument', source="""
window.blockedWrites=[];const savedFetch=window.fetch;
window.fetch=async(...args)=>{const url=String(args[0]);
if(url.includes('/rpc/olay_ekle')){blockedWrites.push('İş olayı gönderimi');throw Error('Salt okuma kontrolü iş yazamaz.')}
return savedFetch(...args)};
""")
    b.navigate('http://localhost:8080/?kip=gosterim')
    b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')", 60)
    b.js("(async()=>{const {BrowserStore}=await import('./client.js');const c=await (await fetch('ayar.json')).json();const s=await BrowserStore.open(c.senaryo?'irp-is-web-v1:'+c.senaryo:'irp-is-web-v1');await s.put('installation','T20-READ-CHECK')})()")
    b.navigate('http://localhost:8080/?kisi=K009#workshop')
    b.wait("document.querySelector('.user-copy strong')?.textContent==='Ekip Lideri'&&!document.querySelector('.loading-line')", 60)
    for person, name in [('K009', 'Ekip Lideri'), ('K004', 'Yönetici'), ('K001', 'CEO')]:
        profile(b, person, name)
        page(b, 'workshop')
        b.js("(()=>{const e=document.querySelector('[data-filter=unit]');e.value='IMALAT';e.dispatchEvent(new Event('change',{bubbles:true}));})()")
        b.wait("!document.querySelector('.loading-line')", 45)
        assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
        assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
        if person == 'K009':
            assert not b.js("!!document.querySelector('[data-drop-person=K009]')")
            click(b, '[data-action=work-unplanned][data-person=K017]')
            b.wait("!!document.querySelector('dialog[open] .work-placement select')", 30)
            assert b.js("(()=>{const s=document.querySelector('.work-placement select');return s.value===s.options[s.options.length-1].value})()")
            assert not b.js("!!document.querySelector('dialog[open] [data-path=sira]')")
            assert b.js("!!document.querySelector('.work-placement>.field+[data-queue-preview]')")
            field(b, 'position', 2)
            b.js("document.querySelector('.work-placement').scrollIntoView({block:'center'})")
            b.screenshot(OUT / '06_kurulu_plansiz_sira.png')
            click(b, 'dialog[open] [data-cancel]')
            checks.append('Kurulu plansız iş: sona varsayılan, açılır sıra ve bitişik önizleme; sayısal alan yok')
            b.js("[...document.querySelectorAll('.person-job')].find(e=>e.querySelector('.job-name strong')?.textContent.startsWith('T3 B'))?.querySelector('[data-action=job-menu]').click()")
            b.wait("!!document.querySelector('.work-detail')", 30)
            click(b, 'dialog[open] [data-code="IS.DEGISTIRDIM"]')
            b.wait("!!document.querySelector('[data-path=\"degisenler.is_tanimi\"]')", 30)
            assert not b.js("!!document.querySelector('[data-path=\"degisenler.tur\"],[data-path=\"degisenler.birim\"],[data-path=\"degisenler.kisi_sayisi\"]')")
            click(b, 'dialog[open] [data-cancel]')
            checks.append('Mevcut B işinin açıklama alanı açık; motorun düzenlemediği alanlar formda yok')
        click(b, '[data-code="IS.TANIMLADIM"]')
        b.wait("!!document.querySelector('dialog[open] [data-path=proje]')", 30)
        assert b.js("document.querySelector('[data-path=proje]').value") == ''
        assert not b.js("!!document.querySelector('dialog[open] [data-path=kisi]')")
        field(b, 'tur', 'ANLIK')
        assert not b.js("!!document.querySelector('dialog[open] [data-path=tahmini_sure_dk]')")
        click(b, 'dialog[open] [data-cancel]')
        page(b, 'team')
        assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
        checks.append(name + ': havuz, ekip ve yeni iş formu doğru')
    profile(b, 'K009', 'Ekip Lideri')
    page(b, 'workshop')
    b.js("(()=>{const e=document.querySelector('[data-filter=unit]');e.value='KURULUM';e.dispatchEvent(new Event('change',{bubbles:true}));})()")
    b.wait("!document.querySelector('.loading-line')", 45)
    assert b.js("!!document.querySelector('[data-drop-person=K031]')")
    checks.append('Lider Saha Çalışanı listesini okuyabiliyor')
    profile(b, 'K041', 'Ofis Çalışanı')
    page(b, 'tasks')
    assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
    checks.append('Mevcut ofis görev ekranı okunuyor')
    profile(b, 'K004', 'Yönetici')
    page(b, 'modules')
    assert not b.js("document.querySelector('#main>.notice.warn')?.textContent")
    checks.append('Mevcut modül sayfası okunuyor')
    assert not b.errors, b.errors
    assert not b.js('window.blockedWrites'), b.js('window.blockedWrites')
    (OUT / 'canli_oku.json').write_text(json.dumps({'tamamlandi': True, 'kontroller': checks}, ensure_ascii=False, indent=2))
    print('\n'.join(checks))
finally:
    b.close()
