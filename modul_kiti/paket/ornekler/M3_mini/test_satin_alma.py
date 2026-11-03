"""Örnek modülün sözleşme testi: simülatöre karşı koşar ve senaryoyu kaydeder.

    python3 -m unittest irp_sozlesme/ornekler/M3_mini/test_satin_alma.py

Sizin modülünüzde: bu dosyanın benzeri modülün kendi klasöründe durur; senaryolar `senaryolar/` altına yazılır,
sonra `irp_sozlesme/arac/senaryo_dogrula.py senaryolar/*.girdi.json` koşulur (sozlesme/05_sinama.md).
"""
from pathlib import Path
import sys
import tempfile
import unittest

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI.parents[2]))      # irp_sozlesme'nin bulunduğu klasör
sys.path.insert(0, str(BURASI))

from irp_sozlesme.baglanti import Cekirdek, CekirdekHatasi  # noqa: E402
from modul.satin_alma import SatinAlma  # noqa: E402


class SatinAlmaSozlesmesi(unittest.TestCase):
    def setUp(self):
        self.cekirdek = Cekirdek.ac(BURASI / 'kunye.json')
        self.surucu = self.cekirdek.surucu
        self.modul = SatinAlma(self.cekirdek)
        self.planlama = self.cekirdek.giris('K006', 'deneme')       # planlama uzmanı (örnek firma)
        self.surucu.saat('2026-10-27T09:00:00+03:00')

    def test_siparis_ve_gecikme(self):
        parca, cevap = self.modul.parca_ac(self.planlama, 'Ana mil', 'AM-001', '2614')
        self.assertTrue(cevap.basarili, cevap)
        self.assertEqual(self.modul.siparis_ver(self.planlama, parca, 'Tedarikçi A', 1200, '2026-10-30T17:00:00+03:00'),
                         {'durum': 'TAMAM'})
        self.assertEqual(self.planlama.oku('TOP_KIMDE', None, nesne=parca).deger['asama'], 'SIPARISTE')

        self.surucu.saat('2026-11-02T09:00:00+03:00')                # termin geçti
        self.assertEqual(self.modul.gecikenleri_bildir(), {'birakilan': 1, 'kaldirilan': 0})
        self.assertEqual(self.modul.gecikenleri_bildir(), {'birakilan': 1, 'kaldirilan': 0})   # tekrar güvenli
        kutu = self.planlama.oku('BILDIRIMLER', self.planlama.kisi).deger
        self.assertEqual([(x['kaynak'], x['kural']) for x in kutu], [('M3', 'SIPARIS_GECIKTI')])

        okunan = self.planlama.oku('NESNE', parca).deger
        cevap = self.planlama.olay_gonder('NESNE.ASAMA_GECIRDIM', {'hedef': parca, 'yeni_asama': 'GELDI',
                                                                    'gerekce': 'teslim alındı'},
                                          neyin_ustunde=[self.planlama.hedef('NESNE', okunan)])
        self.assertTrue(cevap.basarili, cevap)
        self.assertEqual(self.modul.gecikenleri_bildir(), {'birakilan': 0, 'kaldirilan': 1})

        with tempfile.TemporaryDirectory() as d:
            yol = self.surucu.senaryo_yaz(Path(d) / 'M3MINI01.girdi.json')
            sys.path.insert(0, str(BURASI.parents[1] / 'arac'))
            from senaryo_dogrula import dogrula
            _, sayim = dogrula(yol)
            self.assertFalse([k for k in sayim if 'hata' in k or 'REDDEDILDI' in k], sayim)

    def test_bayat_karar_yeniden_sorulur(self):
        parca, _ = self.modul.parca_ac(self.planlama, 'Flanş', 'FL-001', '2614')
        eski = self.planlama.oku('NESNE', parca).deger
        self.modul.siparis_ver(self.planlama, parca, 'Tedarikçi B', 300, '2026-11-05T17:00:00+03:00')
        cevap = self.planlama.olay_gonder('NESNE.ASAMA_GECIRDIM', {'hedef': parca, 'yeni_asama': 'SIPARISTE',
                                                                    'gerekce': 'eski ekrandan'},
                                          neyin_ustunde=[self.planlama.hedef('NESNE', eski)])
        self.assertTrue(cevap.bayat, cevap)

    def test_projeyi_gormeyen_okuyamaz(self):
        parca, _ = self.modul.parca_ac(self.planlama, 'Mil', 'M-002', '2614')
        isci = self.cekirdek.giris('K017', 'deneme')                 # atölye çalışanı; projede değil
        with self.assertRaises(CekirdekHatasi) as h:
            isci.oku('NESNE', parca)
        self.assertEqual(h.exception.tur, 'YETKI')

    def test_kunyede_olmayan_eylem_gonderilmez(self):
        with self.assertRaises(CekirdekHatasi) as h:
            self.planlama.olay_gonder('PLAN.TARIHLEDIM', {'hedefler': []})
        self.assertEqual(h.exception.tur, 'KUNYE')


if __name__ == '__main__':
    unittest.main()
