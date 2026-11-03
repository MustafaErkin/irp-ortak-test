"""Urun karsilastirmasinin hata gizlemedigini dogrular."""
import unittest
from cevap_anahtari.karsilastir import farklar

class PaketKarsilastirma(unittest.TestCase):
    def test_B36_isletim_alanlari_ihmal(self):
        self.assertFalse(farklar({'durum':'ACIK','kural_versiyonu':1,'son_olay':'A'},
                                 {'durum':'ACIK','kural_versiyonu':99,'son_olay':'B'}))
    def test_liste_sirasi_korunur(self):
        self.assertTrue(farklar({'listeler':{'K017':['A','B']}},{'listeler':{'K017':['B','A']}}))
    def test_eksik_alan_ve_bool_sayi_farki(self):
        self.assertTrue(farklar({'onay_gerekli':True},{'onay_gerekli':1}))
        self.assertTrue(farklar({'durum':'ACIK'},{}))
    def test_zaman_ve_sayisal_tolerans(self):
        self.assertFalse(farklar({'an':'2026-10-22T09:00:00+03:00','saat':20/3},
                                 {'an':'2026-10-22T06:00:00Z','saat':6.666667}))
        self.assertTrue(farklar({'saat':20/3},{'saat':6.666}))
    def test_aralik_satir_sirasi_ve_icerik(self):
        a={'araliklar':[{'is':'A','dakika':2},{'is':'B','dakika':3}]}
        self.assertFalse(farklar(a,{'araliklar':list(reversed(a['araliklar']))}))
        self.assertTrue(farklar(a,{'araliklar':[{'is':'A','dakika':3},{'is':'B','dakika':2}]}))
