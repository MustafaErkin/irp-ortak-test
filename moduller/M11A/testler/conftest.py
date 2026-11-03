"""Ortak sınama düzeni (SPEC › 14). Her test temiz bir mod_m11a şemasıyla başlar."""
from collections import Counter
from pathlib import Path
import sys

import pytest

from m11a import vt
from m11a.ayarlar import ortam


@pytest.fixture
def vt_baglanti():
    with vt.baglan(ortam().test_veritabani, autocommit=True) as b:
        vt.sema_kur(b)
        yield b


@pytest.fixture
def cekirdek(vt_baglanti):
    """Her test kendi çekirdeğini açar; zemin D.10 (satis_rolu_kur=True; SPEC › 14.3)."""
    from m11a.baglanti import cekirdek_ac
    from testler.zemin import a_ekibi_zemini
    c = cekirdek_ac(vt_url=ortam().test_veritabani)
    a_ekibi_zemini(c, satis_rolu_kur=True)
    return c


KOK = Path(__file__).resolve().parents[1]


def senaryo_kaydet(c, ad: str) -> Counter:
    """Sözleşme senaryosunu senaryolar/ altına yazar, simülatörde baştan oynatır (.beklenen.json), sayımı döner."""
    sys.path.insert(0, str(KOK / 'irp_sozlesme' / 'arac'))
    from senaryo_dogrula import dogrula
    yol = c.surucu.senaryo_yaz(KOK / 'senaryolar' / f'{ad}.girdi.json')
    return dogrula(yol)[1]


def retler(sayim: Counter) -> dict:
    return {k: v for k, v in sayim.items() if 'REDDEDILDI' in k or 'hata' in k}


def olay_sayisi(c) -> int:
    return sum(a['tur'] == 'olay' for a in c.surucu._adimlar)


class Istemci:
    """API istemcisi; kişinin anahtarıyla istek atar."""

    def __init__(self, test_istemcisi, cekirdek):
        self.t, self.c, self._anahtarlar = test_istemcisi, cekirdek, {}

    def anahtar(self, kisi):
        if kisi not in self._anahtarlar:
            self._anahtarlar[kisi] = self.c.giris(kisi, 'deneme').anahtar
        return self._anahtarlar[kisi]

    def __call__(self, yontem, kisi, yol, **k):
        basliklar = {'Authorization': f'Bearer {self.anahtar(kisi)}'} if kisi else {}
        return self.t.request(yontem, '/api' + yol, headers=basliklar, **k)


@pytest.fixture
def api(cekirdek, vt_baglanti):
    from fastapi.testclient import TestClient
    from m11a.api.uygulama import uygulama_kur
    from m11a.saglayicilar import SahteM10Saglayici
    from testler.ornek import kazanan_surum
    m10 = SahteM10Saglayici([kazanan_surum()])
    app = uygulama_kur(cekirdek=cekirdek, vt_url=ortam().test_veritabani, saglayici=m10, gelistirme=True,
                       kural_araligi_dk=0)
    with TestClient(app) as t:
        i = Istemci(t, cekirdek)
        i.m10, i.vt = m10, vt_baglanti
        yield i
