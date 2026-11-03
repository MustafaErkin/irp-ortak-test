"""Adım 4: ayarlar, geçmiş proje formu, müşteriler (SPEC › 8.1, 8.14)."""
import pytest

from m10 import vt


@pytest.fixture
def yonetim(istemci, h):
    """K004 (Planlama Müdürü) yönetim birimi sayılır: M1.0'ı görür, ayar yapar, teklif düzenlemez."""
    with vt.islem() as b:
        b.execute("""UPDATE ayarlar SET deger = '["YONETIM", "PLANLAMA"]' WHERE anahtar = 'yonetim_birimleri'""")
    return h('K004')


def _kullanilmis_unsur(unsur):
    """Bir sürümde kullanılmış unsur (yalnızca bu test için doğrudan SQL)."""
    with vt.islem() as b:
        m = b.execute("INSERT INTO musteriler (ad, olusturan, olusturma_ani) VALUES ('X', 'K050', now()) "
                      "RETURNING kimlik").fetchone()['kimlik']
        t = b.execute("INSERT INTO talepler (talep_no, musteri, kaynak, tur, konu, gelis_tarihi, olusturan, olusturma_ani) "
                      "VALUES ('T-2026-9999', %s, 'YENI_IS', 'SAHA_NOTU', 'k', current_date, 'K050', now()) "
                      "RETURNING kimlik", (m,)).fetchone()['kimlik']
        s = b.execute("INSERT INTO teklif_surumleri (talep, no, para_birimi, hazirlayan, olusturma_ani) "
                      "VALUES (%s, 1, 'EUR', 'K050', now()) RETURNING kimlik", (t,)).fetchone()['kimlik']
        b.execute("INSERT INTO maliyet_kalemleri (surum, sira, unsur, aciklama, adet) VALUES (%s, 1, %s, 'a', 1)", (s, unsur))


# ---------------------------------------------------------------- unsurlar

def test_unsurlar_ve_yetki(istemci, h, yonetim):
    r = istemci.get('/api/ayarlar/unsurlar', headers=h('K050'))
    assert r.status_code == 200 and len(r.json()['unsurlar']) == 10
    assert istemci.get('/api/ayarlar/unsurlar', headers=h('K041')).status_code == 403
    assert istemci.get('/api/ayarlar/unsurlar', headers=yonetim).status_code == 200


def test_unsur_guncelle_kullanilmis_kalem_uyarisi(istemci, h):
    unsurlar = istemci.get('/api/ayarlar/unsurlar', headers=h('K050')).json()['unsurlar']
    _kullanilmis_unsur('NAKLIYE')
    for u in unsurlar:
        if u['kod'] in ('NAKLIYE', 'ISIL_ISLEM'):
            u['butce_kalemi'] = 'GENEL_GIDER'
    unsurlar.append({'kod': 'YAZILIM_LISANSI', 'ad': 'Yazılım lisansı', 'butce_kalemi': 'MALZEME', 'sik': False,
                     'aktif': True, 'sira': 95})
    r = istemci.put('/api/ayarlar/unsurlar', headers=h('K050'), json=unsurlar)
    assert r.status_code == 200, r.text
    assert [u['mesaj'] for u in r.json()['uyarilar']] == ['Nakliye ve sevkiyat: Gönderilmiş sürümler eski kalemle kaldı.']
    kodlar = {u['kod']: u for u in r.json()['unsurlar']}
    assert kodlar['ISIL_ISLEM']['butce_kalemi'] == 'GENEL_GIDER' and 'YAZILIM_LISANSI' in kodlar


def test_diger_unsur_kod_uretir(istemci, h, yonetim):
    r = istemci.post('/api/unsurlar', headers=h('K050'), json={'ad': 'Hidrolik ünite', 'butce_kalemi': 'MALZEME'})
    assert r.status_code == 201 and r.json()['kod'] == 'HIDROLIK_UNITE'
    r = istemci.post('/api/unsurlar', headers=h('K001'), json={'ad': 'Hidrolik Ünite', 'butce_kalemi': 'FASON'})
    assert r.json()['kod'] == 'HIDROLIK_UNITE_2'
    assert istemci.post('/api/unsurlar', headers=yonetim, json={'ad': 'x', 'butce_kalemi': 'FASON'}).status_code == 403
    r = istemci.post('/api/unsurlar', headers=h('K050'), json={'ad': 'Eksik'})
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == 'butce_kalemi'


# ---------------------------------------------------------------- katalog

KALEM = {'kod': 'PLC-S7', 'ad': 'PLC S7-1500 seti', 'unsur': 'PLC', 'birim_fiyat': '4500.00', 'para_birimi': 'EUR',
         'fiyat_tarihi': '2026-10-01', 'fiyat_kaynagi': 'Tedarikçi teklifi', 'tipik_temin_hafta': 6}


def test_katalog(istemci, h):
    r = istemci.put('/api/ayarlar/katalog', headers=h('K050'), json=[KALEM])
    assert r.status_code == 200, r.text
    kalemler = {k['kod']: k for k in r.json()['kalemler']}
    assert kalemler['PLC-S7']['birim_fiyat'] == '4500.00' and kalemler['PLC-S7']['butce_kalemi'] == 'MALZEME'
    assert kalemler['ROB-6E-20']['tipik_temin_hafta'] == 10
    # aynı kod ikinci kez eklenmez
    r = istemci.put('/api/ayarlar/katalog', headers=h('K050'), json=[dict(KALEM, ad='başka')])
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == 'kod'
    # fiyat ve para birimi birlikte
    r = istemci.put('/api/ayarlar/katalog', headers=h('K050'), json=[dict(KALEM, kod='Y', para_birimi=None)])
    assert r.status_code == 422
    # güncelleme ve pasifleştirme; arama yalnızca aktifleri getirir
    kimlik = kalemler['PLC-S7']['kimlik']
    istemci.put('/api/ayarlar/katalog', headers=h('K050'), json=[dict(KALEM, kimlik=kimlik, aktif=False)])
    assert [k['kod'] for k in istemci.get('/api/katalog?q=plc', headers=h('K050')).json()['kalemler']] == []
    assert [k['kod'] for k in istemci.get('/api/katalog?q=ROBOT 6', headers=h('K050')).json()['kalemler']] == ['ROB-6E-20']


def test_katalog_float_degil_metin(istemci, h):
    r = istemci.get('/api/ayarlar/katalog', headers=h('K050'))
    assert '"birim_fiyat":"28000.00"' in r.text.replace(' ', '')


# ---------------------------------------------------------------- makine türleri, başlangıç tablosu, saat ücretleri

def test_makine_turu_ve_baslangic_tablosu(istemci, h):
    r = istemci.put('/api/ayarlar/makine-turleri', headers=h('K050'),
                    json=[{'kod': 'PRES', 'ad': 'Pres hattı', 'tipik_toplam_hafta': 30}])
    assert {m['kod'] for m in r.json()['makine_turleri']} == {'ROBOTIK_HUCRE', 'OZEL_MAKINE', 'PRES'}
    tablo = istemci.get('/api/ayarlar/baslangic-tablosu', headers=h('K050')).json()['satirlar']
    assert len(tablo) == 3
    tablo.append({'makine_turu': 'PRES', 'birim': 'IMALAT', 'tipik_saat': '300.0', 'tipik_sure_hafta': 9})
    r = istemci.put('/api/ayarlar/baslangic-tablosu', headers=h('K050'), json=tablo)
    assert r.status_code == 200 and len(r.json()['satirlar']) == 4
    r = istemci.get('/api/ayarlar/baslangic-tablosu?makine_turu=PRES', headers=h('K050'))
    assert r.json()['satirlar'] == [{'makine_turu': 'PRES', 'birim': 'IMALAT', 'tipik_saat': '300.0', 'tipik_sure_hafta': 9}]


@pytest.mark.parametrize('satir, alan', [
    ({'makine_turu': 'PRES', 'birim': 'IMALAT', 'tipik_saat': '1'}, 'makine_turu'),
    ({'makine_turu': 'ROBOTIK_HUCRE', 'birim': 'YOK_BOYLE', 'tipik_saat': '1'}, 'birim')])
def test_baslangic_tablosu_dogrulama(istemci, h, satir, alan):
    r = istemci.put('/api/ayarlar/baslangic-tablosu', headers=h('K050'), json=[satir])
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == alan


def test_saat_ucretleri(istemci, h):
    r = istemci.put('/api/ayarlar/saat-ucretleri', headers=h('K001'),
                    json=[{'birim': 'MEK_TASARIM', 'ucret': '1800.00', 'para_birimi': 'TRY'},
                          {'birim': 'SATIS', 'ucret': '50', 'para_birimi': 'EUR'}])
    assert r.status_code == 200, r.text
    u = {x['birim']: x for x in r.json()['ucretler']}
    assert set(u) == {'MEK_TASARIM', 'SATIS'} and u['MEK_TASARIM']['ucret'] == '1800.00'
    assert u['MEK_TASARIM']['guncelleyen'] == 'K001'
    r = istemci.put('/api/ayarlar/saat-ucretleri', headers=h('K001'),
                    json=[{'birim': 'YOK', 'ucret': '1', 'para_birimi': 'TRY'}])
    assert r.status_code == 422
    r = istemci.put('/api/ayarlar/saat-ucretleri', headers=h('K001'),
                    json=[{'birim': 'IMALAT', 'ucret': '1', 'para_birimi': 'GBP'}])
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == 'para_birimi'


def test_takvim_sablonu_yalniz_birim_ve_aktiflik(istemci, h):
    satirlar = istemci.get('/api/ayarlar/takvim-sablonu', headers=h('K050')).json()['satirlar']
    assert [s['kod'] for s in satirlar][:2] == ['ACILIS', 'MEK_TASARIM'] and satirlar[0]['bas_orani'] == '0.000'
    r = istemci.put('/api/ayarlar/takvim-sablonu', headers=h('K050'),
                    json=[{'kod': 'TEST_FAT', 'birim': 'IMALAT', 'aktif': False}])
    s = {x['kod']: x for x in r.json()['satirlar']}
    assert (s['TEST_FAT']['birim'], s['TEST_FAT']['aktif'], s['TEST_FAT']['bit_orani']) == ('IMALAT', False, '0.850')
    r = istemci.put('/api/ayarlar/takvim-sablonu', headers=h('K050'), json=[{'kod': 'YENI_ETAP', 'aktif': True}])
    assert r.status_code == 422


# ---------------------------------------------------------------- genel

def test_genel_ayarlar(istemci, h, yonetim):
    g = istemci.get('/api/ayarlar/genel', headers=h('K050')).json()
    assert (g['varsayilan_para_birimi'], g['varsayilan_gecerlilik_gun'], g['cevap_uyari_gun']) == ('EUR', 30, 3)
    g['firma']['unvan'] = 'Sibernetik Makine A.Ş.'
    g['para_birimleri'] = [{'kod': 'USD', 'aktif': False}]
    r = istemci.put('/api/ayarlar/genel', headers=yonetim, json=g)
    assert r.status_code == 200, r.text
    assert r.json()['firma']['unvan'] == 'Sibernetik Makine A.Ş.'
    assert {p['kod']: p['aktif'] for p in r.json()['para_birimleri']}['USD'] is False
    # yönetim birimlerini yalnızca yetkili değiştirir
    g = r.json()
    g['yonetim_birimleri'] = ['YONETIM']
    del g['para_birimleri']
    assert istemci.put('/api/ayarlar/genel', headers=h('K050'), json=g).status_code == 403
    assert istemci.put('/api/ayarlar/genel', headers=h('K001'), json=g).status_code == 200
    assert istemci.get('/api/ayarlar/genel', headers=yonetim).status_code == 403     # artık yönetim birimi değil
    # varsayılan para birimi aktif olmalı
    g['varsayilan_para_birimi'] = 'USD'
    r = istemci.put('/api/ayarlar/genel', headers=h('K001'), json=g)
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == 'varsayilan_para_birimi'


# ---------------------------------------------------------------- geçmiş proje formu

GECMIS = {'proje_kodu': '2501', 'ad': 'Eski robot hücresi', 'makine_turu': 'ROBOTIK_HUCRE',
          'kapanis_tarihi': '2025-12-01', 'saatler': [{'birim': 'MEK_TASARIM', 'gercek_saat': '140.0'},
                                                      {'birim': 'IMALAT', 'gercek_saat': '95.5'}]}


def test_gecmis_proje_formu(istemci, h):
    r = istemci.post('/api/gecmis-projeler', headers=h('K050'), json=GECMIS)
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p['giren'], {s['birim']: s['gercek_saat'] for s in p['saatler']}) == (
        'K050', {'MEK_TASARIM': '140.0', 'IMALAT': '95.5'})
    assert p['giris_ani'].startswith('2026-11-02T') and p['giris_ani'].endswith('+03:00')
    r = istemci.put(f'/api/gecmis-projeler/{p["kimlik"]}', headers=h('K050'),
                    json=dict(GECMIS, saatler=[{'birim': 'PLANLAMA', 'gercek_saat': '20'}]))
    assert [s['birim'] for s in r.json()['saatler']] == ['PLANLAMA']
    assert len(istemci.get('/api/gecmis-projeler', headers=h('K050')).json()['projeler']) == 1
    assert istemci.post('/api/gecmis-projeler', headers=h('K050'), json=GECMIS).status_code == 422     # aynı kod
    assert istemci.put('/api/gecmis-projeler/999', headers=h('K050'), json=dict(GECMIS, proje_kodu='X')).status_code == 404


@pytest.mark.parametrize('degisen', [{'makine_turu': 'YOK'}, {'saatler': [{'birim': 'YOK', 'gercek_saat': '1'}]},
                                     {'saatler': [{'birim': 'IMALAT', 'gercek_saat': '1'}] * 2}])
def test_gecmis_proje_dogrulama(istemci, h, degisen):
    assert istemci.post('/api/gecmis-projeler', headers=h('K050'), json=dict(GECMIS, **degisen)).status_code == 422


def test_ayarlar_erisimi_olmayan(istemci, h):
    assert istemci.post('/api/gecmis-projeler', headers=h('K041'), json=GECMIS).status_code == 403
    assert istemci.put('/api/ayarlar/makine-turleri', headers=h('K041'), json=[]).status_code == 403


# ---------------------------------------------------------------- müşteriler

MUSTERI = {'ad': 'Autoliv', 'adres': 'Bursa', 'strateji_notu': 'İyi fiyat ver',
           'kisiler': [{'ad': 'Ayşe Demir', 'unvan': 'Satın alma', 'eposta': 'ayse@example.com'}]}


def test_musteri_ac_ve_listele(istemci, h, yonetim):
    r = istemci.post('/api/musteriler', headers=h('K050'), json=MUSTERI)
    assert r.status_code == 201, r.text
    m = r.json()
    assert (m['ad'], m['ulke'], m['olusturan'], m['strateji_notu']) == ('Autoliv', 'TR', 'K050', 'İyi fiyat ver')
    assert [k['ad'] for k in m['kisiler']] == ['Ayşe Demir']
    istemci.post('/api/musteriler', headers=h('K050'), json={'ad': 'Bosch Rexroth', 'kisa_ad': 'Bosch'})
    assert [x['ad'] for x in istemci.get('/api/musteriler?q=AUTOL', headers=yonetim).json()['musteriler']] == ['Autoliv']
    assert [x['ad'] for x in istemci.get('/api/musteriler?q=bosch', headers=h('K050')).json()['musteriler']] == [
        'Bosch Rexroth']
    assert istemci.post('/api/musteriler', headers=yonetim, json={'ad': 'Z'}).status_code == 403
    assert istemci.get('/api/musteriler', headers=h('K041')).status_code == 403


def test_ayni_adli_musteri_uyarisi(istemci, h):
    istemci.post('/api/musteriler', headers=h('K050'), json=MUSTERI)
    r = istemci.post('/api/musteriler', headers=h('K050'), json={'ad': 'AUTOLİV.'})
    assert r.status_code == 409 and r.json()['kod'] == 'AYNI_AD' and r.json()['mesaj'] == 'Bu adla bir müşteri var.'
    assert r.json()['benzerler'][0]['ad'] == 'Autoliv'
    assert istemci.post('/api/musteriler', headers=h('K050'), json={'ad': 'AUTOLİV.', 'yine_de': True}).status_code == 201


def test_musteri_guncelle_kisi_silinmez_pasiflesir(istemci, h):
    m = istemci.post('/api/musteriler', headers=h('K050'), json=MUSTERI).json()
    ayse = m['kisiler'][0]
    r = istemci.put(f'/api/musteriler/{m["kimlik"]}', headers=h('K050'),
                    json=dict(MUSTERI, kisa_ad='AL', kisiler=[{'ad': 'Mehmet Kaya', 'unvan': 'Proje'}]))
    assert r.status_code == 200, r.text
    kisiler = {k['ad']: k['aktif'] for k in r.json()['kisiler']}
    assert kisiler == {'Ayşe Demir': False, 'Mehmet Kaya': True}
    r = istemci.put(f'/api/musteriler/{m["kimlik"]}', headers=h('K050'),
                    json=dict(MUSTERI, aktif=False, kisiler=[dict(ayse, aktif=True)]))
    assert r.json()['aktif'] is False and {k['ad']: k['aktif'] for k in r.json()['kisiler']}['Ayşe Demir'] is True
    assert istemci.get('/api/musteriler?aktif=true', headers=h('K050')).json()['musteriler'] == []
    assert istemci.get('/api/musteriler/999', headers=h('K050')).status_code == 404
