"""Adım 6: sürüm (SPEC › 8.3–8.8): yeni, kopyalama, kaydetme, dört bölüm, eşzamanlılık."""
import pytest

from m10 import vt
from ornek import D5_HESAP, d5_formu, d5_talebi, kaydet, musteri_ac, yeni_surum


@pytest.fixture
def talep(istemci, h):
    return d5_talebi(istemci, h)


@pytest.fixture
def surum(istemci, h, talep):
    return yeni_surum(istemci, h, talep)['kimlik']


def test_bos_surum_varsayilanlardan(istemci, h, talep):
    s = yeni_surum(istemci, h, talep)
    assert (s['no'], s['durum'], s['etiket'], s['para_birimi'], s['gecerlilik_gun'], s['hazirlayan']) == (
        1, 'TASLAK', 'T-2026-0001/V1', 'EUR', 30, 'K050')
    assert s['odeme_kosullari'] == '%40 sipariş ile, %50 sevkten önce, %10 kesin kabulde.'
    assert s['kurlar'] == [{'para_birimi': 'EUR', 'kur_try': '35.200000', 'kur_tarihi': '2026-10-20'}]
    assert s['izinler']['duzenleme'] == 'HAZIRLAYAN' and s['izinler']['onaya_gonder'] is True
    assert s['izinler']['onayla'] is False and s['varsayilan_toplam_hafta'] == 26
    # talepte gönderilmemiş sürüm varken yenisi açılmaz
    r = istemci.post(f'/api/talepler/{talep}/surumler', headers=h('K050'), json={'kaynak': 'BOS'})
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')
    assert [g['islem'] for g in istemci.get(f'/api/talepler/{talep}/gecmis', headers=h('K050')).json()['kayitlar']][-1] \
        == 'SURUM_ACILDI'


def test_d5_formu_kaydedilir_ve_hesaplanir(istemci, h, surum):
    s = kaydet(istemci, h, surum, d5_formu(istemci, h, surum))
    hs = s['hesap']
    assert {k: hs[k] for k in D5_HESAP} == D5_HESAP
    assert hs['kayma_aciklamasi'].startswith('En uzun temin süreli kalem (Robot, 6 eksen, 20 kg, 10 hafta)')
    assert (s['surum'], s['kar_orani'], s['fiyat'], s['teslim_suresi_hafta']) == (2, '28.74', '56000.00', 28)
    assert [(k['sira'], k['tutar'], k['tutar_teklif'], k['butce_kalemi']) for k in s['kalemler']] == [
        (1, '28000.00', '28000.00', 'MALZEME'), (2, '4500.00', '4500.00', 'MALZEME'), (3, '35200.00', '1000.00', 'FASON')]
    assert s['kalemler'][0]['katalog_kodu'] == 'ROB-6E-20' and s['kalemler'][0]['adet'] == '1.000'
    assert s['kalemler'][0]['ortalama_temin_hafta'] is None and s['kalemler'][0]['katalog_temin_hafta'] == 10
    assert [(i['birim'], i['saat'], i['saat_ucreti'], i['tutar_teklif']) for i in s['iscilik']] == [
        ('MEK_TASARIM', '120.0', '1760.00', '6000.00'), ('IMALAT', '100.0', '1408.00', '4000.00')]   # girildiği sıra
    assert [(t['etap_kodu'], t['baslangic_hafta'], t['sure_hafta']) for t in s['takvim']][3] == ('SATIN_ALMA', 4, 8)
    assert next(t for t in s['takvim'] if t['etap_kodu'] == 'MEK_TASARIM')['ipucu_sure_hafta'] == 5
    assert s['dogrulama']['hatalar'] == [] and s['dogrulama']['uyarilar'] == []
    # kurlar son_kurlar ayarına yazılır
    with vt.islem() as b:
        assert b.execute("SELECT deger FROM ayarlar WHERE anahtar = 'son_kurlar'").fetchone()['deger'] == {
            'EUR': {'kur_try': '35.200000', 'kur_tarihi': '2026-10-20'}}


def test_kar_girisi_fiyati_hesaplar_teslim_varsayilani(istemci, h, surum):
    form = d5_formu(istemci, h, surum, fiyat_girisi='KAR', kar_orani='20', fiyat=None, teslim_suresi_hafta=None)
    s = kaydet(istemci, h, surum, form)
    assert (s['hesap']['fiyat'], s['hesap']['fiyatin_yuzdesi_olsaydi'], s['fiyat']) == ('52200.00', '54375.00', '52200.00')
    assert s['teslim_suresi_hafta'] == 27                                       # en erken teslim


def test_eszamanli_duzenleme_409(istemci, h, surum):
    form = d5_formu(istemci, h, surum)
    eski = istemci.get(f'/api/surumler/{surum}', headers=h('K050')).json()['surum']
    assert istemci.put(f'/api/surumler/{surum}', headers=h('K050'), json=dict(form, surum=eski)).status_code == 200
    r = istemci.put(f'/api/surumler/{surum}', headers=h('K001'), json=dict(form, surum=eski, fiyat='1'))
    assert (r.status_code, r.json()['kod']) == (409, 'DEGISTI')
    assert r.json()['guncel']['fiyat'] == '56000.00' and r.json()['guncel']['surum'] == eski + 1


def test_iscilik_ucreti_satirda_donar(istemci, h, surum):
    form = d5_formu(istemci, h, surum)
    kaydet(istemci, h, surum, form)
    istemci.put('/api/ayarlar/saat-ucretleri', headers=h('K050'), json=[
        {'birim': 'MEK_TASARIM', 'ucret': '2000.00', 'para_birimi': 'TRY'},
        {'birim': 'IMALAT', 'ucret': '1500.00', 'para_birimi': 'TRY'},
        {'birim': 'PLANLAMA', 'ucret': '1600.00', 'para_birimi': 'TRY'}])
    form['iscilik'] += [{'birim': 'PLANLAMA', 'saat': '10'}, {'birim': 'SATIS', 'saat': '5'}]
    s = kaydet(istemci, h, surum, form)
    u = {i['birim']: (i['saat_ucreti'], i['tutar_teklif']) for i in s['iscilik']}
    assert u['MEK_TASARIM'] == ('1760.00', '6000.00')                           # eski satır eski ücretle
    assert u['PLANLAMA'][0] == '1600.00'                                        # yeni satır o anki ücretle
    assert u['SATIS'] == (None, 'VERI_EKSIK')                                   # ücret tanımlı değil
    assert s['hesap']['maliyet'] == 'VERI_EKSIK'
    assert [x['alan'] for x in s['dogrulama']['hatalar']] == ['iscilik.saat_ucreti', 'fiyat']


def test_eksik_fiyat_kaydedilir_veri_eksik(istemci, h, surum):
    form = d5_formu(istemci, h, surum)
    form['kalemler'].append({'unsur': 'NAKLIYE', 'aciklama': 'Nakliye', 'adet': '1'})
    s = kaydet(istemci, h, surum, form)
    assert s['kalemler'][3]['tutar_teklif'] == 'VERI_EKSIK' and s['hesap']['kirilim']['FASON'] == 'VERI_EKSIK'
    assert s['fiyat'] == '56000.00' and s['kar_orani'] is None


def test_katalog_da_kaydet(istemci, h, surum):
    form = d5_formu(istemci, h, surum)
    form['kalemler'][1]['katalog_kaydet'] = {'kod': 'PLC-SET'}
    s = kaydet(istemci, h, surum, form)
    assert s['kalemler'][1]['katalog_kodu'] == 'PLC-SET'
    kalem = istemci.get('/api/katalog?q=PLC-SET', headers=h('K050')).json()['kalemler'][0]
    assert (kalem['birim_fiyat'], kalem['tipik_temin_hafta'], kalem['unsur']) == ('4500.00', 6, 'PLC')
    form['kalemler'][2]['katalog_kaydet'] = {'kod': 'PLC-SET'}
    form['kalemler'][1].pop('katalog_kaydet')
    r = istemci.put(f'/api/surumler/{surum}', headers=h('K050'), json=dict(form, surum=s['surum']))
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == 'kalemler.katalog_kaydet'


@pytest.mark.parametrize('bozuk, alan', [
    (lambda f: f['kalemler'][0].update(unsur='YOK_BOYLE'), 'kalemler.unsur'),
    (lambda f: f['kalemler'][0].update(para_birimi=None), 'kalemler.birim_fiyat'),
    (lambda f: f['kalemler'][0].update(kaynak_dosyasi=99999), 'kalemler.kaynak_dosyasi'),
    (lambda f: f['iscilik'].append({'birim': 'YOK', 'saat': '1'}), 'iscilik.birim'),
    (lambda f: f['iscilik'].append({'birim': 'IMALAT', 'saat': '1'}), 'iscilik.birim'),
    (lambda f: f['takvim'].append(dict(f['takvim'][0])), 'takvim.etap_kodu'),
    (lambda f: f['kurlar'].append({'para_birimi': 'TRY', 'kur_try': '1', 'kur_tarihi': '2026-10-20'}), 'kurlar'),
    (lambda f: f.update(para_birimi='GBP'), 'para_birimi'),
])
def test_form_dogrulama(istemci, h, surum, bozuk, alan):
    form = d5_formu(istemci, h, surum)
    bozuk(form)
    s = istemci.get(f'/api/surumler/{surum}', headers=h('K050')).json()
    r = istemci.put(f'/api/surumler/{surum}', headers=h('K050'), json=dict(form, surum=s['surum']))
    assert r.status_code == 422, r.text
    assert alan in [x['alan'] for x in r.json()['hatalar']]


def test_surum_yetki(istemci, h, surum):
    with vt.islem() as b:
        b.execute("""UPDATE ayarlar SET deger = '["YONETIM", "PLANLAMA"]' WHERE anahtar = 'yonetim_birimleri'""")
    assert istemci.get(f'/api/surumler/{surum}', headers=h('K041')).status_code == 403
    s = istemci.get(f'/api/surumler/{surum}', headers=h('K004'))
    assert s.status_code == 200 and s.json()['izinler']['duzenleme'] is None     # yönetim görür, düzenlemez
    r = istemci.put(f'/api/surumler/{surum}', headers=h('K004'), json=dict(d5_formu(istemci, h, surum),
                                                                           surum=s.json()['surum']))
    assert r.status_code == 403
    assert istemci.get('/api/surumler/9999', headers=h('K050')).status_code == 404


def test_islem_gecmisi_alan_farklari(istemci, h, talep, surum):
    form = d5_formu(istemci, h, surum)
    kaydet(istemci, h, surum, form)
    form['kalemler'][1]['birim_fiyat'] = '4800.00'
    form['fiyat'] = '57000.00'
    kaydet(istemci, h, surum, form)
    kayit = istemci.get(f'/api/talepler/{talep}/gecmis', headers=h('K050')).json()['kayitlar'][-1]
    assert kayit['islem'] == 'SURUM_KAYDEDILDI' and kayit['surum_no'] == 1 and kayit['onayci_duzeltmesi'] is False
    farklar = {d['alan']: (d['eski'], d['yeni']) for d in kayit['ayrinti']['degisiklikler']}
    assert farklar['kalemler[2].birim_fiyat'] == ('4500.00', '4800.00')
    assert farklar['fiyat'] == ('56000.00', '57000.00')


def test_eski_talebin_surumunden_kopya(istemci, h, talep, surum):
    """"Benzer işi bulmak": kalemler, işçilik, takvim, metinler gelir; müşteri gelmez; gereksinim ve kapsam boşsa
    eskininkiler gelir; saat ücretleri o anki ayardan."""
    form = d5_formu(istemci, h, surum)
    dosya = istemci.get(f'/api/talepler/{talep}', headers=h('K050')).json()['dosyalar'][0]['kimlik']
    form['kalemler'][0]['kaynak_dosyasi'] = dosya
    kaydet(istemci, h, surum, form)
    istemci.put('/api/ayarlar/saat-ucretleri', headers=h('K050'), json=[
        {'birim': 'MEK_TASARIM', 'ucret': '2000.00', 'para_birimi': 'TRY'}])
    bosch = musteri_ac(istemci, h, ad='Bosch Rexroth')
    yeni_talep = istemci.post('/api/talepler', headers=h('K050'), json={
        'musteri': bosch, 'kaynak': 'YENI_IS', 'tur': 'SAHA_NOTU', 'konu': 'Benzer hücre'}).json()['kimlik']
    s = yeni_surum(istemci, h, yeni_talep, kaynak='SURUM', kaynak_surum=surum)
    assert (s['no'], s['kaynak_surum'], s['teknik_cozum']) == (1, surum, form['teknik_cozum'])
    assert [k['aciklama'] for k in s['kalemler']] == ['Robot, 6 eksen, 20 kg', 'PLC ve HMI seti', 'Fikstür ısıl işlem']
    assert s['kalemler'][0]['kaynak_dosyasi'] is None                          # öbür talebin dosyası gelmez
    assert len(s['takvim']) == 10 and s['fiyat'] is None and s['fiyat_girisi'] == 'KAR'
    assert {i['birim']: i['saat_ucreti'] for i in s['iscilik']} == {'MEK_TASARIM': '2000.00', 'IMALAT': None}
    t = istemci.get(f'/api/talepler/{yeni_talep}', headers=h('K050')).json()
    assert t['musteri']['ad'] == 'Bosch Rexroth'                               # müşteri gelmez
    assert [g['metin'] for g in t['gereksinimler']] == ['Çevrim süresi 45 sn altında']
    assert t['kapsam']['haric'] == ['Saha elektrik altyapısı']
    kayit = istemci.get(f'/api/talepler/{yeni_talep}/gecmis', headers=h('K050')).json()['kayitlar'][-1]
    assert kayit['ayrinti']['kaynak_etiket'] == 'T-2026-0001/V1' and kayit['ayrinti']['kapsam_kopyalandi'] is True


def test_oneriler_ve_sablondan(istemci, h, surum):
    istemci.post('/api/gecmis-projeler', headers=h('K050'), json={
        'proje_kodu': '2501', 'ad': 'Eski hücre', 'makine_turu': 'ROBOTIK_HUCRE',
        'saatler': [{'birim': 'MEK_TASARIM', 'gercek_saat': '140'}, {'birim': 'SATIS', 'gercek_saat': '12'}]})
    r = istemci.get(f'/api/surumler/{surum}/oneriler', headers=h('K050')).json()
    o = {x['birim']: x for x in r['oneriler']}
    assert (o['MEK_TASARIM']['tablo'], o['MEK_TASARIM']['gecmis_ortalama'], o['MEK_TASARIM']['gecmis_sayi']) == (
        '120.0', '140.0', 1)
    assert set(o) == {'MEK_TASARIM', 'IMALAT', 'PLANLAMA'}
    assert {i['birim']: (i['saat'], i['saat_ucreti']) for i in r['doldurulmus']} == {
        'IMALAT': ('100.0', '1408.00'), 'MEK_TASARIM': ('120.0', '1760.00'), 'PLANLAMA': ('40.0', '1500.00')}
    r = istemci.post(f'/api/surumler/{surum}/takvim/sablondan', headers=h('K050'), json={'toplam_hafta': 26}).json()
    assert [(s['etap_kodu'], s['baslangic_hafta'], s['sure_hafta']) for s in r['satirlar']][4] == ('IMALAT', 7, 7)
    assert r['hesap']['takvim_teslim_hafta'] == 25
