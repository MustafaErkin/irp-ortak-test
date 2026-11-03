"""T11 sınırları ve oku'nun bütün eski/yeni dalları gerçek kapı üzerinden."""
import unittest
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from irp import an
from irp.gorunum_v7 import oku
from irp.degismezler_v10_2 import denetle
from irp.gorunum_v10_2 import ESKI_VERILER, YENI_VERILER
from .ortak import Duzenek, t, is_id, yaz
from .test_v7 import kur, gonder
from .test_v10_2 import nesneli, ac, gec
from .test_v10_1 import belge_duzenegi, surum_olayi, ek_yetki


class SinirlarV10_2(unittest.TestCase):
    def test_sira_ana_proje_ve_gun_onay_ayari(self):
        f=Duzenek();d=kur(f,t(22))
        gonder(f,d,'K001','PROJE.ACTIM',t(22,'09:00'),dict(kod='ANA',ad='Ana proje'))
        d.ilerlet(t(22,'10:00'));f.olay('K001','PROJE.ACTIM',t(22,'08:59'),girdiler=dict(kod='ALT',ad='Alt proje',ana_proje='ANA'))
        self.assertEqual(yaz(d,f.olaylar[-1])['neden'],'SIRA')
        g=dict(birim='IMALAT',gerekli=True,gecerli_baslangic='2026-10-23')
        gonder(f,d,'K004','GUN_ONAYI.AYARLADIM',t(22,'10:01'),g)
        d.ilerlet(t(22,'11:00'));f.olay('K004','GUN_ONAYI.AYARLADIM',t(22,'10:00'),girdiler=dict(g,gerekli=False))
        self.assertEqual(yaz(d,f.olaylar[-1])['neden'],'SIRA')

    def test_sira_degisim_kaynagi_ve_ic_sorumlular(self):
        from .test_v9 import gec_duzenegi,pay
        f,g=gec_duzenegi();d=kur(f,t(26,'10:01'))
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(26,'11:00'),dict(kisi='K060',degisenler=dict(ad='Yeni ad'),gecerli_baslangic=t(26,'11:00')))
        d.ilerlet(t(26,'12:00'))
        f.olay('K012','GECIKME.DEGERLENDIRDIM',t(26,'10:30'),girdiler=dict(hedef=g,neden='DURUS_NEDENI.BEKLEME_MUSTERI',sorumlular=[pay('K060')],gerekce='Kontrol'))
        self.assertEqual(yaz(d,f.olaylar[-1])['neden'],'SIRA')
        for z,deg in [(t(26,'09:59'),dict(kaynak=g,neden='IYILESTIRME')),(t(26,'10:30'),dict(kaynak=g,neden='HATA',sorumlular=[pay('K060')]))]:
            s=f.gorev_satiri(ad='Değişiklik',teslim_tarihi='2026-10-27',degisiklik=deg)
            f.olay('K012','GOREV.ATADIM',z,girdiler=dict(gorevler=[s]))
            self.assertEqual(yaz(d,f.olaylar[-1])['neden'],'SIRA')

    def test_sira_fazla_mesainin_dayandigi_takvim(self):
        f=Duzenek();f.ata(1);d=kur(f,t(22))
        gonder(f,d,'K001','TATIL.EKLEDIM',t(22,'09:00'),dict(tarih='2026-10-23',ad='Özel tatil'))
        d.ilerlet(t(22,'10:00'))
        f.olay('K009','EK_MESAI.PLANLADIM',t(22,'08:59'),1,dict(kisi='K017',tarih='2026-10-23',baslangic='08:00',bitis='09:00',aciklama='Tatil çalışması'),tur='IS')
        self.assertEqual(yaz(d,f.olaylar[-1])['neden'],'SIRA')

    def test_tarih_penceresi_tek_gun_ve_tatil(self):
        f=Duzenek();d=kur(f,t(22))
        self.assertEqual(oku(d,'K001','KAPASITE','K017',bas='2026-10-22'),9)
        self.assertEqual(oku(d,'K001','KAPASITE','K017',bas=t(22,'18:00'),bit=t(22,'19:00')),0)
        for tur,key in [('BIRIM','IMALAT'),('TEZGAH','CNC-02')]:
            with self.subTest(tur=tur):
                r=oku(d,'K006','TAKVIM',tur=tur,kimlik=key,bas='2026-10-29')
                self.assertEqual(r['calisma'],[])
                self.assertEqual({x['neden'] for x in r['kapali']},{'TATIL'})
                r=oku(d,'K006','TAKVIM',tur=tur,kimlik=key,bas=t(23,'09:00'),bit=t(23,'10:00'))
                self.assertEqual(r['calisma'],[dict(bas=an(t(23,'09:00')),bit=an(t(23,'10:00')))])

    def test_kaynak_yuku_gorev_sahibi_ve_pencere_siniri(self):
        f=ek_yetki(Duzenek());d=kur(f,t(22))
        a=gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:00'),dict(gorevler=[f.gorev_satiri(planlanan_baslangic=t(23),planlanan_bitis=t(23,'09:00'))]))+'/1'
        gonder(f,d,'K012','GOREV.ATADIM',t(22,'09:01'),dict(gorevler=[f.gorev_satiri(kisi='K060',planlanan_baslangic=t(23),planlanan_bitis=t(23,'09:00'))]))
        r=oku(d,'K001','KAYNAK_YUKU',tur='KISI',kimlik='K041',bas=t(23),bit=t(23,'09:00'))
        self.assertEqual([x['kimlik'] for x in r],[a])
        self.assertEqual(oku(d,'K001','KAYNAK_YUKU',tur='KISI',kimlik='K041',bas=t(23,'09:00'),bit=t(23,'10:00')),[])
        self.assertEqual(oku(d,'K001','ETAPLAR','2509091'),[])
        self.assertEqual({x['kimlik'] for x in oku(d,'K001','ETAPLAR','2509084')},set(f.etap.values()))

    def test_kapali_ayin_maliyeti_oku_uzerinden(self):
        from irp.zaman import ay_kapanisi
        f=Duzenek();f.ata(1)
        f.is_olay('MESAI.GIRDIM','07:58');f.is_olay('BASLADIM','08:00',1);f.is_olay('TAMAMLADIM','09:00',1)
        d=kur(f,t(1,'00:30',11));ay_kapanisi(d,'2026-10-01')
        r=oku(d,'K001','ISCILIK_MALIYETI','2509084',bas='2026-10-01',bit='2026-10-31')
        self.assertEqual(r['iscilik'],Decimal('111.11'))
        for bas,bit in [('2026-10-22','2026-10-22'),(t(1,'00:01'),t(1,'00:00',11)),(t(1,'00:00'),t(31,'23:59'))]:
            with self.subTest(bas=bas,bit=bit),self.assertRaisesRegex(ValueError,'Karar 49'):
                oku(d,'K001','ISCILIK_MALIYETI','2509084',bas=bas,bit=bit)

    def test_gerceklesen_tezgah_gostergesi_dar_pencere(self):
        f=Duzenek();f.ata(8,'K023',1);f.ata(7,'K023',2)
        f.is_olay('MESAI.GIRDIM','07:59',kisi='K023');f.is_olay('TAMAMLADIM','08:10',8,'K023');f.is_olay('TAMAMLADIM','12:40',7,'K023')
        d=kur(f,t(22,'13:00'))
        r=oku(d,'K001','TEZGAH_GOSTERGESI','CNC-02',bas=t(22,'08:30'),bit=t(22,'09:30'))
        self.assertEqual(r['gerceklesen'],1)
        r=oku(d,'K001','TEZGAH_GOSTERGESI','CNC-02',bas=t(22,'12:40'),bit=t(22,'13:00'))
        self.assertEqual(r['gerceklesen'],0)

    def test_bekleyen_maliyet_dar_pencerede(self):
        from .test_v9 import gun_duzenegi
        f,d=gun_duzenegi()
        r=oku(d,'K001','ISCILIK_MALIYETI','2509084',bas=t(22,'09:00'),bit=t(22,'10:00'))
        self.assertEqual(r['onay_bekleyen'],Decimal('111.11'))
        self.assertEqual(oku(d,'K001','ISCILIK_MALIYETI','2509084',bas=t(22,'20:00'),bit=t(22,'21:00'))['onay_bekleyen'],0)

    def test_oku_ret_dallari(self):
        f,d=nesneli(True)
        for kim,veri,h,kw,exc in [
            ('K999','UYGUNLUK','K017',dict(bas=t(23,'09:00'),bit=t(23,'10:00')),PermissionError),
            ('K001','UYGUNLUK','K017',dict(bas=t(23),bit=t(23)),ValueError),
            ('K001','TEZGAH_UYGUNLUK','YOK',dict(bas=t(23),bit=t(23,'09:00')),ValueError),
            ('K006','ETAPLAR','2509091',{},PermissionError),
            ('K001','KAPASITE','K999',dict(bas='2026-10-23'),ValueError),
            ('K001','TAKVIM','YOK',dict(tur='BIRIM',bas='2026-10-23'),ValueError),
            ('K001','KAYNAK_YUKU','YOK',dict(tur='KISI',bas='2026-10-23'),ValueError),
        ]:
            with self.subTest(veri=veri,hedef=h,kim=kim,kw=kw),self.assertRaises(exc):oku(d,kim,veri,h,**kw)
        self.assertFalse(oku(d,'K001','UYGUNLUK','K017',bas=t(1,'00:00',9),bit=t(2,'00:00',9))['uygun'])

    def test_yonetim_ana_verileri_geri_tarihli_guncellenemez(self):
        cases=[
            ('YETKI.TANIMLADIM',dict(eylem_kodu='IS.ATADIM',kimler=['YETKILI'],kapsam='FIRMA')),
            ('TAKVIM.TANIMLADIM',dict(gecerli_baslangic='2026-10-23',mesai_baslangic='08:00',mesai_bitis='18:00',calisma_gunleri=[1,2,3,4,5],sabit_molalar=[])),
            ('TATIL.EKLEDIM',dict(tarih='2026-11-02',ad='Tatil')),
            ('AYAR.YONLENDIRDIM',dict(birim='IMALAT',kisiler=['K009'])),
        ]
        for kod,g in cases:
            with self.subTest(kod=kod):
                f=Duzenek();d=kur(f,t(22));gonder(f,d,'K001',kod,t(22,'09:00'),g)
                d.ilerlet(t(22,'10:00'));f.olay('K001',kod,t(22,'08:59'),girdiler=g)
                self.assertEqual(yaz(d,f.olaylar[-1]),dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))

    def test_not_nesne_hedefi_var_ve_gorunur_olmali(self):
        for uyeler in (False,True):
            f,d=nesneli(uyeler)
            gonder(f,d,'K006','NOT.YAZDIM',t(22,'14:00'),dict(metin='Olmayan nesne'),'K006-2610229999-M','NESNE','YETKI')
        f,d=nesneli(True)
        n=ac(f,d,'Gizli parça',t(22,'14:00'),proje='2509091')
        gonder(f,d,'K012','NOT.YAZDIM',t(22,'14:01'),dict(metin='Görülmeyen nesne'),n,'NESNE','YETKI')

    def test_yeni_kurulum_varsayilanlari_tarihsel_veriden_ayri(self):
        from irp.yetki_v6 import varsayilan_yetkiler,varsayilan_kodlar
        from irp.varsayilanlar_v10_2 import parca_turu,SIBERNETIK_EKLERI
        self.assertIn('ROL:MALIYET',varsayilan_kodlar());self.assertNotIn('ROL:MALIYET',varsayilan_kodlar(10.1))
        r=next(r for r in varsayilan_yetkiler() if r['eylem_kodu']=='KISI.YETKINLIK_TANIMLADIM')
        self.assertEqual(r['kimler'],['BIRIM_YONETICISI','YETKILI']);self.assertEqual(r['kapsam'],'BIRIM')
        self.assertFalse(any(r['eylem_kodu']=='KISI.YETKINLIK_TANIMLADIM' for r in varsayilan_yetkiler(10.1)))
        self.assertEqual(SIBERNETIK_EKLERI['kod_listeleri']['YETKINLIK'],[])
        self.assertIn('FASONDA',[x['kod'] for x in parca_turu()['asamalar']])

    def test_kod_ve_takvim_karari_kendi_kaydindan_onceye_dusmez(self):
        f=Duzenek();d=kur(f,t(22))
        g=dict(liste='YETKINLIK',kod='KAYNAK',ad='Kaynak',aktif=True)
        gonder(f,d,'K001','KOD.TANIMLADIM',t(22,'09:00'),g)
        d.ilerlet(t(22,'10:00'));f.olay('K001','KOD.TANIMLADIM',t(22,'08:59'),girdiler=dict(g,aktif=False))
        self.assertEqual(yaz(d,f.olaylar[-1]),dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))
        g=dict(tezgah='CNC-02',vardiyalar=[dict(gunler=[1,2,3,4,5],bas='06:00',bit='14:00')],gecerli_baslangic='2026-10-23')
        gonder(f,d,'K009','TEZGAH.TAKVIM_TANIMLADIM',t(22,'10:01'),g)
        d.ilerlet(t(22,'11:00'));f.olay('K009','TEZGAH.TAKVIM_TANIMLADIM',t(22,'10:00'),girdiler=g)
        self.assertEqual(yaz(d,f.olaylar[-1])['neden'],'SIRA')
        d.ilerlet(t(23));r=oku(d,'K006','TEZGAHLAR',birim='IMALAT')
        self.assertEqual(next(x for x in r if x['kod']=='CNC-02')['vardiyalar'],g['vardiyalar'])

    def test_yetkinlik_gecmisi_kisi_ana_alanlarini_korur(self):
        f=Duzenek();d=kur(f,t(22))
        gonder(f,d,'K001','YETKI.TANIMLADIM',t(22,'09:00'),dict(eylem_kodu='KISI.YETKINLIK_TANIMLADIM',kimler=['BIRIM_YONETICISI','YETKILI'],kapsam='BIRIM'))
        gonder(f,d,'K001','KOD.TANIMLADIM',t(22,'09:01'),dict(liste='YETKINLIK',kod='KAYNAK',ad='Kaynak',aktif=True))
        old=deepcopy(d.kisiler['K017']);others=deepcopy([x for x in d.kisi_gecmisi if x['kisi']!='K017'])
        gonder(f,d,'K001','KISI.YETKINLIK_TANIMLADIM',t(22,'09:02'),dict(kisi='K017',yetkinlikler=['KAYNAK'],gecerli_baslangic='2026-10-22'))
        rows=[x for x in d.kisi_gecmisi if x['kisi']=='K017'];self.assertEqual(rows[-2]['gecerli_bitis'],'2026-10-22')
        self.assertEqual(rows[-1]['ad'],old['ad']);self.assertEqual(rows[-1]['birim'],old['birim']);self.assertEqual(rows[-1]['yetkinlikler'],['KAYNAK'])
        self.assertEqual([x for x in d.kisi_gecmisi if x['kisi']!='K017'],others)
        self.assertTrue(all(denetle(d,True).values()))

    def test_an_penceresi_datetime_maliyet_ve_ardisik_tezgah(self):
        from irp.gorunum_v10_1 import pencere
        self.assertEqual(pencere(an(t(22,'09:00')),an(t(22,'10:00'))),(an(t(22,'09:00')),an(t(22,'10:00'))))
        f=Duzenek(); f.ata(1); d=kur(f,t(22))
        gonder(f,d,'K017','MESAI.GIRDIM',t(22,'08:00'))
        gonder(f,d,'K017','IS.BASLADIM',t(22,'08:00'),h=1,tur='IS')
        gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'10:00'),h=1,tur='IS')
        a=oku(d,'K001','ISCILIK_MALIYETI','2509084',bas=t(22,'08:00'),bit=t(22,'09:00'))
        b=oku(d,'K001','ISCILIK_MALIYETI','2509084',bas=t(22,'09:00'),bit=t(22,'10:00'))
        self.assertEqual(a['iscilik'],Decimal('111.11'));self.assertEqual(b['iscilik'],Decimal('111.11'))
        self.assertEqual(oku(d,'K001','TEZGAH_GOSTERGESI','CNC-02',bas=an(t(22,'09:00')),bit=an(t(22,'10:00')))['planli_kullanilabilir'],1)

    def test_sira_aktarim_saniye_alti_ve_kucuk_saat_kaymasi(self):
        for giris,fark in [(g,s) for g in ('AKTARIM','LISTE') for s in (-2,-.001,0,.001,2)]:
            with self.subTest(giris=giris,saniye=fark):
                f=Duzenek(); d=kur(f,t(23))
                talep=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(23,'09:00'),dict(kisi='K017',tur='YILLIK',baslangic=t(26),bitis=t(26,'18:00'),gerekce='İzin'))
                d.ilerlet(t(23,'09:01')); z=(an(t(23,'09:00'))+timedelta(seconds=fark)).isoformat()
                f.olay('K009','IZIN.ONAYLADIM',z,girdiler=dict(hedef=talep),giris_sekli=giris)
                e=f.olaylar[-1]; r=d.olay_ekle(e,servis=True)
                if giris!='AKTARIM' and fark<=0: self.assertEqual(r,dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))
                else: self.assertEqual(r['sonuc'],'BASARILI')
                if fark>0: self.assertEqual(d.izinler[talep]['durum'],'ONAYLI')
                self.assertTrue(all(denetle(d,True).values()))

    def test_ayni_an_buyuk_kimlik_kabul_tekrar_ve_pasif_kayit(self):
        f,d=nesneli(False); n=ac(f,d,'Mil',t(22,'14:00'),proje='2509084')
        gec(f,d,n,'SIPARISTE',t(22,'14:00'),'K006')
        e=deepcopy(f.olaylar[-1]); e['neyin_ustunde'][0]['surum']=d.nesneler[n]['surum']
        # İlk gönderimdeki içeriği sakla; tazelik değişse de tekrar kabulü korunur.
        from json import loads
        old=loads(d._icerikler[e['olay_kimligi']])
        self.assertTrue(d.olay_ekle(old,oturum='K006')['tekrar'])
        self.assertTrue(all(denetle(d,True).values()))

    def test_projesiz_nesneye_proje_eklenemez(self):
        f,d=nesneli(False); n=ac(f,d,'Projesiz',t(22,'14:00'))
        gonder(f,d,'K006','NESNE.GUNCELLEDIM',t(22,'14:01'),dict(hedef=n,degisenler=dict(baglar=[dict(tur='PROJE',kimlik='2509084')])),n,'NESNE','BICIM')
        self.assertFalse(d.nesneler[n].get('proje'))

    def test_yetkinlik_gelecek_tarih_bos_liste_ve_is_degistirme(self):
        f=Duzenek(); d=kur(f,t(22,'07:55'))
        gonder(f,d,'K001','YETKI.TANIMLADIM',t(22),dict(eylem_kodu='KISI.YETKINLIK_TANIMLADIM',kimler=['BIRIM_YONETICISI','YETKILI'],kapsam='BIRIM'))
        gonder(f,d,'K001','KOD.TANIMLADIM',t(22,'08:01'),dict(liste='YETKINLIK',kod='KAYNAK',ad='Kaynak',aktif=True))
        gonder(f,d,'K009','KISI.YETKINLIK_TANIMLADIM',t(22,'08:02'),dict(kisi='K017',yetkinlikler=['KAYNAK'],gecerli_baslangic='2026-10-23'))
        self.assertFalse(d.kisiler['K017'].get('yetkinlikler'))
        d.ilerlet(t(23)); self.assertEqual(d.kisiler['K017']['yetkinlikler'],['KAYNAK'])
        gonder(f,d,'K009','IS.DEGISTIRDIM',t(23,'08:01'),dict(degisenler=dict(yetkinlik='KAYNAK')),1,'IS')
        self.assertEqual(d.isler[is_id(1)]['yetkinlik'],'KAYNAK')
        gonder(f,d,'K009','IS.DEGISTIRDIM',t(23,'08:02'),dict(degisenler=dict(yetkinlik='YOK')),1,'IS','DURUM')
        gonder(f,d,'K009','KISI.YETKINLIK_TANIMLADIM',t(23,'08:03'),dict(kisi='K017',yetkinlikler=[],gecerli_baslangic='2026-10-23'))
        self.assertEqual(d.kisiler['K017']['yetkinlikler'],[])
        self.assertTrue(all(denetle(d,True).values()))

    def test_modul_harfi_cihaza_ve_ikinci_module_verilmez(self):
        f=Duzenek(); d=kur(f,t(22,'07:50')); h=d.cihaz_kaydol('K006','ILK')
        g=dict(kod='M3',ad='Modül',servis_kimligi='SRV-M3',aktif=True)
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22),dict(g,cihaz_harfi=h),bek='DURUM')
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'08:01'),dict(g,cihaz_harfi='P'))
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'08:02'),g,bek='DURUM')
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'08:03'),dict(g,cihaz_harfi='Q'),bek='DURUM')
        for j in range(10): self.assertNotEqual(d.cihaz_kaydol('K006',str(j)),'P')
        self.assertEqual(d.cihaz_kaydol('K006','ILK'),h)
        gonder(f,d,'K006','NOT.YAZDIM',t(22,'09:00'),dict(metin='Yanlış cihaz'),'2509084','PROJE',harf='P',bek='YETKI')
        gonder(f,d,'K006','NOT.YAZDIM',t(22,'09:01'),dict(metin='Yanlış harf'),'2509084','PROJE',harf='Q',cihaz='MODUL-M3',bek='YETKI')
        self.assertTrue(all(denetle(d,True).values()))

    def test_bildirim_suzulenler_uc_neden(self):
        f=Duzenek(); d=kur(f,t(22))
        gonder(f,d,'K001','MODUL.TANIMLADIM',t(22,'09:00'),dict(kod='M3',ad='M3',servis_kimligi='S',aktif=True))
        gonder(f,d,'K001','KISI.AYRILDI',t(22,'09:01'),dict(kisi='K060',ayrilis_tarihi='2026-10-22'))
        d.ilerlet(t(23))
        r=d.modul_bildirimi_birak('S','M3','A',dict(tur='PROJE',kimlik='2509084'),[dict(tur='KISI',kimlik=k) for k in ('K060','K999')],'X','BILGI',t(23))
        self.assertTrue(r['alici_kalmadi']); self.assertEqual(r['suzulenler'],[dict(kisi='K060',neden='AYRILDI'),dict(kisi='K999',neden='ISTIHDAM_DISI')])

    def test_kapasite_an_penceresi_ve_takvim_engelleri(self):
        f=Duzenek(); d=kur(f,t(22))
        self.assertEqual(oku(d,'K006','KAPASITE','K017',bas=t(23,'09:00'),bit=t(23,'11:00')),1.75)
        self.assertEqual(oku(d,'K006','TEZGAH_GOSTERGESI','CNC-02',bas=t(23,'09:00'),bit=t(23,'11:00'))['planli_kullanilabilir'],1.75)
        gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(22,'09:00'),dict(tezgah='CNC-02',baslangic=t(23,'09:00'),bitis=t(23,'11:00'),aciklama='Bakım'))
        r=oku(d,'K006','TAKVIM',tur='TEZGAH',kimlik='CNC-02',bas=t(23),bit=t(23,'12:00'))
        self.assertIn(dict(bas=an(t(23,'09:00')),bit=an(t(23,'11:00')),neden='BAKIM'),r['kapali'])
        self.assertEqual(r['calisma'],[dict(bas=an(t(23)),bit=an(t(23,'09:00'))),dict(bas=an(t(23,'11:00')),bit=an(t(23,'12:00')))])
        with self.assertRaisesRegex(ValueError,'TANIMSIZ_VERI'): oku(d,'K999','OLMAYAN')

    def test_kaynak_yuku_kisisel_ve_proje_maskesi(self):
        f=ek_yetki(Duzenek()); d=kur(f,t(22))
        gonder(f,d,'K009','IS.ATADIM',t(22,'09:00'),dict(kisi='K017',sira=1),1,'IS')
        gonder(f,d,'K001','PLAN.TARIHLEDIM',t(22,'09:01'),dict(hedefler=[dict(tur='IS',kimlik=is_id(1),planlanan_baslangic=t(23),planlanan_bitis=t(23,'09:00'))]),1,'IS')
        self.assertEqual(oku(d,'K006','KAYNAK_YUKU',tur='KISI',kimlik='K017',bas='2026-10-23'),[dict(durum='MESGUL',bas=an(t(23)),bit=an(t(23,'09:00')))])
        self.assertEqual(oku(d,'K009','KAYNAK_YUKU',tur='KISI',kimlik='K017',bas='2026-10-23')[0]['kimlik'],is_id(1))
        self.assertTrue(all(denetle(d,True).values()))

    def test_I127_kapi_atlanirsa_yanlis_kaynak_yakalanir(self):
        f=Duzenek(); d=kur(f,t(23))
        talep=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(23,'09:00'),dict(kisi='K017',tur='YILLIK',baslangic=t(26),bitis=t(26,'18:00'),gerekce='İzin'))
        f.olay('K009','IZIN.ONAYLADIM',t(23,'09:00'),girdiler=dict(hedef=talep))
        e=deepcopy(f.olaylar[-1]); e['bulut_ulasma_ani']=t(23,'09:01'); d._kayitlar[e['olay_kimligi']]=e; d.ilerlet(t(23,'09:01'))
        self.assertFalse(denetle(d,True)['I127'])


class OkumaDallariV10_2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f,d,n,g=belge_duzenegi(); surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K041'); surum_olayi(f,d,n,'ONAYLADIM',t(22,'11:00'))
        note=gonder(f,d,'K006','NOT.YAZDIM',t(22,'11:01'),dict(metin='Denetim'),'2509084','PROJE')
        cls.d=d; cls.hedefler={'PROJE':'2509084','ETAP':f.etap['E-IML'],'NOT':note,'DOSYA':'F-1','NESNE':n,'GOREV':g,'IS':is_id(1)}

    def sorgu(self,veri):
        hs=self.hedefler; h='K017'; kw=dict(bas='2026-10-22',bit='2026-10-23',gun='2026-10-22',ay='2026-10-01')
        if veri in ('PROJE','PROJE_DURUM','PLAN','GANTT','ETAPLAR','ISCILIK_MALIYETI','NESNELER'): h='2509084'
        elif veri in ('ETAP','ETAP_DURUM'): h=hs['ETAP']
        elif veri in ('TOP_KIMDE','SURUMLER','GECERLI_SURUM','NESNE'): h=hs['NESNE']
        elif veri in ('BIRIM_PERFORMANS','TEZGAHLAR','KISILER'): h='IMALAT'
        elif veri in ('TEZGAH_UCRETI','TEZGAH_UYGUNLUK','TEZGAH_GOSTERGESI','PLAN_CAKISMALARI'): h='CNC-02'
        elif veri in hs: h=hs[veri]
        elif veri in ('BILDIRIMLER','HAM_OLAY'): h='K001'
        if veri in ('TAKVIM','KAYNAK_YUKU'): kw.update(tur='KISI',kimlik='K017')
        if veri=='TEZGAH_UYGUNLUK': kw.update(bas=t(23),bit=t(23,'09:00'))
        r=oku(self.d,'K001',veri,h,**kw)
        self.assertIsNotNone(r)
        if veri=='SAAT_MALIYETI': self.assertEqual(r,Decimal(20000)/180)
        if veri=='TEZGAH_UCRETI': self.assertEqual(r,200)
        if veri=='KISILER': self.assertEqual({x['kimlik'] for x in r},{'K009','K017','K023'})
        if veri=='KAPASITE': self.assertEqual(r,18)


def okuma_testi(veri):
    def test(self): self.sorgu(veri)
    test.__doc__='oku → '+veri
    return test


for _veri in sorted(ESKI_VERILER | YENI_VERILER):
    setattr(OkumaDallariV10_2,'test_oku_'+_veri,okuma_testi(_veri))


class BicimBosluklariV10_2(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.f=Duzenek(); cls.d=kur(cls.f,t(22))


def bicim_testi(kod,g,h=None):
    def test(self):
        self.f.olay('K001',kod,t(22),h,g,tur='IS' if h else None)
        once=len(self.d.olaylar); r=yaz(self.d,self.f.olaylar[-1])
        self.assertEqual(r['kod'],'BICIM'); self.assertEqual(len(self.d.olaylar),once)
    return test


for _n,(_kod,_g,_h) in enumerate([
    ('KISI.AYRILDI',dict(kisi='K060',iptal=1,ayrilis_tarihi='2026-10-23'),None),
    ('KISI.AYRILDI',dict(kisi='K060',iptal=True,ayrilis_tarihi='2026-10-23'),None),
    ('KISI.AYRILDI',dict(kisi='K060'),None),
    ('KISI.EKLEDIM',dict(kod='K999',ad='X',birim='IMALAT',yaka='MAVI',roller=['CALISAN'],giris_tarihi='2026-10-22',ust='K009'),None),
    ('IS.BAGLANTI_DUZELTTIM',dict(degisenler=dict(proje='2509084'),gerekce='X'),None),
    ('IS.BAGLANTI_DUZELTTIM',dict(degisenler=dict(islem='X'),gerekce='X'),1),
    ('KOD.TANIMLADIM',dict(liste='YOK',kod='X',ad='X',aktif=True),None),
    ('KOD.TANIMLADIM',dict(liste='ROL',kod=' ',ad='X',aktif=True),None),
    ('KOD.TANIMLADIM',dict(liste='ROL',kod='X',ad=3,aktif=True),None),
    ('YETKI.TANIMLADIM',dict(eylem_kodu='IS.ATADIM',kimler=['YETKILI','YETKILI'],kapsam='FIRMA'),None),
    ('YETKI.TANIMLADIM',dict(eylem_kodu='IS.ATADIM',kimler='YETKILI',kapsam='FIRMA'),None),
    ('KISI.YETKINLIK_TANIMLADIM',dict(kisi='K017',yetkinlikler=['A','A'],gecerli_baslangic='2026-10-22'),None),
    ('KISI.YETKINLIK_TANIMLADIM',dict(kisi='K017',yetkinlikler='A',gecerli_baslangic='2026-10-22'),None),
    ('IS.DEGISTIRDIM',dict(degisenler=dict(yetkinlik=['A'])),1),
    ('NESNE.ACTIM',dict(tur='PARCA',ad='X',sorumlu='K006',baglar='x'),None),
    ('MODUL.TANIMLADIM',dict(kod='M',ad='M',servis_kimligi='S',aktif=True,cihaz_harfi='p'),None),
],1): setattr(BicimBosluklariV10_2,'test_bicim_'+str(_n).zfill(2),bicim_testi(_kod,_g,_h))
