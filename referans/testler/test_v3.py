"""Sürüm 3: Y29–Y43, I51–I55 ve karar 38–49 sınırları.

Ortak tarihsel kurulum servis aktarımıdır. Her kabul/red denemesi canlı yoldadır.
Beklenen hata yalnız karşı örneğin son doğrulamasında oluşmalıdır.
"""
import unittest
from copy import deepcopy
from datetime import timedelta
from irp import Depo, Saat, an
from irp.cihaz import Cihaz
from irp.kisi_gunu import kapi
from irp.kapilar_v3 import dongusuz
from irp.surum import liste_surumu
from irp.gorunumler import gorev_payi, kisinin_gunu, maas_dagilimi, iscilik_maliyeti
from irp.is_ import emek
from irp.zaman import ay_kapanisi
from irp.hesap_yetkisi import kullanici_ac, sifre_sifirla
from .ortak import Duzenek, t, is_id, yaz, s1
from .degismezler_v2 import onay_bekleyen
from .tur2_ornekler import iki_kisi


def gonder(f,d,kim,kod,zaman,hedef=None,girdiler=None,**alan):
    if an(zaman)>d.saat.simdi(): d.ilerlet(zaman)
    k=f.olay(kim,kod,zaman,hedef,girdiler,**alan)
    return k,yaz(d,f.olaylar[-1])

def eski_teslim():
    f=Duzenek(); g=f.gorev_ata(t(26,'09:00'),ad='Montaj resmi seti',zaman_degeri=20,zorluk=3,teslim_tarihi='2026-10-30')
    f.gorev_olay('KABUL_ETTIM',t(26,'09:30'),g)
    d=f.calistir(t(28,'09:00'))
    deg,son=gonder(f,d,'K012','GOREV.DEGISTIRDIM',t(28,'09:00'),g,{'degisenler':{'kisi':'K044'}})
    assert son['sonuc']=='BASARILI',son
    kab,son=gonder(f,d,'K044','GOREV.KABUL_ETTIM',t(28,'10:00'),g)
    assert son['sonuc']=='BASARILI',son
    d.ilerlet(t(28,'12:00'))
    bit,son=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(27,'16:00'),g)
    assert son['sonuc']=='BASARILI',son
    return f,d,g,deg,kab,bit

def elle_ornegi(sonra_basla=False,onay=False):
    f=Duzenek(); hedef=9 if onay else 4; f.ata(hedef); f.ata(5,sira=2)
    f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',hedef)
    f.is_olay('MESAI.GIRDIM','07:58',gun=23)
    if sonra_basla: f.is_olay('BASLADIM','08:05',hedef,gun=23)
    d=f.calistir(t(23,'08:30'))
    e,s=gonder(f,d,'K009','IS.SURE_EKLEDIM',t(23,'08:30'),hedef,{'baslangic':t(22,'09:00'),'bitis':t(22,'17:00'),'aciklama':'Telefon kapandi','is_bitti':True},adina='K017',giris_sekli='ELLE')
    return f,d,e,s,hedef

def surumler(d):
    return {ad:{k:v['surum'] for k,v in getattr(d,ad).items()} for ad in ('isler','gorevler','kisiler','birimler','etaplar','projeler','notlar','tezgahlar','kisi_durumu','supheliler','sonuclar','bekletmeler','dosyalar')}


class SenaryolarV3(unittest.TestCase):
    def test_Y29a(self):
        c=Cihaz('K017','T',Saat(t(22,'09:00')))
        ids=[c.olay_kimligi_uret() for _ in range(5)]
        c.saat.ilerlet(t(23,'09:00')); c.sayaci_esitle(Depo(c.saat))
        ids += [c.olay_kimligi_uret() for _ in range(2)]
        c.veri['fark_saniye']=-86400
        yeni=c.olay_kimligi_uret()
        self.assertEqual(yeni,'K017-2610220006-T'); self.assertNotIn(yeni,ids)

    def test_Y29b(self):
        c=Cihaz('K017','T',Saat(t(22))); harfler={'T'}; c.olay_kimligi_uret(); c.depo_kayboldu()
        with self.assertRaises(ConnectionError): c.olay_kimligi_uret()
        with self.assertRaises(ConnectionError): c.yeniden_kaydol(harfler,False)
        self.assertEqual(c.yeniden_kaydol(harfler),'U'); self.assertTrue(c.olay_kimligi_uret().endswith('-U'))
        c.depo_kayboldu(); self.assertEqual(c.yeniden_kaydol(harfler),'V')

    def test_Y30(self):
        f,d,g,deg,kab,bit=eski_teslim()
        self.assertEqual((d.gorevler[g]['durum'],d.gorevler[g]['kisi'],d.gorevler[g]['is_puani']),('BITTI','K041',60))
        self.assertEqual(d.gorevler[g]['bitis_ani'],t(27,'16:00'))
        self.assertTrue({deg,kab}.issubset(d.supheliler)); self.assertNotIn(bit,d.supheliler)
        self.assertEqual(maas_dagilimi(d,'K041','2026-10-01')['toplam_saat'],20)
        self.assertEqual(maas_dagilimi(d,'K044','2026-10-01')['toplam_saat'],0)

    def test_Y31a(self):
        f,d=onay_bekleyen(); e,s=gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'09:30'),9)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertIn(e,d.supheliler)
        self.assertEqual(d.isler[is_id(9)]['durum'],'ONAY_BEKLIYOR')
        _,s=gonder(f,d,'K009','IS.ONAYLADIM',t(22,'10:30'),9)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.isler[is_id(9)]['durum'],'BITTI')

    def test_Y31b(self):
        f=Duzenek(); f.ata(9); f.ata(5,sira=2); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('DEVAM_ETTIM','10:15',9)
        d=f.calistir(t(22,'11:00'))
        _,s=gonder(f,d,'K009','IS.SIRALADIM',t(22,'11:00'),5,{'kisi':'K017','yeni_sira':1}); self.assertEqual(s['sonuc'],'BASARILI')
        once=emek(d,is_id(9)); e,s=gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'11:40'),9)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.isler[is_id(9)]['durum'],'ONAY_BEKLIYOR')
        self.assertEqual(emek(d,is_id(9)),once); self.assertIn(e,d.supheliler)

    def test_Y32a(self):
        f=Duzenek(); g=f.gorev_ata(); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),g); f.gorev_olay('TAMAMLADIM',t(22,'09:40'),g)
        d=f.calistir(t(22,'10:00')); e,s=gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(22,'10:00'),g)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual((d.gorevler[g]['durum'],d.gorevler[g]['is_puani']),('BITTI',2)); self.assertIn(e,d.supheliler)

    def test_Y32b(self):
        f=Duzenek(); g=f.gorev_ata(); f.gorev_olay('IPTAL_ETTIM',t(22,'09:00'),g,'K012'); d=f.calistir(t(22,'10:00'))
        e,s=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(22,'10:00'),g)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.gorevler[g]['durum'],'IPTAL'); self.assertIn(e,d.supheliler)

    def test_Y32c(self):
        f=Duzenek(); g=f.gorev_ata(); d=f.calistir(t(22,'10:00'))
        e,s=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(22,'10:00'),g)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.gorevler[g]['durum'],'BITTI'); self.assertEqual(d.gorevler[g]['kabul_ani'],t(22,'10:00'))

    def test_Y33a(self):
        f,d,e,s,h=elle_ornegi(); self.assertEqual(s['sonuc'],'BASARILI')
        self.assertEqual(emek(d,is_id(h)),480); self.assertEqual(d.isler[is_id(h)]['bitis_ani'],an(t(22,'17:00')))
        self.assertEqual(d.listeler['K017'][0],is_id(5))
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar'],{'CALISMA':480,'SABIT_MOLA':60,'TANIMSIZ':60})
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-23')['kovalar'],{'TANIMSIZ':30})
        elle=[(a['baslangic'].strftime('%H:%M'),a['bitis'].strftime('%H:%M')) for a in d.araliklar if a['elle']]
        self.assertEqual(elle,[('10:15','12:00'),('12:30','15:00'),('15:15','17:00')])

    def test_Y33b(self):
        f,d,e,s,h=elle_ornegi(True); self.assertEqual(s.get('kod'),'DURUM'); self.assertNotIn(e,d.olaylar)
        self.assertEqual(d.listeler['K017'][0],is_id(h))

    def test_Y34(self):
        denemeler=[('IS.ATADIM',5,{'kisi':'K017','sira':1},False),('IS.ATADIM',5,{'kisi':'K017','sira':2},True),('IS.DEVRETTIM',2,{'kimden':'K023','kime':'K017'},False),('IS.DEVRETTIM',2,{'kimden':'K023','kime':'K017','kime_sira':1},False),('IS.DEVRETTIM',2,{'kimden':'K023','kime':'K017','kime_sira':2},True),('IS.PLANSIZ_TANIMLADIM',None,{'kisi':'K017','sira':1,'nereye':'PROJE','proje':'2509084','is_tanimi':'Acil','tur':'SURELI','onay_gerekli':False},False),('IS.SIRALADIM',9,{'kisi':'K017','yeni_sira':2},False)]
        for kod,h,g,ok in denemeler:
            with self.subTest(kod=kod,g=g):
                f=Duzenek(); f.ata(9); f.ata(2,'K023'); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9); d=f.calistir(t(22,'09:10'))
                _,s=gonder(f,d,'K009',kod,t(22,'09:10'),h,g)
                self.assertEqual(s['sonuc'] if ok else s.get('kod'),'BASARILI' if ok else 'DURUM'); self.assertEqual(d.listeler['K017'][0],is_id(9))

    def test_Y35(self):
        f=Duzenek(); g=f.gorev_ata(satirlar=[f.gorev_satiri(onay_gerekli=True,onaylayan='K012') for _ in range(2)]); ids=[g,g.rsplit('/',1)[0]+'/2']; d=f.calistir(t(22,'08:00'))
        _,s=gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(22,'08:00'),ids); self.assertEqual(s['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(22,'09:00'),ids); self.assertEqual(s.get('kod'),'BICIM')
        for x in ids:
            _,s=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(22,'09:00'),x); self.assertEqual(s['sonuc'],'BASARILI')
        self.assertEqual(len([x for x in d.gorevler.values() if x['tur']=='ONAY']),2)
        _,s=gonder(f,d,'K012','GOREV.ONAYLADIM',t(22,'09:30'),ids); self.assertEqual(s['sonuc'],'BASARILI')
        self.assertTrue(all(d.gorevler[x]['durum']=='BITTI' for x in ids))

    def test_Y36(self):
        for kisiler,ayrilmis in [(['K017','K017'],False),(['K017','K023'],True),(['K017','K999'],False),(['K017','K023'],False)]:
            f,g=iki_kisi(); f.olaylar=[e for e in f.olaylar if an(e['oldugu_an'])<=an(t(22,'08:00'))]; d=f.calistir(t(22,'08:01'))
            if ayrilmis:
                _,s=gonder(f,d,'K001','KISI.AYRILDI',t(22,'08:01'),girdiler={'kisi':'K023','ayrilis_tarihi':'2026-10-22'}); self.assertEqual(s['sonuc'],'BASARILI')
            _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'08:02'),g,{'kisiler':kisiler,'sira':1})
            ok=not ayrilmis and kisiler==['K017','K023']; self.assertEqual(s['sonuc'] if ok else s.get('kod'),'BASARILI' if ok else 'DURUM')

    def test_Y37_ayar(self):
        f=Duzenek(); g=f.gorev_ata(t(26,'08:00'),zaman_degeri=60,onay_gerekli=True,onaylayan='K012'); f.gorev_olay('KABUL_ETTIM',t(26,'08:30'),g); o=f.gorev_olay('TAMAMLADIM',t(26,'09:00'),g)
        g2=f.gorev_ata(t(26,'08:01'),zaman_degeri=60,onay_gerekli=True,onaylayan='K012'); f.gorev_olay('KABUL_ETTIM',t(26,'08:31'),g2); d=f.calistir(t(26,'10:00'))
        _,s=gonder(f,d,'K001','AYAR.ONAY_ORANI',t(26,'10:00'),girdiler={'deger':.2,'gecerli_baslangic':t(26,'00:00')}); self.assertEqual(s.get('kod'),'DURUM')
        _,s=gonder(f,d,'K001','AYAR.ONAY_ORANI',t(26,'10:00'),girdiler={'deger':.2}); self.assertEqual(s['sonuc'],'BASARILI')
        o2,s=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(26,'11:00'),g2); self.assertEqual(s['sonuc'],'BASARILI')
        d.yeniden_kur(); self.assertEqual((d.gorevler[o]['zaman_degeri'],d.gorevler[o2]['zaman_degeri']),(6,12))

    def test_Y37_maas_takvim(self):
        f=Duzenek(); d=f.calistir(t(16,'09:00')); _,s=gonder(f,d,'K001','MAAS.GUNCELLEDIM',t(16,'09:00'),girdiler={'kisi':'K041','gecerli_baslangic':'2026-10-01'}); self.assertEqual(s['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K001','TATIL.EKLEDIM',t(26,'09:00'),girdiler={'tarih':'2026-10-23','ad':'Gec tatil'}); self.assertEqual(s.get('kod'),'DURUM')
        d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        _,s=gonder(f,d,'K001','MAAS.GUNCELLEDIM',t(3,'09:00',11),girdiler={'kisi':'K041','gecerli_baslangic':'2026-10-15'}); self.assertEqual(s.get('kod'),'DURUM')

    def test_Y38(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00'))
        for on in ([{'satir':1}],[{'satir':2}]):
            satirlar=[f.gorev_satiri(on_kosul=on),f.gorev_satiri(on_kosul=[{'satir':1}])]
            _,s=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),girdiler={'gorevler':satirlar}); self.assertEqual(s.get('kod'),'DURUM')
        kok,s=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:01'),girdiler={'gorevler':[f.gorev_satiri(),f.gorev_satiri(on_kosul=[{'satir':1}])]}); self.assertEqual(s['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K012','GOREV.DEGISTIRDIM',t(22,'09:02'),kok+'/1',{'degisenler':{'on_kosul':[kok+'/2']}}); self.assertEqual(s.get('kod'),'DURUM')
        _,s=gonder(f,d,'K004','IS.TANIMLADIM',t(22,'09:03'),girdiler={'isler':[{'birim':'IMALAT','on_isler':[{'satir':2}]},{'birim':'IMALAT','on_isler':[{'satir':1}]}]}); self.assertEqual(s.get('kod'),'DURUM')

    def test_Y39(self):
        f=Duzenek(); g=f.gorev_ata(); d=f.calistir(t(22,'09:00')); h1=d.gorevler[g]['surum']; ad=d.gorevler[g]['ad']
        _,s=gonder(f,d,'K012','GOREV.DEGISTIRDIM',t(22,'09:00'),g,{'degisenler':{'ad':'Yeni ad'}}); self.assertEqual(s['sonuc'],'BASARILI'); h2=d.gorevler[g]['surum']; self.assertNotEqual(h1,h2)
        for yeniden in (False,True):
            if yeniden:d.yeniden_kur()
            self.assertEqual(d.gorevler[g]['surum'],h2)
            f.gorev_olay('DEGISTIRDIM',t(22,'09:00'),g,'K012',degisenler={'ad':'Bayat'}); e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=h1
            self.assertEqual(yaz(d,e,taze=False).get('kod'),'BAYAT')
        _,s=gonder(f,d,'K012','GOREV.DEGISTIRDIM',t(22,'09:01'),g,{'degisenler':{'ad':ad}}); self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.gorevler[g]['surum'],h1)
        f.gorev_olay('DEGISTIRDIM',t(22,'09:01'),g,'K012',degisenler={'ad':'Tekrar'}); e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=h1
        self.assertEqual(yaz(d,e,taze=False)['sonuc'],'BASARILI')

    def test_Y40(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00'))
        for kim,ok in [('K004',True),('K012',False)]:
            _,s=gonder(f,d,kim,'IS.TANIMLADIM',t(22,'09:00'),girdiler={'isler':[{'birim':'IMALAT'}]}); self.assertEqual(s['sonuc'] if ok else s.get('kod'),'BASARILI' if ok else 'YETKI')
        with self.assertRaises(PermissionError): kullanici_ac(d,'K012','K041')
        with self.assertRaises(PermissionError): sifre_sifirla(d,'K012','K041')
        self.assertEqual(kullanici_ac(d,'K001','K041')['kisi'],'K041')
        for kim in ('K009','K023'):
            f,d=onay_bekleyen()
            for k,rol in [('K009',['CALISAN']),('K023',['EKIP_LIDERI'])]:
                _,s=gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:10'),girdiler={'kisi':k,'degisenler':{'roller':rol},'gecerli_baslangic':t(22,'09:10')}); self.assertEqual(s['sonuc'],'BASARILI')
            _,s=gonder(f,d,kim,'IS.ONAYLADIM',t(22,'09:11'),9); self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.isler[is_id(9)]['durum'],'BITTI')

    def test_Y41(self):
        f=Duzenek(); g=f.gorev_ata(zaman_degeri=20,onay_gerekli=True,onaylayan='K012'); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),g); o=f.gorev_olay('TAMAMLADIM',t(22,'09:00'),g); d=f.calistir(t(22,'09:10'))
        e,s=gonder(f,d,'K012','GOREV.DEGISTIRDIM',t(22,'09:10'),g,{'degisenler':{'onaylayan':'K001'}})
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.gorevler[o]['durum'],'IPTAL'); self.assertEqual(d.gorevler[e+'/1']['kisi'],'K001'); self.assertEqual(d.gorevler[e+'/1']['zaman_degeri'],2); self.assertEqual(d.gorevler[g]['durum'],'ONAY_BEKLIYOR')

    def test_Y42(self):
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('MESAI.GIRDIM','07:58',kisi='K023'); f.is_olay('BASLADIM','08:00',4); f.is_olay('ARIZA_BILDIRDIM','08:30',4,neden='ARIZA.MAKINE'); d=f.calistir(t(22,'09:00'))
        _,s=gonder(f,d,'K009','IS.DEVRETTIM',t(22,'09:00'),4,{'kimden':'K017','kime':'K023','kime_sira':1}); self.assertEqual(s['sonuc'],'BASARILI')
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar']['BEKLEME_ARIZA'],30); self.assertIsNone(d.isler[is_id(4)]['acik_ariza'])
        self.assertTrue(kapi(d.kisi_durumu['K023'],'IS.BASLADIM',d.isler[is_id(4)],is_id(4)))
        _,s=gonder(f,d,'K023','MESAI.GIRDIM',t(23,'07:58')); self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.kisi_durumu['K023']['durum'],'CALISMIYOR')

    def test_Y43(self):
        f=Duzenek(); f.ata(1); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',1); d=f.calistir(t(22,'12:40'))
        self.assertEqual(d.kisi_durumu['K017']['durum'],'DEVAM_BEKLIYOR'); self.assertTrue(kapi(d.kisi_durumu['K017'],'IS.DEVAM_ETTIM',d.isler[is_id(1)],is_id(1)))
        self.assertEqual(kisinin_gunu(d,'K017','2026-10-22')['kovalar']['TANIMSIZ'],115)


class KararKenarlariV3(unittest.TestCase):
    def test_K38_C32_altmis_gun_sonrasi_geri_saat(self):
        """C32: V4 A1 ve karar 51, eski sayaclari da saklar."""
        from irp.belge_okumalari_v4 import a1_sayaclari_koru as a1_altmis_gun_temizligi
        sayaclar=a1_altmis_gun_temizligi({'261022':1},an(t(22)).date()+timedelta(days=61))
        self.assertNotEqual(sayaclar.get('261022',0)+1,1)

    def test_K38_oncelik_kimlik_guvencesi(self):
        c=Cihaz('K017','T',Saat(t(22))); ilk=c.olay_kimligi_uret()
        c.saat.ilerlet(an(t(22))+timedelta(days=61)); c.sayaci_esitle(Depo(c.saat)); c.veri['fark_saniye']=-61*86400
        self.assertNotEqual(c.olay_kimligi_uret(),ilk)

    def test_K39_eski_adina_rol(self):
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); d=f.calistir(t(22,'09:00'))
        _,s=gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:00'),girdiler={'kisi':'K009','degisenler':{'roller':['CALISAN']},'gecerli_baslangic':t(22,'09:00')}); self.assertEqual(s['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K009','IS.BASLADIM',t(22,'08:00'),4,adina='K017'); self.assertEqual(s['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K009','IS.MOLA_VERDIM',t(22,'09:01'),4,adina='K017'); self.assertEqual(s['sonuc'],'BASARILI')  # karar 60: birim basi kaldi

    def test_K40_I56_C33_molada_onayli_bitis(self):
        """C33/I56: sabit mola sonrasi onay bekleme durumu ve suresi."""
        f=Duzenek(); f.ata(9); f.ata(5,sira=2); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); d=f.calistir(t(22,'10:05'))
        e,s=gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'10:05'),9); self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.isler[is_id(9)]['durum'],'ONAY_BEKLIYOR'); self.assertIn(e,d.supheliler)
        d.ilerlet(t(22,'10:20'))
        self.assertEqual((d.kisi_durumu['K017']['durum'],kisinin_gunu(d,'K017','2026-10-22')['kovalar'].get('BEKLEME_ONAY',0)),('ONAY_BEKLIYOR',5))

    def test_K41_onkosul_bekleyen_teslim_etkisiz(self):
        f=Duzenek(); a=f.gorev_ata(); b=f.gorev_ata(t(21,'17:41'),on_kosul=[a]); f.gorev_olay('KABUL_ETTIM',t(22,'08:00'),b); d=f.calistir(t(22,'09:00'))
        e,s=gonder(f,d,'K041','GOREV.TAMAMLADIM',t(22,'09:00'),b); self.assertEqual(s['sonuc'],'BASARILI'); self.assertIn(e,d.supheliler); self.assertEqual(d.gorevler[b]['durum'],'ON_IS_BEKLIYOR')

    def test_K42_onayli_elle_bitis_bas_kalir(self):
        f,d,e,s,h=elle_ornegi(onay=True); self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.isler[is_id(h)]['durum'],'ONAY_BEKLIYOR'); self.assertEqual(d.listeler['K017'][0],is_id(h)); self.assertEqual(d.kisi_durumu['K017']['durum'],'ONAY_BEKLIYOR')

    def test_K43_cok_kisi_ve_liste_surumu(self):
        f,d=onay_bekleyen(); g=f.olay('K004','IS.TANIMLADIM',t(22,'09:10'),girdiler={'isler':[{'birim':'IMALAT','kisi_sayisi':2}]}); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'09:10'),g,{'kisiler':['K017','K023'],'sira':1}); self.assertEqual(s.get('kod'),'DURUM')
        h=liste_surumu(d,'K017'); _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'09:10'),5,{'kisi':'K017','sira':2}); self.assertEqual(s['sonuc'],'BASARILI')
        f.ata(6,sira=3,zaman=t(22,'09:10')); e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=d.isler[is_id(6)]['surum']; e['neyin_ustunde'].append({'tur':'LISTE','kimlik':'K017','surum':h})
        self.assertEqual(yaz(d,e,taze=False).get('kod'),'BAYAT')

    def test_K44_diger_tek_hedefler(self):
        f=Duzenek(); g=f.gorev_ata(satirlar=[f.gorev_satiri(),f.gorev_satiri()]); d=f.calistir(t(22,'09:00')); ids=[g,g.rsplit('/',1)[0]+'/2']
        for kod,gi in [('GOREV.REDDETTIM',{'not':'Ret','sebep_olan':'K041','revizyon_ver':False}),('GOREV.DEGISTIRDIM',{'degisenler':{'ad':'Yeni'}}),('GOREV.IPTAL_ETTIM',{})]:
            _,s=gonder(f,d,'K012',kod,t(22,'09:00'),ids,gi); self.assertEqual(s.get('kod'),'BICIM')

    def test_K43_cihaz_gordugu_liste_surumunu_tasir(self):
        from irp.kisi_gunu import bos_hal
        f=Duzenek(); d=f.calistir(t(22,'09:00')); c=Cihaz('K009','M',Saat(t(22,'09:00')))
        h=dict(bos_hal(),son_hesap_ani=t(22,'09:00'),liste_surumleri={'K017':liste_surumu(d,'K017')})
        a=c.olay_yaz('IS.ATADIM',h,d.isler,[],is_id(5),{'kisi':'K017','sira':1},depo=d)
        self.assertEqual(c.veri['gunluk'][a['olay_kimligi']]['durum'],'GONDERILDI')
        b=c.olay_yaz('IS.ATADIM',h,d.isler,[],is_id(6),{'kisi':'K017','sira':2},depo=d)
        self.assertEqual(c.veri['gunluk'][b['olay_kimligi']]['sonuc'].get('kod'),'BAYAT')
        self.assertNotIn(b['olay_kimligi'],d.olaylar)

    def test_K45_eksik_kisi_sayisi(self):
        f,g=iki_kisi(); f.olaylar=[e for e in f.olaylar if an(e['oldugu_an'])<=an(t(22,'08:00'))]; d=f.calistir(t(22,'08:01'))
        _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'08:01'),g,{'kisiler':['K017'],'sira':1}); self.assertEqual(s.get('kod'),'DURUM')

    def test_K46_I53_C34_gelecek_tatil_eski_payi(self):
        """I53 karar 50: acik ayin gecmis payi degisir, gorev toplami korunur."""
        f=Duzenek(); g=f.gorev_ata(t(26,'08:00'),zaman_degeri=20,teslim_tarihi='2026-10-30'); f.gorev_olay('KABUL_ETTIM',t(26,'08:30'),g); d=f.calistir(t(26,'10:00'))
        once=gorev_payi(d,d.gorevler[g],'2026-10-26','2026-10-26'); self.assertEqual(once,5)
        _,s=gonder(f,d,'K001','TATIL.EKLEDIM',t(26,'10:00'),girdiler={'tarih':'2026-10-30','ad':'Yeni tatil','gecerli_baslangic':t(26,'10:00')}); self.assertEqual(s['sonuc'],'BASARILI')
        d.yeniden_kur(); self.assertAlmostEqual(gorev_payi(d,d.gorevler[g],'2026-10-26','2026-10-26'),20/3)
        self.assertAlmostEqual(gorev_payi(d,d.gorevler[g],'2026-10-26','2026-10-30'),20)

    def test_K47_olmayan_onkosul(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00')); _,s=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),girdiler={'gorevler':[f.gorev_satiri(on_kosul=['yok'])]}); self.assertEqual(s.get('kod'),'DURUM')

    def test_K48_hesap_zamani_surumu_degistirmez(self):
        f=Duzenek(); g=f.gorev_ata(); d=f.calistir(t(22,'09:00')); h=d.gorevler[g]['surum']
        d.ilerlet(t(22,'09:01')); self.assertEqual(d.gorevler[g]['surum'],h)

    def test_K49_bilinmeyen_hedef_ve_kapali_ay(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00'))
        _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'09:00'),'yok',{'kisi':'K017','sira':1})
        self.assertIn(s.get('kod'),('YETKI','DURUM'))
        d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        with self.assertRaises(ValueError): iscilik_maliyeti(d,'2509084','2026-10-22','2026-10-22')

    def test_E14_anlik_tamamla(self):
        f=Duzenek(); f.ata(8); f.is_olay('MESAI.GIRDIM','07:58'); d=f.calistir(t(22,'09:00')); e,s=gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'09:00'),8)
        self.assertEqual(s['sonuc'],'BASARILI'); self.assertEqual(d.isler[is_id(8)]['durum'],'BITTI'); self.assertNotIn(e,d.supheliler); self.assertEqual(emek(d,is_id(8)),0)


class DegismezlerV3(unittest.TestCase):
    def test_I51(self):
        f,d=onay_bekleyen()
        for sira in (1,2,3):
            _,s=gonder(f,d,'K009','IS.ATADIM',t(22,'09:10'),4+sira,{'kisi':'K017','sira':sira})
            self.assertEqual(s['sonuc'] if sira>1 else s.get('kod'),'BASARILI' if sira>1 else 'DURUM'); self.assertEqual(d.listeler['K017'][0],is_id(9))

    def test_I52(self):
        f,d,g,deg,kab,bit=eski_teslim(); self.assertIn(bit,d.olaylar); self.assertEqual(d.gorevler[g]['kisi'],'K041')
        once=d.son_hal(); d.yeniden_kur(); self.assertEqual(d.son_hal(),once)

    def test_I54(self):
        f=Duzenek(); d=f.calistir(t(22,'09:00'))
        for n in range(8):
            kok,s=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),girdiler={'gorevler':[f.gorev_satiri(on_kosul=[once] if n else [])]}); self.assertEqual(s['sonuc'],'BASARILI'); once=kok+'/1'
        graf={k:g.get('on_kosul',[]) for k,g in d.gorevler.items()}; self.assertTrue(dongusuz(graf))

    def test_I55(self):
        f,d,g,deg,kab,bit=eski_teslim(); bek=surumler(d)
        yeni=Depo(Saat(d.saat.simdi())); yeni._kayitlar=deepcopy(d._kayitlar); yeni._olaylar=deepcopy(d._olaylar); yeni._icerikler=deepcopy(d._icerikler); yeni.hassas_ekler=deepcopy(d.hassas_ekler); yeni.ay_kapanislari=deepcopy(d.ay_kapanislari); yeni.yeniden_kur()
        self.assertEqual(surumler(yeni),bek)
