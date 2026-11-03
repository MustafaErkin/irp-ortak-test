"""Paket 1.1 sınırları: ortak firma, ayrı servis kimliği, proje ve plan okumaları."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

PAKET=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PAKET.parent),str(PAKET/'arac'),str(PAKET/'simulator')]
from irp_sozlesme.baglanti import Cekirdek,CekirdekHatasi
from irp_sozlesme.baglanti.surucu_http import HttpSurucu
from irp_sozlesme.baglanti.surucu_simulator import SimulatorSurucu
from kunye_denetle import kunye_denetle
from sunucu import ANON,baslat

M3=json.loads((PAKET/'ornekler/M3_mini/kunye.json').read_text())
KAL=json.loads((PAKET/'ornekler/kunyeler/KAL/kunye.json').read_text())

class OrtakBaglanti(unittest.TestCase):
    def test_mevcut_sozde_rol_yeni_kapsam_uydurmadan_kabul_edilir(self):
        k=deepcopy(M3);k['yetki_onerileri']=[{'eylem_kodu':'ETAP.DEGISTIRDIM','kimler':['PROJE_SORUMLUSU'],'kapsam':'FIRMA'}]
        self.assertFalse(kunye_denetle(k).hatalar)
        k['yetki_onerileri'][0]['kapsam']='PROJE'
        self.assertTrue(kunye_denetle(k).hatalar)

    def test_yeni_plan_okumalari_ve_dar_servis(self):
        k=deepcopy(M3);k['kapilar']['servis_okumalari']+=['PROJE','PROJELER','KISILER']
        s=SimulatorSurucu(k);c=Cekirdek(s,k);ceo=c.giris('K001','test')
        projects=ceo.oku('PROJELER').deger
        self.assertIn('2614',[p['kimlik'] for p in projects])
        ordinary=ceo.oku('PLAN','2614').deger
        versioned=ceo.oku('PLAN','2614',surumler=True).deger
        self.assertNotIn('surumler',ordinary)
        self.assertEqual({k:v for k,v in versioned.items() if k!='surumler'},ordinary)
        people=c.servis().oku('KISILER').deger
        self.assertTrue(people);self.assertFalse(any('ad' in p or 'maas' in p for p in people))
        with self.assertRaises(CekirdekHatasi):s.servis_oku(k['servis_kimligi'],'MAAS','K001',{})

    def test_iki_modul_ayni_firmada_ayri_servisle_calisir(self):
        server,cloud=baslat([M3,KAL],port=0)
        try:
            base=f'http://127.0.0.1:{server.server_port}'
            self.assertIs(cloud.moduller['M3'].d,cloud.moduller['KAL'].d)
            self.assertEqual(set(cloud.moduller),{'M3','KAL'})
            http=HttpSurucu(base+'/modul/KAL',ANON,cloud.servis_anahtari('M3'))
            with self.assertRaises(CekirdekHatasi):http.servis_oku('SRV-KAL','TOP_KIMDE','yok',{})
            op=HttpSurucu(base,ANON)
            payload={'eylem_kodu':'PROJE.ACTIM','girdiler':{'kod':'YENI','ad':'Yeni Proje','sorumlu':'K004'}}
            with self.assertRaises(CekirdekHatasi):op._istek('/sahte/yetkili',payload)
            result=op._istek('/sahte/yetkili',payload,cloud.yetkili_anahtari())
            self.assertEqual(result['sonuc'],'BASARILI')
            self.assertEqual(cloud.moduller['M3'].simdi(),cloud.moduller['KAL'].simdi())
            for mod in cloud.moduller.values():
                projects=Cekirdek(mod,mod.kunye).giris('K001','test').oku('PROJELER').deger
                self.assertIn('Yeni Proje',[p['ad'] for p in projects])
        finally:
            server.shutdown();server.server_close()
