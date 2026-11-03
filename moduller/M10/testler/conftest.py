"""Testlerin ortak fikstürleri.

- Çekirdeğe karşı olanlar simülatörle: her test kendi çekirdeğini açar ve D.10'daki zemini kurar.
- Veritabanı: M10_TEST_VERITABANI; her test şemayı temiz bulur (göçler + gelistirme/ornek_veriler.sql).
"""
import os

import pytest

os.environ.setdefault('IRP_CEKIRDEK', 'simulator')

from fastapi.testclient import TestClient  # noqa: E402

from irp_sozlesme.baglanti import Cekirdek  # noqa: E402
from m10 import ayarlar, baglanti, komutlar, vt  # noqa: E402
from m10.api.uygulama import uygulama_kur  # noqa: E402

from zemin import a_ekibi_zemini  # noqa: E402


@pytest.fixture(scope='session')
def _havuz():
    vt.kur(ayarlar.test_veritabani())
    yield
    vt.kapat()


@pytest.fixture
def temiz_vt(_havuz):
    komutlar.sema_kur(ayarlar.test_veritabani())


@pytest.fixture
def cekirdek():
    c = Cekirdek.ac(ayarlar.kunye_yolu())
    a_ekibi_zemini(c)
    baglanti.kur(c)
    yield c
    baglanti.kur(None)


@pytest.fixture
def istemci(cekirdek, temiz_vt):
    return TestClient(uygulama_kur())


@pytest.fixture
def h(cekirdek):
    """h('K050') → o kişinin erişim anahtarıyla istek başlıkları."""
    anahtarlar = {}

    def basliklar(kisi):
        if kisi not in anahtarlar:
            anahtarlar[kisi] = cekirdek.giris(kisi, 'deneme').anahtar
        return {'Authorization': f'Bearer {anahtarlar[kisi]}'}
    return basliklar


@pytest.fixture
def senaryo(cekirdek):
    """senaryo('M1002_bagli_proje') → çekirdeğe giden adımları senaryolar/ altına yazar, simülatörde baştan oynatır
    (.beklenen.json) ve çekirdeğin cevaplarının sayımını döner (sozlesme/05_sinama.md)."""
    def kaydet(ad):
        import sys
        sys.path.insert(0, str(ayarlar.KOK / 'irp_sozlesme' / 'arac'))
        from senaryo_dogrula import dogrula
        yol = cekirdek.surucu.senaryo_yaz(ayarlar.KOK / 'senaryolar' / f'{ad}.girdi.json')
        return dict(dogrula(yol)[1])
    return kaydet
