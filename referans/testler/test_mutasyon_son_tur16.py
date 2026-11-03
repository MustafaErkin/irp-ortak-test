"""Görünüm, bildirim ve geç olay mutasyonlarından kalan somut karşı örnekler."""
import unittest
from decimal import Decimal
from irp import an
from .ortak import Duzenek,t,is_id,yaz
from .test_v7 import kur,gonder
from . import test_v10_1 as v10


class SonMutasyonOrnekleri(unittest.TestCase):
    def test_M092_ayin_son_gununun_gec_tanikligi_duzeltmeye_girer(self):
        """Karar 50/69/74: son günün geç emeği düzeltmedir; karar 70: 20000/180 TL/saat."""
        from irp.zaman import ay_kapanisi
        from irp.gorunum_v7 import duzeltme_defteri
        f=Duzenek(); f.ata(4)
        next(e['girdiler'] for e in f.olaylar if e['eylem_kodu']=='TAKVIM.TANIMLADIM')['calisma_gunleri']=[1,2,3,4,5,6,7]
        d=kur(f,t(1,'00:00',11)); ay_kapanisi(d,'2026-10-01'); d.ilerlet(t(2,'09:00',11))
        for code,clock,job in [('MESAI.GIRDIM','07:58',None),('IS.BASLADIM','08:00',4),('IS.TAMAMLADIM','09:00',4)]:
            f.olay('K017',code,t(31,clock),job)
            self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
        row=duzeltme_defteri(d,'2026-10-01')['2509084|K017|ISCILIK']
        self.assertEqual(row['saat'],1); self.assertEqual(row['tutar'],Decimal('111.11'))

    def test_M108_sessiz_kabul_sifir_ile_kapatilir(self):
        """Karar 41/61, T8: sessiz kabul 0 ise kapalıdır, negatif değer biçim hatasıdır."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:01'),dict(anahtar='sessiz_kabul_is_gunu',deger=0,gecerli_baslangic=t(22,'09:01')))
        self.assertEqual(d.ayar('sessiz_kabul_is_gunu',d.saat.simdi(),3),0)
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:02'),dict(anahtar='sessiz_kabul_is_gunu',deger=-1,gecerli_baslangic=t(22,'09:02')),bek='BICIM')

    def test_M223_nesne_ustunde_acilan_gorev_bagini_korur(self):
        """T8 §12: nesnenin üstünde açılan görev nesneye bağlanır."""
        _,d,n,g=v10.belge_duzenegi()
        self.assertEqual(d.gorevler[g]['nesne'],n)

    def test_M111_M284_B60_davranis_kilidi_bildirim_araliginin_uclari(self):
        """DAVRANIS_KILIDI B60: eşit zamanlı görülme, etkinlik aralığının iki ucunda da tutulur."""
        for end in (False,True):
            with self.subTest(kaldirma_ucu=end):
                f,d=v10.modul_duzenegi(); v10.birak(d,t(22,'09:00'),alicilar=[dict(tur='KISI',kimlik='K006')])
                key=next(iter(d.modul_bildirimleri)); seen=t(22,'09:01' if end else '09:00')
                if end:
                    d.ilerlet(seen)
                    d.modul_bildirimi_kaldir(servis_kimligi='SRV-M3',modul='M3',kural='SIPARIS_GECIKTI',kayit=dict(tur='IS',kimlik=is_id(4)),an=seen)
                d.ilerlet(t(22,'09:02'))
                f.olay('K006','BILDIRIM.GORDUM',seen,girdiler=dict(bildirimler=[key]))
                self.assertEqual(yaz(d,f.olaylar[-1])['sonuc'],'BASARILI')
                self.assertEqual(d.modul_bildirimleri[key]['gorulme_ani'],an(seen))

    def test_M153_gun_onayi_gerekmese_de_gonderilmis_rapor_hatirlatilir(self):
        """T9 §8 R33(a): beyaz yakanın gönderdiği fakat onaylanmamış rapor üstüne gider."""
        from irp.gorunum_v9 import hatirlatmalar
        f=Duzenek(); d=kur(f,t(22,'18:01'))
        gonder(f,d,'K041','GUN_SONU.GONDERDIM',t(22,'18:02'),dict(gun='2026-10-22',aciklama='Gün tamam',tanimsiz_aciklama=''))
        d.ilerlet(t(23,'08:00'))
        self.assertTrue(any(r['kural']=='R33' and r['kisi']=='K041' and r['alici']=='K012' and r['gun']=='2026-10-22' for r in hatirlatmalar(d)))

    def test_M192_gantt_etap_bitisinde_iptal_edilmis_is_sayilmaz(self):
        """Karar 58/T10: iptal edilen iş proje ilerleme ve gerçekleşen bitişi engellemez."""
        f=Duzenek()
        rows=next(e['girdiler'] for e in f.olaylar if e['eylem_kodu']=='IS.TANIMLADIM')
        rows['isler']=rows['isler'][3:5]
        f.ata(1); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',1); f.is_olay('TAMAMLADIM','09:00',1)
        d=kur(f,t(22,'09:01')); gonder(f,d,'K004','IS.IPTAL_ETTIM',t(22,'09:02'),dict(gerekce='Kapsamdan çıktı'),2)
        row=next(x for x in v10.gantt(d,'2509084','2026-10-22') if x['kimlik']==f.etap['E-IML'])
        self.assertEqual(row['durum'],'BITTI'); self.assertEqual(row['gerceklesen_bitis'],an(t(22,'09:00')))

    def test_M200_elle_bitisle_ayni_andaki_taniklik_sonrasi_degil(self):
        """T3 elle bitirme kapısı: bitişten sonraki tanıklık engeldir; eşit an değildir."""
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','09:00',4)
        d=kur(f,t(22,'09:05'))
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(22,'09:06'),dict(baslangic=t(22,'08:45'),bitis=t(22,'09:00'),aciklama='Eksik kayıt',is_bitti=True),4,adina='K017')
        self.assertEqual(d.isler[is_id(4)]['durum'],'BITTI')

    def test_M248_degisiklik_isinin_yarim_saat_maliyeti(self):
        """Karar 70/80, T9 §5: .5 saat × 20000/180 TL/saat, yarım yukarı = 55.56 TL."""
        from irp.gorunum_v9 import proje_degisiklikleri
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',4); f.is_olay('TAMAMLADIM','09:00',4)
        d=kur(f,t(22,'09:00'))
        row=dict(nereye='PROJE',proje='2509084',etap=f.etap['E-IML'],birim='IMALAT',islem='Değişiklik',tur='SURELI',tahmini_sure_dk=60,onay_gerekli=False,degisiklik=dict(kaynak=is_id(4),neden='MUSTERI'))
        key=gonder(f,d,'K004','IS.TANIMLADIM',t(22,'09:01'),dict(isler=[row]))
        gonder(f,d,'K009','IS.ATADIM',t(22,'09:02'),dict(kisi='K017',sira=1),key)
        gonder(f,d,'K017','IS.BASLADIM',t(22,'09:03'),{},key)
        gonder(f,d,'K017','IS.TAMAMLADIM',t(22,'09:33'),{},key)
        result=proje_degisiklikleri(d,'2509084','2026-10-22','2026-10-22',cagiran='K001')['MUSTERI']
        self.assertEqual(result['atolye_saati'],.5); self.assertEqual(result['maliyet'],Decimal('55.56'))

    def test_M261_izinle_cakisan_siradaki_is_uyarisi(self):
        """T8 §5 R37: onaylı izinle çakışan listedeki iş yöneticisine bildirilir."""
        f=Duzenek(); f.ata(4); d=kur(f,t(22,'09:00'))
        key=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(22,'09:01'),dict(kisi='K017',tur='MAZERET',baslangic=t(23,'08:00'),bitis=t(23,'18:00'),gerekce='İzin'))
        oid=gonder(f,d,'K009','IZIN.ONAYLADIM',t(22,'09:02'),dict(hedef=key))
        self.assertTrue(any(r['kural']=='R37' and r['alici']=='K009' and r['doguran_olay']==oid for r in d.bildirimler.values()))

    def test_M267_proje_atolye_emegi_saat_cinsindedir(self):
        """Karar 81/T9 proje göstergesi: 60 dakika atölye emeği 1 saattir."""
        from irp.gorunum_v9 import proje_ekleri
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',4); f.is_olay('TAMAMLADIM','09:00',4)
        d=kur(f,t(22,'09:01'))
        self.assertEqual(proje_ekleri(d,'2509084')['harcanan_emek'],1)

    def test_M268_B59_davranis_kilidi_etap_planinin_tam_sonu(self):
        """DAVRANIS_KILIDI B59: yalnız etap planı da yarı açık aralıkla süzülür."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(22,'09:01'),dict(proje='2509084',gerekce='Plan'))
        self.assertNotIn(f.etap['E-IML'],{r['kimlik'] for r in v10.gantt(d,'2509084','2026-12-26')})
