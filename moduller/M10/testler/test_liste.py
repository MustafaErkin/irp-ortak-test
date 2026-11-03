"""Adım 9: talepler listesi, arama, sayaç şeridi, onay bekleyenler (SPEC › 8.13, 8.10)."""
from datetime import date

from m10.alan.durum import cevap_isareti
from ornek import TALEP, d5_surumu, d5_talebi, gecir, gonderilmis, musteri_ac

BUGUN = date(2026, 11, 2)


def test_cevap_isareti():
    assert cevap_isareti('ACIK', False, date(2026, 11, 5), BUGUN, 3) == {
        'tur': 'YAKLASIYOR', 'metin': 'Cevap tarihi yaklaşıyor', 'kalan_gun': 3}
    assert cevap_isareti('ACIK', False, date(2026, 11, 6), BUGUN, 3) is None
    assert cevap_isareti('BEKLEMEDE', False, date(2026, 11, 1), BUGUN, 3)['tur'] == 'GECTI'
    assert cevap_isareti('ACIK', True, date(2026, 11, 1), BUGUN, 3) is None        # gönderilmiş sürüm var
    assert cevap_isareti('TEKLIF_VERILDI', False, date(2026, 11, 1), BUGUN, 3) is None
    assert cevap_isareti('ACIK', False, None, BUGUN, 3) is None


def _talep(istemci, h, musteri, **ek):
    r = istemci.post('/api/talepler', headers=h('K050'), json={**TALEP, 'musteri': musteri, **ek})
    assert r.status_code == 201, r.text
    return r.json()['kimlik']


def test_liste_sira_isaret_ve_son_surum(istemci, h):
    autoliv = musteri_ac(istemci, h)
    bosch = musteri_ac(istemci, h, ad='Bosch Rexroth', kisa_ad='Bosch')
    uzak = _talep(istemci, h, bosch, konu='Pres hattı', makine_turu='OZEL_MAKINE', cevap_tarihi='2026-12-20')
    yakin = _talep(istemci, h, autoliv, konu='Burç Çakma', cevap_tarihi='2026-11-04')
    gecmis = _talep(istemci, h, bosch, konu='Kaynak fikstürü', cevap_tarihi='2026-10-30')
    kapali = _talep(istemci, h, autoliv, konu='Eski iş', cevap_tarihi='2026-10-01')
    istemci.post(f'/api/talepler/{kapali}/kapat', headers=h('K050'), json={'gerekce': 'Kapasite yok'})
    _, s = d5_surumu(istemci, h, talep=yakin)

    t = istemci.get('/api/talepler', headers=h('K050')).json()['talepler']
    assert [x['kimlik'] for x in t] == [gecmis, yakin, uzak, kapali]               # açık önce, cevap tarihi yakın önce
    x = {r['kimlik']: r for r in t}
    assert x[gecmis]['isaret']['tur'] == 'GECTI' and x[yakin]['isaret']['tur'] == 'YAKLASIYOR'
    assert x[uzak]['isaret'] is None and x[kapali]['isaret'] is None
    assert (x[yakin]['son_surum'], x[yakin]['son_surum_no'], x[yakin]['son_surum_durumu'], x[yakin]['fiyat']) == (
        s, 1, 'TASLAK', '56000.00')
    assert x[uzak]['son_surum'] is None and x[uzak]['makine_turu_adi'] == 'Özel makine'


def test_arama_ve_suzgecler(istemci, h):
    autoliv = musteri_ac(istemci, h)
    bosch = musteri_ac(istemci, h, ad='Bosch Rexroth')
    a = _talep(istemci, h, autoliv, konu='Burç Çakma')
    b = _talep(istemci, h, bosch, konu='Pres hattı', makine_turu='OZEL_MAKINE')
    talepler = lambda q: [x['kimlik'] for x in istemci.get(f'/api/talepler?{q}', headers=h('K050')).json()['talepler']]  # noqa: E731
    assert talepler('q=çakma autoliv') == [a]
    assert talepler('q=CAKMA') == [a]
    assert talepler('q=çakma bosch') == []
    assert talepler('q=T-2026-0002') == [b]
    assert sorted(talepler('q=Çevrim')) == sorted([a, b])                          # gereksinim metni
    assert talepler(f'musteri={bosch}') == [b]
    assert talepler('makine_turu=OZEL_MAKINE') == [b]
    assert talepler('durum=ACIK&yil=2026') == talepler('')
    assert talepler('yil=2025') == []
    # en son sürümün kalem açıklamaları da aranır
    d5_surumu(istemci, h, talep=a)
    assert talepler('q=robot 6 eksen') == [a]


def test_sayac_seridi(istemci, h, cekirdek):
    m = musteri_ac(istemci, h)
    t1, s1 = gonderilmis(istemci, h, d5_talebi(istemci, h, m))
    istemci.post(f'/api/talepler/{t1}/sonuc', headers=h('K050'), json={'sonuc': 'KAZANILDI', 'kazanan_surum': s1})
    t2, _ = gonderilmis(istemci, h, d5_talebi(istemci, h, m))
    istemci.post(f'/api/talepler/{t2}/sonuc', headers=h('K050'), json={'sonuc': 'KAYBEDILDI', 'kayip_nedeni': 'FIYAT'})
    t3, _ = gonderilmis(istemci, h, d5_talebi(istemci, h, m))
    istemci.post(f'/api/talepler/{t3}/sonuc', headers=h('K050'),
                 json={'sonuc': 'KAYBEDILDI', 'kayip_nedeni': 'TESLIM_SURESI'})
    _talep(istemci, h, m)
    r = istemci.get('/api/talepler/sayac', headers=h('K050')).json()
    assert r == {'yil': 2026, 'kazanilan': 1, 'kaybedilen': 2, 'kazanma_orani': 33.3,
                 'kayip_nedenleri': {'FIYAT': 1, 'TEKNIK_COZUM': 0, 'TESLIM_SURESI': 1}, 'acik': 1}
    r = istemci.get('/api/talepler/sayac?yil=2025', headers=h('K050')).json()
    assert (r['kazanilan'], r['kaybedilen'], r['kazanma_orani']) == (0, 0, None)
    assert istemci.get('/api/talepler/sayac', headers=h('K041')).status_code == 403


def test_onay_bekleyenler(istemci, h):
    _, s = d5_surumu(istemci, h)
    assert istemci.get('/api/onay-bekleyenler', headers=h('K001')).json()['surumler'] == []
    gecir(istemci, h, s, 'onaya-gonder', 'K050')
    r = istemci.get('/api/onay-bekleyenler', headers=h('K001')).json()['surumler']
    assert [(x['kimlik'], x['etiket'], x['musteri_adi'], x['hazirlayan_adi'], x['fiyat']) for x in r] == [
        (s, 'T-2026-0001/V1', 'Autoliv', 'Satış Yöneticisi', '56000.00')]
    assert istemci.get('/api/ben', headers=h('K001')).json()['onay_bekleyen'] == 1
    assert istemci.get('/api/onay-bekleyenler', headers=h('K050')).status_code == 403
    gecir(istemci, h, s, 'onayla', 'K001')
    assert istemci.get('/api/ben', headers=h('K001')).json()['onay_bekleyen'] == 0
