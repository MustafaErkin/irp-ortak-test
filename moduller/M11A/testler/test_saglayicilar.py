"""M1.0 sağlayıcı istemcisi (SPEC › 14.4, Ek D.4)."""
import httpx
import pytest

from m11a.saglayicilar import HttpM10Saglayici, SaglayiciHatasi, SahteM10Saglayici
from testler.ornek import kazanan_surum

TABAN = 'http://m10.yerel/api'
ANAHTAR = 'aaa.bbb.ccc'


def _saglayici(isleyici):
    gelen = []

    def kayit(istek: httpx.Request):
        gelen.append(istek)
        return isleyici(istek)
    return HttpM10Saglayici(TABAN, transport=httpx.MockTransport(kayit)), gelen


def test_200_ve_anahtar_degismeden_iletilir():
    ornek = kazanan_surum()
    s, gelen = _saglayici(lambda r: httpx.Response(200, json=ornek))
    assert s.kazanan_surum(ANAHTAR, 57) == ornek
    (r,) = gelen
    assert r.headers['authorization'] == f'Bearer {ANAHTAR}'
    assert str(r.url) == f'{TABAN}/saglanan/M10.KAZANAN_SURUM?surum=57'


def test_hesaplaniyor_govdede_kalir():
    s, _ = _saglayici(lambda r: httpx.Response(200, json={'surum': 57, 'hesaplaniyor': True}))
    assert s.kazanan_surum(ANAHTAR, 57)['hesaplaniyor'] is True


@pytest.mark.parametrize('http, govde, kod', [
    (401, None, 'OTURUM'),
    (403, {'kod': 'YETKI', 'mesaj': 'yok'}, 'YETKI'),
    (404, {'kod': 'BULUNAMADI', 'mesaj': 'yok'}, 'BULUNAMADI'),
    (404, {'kod': 'TANIMSIZ_VERI', 'mesaj': 'yok'}, 'TANIMSIZ_VERI'),
    (409, {'kod': 'KAPI', 'mesaj': 'kapı', 'neden': 'KAZANILMADI'}, 'KAPI'),
    (422, {'kod': 'DOGRULAMA', 'mesaj': 'eksik'}, 'DOGRULAMA'),
    (500, None, 'SAGLAYICI_YOK'),
    (503, {'kod': 'x'}, 'SAGLAYICI_YOK'),
])
def test_cevap_eslemesi(http, govde, kod):
    s, _ = _saglayici(lambda r: httpx.Response(http, json=govde) if govde else httpx.Response(http))
    with pytest.raises(SaglayiciHatasi) as h:
        s.kazanan_surum(ANAHTAR, 57)
    assert h.value.kod == kod and h.value.http == http
    if kod == 'KAPI':
        assert h.value.neden == 'KAZANILMADI'


def test_zaman_asimi_bir_kez_yeniden_denenir():
    def zaman_asimi(r):
        raise httpx.ReadTimeout('yavaş', request=r)
    s, gelen = _saglayici(zaman_asimi)
    with pytest.raises(SaglayiciHatasi) as h:
        s.kazanan_surum(ANAHTAR, 57)
    assert h.value.kod == 'SAGLAYICI_YOK' and len(gelen) == 2


def test_ikinci_denemede_gelirse_kullanilir():
    sayac = []

    def bir_kez_kopar(r):
        sayac.append(1)
        if len(sayac) == 1:
            raise httpx.ConnectError('kopuk', request=r)
        return httpx.Response(200, json={'surum': 57})
    s, _ = _saglayici(bir_kez_kopar)
    assert s.kazanan_surum(ANAHTAR, 57) == {'surum': 57}


def test_baglanti_hatasi_ve_bos_adres():
    def kopuk(r):
        raise httpx.ConnectError('yok', request=r)
    s, _ = _saglayici(kopuk)
    with pytest.raises(SaglayiciHatasi) as h:
        s.kazanan_surum(ANAHTAR, 57)
    assert h.value.kod == 'SAGLAYICI_YOK'
    for taban in (None, '', '  '):
        with pytest.raises(SaglayiciHatasi) as h:
            HttpM10Saglayici(taban).kazanan_surum(ANAHTAR, 57)
        assert h.value.kod == 'SAGLAYICI_YOK'


def test_sahte_saglayici_kapi_ve_anahtar():
    s = SahteM10Saglayici([kazanan_surum(), kazanan_surum(surum=60, durum='HAZIRLANIYOR'),
                           kazanan_surum(surum=61, talep_durumu='KAYBEDILDI')])
    assert s.kazanan_surum(ANAHTAR, 57)['fiyat'] == '56000.00'
    assert s.cagrilar == [(ANAHTAR, 57)]
    for surum, neden in ((60, 'GONDERILMEDI'), (61, 'KAZANILMADI')):
        with pytest.raises(SaglayiciHatasi) as h:
            s.kazanan_surum(ANAHTAR, surum)
        assert (h.value.kod, h.value.neden) == ('KAPI', neden)
    with pytest.raises(SaglayiciHatasi) as h:
        s.kazanan_surum(ANAHTAR, 99)
    assert h.value.kod == 'BULUNAMADI'


def test_sabit_ornek_pdf_parmak_izi():
    import base64
    import hashlib
    s = kazanan_surum()
    pdf = base64.b64decode(s['pdf']['icerik_base64'])
    assert pdf.startswith(b'%PDF-') and hashlib.sha256(pdf).hexdigest() == s['pdf']['parmak_izi']
