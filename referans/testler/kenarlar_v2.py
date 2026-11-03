"""Yeni küçük karşı örnekler; TASARIM hataları gerçek üretim yolunda sınanır."""
import unittest,random
from copy import deepcopy
from irp import Saat,Depo,an
from irp.cihaz import Cihaz
from irp.kisi_gunu import kapi
from irp.gorunumler import *
from irp.zaman import ay_kapanisi
from irp.is_ import emek
from .ortak import Duzenek,t,is_id,s1,yaz
from .tur2_ornekler import isaret,iki_kisi,kisi_degisim
from .degismezler_v2 import onay_bekleyen
from .test_senaryolar import revizyon_ornegi

class KenarlarV2(unittest.TestCase):
    def test_notun_coklu_hedefi_ve_alici_sirasi(self):
        f=Duzenek()
        f.olay('K012','AYAR.YONLENDIRDIM',t(22,'08:00'),girdiler={'birim':'MEK_TASARIM','kisiler':['K044','K041']})
        f.olay('K004','AYAR.YONLENDIRDIM',t(22,'08:00'),girdiler={'birim':'PLANLAMA','kisiler':['K041','K012']})
        hedef=[{'tur':'PROJE','kimlik':'2509084'},{'tur':'PARCA','kimlik':'2509084_07_04-14'}]
        e=f.olay('K041','NOT.YAZDIM',t(22,'09:00'),hedef,{'metin':'Ortak not','etiketler':['MEK_TASARIM','PLANLAMA']})
        d=f.calistir(t(22,'10:00'))
        self.assertEqual(d.notlar[e]['neyin_ustunde'],hedef)
        self.assertEqual([d.gorevler[e+'/'+str(n)]['kisi'] for n in (1,2,3)],['K012','K041','K044'])
        self.assertEqual(len([g for g in d.gorevler.values() if g['tur']=='NOT']),3)

    def test_adil_performans_donem(self):
        from irp.gorunumler import adil_performans
        f=Duzenek(); g=f.gorev_ata(t(26,'09:00'),zaman_degeri=4,onay_gerekli=True,onaylayan='K012',nereye='PROJE_DISI',kategori='PD.IDARI_MALI',teslim_tarihi='2026-10-30')
        f.gorev_olay('KABUL_ETTIM',t(26,'10:00'),g)
        f.gorev_olay('TAMAMLADIM',t(30,'16:00'),g)
        f.gorev_olay('REDDETTIM',t(2,'09:00',11),g,'K012',**{'not':'Ret','sebep_olan':'K041','revizyon_ver':False})
        f.gorev_olay('TAMAMLADIM',t(2,'10:00',11),g)
        f.gorev_olay('ONAYLADIM',t(2,'11:00',11),g,'K012')
        d=f.calistir(t(2,'12:00',11)); a=adil_performans(d,'K041','2026-10-01','2026-10-31'); b=adil_performans(d,'K041','2026-11-01','2026-11-30')
        self.assertEqual((a['teslim'],a['zamaninda'],a['kalite_ret'],a['katki_saat'],a['sebep_olunan_gecikme']),(1,1,0,0,0))
        self.assertEqual((b['teslim'],b['kalite_ret'],b['katki_saat'],b['sebep_olunan_gecikme']),(0,1,4,4))

    def test_C21_saat_geri_gelince_silinen_gun_sayaci(self):
        """C21 TASARIM A1: eski günleri silmek saat düzeltmesinde kimliği yineleyebilir."""
        d=Duzenek().calistir(t(23,'00:01')); c=Cihaz('K017','T',Saat(t(22,'23:59'))); ilk=c.olay_kimligi_uret()
        c.saat.ilerlet(t(23,'00:01')); c.sayaci_esitle(d)
        c.veri['fark_saniye']=-120
        self.assertNotEqual(c.olay_kimligi_uret(),ilk)

    def test_C22_cevrimdisi_teslim_eski_kisi_yetkisi(self):
        """C22 TASARIM T3 §4/A5: olay anında sahibi olan kişi aktarım anında reddediliyor."""
        f,g=kisi_degisim(); d=f.calistir(t(28,'11:00'))
        f.gorev_olay('TAMAMLADIM',t(27,'16:00'),g,'K041')
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')

    def test_C23_ikinci_tamamla_onayi_atlar(self):
        """C23 TASARIM A8: onay bekleyen işte ikinci fiziksel bitiş onayı atlıyor."""
        f,d=onay_bekleyen(); f.is_olay('TAMAMLADIM','09:05',9)
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        d.ilerlet(t(22,'09:15'))
        self.assertEqual(d.isler[is_id(9)]['durum'],'ONAY_BEKLIYOR')

    def test_C24_biten_goreve_gec_kabul(self):
        """C24 TASARIM A10: kapı dışı görev tanıklığı terminal durumu tekrar açıyor."""
        f=Duzenek(); g=f.gorev_ata(); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),g); f.gorev_olay('TAMAMLADIM',t(22,'09:00'),g); d=f.calistir(t(22,'09:10'))
        f.gorev_olay('KABUL_ETTIM',t(22,'09:05'),g); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.gorevler[g]['durum'],'BITTI')

    def test_C25_elle_bitis_sonraki_gunun_basi(self):
        """C25 TASARIM A8b/A11: geriye etkili bitiş sonraki günün bağlamını kesmiyor."""
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('MESAI.GIRDIM','07:58',gun=23); f.is_olay('BASLADIM','08:00',4,gun=23)
        d=f.calistir(t(23,'09:05'))
        f.olay('K009','IS.SURE_EKLEDIM',t(23,'09:00'),4,{'baslangic':t(22,'16:00'),'bitis':t(22,'17:00'),'aciklama':'Dun bitti','is_bitti':True},adina='K017',giris_sekli='ELLE')
        self.assertEqual(yaz(d,f.olaylar[-1]).get('kod'),'DURUM')
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-23')['kovalar'].get('CALISMA',0),65)

    def test_C26_onayli_basin_onune_devir(self):
        """C26 TASARIM: DEVRETTIM kapısı hedef kişinin onay bekleyen başını kontrol etmiyor."""
        f,d=onay_bekleyen(); f.ata(5,'K023',zaman=t(22,'09:09')); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        f.is_olay('DEVRETTIM','09:10',5,'K009',kimden='K023',kime='K017'); self.assertEqual(yaz(d,f.olaylar[-1]).get('kod'),'DURUM')

    def test_C27_onay_gorevi_kimligi_coklu_teslim(self):
        """C27 TASARIM T2 olay listesi/A7: çok hedefli teslim onay kimliğini çakıştırıyor."""
        f=Duzenek(); g=f.gorev_ata(satirlar=[f.gorev_satiri(onay_gerekli=True,onaylayan='K012') for _ in range(2)]); ids=[g,g.rsplit('/',1)[0]+'/2']
        f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),ids); d=f.calistir(t(22,'09:00'))
        f.gorev_olay('TAMAMLADIM',t(22,'09:00'),ids); self.assertEqual(yaz(d,f.olaylar[-1]).get('kod'),'BICIM')
        self.assertEqual(len([x for x in d.gorevler.values() if x['tur']=='ONAY']),0)

    def test_C28_ayni_kisi_iki_kisilik_ise(self):
        """C28 TASARIM T3 §2: kişi sayısı kontrolü benzersiz kişi kontrolü değil."""
        f,g=iki_kisi(); d=f.calistir(t(22,'08:01'))
        f.olay('K009','IS.ATADIM',t(22,'08:01'),g,{'kisiler':['K017','K017'],'sira':1})
        self.assertEqual(yaz(d,f.olaylar[-1]).get('kod'),'DURUM')

    def test_C29_ayni_gun_oran_gecmisi_degisir(self):
        """C29 TASARIM A17 gün sınırı: aynı gün geriye etkili oran eski doğumu değiştirir."""
        f=Duzenek(); g=f.gorev_ata(zaman_degeri=60,onay_gerekli=True,onaylayan='K012'); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),g); o=f.gorev_olay('TAMAMLADIM',t(22,'09:00'),g)
        d=f.calistir(t(22,'11:00')); self.assertEqual(d.gorevler[o]['zaman_degeri'],6)
        f.olay('K001','AYAR.ONAY_ORANI',t(22,'10:00'),girdiler={'deger':.2,'gecerli_baslangic':'2026-10-22'})
        sonuc=yaz(d,f.olaylar[-1]); self.assertEqual(sonuc.get('kod'),'DURUM')
        d.yeniden_kur(); self.assertEqual(d.gorevler[o]['zaman_degeri'],6)

    def test_C30_gorev_on_kosul_dongusu(self):
        """C30 TASARIM T3 §3/A6: sabit noktaya ulaşan döngü yine de işi kilitler."""
        f=Duzenek(); d=f.calistir(t(22,'09:00')); f.gorev_ata(t(22,'09:00'),satirlar=[f.gorev_satiri(on_kosul=[{'satir':2}]),f.gorev_satiri(on_kosul=[{'satir':1}])])
        self.assertEqual(yaz(d,f.olaylar[-1]).get('kod'),'DURUM')

    def test_bayat_siralama_ve_devir(self):
        f=Duzenek(); f.ata(1); f.ata(2,sira=2); d=f.calistir(t(22,'09:00')); surum=d.isler[is_id(2)]['surum']
        f.olay('K009','IS.SIRALADIM',t(22,'09:00'),2,{'kisi':'K017','yeni_sira':1}); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        for kod,girdi in [('IS.SIRALADIM',{'kisi':'K017','yeni_sira':2}),('IS.DEVRETTIM',{'kimden':'K017','kime':'K023'})]:
            f.olay('K009',kod,t(22,'09:01'),2,girdi); e=f.olaylar[-1]; e['neyin_ustunde'][0]['surum']=surum; self.assertEqual(yaz(d,e,taze=False)['kod'],'BAYAT')

    def test_gecersiz_sayilan_taniklik_tekrar_gelir(self):
        f=s1(); h=next(e for e in f.olaylar if e['eylem_kodu']=='IS.MOLA_VERDIM'); d=f.calistir(t(22,'11:45')); isaret(f,h['olay_kimligi']); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI'); once=d.son_hal()
        self.assertTrue(d.olay_ekle(h,servis=True)['tekrar']); self.assertEqual(d.son_hal(),once)
        # İlk kez gelmeden işaretlemek FK/varlık kontrolüne takılır; kayıp olay sonra kabul edilir.
        isaret(f,'K017-2610229988-T'); self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'YETKI')

    def test_aktarimda_isaret_hedeften_once(self):
        f=s1(); h=next(e for e in f.olaylar if e['eylem_kodu']=='IS.MOLA_VERDIM'); isaret(f,h['olay_kimligi'])
        a=f.calistir(t(22,'11:45')); b=f.yeniden_hesapla(t(22,'11:45'),list(reversed(f.olaylar))); self.assertEqual(a.son_hal(),b.son_hal())

    def test_revizyon_iptali_ve_aslin_iptali(self):
        for asil_iptal in (False,True):
            f,g,r,o=revizyon_ornegi(); f.olaylar=[e for e in f.olaylar if an(e['oldugu_an'])<an(t(3,'12:00',11))]
            d=f.calistir(t(3,'12:00',11)); f.gorev_olay('IPTAL_ETTIM',t(3,'12:00',11),g if asil_iptal else r,'K012'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
            self.assertEqual(d.gorevler[r]['durum'],'IPTAL'); self.assertEqual(d.gorevler[g]['durum'],'IPTAL' if asil_iptal else 'REDDEDILDI')

    def test_alt_is_devri_gecersiz_bitis_habersiz(self):
        f,g=iki_kisi(); f.olaylar=[e for e in f.olaylar if an(e['oldugu_an'])<an(t(22,'09:00'))]; d=f.calistir(t(22,'09:00'))
        f.is_olay('DEVRETTIM','09:00',g+'/k1','K009',kimden='K017',kime='K009'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        bit=f.is_olay('TAMAMLADIM','09:01',g+'/k1'); d.ilerlet(t(22,'09:02')); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.isler[g+'/k1']['durum'],'ONAY_BEKLIYOR'); self.assertNotEqual(d.isler[g]['durum'],'BITTI')
        isaret(f,bit,zaman=t(22,'09:02')); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI'); self.assertNotEqual(d.isler[g+'/k1']['durum'],'BITTI')

    def test_ay_sinirinda_onay_ve_kapanis_sonrasi_gec_olay(self):
        f=Duzenek(); f.ata(9,zaman=t(30,'07:00')); f.is_olay('MESAI.GIRDIM','07:58',gun=30); f.is_olay('BASLADIM','16:00',9,gun=30); f.is_olay('TAMAMLADIM','17:30',9,gun=30)
        d=f.calistir(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01'); once=deepcopy(d.ay_kapanislari)
        f.is_olay('MOLA_VERDIM','16:30',9,gun=30); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        d.ilerlet(t(2,'08:10',11)); f.is_olay('MESAI.GIRDIM','07:58',gun=2,ay=11); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.ay_kapanislari,once)

    def test_dunden_gec_ariza_bugunun_gun_basini_degistirir(self):
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','16:00',4); f.is_olay('MESAI.GIRDIM','07:58',gun=23)
        d=f.calistir(t(23,'08:10')); self.assertEqual(d.kisi_durumu['K017']['durum'],'CALISMIYOR')
        f.is_olay('ARIZA_BILDIRDIM','17:40',4,neden='ARIZA.MAKINE'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.kisi_durumu['K017']['durum'],'ARIZADA'); self.assertEqual(kisinin_gunu(d,'K017','2026-10-23')['kovalar'],{'BEKLEME_ARIZA':10})

    def test_onayli_basi_siralamak_ve_devretmek_reddedilir(self):
        f,d=onay_bekleyen()
        for kod,h,g in [('IS.SIRALADIM',9,{'kisi':'K017','yeni_sira':2}),('IS.SIRALADIM',2,{'kisi':'K017','yeni_sira':1}),('IS.DEVRETTIM',9,{'kimden':'K017','kime':'K023'})]:
            f.olay('K009',kod,t(22,'09:10'),h,g); self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'DURUM')

    def test_odunc_atama_adina_birim_basi(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); f.ata(4,'K041',zaman=t(22,'08:00')); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        f.olay('K009','IS.BASLADIM',t(22,'09:00'),4,adina='K041'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        f.olay('K012','IS.BASLADIM',t(22,'09:00'),4,adina='K041'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')  # sabit iliski zinciri, karar 60
        f.olay('K001','BIRIM.TANIMLADIM',t(22,'09:00'),girdiler={'kod':'MEK_TASARIM','ad':'MEK','tur':'MASA_BASI','basi':'K041'}); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        f.olay('K012','AYAR.YONLENDIRDIM',t(22,'09:00'),girdiler={'birim':'MEK_TASARIM','kisiler':['K012']}); self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'YETKI')

    def test_onaylayan_degisiminde_yeni_gorev(self):
        f=Duzenek(); g=f.gorev_ata(zaman_degeri=20,onay_gerekli=True,onaylayan='K012'); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),g); o=f.gorev_olay('TAMAMLADIM',t(22,'09:00'),g); d=f.calistir(t(22,'09:10'))
        e=f.gorev_olay('DEGISTIRDIM',t(22,'09:10'),g,'K012',degisenler={'onaylayan':'K004'}); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.gorevler[o]['durum'],'IPTAL'); self.assertEqual(d.gorevler[e+'/1']['kisi'],'K004'); self.assertEqual(d.gorevler[e+'/1']['durum'],'ACIK')
        d.ilerlet(t(22,'09:11'))
        f.gorev_olay('ONAYLADIM',t(22,'09:11'),g,'K004'); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.gorevler[o]['durum'],'IPTAL'); self.assertEqual(d.gorevler[e+'/1']['durum'],'BITTI')

    def test_iki_farkli_lider_es_zamanli_atama(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        f=Duzenek(); f.olay('K001','KISI.DEGISTIRDIM',t(22,'08:00'),girdiler={'kisi':'K023','degisenler':{'roller':['EKIP_LIDERI']},'gecerli_baslangic':'2026-10-22'})
        d=f.calistir(t(22,'09:00')); surum=d.isler[is_id(5)]['surum']; esik=Barrier(2); olaylar=[]
        for kim,kisi in [('K009','K017'),('K023','K023')]:
            f.olay(kim,'IS.ATADIM',t(22,'09:00'),5,{'kisi':kisi,'sira':1}); e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=surum; olaylar.append(e)
        def gonder(e): esik.wait(); return yaz(d,e,taze=False)
        with ThreadPoolExecutor(max_workers=2) as h: sonuclar=list(h.map(gonder,olaylar))
        self.assertEqual(sum(x['sonuc']=='BASARILI' for x in sonuclar),1); self.assertEqual(sum(x.get('kod')=='BAYAT' for x in sonuclar),1)
        self.assertEqual(sum(is_id(5) in l for l in d.listeler.values()),1)

    def test_isleme_hatasi_kaynakta_kalir(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); f.is_olay('MESAI.GIRDIM','08:00')
        once=d.olay_isle
        def bozuk(e): raise RuntimeError('Deneme')
        d.olay_isle=bozuk; e=f.olaylar[-1]; self.assertEqual(yaz(d,e)['sonuc'],'BASARILI'); self.assertIn(e['olay_kimligi'],d.olaylar)
        d.olay_isle=once; d.yeniden_isle(e['olay_kimligi']); self.assertTrue(d.isleme_hatalari[-1]['cozuldu'])

    def test_C31_yeniden_kurmada_surum_aba(self):
        """C31 TASARIM T2 §0/T5 yeniden_kur: üç kaynak sürüm tarihçesini taşımıyor."""
        f=Duzenek(); g=f.gorev_ata(); d=f.calistir(t(22,'09:00')); eski=d.gorevler[g]['surum']
        f.gorev_olay('DEGISTIRDIM',t(22,'09:00'),g,'K012',degisenler={'ad':'Degisti'}); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        yeni=Depo(Saat(t(22,'09:00'))); yeni._kayitlar=deepcopy(d._kayitlar); yeni._olaylar=deepcopy(d._olaylar); yeni._icerikler=deepcopy(d._icerikler)
        yeni.hassas_ekler=deepcopy(d.hassas_ekler); yeni.ay_kapanislari=deepcopy(d.ay_kapanislari); yeni.yeniden_kur()
        self.assertNotEqual(yeni.gorevler[g]['surum'],eski)

    def test_elli_turda_islenemedi_kismi_sonuc_yayinlanmaz(self):
        from unittest.mock import patch
        from irp.motor import Motor
        f=Duzenek(); d=f.calistir(t(22,'09:00')); once=d.son_hal(); f.is_olay('MESAI.GIRDIM','08:00')
        asil=Motor.yurut
        def yakinsemeyen(m,olaylar):
            asil(m,olaylar); m.islenemedi=True; m.yakinsama_turlari=[50]; m.motor_hatalari=[{'hata':'yakinsamadi'}]
        with patch.object(Motor,'yurut',yakinsemeyen): self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertIn(f.olaylar[-1]['olay_kimligi'],d.olaylar); self.assertEqual(d.son_hal(),once); self.assertTrue(d.isleme_hatalari[-1]['islenemedi'])
