"""Yalniz T9 sinirlari; tasarim bulgularinin yeniden uretimleri dahil."""
import unittest
from copy import deepcopy
from irp import an
from irp.gorunumler import adil_performans,iscilik_maliyeti
from irp.gorunum_v7 import gun_sonu_raporu,durum,kapasite
from irp.gorunum_v9 import proje_gorebilir_mi,gecikme_raporu,gun_isleri,okunmamis_bildirimler
from irp.degismezler_v9 import denetle
from .ortak import t,is_id,yaz
from .test_v7 import kur,gonder,parca_turu
from .test_v9 import duzenek,gec_duzenegi,degerlendir,pay,gun_duzenegi,onaylar,izin_duzenegi,durus_duzenegi


class KenarlarV9(unittest.TestCase):
    def test_gecersiz_durus_gecikme_raporuna_girmez(self):
        f,h=durus_duzenegi(); d=kur(f,t(22,'14:00'))
        gonder(f,d,'K017','KAYIT.GECERSIZ_SAYDIM',t(22,'14:01'),dict(hedef=h,gerekce='Yanlis tus'),duzelttigi_olay=h)
        self.assertEqual(gecikme_raporu(d,'2026-10-01','2026-10-31'),[])
        self.denetle(d)

    def test_birim_cumartesi_lider_elle_sure_yazabilir(self):
        f=duzenek(); f.ata(4)
        tak=dict(mesai_baslangic='08:00',mesai_bitis='12:00',gunler=[6],sabit_molalar=[])
        f.olay('K001','BIRIM.TANIMLADIM',t(21,'09:00'),girdiler=dict(kod='IMALAT',ad='IMALAT',tur='ATOLYE',basi='K009',ust_birim='PLANLAMA',takvim=tak,takvim_gecerli='2026-10-22'))
        f.olay('K017','MESAI.GIRDIM',t(24,'08:00'))
        d=kur(f,t(24,'11:00'))
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(24,'11:01'),dict(baslangic=t(24,'08:00'),bitis=t(24,'10:00'),aciklama='Eksik kayit',is_bitti=False),4,adina='K017')
        self.assertEqual(sum((a['bitis']-a['baslangic']).total_seconds()/60 for a in d.araliklar if a['kisi']=='K017' and a['elle']),120)
        from irp.cihaz import atama_uyarilari
        # Gecis haftasinda eski uc gun (27 saat) ve yeni cumartesi (4) vardir.
        self.assertTrue(any(x['kural']=='R23' for x in atama_uyarilari(d,[dict(kisi='K017',teslim_tarihi='2026-10-24',zaman_degeri=40)])))
        self.denetle(d)

    def test_not_dosya_butun_projeler_ve_pano_maskeleme(self):
        from irp.gorunum_v7 import oku
        f=duzenek()
        g=f.gorev_ata(t(22,'09:00'),proje='2509091',etap=None,zaman_degeri=8,teslim_tarihi='2026-10-23')
        f.gorev_olay('KABUL_ETTIM',t(22,'09:01'),g)
        h=[dict(tur='PROJE',kimlik=p,surum=None) for p in ('2509084','2509091')]
        n=f.olay('K001','NOT.YAZDIM',t(22,'09:02'),h,dict(metin='Iki proje',etiketler=[]),kanit=[dict(dosya_kimligi='F-T9',ad='not.txt',tur='text/plain',boyut=10)])
        f.olay('K001','AYAR.DEGISTIRDIM',t(22,'09:03'),girdiler=dict(anahtar='proje_gorunurlugu',deger='UYELER'))
        d=kur(f,t(23,'18:00'))
        self.assertTrue(proje_gorebilir_mi(d,'K009','2509084'))
        self.assertFalse(proje_gorebilir_mi(d,'K009','2509091'))
        for tur,hedef in [('PROJE','2509091'),('PLAN','2509091'),('NOT',n),('DOSYA','F-T9')]:
            with self.assertRaises(PermissionError): oku(d,'K009',tur,hedef)
        pano=oku(d,'K009','SAAT_NEREYE_GITTI',bas='2026-10-22',bit='2026-10-23')
        self.assertEqual(pano['MEK_TASARIM']['erişim dışı proje'],8)
        self.assertNotIn('2509091',pano['MEK_TASARIM'])
        self.assertEqual(oku(d,'K001','NOT',n)['metin'],'Iki proje')
        self.denetle(d)

    def test_eski_ekip_liderinin_uyeligi_kalir(self):
        f=duzenek()
        for z,roller in [('09:00',['CALISAN','EKIP_LIDERI']),('10:00',['CALISAN'])]:
            f.olay('K001','KISI.DEGISTIRDIM',t(21,z),girdiler=dict(kisi='K023',gecerli_baslangic=t(21,z),degisenler=dict(roller=roller),gerekce='Gorev degisikligi'))
        f.olay('K001','AYAR.DEGISTIRDIM',t(21,'11:00'),girdiler=dict(anahtar='proje_gorunurlugu',deger='UYELER'))
        d=kur(f,t(22,'09:00'))
        self.assertTrue(proje_gorebilir_mi(d,'K023','2509084'))
        self.denetle(d)

    def test_neden_basligi_alt_nedene_cevrilip_uc_katman_yaratamaz(self):
        f=duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','KOD.TANIMLADIM',t(22,'09:01'),dict(liste='DURUS_NEDENI',kod='MALZEME',ad='Malzeme',ust='CALISAN',aktif=True),bek='DURUM')
        self.assertIsNone(d.kod_listesi['DURUS_NEDENI:MALZEME']['ust'])
        self.denetle(d)

    def denetle(self,d):
        s=denetle(d,True); self.assertTrue(all(s.values()),s)
        from irp.degismezler_v5 import denetle as d5
        from irp.degismezler_v6 import denetle as d6
        from irp.degismezler_v7 import denetle as d7
        s=dict(d5(d),**d6(d),**d7(d,True)); self.assertTrue(all(s.values()),s)

    def test_degerlendirme_itiraz_dogrulama_sirasi(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05'))
        ev=degerlendir(f,d,g,[pay('K041',50),pay('K044',50)])
        gonder(f,d,'K041','SORUMLULUK.ITIRAZ_ETTIM',t(26,'11:10'),dict(hedef=ev,satir=1,gerekce='Itiraz'))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],.5)
        gonder(f,d,'K012','SORUMLULUK.DOGRULADIM',t(26,'11:11'),dict(hedef=ev,satir=1,karar='ONAY',gerekce='Dogrula'))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],.5)
        gonder(f,d,'K012','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(26,'11:12'),dict(hedef=ev,satir=1,karar='RET',gerekce='Incelendi'))
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],.5)
        self.denetle(d)

    def test_B46_kaldirilan_pay_teslim_edene_doner(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05')); ev=degerlendir(f,d,g,[pay('K041',50),pay('K044',50)])
        it=gonder(f,d,'K044','SORUMLULUK.ITIRAZ_ETTIM',t(26,'11:30'),dict(hedef=ev,satir=2,gerekce='Itiraz'))
        gonder(f,d,'K012','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(26,'11:40'),dict(hedef=it,karar='KABUL',gerekce='Hakli'))
        self.assertEqual(sum(x['yuzde'] for x in d.sorumluluklar.values() if x['ret']==ev),50)
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],0)
        self.assertFalse(adil_performans(d,'K041','2026-10-01','2026-10-31')['kesinlesmedi'])
        self.denetle(d)

    def test_B47_gizli_projeye_yazma_uyelik_kazandiramaz(self):
        f=duzenek(); f.olay('K001','AYAR.DEGISTIRDIM',t(1,'07:12'),girdiler=dict(anahtar='proje_gorunurlugu',deger='UYELER'))
        d=kur(f,t(22,'08:50')); self.assertFalse(proje_gorebilir_mi(d,'K009','2509091'))
        gonder(f,d,'K009','GOREV.ATADIM',t(22,'09:00'),dict(gorevler=[f.gorev_satiri(proje='2509091',etap=None)]),bek='YETKI')
        self.assertFalse(proje_gorebilir_mi(d,'K009','2509091'))
        self.denetle(d)

    def test_B48_dogrulanmamis_baska_pay_kredi_olmaz(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05')); ev=degerlendir(f,d,g,[pay('K052')])
        self.assertFalse(d.sorumluluklar[ev+'/1']['dogrulandi'])
        self.assertEqual(adil_performans(d,'K041','2026-10-01','2026-10-31')['zaman_orani'],0)
        self.assertTrue(adil_performans(d,'K041','2026-10-01','2026-10-31')['kesinlesmedi'])
        self.assertEqual(adil_performans(d,'K052','2026-10-01','2026-10-31')['sebep_olunan_gecikme'],0)
        self.denetle(d)

    def test_son_degerlendirme_eskisinin_payini_kaldirir(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05')); degerlendir(f,d,g,[pay('K044')])
        degerlendir(f,d,g,[pay('MUSTERI',tur='DIS')],zaman=t(26,'11:10'))
        self.assertEqual(len(d.gecikme_degerlendirmeleri),2)
        self.assertEqual(adil_performans(d,'K044','2026-10-01','2026-10-31')['sebep_olunan_gecikme'],0)
        self.denetle(d)

    def test_onay_degisti_isi_yeniden_acar(self):
        f,d=gun_duzenegi()
        gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'18:10'),dict(gunler=onaylar(d)))
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(23,'09:00'),dict(baslangic=t(22,'13:00'),bitis=t(22,'14:00'),aciklama='Eksik kayit',is_bitti=False),1,adina='K017')
        self.assertEqual(gun_sonu_raporu(d,'K017','2026-10-22')['durum'],'DEGISTI')
        self.assertTrue(any(x['gun']=='2026-10-22' and x['kisiler']==['K017'] for x in gun_isleri(d,'K009')))
        self.assertGreater(iscilik_maliyeti(d,'2509084','2026-10-01','2026-10-31')['onay_bekleyen'],0)
        self.denetle(d)

    def test_toplu_onay_bayat_satir_atomik(self):
        f,d=gun_duzenegi(); ss=onaylar(d); ss[1]['ozet_surumu']='eski'
        gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'18:10'),dict(gunler=ss),bek='DURUM')
        self.assertEqual(gun_sonu_raporu(d,'K017','2026-10-22')['durum'],'TASLAK')

    def test_kod_gecmisi_kapali_proje_ve_durum_t(self):
        f=duzenek(); d=kur(f,t(22,'08:50'))
        gonder(f,d,'K001','PROJE.KAPATTIM',t(22,'09:00'),h='2509091',tur='PROJE')
        gonder(f,d,'K001','PROJE.KOD_DEGISTIRDIM',t(22,'09:01'),dict(kod='YENI',gerekce='Duzeltme'),'2509091','PROJE')
        self.assertFalse(d.projeler['2509091']['aktif']); self.assertEqual(durum(d,t(22,'09:00')).projeler['2509091']['kod'],'2509091')
        gonder(f,d,'K001','PROJE.ACTIM',t(22,'09:02'),dict(kimlik='P-X',kod='2509091',ad='Deneme'),bek='DURUM')
        self.denetle(d)

    def test_nesne_kodu_gecmis_parca_eslesmesi(self):
        f=duzenek(); f.olay('K001','NESNE_TURU.TANIMLADIM',t(1,'07:12'),girdiler=parca_turu()); d=kur(f,t(22,'08:50'))
        kod=d.isler[is_id(1)]['parca_kodu']
        n=gonder(f,d,'K045','NESNE.ACTIM',t(22,'09:00'),dict(tur='PARCA',ad='Kaynak parcasi',kod=kod,sorumlu='K045',proje='2509084'))
        gonder(f,d,'K045','NESNE.GUNCELLEDIM',t(22,'09:01'),dict(hedef=n,degisenler=dict(kod='YENI-PARCA')))
        self.assertEqual(d.isler[is_id(1)]['nesne'],n)
        gonder(f,d,'K045','NESNE.ACTIM',t(22,'09:02'),dict(tur='PARCA',ad='Yeni',kod=kod,sorumlu='K045',proje='2509084'),bek='DURUM')
        self.denetle(d)

    def test_ileri_ik_rolu_kaybi_reddedilir(self):
        f,d,h=izin_duzenegi()
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'12:00'),dict(kisi='K007',degisenler=dict(roller=['YONETICI']),gecerli_baslangic=t(2,'00:00',11)),bek='DURUM')
        gonder(f,d,'K007','IZIN.REDDETTIM',t(22,'12:01'),dict(hedef=h,gerekce='Henuz ust onayi yok'),bek='YETKI')

    def test_gordum_sirasiz_ilk_an(self):
        f,h=durus_duzenegi(); d=kur(f,t(22,'13:29')); b=h+'/R07/K009'
        gonder(f,d,'K009','BILDIRIM.GORDUM',t(22,'13:35'),dict(bildirimler=[b]))
        f.olay('K009','BILDIRIM.GORDUM',t(22,'13:30'),girdiler=dict(bildirimler=[b]))
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(next(x['gorulme_ani'] for x in d.bildirimler.values() if x['kural']=='R07'),an(t(22,'13:30')))
        self.denetle(d)

    def test_gecersiz_bildirimi_gormek_etkisiz(self):
        f,h=durus_duzenegi(); d=kur(f,t(22,'13:29')); b=h+'/R07/K009'
        gonder(f,d,'K009','KAYIT.GECERSIZ_SAYDIM',t(22,'13:30'),dict(hedef=h,gerekce='Yanlis kayit'),duzelttigi_olay=h)
        gonder(f,d,'K009','BILDIRIM.GORDUM',t(22,'13:31'),dict(bildirimler=[b]))
        self.assertFalse(any(x['kural']=='R07' for x in okunmamis_bildirimler(d,'K009')))
        self.assertTrue(all(x.get('gorulme_ani') is None for x in d.bildirimler.values() if x['kural']=='R07'))
        self.denetle(d)

    def test_birim_takvimi_gecmisi_degistirmez_firma_gunu_ustundur(self):
        f=duzenek(); d=kur(f,t(21,'09:00')); b=dict(d.birimler['IMALAT']); b.pop('surum',None)
        tak=dict(mesai_baslangic='07:00',mesai_bitis='16:00',gunler=[1,2,3,4,5,6],sabit_molalar=[dict(ad='Mola',bas='12:00',bit='12:30')])
        gonder(f,d,'K001','BIRIM.TANIMLADIM',t(21,'10:00'),dict(b,takvim=tak,takvim_gecerli='2026-10-22'))
        gonder(f,d,'K001','GUN.TANIMLADIM',t(21,'10:01'),dict(tarih='2026-10-23',tur='YARIM_GUN',ad='Firma gunu',mesai_baslangic='08:00',mesai_bitis='12:00',sabit_molalar=[]))
        self.assertEqual(kapasite(d,'K017','2026-10-21','2026-10-21'),9)
        self.assertEqual(kapasite(d,'K017','2026-10-22','2026-10-22'),8.5)
        self.assertEqual(kapasite(d,'K017','2026-10-23','2026-10-23'),4)
        gonder(f,d,'K001','BIRIM.TANIMLADIM',t(23,'13:00'),dict(b,takvim=dict(tak,mesai_bitis='15:00'),takvim_gecerli='2026-10-24'))
        self.assertEqual(kapasite(d,'K017','2026-10-22','2026-10-22'),8.5)
        self.assertEqual(kapasite(d,'K017','2026-10-24','2026-10-24'),7.5)
        self.assertEqual(kapasite(durum(d,t(21,'09:59')),'K017','2026-10-22','2026-10-22'),9)
        self.denetle(d)

    def test_birim_cumartesi_gorev_ve_maliyet_izi(self):
        from irp.gorunumler import gorev_gunluk_paylar,kim_nerede
        from irp.maliyet_izi_v6 import maliyet_izleri
        f=duzenek(); d=kur(f,t(21,'09:00')); b=dict(d.birimler['MEK_TASARIM']); b.pop('surum',None)
        tak=dict(mesai_baslangic='08:00',mesai_bitis='12:00',gunler=[1,2,3,4,5,6],sabit_molalar=[])
        gonder(f,d,'K001','BIRIM.TANIMLADIM',t(21,'10:00'),dict(b,takvim=tak,takvim_gecerli='2026-10-22'))
        h=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),dict(gorevler=[f.gorev_satiri(zaman_degeri=12,teslim_tarihi='2026-10-24')]))+'/1'
        gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(22,'09:30'),h=h)
        paylar=gorev_gunluk_paylar(d,d.gorevler[h]); self.assertEqual([s['saat'] for s in paylar],[4,4,4])
        self.assertEqual(kim_nerede(d,'2026-10-24','2026-10-24')['K041:2026-10-24']['2509084'],4)
        iz=[x for x in maliyet_izleri(d,'2026-10-24','2026-10-24') if x['kimlik']==h]; self.assertEqual(iz[0]['emek_saat'],4)
        self.denetle(d)

    def test_uyelik_sorumlu_kisi_degisiminde_kalir(self):
        f=duzenek(); f.olay('K001','AYAR.DEGISTIRDIM',t(1,'07:12'),girdiler=dict(anahtar='proje_gorunurlugu',deger='UYELER')); d=kur(f,t(22,'08:50'))
        gonder(f,d,'K001','PROJE.DEGISTIRDIM',t(22,'09:00'),dict(degisenler=dict(sorumlu='K006')),'2509091','PROJE')
        gonder(f,d,'K001','PROJE.DEGISTIRDIM',t(22,'09:01'),dict(degisenler=dict(sorumlu='K045')),'2509091','PROJE')
        self.assertTrue(proje_gorebilir_mi(d,'K006','2509091')); self.assertTrue(proje_gorebilir_mi(d,'K045','2509091'))
        self.denetle(d)

    def test_ik_ayrilis_guvencesi(self):
        f=duzenek(); d=kur(f,t(22,'08:50'))
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:00'),dict(kisi='K052',degisenler=dict(roller=['BEYAZ_YAKA','IK']),gecerli_baslangic=t(22,'09:00')))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:01'),dict(anahtar='izin_ik_onayi',deger={'YILLIK':True}))
        gonder(f,d,'K001','KISI.AYRILDI',t(22,'09:02'),dict(kisi='K052',ayrilis_tarihi='2026-10-23'),bek='DURUM')
        self.denetle(d)

    def test_beyaz_yaka_onay_gonderim_ister(self):
        f=duzenek(); d=kur(f,t(22,'18:05')); r=gun_sonu_raporu(d,'K041','2026-10-22')
        gonder(f,d,'K012','GUN_SONU.ONAYLADIM',t(22,'18:10'),dict(kisi='K041',gun='2026-10-22',ozet_surumu=r['ozet_surumu']),bek='DURUM')
        gonder(f,d,'K041','GUN_SONU.GONDERDIM',t(22,'18:11'),dict(gun='2026-10-22'))
        gonder(f,d,'K012','GUN_SONU.ONAYLADIM',t(22,'18:12'),dict(kisi='K041',gun='2026-10-22',ozet_surumu=r['ozet_surumu']))
        self.assertEqual(gun_sonu_raporu(d,'K041','2026-10-22')['durum'],'ONAYLANDI'); self.denetle(d)
