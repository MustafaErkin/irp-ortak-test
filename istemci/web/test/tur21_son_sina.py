"""Tur2.1 son kullanıcı notları: ayrı firmada gerçek SQL ve normal web akışı."""
from datetime import date, timedelta
from pathlib import Path
import json, sys, threading, time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tarayici import Browser, page, click, field, submit
from yerel_api import Database, ApiServer
from senaryo1_sina import profile, wait_state

OUT = HERE.parents[2] / 'codex/sonuclar/tur21_son_kanit'


def run():
    db = server = b = None
    checks, complete = [], False
    deadline = (date.today() + timedelta(days=14)).strftime('%d.%m.%Y')
    try:
        db = Database(empty=True)
        server = ApiServer(db, HERE.parent / 'build')
        threading.Thread(target=server.serve_forever, daemon=True).start()
        b = Browser(); b.ws.settimeout(60)
        b.navigate(f'http://127.0.0.1:{server.server_port}/')
        b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')", 60)

        def ok(name):
            checks.append(name); print('GEÇTİ: ' + name, flush=True)

        def op(code):
            click(b, '[data-code="' + code + '"]')
            b.wait("!!document.querySelector('dialog[open] form')")

        def select(task, tab):
            page(b, 'tasks'); click(b, '[data-action=tab][data-tab=' + tab + ']')
            click(b, 'tr[data-id="' + task['kimlik'] + '"]')
            b.wait("!!document.querySelector('.task-heading')&&!document.querySelector('.loading-line')")

        def read(veri, hedef=None):
            return db.rpc('K004', 'oku', {'veri': veri, 'hedef': hedef})['deger']

        def event_count():
            driver = db.driver()
            try: return driver._cagir('SELECT count(*) FROM public.olaylar', kontrol=True)
            finally: driver.kapat()

        page(b, 'projects'); op('PROJE.ACTIM')
        for k, v in {'kod': 'T21-SON', 'ad': 'Son Not Kontrolü', 'sorumlu': 'K004', 'teslim_tarihi': deadline}.items(): field(b, k, v)
        submit(b); b.wait("document.querySelector('.project-summary h2')?.textContent==='Son Not Kontrolü'", 40)
        op('ETAP.TANIMLADIM')
        for k, v in {'ad': 'Ofis Etabı', 'birim': 'MEK_TASARIM', 'sorumlu': 'K004', 'bitis': deadline, 'hedef_saat': 20}.items(): field(b, k, v)
        submit(b); stage = read('ETAPLAR', 'T21-SON')[0]['kimlik']
        profile(b, 'K004', 'Yönetici'); page(b, 'assign'); click(b, '[data-action=assign-add]')
        for k, v in {'ad': 'Önce Açılan Son Biten', 'proje': 'T21-SON', 'kisi': 'K041', 'teslim_tarihi': deadline, 'zaman_degeri': 2, 'zorluk': 2, 'onaylayan': 'K004'}.items(): field(b, k, v)
        assert b.js("document.querySelector('[data-path=etap]').selectedOptions[0].textContent") == 'Seçiniz'
        click(b, '[data-action=assign-review]')
        b.wait("document.querySelector('[data-path=etap]').getAttribute('aria-invalid')==='true'")
        assert not b.js("!!document.querySelector('dialog[open]')")
        field(b, 'etap', '@none')
        # Önceki eksik alan vurgusunu temizle; kutuların kendi yerleşimini ölç.
        field(b, 'onay_gerekli', True)
        assert not b.js("[...document.querySelectorAll('.checkbox-field span')].some(x=>x.textContent.includes('*'))")
        for width in [1440, 960]:
            b.call('Emulation.setDeviceMetricsOverride', width=width, height=1000, deviceScaleFactor=1, mobile=False)
            positions = "['onay_gerekli','dosya_gerekli'].map(k=>{const r=document.querySelector('[data-path='+k+']').getBoundingClientRect();return [r.x,r.y+scrollY]})"
            before = b.js(positions); field(b, 'onay_gerekli', False); after = b.js(positions)
            assert all(abs(x-y) < 1 for a, z in zip(before, after) for x, y in zip(a, z)), (width, before, after)
            assert not b.js("!!document.querySelector('[data-path=onaylayan]')")
            field(b, 'onay_gerekli', True)
        b.call('Emulation.setDeviceMetricsOverride', width=1440, height=1000, deviceScaleFactor=1, mobile=False)
        field(b, 'proje', ''); field(b, 'proje', 'T21-SON')
        assert b.js("document.querySelector('[data-path=etap]').value") == ''
        field(b, 'etap', stage); field(b, 'etap', '@none')
        b.js("document.querySelector('[data-path=onay_gerekli]').scrollIntoView({block:'center'})")
        b.screenshot(OUT / '01_sabit_kutular.png')
        ok('Etapta açık seçim zorunlu; Etap Dışı seçilebilir; proje değişince sıfırlanır; yıldızsız kutular iki genişlikte yerinde')

        click(b, '[data-action=assign-copy]')
        assert b.js("document.querySelector('[data-path=etap]').value") == '@none'
        field(b, 'ad', 'Sonra Açılan Önce Biten'); field(b, 'etap', stage)
        click(b, '[data-action=assign-review]'); b.wait("!!document.querySelector('[data-assign]')", 40)
        click(b, '[data-assign]'); b.wait("!document.querySelector('dialog[open]')", 45)
        tasks = [t for t in read('WEB_GOREVLER') if t.get('proje') == 'T21-SON' and t['tur'] == 'NORMAL']
        first = next(t for t in tasks if t['ad'] == 'Önce Açılan Son Biten')
        second = next(t for t in tasks if t['ad'] == 'Sonra Açılan Önce Biten')
        assert not first.get('etap') and second['etap'] == stage
        ok('Çoğaltmada bilinçli seçim korunur; gerçek atamada etapsız ve etaplı görev doğru oluşur')

        profile(b, 'K041', 'Ofis Çalışanı')
        for task in [first, second]:
            select(task, 'waiting'); click(b, '[data-code="GOREV.KABUL_ETTIM"]')
            b.wait("!document.querySelector('.loading-line')&&!document.querySelector('.task-heading')", 45)
        for task in [second, first]:
            select(task, 'open'); op('GOREV.TAMAMLADIM')
            paths = b.js("[...document.querySelectorAll('dialog[open] [data-path]')].map(x=>x.dataset.path)")
            assert paths == ['not', '_files', 'gecikme_nedeni', 'gecikme_aciklamasi'], paths
            field(b, 'not', task['ad'] + ' teslim notu')
            field(b, 'gecikme_aciklamasi', 'Alan sırası doğrulandı.')
            b.screenshot(OUT / '02_teslim_sirasi.png'); submit(b)
            wait_state(db, 'GOREV', task['kimlik'], 'ONAY_BEKLIYOR', 'K041')
        ok('Teslim Notu ilk kutu; dosya alanı sonra; gecikme alanları en altta; iki gerçek teslim başarılı')

        profile(b, 'K004', 'Yönetici'); page(b, 'approvals')
        assert b.js("parseFloat(getComputedStyle(document.querySelector('.approval-list th')).fontSize)") == 12
        assert b.js("parseFloat(getComputedStyle(document.querySelector('.approval-list td strong')).fontSize)") == 14
        assert b.js("parseFloat(getComputedStyle(document.querySelector('.approval-list td small')).fontSize)") == 12
        for width in [1440, 960]:
            b.call('Emulation.setDeviceMetricsOverride', width=width, height=1000, deviceScaleFactor=1, mobile=False)
            assert b.js('document.documentElement.scrollWidth<=innerWidth+1')
        b.call('Emulation.setDeviceMetricsOverride', width=1440, height=1000, deviceScaleFactor=1, mobile=False)
        b.screenshot(OUT / '03_onay_tablosu.png')
        opbutton = '[data-code="GOREV.REDDETTIM"][data-id="' + first['kimlik'] + '"]'
        click(b, opbutton); b.wait("!!document.querySelector('[data-add=sorumlular]')")
        def gap():
            return b.js("(()=>{const a=document.querySelector('[data-form-section=\"Sorumluluk\"]'),z=document.querySelector('[data-form-section=\"Ayrı Revizyon Görevi\"]');return z.getBoundingClientRect().top-a.getBoundingClientRect().bottom})()")
        assert gap() >= 23
        click(b, '[data-form-section="Sorumluluk"] summary'); click(b, '[data-add=sorumlular]')
        assert gap() >= 23
        field(b, 'not', 'Silinmemesi gereken gerekçe'); field(b, 'revizyon_ver', True)
        assert gap() >= 23 and b.js("document.querySelector('[data-path=not]').value") == 'Silinmemesi gereken gerekçe'
        b.screenshot(OUT / '04_bolum_araligi.png'); click(b, '[data-cancel]')
        ok('Onay başlıkları/içerik yazıları büyüdü; dar pencere taşmıyor; sorumluluk/revizyon arasında en az 24px')

        # Yalnız bu yanıt kontrollüdür; ret öncesi SQL'e yazılmaz, tekrar gerçek motora gider.
        rpc = db.rpc; rejected = []
        def hold_once(person, name, params):
            if name == 'olay_ekle' and params.get('olay', {}).get('eylem_kodu') == 'GOREV.ONAYLADIM' and not rejected:
                rejected.append(params['olay']['olay_kimligi'])
                return {'sonuc': 'RED', 'kod': 'HESAP_BEKLIYOR', 'neden': 'Hesap bekliyor'}
            return rpc(person, name, params)
        db.rpc = hold_once
        click(b, '[data-action=quick-approve][data-id="' + second['kimlik'] + '"]'); b.wait("!!document.querySelector('[data-continue]')")
        before = event_count(); click(b, '[data-continue]')
        b.wait("document.querySelector('dialog[open] .form-error')?.textContent==='İşlem gönderilmedi. Biraz sonra tekrar deneyin.'")
        assert event_count() == before and len(rejected) == 1
        assert not b.js("document.querySelector('[data-continue]').disabled")
        assert 'Sonra Açılan Önce Biten' in b.js("document.querySelector('dialog[open]').innerText")
        click(b, '[data-continue]'); b.wait("!document.querySelector('dialog[open]')", 45)
        wait_state(db, 'GOREV', second['kimlik'], 'BITTI')
        assert event_count() == before + 1
        db.rpc = rpc
        ok('Hesap bekleme reddinde kısa uyarı/form korunur ve olay oluşmaz; tekrar gerçek motorda tek onay oluşturur')
        click(b, '[data-action=quick-approve][data-id="' + first['kimlik'] + '"]'); b.wait("!!document.querySelector('[data-continue]')")
        click(b, '[data-continue]'); b.wait("!document.querySelector('dialog[open]')", 45)
        last = wait_state(db, 'GOREV', first['kimlik'], 'BITTI')
        assert last['bitis_ani'] > read('GOREV', second['kimlik'])['bitis_ani']
        page(b, 'projects'); click(b, '[data-action=project-open][data-id="T21-SON"]')
        b.wait("!!document.querySelector('.project-summary')&&!document.querySelector('.loading-line')")
        click(b, '[data-action=tab][data-tab=jobs]')
        names = b.js("[...document.querySelectorAll('.project-workspace tbody tr td:first-child strong')].map(x=>x.textContent)")
        assert names.index(first['ad']) < names.index(second['ad']), names
        b.screenshot(OUT / '05_tamamlanma_sirasi.png')
        ok('Oluşturma sırası farklı iki gerçek görevde en son tamamlanan üstte; etap bağı ve tamamlanma durumu korunur')
        assert not b.errors, b.errors
        assert not db.errors, db.errors
        complete = True
    finally:
        if b:
            if not complete:
                print('SON EKRAN:', b.js('document.body.innerText.slice(-3200)'), flush=True)
                b.screenshot(OUT / 'hata.png')
            b.close()
        if server: server.shutdown(); server.server_close()
        if db: db.close()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'sonuc.json').write_text(json.dumps({'tamamlandi': complete, 'gecen': checks}, ensure_ascii=False, indent=2))


if __name__ == '__main__': run()
