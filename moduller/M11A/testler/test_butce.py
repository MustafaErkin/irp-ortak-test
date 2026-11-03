"""Bütçe ölçümü, şerit, panel, bütçeler listesi (SPEC › 8.6; senaryolar M11A04, M11A06)."""
from decimal import ROUND_HALF_UP, Decimal

from testler.akis import ac, erisim_ver, etap_ve_gorev, parcalar
from testler.conftest import retler, senaryo_kaydet
from testler.ornek import kazanan_surum

TUTAR_ALANLARI = {'sozlesme_tutari', 'guncel_tutar', 'tutar', 'kalemler', 'baslangic', 'guncel',
                  'tahmini_gerceklesen', 'ucret'}


def _anahtarlar(x):
    if isinstance(x, dict):
        return set(x) | set().union(*(_anahtarlar(v) for v in x.values()))
    if isinstance(x, list):
        return set().union(*(_anahtarlar(v) for v in x)) if x else set()
    return set()


def test_M11A04_butce_olcumu(api):
    ac(api)
    etap_ve_gorev(api)
    parcalar(api, hazir=1)
    pd = api.c.giris('K050', 'deneme').oku('PROJE_DURUM', '2611001').deger
    saat = Decimal(str(next(iter(pd['etaplar'].values()))['harcanan_emek']))
    assert saat == Decimal('12.8')                       # PROJE_DURUM'dan geldiği gibi; denemede 12,8
    dolum = (saat * 1760 / Decimal('35.2') / 10000 * 100).quantize(Decimal('0.1'), ROUND_HALF_UP)

    r = api('GET', 'K050', '/projeler/2611001/butce').json()
    s = r['serit']
    assert (s['dolum_yuzde'], s['ilerleme_yuzde'], s['sapma_puan'], s['renk'], s['simge']) == (
        float(dolum), 25.0, -18.6, 'YESIL', '●')
    assert s['kapsam'] == ['ISCILIK'] and s['po_bekleniyor'] is True
    iscilik = next(k for k in r['panel']['kalemler'] if k['kalem'] == 'ISCILIK')
    assert iscilik == {'kalem': 'ISCILIK', 'baslangic': '10000.00', 'guncel': '10000.00',
                       'tahmini_gerceklesen': '640.00', 'kaynak': 'SAAT_X_UCRET'}
    assert next(k for k in r['panel']['kalemler'] if k['kalem'] == 'MALZEME')['kaynak'] == 'BILGI_YOK_M3'
    assert r['panel']['iscilik'] == [{'etap': r['panel']['iscilik'][0]['etap'], 'birim': 'MEK_TASARIM',
                                      'saat': '12.8', 'ucret': '1760.00', 'para_birimi': 'TRY', 'tutar': '640.00'}]
    assert r['panel']['ilerleme'] == {'hazir': 1, 'toplam': 4} and r['panel']['bilinmeyen_saat'] == '0.0'

    olcumler = api.vt.execute('SELECT * FROM mod_m11a.butce_olcumleri').fetchall()
    assert len(olcumler) == 1 and float(olcumler[0]['dolum_yuzde']) == 6.4 and olcumler[0]['uyari'] is False
    api('GET', 'K050', '/projeler/2611001/butce')        # aynı değer, bir saat geçmedi: yeni satır yok
    assert api.vt.execute('SELECT count(*) AS n FROM mod_m11a.butce_olcumleri').fetchone()['n'] == 1

    assert retler(senaryo_kaydet(api.c, 'M11A04_butce_olcumu')) == {}


def test_M11A06_gorunurluk(api):
    ac(api)
    etap_ve_gorev(api)                       # K012 etap sorumlusu olarak projeyi görür
    r = api('GET', 'K017', '/projeler/2611001')
    assert (r.status_code, r.json()['mesaj']) == (403, 'Bu projeyi göremiyorsunuz.')

    r = api('GET', 'K012', '/projeler/2611001/butce')
    assert r.status_code == 200 and set(r.json()) == {'serit'}
    assert not (_anahtarlar(r.json()) & TUTAR_ALANLARI)
    y = api('GET', 'K012', '/saglanan/M11A.BUTCE_YUZDELERI?proje=2611001').json()
    assert (y['dolum_yuzde'], y['renk'], y['kapsam']) == (6.4, 'GRI', ['ISCILIK'])
    assert not (_anahtarlar(y) & TUTAR_ALANLARI)
    kart = api('GET', 'K012', '/projeler/2611001').json()
    assert kart['serit']['dolum_yuzde'] == 6.4 and not (_anahtarlar(kart) & TUTAR_ALANLARI)

    for yol in ('/projeler/2611001/ticari', '/saglanan/M11A.PROJE_BUTCESI?proje=2611001', '/butceler'):
        r = api('GET', 'K012', yol)
        assert (r.status_code, r.json()['kod']) == (403, 'YETKI'), yol

    assert retler(senaryo_kaydet(api.c, 'M11A06_gorunurluk')) == {'sorgu: hata PermissionError': 1}


def test_proje_butcesi_okumasi(api):
    ac(api)
    etap_ve_gorev(api)
    r = api('GET', 'K050', '/saglanan/M11A.PROJE_BUTCESI?proje=2611001').json()
    assert (r['sozlesme_tutari'], r['guncel_tutar'], r['butce_durumu'], r['kapanis']) == (
        '56000.00', '56000.00', 'ACIK', None)
    assert {k['kalem']: k['tahmini_gerceklesen'] for k in r['kalemler']} == {
        'MALZEME': None, 'ISCILIK': '640.00', 'FASON': None, 'GENEL_GIDER': None}


def test_butceler_listesi(api):
    ac(api)
    api.m10.ekle(kazanan_surum(surum=65, etiket='T-65'))
    ac(api, surum=65)
    etap_ve_gorev(api, '2611002')
    parcalar(api, hazir=0, toplam=2, proje='2611002')
    api.vt.execute("UPDATE mod_m11a.butce_satirlari SET guncel = 2000 WHERE proje = '2611002' AND kalem = 'ISCILIK'")
    satirlar = api('GET', 'K050', '/butceler').json()['satirlar']
    assert [(s['proje'], s['renk']) for s in satirlar] == [('2611002', 'KIRMIZI'), ('2611001', 'GRI')]
    assert satirlar[0]['etiket'] == 'Dolum ilerlemenin 32,0 puan önünde'
    assert api('GET', 'K060', '/butceler').json()['satirlar'] == []         # K060 projeleri göremiyor
    erisim_ver(api, 'K060')
    assert [s['proje'] for s in api('GET', 'K060', '/butceler').json()['satirlar']] == ['2611001']


def test_aciliyor_proje_listelere_girmez(api, monkeypatch):
    from m11a.baglanti import CekirdekHatasi
    from testler.akis import donustur

    def kopuk(*a, **k):
        raise CekirdekHatasi('BAGLANTI', 'ağ')
    monkeypatch.setattr(api.c.surucu, 'olay_ekle', kopuk)
    assert donustur(api).status_code == 503
    monkeypatch.undo()
    assert api('GET', 'K050', '/butceler').json()['satirlar'] == []
    assert api('GET', 'K001', '/gelen-kutusu').json()['satirlar'] == []
    assert api('GET', 'K050', '/projeler/2611001').json() == {'proje': '2611001', 'durum': 'ACILIYOR',
                                                               'mesaj': 'Açılış tamamlanmadı.'}
    assert api('GET', 'K001', '/projeler/2611001').status_code == 404


def test_hesaplaniyor(api, monkeypatch):
    ac(api)
    asil = api.c.surucu.oku

    def bekliyor(*a, **k):
        return dict(asil(*a, **k), hesap='BEKLIYOR')
    monkeypatch.setattr(api.c.surucu, 'oku', bekliyor)
    r = api('GET', 'K050', '/projeler/2611001/butce').json()
    assert r['hesaplaniyor'] is True and r['serit']['hesaplaniyor'] is True
    assert api.vt.execute('SELECT count(*) AS n FROM mod_m11a.butce_olcumleri').fetchone()['n'] == 0
