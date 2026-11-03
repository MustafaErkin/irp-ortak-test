"""Ayarlar, sağlanan okumalar, müşteri PDF'i (SPEC › 8.9, 8.10, Ek D.7)."""
import base64
import hashlib

from testler.akis import ac, erisim_ver, etap_ve_gorev
from testler.ornek import kazanan_surum

AYAR = {'proje_kodu_deseni': '{YY}{AA}{SIRA3}', 'proje_kodu_sira_kapsami': 'YIL',
        'siparis_adi_deseni': '{YYYY}-{YILLIK_SIRA3}-{PROJE_KODU}___{MUSTERI}-{PROJE_ADI}_{PO}',
        'sapma_esigi_puan': '15', 'yaklasan_tarih_gun': 30, 'saat_ucretleri': []}


def test_ayarlar_yalnizca_yetkili(api):
    assert api('GET', 'K050', '/ayarlar').status_code == 403
    assert api('PUT', 'K060', '/ayarlar', json=AYAR).status_code == 403
    a = api('GET', 'K001', '/ayarlar').json()
    assert a['proje_kodu_deseni'] == '{YY}{AA}{SIRA3}' and a['sapma_esigi_puan'] == 15


def test_bilinmeyen_degisken_422(api):
    for alan, deger in (('siparis_adi_deseni', '{YYYY}-{GUN}'), ('proje_kodu_deseni', '{YY}{MUSTERI}{SIRA3}'),
                        ('proje_kodu_deseni', '{YY}{AA}')):
        r = api('PUT', 'K001', '/ayarlar', json={**AYAR, alan: deger})
        assert (r.status_code, r.json()['hatalar'][0]['alan']) == (422, alan), deger
    r = api('PUT', 'K001', '/ayarlar', json={**AYAR, 'saat_ucretleri': [{'birim': 'YOK', 'ucret': '1.00',
                                                                         'para_birimi': 'TRY'}]})
    assert r.status_code == 422


def test_ay_kapsami_ve_desen(api):
    r = api('PUT', 'K001', '/ayarlar', json={**AYAR, 'proje_kodu_deseni': 'P{YYYY}{AA}-{SIRA3}',
                                             'proje_kodu_sira_kapsami': 'AY', 'sapma_esigi_puan': '20.5'})
    assert r.status_code == 200 and r.json()['sapma_esigi_puan'] == 20.5
    assert api('GET', 'K050', '/donustur/onizleme?surum=57').json()['proje_kodu'] == 'P202611-001'
    assert ac(api) == 'P202611-001'
    assert api.vt.execute("SELECT donem FROM mod_m11a.sayaclar WHERE ad = 'PROJE_KODU'").fetchone()['donem'] == '2026-11'


def test_yedek_saat_ucreti_olcume_girer(api):
    ac(api)
    etap_ve_gorev(api)
    # Teklifte bu birimin işçiliği olmasaydı: donmuş ücret yok, yedek ücret ayarlardan gelir
    api.vt.execute("DELETE FROM mod_m11a.proje_saat_ucretleri WHERE birim = 'MEK_TASARIM'")
    pn = api('GET', 'K050', '/projeler/2611001/butce').json()['panel']
    assert pn['bilinmeyen_saat'] == '12.8'                          # ücreti bilinmeyen birim
    r = api('PUT', 'K001', '/ayarlar', json={**AYAR, 'saat_ucretleri': [
        {'birim': 'MEK_TASARIM', 'ucret': '1760.00', 'para_birimi': 'TRY'}]})
    assert r.json()['saat_ucretleri'] == [{'birim': 'MEK_TASARIM', 'ucret': '1760.00', 'para_birimi': 'TRY'}]
    pn = api('GET', 'K050', '/projeler/2611001/butce').json()['panel']
    assert pn['bilinmeyen_saat'] == '0.0'
    assert next(k for k in pn['kalemler'] if k['kalem'] == 'ISCILIK')['tahmini_gerceklesen'] == '640.00'


def test_teklif_girdileri_ve_pdf(api):
    ac(api)
    etap_ve_gorev(api)                                  # K012 projeyi görür
    for kisi in ('K050', 'K012'):
        t = api('GET', kisi, '/saglanan/M11A.TEKLIF_GIRDILERI?proje=2611001').json()
        assert (t['kaynak'], t['konu']) == ('T-2026-0012/V2', '710 Projesi Burç Çakma Ekipmanı')
        assert t['gereksinimler'][0]['metin'] == 'Çevrim süresi 45 sn altında'
        assert t['kapsam']['haric'] == ['Saha elektrik altyapısı'] and t['dosyalar'][0]['tur'] == 'SARTNAME'
        assert t['musteri_pdf']['yol'] == '/api/projeler/2611001/teklif-pdf'
        assert not ({'fiyat', 'maliyet', 'kar_orani', 'toplamlar', 'kalemler', 'iscilik'} & set(t))
        assert api('GET', kisi, '/projeler/2611001/teklif-girdileri').json() == t
        r = api('GET', kisi, '/projeler/2611001/teklif-pdf')
        assert r.headers['content-type'] == 'application/pdf'
        assert r.content == base64.b64decode(kazanan_surum()['pdf']['icerik_base64'])
        assert hashlib.sha256(r.content).hexdigest() == t['musteri_pdf']['parmak_izi']
    assert api('GET', 'K017', '/projeler/2611001/teklif-pdf').status_code == 403
    plan = api('GET', 'K012', '/projeler/2611001/baslangic-plani').json()
    assert len(plan['etaplar']) == 10 and plan['kesin_kabul_tarihi'] == '2027-05-23'


def test_saglanan_hatalari(api):
    ac(api)
    assert api('GET', 'K050', '/saglanan/M11A.YOK?proje=2611001').json()['kod'] == 'TANIMSIZ_VERI'
    r = api('GET', 'K050', '/saglanan/M11A.BASLANGIC_PLANI')
    assert (r.status_code, r.json()['kod']) == (422, 'DOGRULAMA')
    r = api('GET', 'K001', '/saglanan/M11A.BASLANGIC_PLANI?proje=2614')        # çekirdekte var, M1.1A kaydı yok
    assert (r.status_code, r.json()['kod']) == (404, 'BULUNAMADI')
    r = api('GET', 'K060', '/saglanan/M11A.BUTCE_YUZDELERI?proje=2611001')
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')
    erisim_ver(api, 'K060')
    assert api('GET', 'K060', '/saglanan/M11A.PROJE_BUTCESI?proje=2611001').status_code == 200
    r = api('GET', 'K001', '/projeler/2614')
    assert (r.status_code, r.json()['mesaj']) == (404, 'Bu projenin M1.1A kaydı yok.')
