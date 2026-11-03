"""Siparişe dönüştürme (SPEC › 8.1; senaryolar M11A01, M11A02, M11A08)."""
from m11a.baglanti import CekirdekHatasi
from m11a.saglayicilar import SaglayiciHatasi, SahteM10Saglayici
from testler.akis import PO_DOSYASI, SOZLESME, ac, donustur, govde
from testler.conftest import olay_sayisi, retler, senaryo_kaydet
from testler.ornek import ek_is, kazanan_surum
from testler.test_saf import PLAN


def _projeler(api):
    return api.vt.execute('SELECT proje, durum, acilis_olayi FROM mod_m11a.projeler ORDER BY proje').fetchall()


def test_M11A01_siparise_donustur(api):
    on = api('GET', 'K050', '/donustur/onizleme?surum=57').json()
    assert (on['proje_kodu'], on['sorumlu'], on['siparis_tarihi']) == ('2611001', 'K050', '2026-11-02')
    assert (on['teslim_tarihi'], on['kesin_kabul_tarihi'], on['kayma_hafta']) == ('2027-05-16', '2027-05-23', 3)
    assert on['siparis_adi'] == '2026-001-2611001___Autoliv-710 Projesi Burç Çakma Ekipmanı_PO-BEKLENIYOR'
    assert on['butce'] == {'MALZEME': '32500.00', 'ISCILIK': '10000.00', 'FASON': '1000.00', 'GENEL_GIDER': '0.00'}
    assert on['sozlesme_tutari'] == '56000.00' and on['ana_proje'] is None

    r = api('POST', 'K050', '/donustur', json=govde(on, po_no='PO1246789', po_dosyasi=PO_DOSYASI,
                                                    sozlesme_dosyasi=SOZLESME))
    assert r.status_code == 200, r.json()
    s = r.json()
    assert s['proje'] == '2611001' and s['acilis_olayi'] == 'K050-2611020001-Q'
    assert s['siparis_adi'] == '2026-001-2611001___Autoliv-710 Projesi Burç Çakma Ekipmanı_PO1246789'
    assert not s['po_bekleniyor']
    assert [e['alan'] for e in s['eksikler']] == ['ODEME_TAKVIMI', 'FATURALAMA', 'TESLIM_SEKLI', 'IHRACAT', 'TESVIK',
                                                  'TEMINAT']
    assert '2611001' in s['m11b']['mesaj']

    p = api.c.giris('K050', 'deneme').oku('PROJE', '2611001').deger
    assert (p['sorumlu'], p['baslangic_tarihi'], p['teslim_tarihi'], p['kesin_kabul_tarihi'], p['musteri']) == (
        'K050', '2026-11-02', '2027-05-16', '2027-05-23', 'Autoliv')

    plan = api('GET', 'K050', '/saglanan/M11A.BASLANGIC_PLANI?proje=2611001').json()
    assert (plan['kaynak'], plan['teslim_suresi_hafta']) == ('T-2026-0012/V2', 28)
    assert [(e['etap_kodu'], e['baslangic'], e['bitis']) for e in plan['etaplar']] == PLAN

    olaylar = olay_sayisi(api.c)
    r = api('POST', 'K050', '/donustur', json=govde(on))
    assert (r.status_code, r.json()['kod'], r.json()['proje']) == (409, 'ZATEN_DONUSTU', '2611001')
    assert olay_sayisi(api.c) == olaylar
    assert api('GET', 'K050', '/donustur/onizleme?surum=57').json()['zaten_donustu'] is True

    assert retler(senaryo_kaydet(api.c, 'M11A01_siparise_donustur')) == {}


def test_M11A02_kod_ve_yetki(api):
    r = donustur(api, proje_kodu='2614')
    assert (r.status_code, r.json()['kod'], r.json()['onerilen_kod']) == (409, 'KOD_KULLANILIYOR', '2611001')
    assert _projeler(api) == []
    assert api.vt.execute("SELECT son FROM mod_m11a.sayaclar WHERE ad = 'SIPARIS'").fetchone()['son'] == 0

    r = api('GET', 'K004', '/donustur/onizleme?surum=57')
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')
    r = api('POST', 'K004', '/donustur', json=govde(api('GET', 'K050', '/donustur/onizleme?surum=57').json()))
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')

    # Çekirdeğin kuralı: SATIS'i olmayan K004'ün doğrudan PROJE.ACTIM'ı çekirdekten YETKI alır.
    cevap = api.c.giris('K004', 'deneme').olay_gonder('PROJE.ACTIM', {
        'kimlik': '2611009', 'kod': '2611009', 'ad': 'Deneme', 'musteri': 'Autoliv', 'sorumlu': 'K004',
        'baslangic_tarihi': '2026-11-02', 'teslim_tarihi': '2027-05-16'})
    assert cevap.kod == 'YETKI'

    assert retler(senaryo_kaydet(api.c, 'M11A02_kod_ve_yetki')) == {'olay: REDDEDILDI DURUM': 1,
                                                                    'olay: REDDEDILDI YETKI': 1}


def test_M11A08_ek_is(api):
    api.m10.ekle(ek_is(58, '2611001'))
    api.m10.ekle(ek_is(59, '2611002'))
    assert ac(api) == '2611001'
    on = api('GET', 'K050', '/donustur/onizleme?surum=58').json()
    assert (on['kaynak'], on['ana_proje'], on['proje_kodu']) == ('EK_IS', '2611001', '2611002')
    assert ac(api, surum=58) == '2611002'
    assert api.c.giris('K050', 'deneme').oku('PROJE', '2611002').deger['ana_proje'] == '2611001'

    r = donustur(api, surum=59)
    assert (r.status_code, r.json()['kod']) == (409, 'ANA_PROJE')
    assert [p['proje'] for p in _projeler(api)] == ['2611001', '2611002']

    assert retler(senaryo_kaydet(api.c, 'M11A08_ek_is')) == {'olay: REDDEDILDI DURUM': 1}


# ---- hata yolları (senaryoya yazılmaz)

def test_m10_ulasilamiyor(api):
    api.m10.hata = SaglayiciHatasi('SAGLAYICI_YOK', 'kapalı')
    r = api('GET', 'K050', '/donustur/onizleme?surum=57')
    assert (r.status_code, r.json()['kod']) == (503, 'SAGLAYICI_YOK')
    api.m10.hata = SaglayiciHatasi('YETKI', 'yok', 403)
    r = api('GET', 'K050', '/donustur/onizleme?surum=57')
    assert (r.status_code, r.json()['mesaj']) == (403, 'Bu teklifi görme yetkiniz yok.')


def test_kapi(api):
    api.m10.ekle(kazanan_surum(surum=60, durum='HAZIRLANIYOR'))
    r = api('GET', 'K050', '/donustur/onizleme?surum=60')
    assert (r.status_code, r.json()['kod']) == (409, 'KAPI')
    # M1.0 kapıyı uygulamasa da M1.1A ayrıca denetler
    api.m10.kapi = False
    api.m10.ekle(kazanan_surum(surum=61, talep_durumu='KAYBEDILDI'))
    for surum in (60, 61):
        r = api('GET', 'K050', f'/donustur/onizleme?surum={surum}')
        assert (r.status_code, r.json()['kod']) == (409, 'KAPI')
    on = api('GET', 'K050', '/donustur/onizleme?surum=57').json()
    r = api('POST', 'K050', '/donustur', json=govde(on, surum=61))
    assert (r.status_code, r.json()['kod']) == (409, 'KAPI') and _projeler(api) == []


def test_dogrulama(api):
    on = api('GET', 'K050', '/donustur/onizleme?surum=57').json()
    r = api('POST', 'K050', '/donustur', json=govde(on, teslim_tarihi='2026-11-01', kesin_kabul_tarihi='2026-10-01',
                                                    sorumlu='K999', proje_adi=' ', proje_kodu='26/14'))
    assert r.status_code == 422 and r.json()['kod'] == 'DOGRULAMA'
    assert {h['alan'] for h in r.json()['hatalar']} == {'teslim_tarihi', 'kesin_kabul_tarihi', 'sorumlu',
                                                        'proje_adi', 'proje_kodu'}
    assert _projeler(api) == []


def test_pdf_parmak_izi_uyusmazsa(api):
    k = kazanan_surum()
    k['pdf']['parmak_izi'] = 'f' * 64
    api.m10.ekle(k)
    r = donustur(api)
    assert (r.status_code, r.json()['kod']) == (502, 'BEKLENMEYEN') and _projeler(api) == []


def test_modulde_olan_elle_kod(api):
    ac(api)
    api.m10.ekle(kazanan_surum(surum=62, etiket='T-62'))
    olaylar = olay_sayisi(api.c)
    r = donustur(api, surum=62, proje_kodu='2611001')
    assert (r.status_code, r.json()['kod'], r.json()['onerilen_kod']) == (409, 'KOD_KULLANILIYOR', '2611002')
    assert olay_sayisi(api.c) == olaylar


def _kopuk(api, monkeypatch, once_ilet: bool):
    asil = api.c.surucu.olay_ekle

    def kopuk(*a, **k):
        if once_ilet:
            asil(*a, **k)
        raise CekirdekHatasi('BAGLANTI', 'ağ')
    monkeypatch.setattr(api.c.surucu, 'olay_ekle', kopuk)
    r = donustur(api)
    assert (r.status_code, r.json()['kod'], r.json()['proje']) == (503, 'BAGLANTI', '2611001')
    assert _projeler(api) == [{'proje': '2611001', 'durum': 'ACILIYOR', 'acilis_olayi': None}]
    monkeypatch.setattr(api.c.surucu, 'olay_ekle', asil)


def test_cekirdek_kabul_etti_ag_koptu(api, monkeypatch):
    _kopuk(api, monkeypatch, once_ilet=True)
    r = api('GET', 'K050', '/saglanan/M11A.BASLANGIC_PLANI?proje=2611001')
    assert (r.status_code, r.json()['kod']) == (409, 'KAPI')
    assert api('POST', 'K001', '/donustur/2611001/yeniden-dene').status_code == 404
    olaylar = olay_sayisi(api.c)
    r = api('POST', 'K050', '/donustur/2611001/yeniden-dene')
    assert r.status_code == 200 and r.json()['durum'] == 'ACIK' and r.json()['acilis_olayi'] is None
    assert olay_sayisi(api.c) == olaylar          # PROJE okumasıyla doğrulandı; olay yeniden gitmedi


def test_cekirdege_ulasmadi_yeniden_gonderilir(api, monkeypatch):
    _kopuk(api, monkeypatch, once_ilet=False)
    r = api('POST', 'K050', '/donustur/2611001/yeniden-dene')
    assert r.status_code == 200 and r.json()['acilis_olayi'].startswith('K050-')
    assert api('POST', 'K050', '/donustur/2611001/yeniden-dene').json()['kod'] == 'DURUM'
