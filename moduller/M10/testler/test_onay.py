"""Adım 8: onay, gönderim, müşterinin cevabı, işlem geçmişi (SPEC › 8.10–8.12, 8.15, 14.4)."""
import hashlib

import psycopg
import pytest

from m10 import vt
from ornek import d5_formu, d5_surumu, d5_talebi, gecir, gonderilmis, kaydet, yeni_surum


def test_onay_dongusu(istemci, h):
    talep, s = d5_surumu(istemci, h)
    v = gecir(istemci, h, s, 'onaya-gonder', 'K050')
    assert (v['durum'], v['onaya_gonderen']) == ('ONAY_BEKLIYOR', 'K050')
    assert v['izinler']['duzenleme'] is None                                    # satış onay beklerken düzenleyemez
    r = istemci.post(f'/api/surumler/{s}/onayla', headers=h('K050'), json={})
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')
    v = gecir(istemci, h, s, 'onayla', 'K001')
    assert (v['durum'], v['onaylayan'], v['hazirlayan_onaylayan_ayni']) == ('ONAYLANDI', 'K001', False)
    pdf = istemci.get(f'/api/surumler/{s}/pdf', headers=h('K050')).content
    assert hashlib.sha256(pdf).hexdigest() == v['pdf_parmak_izi']
    assert [k['karar'] for k in v['onay_kayitlari']] == ['ONAYA_GONDERILDI', 'ONAYLANDI']
    v = gecir(istemci, h, s, 'gonderildi', 'K050', gonderim_sekli='ELDEN', **{'not': 'toplantıda'})
    assert (v['durum'], v['gonderen'], v['gonderim_sekli'], v['gonderim_notu']) == ('GONDERILDI', 'K050', 'ELDEN',
                                                                                     'toplantıda')
    assert v['izinler']['yeni_surum'] is True
    assert istemci.get(f'/api/surumler/{s}/pdf', headers=h('K050')).content == pdf
    t = istemci.get(f'/api/talepler/{talep}', headers=h('K050')).json()
    assert t['durum'] == 'TEKLIF_VERILDI'
    islemler = [(g['islem'], g['ayrinti'].get('yeni')) for g in
                istemci.get(f'/api/talepler/{talep}/gecmis', headers=h('K050')).json()['kayitlar']]
    assert islemler[-4:] == [('DURUM_DEGISTI', 'ONAY_BEKLIYOR'), ('DURUM_DEGISTI', 'ONAYLANDI'),
                             ('DURUM_DEGISTI', 'GONDERILDI'), ('DURUM_DEGISTI', 'TEKLIF_VERILDI')]


def test_donmus_ozet(istemci, h):
    talep, s = gonderilmis(istemci, h)
    with vt.islem() as b:
        oz = b.execute('SELECT donmus_ozet FROM teklif_surumleri WHERE kimlik = %s', (s,)).fetchone()['donmus_ozet']
    assert oz['toplamlar'] == {'maliyet': '43500.00', 'marj_yuzde': '22.32', 'kalemler': {
        'MALZEME': '32500.00', 'ISCILIK': '10000.00', 'FASON': '1000.00', 'GENEL_GIDER': '0.00'}}
    assert (oz['takvim_teslim_hafta'], oz['en_erken_teslim_hafta']) == (25, 27)
    assert 'strateji_notu' not in oz['musteri'] and oz['musteri']['kisiler'][0]['ad'] == 'Ayşe Demir'
    assert oz['kapsam']['haric'] == ['Saha elektrik altyapısı'] and oz['dosyalar'][0]['tur'] == 'SARTNAME'
    # talep düzeyindeki bilgi sonradan değişse de özet onaydaki haliyle kalır
    t = istemci.get(f'/api/talepler/{talep}', headers=h('K050')).json()
    r = istemci.put(f'/api/talepler/{talep}', headers=h('K050'), json={
        'musteri': t['musteri']['kimlik'], 'kaynak': 'YENI_IS', 'tur': t['tur'], 'konu': t['konu'],
        'surum': t['surum'], 'kapsam': {'dahil': ['Yalnız tasarım'], 'haric': []}})
    assert r.status_code == 200
    with vt.islem() as b:
        oz2 = b.execute('SELECT donmus_ozet FROM teklif_surumleri WHERE kimlik = %s', (s,)).fetchone()['donmus_ozet']
    assert oz2 == oz


def test_onaya_gonder_dogrulamasi(istemci, h):
    talep = d5_talebi(istemci, h)
    s = yeni_surum(istemci, h, talep)['kimlik']
    r = istemci.post(f'/api/surumler/{s}/onaya-gonder', headers=h('K050'), json={})
    assert (r.status_code, r.json()['kod']) == (422, 'DOGRULAMA')
    assert {x['alan'] for x in r.json()['hatalar']} >= {'kalemler', 'fiyat', 'takvim', 'teslim_suresi_hafta'}
    form = d5_formu(istemci, h, s, teslim_suresi_hafta=26)
    kaydet(istemci, h, s, form)
    r = istemci.post(f'/api/surumler/{s}/onaya-gonder', headers=h('K050'), json={})
    assert [x['alan'] for x in r.json()['hatalar']] == ['teslim_suresi_hafta']
    assert istemci.get(f'/api/surumler/{s}', headers=h('K050')).json()['durum'] == 'TASLAK'


def test_onaysiz_teklif_gonderilemez(istemci, h):
    _, s = d5_surumu(istemci, h)
    for kisi in ('K050', 'K001'):
        r = istemci.post(f'/api/surumler/{s}/gonderildi', headers=h(kisi), json={'gonderim_sekli': 'E_POSTA'})
        assert (r.status_code, r.json()['kod']) == (409, 'KAPI')
        assert r.json()['mesaj'] == 'Onaylanmamış teklif müşteriye gönderilemez.'
    gecir(istemci, h, s, 'onaya-gonder', 'K050')
    r = istemci.post(f'/api/surumler/{s}/gonderildi', headers=h('K001'), json={'gonderim_sekli': 'E_POSTA'})
    assert (r.status_code, r.json()['kod']) == (409, 'KAPI')


def test_geri_gonder_ve_ayni_surum_duzeltilir(istemci, h):
    talep, s = d5_surumu(istemci, h)
    gecir(istemci, h, s, 'onaya-gonder', 'K050')
    gecir(istemci, h, s, 'geri-gonder', 'K001', 422, gerekce='')
    gecir(istemci, h, s, 'geri-gonder', 'K050', 403, gerekce='x')
    v = gecir(istemci, h, s, 'geri-gonder', 'K001', gerekce='Robot fiyatını güncelle')
    assert v['durum'] == 'TASLAK' and v['onay_kayitlari'][-1]['gerekce'] == 'Robot fiyatını güncelle'
    kaydet(istemci, h, s, d5_formu(istemci, h, s, fiyat='57000.00'))
    assert gecir(istemci, h, s, 'onaya-gonder', 'K050')['no'] == 1


def test_kendim_duzelt(istemci, h):
    talep, s = d5_surumu(istemci, h)
    gecir(istemci, h, s, 'onaya-gonder', 'K050')
    form = d5_formu(istemci, h, s)
    surum = istemci.get(f'/api/surumler/{s}', headers=h('K050')).json()['surum']
    r = istemci.put(f'/api/surumler/{s}', headers=h('K050'), json=dict(form, surum=surum))
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')
    assert istemci.get(f'/api/surumler/{s}', headers=h('K001')).json()['izinler']['duzenleme'] == 'ONAYCI'
    kaydet(istemci, h, s, dict(form, fiyat='58000.00'), 'K001')
    v = kaydet(istemci, h, s, dict(form, fiyat='58500.00'), 'K001')
    assert [k['karar'] for k in v['onay_kayitlari']] == ['ONAYA_GONDERILDI', 'ONAYCI_DUZELTTI']
    duzeltmeler = istemci.get(f'/api/talepler/{talep}/gecmis?onayci=true', headers=h('K050')).json()['kayitlar']
    assert len(duzeltmeler) == 2 and all(d['onayci_duzeltmesi'] and d['kim'] == 'K001' for d in duzeltmeler)
    assert {'alan': 'fiyat', 'eski': '56000.00', 'yeni': '58000.00'} in duzeltmeler[0]['ayrinti']['degisiklikler']
    v = gecir(istemci, h, s, 'onayla', 'K001')
    assert v['fiyat'] == '58500.00' and v['durum'] == 'ONAYLANDI'


def test_duzenlemeye_ac(istemci, h):
    _, s = d5_surumu(istemci, h)
    gecir(istemci, h, s, 'onaya-gonder', 'K050')
    gecir(istemci, h, s, 'onayla', 'K001')
    gecir(istemci, h, s, 'duzenlemeye-ac', 'K050', 422, gerekce=' ')
    v = gecir(istemci, h, s, 'duzenlemeye-ac', 'K050', gerekce='Müşteri teslim yerini değiştirdi')
    assert (v['durum'], v['onaylayan'], v['onay_ani'], v['pdf_parmak_izi']) == ('TASLAK', None, None, None)
    with vt.islem() as b:
        r = b.execute('SELECT pdf, donmus_ozet FROM teklif_surumleri WHERE kimlik = %s', (s,)).fetchone()
    assert r == {'pdf': None, 'donmus_ozet': None}
    assert v['onay_kayitlari'][-1]['karar'] == 'DUZENLEMEYE_ACILDI'
    gecir(istemci, h, s, 'duzenlemeye-ac', 'K001', 409, gerekce='x')            # artık TASLAK


def test_hazirlayan_ve_onaylayan_ayni_kisi(istemci, h):
    talep, s = d5_surumu(istemci, h, kisi='K001')
    gecir(istemci, h, s, 'onaya-gonder', 'K001')
    v = gecir(istemci, h, s, 'onayla', 'K001')
    assert v['hazirlayan_onaylayan_ayni'] is True


def test_gonderilmis_surum_degismez(istemci, h):
    _, s = gonderilmis(istemci, h)
    v = istemci.get(f'/api/surumler/{s}', headers=h('K001')).json()
    r = istemci.put(f'/api/surumler/{s}', headers=h('K001'), json=dict(d5_formu(istemci, h, s), surum=v['surum']))
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')                  # çocuk satırlarına yazma
    for e, govde in (('onaya-gonder', {}), ('onayla', {}), ('geri-gonder', {'gerekce': 'x'}),
                     ('duzenlemeye-ac', {'gerekce': 'x'})):
        assert istemci.post(f'/api/surumler/{s}/{e}', headers=h('K001'), json=govde).status_code == 409
    with pytest.raises(psycopg.errors.RaiseException), vt.islem() as b:          # veritabanının tetikleyicisi
        b.execute("UPDATE teklif_surumleri SET fiyat = 1 WHERE kimlik = %s", (s,))


def test_ayni_talepten_yeni_surum_revize(istemci, h):
    talep, s1 = gonderilmis(istemci, h)
    istemci.put('/api/ayarlar/saat-ucretleri', headers=h('K050'), json=[
        {'birim': 'MEK_TASARIM', 'ucret': '2000.00', 'para_birimi': 'TRY'},
        {'birim': 'IMALAT', 'ucret': '1408.00', 'para_birimi': 'TRY'}])
    v2 = yeni_surum(istemci, h, talep, kaynak='SURUM', kaynak_surum=s1, revize=True)
    assert (v2['no'], v2['etiket'], v2['para_birimi'], v2['fiyat_girisi'], v2['fiyat']) == (
        2, 'T-2026-0001/V2', 'EUR', 'FIYAT', '56000.00')
    assert v2['kurlar'][0]['kur_try'] == '35.200000' and len(v2['kalemler']) == 3
    assert {i['birim']: i['saat_ucreti'] for i in v2['iscilik']}['MEK_TASARIM'] == '2000.00'
    assert v2['hesap']['maliyet'] == '44318.18'                                 # 120 × 2.000 TL = 6.818,18 €
    assert v2['teslim_suresi_hafta'] == 28
    kayitlar = istemci.get(f'/api/talepler/{talep}/gecmis', headers=h('K050')).json()['kayitlar']
    assert [(k['islem'], k['ayrinti'].get('not')) for k in kayitlar[-2:]] == [
        ('SURUM_ACILDI', None), ('NOT', 'Müşteri revize istedi')]
    assert istemci.get(f'/api/talepler/{talep}', headers=h('K050')).json()['durum'] == 'TEKLIF_VERILDI'


def test_musterinin_cevabi(istemci, h):
    talep, s = gonderilmis(istemci, h)
    yol = f'/api/talepler/{talep}/sonuc'
    t = istemci.post(yol, headers=h('K050'), json={'sonuc': 'BEKLEMEDE'}).json()
    assert t['durum'] == 'BEKLEMEDE'
    assert istemci.post(yol, headers=h('K050'), json={'sonuc': 'BEKLENIYOR'}).json()['durum'] == 'TEKLIF_VERILDI'
    r = istemci.post(yol, headers=h('K050'), json={'sonuc': 'KAYBEDILDI'})
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == 'kayip_nedeni'
    t = istemci.post(yol, headers=h('K050'), json={'sonuc': 'KAYBEDILDI', 'kayip_nedeni': 'FIYAT',
                                                   'aciklama': 'Rakip %10 ucuz'}).json()
    assert (t['durum'], t['kayip_nedeni'], t['sonucu_yazan']) == ('KAYBEDILDI', 'FIYAT', 'K050')
    r = istemci.post(f'/api/talepler/{talep}/geri-ac', headers=h('K050'), json={'gerekce': 'Müşteri döndü'})
    assert r.status_code == 403
    t = istemci.post(f'/api/talepler/{talep}/geri-ac', headers=h('K001'), json={'gerekce': 'Müşteri döndü'}).json()
    assert (t['durum'], t['kayip_nedeni'], t['sonuc_ani']) == ('TEKLIF_VERILDI', None, None)
    t = istemci.post(yol, headers=h('K050'), json={'sonuc': 'KAZANILDI', 'kazanan_surum': s}).json()
    assert (t['durum'], t['kazanan_surum']) == ('KAZANILDI', s)
    # KAZANILDI geri alınmaz
    r = istemci.post(f'/api/talepler/{talep}/geri-ac', headers=h('K001'), json={'gerekce': 'x'})
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')
    assert istemci.post(yol, headers=h('K050'), json={'sonuc': 'KAYBEDILDI', 'kayip_nedeni': 'FIYAT'}).status_code == 409
    r = istemci.post(f'/api/talepler/{talep}/surumler', headers=h('K050'), json={'kaynak': 'BOS'})
    assert r.status_code == 409                                                 # kazanılmış talepte yeni sürüm yok


def test_kazanan_gonderilmis_surum_olmali(istemci, h):
    talep, s1 = gonderilmis(istemci, h)
    v2 = yeni_surum(istemci, h, talep, kaynak='SURUM', kaynak_surum=s1)['kimlik']
    r = istemci.post(f'/api/talepler/{talep}/sonuc', headers=h('K050'), json={'sonuc': 'KAZANILDI', 'kazanan_surum': v2})
    assert r.status_code == 422
    r = istemci.post(f'/api/talepler/{talep}/sonuc', headers=h('K050'), json={'sonuc': 'KAZANILDI'})
    assert r.status_code == 422


def test_kapatilan_talep_geri_acilir(istemci, h):
    talep = d5_talebi(istemci, h)
    istemci.post(f'/api/talepler/{talep}/kapat', headers=h('K050'), json={'gerekce': 'Kapasite yok'})
    t = istemci.post(f'/api/talepler/{talep}/geri-ac', headers=h('K001'), json={'gerekce': 'Kapasite açıldı'}).json()
    assert (t['durum'], t['kapatma_gerekcesi']) == ('ACIK', None)


# ---------------------------------------------------------------- veritabanının kısıtları (14.4)

def _sql_hatasi(sql, *p):
    with pytest.raises(psycopg.errors.IntegrityError), vt.islem() as b:
        b.execute(sql, p)


def test_kisit_tek_acik_surum(istemci, h):
    talep, s = d5_surumu(istemci, h)
    _sql_hatasi("INSERT INTO teklif_surumleri (talep, no, para_birimi, hazirlayan, olusturma_ani) "
                "VALUES (%s, 2, 'EUR', 'K050', now())", talep)


def test_kisit_kazanildida_kazanan_surum(istemci, h):
    talep = d5_talebi(istemci, h)
    _sql_hatasi("UPDATE talepler SET durum = 'KAZANILDI' WHERE kimlik = %s", talep)


def test_kisit_fiyat_ve_para_birimi_birlikte(istemci, h):
    _, s = d5_surumu(istemci, h)
    _sql_hatasi("UPDATE maliyet_kalemleri SET para_birimi = NULL WHERE surum = %s", s)
    _sql_hatasi("INSERT INTO surum_kurlari (surum, para_birimi, kur_try, kur_tarihi) VALUES (%s, 'TRY', 1, now())", s)


def test_kisit_onaylida_pdf_ve_ozet(istemci, h):
    _, s = d5_surumu(istemci, h)
    _sql_hatasi("UPDATE teklif_surumleri SET durum = 'ONAYLANDI', onaylayan = 'K001', onay_ani = now() "
                "WHERE kimlik = %s", s)
