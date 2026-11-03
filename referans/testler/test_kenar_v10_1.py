"""T10 kenarları: yetki, atomiklik, eşzamanlılık ve kalıcı bildirim."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from irp import an, Depo, Saat
from irp.kabul import nesne
from irp.gorunum_v7 import oku
from irp.gorunum_v10_1 import gantt, plan_cakismalari, gecerli_surum, surumler
from irp.gorunum_v9 import okunmamis_bildirimler
from irp.modul_bildirimi import kimlik
from .ortak import Duzenek, t, is_id, yaz
from .test_v7 import kur, gonder
from .test_v10 import proje_duzenegi
from .test_v10_1 import ek_yetki, plan, tarih, belge_turu, belge_duzenegi, surum_olayi, modul_duzenegi, birak


class PlanKenarlari(unittest.TestCase):
    def setUp(self):
        self.f=ek_yetki(Duzenek()); self.f.ata(1); self.f.ata(2,sira=2)
        self.d=kur(self.f,t(21,'17:00'))

    def planla(self):
        tarih(self.f,self.d,[plan(i,t(22,'08:00'),t(22,'11:00')) for i in (1,2)],t(21,'17:01'))

    def test_devir_cakismayi_yeni_listeye_tasir(self):
        self.planla(); self.assertEqual(len(plan_cakismalari(self.d,'K017','2026-10-22')),1)
        gonder(self.f,self.d,'K009','IS.DEVRETTIM',t(21,'17:02'),dict(kimden='K017',kime='K023',kime_sira=1),1)
        self.assertEqual(plan_cakismalari(self.d,'K017','2026-10-22'),[])
        gonder(self.f,self.d,'K009','IS.DEVRETTIM',t(21,'17:03'),dict(kimden='K017',kime='K023',kime_sira=2),2)
        self.assertEqual(len(plan_cakismalari(self.d,'K023','2026-10-22')),1)

    def test_iptal_plani_korur_cakismadan_cikarir(self):
        self.planla(); once=self.d.isler[is_id(1)]['planlanan_baslangic']
        gonder(self.f,self.d,'K009','IS.IPTAL_ETTIM',t(21,'17:02'),dict(gerekce='İptal'),1)
        self.assertEqual(self.d.isler[is_id(1)]['planlanan_baslangic'],once)
        self.assertEqual(plan_cakismalari(self.d,'K017','2026-10-22'),[])
        tarih(self.f,self.d,[plan(1,t(23),t(23,'09:00'))],t(21,'17:03'),bek='DURUM')

    def test_tezgah_kesismesi_ve_uc_uca(self):
        tarih(self.f,self.d,[plan(i,t(22),t(22,'11:00')) for i in (7,8)],t(21,'17:01'))
        self.assertEqual(len(plan_cakismalari(self.d,'CNC-02','2026-10-22')),1)
        tarih(self.f,self.d,[plan(8,t(22,'11:00'),t(22,'12:00'))],t(21,'17:02'))
        self.assertEqual(plan_cakismalari(self.d,'CNC-02','2026-10-22'),[])

    def test_olmayan_hedef_topluyu_atomik_reddeder(self):
        self.planla(); once=deepcopy(self.d.isler)
        tarih(self.f,self.d,[plan(1,t(23),t(23,'09:00')),plan('YOK',t(23),t(23,'09:00'))],t(21,'17:02'),bek='DURUM')
        self.assertEqual(self.d.isler,once)

    def test_eksik_ve_bayat_hedef_surumu(self):
        self.planla(); z=t(21,'17:02'); self.d.ilerlet(z)
        self.f.olay('K004','PLAN.TARIHLEDIM',z,girdiler=dict(hedefler=[plan(1,t(23),t(23,'09:00'))]))
        self.assertEqual(yaz(self.d,self.f.olaylar[-1])['kod'],'BAYAT')
        e=deepcopy(self.f.olaylar[-1]); e['neyin_ustunde']=[dict(tur='IS',kimlik=is_id(1),surum='x'*64)]
        self.assertEqual(yaz(self.d,e,taze=False)['kod'],'BAYAT')

    def test_uyeler_payload_projesi_de_denetlenir(self):
        f=ek_yetki(proje_duzenegi()); d=kur(f,t(22,'12:00'))
        z=t(22,'12:01'); d.ilerlet(z)
        f.olay('K007','PLAN.TARIHLEDIM',z,girdiler=dict(hedefler=[plan(2,t(23),t(23,'10:00'))]))
        self.assertEqual(yaz(d,f.olaylar[-1])['kod'],'YETKI')

    def test_projesiz_gorev_veren_ve_ustleri(self):
        f,d=self.f,self.d
        oid=gonder(f,d,'K012','GOREV.ATADIM',t(21,'17:01'),dict(gorevler=[f.gorev_satiri(nereye='PROJE_DISI',kategori='PD.EGITIM_GELISIM',proje=None,etap=None)]))+'/1'
        tarih(f,d,[plan(oid,t(22),t(22,'09:00'),'GOREV')],t(21,'17:02'),kim='K004',bek='YETKI')
        tarih(f,d,[plan(oid,t(22),t(22,'09:00'),'GOREV')],t(21,'17:03'),kim='K012')

    def test_atamada_plan_ve_gecersiz_aralik(self):
        f,d=self.f,self.d
        gonder(f,d,'K012','GOREV.ATADIM',t(21,'17:01'),dict(gorevler=[f.gorev_satiri(planlanan_baslangic=t(23))]),bek='BICIM')
        oid=gonder(f,d,'K012','GOREV.ATADIM',t(21,'17:02'),dict(gorevler=[f.gorev_satiri(planlanan_baslangic=t(22),planlanan_bitis=t(22,'09:00'))]))+'/1'
        self.assertEqual(plan_cakismalari(d,'K041','2026-10-22'),[])
        self.assertEqual(next(x for x in gantt(d,'2509084','2026-10-22') if x['kimlik']==oid)['planlanan_bitis'],an(t(22,'09:00')))

    def test_esit_aralik_ve_tekrar_hedef_bicim(self):
        h=plan(1,t(22),t(22))
        tarih(self.f,self.d,[h],t(21,'17:01'),bek='BICIM')
        h=plan(1,t(22),t(22,'09:00'))
        tarih(self.f,self.d,[h,h],t(21,'17:02'),bek='BICIM')

    def test_kisisel_gorunum_suzgeci(self):
        self.planla()
        c=plan_cakismalari(self.d,'K017','2026-10-22',cagiran='K041')
        self.assertEqual(len(c),1)
        self.assertEqual(c[0]['hedefler'],[{'tur':'ERISIM_DISI'},{'tur':'ERISIM_DISI'}])
        self.assertFalse(any(x['tur']=='IS' for x in gantt(self.d,'2509084','2026-10-22',cagiran='K041')))

    def test_gantt_onayli_etap_plani_ve_geride(self):
        self.planla()
        gonder(self.f,self.d,'K004','PLAN.ONAYLADIM',t(21,'17:02'),dict(proje='2509084'))
        etap=self.f.etap['E-IML']
        gonder(self.f,self.d,'K004','ETAP.DEGISTIRDIM',t(21,'17:03'),dict(degisenler=dict(baslangic='2026-10-22',bitis='2026-10-23')),etap,'ETAP')
        self.d.ilerlet(t(22,'12:00'))
        rows={x['kimlik']:x for x in gantt(self.d,'2509084','2026-10-22','2026-12-30')}
        self.assertEqual(rows[etap]['planlanan_baslangic'],an('2026-11-02T00:00:00+03:00'))
        self.assertEqual(rows[is_id(1)]['sapma'],dict(tur='GERIDE'))


class SurumKenarlari(unittest.TestCase):
    def setUp(self): self.f,self.d,self.n,self.g=belge_duzenegi()

    def ekle(self,no=1,z=None,**kw):
        return surum_olayi(self.f,self.d,self.n,'EKLEDIM',z or t(22,'10:00'),kim='K041',no=no,**kw)

    def onay(self,no=1,z=None,**kw):
        return surum_olayi(self.f,self.d,self.n,'ONAYLADIM',z or t(22,'11:00'),no=no,**kw)

    def test_en_buyuk_onayli_numara_ve_r43(self):
        self.ekle(); self.ekle(2,t(22,'10:01')); self.onay(2)
        self.onay(1,t(22,'11:01'))
        self.assertEqual(gecerli_surum(self.d,self.n)['surum_no'],2)
        self.assertEqual(len([x for x in self.d.bildirimler.values() if x['kural']=='R43']),1)

    def test_son_onayi_geri_cekmek_yok_uretmesi(self):
        self.ekle(); self.onay()
        surum_olayi(self.f,self.d,self.n,'GERI_CEKTIM',t(22,'11:01'))
        self.assertIsNone(gecerli_surum(self.d,self.n))
        self.assertEqual(len([x for x in self.d.bildirimler.values() if x['kural']=='R43']),2)

    def test_taslagi_geri_cekmek_r43_uretmez(self):
        self.ekle(); surum_olayi(self.f,self.d,self.n,'GERI_CEKTIM',t(22,'10:01'))
        self.assertFalse(any(x['kural']=='R43' for x in self.d.bildirimler.values()))
        self.onay(z=t(22,'10:02'),bek='DURUM')

    def test_yeni_tur_yetkisi_eski_taslakta_gecerli(self):
        self.ekle()
        r=dict(kimler=['IK'],kapsam='FIRMA')
        gonder(self.f,self.d,'K001','NESNE_TURU.TANIMLADIM',t(22,'10:01'),belge_turu(surum_onaylayanlar=r))
        self.assertEqual(len(surumler(self.d,self.n,cagiran='K012')),1)  # Karar 99: üst okur, güncel tür yetkisi onayı belirler.
        self.onay(z=t(22,'10:02'),bek='YETKI')
        self.assertEqual(len(surumler(self.d,self.n,cagiran='K041')),1)

    def test_taslak_dosyasi_dogrudan_okunamaz(self):
        self.ekle()
        with self.assertRaises(PermissionError): oku(self.d,'K044','DOSYA','F-1')
        self.assertEqual(oku(self.d,'K012','DOSYA','F-1')['dosya_kimligi'],'F-1')
        self.onay(); self.assertEqual(oku(self.d,'K044','DOSYA','F-1')['dosya_kimligi'],'F-1')

    def test_bilinmeyen_dosya_durum(self):
        z=t(22,'10:00')
        gonder(self.f,self.d,'K041','NESNE.SURUM_EKLEDIM',z,dict(hedef=self.n,dosyalar=['YOK']),self.n,'NESNE',bek='DURUM')

    def test_kendi_geri_cekme_yetkisi_yok(self):
        self.ekle()
        surum_olayi(self.f,self.d,self.n,'GERI_CEKTIM',t(22,'10:01'),kim='K041',bek='YETKI')

    def test_varsayilan_ad_tekilligi(self):
        self.ekle(ad='2'); self.ekle(2,t(22,'10:01'),bek='DURUM')
        self.assertEqual(len(self.d.nesne_surumleri),1)

    def test_ayni_anda_ekle_onay_ve_ters_kaynak(self):
        z=t(22,'10:00'); self.ekle(z=z); self.onay(z=z,bek='BAYAT')
        self.assertIsNone(gecerli_surum(self.d,self.n))
        self.onay(z=t(22,'10:01'))
        self.assertEqual(gecerli_surum(self.d,self.n)['surum_no'],1)
        once=deepcopy(self.d.nesne_surumleri)
        self.d._kayitlar=dict(reversed(list(self.d._kayitlar.items())))
        self.d.yeniden_kur(); self.assertEqual(self.d.nesne_surumleri,once)
        self.assertFalse(self.d.supheliler)

    def test_eszamanli_taze_isteklerden_yalniz_biri_kabul(self):
        self.ekle(); z=t(22,'11:00'); self.d.ilerlet(z)
        self.f.olay('K012','NESNE.SURUM_ONAYLADIM',z,self.n,dict(hedef=self.n,surum_no=1),tur='NESNE')
        self.f.olay('K041','NESNE.SURUM_EKLEDIM',z,self.n,dict(hedef=self.n,dosyalar=['F-2']),tur='NESNE',kanit=[dict(dosya_kimligi='F-2',parmak_izi='abc')])
        es=deepcopy(self.f.olaylar[-2:])
        for e in es:
            for h in e['neyin_ustunde']: h['surum']=nesne(self.d,h['tur'],h['kimlik'])['surum']
        with ThreadPoolExecutor(max_workers=2) as pool: rs=list(pool.map(lambda e:self.d.olay_ekle(e,oturum=e['kim']),es))
        self.assertEqual(sorted(r.get('kod',r['sonuc']) for r in rs),['BASARILI','BAYAT'])
        self.assertFalse(self.d.isleme_hatalari)

    def test_gecmiste_gecerli_surum(self):
        self.ekle(); self.onay(); self.ekle(2,t(23,'09:00')); self.onay(2,t(23,'10:00'))
        self.assertEqual(gecerli_surum(self.d,self.n,t(22,'11:05'))['surum_no'],1)

    def test_gecmis_sorgusu_guncel_erisim_kaybini_asamaz(self):
        self.ekle(); self.onay()
        gonder(self.f,self.d,'K001','AYAR.DEGISTIRDIM',t(22,'12:00'),dict(anahtar='proje_gorunurlugu',deger='UYELER'))
        self.assertIsNone(oku(self.d,'K007','GECERLI_SURUM',self.n,t=t(22,'11:05')))

    def test_gec_gelen_surume_numara_kabulde_verilir(self):
        self.ekle(ad='R0'); self.onay()
        self.f.olay('K041','NESNE.SURUM_EKLEDIM',t(22,'09:59'),self.n,dict(hedef=self.n,dosyalar=['F-yeni'],surum_adi='R1'),tur='NESNE',kanit=[dict(dosya_kimligi='F-yeni',parmak_izi='xyz')])
        self.assertEqual(yaz(self.d,self.f.olaylar[-1]),dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))
        self.assertEqual([(s['surum_no'],s['surum_adi'],s['durum']) for s in surumler(self.d,self.n)],[(1,'R0','ONAYLI')])
        self.assertEqual(gecerli_surum(self.d,self.n)['surum_adi'],'R0')
        self.d.yeniden_kur(); self.assertEqual(gecerli_surum(self.d,self.n)['surum_adi'],'R0')

    def test_onaydan_onceye_geri_cekme_yazilamaz(self):
        self.ekle(); self.onay()
        self.f.olay('K012','NESNE.SURUM_GERI_CEKTIM',t(22,'10:30'),self.n,dict(hedef=self.n,surum_no=1,gerekce='Geç yazıldı'),tur='NESNE')
        self.assertEqual(yaz(self.d,self.f.olaylar[-1]),dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))

    def test_nesne_dogumundan_once_surum_yok(self):
        self.f.olay('K041','NESNE.SURUM_EKLEDIM',t(22,'08:59'),self.n,dict(hedef=self.n,dosyalar=['F-yeni']),tur='NESNE',kanit=[dict(dosya_kimligi='F-yeni',parmak_izi='xyz')])
        self.assertEqual(yaz(self.d,self.f.olaylar[-1]),dict(sonuc='REDDEDILDI',kod='BAYAT',neden='SIRA'))

    def test_gelecekteki_surume_numara_ayrilmaz(self):
        self.f.olay('K041','NESNE.SURUM_EKLEDIM',t(22,'10:00'),self.n,dict(hedef=self.n,dosyalar=['F-yeni']),tur='NESNE',kanit=[dict(dosya_kimligi='F-yeni',parmak_izi='xyz')])
        self.assertEqual(yaz(self.d,self.f.olaylar[-1])['kod'],'BICIM')
        self.assertEqual(self.d.nesne_surumleri,{})

    def test_istemci_surum_numarasi_atayamaz(self):
        self.d.ilerlet(t(22,'10:00'))
        self.f.olay('K041','NESNE.SURUM_EKLEDIM',t(22,'10:00'),self.n,dict(hedef=self.n,dosyalar=['F-yeni']),tur='NESNE',kanit=[dict(dosya_kimligi='F-yeni',parmak_izi='xyz')],nesne_surum_no=999,kabul_sirasi=999)
        self.assertEqual(yaz(self.d,self.f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(surumler(self.d,self.n)[0]['surum_no'],1)

    def test_biten_gorev_r43_almaz(self):
        gonder(self.f,self.d,'K044','GOREV.TAMAMLADIM',t(22,'09:51'),{},self.g,'GOREV')
        self.ekle(); self.onay()
        self.assertFalse(any(x['kural']=='R43' for x in self.d.bildirimler.values()))

    def test_ikinci_nesne_bagi_da_r43_uretir(self):
        n=gonder(self.f,self.d,'K012','NESNE.ACTIM',t(22,'09:51'),dict(tur='BELGE',ad='İkinci resim',sorumlu='K041',proje='2509084'))
        gonder(self.f,self.d,'K012','GOREV.ATADIM',t(22,'09:52'),dict(gorevler=[self.f.gorev_satiri(kisi='K044')]),[dict(tur='NESNE',kimlik=k) for k in (self.n,n)])
        surum_olayi(self.f,self.d,n,'EKLEDIM',t(22,'10:00'),kim='K041')
        surum_olayi(self.f,self.d,n,'ONAYLADIM',t(22,'11:00'))
        self.assertEqual([x['alici'] for x in self.d.bildirimler.values() if x['kural']=='R43'],['K044'])

    def test_ozel_onay_taniminda_ust_taslagi_okur(self):
        self.ekle()
        gonder(self.f,self.d,'K001','NESNE_TURU.TANIMLADIM',t(22,'10:01'),belge_turu(surum_onaylayanlar=dict(kimler=['IK'],kapsam='FIRMA')))
        self.assertEqual(oku(self.d,'K012','DOSYA','F-1')['dosya_kimligi'],'F-1')
        self.assertTrue(any(e['eylem_kodu']=='NESNE.SURUM_EKLEDIM' for e in oku(self.d,'K001','HAM_OLAY','K001')))

    def test_uyeler_projeyi_gormeyen_sorumlu_ekleyemez(self):
        self.ekle()
        gonder(self.f,self.d,'K001','AYAR.DEGISTIRDIM',t(22,'10:01'),dict(anahtar='proje_gorunurlugu',deger='UYELER'))
        self.ekle(2,t(22,'10:02'),bek='YETKI')  # K041'in projede işi veya ek erişimi yok.


class ModulKenarlari(unittest.TestCase):
    def setUp(self): self.f,self.d=modul_duzenegi()

    def gor(self):
        birak(self.d,t(22,'10:00'))
        key=next(k for k,x in self.d.modul_bildirimleri.items() if x['alici']=='K009')
        gonder(self.f,self.d,'K009','BILDIRIM.GORDUM',t(22,'10:01'),dict(bildirimler=[key]))
        return key

    def kaldir(self,z=t(22,'10:02')):
        self.d.ilerlet(z)
        return self.d.modul_bildirimi_kaldir('SRV-M3','M3','SIPARIS_GECIKTI',dict(tur='IS',kimlik=is_id(4)),z)

    def test_pasif_modul_eski_kayit_kalir_yeni_red_kaldirma_acik(self):
        birak(self.d,t(22,'10:00'))
        gonder(self.f,self.d,'K001','MODUL.TANIMLADIM',t(22,'10:01'),dict(kod='M3',ad='M3',servis_kimligi='SRV-M3',aktif=False))
        self.assertEqual(birak(self.d,t(22,'10:02'))['kod'],'YETKI')
        self.assertEqual(len([x for x in okunmamis_bildirimler(self.d,'K006') if x.get('kaynak')=='M3']),1)
        self.assertEqual(self.kaldir(t(22,'10:03'))['kaldirilan'],2)

    def test_erisimi_kaldirilan_kiside_kutu_gizlenir(self):
        f,d=modul_duzenegi(True); p='2509091'
        gonder(f,d,'K004','PROJE.ERISIM_VERDIM',t(22,'10:00'),dict(proje=p,kisi='K006',gerekce='İnceleme'))
        r=birak(d,t(22,'10:01'),kayit=dict(tur='PROJE',kimlik=p),alicilar=[dict(tur='KISI',kimlik='K006')]); self.assertEqual(r['yeni'],1)
        gonder(f,d,'K004','PROJE.ERISIM_KALDIRDIM',t(22,'10:02'),dict(proje=p,kisi='K006',gerekce='Bitti'))
        self.assertFalse(any(x.get('kaynak')=='M3' for x in okunmamis_bildirimler(d,'K006')))
        self.assertEqual(len(d.modul_bildirimleri),1); self.assertTrue(next(iter(d.modul_bildirimleri.values()))['gecerli'])

    def test_tekrar_metni_degistirir_gorulmeyi_korur(self):
        key=self.gor(); birak(self.d,t(22,'10:02'),metin='Yeni',onem='BILGI')
        self.assertEqual((self.d.modul_bildirimleri[key]['metin'],self.d.modul_bildirimleri[key]['gorulme_ani']),('Yeni',an(t(22,'10:01'))))

    def test_tekrar_yeni_alici_ekler(self):
        self.gor(); r=birak(self.d,t(22,'10:02'),alicilar=[dict(tur='KISI',kimlik='K041')])
        self.assertEqual(r['yeni'],1); self.assertEqual(len(self.d.modul_bildirimleri),3)

    def test_kaldirilan_anahtar_yeniden_etkin_ayni_gorulme(self):
        key=self.gor(); self.kaldir(); birak(self.d,t(22,'10:03'))
        self.assertEqual(len(self.d.modul_bildirimleri),2)
        self.assertEqual(self.d.modul_bildirimleri[key]['gorulme_ani'],an(t(22,'10:01')))

    def test_gec_gordum_kaldirma_sonrasi_tarihsel_gorulme(self):
        birak(self.d,t(22,'10:00')); self.kaldir()
        key=next(k for k,x in self.d.modul_bildirimleri.items() if x['alici']=='K009')
        self.f.olay('K009','BILDIRIM.GORDUM',t(22,'10:01'),girdiler=dict(bildirimler=[key]))
        self.assertEqual(yaz(self.d,self.f.olaylar[-1])['sonuc'],'BASARILI')
        self.assertEqual(self.d.modul_bildirimleri[key]['gorulme_ani'],an(t(22,'10:01')))

    def test_baskasinin_gordum_olayi_yetkisiz(self):
        key=self.gor()
        gonder(self.f,self.d,'K006','BILDIRIM.GORDUM',t(22,'10:02'),dict(bildirimler=[key]),bek='YETKI')

    def test_bos_alici_ve_onem_ve_kayit_kapilari(self):
        for kw,kod in [(dict(alicilar=[]),'BICIM'),(dict(onem='ACIL'),'BICIM'),(dict(metin=' '),'BICIM'),(dict(kayit=dict(tur='IS',kimlik='YOK')),'DURUM'),(dict(alicilar=[dict(tur='YOK',kimlik='K001')]),'BICIM')]:
            self.assertEqual(birak(self.d,t(22,'10:00'),**kw)['kod'],kod)
        self.assertEqual(self.d.modul_bildirimleri,{})

    def test_an_gecmis_olabilir_gelecek_olamaz(self):
        self.assertEqual(birak(self.d,t(22,'10:00'),an=t(23))['kod'],'BICIM')
        r=birak(self.d,t(22,'10:01'),an=t(21)); self.assertEqual(r['yeni'],2)
        self.assertEqual({x['birakma_ani'] for x in self.d.modul_bildirimleri.values()},{an(t(22,'10:01'))})

    def test_butun_alici_turleri_ve_tekillik(self):
        f,d=self.f,self.d
        gonder(f,d,'K001','NESNE_TURU.TANIMLADIM',t(22,'09:01'),belge_turu())
        n=gonder(f,d,'K012','NESNE.ACTIM',t(22,'09:02'),dict(tur='BELGE',ad='N',sorumlu='K041',proje='2509084'))
        rs=[dict(tur='ROL',kimlik='BEYAZ_YAKA'),dict(tur='NESNE_SORUMLUSU',kimlik=n),dict(tur='PROJEDE_YETKILILER',kimlik='2509084')]
        r=birak(d,t(22,'10:00'),alicilar=rs)
        self.assertIn('K041',r['alicilar']); self.assertIn('K001',r['alicilar'])
        self.assertEqual(len(r['alicilar']),len(set(r['alicilar'])))

    def test_istihdam_disi_alici_elendigi(self):
        gonder(self.f,self.d,'K001','KISI.AYRILDI',t(22,'09:01'),dict(kisi='K006',ayrilis_tarihi='2026-10-22'))
        r=birak(self.d,t(23,'10:00'),alicilar=[dict(tur='KISI',kimlik='K006')])
        self.assertTrue(r['alici_kalmadi'])

    def test_servis_kimligi_moduller_arasi_tekil(self):
        gonder(self.f,self.d,'K001','MODUL.TANIMLADIM',t(22,'09:01'),dict(kod='M9',ad='M9',servis_kimligi='SRV-M3',aktif=True),bek='DURUM')

    def test_anahtar_bolumleri_cakismiyor(self):
        h=dict(tur='PROJE',kimlik='A/B')
        self.assertNotEqual(kimlik('M3','A/B',h,'K001'),kimlik('M3/A','B',h,'K001'))
        self.assertNotEqual(kimlik('M3','X',h,'K001'),kimlik('M3','X',dict(tur='NESNE',kimlik='A/B'),'K001'))

    def test_cekirdek_kaynak_adi_ayrilmis(self):
        gonder(self.f,self.d,'K001','MODUL.TANIMLADIM',t(22,'09:01'),dict(kod='CEKIRDEK',ad='A',servis_kimligi='SRV-A',aktif=True),bek='BICIM')

    def test_kapi_kaynaklara_girmez_tam_kurulumda_korunur(self):
        self.gor(); once=deepcopy(self.d.modul_bildirimleri)
        ids=set(self.d.olaylar); self.d.yeniden_kur()
        self.assertEqual(self.d.modul_bildirimleri,once); self.assertEqual(set(self.d.olaylar),ids)
        self.assertTrue(set(self.d.modul_bildirimleri).isdisjoint(self.d.olay_nesneleri))
        z=Depo(Saat(self.d.saat.simdi()),'tam'); z._kayitlar=deepcopy(self.d._kayitlar); z.yeniden_kur()
        self.assertEqual(z.modul_bildirimleri,{})  # Olaylardan modül bildirimi üretilemez.
