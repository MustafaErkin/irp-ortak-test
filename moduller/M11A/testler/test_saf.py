"""Saf fonksiyonların birim testleri (SPEC › 14.2)."""
from datetime import date
from decimal import Decimal

import pytest

from m11a.alan import butce, devir, eksik, kod, olcum, tarih
from testler.ornek import kazanan_surum

SIPARIS = date(2026, 11, 2)


# ---- kod
def test_proje_kodu_ilk_siparis():
    assert kod.proje_kodu('{YY}{AA}{SIRA3}', SIPARIS, 1) == '2611001'
    assert kod.proje_kodu('P{YYYY}-{SIRA3}', SIPARIS, 12) == 'P2026-012'


def test_sira_donemi_kapsami():
    assert kod.sira_donemi(SIPARIS, 'YIL') == '2026'
    assert kod.sira_donemi(SIPARIS, 'AY') == '2026-11'
    with pytest.raises(ValueError):
        kod.sira_donemi(SIPARIS, 'HAFTA')


def test_kalip_degiskenleri():
    assert kod.bilinmeyen_degiskenler('{YY}{AA}{SIRA3}') == []
    assert kod.bilinmeyen_degiskenler('{YY}{GUN}{SIRA3}') == ['GUN']


@pytest.mark.parametrize('k, gecerli', [('2614', True), ('2611001', True), ('AB-12', True), ('a', False),
                                        ('26 14', False), ('2611/1', False), ('X' * 21, False), ('', False)])
def test_elle_kod_deseni(k, gecerli):
    assert kod.elle_kod_gecerli(k) is gecerli


def test_siparis_adi_po_lu_ve_po_suz():
    desen = '{YYYY}-{YILLIK_SIRA3}-{PROJE_KODU}___{MUSTERI}-{PROJE_ADI}_{PO}'
    ad = kod.siparis_adi(desen, SIPARIS, 1, '2611001', 'Autoliv', '710 Projesi Burç Çakma Ekipmanı', 'PO1246789')
    assert ad == '2026-001-2611001___Autoliv-710 Projesi Burç Çakma Ekipmanı_PO1246789'
    assert kod.siparis_adi(desen, SIPARIS, 1, '2611001', 'Autoliv', 'X', None).endswith('_PO-BEKLENIYOR')
    assert kod.siparis_adi(desen, SIPARIS, 1, '2611001', 'Autoliv', 'X', '  ').endswith('_PO-BEKLENIYOR')


# ---- tarih
PLAN = [('ACILIS', '2026-11-02', '2026-11-08'), ('MEK_TASARIM', '2026-11-09', '2026-12-13'),
        ('OTO_TASARIM', '2026-11-09', '2026-12-27'), ('SATIN_ALMA', '2026-11-30', '2027-01-24'),
        ('IMALAT', '2026-12-21', '2027-02-07'), ('MEK_MONTAJ', '2027-02-01', '2027-03-07'),
        ('ELK_YAZILIM', '2027-02-08', '2027-03-21'), ('TEST_FAT', '2027-03-15', '2027-04-04'),
        ('SEVK_KURULUM', '2027-04-05', '2027-04-25'), ('KESIN_KABUL', '2027-04-26', '2027-05-02')]


def test_tarihler_ek_d5():
    o = tarih.oneriler(SIPARIS, kazanan_surum())
    assert o['teslim_tarihi'] == date(2027, 5, 16)
    assert o['kayma_hafta'] == 3
    assert o['kesin_kabul_tarihi'] == date(2027, 5, 23)
    assert [(s['etap_kodu'], s['baslangic'].isoformat(), s['bitis'].isoformat()) for s in o['baslangic_plani']] == PLAN


def test_kesin_kabul_yokken():
    k = kazanan_surum()
    k['takvim'] = [s for s in k['takvim'] if s['etap_kodu'] != 'KESIN_KABUL']
    assert tarih.oneriler(SIPARIS, k)['kesin_kabul_tarihi'] is None


def test_kayma_negatif_olmaz():
    assert tarih.kayma(20, 25) == 0


# ---- bütçe
def test_butce_donusumu():
    k = kazanan_surum()
    assert butce.baslangic_butcesi(k) == {'MALZEME': Decimal('32500.00'), 'ISCILIK': Decimal('10000.00'),
                                          'FASON': Decimal('1000.00'), 'GENEL_GIDER': Decimal('0.00')}
    assert {u['birim']: (u['ucret'], u['para_birimi']) for u in butce.saat_ucretleri(k)} == {
        'MEK_TASARIM': (Decimal('1760.00'), 'TRY'), 'IMALAT': (Decimal('1408.00'), 'TRY')}


def test_kur_ve_yuvarlama():
    kurlar = kazanan_surum()['kurlar']
    assert butce.cevir(Decimal('35200.00'), 'TRY', 'EUR', kurlar) == Decimal('1000.00')
    assert butce.cevir(Decimal('211200'), 'TRY', 'EUR', kurlar) == Decimal('6000.00')
    assert butce.cevir(Decimal('1'), 'USD', 'EUR', kurlar) is None
    assert butce.metin(Decimal('56000')) == '56000.00'
    assert butce.para('0.005') == Decimal('0.01')


# ---- ölçüm
EUR = kazanan_surum()['kurlar']
UCRET = {'MEK_TASARIM': {'ucret': Decimal('1760.00'), 'para_birimi': 'TRY'}}
ETAPLAR = [{'kimlik': 'E1', 'birim': 'MEK_TASARIM'}]


def _parcalar(hazir, toplam):
    return [{'tur': 'PARCA', 'asama': 'MONTAJA_HAZIR' if i < hazir else 'SIPARIS_VERILMELI'} for i in range(toplam)]


def _olc(iscilik='10000.00', saat=12.8, parcalar=None, etaplar=ETAPLAR, ucret=UCRET, toplam=None, esik=15,
         pd_etap='E1', ilerleme=25):
    pd = {'yuzde':ilerleme,'tamamlanan':5,'hedef':20,'harcanan_emek': saat if toplam is None else toplam, 'etaplar': {pd_etap: {'harcanan_emek': saat}}}
    return olcum.olcum({'para_birimi': 'EUR', 'guncel': {'ISCILIK': Decimal(iscilik)}}, etaplar, pd, ucret, EUR,
                       _parcalar(1, 4) if parcalar is None else parcalar, esik)


def test_olcum_ornek():
    o = _olc()
    assert o['gerceklesen']['ISCILIK'] == Decimal('640.00')
    assert (o['dolum_yuzde'], o['ilerleme_yuzde'], o['sapma_puan'], o['renk']) == (6.4, 25.0, -18.6, 'YESIL')
    assert o['kapsam'] == ['ISCILIK'] and o['bilinmeyen_saat'] == Decimal('0.0')
    assert o['ilerleme'] == {'kaynak':'CEKIRDEK','tamamlanan':5,'hedef':20}
    assert o['gerceklesen']['MALZEME'] is None and o['kaynaklar']['GENEL_GIDER'] == 'FORMUL_YOK'


def test_olcum_kirmizi():
    o = _olc(iscilik='2000.00', parcalar=_parcalar(0, 4),ilerleme=0)
    assert (o['dolum_yuzde'], o['ilerleme_yuzde'], o['sapma_puan'], o['renk']) == (32.0, 0.0, 32.0, 'KIRMIZI')


def test_cekirdek_ilerlemesi_bilinmiyorsa_gri():
    o = _olc(parcalar=[{'tur': 'BELGE', 'asama': 'TAMAM'}],ilerleme=None)
    assert (o['ilerleme_yuzde'], o['sapma_puan'], o['renk']) == (None, None, 'GRI')


def test_parca_asamasi_cekirdek_ilerlemesini_ezmez():
    o = _olc(parcalar=[{'tur': 'PARCA', 'asama': 'MONTAJDA'}, {'tur': 'PARCA', 'asama': 'GELDI'}])
    assert o['ilerleme_yuzde'] == 25.0


def test_ucreti_bilinmeyen_birim():
    o = _olc(etaplar=[{'kimlik': 'E1', 'birim': 'ELEKTRIK'}])
    assert o['gerceklesen']['ISCILIK'] is None and o['bilinmeyen_saat'] == Decimal('12.8')
    assert o['dolum_yuzde'] is None


def test_kuru_bilinmeyen_birim():
    o = _olc(ucret={'MEK_TASARIM': {'ucret': Decimal('40'), 'para_birimi': 'USD'}})
    assert o['bilinmeyen_saat'] == Decimal('12.8') and o['gerceklesen']['ISCILIK'] is None


def test_etapsiz_saat():
    o = _olc(toplam=16.3)
    assert o['bilinmeyen_saat'] == Decimal('3.5')
    assert o['iscilik_satirlari'][-1] == {'etap': None, 'birim': None, 'saat': Decimal('3.5'), 'ucret': None,
                                          'para_birimi': None, 'tutar': None}
    assert o['dolum_yuzde'] is None


def test_iscilik_butcesi_sifirsa_kapsam_bos():
    o = _olc(iscilik='0.00')
    assert (o['kapsam'], o['dolum_yuzde'], o['renk']) == ([], None, 'GRI')


def test_esik_siniri():
    # dolum 15,0 ve ilerleme 0,0 → sapma tam 15,0: YESIL
    o = _olc(iscilik='4266.67', parcalar=_parcalar(0, 4),ilerleme=0)
    assert (o['dolum_yuzde'], o['sapma_puan'], o['renk']) == (15.0, 15.0, 'YESIL')
    o = _olc(iscilik='4266.67', parcalar=_parcalar(0, 4), esik=14.9,ilerleme=0)
    assert o['renk'] == 'KIRMIZI'


def test_yedek_ucret_birlesimi():
    u = olcum.ucret_birlestir([{'birim': 'A', 'ucret': 1, 'para_birimi': 'TRY'}],
                              [{'birim': 'A', 'ucret': 9, 'para_birimi': 'TRY'},
                               {'birim': 'B', 'ucret': 2, 'para_birimi': 'TRY'}])
    assert u['A']['ucret'] == 1 and u['B']['ucret'] == 2


# ---- eksik
DOLU = {'faturalama_bicimi': 'KADEMELI', 'teslim_sekli': 'DAP', 'ihracat': False, 'tesvik': 'YOK',
        'teminat_gerekli': 'YOK'}


def test_her_alanin_kosulu():
    assert eksik.eksik_alanlar('PO1', 5, DOLU, 1, 0) == []
    assert eksik.eksik_alanlar(None, None, {}, 0, 0) == list(eksik.ALANLAR)
    assert eksik.eksik_alanlar(' ', 5, DOLU, 1, 0) == ['PO']
    assert eksik.eksik_alanlar('PO1', 5, DOLU | {'teslim_sekli': ''}, 1, 0) == ['TESLIM_SEKLI']
    assert eksik.eksik_alanlar('PO1', 5, DOLU | {'ihracat': True}, 1, 0) == []
    assert eksik.eksik_alanlar('PO1', 5, DOLU | {'tesvik': 'VAR'}, 1, 0) == ['TESVIK']
    assert eksik.eksik_alanlar('PO1', 5, DOLU | {'tesvik': 'VAR', 'tesvik_belge_no': 'T-1'}, 1, 0) == []
    assert eksik.eksik_alanlar('PO1', 5, DOLU | {'teminat_gerekli': 'VAR'}, 1, 0) == ['TEMINAT']
    assert eksik.eksik_alanlar('PO1', 5, DOLU | {'teminat_gerekli': 'VAR'}, 1, 1) == []
    assert eksik.eksik_alanlar('PO1', 5, DOLU, 0, 0) == ['ODEME_TAKVIMI']
    assert eksik.eksik_alanlar('PO1', None, DOLU, 1, 0) == ['SOZLESME']


def test_dolan_ve_bosalan_alan():
    satirlar = [{'kimlik': 1, 'alan': 'PO', 'durum': 'EKSIK'}, {'kimlik': 2, 'alan': 'TESVIK', 'durum': 'ALINDI'},
                {'kimlik': 3, 'alan': 'IHRACAT', 'durum': 'ISTENDI'}, {'kimlik': 4, 'alan': None, 'durum': 'EKSIK'}]
    acilacak, degisen = eksik.esitle(satirlar, ['TESVIK', 'IHRACAT', 'TEMINAT'])
    assert acilacak == ['TEMINAT']
    assert sorted(degisen) == [(1, 'ALINDI'), (2, 'EKSIK')]
    assert eksik.acik_sayisi(satirlar) == 3


def test_eksik_satir_gecisleri():
    oto, elle = {'alan': 'PO', 'durum': 'EKSIK'}, {'alan': None, 'durum': 'EKSIK'}
    assert eksik.gecis_hatasi(oto, 'ISTENDI', None) == 'Kimden istendiği seçilmeli.'
    assert eksik.gecis_hatasi(oto, 'ISTENDI', 'MUSTERI') is None
    assert eksik.gecis_hatasi(oto | {'durum': 'ISTENDI'}, 'ALINDI', None)
    assert eksik.gecis_hatasi(elle | {'durum': 'ISTENDI'}, 'ALINDI', None) is None
    assert eksik.gecis_hatasi(elle | {'durum': 'ALINDI'}, 'ISTENDI', 'SATIS')


# ---- devir
def test_devir_gecisleri():
    assert devir.durum('DEVREDILDI', 3) == 'DEVREDILDI'
    assert devir.aldim('DEVREDILDI', 3) == 'EKSIK_VAR'
    assert devir.aldim('DEVREDILDI', 0) == 'MUHASEBE_GORDU'
    assert devir.durum('EKSIK_VAR', 0) == 'MUHASEBE_GORDU'
    assert devir.durum('MUHASEBE_GORDU', 1) == 'EKSIK_VAR'
    assert devir.durum('TAMAM', 2) == 'TAMAM' and devir.aldim('TAMAM', 2) == 'TAMAM'


def test_tamamlama_kosullari():
    assert devir.tamamlama_engeli('EKSIK_VAR', 1, 'C1', 'P1') == 'Açık eksik var.'
    assert devir.tamamlama_engeli('MUHASEBE_GORDU', 0, 'C1', ' ') == 'VEGA kodları boş.'
    assert devir.tamamlama_engeli('MUHASEBE_GORDU', 0, None, 'P1') == 'VEGA kodları boş.'
    assert devir.tamamlama_engeli('MUHASEBE_GORDU', 0, 'C1', 'P1') is None
    assert devir.tamamlama_engeli('TAMAM', 0, 'C1', 'P1')
