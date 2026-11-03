"""/ben, geliştirme girişi, hata eşleme (SPEC › 9, 10)."""
from fastapi.testclient import TestClient

from m11a.api.uygulama import uygulama_kur
from m11a.ayarlar import ortam
from m11a.baglanti import CekirdekHatasi


def test_ben_satis(api):
    r = api('GET', 'K050', '/ben').json()
    assert r['kisi'] == 'K050' and set(r['roller']) == {'YONETICI', 'SATIS'}
    assert r['izinler']['donusturme'] and r['izinler']['tutar_gorme'] and not r['izinler']['kapanis']


def test_ben_muhasebe_ve_yetkili(api):
    m = api('GET', 'K060', '/ben').json()['izinler']
    assert m['gelen_kutusu'] and m['kapanis'] and not m['donusturme'] and not m['ayarlar']
    y = api('GET', 'K001', '/ben').json()['izinler']
    assert all(y.values())


def test_ben_rolsuz(api):
    r = api('GET', 'K017', '/ben').json()
    assert not any(r['izinler'].values())


def test_oturumsuz_401(api):
    r = api('GET', None, '/ben')
    assert r.status_code == 401 and r.json()['kod'] == 'OTURUM'
    r = api.t.get('/api/ben', headers={'Authorization': 'Bearer bozuk'})
    assert r.status_code == 401


def test_gelistirme_girisi(api):
    r = api.t.post('/api/gelistirme/giris', json={'kisi': 'k060'})
    assert r.status_code == 200 and r.json()['kisi'] == 'K060'
    r = api.t.get('/api/ben', headers={'Authorization': 'Bearer ' + r.json()['anahtar']})
    assert r.json()['kisi'] == 'K060'


def test_gelistirme_girisi_kapali(cekirdek):
    app = uygulama_kur(cekirdek=cekirdek, vt_url=ortam().test_veritabani, gelistirme=False, kural_araligi_dk=0)
    with TestClient(app) as t:
        assert t.post('/api/gelistirme/giris', json={'kisi': 'K050'}).status_code == 404


def test_secim_listeleri(api):
    kisiler = {k['kimlik'] for k in api('GET', 'K050', '/kisiler').json()['kisiler']}
    assert {'K050', 'K060', 'K001'} <= kisiler
    birimler = {b['kimlik'] for b in api('GET', 'K050', '/birimler').json()['birimler']}
    assert {'SATIS', 'MUHASEBE', 'MEK_TASARIM'} <= birimler


def test_cekirdek_hatalari_eslenir(api, monkeypatch):
    for tur, http, kod in [('BAGLANTI', 503, 'BAGLANTI'), ('BICIM', 400, 'BEKLENMEYEN'),
                           ('KUNYE', 500, 'BEKLENMEYEN'), ('URUN', 502, 'URUN')]:
        def bozuk(*a, tur=tur, **k):
            raise CekirdekHatasi(tur, 'deneme')
        monkeypatch.setattr(api.c.surucu, 'oku', bozuk)
        r = api('GET', 'K050', '/ben')
        assert (r.status_code, r.json()['kod']) == (http, kod), tur
