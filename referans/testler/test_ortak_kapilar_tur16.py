"""90 olay için ortak biçim/kimlik kapıları; eyleme özel rol/durum kanıtı değildir.

Girdiler gerçek kabul izlerinden alınmıştır. Beklenen ret modeli taklit etmez:
T2 olay kimliği sözleşmesi ve T3/A5 servis aktarımı yetkisi kullanılır.
"""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from irp import Depo,Saat

ORNEKLER=json.loads((Path(__file__).parent/'veri/tur16_kapi_ornekleri.json').read_text('utf-8'))


class OrtakKapiMatrisi(unittest.TestCase):
    def test_her_olayda_gecersiz_olay_kimligi_bicim_hatasidir(self):
        for kod,original in ORNEKLER.items():
            with self.subTest(eylem=kod):
                e=deepcopy(original); e['olay_kimligi']='gecersiz-kimlik'
                d=Depo(Saat(e['oldugu_an']))
                self.assertEqual(d.olay_ekle(e,oturum=e['kim'],servis=True).get('kod'),'BICIM')
                self.assertEqual(d.olaylar,{})

    def test_aktarim_servis_yetkisi_gerektirir(self):
        for kod,original in ORNEKLER.items():
            if kod=='KURULUM.TAMAMLADIM': continue  # Atomik kurulumun ayrı DURUM kapısı önce gelir.
            with self.subTest(eylem=kod):
                e=deepcopy(original); e['giris_sekli']='AKTARIM'
                d=Depo(Saat(e['oldugu_an']))
                if kod=='GECIKME.DEGERLENDIRDIM':
                    # Bu olayın biçimi aktif duruş nedeni listesini de kullanır.
                    from .test_v9 import duzenek
                    from .test_v7 import kur
                    d=kur(duzenek(),e['oldugu_an'])
                once=set(d.olaylar)
                self.assertEqual(d.olay_ekle(e,oturum=e['kim'],servis=False).get('kod'),'YETKI')
                self.assertEqual(set(d.olaylar),once)
