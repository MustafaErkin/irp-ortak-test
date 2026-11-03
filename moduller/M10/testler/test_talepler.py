"""Adım 5: talep (SPEC › 8.2)."""
import pytest

from ornek import musteri_ac

TALEP = {'kaynak': 'YENI_IS', 'tur': 'KURUMSAL_SARTNAME', 'makine_turu': 'ROBOTIK_HUCRE',
         'konu': '710 Projesi Burç Çakma Ekipmanı', 'aciklama': 'Burç çakma hücresi', 'cevap_tarihi': '2026-11-20',
         'gereksinimler': [{'metin': 'Çevrim süresi 45 sn altında'},
                           {'metin': 'Robot markası?', 'belirsiz': True, 'soru': 'Hangi marka?'}],
         'kapsam': {'dahil': ['Mekanik ve otomasyon tasarımı', 'FAT'], 'haric': ['Saha elektrik altyapısı']}}


@pytest.fixture
def musteri(istemci, h):
    return musteri_ac(istemci, h)


def talep_ac(istemci, h, musteri_, kisi='K050', **ek):
    return istemci.post('/api/talepler', headers=h(kisi), json={**TALEP, 'musteri': musteri_, **ek})


def test_talep_ac_numara_ve_kart(istemci, h, musteri):
    r = talep_ac(istemci, h, musteri)
    assert r.status_code == 201, r.text
    t = r.json()
    assert (t['talep_no'], t['durum'], t['gelis_tarihi'], t['surum']) == ('T-2026-0001', 'ACIK', '2026-11-02', 1)
    assert (t['musteri']['ad'], t['makine_turu_adi'], t['olusturan'], t['olusturan_adi']) == (
        'Autoliv', 'Robotik hücre', 'K050', 'Satış Yöneticisi')
    assert [g['sira'] for g in t['gereksinimler']] == [1, 2] and t['acik_gereksinim'] == 1
    assert t['kapsam'] == TALEP['kapsam'] and t['bagli_proje'] is None and t['surumler'] == []
    assert talep_ac(istemci, h, musteri).json()['talep_no'] == 'T-2026-0002'


def test_talep_numarasi_yil_basina(istemci, h, musteri, cekirdek):
    talep_ac(istemci, h, musteri)
    cekirdek.surucu.saat('2027-01-04T09:00:00+03:00')
    assert talep_ac(istemci, h, musteri).json()['talep_no'] == 'T-2027-0001'


def test_talep_yetki(istemci, h, musteri):
    assert talep_ac(istemci, h, musteri, 'K041').status_code == 403
    assert talep_ac(istemci, h, musteri, 'K001').status_code == 201
    tid = talep_ac(istemci, h, musteri).json()['kimlik']
    assert istemci.get(f'/api/talepler/{tid}', headers=h('K041')).status_code == 403
    assert istemci.get('/api/talepler/9999', headers=h('K050')).status_code == 404


@pytest.mark.parametrize('ek, alan', [({'kaynak': 'EK_IS'}, 'bagli_proje'), ({'makine_turu': 'YOK'}, 'makine_turu'),
                                      ({'musteri': 9999}, 'musteri'), ({'konu': '  '}, 'konu')])
def test_talep_dogrulama(istemci, h, musteri, ek, alan):
    r = talep_ac(istemci, h, musteri, **ek)
    assert r.status_code == 422 and r.json()['hatalar'][0]['alan'] == alan


def test_bagli_proje_okunur_kimligi_tutulur(istemci, h, musteri):
    r = talep_ac(istemci, h, musteri, 'K001', kaynak='SERVIS', bagli_proje=' 2614 ')
    assert r.status_code == 201, r.text
    assert r.json()['bagli_proje'] == {'kod': '2614', 'ad': 'Servo Döner Tablalı Robotik Kaynak Hücresi', 'gorunur': True}
    # aynı talebi projeyi göremeyen satış yöneticisi açar: kod görünür, ad görünmez
    assert istemci.get(f'/api/talepler/{r.json()["kimlik"]}', headers=h('K050')).json()['bagli_proje'] == {
        'kod': '2614', 'ad': None, 'gorunur': False}
    r = talep_ac(istemci, h, musteri, 'K001', kaynak='EK_IS', bagli_proje='9999')
    assert r.status_code == 404
    # YENI_IS'te bağlı proje tutulmaz
    assert talep_ac(istemci, h, musteri, bagli_proje='2614').json()['bagli_proje'] is None


def test_projeler_ucu(istemci, h):
    assert istemci.get('/api/projeler/2614', headers=h('K001')).json() == {
        'kod': '2614', 'ad': 'Servo Döner Tablalı Robotik Kaynak Hücresi'}
    r = istemci.get('/api/projeler/2614', headers=h('K050'))
    assert r.status_code == 403
    assert r.json()['mesaj'] == 'Bu projeyi göremiyorsunuz; bağlamak için projede erişiminiz olmalı.'


def test_talep_guncelle_eszamanlilik_ve_gecmis(istemci, h, musteri):
    t = talep_ac(istemci, h, musteri).json()
    govde = {**TALEP, 'musteri': musteri, 'surum': t['surum'], 'konu': 'Burç çakma hücresi',
             'gereksinimler': [{'metin': 'Robot markası?', 'belirsiz': True, 'cevap': 'ABB'}],
             'kapsam': {'dahil': ['FAT'], 'haric': []}}
    r = istemci.put(f'/api/talepler/{t["kimlik"]}', headers=h('K050'), json=govde)
    assert r.status_code == 200, r.text
    y = r.json()
    assert (y['konu'], y['surum'], y['acik_gereksinim']) == ('Burç çakma hücresi', 2, 0)
    assert y['gereksinimler'][0]['cevap_ani'] is not None and y['kapsam'] == {'dahil': ['FAT'], 'haric': []}
    # eski sayaçla ikinci kayıt: 409 DEGISTI ve güncel hal
    r = istemci.put(f'/api/talepler/{t["kimlik"]}', headers=h('K001'), json=dict(govde, konu='başka'))
    assert r.status_code == 409 and r.json()['kod'] == 'DEGISTI'
    assert r.json()['guncel']['konu'] == 'Burç çakma hücresi' and r.json()['guncel']['surum'] == 2
    gecmis = istemci.get(f'/api/talepler/{t["kimlik"]}/gecmis', headers=h('K050')).json()['kayitlar']
    assert [g['islem'] for g in gecmis] == ['TALEP_ACILDI', 'TALEP_GUNCELLENDI']
    alanlar = {d['alan']: d for d in gecmis[1]['ayrinti']['degisiklikler']}
    assert alanlar['konu'] == {'alan': 'konu', 'eski': '710 Projesi Burç Çakma Ekipmanı', 'yeni': 'Burç çakma hücresi'}
    assert {'gereksinimler', 'kapsam'} <= set(alanlar) and gecmis[1]['kim_adi'] == 'Satış Yöneticisi'


def test_dosya_kaydi(istemci, h, musteri):
    t = talep_ac(istemci, h, musteri).json()
    r = istemci.post(f'/api/talepler/{t["kimlik"]}/dosyalar', headers=h('K050'),
                     json={'tur': 'SARTNAME', 'ad': 'Autoliv_710_sartname.pdf',
                           'konum': '\\\\sunucu\\satis\\T-2026-0001\\sartname.pdf', 'parmak_izi': 'a' * 64})
    assert r.status_code == 201, r.text
    assert [(d['ad'], d['ekleyen']) for d in r.json()['dosyalar']] == [('Autoliv_710_sartname.pdf', 'K050')]
    r = istemci.post(f'/api/talepler/{t["kimlik"]}/dosyalar', headers=h('K050'), json={'tur': 'CIZIM', 'ad': 'x', 'konum': ''})
    assert r.status_code == 422
    r = istemci.post(f'/api/talepler/{t["kimlik"]}/dosyalar', headers=h('K050'),
                     json={'tur': 'CIZIM', 'ad': 'x', 'konum': 'y', 'parmak_izi': 'XYZ'})
    assert r.status_code == 422
    assert istemci.get(f'/api/talepler/{t["kimlik"]}/gecmis', headers=h('K050')).json()['kayitlar'][-1]['islem'] == \
        'DOSYA_EKLENDI'


def test_teklif_vermiyoruz(istemci, h, musteri):
    t = talep_ac(istemci, h, musteri).json()
    r = istemci.post(f'/api/talepler/{t["kimlik"]}/kapat', headers=h('K050'), json={'gerekce': ''})
    assert r.status_code == 422
    r = istemci.post(f'/api/talepler/{t["kimlik"]}/kapat', headers=h('K050'), json={'gerekce': 'Kapasite yok'})
    assert r.status_code == 200, r.text
    k = r.json()
    assert (k['durum'], k['kapatma_gerekcesi'], k['sonucu_yazan']) == ('KAPATILDI', 'Kapasite yok', 'K050')
    r = istemci.post(f'/api/talepler/{t["kimlik"]}/kapat', headers=h('K050'), json={'gerekce': 'yine'})
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')


def test_arama_metni(istemci, h, musteri):
    from m10 import vt
    t = talep_ac(istemci, h, musteri).json()
    with vt.islem() as b:
        arama = b.execute('SELECT arama FROM talepler WHERE kimlik = %s', (t['kimlik'],)).fetchone()['arama']
    for kelime in ('t 2026 0001', 'autoliv', 'burc cakma', 'robotik hucre', 'cevrim suresi', 'saha elektrik'):
        assert kelime in arama, kelime
