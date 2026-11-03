"""Tutar değişikliği, bildirimler, kural işi (SPEC › 8.5–8.7; senaryo M11A05)."""
from m11a.alan import kurallar
from m11a.baglanti import CekirdekHatasi
from testler.akis import _y, ac, erisim_ver, etap_ve_gorev, kutu, parcalar, tutar_degistir
from testler.conftest import retler, senaryo_kaydet


def _acik(api):
    return sorted((r['proje'], r['kural']) for r in api.vt.execute('SELECT * FROM mod_m11a.acik_bildirimler'))


def test_M11A05_bildirim_sapma(api):
    ac(api)
    erisim_ver(api, 'K060')
    etap_ve_gorev(api)
    parcalar(api, hazir=0)                                     # dört parça da SIPARIS_VERILMELI

    r = tutar_degistir(api, ISCILIK='2000.00', gerekce='İşçilik yeniden planlandı')
    assert r.status_code == 200, r.json()
    s = r.json()['serit']
    assert (s['dolum_yuzde'], s['ilerleme_yuzde'], s['sapma_puan'], s['renk']) == (32.0, 0.0, 32.0, 'KIRMIZI')
    assert kutu(api, 'K060') == ['TUTAR_DEGISTI']
    assert kutu(api, 'K050') == ['BUTCE_SAPMASI'] and kutu(api, 'K001') == ['BUTCE_SAPMASI']
    metin = api.vt.execute("SELECT metin FROM mod_m11a.acik_bildirimler WHERE kural = 'BUTCE_SAPMASI'").fetchone()
    assert metin['metin'] == ('2611001 710 Projesi Burç Çakma Ekipmanı · İşçilik dolumu %32,0, ilerleme %0,0 '
                              '(32,0 puan; eşik 15)')

    s = tutar_degistir(api, ISCILIK='10000.00', gerekce='Plan geri alındı').json()['serit']
    assert (s['dolum_yuzde'], s['renk']) == (6.4, 'YESIL')
    assert kutu(api, 'K050') == [] and kutu(api, 'K001') == []
    metin = api.vt.execute("SELECT metin FROM mod_m11a.acik_bildirimler WHERE kural = 'TUTAR_DEGISTI'").fetchone()
    assert metin['metin'].endswith('(değişiklik #2)')          # tek bildirim durur, metni güncellenir

    assert tutar_degistir(api, ISCILIK='2000.00').json()['serit']['renk'] == 'KIRMIZI'
    assert kutu(api, 'K050') == ['BUTCE_SAPMASI']
    assert _acik(api) == [('2611001', 'BUTCE_SAPMASI'), ('2611001', 'TUTAR_DEGISTI')]

    k001 = api.c.giris('K001', 'deneme')
    _y(api, 'PROJE.KAPATTIM', {}, neyin_ustunde=[k001.hedef('PROJE', k001.oku('PROJE', '2611001').deger)])
    assert kurallar.calistir(api.c, api.vt) == {'kaldirilan': 2}
    assert _acik(api) == [] and kutu(api, 'K050') == [] and kutu(api, 'K060') == []
    assert kurallar.calistir(api.c, api.vt) == {}               # tekrar güvenli

    assert retler(senaryo_kaydet(api.c, 'M11A05_bildirim_sapma')) == {}


def test_tutar_degisikligi_kayitlari(api):
    ac(api)
    r = tutar_degistir(api, yeni_tutar='50000.00', MALZEME='26500.00', gerekce='Robotu müşteri verecek')
    pn = r.json()['panel']
    assert (pn['sozlesme_tutari'], pn['guncel_tutar']) == ('56000.00', '50000.00')
    malzeme = next(k for k in pn['kalemler'] if k['kalem'] == 'MALZEME')
    assert (malzeme['baslangic'], malzeme['guncel']) == ('32500.00', '26500.00')
    (d,) = pn['degisiklikler']
    assert (d['kim'], d['eski_tutar'], d['yeni_tutar'], d['gerekce']) == ('K050', '56000.00', '50000.00',
                                                                         'Robotu müşteri verecek')
    assert (d['butce_eski']['MALZEME'], d['butce_yeni']['MALZEME']) == ('32500.00', '26500.00')
    assert d['belge']['ad'] == 'Kapsam_degisikligi.pdf'


def test_tutar_degisikligi_yetki_ve_dogrulama(api):
    ac(api)
    erisim_ver(api, 'K060')
    assert tutar_degistir(api, 'K060').status_code == 403
    r = api('POST', 'K050', '/projeler/2611001/tutar-degisikligi',
            json={'yeni_tutar': '1.00', 'butce': {'MALZEME': '-1'}, 'gerekce': ' '})
    assert r.status_code == 422 and {h['alan'] for h in r.json()['hatalar']} == {'gerekce', 'butce', 'butce.MALZEME',
                                                                                 'belge'}


def test_tutar_degisti_basarisizsa_kural_isi_birakir(api, monkeypatch):
    ac(api)
    erisim_ver(api, 'K060')

    def kopuk(*a, **k):
        raise CekirdekHatasi('BAGLANTI', 'ağ')
    monkeypatch.setattr(api.c.surucu, 'bildirim', kopuk)
    assert tutar_degistir(api).status_code == 200
    monkeypatch.undo()
    assert kutu(api, 'K060') == []
    assert kurallar.calistir(api.c, api.vt) == {'birakilan': 1}
    assert kutu(api, 'K060') == ['TUTAR_DEGISTI']
    assert kurallar.calistir(api.c, api.vt) == {}


def test_servis_okumasi_yoksa_oteki_adimlar_calisir(api, monkeypatch):
    ac(api)
    erisim_ver(api, 'K060')
    api('POST', 'K050', '/projeler/2611001/devir')
    api.vt.execute("UPDATE mod_m11a.devirler SET bildirim_birakildi = false")

    def yok(*a, **k):
        raise CekirdekHatasi('BICIM', 'servis_oku yok')
    monkeypatch.setattr(api.c.surucu, 'servis_oku', yok)
    assert kurallar.calistir(api.c, api.vt) == {'birakilan': 1}


def test_bildirimleri_kaldir(api):
    ac(api)
    erisim_ver(api, 'K060')
    api('POST', 'K050', '/projeler/2611001/devir')
    tutar_degistir(api)
    assert len(_acik(api)) == 2
    assert kurallar.hepsini_kaldir(api.c, api.vt) == 2
    assert _acik(api) == [] and kutu(api, 'K060') == []
