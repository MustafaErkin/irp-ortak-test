"""T8 kesisimleri, yanlis girisler ve yeniden hesap karsi ornekleri."""
import unittest
from copy import deepcopy
from decimal import Decimal
from irp.saat import an
from irp.gorunum_v7 import *
from irp.gorunumler import gorev_gunluk_paylar,gunluk_saat,maas_dagilimi
from irp.degismezler_v7 import denetle,TANIMLAR
from irp.zaman import ay_kapanisi
from .ortak import Duzenek,t,is_id,yaz
from .test_v7 import kur,gonder,mesai_f,durus_f,parca_turu,dakika


class KenarlarV7(unittest.TestCase):
    def denetle(self,d):
        s=denetle(d,True); self.assertTrue(all(s.values()),s)

    def test_mesai_durus_sabit_mola(self):
        f=mesai_f(); x=f.olay('K009','DURUS.BASLADI',t(22,'17:50'),girdiler=dict(kapsam=['IMALAT'],neden='ELEKTRIK'))
        f.olay('K009','DURUS.BITTI',t(22,'18:15'),girdiler=dict(hedef=x)); f.is_olay('DEVAM_ETTIM','18:20',4)
        d=kur(f,t(22,'20:30')); self.assertEqual(dakika(d,'BEKLEME_DURUS'),25)
        self.assertEqual(sum(x['saat'] for x in fazla_mesai_kayitlari(d)),40/60); self.denetle(d)

    def test_izin_mesai_durus_onceligi(self):
        f=mesai_f(); x=f.olay('K017','IZIN.TALEP_ETTIM',t(21,'10:00'),girdiler=dict(kisi='K017',tur='SAATLIK',baslangic=t(22,'09:30'),bitis=t(22,'10:30'),gerekce='Saatlik'))
        f.olay('K009','IZIN.ONAYLADIM',t(21,'11:00'),girdiler=dict(hedef=x))
        x=f.olay('K009','DURUS.BASLADI',t(22,'09:00'),girdiler=dict(kapsam=['IMALAT'],neden='ELEKTRIK'))
        f.olay('K009','DURUS.BITTI',t(22,'10:45'),girdiler=dict(hedef=x)); f.is_olay('DEVAM_ETTIM','10:50',4)
        d=kur(f,t(22,'20:30')); self.assertEqual(dakika(d,'IZIN'),60)
        self.assertEqual(dakika(d,'BEKLEME_DURUS'),45); self.denetle(d)

    def test_gece_yarisi_katsayi(self):
        f=Duzenek(); f.ata(4)
        f.olay('K009','EK_MESAI.PLANLADIM',t(23,'09:00'),4,dict(kisi='K017',tarih='2026-10-24',baslangic=t(24,'23:00'),bitis=t(25,'02:00'),aciklama='Gece'),tur='IS')
        f.is_olay('MESAI.GIRDIM','23:00',gun=24); f.is_olay('BASLADIM','23:01',4,gun=24); f.is_olay('TAMAMLADIM','02:00',4,gun=25)
        d=kur(f,t(25,'03:00')); x=fazla_mesai_kayitlari(d)
        self.assertEqual([v['katsayi'] for v in x],[1.5,2]); self.assertEqual([v['saat'] for v in x],[59/60,2]); self.assertFalse(d.supheliler); self.denetle(d)

    def test_ayri_pencere_boslukta_ucret_yok(self):
        f=mesai_f(False); f.olaylar=[e for e in f.olaylar if e['eylem_kodu']!='IS.TAMAMLADIM']
        f.olay('K009','EK_MESAI.PLANLADIM',t(21,'17:00'),4,dict(kisi='K017',tarih='2026-10-22',baslangic='20:00',bitis='22:00',aciklama='Gece'),tur='IS')
        f.is_olay('MESAI.GIRDIM','20:00'); f.is_olay('BASLADIM','20:01',4); f.is_olay('TAMAMLADIM','21:00',4)
        d=kur(f,t(22,'23:00')); self.assertFalse(any(a['baslangic']<an(t(22,'20:00')) and (a['bitis'] or d.saat.simdi())>an(t(22,'18:00')) for a in d.araliklar)); self.denetle(d)

    def test_plan_iptali_ve_cakisma(self):
        f=Duzenek(); f.ata(4); d=kur(f,t(21,'17:00')); g=dict(kisi='K017',tarih='2026-10-22',baslangic='18:00',bitis='20:00',aciklama='Ek')
        x=gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(21,'17:01'),g,4)
        gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(21,'17:02'),dict(g,baslangic='19:00',bitis='21:00'),4,bek='DURUM')
        gonder(f,d,'K009','EK_MESAI.IPTAL_ETTIM',t(21,'17:03'),dict(hedef=x)); self.assertEqual(kapasite(d,'K017','2026-10-22','2026-10-22'),9)
        x=gonder(f,d,'K009','EK_MESAI.PLANLADIM',t(21,'17:04'),g,4)
        gonder(f,d,'K009','EK_MESAI.IPTAL_ETTIM',t(22,'18:00'),dict(hedef=x),bek='DURUM')

    def test_plan_penceresinde_baska_is_ve_devir(self):
        f=mesai_f(); f.olaylar=[e for e in f.olaylar if e['eylem_kodu']!='IS.TAMAMLADIM']; f.ata(2,'K023')
        f.olay('K009','IS.DEVRETTIM',t(22,'18:15'),2,dict(kimden='K023',kime='K017',kime_sira=1))
        f.is_olay('BASLADIM','18:20',2); f.is_olay('TAMAMLADIM','19:00',2)
        d=kur(f,t(22,'20:30')); self.assertTrue(any(x['hedef']==is_id(2) for x in fazla_mesai_kayitlari(d))); self.denetle(d)

    def test_iki_kisi_mesai_kisiye_ait(self):
        f=Duzenek(); f.olay('K009','IS.ATADIM',t(21,'16:00'),4,dict(kisiler=['K017','K023'],kisi_sayisi=2,sira=1,ek_mesai=dict(tarih='2026-10-22',baslangic='18:00',bitis='20:00',aciklama='Iki kisi')))
        for k,alt in [('K017','/k1'),('K023','/k2')]:
            for kod,saat in [('MESAI.GIRDIM','07:58'),('IS.BASLADIM','08:00'),('IS.DEVAM_ETTIM','10:15'),('IS.DEVAM_ETTIM','12:30'),('IS.DEVAM_ETTIM','15:15'),('IS.TAMAMLADIM','19:00')]: f.olay(k,kod,t(22,saat),None if kod.startswith('MESAI') else is_id(4)+alt)
        d=kur(f,t(22,'20:30')); self.assertEqual(sum(x['saat'] for x in fazla_mesai_kayitlari(d)),2); self.denetle(d)

    def test_sonradan_gun_tanimi_normal_mesai_olur(self):
        f=mesai_f(); d=kur(f,t(21,'17:00'))
        gonder(f,d,'K001','GUN.TANIMLADIM',t(21,'17:10'),dict(tarih='2026-10-22',tur='OZEL_MESAI',ad='Uzun gun',mesai_baslangic='08:00',mesai_bitis='20:00',sabit_molalar=d.varsayilan_takvim['sabit_molalar']))
        self.assertEqual(kapasite(d,'K017','2026-10-22','2026-10-22'),11)
        self.assertEqual(ekler(d,'K017','2026-10-22'),[])

    def test_beyaz_yaka_yuksek_deger_otomatik_mesai_degil(self):
        f=Duzenek(); g=f.gorev_ata(t(22,'09:00'),zaman_degeri=200,teslim_tarihi='2026-10-23'); f.gorev_olay('KABUL_ETTIM',t(22,'10:00'),g); f.gorev_olay('TAMAMLADIM',t(23,'16:00'),g)
        d=kur(f,t(23,'17:00')); self.assertEqual(fazla_mesai_kayitlari(d),[]); self.assertEqual(d.gorevler[g]['is_puani'],400)

    def test_izin_ik_iptal_ve_istihdam(self):
        f=Duzenek()
        # T9 9: IK onayi acilabilmesi icin ayri bir aktif IK gerekir.
        f.olay('K001','KISI.DEGISTIRDIM',t(20,'08:00'),girdiler=dict(kisi='K023',degisenler=dict(roller=['CALISAN','IK']),gecerli_baslangic=t(20,'08:00'),gerekce='IK gorevi'))
        d=kur(f,t(21,'09:00'))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(21,'09:01'),dict(anahtar='izin_ik_onayi',deger={'YILLIK':True}))
        x=gonder(f,d,'K041','IZIN.TALEP_ETTIM',t(21,'09:02'),dict(kisi='K041',tur='YILLIK',baslangic=t(22),bitis=t(22,'18:00'),gerekce='Izin'))
        gonder(f,d,'K012','IZIN.ONAYLADIM',t(21,'09:03'),dict(hedef=x)); self.assertEqual(d.izinler[x]['durum'],'IK_BEKLIYOR'); self.assertEqual(kapasite(d,'K041','2026-10-22','2026-10-22'),9)
        gonder(f,d,'K012','IZIN.IK_ONAYLADIM',t(21,'09:04'),dict(hedef=x),bek='YETKI')
        gonder(f,d,'K001','IZIN.IK_ONAYLADIM',t(21,'09:05'),dict(hedef=x)); self.assertEqual(kapasite(d,'K041','2026-10-22','2026-10-22'),0)
        gonder(f,d,'K041','IZIN.IPTAL_ETTIM',t(21,'09:06'),dict(hedef=x),bek='YETKI')
        gonder(f,d,'K012','IZIN.IPTAL_ETTIM',t(21,'09:07'),dict(hedef=x)); self.assertEqual(kapasite(d,'K041','2026-10-22','2026-10-22'),9)
        gonder(f,d,'K001','KISI.AYRILDI',t(21,'09:08'),dict(kisi='K041',ayrilis_tarihi='2026-10-23'))
        gonder(f,d,'K041','IZIN.TALEP_ETTIM',t(21,'09:09'),dict(kisi='K041',tur='YILLIK',baslangic=t(26),bitis=t(26,'18:00'),gerekce='Ayrilis sonrasi'),bek='DURUM')

    def test_izin_sonrasi_ayrilis_kapasite_ve_gun(self):
        f=Duzenek(); d=kur(f,t(21,'09:00'))
        x=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(21,'09:01'),dict(kisi='K017',tur='YILLIK',baslangic=t(27),bitis=t(27,'18:00'),gerekce='Plan'))
        gonder(f,d,'K009','IZIN.ONAYLADIM',t(21,'09:02'),dict(hedef=x)); gonder(f,d,'K001','KISI.AYRILDI',t(21,'09:03'),dict(kisi='K017',ayrilis_tarihi='2026-10-23'))
        d.ilerlet(t(28,'09:00')); self.assertEqual(kapasite(d,'K017','2026-10-26','2026-10-30'),0); self.assertFalse([a for a in d.araliklar if a['kisi']=='K017']); self.denetle(d)

    def test_tam_izin_girissiz_hayali_calisma_yok(self):
        f=Duzenek(); x=f.olay('K017','IZIN.TALEP_ETTIM',t(21,'09:00'),girdiler=dict(kisi='K017',tur='YILLIK',baslangic=t(22),bitis=t(22,'18:00'),gerekce='Izin'))
        f.olay('K009','IZIN.ONAYLADIM',t(21,'09:01'),girdiler=dict(hedef=x)); d=kur(f,t(26,'12:00'))
        self.assertEqual(dakika(d,'IZIN'),600); self.assertEqual(dakika(d,'TANIMSIZ'),0); self.denetle(d)

    def test_durus_ariza_ve_onay_beklemesi(self):
        for onay in (False,True):
            f=Duzenek(); n=9 if onay else 4; f.ata(n); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',n)
            if onay: f.is_olay('TAMAMLADIM','09:00',n)
            else: f.is_olay('ARIZA_BILDIRDIM','09:00',n,neden='ARIZA.MAKINE')
            x=f.olay('K009','DURUS.BASLADI',t(22,'09:15'),girdiler=dict(kapsam=['IMALAT'],neden='ELEKTRIK')); f.olay('K009','DURUS.BITTI',t(22,'09:30'),girdiler=dict(hedef=x))
            d=kur(f,t(22,'09:40')); self.assertEqual(dakika(d,'BEKLEME_DURUS'),15)
            self.assertEqual(d.kisi_durumu['K017']['durum'],'ONAY_BEKLIYOR' if onay else 'ARIZADA'); self.denetle(d)

    def test_durus_gun_siniri(self):
        f=mesai_f(); x=f.olay('K009','DURUS.BASLADI',t(22,'19:10'),girdiler=dict(kapsam=['IMALAT'],neden='ELEKTRIK'))
        f.olay('K009','DURUS.BITTI',t(23,'07:00'),girdiler=dict(hedef=x)); d=kur(f,t(23,'09:00'))
        self.assertEqual(dakika(d,'BEKLEME_DURUS'),50); self.assertEqual(d.kisi_durumu['K017']['durum'],'MESAI_DISI'); self.denetle(d)

    def test_bakim_cakismasi_birlesim(self):
        f=Duzenek(); d=kur(f,t(21,'09:00'))
        for saat,bas,bit in [('09:01','08:00','12:00'),('09:02','11:00','14:00')]:
            gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(21,saat),dict(tezgah='CNC-02',baslangic=t(22,bas),bitis=t(22,bit),aciklama='Bakim'))
        self.assertEqual(tezgah_gostergesi(d,'CNC-02','2026-10-22','2026-10-22')['planli_kullanilabilir'],3.75)

    def test_rapor_bayat_ozet_ve_gecersiz_sayma(self):
        f=mesai_f(); d=kur(f,t(22,'20:30'))
        gonder(f,d,'K017','GUN_SONU.GONDERDIM',t(22,'20:31'),dict(gun='2026-10-22',aciklama='Rapor',tanimsiz_aciklama='Bekledim'))
        g=dict(kisi='K017',gun='2026-10-22',ozet_surumu='bayat')
        gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'20:32'),g,bek='DURUM')
        g['ozet_surumu']=gun_sonu_raporu(d,'K017','2026-10-22')['ozet_surumu']; gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'20:33'),g)
        hedef=next(e['olay_kimligi'] for e in f.olaylar if e['eylem_kodu']=='IS.BASLADIM')
        gonder(f,d,'K009','KAYIT.GECERSIZ_SAYDIM',t(23,'09:00'),dict(hedef=hedef,gerekce='Yanlis baslangic'),duzelttigi_olay=hedef)
        self.assertEqual(gun_sonu_raporu(d,'K017','2026-10-22')['durum'],'DEGISTI'); self.denetle(d)

    def test_rapor_kapali_ay_donuk(self):
        f=mesai_f(); d=kur(f,t(22,'20:30')); gonder(f,d,'K017','GUN_SONU.GONDERDIM',t(22,'20:31'),dict(gun='2026-10-22',aciklama='Rapor',tanimsiz_aciklama='Bekledim'))
        ozet=gun_sonu_raporu(d,'K017','2026-10-22')['ozet_surumu']; gonder(f,d,'K009','GUN_SONU.ONAYLADIM',t(22,'20:32'),dict(kisi='K017',gun='2026-10-22',ozet_surumu=ozet))
        d.ilerlet(t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01'); once=gun_sonu_raporu(d,'K017','2026-10-22')
        f.is_olay('MOLA_VERDIM','18:30',4); d.ilerlet(t(2,'09:00',11)); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(gun_sonu_raporu(d,'K017','2026-10-22'),once); self.denetle(d)

    def test_gec_olay_ikinci_kapanista_tekrar_yazilmaz(self):
        f=Duzenek(); f.ata(4); d=kur(f,t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        for kod,saat,n in [('MESAI.GIRDIM','07:58',None),('BASLADIM','08:00',4),('MESAI.CIKTIM','09:00',None)]:
            f.is_olay(kod,saat,n,gun=30); d.ilerlet(t(2,'09:00',11)); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(onceki_donem_duzeltmeleri(d)[0]['tutar'],Decimal('111.11'))
        d.ilerlet('2026-12-01T00:30:00+03:00'); ay_kapanisi(d,'2026-11-01')
        self.assertEqual(onceki_donem_duzeltmeleri(d),[]); self.denetle(d)

    def test_nesne_turu_son_asama_bag_ve_modul_yetki(self):
        f=Duzenek(); d=kur(f,t(26,'08:00')); tur=parca_turu()
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(26,'09:00'),tur)
        gonder(f,d,'K006','NESNE.ACTIM',t(26,'09:01'),dict(tur='PARCA',ad='St10-1',sorumlu='K006',baglar=[dict(tur='KISI',kimlik='K017')]),bek='DURUM')
        x=gonder(f,d,'K006','NESNE.ACTIM',t(26,'09:02'),dict(tur='PARCA',ad='St10-1',sorumlu='K006',baglar=[dict(tur='PROJE',kimlik='2509084')]))
        gonder(f,d,'K004','NESNE.ASAMA_GECIRDIM',t(26,'09:03'),dict(hedef=x,yeni_asama='MONTAJA_HAZIR',gerekce='Stok'))
        gonder(f,d,'K009','NESNE.ASAMA_GECIRDIM',t(26,'09:04'),dict(hedef=x,yeni_asama='MONTAJDA',gerekce='Montaj'))
        gonder(f,d,'K001','NESNE.ASAMA_GECIRDIM',t(26,'09:05'),dict(hedef=x,yeni_asama='SIPARISTE',gerekce='Geri'),bek='DURUM')
        gecissiz=deepcopy(tur); gecissiz['gecisler']=[z for z in gecissiz['gecisler'] if not (z['den']=='MONTAJA_HAZIR' and z['e']=='MONTAJDA')]
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(26,'09:05'),gecissiz,bek='DURUM')
        tur['asamalar']=tur['asamalar'][:-1]; tur['gecisler']=[x for x in tur['gecisler'] if x['e']!='MONTAJDA']
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(26,'09:06'),tur,bek='DURUM')
        e=deepcopy(f.olaylar[-1]); e['giris_sekli']='AKTARIM'; self.assertEqual(modul_yaz(d,'K001',e)['kod'],'YETKI'); self.denetle(d)

    def test_sorumluluk_itiraz_dogrulama_siniri_ve_revizyon(self):
        f=Duzenek(); g=f.gorev_ata(t(22,'09:00'),zaman_degeri=8,teslim_tarihi='2026-10-23',onay_gerekli=True,onaylayan='K012')
        f.gorev_olay('KABUL_ETTIM',t(22,'09:30'),g); f.gorev_olay('TAMAMLADIM',t(22,'10:30'),g); d=kur(f,t(22,'11:00'))
        ret=gonder(f,d,'K012','GOREV.REDDETTIM',t(22,'11:01'),dict(**{'not':'Ret'},sorumlular=[dict(tur='KISI',kimlik='K041',yuzde=60),dict(tur='BIRIM',kimlik='OTO_TASARIM',yuzde=40)],revizyon_ver=True,zaman_degeri=2,kime='K041',yeni_teslim_tarihi='2026-10-23'),g,'GOREV')
        r=ret+'/1'; gonder(f,d,'K041','GOREV.KABUL_ETTIM',t(22,'11:02'),h=r,tur='GOREV'); gonder(f,d,'K041','GOREV.TAMAMLADIM',t(22,'11:03'),h=r,tur='GOREV'); gonder(f,d,'K012','GOREV.ONAYLADIM',t(22,'11:04'),h=r,tur='GOREV')
        self.assertIsNone(d.gorevler[r]['is_puani'])
        gonder(f,d,'K012','SORUMLULUK.DOGRULADIM',t(22,'11:05'),dict(hedef=ret+'/1',karar='DEGISTIR',yuzde=70,gerekce='Fazla'),bek='DURUM')
        gonder(f,d,'K001','SORUMLULUK.DOGRULADIM',t(22,'11:06'),dict(hedef=ret+'/1',karar='ONAY',gerekce='Zincir')); self.assertIsNone(d.gorevler[r]['is_puani'])
        it=gonder(f,d,'K041','SORUMLULUK.ITIRAZ_ETTIM',t(22,'11:07'),dict(hedef=ret+'/1',gerekce='Itiraz')); self.assertEqual(d.gorevler[r]['is_puani'],4)
        gonder(f,d,'K001','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(22,'11:08'),dict(hedef=it,karar='RET',gerekce='Kanit')); self.assertIsNone(d.gorevler[r]['is_puani']); self.denetle(d)
        gonder(f,d,'K001','SORUMLULUK.DOGRULADIM',t(22,'11:09'),dict(hedef=ret+'/2',karar='ONAY',gerekce='Birim'))
        self.assertEqual(oku(d,'K001','BIRIM_PERFORMANS','OTO_TASARIM',bas='2026-10-01',bit='2026-10-31')['kalite_ret'],.4)
        self.assertEqual(oku(d,'K001','BIRIM_PERFORMANS','MEK_TASARIM',bas='2026-10-01',bit='2026-10-31')['kalite_ret'],.6)
        gonder(f,d,'K001','KISI.AYRILDI',t(23,'09:00'),dict(kisi='K041',ayrilis_tarihi='2026-10-23'))
        d.ilerlet(t(24,'09:00'))
        self.assertEqual(oku(d,'K001','PERFORMANS','K041',bas='2026-10-01',bit='2026-10-31')['kalite_ret'],.6)
        self.assertIsNone(d.gorevler[r]['is_puani']); self.denetle(d)

    def test_eksik_maas_genel_gider_negatif_prim(self):
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        for deger in (.5,float('nan'),float('inf')):
            gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:01'),dict(anahtar='fazla_mesai_katsayilari',deger=dict(TATIL=2,PAZAR=2,CUMARTESI=1.5,HAFTA_ICI=deger)),bek='BICIM')
        d.hassas_ekler.append(dict(nesne_kimlik='K017',tur='GENEL_GIDER_PAYI',tutar=1600,gecerli_baslangic='2026-10-01'))
        self.assertEqual(saat_maliyeti(d,'K017','2026-10-22'),120); self.denetle(d)
        f=Duzenek(); f.olay('K001','KISI.EKLEDIM',t(15),girdiler=dict(kod='K061',ad='Yeni',birim='IMALAT',yaka='MAVI',roller=['CALISAN'],giris_tarihi='2026-10-19'))
        f.ata(2,'K061')
        for kod,saat,n in [('MESAI.GIRDIM','07:58',None),('BASLADIM','08:00',2),('TAMAMLADIM','09:30',2)]: f.is_olay(kod,saat,n,'K061')
        d=kur(f,t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        self.assertEqual(onceki_donem_duzeltmeleri(d),[]); self.denetle(d)

    def test_gorunurluk_sorgu_parasal_sizma_yok(self):
        d=kur(mesai_f(),t(22,'20:30'))
        for k in ('K017','K009','K004'):
            self.assertNotIn('prim',oku(d,k,'FAZLA_MESAI','K017')[0])
            with self.assertRaises(PermissionError): oku(d,k,'SAAT_MALIYETI','K017',gun='2026-10-22')
        self.assertIn('prim',oku(d,'K001','FAZLA_MESAI','K017')[0])
        v=aylik_maliyet_ozeti(d,'K017','2026-10-01')
        self.assertEqual(v['tutarlar']['2509084'],Decimal('1111.11')); self.assertEqual(v['dagitilamayan'],Decimal('18888.89'))
        self.denetle(d)

    def test_sonraki_ayin_tatili_eski_aya_duzeltme_uretmez(self):
        f=Duzenek(); g=f.gorev_ata(t(28,'09:00'),zaman_degeri=30,teslim_tarihi='2026-11-05'); f.gorev_olay('KABUL_ETTIM',t(28,'10:00'),g)
        d=kur(f,t(1,'00:30',11)); ay_kapanisi(d,'2026-10-01')
        gonder(f,d,'K001','GUN.TANIMLADIM',t(2,'09:00',11),dict(tarih='2026-11-04',tur='TATIL',ad='Tatil'))
        self.assertEqual(onceki_donem_duzeltmeleri(d),[]); self.denetle(d)

    def test_gec_etap_olayi_B0_kopyasini_degistirmez(self):
        f=Duzenek(); d=kur(f,t(26,'08:00')); gonder(f,d,'K004','PLAN.ONAYLADIM',t(26,'09:00'),dict(proje='2509084'))
        once=deepcopy(d.plan_surumleri)
        f.olay('K004','ETAP.DEGISTIRDIM',t(25,'09:00'),f.etap['E-IML'],dict(degisenler=dict(bitis='2027-01-08')),tur='ETAP')
        d.ilerlet(t(27,'09:00')); self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(d.plan_surumleri,once); self.assertTrue(plan_karsilastir(d,'2509084')['onaysiz_degisti']); self.denetle(d)
        gonder(f,d,'K004','ETAP.TANIMLADIM',t(27,'10:00'),dict(proje='2509091',ad='Bos etap',birim='IMALAT',baslangic='2026-10-27',bitis='2026-11-01',hedef_saat=10))
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(27,'10:01'),dict(proje='2509091'))
        b0=deepcopy(d.plan_surumleri['2509091'])
        gonder(f,d,'K001','PROJE.KAPATTIM',t(27,'10:02'),dict(gerekce='Tamamlandi'),'2509091','PROJE')
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(27,'10:03'),dict(proje='2509091',gerekce='Yeni plan'),bek='DURUM')
        self.assertEqual(d.plan_surumleri['2509091'],b0); self.denetle(d)


class DegismezlerV7(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.depolar=[kur(mesai_f(),t(22,'20:30')),kur(durus_f(),t(22,'10:45'))]

def degismez_testi(k):
    def test(self):
        for d in self.depolar: self.assertTrue(denetle(d,True)[k],TANIMLAR[k])
    test.__doc__=TANIMLAR[k]; return test
for _k in TANIMLAR: setattr(DegismezlerV7,'test_'+_k,degismez_testi(_k))

if __name__=='__main__': unittest.main()
