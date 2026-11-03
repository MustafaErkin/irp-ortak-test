"""Paketin kendi testleri: ortam sağlam mı, bağlantı katmanı iki sürücüyle aynı davranıyor mu?

    python3 -m unittest discover -s irp_sozlesme/testler          (irp_sozlesme'nin bulunduğu klasörden)

İlk iş bunu koşun. Geçmiyorsa modüle başlamayın; çıktıyı bize gönderin.
"""
import json
from pathlib import Path
import socket
import sys
import unittest

PAKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAKET.parent))
sys.path.insert(0, str(PAKET / 'arac'))

from irp_sozlesme.baglanti import Cekirdek, CekirdekHatasi  # noqa: E402
from irp_sozlesme.baglanti.surucu_http import HttpSurucu  # noqa: E402
from irp_sozlesme.baglanti.surucu_simulator import SimulatorSurucu  # noqa: E402
sys.path.insert(0, str(PAKET / 'simulator'))
import kunye_denetle  # noqa: E402
import paket_denetle  # noqa: E402
from senaryo_dogrula import dogrula  # noqa: E402
from sunucu import ANON, baslat  # noqa: E402

KUNYE = json.loads((PAKET / 'ornekler' / 'M3_mini' / 'kunye.json').read_text('utf-8'))


def bos_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def akis(test, cekirdek):
    """Aynı akış iki sürücüde: giriş, olay, sürümle okuma, bayat, bildirim, hatalar."""
    o = cekirdek.giris('K006', 'deneme')
    test.assertEqual(o.kisi, 'K006')
    c = o.olay_gonder('NESNE.ACTIM', {'tur': 'PARCA', 'ad': 'Mil', 'kod': 'PT-1', 'proje': '2614',
                                      'sorumlu': 'K006', 'baglar': [{'tur': 'PROJE', 'kimlik': '2614'}]})
    test.assertTrue(c.basarili, c)
    test.assertTrue(c['olay_kimligi'].endswith('-P'))
    parca = c['olay_kimligi']
    n = o.oku('NESNE', parca)
    test.assertTrue(n.guncel)
    test.assertTrue(n.deger.get('surum'))
    hedef = o.hedef('NESNE', n.deger)
    c = o.olay_gonder('NESNE.ASAMA_GECIRDIM', {'hedef': parca, 'yeni_asama': 'SIPARISTE', 'gerekce': 't'}, [hedef])
    test.assertTrue(c.basarili, c)
    c = o.olay_gonder('NESNE.ASAMA_GECIRDIM', {'hedef': parca, 'yeni_asama': 'GELDI', 'gerekce': 't'}, [hedef])
    test.assertTrue(c.bayat, c)
    b = cekirdek.servis().bildirim_birak('SIPARIS_GECIKTI', {'tur': 'NESNE', 'kimlik': parca},
                                         [{'tur': 'KISI', 'kimlik': 'K006'}, {'tur': 'KISI', 'kimlik': 'K017'}], 'deneme')
    test.assertEqual(b['sonuc'], 'BASARILI')
    test.assertIn({'kisi': 'K017', 'neden': 'PROJEYI_GOREMEZ'}, b['suzulenler'])
    test.assertEqual(cekirdek.servis().oku('TOP_KIMDE', None, nesne=parca).deger['asama'], 'SIPARISTE')
    with test.assertRaises(CekirdekHatasi) as h:
        cekirdek.giris('K017', 'deneme').oku('NESNE', parca)
    test.assertEqual(h.exception.tur, 'YETKI')
    with test.assertRaises(CekirdekHatasi) as h:
        o.oku('BOYLE_BIR_OKUMA_YOK')
    test.assertEqual(h.exception.tur, 'BICIM')
    return parca


class A_Paket(unittest.TestCase):
    def test_paket_saglam(self):
        _, degisen, eksik, _ = paket_denetle.denetle()
        self.assertEqual((degisen, eksik), ([], []), 'Paket değişmiş; zip dosyasından yeniden açın')

    def test_ornek_kunyeler_gecer(self):
        for klasor in sorted((PAKET / 'ornekler' / 'kunyeler').iterdir()):
            _, b = kunye_denetle.klasor_denetle(klasor)
            self.assertEqual(b.hatalar, [], klasor.name)
        _, b = kunye_denetle.klasor_denetle(PAKET / 'ornekler' / 'M3_mini')
        self.assertEqual(b.hatalar, [])


class B_Simulator(unittest.TestCase):
    def test_akis_ve_senaryo(self):
        cekirdek = Cekirdek(SimulatorSurucu(KUNYE), KUNYE)
        akis(self, cekirdek)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            yol = cekirdek.surucu.senaryo_yaz(Path(d) / 'PAKET01.girdi.json')
            beklenen, sayim = dogrula(yol)
            self.assertTrue(beklenen.exists())
            self.assertEqual(sayim['olay: REDDEDILDI BAYAT'], 1, sayim)
            self.assertEqual(sayim['sorgu: hata PermissionError'], 1, sayim)

    def test_yetkili_rol_verir(self):
        """Sınamada yetkilinin işi simülatörden yazılır: modülün rolü bir kişiye verilir."""
        kal = json.loads((PAKET / 'ornekler' / 'kunyeler' / 'KAL' / 'kunye.json').read_text('utf-8'))
        cekirdek = Cekirdek(SimulatorSurucu(kal), kal)
        c = cekirdek.surucu.yetkili_olay('KISI.DEGISTIRDIM', {
            'kisi': 'K004', 'degisenler': {'roller': ['YONETICI', 'KALITECI']}, 'gecerli_baslangic': cekirdek.simdi()})
        self.assertEqual(c['sonuc'], 'BASARILI', c)
        kisiler = cekirdek.giris('K004', 'x').oku('KISILER').deger
        self.assertIn('KALITECI', next(k for k in kisiler if k['kimlik'] == 'K004')['roller'])
        self.assertIn('KALITE_KAYDI', cekirdek.surucu.d.nesne_turleri)


class C_SahteBulut(unittest.TestCase):
    def setUp(self):
        self.port = bos_port()
        self.sunucu, self.bulut = baslat(KUNYE, self.port)
        self.surucu = HttpSurucu(f'http://127.0.0.1:{self.port}', ANON, self.bulut.servis_anahtari())

    def tearDown(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()

    def test_ayni_akis_http_uzerinden(self):
        akis(self, Cekirdek(self.surucu, KUNYE))

    def test_anahtarsiz_ve_yanlis_anahtar(self):
        with self.assertRaises(CekirdekHatasi) as h:
            self.surucu.olay_ekle(None, {})
        self.assertEqual(h.exception.tur, 'YETKI')
        kullanici = self.surucu.giris('K006', 'deneme')
        with self.assertRaises(CekirdekHatasi) as h:
            self.surucu.bildirim('SRV-M3', 'birak', {})
        self.assertEqual(h.exception.tur, 'BICIM')                 # servis anahtarıyla ama eksik alan
        with self.assertRaises(CekirdekHatasi) as h:
            HttpSurucu(f'http://127.0.0.1:{self.port}', ANON, kullanici).bildirim('SRV-M3', 'birak', {'modul': 'M3'})
        self.assertEqual(h.exception.tur, 'YETKI')                 # kullanıcı anahtarı servis yerine geçmez

    def test_ag_yoksa_baglanti_hatasi(self):
        surucu = HttpSurucu(f'http://127.0.0.1:{bos_port()}', 'x', zaman_asimi=2, deneme=1)
        with self.assertRaises(CekirdekHatasi) as h:
            surucu.simdi()
        self.assertEqual(h.exception.tur, 'BAGLANTI')


if __name__ == '__main__':
    unittest.main()
