"""Sözleşme testleri: simülatöre karşı, senaryoyu senaryolar/ altına kaydeder (SPEC › 14.3).

M1.0 çekirdeğe yalnızca okur; senaryolar okumaları ve zemin olaylarını kaydeder.
"""
import base64
import hashlib
import json
from pathlib import Path

from m10 import vt
from ornek import D5_HESAP, d5_formu, d5_talebi, gecir, kaydet, musteri_ac, yeni_surum


def test_M1002_bagli_proje(istemci, h, cekirdek, senaryo):
    """K050 bağlı projesi 2614 olan ek iş talebi açmak ister; PROJE okuması YETKI alır, modül 403 döner, talep açılmaz.
    Yetkili K050'ye projede erişim verir; K050 yeniden dener, proje okunur, talep açılır."""
    musteri = musteri_ac(istemci, h)
    talep = {'musteri': musteri, 'kaynak': 'EK_IS', 'bagli_proje': '2614', 'tur': 'SAHA_NOTU',
             'konu': 'Kaynak hücresine ikinci fikstür'}

    r = istemci.post('/api/talepler', headers=h('K050'), json=talep)
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')
    assert r.json()['mesaj'] == 'Bu projeyi göremiyorsunuz; bağlamak için projede erişiminiz olmalı.'
    with vt.islem() as b:
        assert b.execute('SELECT count(*) AS n FROM talepler').fetchone()['n'] == 0     # talep açılmadı

    cevap = cekirdek.surucu.yetkili_olay('PROJE.ERISIM_VERDIM', {'proje': '2614', 'kisi': 'K050', 'gerekce': 'ek iş'})
    assert cevap['sonuc'] == 'BASARILI', cevap

    r = istemci.post('/api/talepler', headers=h('K050'), json=talep)
    assert r.status_code == 201, r.text
    assert (r.json()['talep_no'], r.json()['bagli_proje']['kod']) == ('T-2026-0001', '2614')

    sayim = senaryo('M1002_bagli_proje')
    # Beklenen tek ret: PROJE okumasının YETKI'si (simülatörün dilinde PermissionError)
    assert sayim.get('sorgu: hata PermissionError') == 1, sayim
    assert not [k for k in sayim if 'REDDEDILDI' in k or ('hata' in k and 'PermissionError' not in k)], sayim


SABIT = Path(__file__).resolve().parent / 'sabitler' / 'M10.KAZANAN_SURUM.json'
# Karşılaştırma dışı: kimlikler, anlar ve PDF'in içeriği (SPEC › 8.16)
KARSILASTIRMA_DISI = ('surum', 'talep', 'onay_ani', 'gonderim_ani')


def _karsilastirilir(d):
    d = json.loads(json.dumps(d))
    for a in KARSILASTIRMA_DISI:
        d.pop(a)
    d['musteri'].pop('kimlik')
    d['pdf'].pop('parmak_izi')
    d['pdf'].pop('icerik_base64')
    return d


def test_M1001_teklif_dongusu(istemci, h, cekirdek, senaryo):
    """K050 müşteri ve talep açar, V2'yi Ek D.5'teki gibi kurar; onaya gönderir; K050'nin onay denemesi 403;
    K001 onaylar; K050 "gönderildi" der ve talebi bu sürümle KAZANILDI yapar. M10.KAZANAN_SURUM K050'nin
    anahtarıyla Ek D.5'e eşittir; K041'in anahtarıyla 403; TASLAK sürümde 409 KAPI."""
    with vt.islem() as b:            # Ek D.5'in talep numarası T-2026-0012: yılın on ikinci talebi
        b.execute("INSERT INTO sayaclar (ad, donem, son) VALUES ('TALEP', '2026', 11)")
    talep = d5_talebi(istemci, h)
    assert istemci.get(f'/api/talepler/{talep}', headers=h('K050')).json()['talep_no'] == 'T-2026-0012'

    # V1: ilk teklif, gönderildi; müşteri revize istedi
    v1 = yeni_surum(istemci, h, talep)['kimlik']
    kaydet(istemci, h, v1, d5_formu(istemci, h, v1, fiyat='60000.00', teslim_suresi_hafta=30))
    gecir(istemci, h, v1, 'onaya-gonder', 'K050')
    gecir(istemci, h, v1, 'onayla', 'K001')
    gecir(istemci, h, v1, 'gonderildi', 'K050', gonderim_sekli='E_POSTA')

    # V2: V1'den kopya, Ek D.5'teki gibi; işçilik birimleri çekirdeğin BIRIMLER'inden
    v2 = yeni_surum(istemci, h, talep, kaynak='SURUM', kaynak_surum=v1, revize=True)['kimlik']
    birimler = {b_['kimlik'] for b_ in istemci.get('/api/birimler', headers=h('K050')).json()['birimler']}
    form = d5_formu(istemci, h, v2)
    assert {i['birim'] for i in form['iscilik']} <= birimler
    s = kaydet(istemci, h, v2, form)
    assert {k: s['hesap'][k] for k in D5_HESAP} == D5_HESAP
    gecir(istemci, h, v2, 'onaya-gonder', 'K050')
    r = istemci.post(f'/api/surumler/{v2}/onayla', headers=h('K050'), json={})
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')                   # modülün kuralı
    gecir(istemci, h, v2, 'onayla', 'K001')
    gecir(istemci, h, v2, 'gonderildi', 'K050', gonderim_sekli='E_POSTA')
    t = istemci.post(f'/api/talepler/{talep}/sonuc', headers=h('K050'),
                     json={'sonuc': 'KAZANILDI', 'kazanan_surum': v2}).json()
    assert (t['durum'], t['kazanan_surum']) == ('KAZANILDI', v2)

    # M1.1A'nın çağrısı: kullanıcının anahtarıyla
    r = istemci.get(f'/api/saglanan/M10.KAZANAN_SURUM?surum={v2}', headers=h('K050'))
    assert r.status_code == 200, r.text
    cevap = r.json()
    assert _karsilastirilir(cevap) == _karsilastirilir(json.loads(SABIT.read_text('utf-8')))
    pdf = base64.b64decode(cevap['pdf']['icerik_base64'])
    assert pdf.startswith(b'%PDF') and hashlib.sha256(pdf).hexdigest() == cevap['pdf']['parmak_izi']
    assert 'strateji_notu' not in json.dumps(cevap) and 'İyi fiyat ver' not in json.dumps(cevap, ensure_ascii=False)
    assert cevap['onay_ani'].endswith('+03:00') and cevap['surum'] == v2
    assert istemci.get(f'/api/saglanan/M10.KAZANAN_SURUM?surum={v2}', headers=h('K050')).json() == cevap   # donmuş

    r = istemci.get(f'/api/saglanan/M10.KAZANAN_SURUM?surum={v2}', headers=h('K041'))
    assert (r.status_code, r.json()['kod']) == (403, 'YETKI')
    r = istemci.get(f'/api/saglanan/M10.KAZANAN_SURUM?surum={v1}', headers=h('K050'))
    assert (r.status_code, r.json()['kod'], r.json()['neden']) == (409, 'KAPI', 'KAZANILMADI')
    taslak = yeni_surum(istemci, h, d5_talebi(istemci, h, t['musteri']['kimlik']))['kimlik']
    r = istemci.get(f'/api/saglanan/M10.KAZANAN_SURUM?surum={taslak}', headers=h('K050'))
    assert (r.status_code, r.json()['kod'], r.json()['neden']) == (409, 'KAPI', 'GONDERILMEDI')

    sayim = senaryo('M1001_teklif_dongusu')
    assert not [k for k in sayim if 'hata' in k or 'REDDEDILDI' in k], sayim     # ret yok


def test_saglanan_okumalarin_hatalari(istemci, h):
    r = istemci.get('/api/saglanan/M10.KAZANAN_SURUM', headers=h('K050'))
    assert (r.status_code, r.json()['kod']) == (422, 'DOGRULAMA')
    assert istemci.get('/api/saglanan/M10.KAZANAN_SURUM?surum=999', headers=h('K050')).status_code == 404
    r = istemci.get('/api/saglanan/M10.YOK', headers=h('K050'))
    assert (r.status_code, r.json()['kod']) == (404, 'TANIMSIZ_VERI')
    assert istemci.get('/api/saglanan/M10.KAZANAN_SURUM?surum=1').status_code == 401


def test_katalog_temin_sureleri_herkes_okur_fiyat_yok(istemci, h):
    for kisi in ('K041', 'K017', 'K050'):                                      # mühendis, atölye, satış
        r = istemci.get('/api/saglanan/M10.KATALOG_TEMIN_SURELERI', headers=h(kisi))
        assert r.status_code == 200, (kisi, r.text)
        assert r.json() == {'kalemler': [{'kod': 'ROB-6E-20', 'ad': 'Robot, 6 eksen, 20 kg', 'unsur': 'ROBOT',
                                          'butce_kalemi': 'MALZEME', 'tipik_temin_hafta': 10,
                                          'ortalama_temin_hafta': None, 'kritik': True}]}
    assert '28000' not in r.text
