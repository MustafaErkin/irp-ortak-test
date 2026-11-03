"""Adım 2: kişi ve erişim (SPEC › 6), hata eşleme (SPEC › 10), /ben, geliştirme girişi."""
import pytest
from fastapi.testclient import TestClient

from irp_sozlesme.baglanti import CekirdekHatasi
from m10 import vt
from m10.alan.yetki import kisi_kur
from m10.api import hatalar
from m10.api.uygulama import uygulama_kur


# ---- saf: erişim kuralı

def test_erisim_kurali():
    satis = kisi_kur({'kimlik': 'K050', 'birim': 'SATIS', 'roller': ['YONETICI', 'SATIS']}, ['YONETIM'])
    ceo = kisi_kur({'kimlik': 'K001', 'birim': 'YONETIM', 'roller': ['YETKILI']}, ['YONETIM'])
    yonetim = kisi_kur({'kimlik': 'K099', 'birim': 'YONETIM', 'roller': ['YONETICI']}, ['YONETIM'])
    muhendis = kisi_kur({'kimlik': 'K041', 'birim': 'MEK_TASARIM', 'roller': ['BEYAZ_YAKA']}, ['YONETIM'])
    assert (satis.erisim, satis.duzenleyici, satis.onayci) == (True, True, False)
    assert (ceo.erisim, ceo.duzenleyici, ceo.onayci) == (True, True, True)
    assert (yonetim.erisim, yonetim.duzenleyici, yonetim.onayci, yonetim.ayarlayabilir) == (True, False, False, True)
    assert (muhendis.erisim, muhendis.duzenleyici, muhendis.ayarlayabilir) == (False, False, False)
    assert satis.duzenlemeye_acabilir('K050') and not satis.duzenlemeye_acabilir('K001')
    assert ceo.duzenlemeye_acabilir('K050')
    assert ceo.yonetim_birimlerini_degistirebilir and not satis.yonetim_birimlerini_degistirebilir
    assert ceo.geri_acabilir and not satis.geri_acabilir


# ---- /ben

def test_ben_satis_yoneticisi(istemci, h):
    r = istemci.get('/api/ben', headers=h('K050'))
    assert r.status_code == 200, r.text
    j = r.json()
    assert (j['kimlik'], j['birim'], j['erisim'], j['duzenleyici'], j['onayci']) == ('K050', 'SATIS', True, True, False)
    assert 'SATIS' in j['roller']


def test_ben_onayci(istemci, h):
    j = istemci.get('/api/ben', headers=h('K001')).json()
    assert (j['onayci'], j['onay_bekleyen'], j['erisim']) == (True, 0, True)


def test_erisimi_olmayan_kendini_gorur_baska_bir_sey_goremez(istemci, h):
    j = istemci.get('/api/ben', headers=h('K041')).json()
    assert j['erisim'] is False
    r = istemci.get('/api/kisiler', headers=h('K041'))
    assert r.status_code == 403 and r.json()['kod'] == 'YETKI'


def test_yonetim_birimleri_ayari_erisim_verir(istemci, h):
    assert istemci.get('/api/birimler', headers=h('K004')).status_code == 403
    with vt.islem() as b:
        b.execute("""UPDATE ayarlar SET deger = '["YONETIM", "PLANLAMA"]' WHERE anahtar = 'yonetim_birimleri'""")
    r = istemci.get('/api/birimler', headers=h('K004'))
    assert r.status_code == 200
    assert {'SATIS', 'MUHASEBE', 'IMALAT'} <= {x['kimlik'] for x in r.json()['birimler']}


@pytest.mark.parametrize('baslik', [None, 'Bearer', 'Bearer bozuk', 'Basic abc'])
def test_oturumsuz_istek_401(istemci, baslik):
    r = istemci.get('/api/ben', headers={'Authorization': baslik} if baslik else {})
    assert r.status_code == 401 and r.json()['kod'] == 'OTURUM'


def test_kisiler_listesi(istemci, h):
    kisiler = istemci.get('/api/kisiler', headers=h('K050')).json()['kisiler']
    assert {'K001', 'K050', 'K041'} <= {k['kimlik'] for k in kisiler}


# ---- geliştirme girişi

def test_gelistirme_girisi_kapaliyken_yok(istemci, monkeypatch):
    monkeypatch.delenv('M10_GELISTIRME', raising=False)
    assert istemci.post('/api/gelistirme/giris', json={'kisi': 'K001'}).status_code == 404


def test_gelistirme_girisi(istemci, monkeypatch):
    monkeypatch.setenv('M10_GELISTIRME', '1')
    r = istemci.post('/api/gelistirme/giris', json={'kisi': 'k050'})
    assert r.status_code == 200 and r.json()['kisi'] == 'K050'
    j = istemci.get('/api/ben', headers={'Authorization': f'Bearer {r.json()["anahtar"]}'}).json()
    assert j['kimlik'] == 'K050'


# ---- hata eşleme

@pytest.mark.parametrize('tur, http, kod', [
    ('YETKI', 403, 'YETKI'), ('BICIM', 400, 'BEKLENMEYEN'), ('KUNYE', 500, 'BEKLENMEYEN'),
    ('BAGLANTI', 503, 'BAGLANTI'), ('URUN', 502, 'URUN')])
def test_cekirdek_hatasi_eslemesi(tur, http, kod, cekirdek, temiz_vt):
    app = uygulama_kur()

    @app.get('/api/_deneme')
    def _deneme():
        raise CekirdekHatasi(tur, 'ayrıntı')

    r = TestClient(app).get('/api/_deneme')
    assert (r.status_code, r.json()['kod']) == (http, kod)
    assert r.json()['mesaj'] == hatalar.CEKIRDEK[tur][2]
    assert 'ayrıntı' not in r.text


def test_dogrulama_hatasi_bicimi(istemci):
    r = istemci.post('/api/gelistirme/giris', json={})
    assert r.status_code == 422
    j = r.json()
    assert j['kod'] == 'DOGRULAMA' and j['hatalar'][0]['alan'] == 'kisi'
    assert set(j['hatalar'][0]) == {'alan', 'sira', 'mesaj'}


def test_bilinmeyen_yol_404(istemci, h):
    r = istemci.get('/api/yok-boyle', headers=h('K050'))
    assert (r.status_code, r.json()['kod']) == (404, 'BULUNAMADI')
