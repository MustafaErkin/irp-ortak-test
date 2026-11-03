"""KP: 10.1.1 kapsam ekinin bağımsız beklentili kabul örnekleri."""
import unittest
from decimal import Decimal
from irp.gorunumler import maas_dagilimi,gorev_payi
from irp.gorunum_v10_1 import surumler,bildirim_kutusu
from irp.degismezler_v10 import denetle
from .test_karar99 import ek_erisim_duzenegi
from .test_v10_1 import surum_olayi,modul_duzenegi,birak
from . import test_tur16 as kapsam
from .ortak import t,is_id


class KapsamSenaryolari(unittest.TestCase):
    def test_KP01_sorumlu_taslagi_tarihsel_denetim(self):
        """Karar 99: ek erişimli belge sorumlusu; I106/I107 de izin vermeli."""
        f,d,n=ek_erisim_duzenegi()
        surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        self.assertEqual([x['durum'] for x in surumler(d,n,cagiran='K041')],['TASLAK'])
        result=denetle(d,True)
        self.assertTrue(result['I106']); self.assertTrue(result['I107'])

    def test_KP02_onay_maliyeti_kisiye_ozel(self):
        """T9 §8: hiç görevi olmayan K009un onay bekleyen tutarı sıfırdır."""
        kapsam.OnayGoreviMaliyeti.setUp(self)
        self.assertEqual(gorev_payi(self.d,self.o,'2026-10-22','2026-10-22',kisi='K012'),1)
        self.assertEqual(gorev_payi(self.d,self.o,'2026-10-22','2026-10-22',kisi='K009'),0)
        self.assertEqual(maas_dagilimi(self.d,'K009','2026-10-01')['onay_bekleyen'],Decimal('0.00'))

    def test_KP03_modul_tekillik_ve_ret(self):
        """T10 §3: aynı anahtar güncellenir; gelecek an tabloyu değiştirmez."""
        f,d=modul_duzenegi()
        a=birak(d,t(22,'10:00'),kural='KAPSAM'); b=birak(d,t(22,'10:00'),kural='KAPSAM',metin='Yeni metin')
        self.assertEqual((a['yeni'],b['yeni'],b['guncellenen']),(2,0,2))
        self.assertEqual(len(bildirim_kutusu(d,'K009')),1)
        c=d.modul_bildirimi_birak('SRV-M3','M3','KAPSAM',dict(tur='IS',kimlik=is_id(4)),
                                 [dict(tur='KISI',kimlik='K009')],'Gelecek','UYARI',t(22,'10:01'))
        self.assertEqual(c['kod'],'BICIM')
        self.assertEqual(bildirim_kutusu(d,'K009')[0]['metin'],'Yeni metin')

    def test_KP04_cok_bicimli_kanit_baglari(self):
        """T2 kanıtı dosya türüne göre yorumlamaz; kimlik ve parmak izi korunur."""
        kapsam.SartnameKopru.test_kanitlar_nesne_olay_ve_dosyaya_baglanir(self)
