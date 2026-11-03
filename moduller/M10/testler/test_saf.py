"""Adım 3: saf fonksiyonların birim testleri (SPEC › 14.2). Sayılar Ek D.5'in örneğidir."""
from decimal import Decimal as D

import pytest

from m10.alan import arama, dogrulama, durum, hesap, oneri, takvim
from m10.alan.yetki import kisi_kur
from m10.hatalar import ModulHatasi

KURLAR = {'EUR': D('35.200000')}
KALEMLER = [
    {'sira': 1, 'unsur': 'ROBOT', 'butce_kalemi': 'MALZEME', 'aciklama': 'Robot, 6 eksen, 20 kg', 'adet': D('1.000'),
     'birim_fiyat': D('28000.00'), 'para_birimi': 'EUR', 'temin_hafta': 10},
    {'sira': 2, 'unsur': 'PLC', 'butce_kalemi': 'MALZEME', 'aciklama': 'PLC ve HMI seti', 'adet': D('1.000'),
     'birim_fiyat': D('4500.00'), 'para_birimi': 'EUR', 'temin_hafta': 6},
    {'sira': 3, 'unsur': 'ISIL_ISLEM', 'butce_kalemi': 'FASON', 'aciklama': 'Fikstür ısıl işlem', 'adet': D('1.000'),
     'birim_fiyat': D('35200.00'), 'para_birimi': 'TRY', 'temin_hafta': 2},
]
ISCILIK = [
    {'birim': 'MEK_TASARIM', 'saat': D('120.0'), 'saat_ucreti': D('1760.00'), 'para_birimi': 'TRY'},
    {'birim': 'IMALAT', 'saat': D('100.0'), 'saat_ucreti': D('1408.00'), 'para_birimi': 'TRY'},
]
# veritabani/002_varsayilanlar.sql'deki şablon
SABLON = [
    {'kod': k, 'ad': a, 'sira': s, 'paralel_grup': p, 'bas_orani': D(b), 'bit_orani': D(e), 'aktif': True}
    for k, a, s, p, b, e in [
        ('ACILIS', 'Proje açılışı ve planlama', 1, None, '0.000', '0.040'),
        ('MEK_TASARIM', 'Mekanik tasarım (3D/2D)', 2, 'TASARIM', '0.020', '0.220'),
        ('OTO_TASARIM', 'Otomasyon tasarımı (elektrik, PLC/HMI mimarisi)', 3, 'TASARIM', '0.040', '0.300'),
        ('SATIN_ALMA', 'Satın alma ve malzeme temini', 4, 'TEDARIK', '0.150', '0.450'),
        ('IMALAT', 'İmalat', 5, 'TEDARIK', '0.250', '0.550'),
        ('MEK_MONTAJ', 'Mekanik, hidrolik ve pnömatik montaj', 6, 'MONTAJ', '0.500', '0.700'),
        ('ELK_YAZILIM', 'Elektrik montajı ve yazılım', 7, 'MONTAJ', '0.550', '0.750'),
        ('TEST_FAT', 'Testler, ön deneme ve ön kabul (FAT)', 8, None, '0.720', '0.850'),
        ('SEVK_KURULUM', 'Sevkiyat, saha kurulumu ve devreye alma', 9, None, '0.850', '0.950'),
        ('KESIN_KABUL', 'Kesin kabul', 10, None, '0.950', '1.000')]]
D5_TAKVIM = [('ACILIS', 0, 1), ('MEK_TASARIM', 1, 5), ('OTO_TASARIM', 1, 7), ('SATIN_ALMA', 4, 8), ('IMALAT', 7, 7),
             ('MEK_MONTAJ', 13, 5), ('ELK_YAZILIM', 14, 6), ('TEST_FAT', 19, 3), ('SEVK_KURULUM', 22, 3),
             ('KESIN_KABUL', 25, 1)]


def d5(**k):
    return hesap.surum_hesabi('EUR', KURLAR, KALEMLER, ISCILIK, **k)


# ---------------------------------------------------------------- hesap

def test_satir_tutarlari_ve_ceviri():
    h = d5(fiyat_girisi='FIYAT', fiyat=D('56000'))
    assert [(k['tutar'], k['tutar_teklif']) for k in h['kalemler']] == [
        (D('28000.00'), D('28000.00')), (D('4500.00'), D('4500.00')), (D('35200.00'), D('1000.00'))]
    assert [(s['tutar'], s['tutar_teklif']) for s in h['iscilik']] == [
        (D('211200.00'), D('6000.00')), (D('140800.00'), D('4000.00'))]
    assert hesap.cevir(D('35200'), 'TRY', 'EUR', KURLAR) == D('1000.00')


def test_kirilim_ve_maliyet():
    h = d5()
    assert h['kirilim'] == {'MALZEME': D('32500.00'), 'ISCILIK': D('10000.00'), 'FASON': D('1000.00'),
                            'GENEL_GIDER': D('0.00')}
    assert str(h['kirilim']['GENEL_GIDER']) == '0.00'
    assert h['maliyet'] == D('43500.00')


def test_fiyat_girisinden_kar_ve_marj():
    h = d5(fiyat_girisi='FIYAT', fiyat=D('56000.00'))
    assert (h['fiyat'], h['kar_orani'], h['marj_yuzde']) == (D('56000.00'), D('28.74'), D('22.32'))
    assert h['fiyatin_yuzdesi_olsaydi'] is None


def test_kar_girisinden_fiyat_ve_fiyatin_yuzdesi():
    h = d5(fiyat_girisi='KAR', kar_orani=D('20'))
    assert (h['fiyat'], h['kar_orani']) == (D('52200.00'), D('20.00'))
    assert h['fiyatin_yuzdesi_olsaydi'] == D('54375.00')


def test_maliyet_degisince_girilen_sabit_kalir():
    az = [KALEMLER[0]]
    h = hesap.surum_hesabi('EUR', KURLAR, az, [], 'FIYAT', None, D('56000'))
    assert (h['fiyat'], h['kar_orani']) == (D('56000.00'), D('100.00'))
    h = hesap.surum_hesabi('EUR', KURLAR, az, [], 'KAR', D('20'), D('56000'))
    assert (h['fiyat'], h['kar_orani']) == (D('33600.00'), D('20.00'))


def test_eksik_fiyat_veri_eksik_sifir_sayilmaz():
    kalemler = [*KALEMLER, {'sira': 4, 'unsur': 'NAKLIYE', 'butce_kalemi': 'FASON', 'aciklama': 'Nakliye',
                            'adet': D('1'), 'birim_fiyat': None, 'para_birimi': None}]
    h = hesap.surum_hesabi('EUR', KURLAR, kalemler, ISCILIK, 'KAR', D('20'))
    assert h['kalemler'][3]['tutar_teklif'] == hesap.VERI_EKSIK and h['kalemler'][3]['eksik_nedeni'] == 'FIYAT'
    assert h['kirilim']['FASON'] == hesap.VERI_EKSIK
    assert h['kirilim']['MALZEME'] == D('32500.00')
    assert h['maliyet'] == hesap.VERI_EKSIK
    assert (h['fiyat'], h['kar_orani'], h['marj_yuzde']) == (None, D('20.00'), None)


def test_eksik_kur_veri_eksik():
    h = hesap.surum_hesabi('EUR', {}, KALEMLER, ISCILIK, 'FIYAT', None, D('56000'))
    assert [k['tutar_teklif'] for k in h['kalemler']] == [D('28000.00'), D('4500.00'), hesap.VERI_EKSIK]
    assert h['kalemler'][2]['eksik_nedeni'] == 'KUR'
    assert all(s['tutar_teklif'] == hesap.VERI_EKSIK for s in h['iscilik'])
    assert h['maliyet'] == hesap.VERI_EKSIK and h['kar_orani'] is None
    assert h['eksik_kurlar'] == ['EUR']


def test_ucretsiz_iscilik_veri_eksik():
    h = hesap.surum_hesabi('EUR', KURLAR, [], [{'birim': 'PLANLAMA', 'saat': D('10'), 'saat_ucreti': None,
                                                'para_birimi': None}])
    assert h['iscilik'][0]['eksik_nedeni'] == 'UCRET' and h['maliyet'] == hesap.VERI_EKSIK


def test_maliyet_sifirken_kar_hesaplanamaz():
    h = hesap.surum_hesabi('EUR', KURLAR, [], [], 'FIYAT', None, D('1000'))
    assert h['maliyet'] == D('0.00') and h['kar_orani'] is None


def test_yuvarlama_yarim_yukari():
    assert hesap.yuvarla(D('2.675')) == D('2.68')
    assert hesap.yuvarla(D('-0.005')) == D('-0.01')
    assert hesap.cevir(D('0.176'), 'TRY', 'EUR', KURLAR) == D('0.01')       # 0,005 € → 0,01 €
    # her satır ayrı yuvarlanır; toplam yuvarlanmış satırların toplamıdır
    satirlar = [{'butce_kalemi': 'MALZEME', 'adet': D('1'), 'birim_fiyat': D('0.176'), 'para_birimi': 'TRY'}] * 3
    h = hesap.surum_hesabi('EUR', KURLAR, satirlar, [])
    assert h['maliyet'] == D('0.03')                                        # 3 × 0,01; 0,528 ÷ 35,2 = 0,015 değil


# ---------------------------------------------------------------- takvim

def test_sablondan_on_satir_d5():
    satirlar = takvim.sablondan(SABLON, 26)
    assert [(s['etap_kodu'], s['baslangic_hafta'], s['sure_hafta']) for s in satirlar] == D5_TAKVIM
    imalat = next(s for s in satirlar if s['etap_kodu'] == 'IMALAT')
    assert imalat['baslangic_hafta'] == 7                                   # 0,25 × 26 = 6,5 → 7
    assert satirlar[1]['paralel_grup'] == 'TASARIM' and satirlar[1]['ad'] == 'Mekanik tasarım (3D/2D)'


def test_sablondan_pasif_satir_atlanir_sure_en_az_bir():
    sablon = [dict(s, aktif=s['kod'] != 'TEST_FAT') for s in SABLON]
    satirlar = takvim.sablondan(sablon, 2)
    assert 'TEST_FAT' not in [s['etap_kodu'] for s in satirlar]
    assert all(s['sure_hafta'] >= 1 for s in satirlar)


def test_takvim_teslimi_kayma_en_erken_d5():
    h = takvim.takvim_hesabi(takvim.sablondan(SABLON, 26), KALEMLER)
    assert (h['takvim_teslim_hafta'], h['kayma_hafta'], h['en_erken_teslim_hafta']) == (25, 2, 27)
    assert h['kayma_aciklamasi'] == ('En uzun temin süreli kalem (Robot, 6 eksen, 20 kg, 10 hafta) satın almanın '
                                     'bitişini 2 hafta geçiyor; en erken teslim 2 hafta kayar.')


def test_satin_alma_yokken_kayma():
    satirlar = [{'etap_kodu': None, 'ad': 'Tasarım', 'baslangic_hafta': 0, 'sure_hafta': 4},
                {'etap_kodu': 'IMALAT', 'ad': 'İmalat', 'baslangic_hafta': 4, 'sure_hafta': 4}]
    h = takvim.takvim_hesabi(satirlar, KALEMLER)
    assert (h['takvim_teslim_hafta'], h['kayma_hafta'], h['en_erken_teslim_hafta']) == (8, 2, 10)
    h = takvim.takvim_hesabi(satirlar, [dict(KALEMLER[0], temin_hafta=5)])
    assert (h['kayma_hafta'], h['en_erken_teslim_hafta'], h['kayma_aciklamasi']) == (0, 8, None)


def test_temin_suresi_olmayan_kalem():
    satirlar = takvim.sablondan(SABLON, 26)
    h = takvim.takvim_hesabi(satirlar, [dict(k, temin_hafta=None) for k in KALEMLER])
    assert (h['kayma_hafta'], h['en_erken_teslim_hafta'], h['en_uzun_temin_hafta']) == (0, 25, None)
    h = takvim.takvim_hesabi(satirlar, [dict(KALEMLER[0], temin_hafta=None), KALEMLER[1]])
    assert (h['en_uzun_temin_hafta'], h['kayma_hafta']) == (6, 0)


def test_kesin_kabul_takvim_tesliminde_sayilmaz():
    h = takvim.takvim_hesabi([{'etap_kodu': 'KESIN_KABUL', 'baslangic_hafta': 30, 'sure_hafta': 2},
                              {'etap_kodu': 'IMALAT', 'baslangic_hafta': 0, 'sure_hafta': 5}], [])
    assert h['takvim_teslim_hafta'] == 5


# ---------------------------------------------------------------- öneri

TABLO = {('ROBOTIK_HUCRE', 'MEK_TASARIM'): D('120'), ('ROBOTIK_HUCRE', 'IMALAT'): D('100'),
         ('ROBOTIK_HUCRE', 'PLANLAMA'): D('40'), ('OZEL_MAKINE', 'IMALAT'): D('60')}
GECMIS = [{'makine_turu': 'ROBOTIK_HUCRE', 'birim': 'MEK_TASARIM', 'gercek_saat': D(x)} for x in ('130', '140', '150')] + \
         [{'makine_turu': 'ROBOTIK_HUCRE', 'birim': 'SATIS', 'gercek_saat': D(x)} for x in ('100', '101', '101')] + \
         [{'makine_turu': 'OZEL_MAKINE', 'birim': 'MEK_TASARIM', 'gercek_saat': D('999')}]


def test_oneri_tablo_ve_gecmis():
    assert oneri.iscilik_onerisi('ROBOTIK_HUCRE', 'MEK_TASARIM', TABLO, GECMIS) == {
        'tablo': D('120'), 'gecmis_ortalama': D('140.0'), 'gecmis_sayi': 3}


def test_oneri_biri_yokken():
    assert oneri.iscilik_onerisi('ROBOTIK_HUCRE', 'IMALAT', TABLO, GECMIS) == {
        'tablo': D('100'), 'gecmis_ortalama': None, 'gecmis_sayi': 0}
    assert oneri.iscilik_onerisi('ROBOTIK_HUCRE', 'SATIS', TABLO, GECMIS) == {
        'tablo': None, 'gecmis_ortalama': D('100.7'), 'gecmis_sayi': 3}             # 100,67 → 100,7
    assert oneri.iscilik_onerisi('YOK', 'YOK', TABLO, GECMIS) == {'tablo': None, 'gecmis_ortalama': None, 'gecmis_sayi': 0}


def test_onerileri_doldur_dolu_saate_dokunmaz():
    satirlar = [{'birim': 'MEK_TASARIM', 'saat': D('90')}, {'birim': 'SATIS', 'saat': None}]
    sonuc = oneri.onerileri_doldur(satirlar, 'ROBOTIK_HUCRE', TABLO, GECMIS)
    assert {s['birim']: s['saat'] for s in sonuc} == {'MEK_TASARIM': D('90'), 'SATIS': D('100.7'), 'IMALAT': D('100'),
                                                       'PLANLAMA': D('40')}
    assert [s['birim'] for s in sonuc if s.get('yeni')] == ['IMALAT', 'PLANLAMA']


# ---------------------------------------------------------------- durum

SATIS = kisi_kur({'kimlik': 'K050', 'birim': 'SATIS', 'roller': ['YONETICI', 'SATIS']}, ['YONETIM'])
CEO = kisi_kur({'kimlik': 'K001', 'birim': 'YONETIM', 'roller': ['YETKILI']}, ['YONETIM'])
YONETIM = kisi_kur({'kimlik': 'K099', 'birim': 'YONETIM', 'roller': ['YONETICI']}, ['YONETIM'])

SURUM_TABLOSU = {
    ('TASLAK', 'ONAYA_GONDER'): 'ONAY_BEKLIYOR',
    ('ONAY_BEKLIYOR', 'ONAYLA'): 'ONAYLANDI',
    ('ONAY_BEKLIYOR', 'GERI_GONDER'): 'TASLAK',
    ('ONAYLANDI', 'DUZENLEMEYE_AC'): 'TASLAK',
    ('ONAYLANDI', 'GONDERILDI'): 'GONDERILDI',
}


@pytest.mark.parametrize('d', durum.SURUM_DURUMLARI)
@pytest.mark.parametrize('e', list(durum.SURUM_GECISLERI))
def test_surum_gecis_tablosu(d, e):
    beklenen = SURUM_TABLOSU.get((d, e))
    if beklenen:
        assert durum.surum_gecisi(d, e, CEO, hazirlayan='K050') == beklenen
    else:
        with pytest.raises(ModulHatasi) as h:
            durum.surum_gecisi(d, e, CEO, hazirlayan='K050')
        assert (h.value.http, h.value.kod) == ((409, 'KAPI') if e == 'GONDERILDI' else (409, 'DURUM'))


def test_surum_gecisinde_kim():
    assert durum.surum_gecisi('TASLAK', 'ONAYA_GONDER', SATIS) == 'ONAY_BEKLIYOR'
    for e, d in [('ONAYLA', 'ONAY_BEKLIYOR'), ('GERI_GONDER', 'ONAY_BEKLIYOR')]:
        with pytest.raises(ModulHatasi) as h:
            durum.surum_gecisi(d, e, SATIS)
        assert h.value.http == 403
    assert durum.surum_gecisi('ONAYLANDI', 'DUZENLEMEYE_AC', SATIS, hazirlayan='K050') == 'TASLAK'
    with pytest.raises(ModulHatasi) as h:
        durum.surum_gecisi('ONAYLANDI', 'DUZENLEMEYE_AC', SATIS, hazirlayan='K001')
    assert h.value.http == 403
    with pytest.raises(ModulHatasi) as h:
        durum.surum_gecisi('TASLAK', 'ONAYA_GONDER', YONETIM)                 # yönetim görür, düzenlemez
    assert h.value.http == 403


def test_onaysiz_gonderim_kapi_hicbir_rol_gecemez():
    for k in (SATIS, CEO):
        for d in ('TASLAK', 'ONAY_BEKLIYOR'):
            with pytest.raises(ModulHatasi) as h:
                durum.surum_gecisi(d, 'GONDERILDI', k)
            assert (h.value.kod, h.value.mesaj) == ('KAPI', 'Onaylanmamış teklif müşteriye gönderilemez.')


def test_surum_duzenlenebilir():
    assert durum.surum_duzenlenebilir('TASLAK', SATIS) == 'HAZIRLAYAN'
    assert durum.surum_duzenlenebilir('ONAY_BEKLIYOR', CEO) == 'ONAYCI'
    for d, k in [('ONAY_BEKLIYOR', SATIS), ('ONAYLANDI', CEO), ('GONDERILDI', CEO), ('TASLAK', YONETIM)]:
        with pytest.raises(ModulHatasi):
            durum.surum_duzenlenebilir(d, k)


TALEP_TABLOSU = {
    ('ACIK', 'GONDERIM'): 'TEKLIF_VERILDI', ('BEKLEMEDE', 'GONDERIM'): 'TEKLIF_VERILDI',
    ('TEKLIF_VERILDI', 'GONDERIM'): 'TEKLIF_VERILDI',
    ('ACIK', 'KAPAT'): 'KAPATILDI', ('BEKLEMEDE', 'KAPAT'): 'KAPATILDI',
    ('TEKLIF_VERILDI', 'KAZANILDI'): 'KAZANILDI', ('BEKLEMEDE', 'KAZANILDI'): 'KAZANILDI',
    ('TEKLIF_VERILDI', 'KAYBEDILDI'): 'KAYBEDILDI', ('BEKLEMEDE', 'KAYBEDILDI'): 'KAYBEDILDI',
    ('TEKLIF_VERILDI', 'BEKLEMEDE'): 'BEKLEMEDE',
    ('BEKLEMEDE', 'BEKLENIYOR'): 'TEKLIF_VERILDI',
    ('KAYBEDILDI', 'GERI_AC'): 'ACIK', ('KAPATILDI', 'GERI_AC'): 'ACIK',
}


@pytest.mark.parametrize('d', durum.TALEP_DURUMLARI)
@pytest.mark.parametrize('e', list(durum.TALEP_GECISLERI))
def test_talep_gecis_tablosu(d, e):
    beklenen = TALEP_TABLOSU.get((d, e))
    if beklenen:
        assert durum.talep_gecisi(d, e, CEO) == beklenen
    else:
        with pytest.raises(ModulHatasi) as h:
            durum.talep_gecisi(d, e, CEO)
        assert (h.value.http, h.value.kod) == (409, 'DURUM')


def test_kazanildi_geri_alinmaz_geri_ac_gonderilmis_surume_bakar():
    with pytest.raises(ModulHatasi):
        durum.talep_gecisi('KAZANILDI', 'GERI_AC', CEO)
    assert durum.talep_gecisi('KAYBEDILDI', 'GERI_AC', CEO, gonderilmis_var=True) == 'TEKLIF_VERILDI'
    with pytest.raises(ModulHatasi) as h:
        durum.talep_gecisi('KAYBEDILDI', 'GERI_AC', SATIS)
    assert h.value.http == 403


def test_yeni_surum_acilabilir():
    durum.yeni_surum_acilabilir('ACIK', False, SATIS)
    for d, acik in [('ACIK', True), ('KAZANILDI', False), ('KAPATILDI', False), ('KAYBEDILDI', False)]:
        with pytest.raises(ModulHatasi) as h:
            durum.yeni_surum_acilabilir(d, acik, SATIS)
        assert h.value.kod == 'DURUM'


# ---------------------------------------------------------------- doğrulama

def _gecerli():
    satirlar = takvim.sablondan(SABLON, 26)
    surum = {'teslim_suresi_hafta': 28, 'gecerlilik_gun': 30, 'takvim': satirlar}
    h = d5(fiyat_girisi='FIYAT', fiyat=D('56000'))
    t = takvim.takvim_hesabi(satirlar, KALEMLER)
    talep = {'kapsam': [{'tur': 'DAHIL', 'metin': 'FAT'}], 'gereksinimler': [{'belirsiz': False, 'cevap': None}]}
    return surum, h, t, talep


def _alanlar(hatalar):
    return [x['alan'] for x in hatalar]


def test_dogrulama_gecerli_surum():
    assert dogrulama.onaya_gonderim(*_gecerli()) == ([], [])


def test_dogrulama_kalem_ya_da_iscilik():
    surum, _, t, talep = _gecerli()
    h = hesap.surum_hesabi('EUR', KURLAR, [], [], 'FIYAT', None, D('100'))
    assert 'kalemler' in _alanlar(dogrulama.onaya_gonderim(surum, h, t, talep)[0])


def test_dogrulama_birim_fiyat():
    surum, _, t, talep = _gecerli()
    kalemler = [*KALEMLER, {'sira': 4, 'butce_kalemi': 'FASON', 'aciklama': 'Nakliye', 'adet': D('1'),
                            'birim_fiyat': None, 'para_birimi': None}]
    h = hesap.surum_hesabi('EUR', KURLAR, kalemler, ISCILIK, 'FIYAT', None, D('56000'))
    hatalar = dogrulama.onaya_gonderim(surum, h, t, talep)[0]
    assert [(x['alan'], x['sira']) for x in hatalar if x['alan'] == 'kalemler.birim_fiyat'] == [('kalemler.birim_fiyat', 4)]
    assert 'fiyat' in _alanlar(hatalar)                                     # maliyet eksik → kâr hesaplanamaz


def test_dogrulama_saat_ucreti():
    surum, _, t, talep = _gecerli()
    isc = [*ISCILIK, {'birim': 'PLANLAMA', 'saat': D('5'), 'saat_ucreti': None, 'para_birimi': None}]
    h = hesap.surum_hesabi('EUR', KURLAR, KALEMLER, isc, 'FIYAT', None, D('56000'))
    hatalar = dogrulama.onaya_gonderim(surum, h, t, talep)[0]
    assert ('iscilik.saat_ucreti', 3) in [(x['alan'], x['sira']) for x in hatalar]


def test_dogrulama_kur():
    surum, _, t, talep = _gecerli()
    h = hesap.surum_hesabi('EUR', {}, KALEMLER, ISCILIK, 'FIYAT', None, D('56000'))
    hatalar = dogrulama.onaya_gonderim(surum, h, t, talep)[0]
    assert [x['mesaj'] for x in hatalar if x['alan'] == 'kurlar'] == ['EUR kuru girilmeli.']


@pytest.mark.parametrize('fiyat', [None, D('0')])
def test_dogrulama_fiyat(fiyat):
    surum, _, t, talep = _gecerli()
    h = d5(fiyat_girisi='FIYAT', fiyat=fiyat)
    assert _alanlar(dogrulama.onaya_gonderim(surum, h, t, talep)[0]) == ['fiyat']


def test_dogrulama_takvim_bos():
    surum, h, t, talep = _gecerli()
    surum['takvim'] = []
    assert _alanlar(dogrulama.onaya_gonderim(surum, h, takvim.takvim_hesabi([], KALEMLER), talep)[0]) == ['takvim']


@pytest.mark.parametrize('teslim, hata', [(26, True), (27, False), (None, True)])
def test_dogrulama_teslim_en_erkenden_kisa_olamaz(teslim, hata):
    surum, h, t, talep = _gecerli()
    surum['teslim_suresi_hafta'] = teslim
    assert ('teslim_suresi_hafta' in _alanlar(dogrulama.onaya_gonderim(surum, h, t, talep)[0])) is hata


def test_dogrulama_gecerlilik():
    surum, h, t, talep = _gecerli()
    surum['gecerlilik_gun'] = None
    assert _alanlar(dogrulama.onaya_gonderim(surum, h, t, talep)[0]) == ['gecerlilik_gun']


def test_dogrulama_uyarilari_durdurmaz():
    surum, h, t, _ = _gecerli()
    talep = {'kapsam': [], 'gereksinimler': [{'belirsiz': True, 'cevap': None}, {'belirsiz': True, 'cevap': 'Evet'},
                                              {'belirsiz': True, 'cevap': '  '}]}
    hatalar, uyarilar = dogrulama.onaya_gonderim(surum, h, t, talep)
    assert hatalar == []
    assert [(u['alan'], u['mesaj']) for u in uyarilar] == [('kapsam', 'Kapsam boş.'),
                                                           ('gereksinimler', '2 belirsiz ve cevapsız gereksinim var.')]


# ---------------------------------------------------------------- arama ve kod üretme

def test_normal():
    assert arama.normal('ÇAKMA') == arama.normal('cakma') == arama.normal('Çakma') == 'cakma'
    assert arama.normal('IŞIK') == 'isik'
    assert arama.normal('İSTANBUL ışık') == 'istanbul isik'
    assert arama.normal('  Autoliv — Burç  Çakma!! ') == 'autoliv burc cakma'
    assert arama.normal('Ölçü/Şekil, Ğ') == 'olcu sekil g'
    assert arama.normal(None) == ''


def test_ve_aramasi():
    assert arama.eslesir('çakma autoliv', 'Autoliv — Burç Çakma')
    assert arama.eslesir('CAKMA', 'Autoliv — Burç Çakma')
    assert not arama.eslesir('çakma bosch', 'Autoliv — Burç Çakma')
    assert arama.eslesir('', 'herhangi')


def test_kod_uretme():
    assert arama.kod_uret('Hidrolik ünite', []) == 'HIDROLIK_UNITE'
    assert arama.kod_uret('Hidrolik ünite', ['HIDROLIK_UNITE']) == 'HIDROLIK_UNITE_2'
    assert arama.kod_uret('Hidrolik ünite', ['HIDROLIK_UNITE', 'HIDROLIK_UNITE_2']) == 'HIDROLIK_UNITE_3'
    assert arama.kod_uret('Işık perdesi (güvenlik)', []) == 'ISIK_PERDESI_GUVENLIK'
    assert arama.kod_uret('3D baskı', []) == 'U_3D_BASKI'
    k = arama.kod_uret('a' * 60, ['A' * 40])
    assert k == 'A' * 38 + '_2' and len(k) == 40
