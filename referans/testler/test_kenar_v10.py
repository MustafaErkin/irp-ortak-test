"""Karar 91–92 için tarih, yetki ve pay sınırları."""
import unittest
from copy import deepcopy
from irp import an
from irp.gorunum_v9 import proje_gorebilir_mi, gecikme_raporu
from irp.kurallar_v10 import projede_yetkili, etkin_pay, kredi
from .ortak import t, yaz, is_id
from .test_v7 import kur, gonder
from .test_v9 import degerlendir, pay, gec_duzenegi, durus_duzenegi
from .test_v10 import proje_duzenegi, gecikme_duzenegi, performans


class KenarlarV10(unittest.TestCase):
    def test_I106_I113_yetki_ve_kredi_kaynaklardan_denetlenir(self):
        from irp.degismezler_v10 import denetle
        f=proje_duzenegi();d=kur(f,t(22,'12:00'))
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:01'),dict(gorevler=[f.gorev_satiri()]))
        self.assertTrue(all(denetle(d,True).values()))
        f,d,g,ev=gecikme_duzenegi();d.ilerlet(t(30,'11:00'))
        self.assertTrue(all(denetle(d,True).values()))
        d.sorumluluklar[ev+'/1']['yuzde']=150
        self.assertFalse(denetle(d)['I108'])
        self.assertFalse(denetle(d)['I112'])

    def test_hata_sorumlulugu_sessiz_kabule_girmez(self):
        f,d,g,ev=gecikme_duzenegi();d.ilerlet(t(30,'11:00'))
        x=deepcopy(d.sorumluluklar[ev+'/1']);x.pop('kaynak_turu')
        self.assertFalse(etkin_pay(d,x))

    def test_ek_erisim_kalkinca_acik_is_tanikligi_surur_yeni_atama_reddedilir(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K012','PROJE.ERISIM_VERDIM',t(22,'12:01'),dict(proje='2509084',kisi='K044',gerekce='Destek'))
        g=gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:02'),dict(gorevler=[f.gorev_satiri(kisi='K044',etap=None)]))+'/1'
        gonder(f,d,'K012','PROJE.ERISIM_KALDIRDIM',t(22,'12:03'),dict(proje='2509084',kisi='K044',gerekce='Bitti'))
        gonder(f,d,'K044','GOREV.KABUL_ETTIM',t(22,'12:04'),h=g)
        gonder(f,d,'K044','GOREV.TAMAMLADIM',t(22,'12:05'),h=g)
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:06'),dict(gorevler=[f.gorev_satiri(kisi='K044',etap=None)]),bek='YETKI')
        self.assertTrue(proje_gorebilir_mi(d,'K044','2509084'))

    def test_cevrimdisi_taniklik_sonraki_erisim_degisiminden_etkilenmez(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        g=gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:01'),dict(gorevler=[f.gorev_satiri()]))+'/1'
        f.olay('K041','GOREV.KABUL_ETTIM',t(22,'12:02'),g)
        e=deepcopy(f.olaylar[-1]); d.ilerlet(t(23,'12:00'))
        self.assertEqual(yaz(d,e)['sonuc'],'BASARILI')
        self.assertEqual(d.gorevler[g]['kabul_ani'],t(22,'12:02'))

    def test_proje_sorumlusu_degisiminde_eski_kisi_gorur_yazamaz(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K001','PROJE.DEGISTIRDIM',t(22,'12:01'),dict(degisenler=dict(sorumlu='K007')),'2509091','PROJE')
        self.assertTrue(proje_gorebilir_mi(d,'K004','2509091'))
        self.assertFalse(projede_yetkili(d,'K004','2509091'))
        self.assertTrue(projede_yetkili(d,'K007','2509091'))
        gonder(f,d,'K004','PROJE.ERISIM_VERDIM',t(22,'12:02'),dict(proje='2509091',kisi='K006',gerekce='Eski sorumlu'),bek='YETKI')

    def test_etap_bitis_tarihi_birimi_cikarmaz(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K001','ETAP.DEGISTIRDIM',t(22,'12:01'),dict(degisenler=dict(bitis='2026-10-22')),f.etap['E-TAS'],'ETAP')
        d.ilerlet(t(23,'12:00'))
        self.assertTrue(projede_yetkili(d,'K012','2509084'))
        gonder(f,d,'K012','GOREV.ATADIM',t(23,'12:01'),dict(gorevler=[f.gorev_satiri(teslim_tarihi='2026-10-26')]))

    def test_servis_okumasi_yazma_ve_departman_uyeligini_miras_almaz(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K001','PROJE.ACTIM',t(22,'12:01'),dict(kimlik='SRV',kod='2509084',ek='Servis',ad='Servis',ana_proje='2509084'))
        self.assertTrue(proje_gorebilir_mi(d,'K017','SRV'))
        self.assertFalse(projede_yetkili(d,'K009','SRV'))
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:02'),dict(gorevler=[f.gorev_satiri(proje='SRV',etap=None)]),bek='YETKI')
        gonder(f,d,'K001','GOREV.ATADIM',t(22,'12:03'),dict(gorevler=[f.gorev_satiri(proje='SRV',etap=None)]),bek='YETKI')

    def test_ek_erisim_yonetim_yetkisi_vermez(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K012','PROJE.ERISIM_VERDIM',t(22,'12:01'),dict(proje='2509084',kisi='K007',gerekce='Inceleme'))
        self.assertTrue(proje_gorebilir_mi(d,'K007','2509084'))
        self.assertFalse(projede_yetkili(d,'K007','2509084'))
        gonder(f,d,'K007','GOREV.ATADIM',t(22,'12:02'),dict(gorevler=[f.gorev_satiri(kisi='K052')]),bek='YETKI')

    def test_toplu_atama_bir_yetkisiz_proje_ile_tamamen_reddedilir(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00')); once=set(d.gorevler)
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'12:01'),dict(gorevler=[f.gorev_satiri(),f.gorev_satiri(proje='2509091',etap=None)]),bek='YETKI')
        self.assertEqual(set(d.gorevler),once)

    def test_not_coklu_proje_kapisi(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        h=[dict(tur='PROJE',kimlik=p,surum=None) for p in ('2509084','2509091')]
        gonder(f,d,'K017','NOT.YAZDIM',t(22,'12:01'),dict(metin='Iki proje'),h,bek='YETKI')
        gonder(f,d,'K017','NOT.YAZDIM',t(22,'12:02'),dict(metin='Kendi projem'),h[:1])
        from irp.degismezler_v10 import denetle
        self.assertTrue(all(denetle(d,True).values()))

    def test_etap_sorumlusu_alan_yetkisi_ve_devri(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K001','ETAP.DEGISTIRDIM',t(22,'12:01'),dict(degisenler=dict(sorumlu='K007')),f.etap['E-TAS'],'ETAP')
        self.assertTrue(projede_yetkili(d,'K007','2509084'))
        gonder(f,d,'K001','ETAP.DEGISTIRDIM',t(22,'12:02'),dict(degisenler=dict(sorumlu='YOK')),f.etap['E-TAS'],'ETAP',bek='DURUM')
        gonder(f,d,'K001','ETAP.DEGISTIRDIM',t(22,'12:03'),dict(degisenler=dict(sorumlu=None)),f.etap['E-TAS'],'ETAP')
        self.assertFalse(projede_yetkili(d,'K007','2509084'))

    def test_gec_gelen_yonetim_olay_aninda_yetki_ister(self):
        f=proje_duzenegi(); d=kur(f,t(22,'12:00'))
        gonder(f,d,'K001','PROJE.DEGISTIRDIM',t(22,'12:02'),dict(degisenler=dict(sorumlu='K007')),'2509091','PROJE')
        f.olay('K007','PROJE.ERISIM_VERDIM',t(22,'12:01'),girdiler=dict(proje='2509091',kisi='K006',gerekce='Gec gelen'))
        self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'YETKI')

    def test_gec_gelen_itiraz_sessiz_kabulu_geri_hesaplar(self):
        f,d,g,ev=gecikme_duzenegi(); d.ilerlet(t(30,'11:00'))
        self.assertEqual(performans(d)['zaman_orani'],1)
        f.olay('K052','SORUMLULUK.ITIRAZ_ETTIM',t(27,'10:00'),girdiler=dict(hedef=ev,satir=1,gerekce='Sure icinde'))
        self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(performans(d)['zaman_orani'],0)
        self.assertTrue(performans(d)['kesinlesmedi'])

    def test_itiraz_suresi_dolsa_da_bekler(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K052','SORUMLULUK.ITIRAZ_ETTIM',t(27,'10:00'),dict(hedef=ev,satir=1,gerekce='Incelensin'))
        d.ilerlet(t(10,'11:00',11))
        self.assertFalse(etkin_pay(d,d.sorumluluklar[ev+'/1']))
        self.assertTrue(performans(d)['kesinlesmedi'])

    def test_itiraz_reddi_ustun_dogrulamasi_olur(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K052','SORUMLULUK.ITIRAZ_ETTIM',t(27,'10:00'),dict(hedef=ev,satir=1,gerekce='Incelensin'))
        gonder(f,d,'K007','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(27,'11:00'),dict(hedef=ev,satir=1,karar='RET',gerekce='Pay dogru'))
        self.assertEqual(performans(d)['zaman_orani'],1)
        self.assertFalse(performans(d)['kesinlesmedi'])

    def test_yeni_degerlendirme_eski_itirazin_sonucunu_tasiyamaz(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K052','SORUMLULUK.ITIRAZ_ETTIM',t(27,'10:00'),dict(hedef=ev,satir=1,gerekce='Incelensin'))
        degerlendir(f,d,g,[pay('MUSTERI',tur='DIS')],zaman=t(27,'10:30'))
        gonder(f,d,'K007','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(27,'11:00'),dict(hedef=ev,satir=1,karar='KABUL',gerekce='Eski degerlendirme'))
        self.assertEqual(performans(d)['zaman_orani'],1)
        self.assertFalse(performans(d)['kesinlesmedi'])

    def test_kaldirma_payini_teslim_edene_dondurur(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K007','SORUMLULUK.DOGRULADIM',t(27,'09:00'),dict(hedef=ev,satir=1,karar='KALDIR'))
        d.ilerlet(t(30,'11:00')); self.assertEqual(performans(d)['zaman_orani'],0)
        self.assertFalse(performans(d)['kesinlesmedi'])

    def test_karisik_dis_ve_onaysiz_pay(self):
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05'))
        degerlendir(f,d,g,[pay('MUSTERI',25,'DIS'),pay('K052',75)])
        self.assertEqual(performans(d)['zaman_orani'],.25)
        self.assertEqual(performans(d)['bekleyen_satir_sayisi'],1)

    def test_sessiz_kabul_sifir_ve_bicim(self):
        f,d,g,ev=gecikme_duzenegi()
        for i,v in enumerate([-1,True,1.5]):
            gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(26,'11:1'+str(i)),dict(anahtar='sessiz_kabul_is_gunu',deger=v),bek='BICIM')
        f,g=gec_duzenegi(); d=kur(f,t(26,'10:05')); ev=degerlendir(f,d,g,[pay('K052')])
        d.ilerlet(t(30,'11:00')); self.assertFalse(etkin_pay(d,d.sorumluluklar[ev+'/1']))

    def test_birim_takvimi_sessiz_kabulde_kullanilir(self):
        f,h=durus_duzenegi()
        f.olay('K001','AYAR.DEGISTIRDIM',t(1,'07:12'),girdiler=dict(anahtar='sessiz_kabul_is_gunu',deger=1))
        f.olay('K001','BIRIM.TANIMLADIM',t(21,'09:00'),girdiler=dict(kod='PLANLAMA',ad='Planlama',tur='MASA_BASI',basi='K004',ust_birim='YONETIM',takvim_gecerli='2026-10-22',takvim=dict(gunler=[6],mesai_baslangic='08:00',mesai_bitis='12:00',sabit_molalar=[])))
        d=kur(f,t(22,'13:50')); ev=degerlendir(f,d,h,[pay('PLANLAMA',100,'BIRIM')],'K009',t(22,'14:00'),neden='BEKLEME_BIRIM')
        d.ilerlet(t(24,'13:59')); self.assertFalse(etkin_pay(d,d.sorumluluklar[ev+'/1']))
        d.ilerlet(t(24,'14:00')); self.assertTrue(etkin_pay(d,d.sorumluluklar[ev+'/1']))
        self.assertEqual(gecikme_raporu(d,'2026-10-01','2026-10-31')[0]['sebep_olunan_bekleme_dk'],26)

    def test_farkli_ekip_sorumluluk_karari_projeyi_acmaz(self):
        f,d,g,ev=gecikme_duzenegi()
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(26,'11:01'),dict(anahtar='proje_gorunurlugu',deger='UYELER'))
        self.assertFalse(proje_gorebilir_mi(d,'K052','2509084'))
        gonder(f,d,'K052','SORUMLULUK.ITIRAZ_ETTIM',t(27,'10:00'),dict(hedef=ev,satir=1,gerekce='Kendi payim'))
        gonder(f,d,'K007','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(27,'11:00'),dict(hedef=ev,satir=1,karar='RET',gerekce='Pay dogru'))
        self.assertFalse(proje_gorebilir_mi(d,'K007','2509084'))
        self.assertEqual(performans(d)['zaman_orani'],1)
