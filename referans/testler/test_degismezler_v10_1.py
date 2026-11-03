import unittest
from irp.degismezler_v10_1 import denetle
from .test_v10_1 import belge_duzenegi, surum_olayi, modul_duzenegi, birak, plan, tarih
from .ortak import t, is_id


class DegismezlerT10(unittest.TestCase):
    def test_I114_I126_dolu_akis(self):
        f,d,n,g=belge_duzenegi()
        tarih(f,d,[plan(i,t(23),t(23,'10:00')) for i in (7,8)],t(22,'09:51'))
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        self.assertTrue(all(denetle(d,True).values()))
        surum_olayi(f,d,n,'ONAYLADIM',t(22,'11:00'))
        self.assertTrue(all(denetle(d,True).values()))
        f,d=modul_duzenegi(); birak(d,t(22,'10:00'))
        self.assertTrue(all(denetle(d,True).values()))

    def test_bozuk_plan_yakalanir(self):
        f,d=modul_duzenegi(); d.isler[is_id(1)].update(planlanan_baslangic=t(23),planlanan_bitis=t(22))
        self.assertFalse(denetle(d)['I114'])

    def test_kendi_onayi_yakalanir(self):
        f,d,n,g=belge_duzenegi(); surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        next(iter(d.nesne_surumleri.values()))['onaylayan']='K041'
        self.assertFalse(denetle(d)['I120'])

    def test_modul_anahtar_bozulmasi_yakalanir(self):
        f,d=modul_duzenegi(); birak(d,t(22,'10:00'))
        x=next(iter(d.modul_bildirimleri.values())); x['alici']='K041'
        self.assertFalse(denetle(d)['I121'])

    def test_olmayan_gorulme_olayi_yakalanir(self):
        from irp import an
        f,d=modul_duzenegi(); birak(d,t(22,'10:00'))
        next(iter(d.modul_bildirimleri.values()))['gorulme_ani']=an(t(22,'10:01'))
        self.assertFalse(denetle(d)['I124'])

    def test_I90_ayri_kalici_tabloyu_korur(self):
        from irp.degismezler_v7 import denetle as d7
        f,d=modul_duzenegi(); birak(d,t(22,'10:00'))
        self.assertTrue(d7(d,True)['I90'])
