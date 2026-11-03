"""Kapanış ve kapanış sonrası düzeltme (SPEC › 8.8; senaryo M11A07)."""
from m11a.alan import kurallar
from testler.akis import ac, erisim_ver, kutu, tutar_degistir
from testler.conftest import retler, senaryo_kaydet

FATURA = {'ad': 'Fatura_2027_118.pdf', 'konum': '\\\\sunucu\\muhasebe\\2611001\\fatura118.pdf'}


def test_M11A07_tutar_ve_kapanis(api):
    ac(api)
    erisim_ver(api, 'K060')
    r = tutar_degistir(api, yeni_tutar='50000.00', MALZEME='26500.00', gerekce='Robotu müşteri verecek')
    pn = r.json()['panel']
    assert (pn['sozlesme_tutari'], pn['guncel_tutar']) == ('56000.00', '50000.00')
    assert {k['kalem']: (k['baslangic'], k['guncel']) for k in pn['kalemler']}['MALZEME'] == ('32500.00', '26500.00')
    assert kutu(api, 'K060') == ['TUTAR_DEGISTI']

    r = api('POST', 'K060', '/projeler/2611001/kapanis', json={'kesin_kabul_tarihi': '2027-05-23'})
    assert r.status_code == 200, r.json()
    k = r.json()['panel']['kapanis']
    assert (k['kesin_kabul_tarihi'], k['kapatan'], k['duzeltmeler']) == ('2027-05-23', 'K060', [])
    assert k['an'].endswith('+03:00')                                   # çekirdeğin saati
    assert [(f['kalem'], f['butce'], f['gerceklesen'], f['fark'], f['kaynak']) for f in k['farklar']] == [
        ('MALZEME', '26500.00', None, None, 'BILGI_YOK_M3'),
        ('ISCILIK', '10000.00', '0.00', '10000.00', 'SAAT_X_UCRET'),
        ('FASON', '1000.00', None, None, 'BILGI_YOK_M3'),
        ('GENEL_GIDER', '0.00', None, None, 'FORMUL_YOK')]
    assert r.json()['serit']['butce_durumu'] == 'KAPALI'
    assert kutu(api, 'K060') == []
    assert api.vt.execute('SELECT count(*) AS n FROM mod_m11a.acik_bildirimler').fetchone()['n'] == 0

    r = tutar_degistir(api, yeni_tutar='45000.00')
    assert (r.status_code, r.json()['kod']) == (409, 'BUTCE_KAPALI')

    r = api('POST', 'K060', '/projeler/2611001/kapanis-sonrasi',
            json={'kalem': 'MALZEME', 'tutar': '1200.00', 'gerekce': 'Kilitten sonra gelen fatura',
                  'belge_dosyasi': FATURA})
    assert r.status_code == 200, r.json()
    pb = api('GET', 'K060', '/saglanan/M11A.PROJE_BUTCESI?proje=2611001').json()
    assert [(d['kalem'], d['tutar'], d['gerekce']) for d in pb['kapanis']['duzeltmeler']] == [
        ('MALZEME', '1200.00', 'Kilitten sonra gelen fatura')]
    assert pb['kapanis']['farklar'] == k['farklar'] and pb['butce_durumu'] == 'KAPALI'
    assert (pb['sozlesme_tutari'], pb['guncel_tutar']) == ('56000.00', '50000.00')

    assert retler(senaryo_kaydet(api.c, 'M11A07_tutar_ve_kapanis')) == {}


def test_kapanis_kurallari(api):
    ac(api)
    erisim_ver(api, 'K060')
    assert api('POST', 'K050', '/projeler/2611001/kapanis', json={}).status_code == 403
    r = api('POST', 'K060', '/projeler/2611001/kapanis-sonrasi', json={'kalem': 'FASON', 'tutar': '-5.00',
                                                                       'gerekce': 'iade'})
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')
    r = api('POST', 'K060', '/projeler/2611001/kapanis', json={})       # varsayılan: çekirdeğin kesin kabulü
    assert r.json()['panel']['kapanis']['kesin_kabul_tarihi'] == '2027-05-23'
    assert api('POST', 'K060', '/projeler/2611001/kapanis', json={}).json()['kod'] == 'BUTCE_KAPALI'
    r = api('POST', 'K060', '/projeler/2611001/kapanis-sonrasi', json={'kalem': 'FASON', 'tutar': '-5.00',
                                                                       'gerekce': ' '})
    assert r.status_code == 422
    r = api('POST', 'K001', '/projeler/2611001/kapanis-sonrasi', json={'kalem': 'FASON', 'tutar': '-5.00',
                                                                       'gerekce': 'iade'})
    assert r.json()['panel']['kapanis']['duzeltmeler'][0]['tutar'] == '-5.00'


def test_kesin_kabul_yoksa_tarih_zorunlu(api):
    from testler.akis import donustur
    r = donustur(api, kesin_kabul_tarihi=None)
    assert r.status_code == 200
    erisim_ver(api, 'K060')
    r = api('POST', 'K060', '/projeler/2611001/kapanis', json={})
    assert (r.status_code, r.json()['hatalar'][0]['alan']) == (422, 'kesin_kabul_tarihi')


def test_kural_isi_kapali_butcede_kaldirir(api, monkeypatch):
    from m11a.baglanti import CekirdekHatasi
    ac(api)
    erisim_ver(api, 'K060')
    tutar_degistir(api)
    asil = api.c.surucu.bildirim

    def kaldiramaz(servis, ad, g):
        if ad == 'kaldir':
            raise CekirdekHatasi('BAGLANTI', 'ağ')
        return asil(servis, ad, g)
    monkeypatch.setattr(api.c.surucu, 'bildirim', kaldiramaz)
    api('POST', 'K060', '/projeler/2611001/kapanis', json={})
    monkeypatch.undo()
    assert kutu(api, 'K060') == ['TUTAR_DEGISTI']
    assert kurallar.calistir(api.c, api.vt) == {'kaldirilan': 1}
    assert kutu(api, 'K060') == []
