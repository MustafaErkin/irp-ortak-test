"""İkinci mutasyon incelemesi: tasarımdan bağımsız sayısal/sınır beklentileri."""
import unittest
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from irp import Depo, Saat, an
from .ortak import Duzenek, t, is_id
from .test_v7 import kur, gonder, mesai_f
from . import test_v10_1 as v10


class EkMutasyonSinirlari(unittest.TestCase):
    def test_M003_onay_bekleyen_basin_arkasindaki_is_devredilir(self):
        """T3 liste kilidi: yalnız ilk iş kilitlenir; sonraki iş devredilebilir."""
        f=Duzenek(); f.ata(9); f.ata(4,sira=2)
        f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
        d=kur(f,t(22,'09:01'))
        gonder(f,d,'K009','IS.DEVRETTIM',t(22,'09:02'),dict(kimden='K017',kime='K023',kime_sira=1),4)
        self.assertEqual(d.listeler['K017'],[is_id(9)]); self.assertEqual(d.listeler['K023'],[is_id(4)])

    def test_M030_yetkili_sahibi_ve_ustu_olmadigi_belgeye_taslak_ekler(self):
        """Karar 99/T10: sahip, üst ve YETKILI birbirinden bağımsız seçeneklerdir."""
        f,d,n,_=v10.belge_duzenegi()
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:51'),
               dict(kisi='K052',degisenler=dict(roller=['BEYAZ_YAKA','YETKILI']),gecerli_baslangic=t(22,'09:51')))
        v10.surum_olayi(f,d,n,'EKLEDIM',t(22,'10:00'),kim='K052')
        self.assertEqual(v10.surumler(d,n,cagiran='K052')[0]['durum'],'TASLAK')

    def test_M051_M227_modul_alicisi_simdiki_rol_ile_cozulur(self):
        """T10 §3: rol alıcıları bildirim bırakıldığı anda çözülür."""
        f,d=v10.modul_duzenegi()
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:01'),
               dict(kisi='K006',degisenler=dict(roller=['YETKILI']),gecerli_baslangic=t(22,'10:00')))
        # Saatin ilerlemesi olay değildir. Kapının güncel hesap istemesi sınanır.
        d.saat.ilerlet(t(22,'10:00'))
        r=d.modul_bildirimi_birak(servis_kimligi='SRV-M3',modul='M3',kural='ROL',
            kayit=dict(tur='IS',kimlik=is_id(4)),alicilar=[dict(tur='ROL',kimlik='YETKILI')],
            metin='Rol bildirimi',onem='BILGI',an=t(22,'10:00'))
        self.assertEqual(r['sonuc'],'BASARILI'); self.assertEqual(set(r['alicilar']),{'K001','K006'})

    def test_M058_not_gorevinin_kabulu_bitis_anidir(self):
        """T3 not görevi/karar 37: kabul edildiğinde biter, bitiş kabul anıdır."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        oid=gonder(f,d,'K041','NOT.YAZDIM',t(22,'09:01'),dict(metin='Kontrol',etiketler=['MEK_TASARIM']),
                   '2509084','PROJE')
        ids=[k for k,g in d.gorevler.items() if g.get('kaynak')==oid and g['tur']=='NOT']
        self.assertTrue(ids)
        gonder(f,d,'K012','GOREV.KABUL_ETTIM',t(22,'09:02'),{},ids,'GOREV')
        for key in ids:
            self.assertEqual(d.gorevler[key]['durum'],'BITTI')
            self.assertEqual(an(d.gorevler[key]['bitis_ani']),an(t(22,'09:02')))

    def test_M062_M235_atayan_disindaki_lider_onayinda_suphe_yok(self):
        """T3/T4: iş biriminin ekip lideri, atayan başka kişi olsa da onaylar."""
        f=Duzenek(); f.ata(9)
        # İkinci ekip lideri, birim başı olmayan ayrı kişidir.
        next(e['girdiler'] for e in f.olaylar if e['eylem_kodu']=='KISI.EKLEDIM' and e['girdiler']['kod']=='K023')['roller']=['EKIP_LIDERI']
        f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
        d=kur(f,t(22,'09:01'))
        oid=gonder(f,d,'K023','IS.ONAYLADIM',t(22,'09:02'),{},9)
        self.assertNotIn(oid,d.supheliler); self.assertEqual(d.isler[is_id(9)]['durum'],'BITTI')

    def test_M086_yeniden_giriste_kapanmis_kisi_gecmisi_degismez(self):
        """Karar 59: istihdam dönemleri ayrı; eski ana veri geçerliliği korunur."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:01'),dict(kisi='K060',degisenler=dict(ad='Yeni ad'),gecerli_baslangic=t(22,'09:01')))
        ilk=deepcopy([r for r in d.kisi_gecmisi if r['kisi']=='K060' and r['gecerli_bitis'] is not None])
        self.assertTrue(ilk)
        gonder(f,d,'K001','KISI.AYRILDI',t(22,'09:02'),dict(kisi='K060',ayrilis_tarihi='2026-10-23'))
        gonder(f,d,'K001','KISI.EKLEDIM',t(26,'09:00'),dict(kod='K060',ad='Geri döndü',birim='MEK_TASARIM',yaka='BEYAZ',roller=['BEYAZ_YAKA'],giris_tarihi='2026-11-02'))
        self.assertEqual([r for r in d.kisi_gecmisi if r['kisi']=='K060'][:len(ilk)],ilk)

    def test_M097_tam_gece_yarisindaki_birim_degisimi(self):
        """Karar 83/T9: gün başındaki birim, o günün takvimini belirler."""
        from irp.takvim_v9 import kisi_birimi
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','KISI.DEGISTIRDIM',t(22,'09:01'),dict(kisi='K017',degisenler=dict(birim='PLANLAMA'),gecerli_baslangic=t(23,'00:00')))
        d.ilerlet(t(23,'00:00'))
        self.assertEqual(kisi_birimi(d,'K017','2026-10-22'),'IMALAT')
        self.assertEqual(kisi_birimi(d,'K017','2026-10-23'),'PLANLAMA')

    def test_M099_anlik_isin_basinda_ariza_bildirilebilir(self):
        """T3/T4 A8: liste başındaki ANLIK işte arıza kapısı açıktır."""
        f=Duzenek(); f.ata(8); f.is_olay('MESAI.GIRDIM','07:58'); d=kur(f,t(22,'08:00'))
        oid=gonder(f,d,'K017','IS.ARIZA_BILDIRDIM',t(22,'08:01'),{'not':'Makine başlamıyor'},8)
        self.assertNotIn(oid,d.supheliler); self.assertEqual(d.kisi_durumu['K017']['durum'],'ARIZADA')

    def test_M106_iki_yetkili_arasinda_bir_gun_bosluk_olamaz(self):
        """Karar 60: her ileri sınırda istihdamda bir yetkili kalır; ayrılış günü dahildir."""
        from irp.kurallar_v6 import yetkili_kalir
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','KISI.EKLEDIM',t(22,'09:01'),dict(kod='K061',ad='Yeni yetkili',birim='YONETIM',yaka='BEYAZ',roller=['YETKILI'],giris_tarihi='2026-10-24'))
        f.olay('K001','KISI.AYRILDI',t(22,'09:02'),girdiler=dict(kisi='K001',ayrilis_tarihi='2026-10-22'))
        # Bileşen testi yalnız tüm zaman çizgisindeki yetkili varlığını sorar;
        # ayrıca birim başı olma yasağı bu hesapla karıştırılmaz.
        self.assertFalse(yetkili_kalir(d,f.olaylar[-1]))

    def test_M121_demo_saatini_ayni_ana_almak_geri_gitmek_degildir(self):
        """Karar 19/T4 A17: geri saat yasak; aynı ana ayarlama geçerlidir."""
        f=Duzenek(); d=f.calistir(t(22,'09:00'),demo=True)
        gonder(f,d,'K001','AYAR.SAAT_KAYDIRDIM',t(22,'09:00'),dict(hedef=t(22,'09:00')))
        self.assertEqual(d.saat.simdi(),an(t(22,'09:00')))

    def test_M134_M173_B59_davranis_kilidi_tarih_sonu_dahildir(self):
        """DAVRANIS_KILIDI B59: tarih sonu ertesi gün 00:00'a çevrilir."""
        from irp.gorunum_v10_1 import pencere
        self.assertEqual(pencere('2026-10-22','2026-10-23'),(an(t(22,'00:00')),an(t(24,'00:00'))))
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K004','PLAN.ONAYLADIM',t(22,'09:01'),dict(proje='2509084',gerekce='İlk plan'))
        rows={r['kimlik']:r for r in v10.gantt(d,'2509084','2026-11-02')}
        self.assertEqual(rows[f.etap['E-IML']]['planlanan_bitis'],an('2026-12-26T00:00:00+03:00'))

    def test_M135_M174_M193_etapta_yeniden_isleme_ve_planli_saat(self):
        """Karar 9/21, T4 A15: tahmin dakikadan saate; ret emeği ayrı maliyettir."""
        from irp.gorunumler import etap_gostergesi
        f=Duzenek(); f.ata(9); f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9)
        f.is_olay('TAMAMLADIM','09:00',9); d=kur(f,t(22,'09:01'))
        gonder(f,d,'K009','IS.REDDETTIM',t(22,'09:02'),{'not':'Ölçü hatası'},9)
        gonder(f,d,'K017','IS.DEVAM_ETTIM',t(22,'09:03'),{},9)
        d.ilerlet(t(22,'09:33'))
        result=etap_gostergesi(d,f.etap['E-IML'])
        self.assertEqual(result['planli_toplam'],22)
        self.assertAlmostEqual(result['revizyon_maliyeti_saat'],.5)
        self.assertEqual(etap_gostergesi(d,f.etap['E-TAS'])['revizyon_maliyeti_saat'],0)

    def test_M140_ayin_son_gununde_kapanis_olmaz(self):
        """Karar 30/52: ay bittikten sonra kapanır; son gün henüz ay içidir."""
        from irp.zaman import ay_kapanisi
        d=Depo(Saat(t(31,'23:59')))
        with self.assertRaises(ValueError): ay_kapanisi(d,'2026-10-01')

    def test_M162_takvim_yarindan_gecerli_olabilir(self):
        """T4 A17: takvim en erken ertesi günün başlangıcında geçerlidir."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','TAKVIM.TANIMLADIM',t(22,'09:01'),dict(gecerli_baslangic='2026-10-23',mesai_baslangic='09:00',mesai_bitis='18:00',calisma_gunleri=[1,2,3,4,5],sabit_molalar=[]))
        self.assertEqual(d.takvim('2026-10-23')['mesai_baslangic'],'09:00')

    def test_M185_fazla_mesai_katsayisi_sayi_olmali(self):
        """T8 §3: katsayılar en az bir sayıdır; mantıksal değer sayı değildir."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        values=dict(TATIL=2,PAZAR=2,CUMARTESI=1.5,HAFTA_ICI=1.5)
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:01'),dict(anahtar='fazla_mesai_katsayilari',deger=values,gecerli_baslangic=t(22,'09:01')))
        gonder(f,d,'K001','AYAR.DEGISTIRDIM',t(22,'09:02'),dict(anahtar='fazla_mesai_katsayilari',deger=dict(values,TATIL=True),gecerli_baslangic=t(22,'09:02')),bek='BICIM')

    def test_M191_mesainin_tam_baslangicinda_beyaz_yaka_gun_isi(self):
        """T9 §8 açık hüküm: MESAI_SONU o günün mesai başlangıcında görünür."""
        from irp.gorunum_v9 import gun_isleri
        f=Duzenek(); d=kur(f,t(22,'07:59'))
        def var(): return any(r['tur']=='MESAI_SONU' and r['gun']=='2026-10-22' for r in gun_isleri(d,'K041'))
        self.assertFalse(var()); d.ilerlet(t(22,'08:00')); self.assertTrue(var())

    def test_M194_firma_durusu_her_birimi_kapsar(self):
        """T8 §4: FIRMA kapsamı bütün birimleri kapsar; birim alt ağacı ayrıdır."""
        from irp.takvim_v7 import birim_kapsamda
        d=SimpleNamespace(birimler={'A':{'ust_birim':None},'B':{'ust_birim':'A'},'C':{'ust_birim':None}})
        self.assertTrue(birim_kapsamda(d,'C','FIRMA'))
        self.assertTrue(birim_kapsamda(d,'B',['A']))
        self.assertFalse(birim_kapsamda(d,'C',['A']))

    def test_gunluk_30_gunden_eski_gonderilenler_temizlenir(self):
        """Karar 14/T4 A3: yalnız gönderilmiş ve 30 günden eski yerel kayıt silinir."""
        from irp.cihaz import Cihaz
        c=Cihaz('K017','T',Saat(t(31,'09:00')))
        for key,age,state in [('eski',31,'GONDERILDI'),('sinir',30,'GONDERILDI'),('bekleyen',31,'BEKLIYOR'),('hata',31,'HATA')]:
            c.veri['gunluk'][key]=dict(durum=state,olay=dict(oldugu_an=(c.saat.simdi()-timedelta(days=age)).isoformat()))
        c.gunluk_temizle(); self.assertEqual(set(c.veri['gunluk']),{'sinir','bekleyen','hata'})

    def test_birim_kapasitesi_ve_fazla_mesai_ozeti(self):
        """T5/T8: birimin üç çalışanı × 9 saat; onaylı ek çalışma 18–19 = 1 saat."""
        from irp.gorunumler import etap_kapasitesi, birim_dolulugu
        from irp.gorunum_v7 import fazla_mesai_ozeti
        f=mesai_f(); d=kur(f,t(22,'19:01'))
        self.assertEqual(etap_kapasitesi(d,'IMALAT','2026-10-23','2026-10-23')['toplam']['kapasite'],27)
        self.assertEqual(birim_dolulugu(d,'2026-10-23','2026-10-23')['IMALAT']['kapasite'],27)
        self.assertEqual(fazla_mesai_ozeti(d,'K017','2026-10-01'),{'1.5':1})
