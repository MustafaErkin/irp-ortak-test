"""Haritada kalan olay/ret boşlukları: geçerli kimlik ve yetkiyle durum kapısı."""
import unittest
from copy import deepcopy
from irp import Depo,Saat
from .ortak import Duzenek,t,is_id
from .test_v7 import kur,gonder


class DurumKapilari(unittest.TestCase):
    def test_yonlendirme_var_olmayan_kisiye_yapilamaz(self):
        """T3/T4 yönlendirme: alıcılar aktif firma kişileri olmalıdır."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K012','AYAR.YONLENDIRDIM',t(22,'09:01'),dict(birim='MEK_TASARIM',kisiler=['K999']),bek='DURUM')

    def test_gorev_onay_ret_ve_iptal_durumlari(self):
        """T3 görev: teslim edilmemiş görev onay/ret; iptal edilmiş görev yeniden iptal alamaz."""
        f=Duzenek(); g=f.gorev_ata(t(22,'08:00'),onay_gerekli=True,onaylayan='K012'); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K012','GOREV.ONAYLADIM',t(22,'09:01'),{},g,'GOREV',bek='DURUM')
        gonder(f,d,'K012','GOREV.REDDETTIM',t(22,'09:02'),{'not':'Teslim yok','revizyon_ver':False},g,'GOREV',bek='DURUM')
        gonder(f,d,'K012','GOREV.IPTAL_ETTIM',t(22,'09:03'),dict(gerekce='Kapsamdan çıktı'),g,'GOREV')
        gonder(f,d,'K012','GOREV.IPTAL_ETTIM',t(22,'09:04'),dict(gerekce='İkinci iptal'),g,'GOREV',bek='DURUM')

    def test_gun_kaldirma_ve_onay_ayari_gecmise_yazilamaz(self):
        """T8 gün istisnası ileri gün; T9 gün onayı ayarı en erken bugündür."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','GUN.KALDIRDIM',t(22,'09:01'),dict(tarih='2026-10-21'),bek='DURUM')
        gonder(f,d,'K001','GUN_ONAYI.AYARLADIM',t(22,'09:02'),dict(birim='IMALAT',gerekli=True,gecerli_baslangic='2026-10-21'),bek='DURUM')

    def test_is_devam_ret_ve_iptal_durumlari(self):
        """T3: devam izni arıza, ret onay bekleme ister; iptal tekrarlanmaz."""
        f=Duzenek(); f.ata(4); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K009','IS.DEVAM_ONAYLADIM',t(22,'09:01'),{},4,bek='DURUM')
        gonder(f,d,'K009','IS.REDDETTIM',t(22,'09:02'),{'not':'Teslim yok'},4,bek='DURUM')
        gonder(f,d,'K004','IS.IPTAL_ETTIM',t(22,'09:03'),dict(gerekce='Kapsamdan çıktı'),4)
        gonder(f,d,'K004','IS.IPTAL_ETTIM',t(22,'09:04'),dict(gerekce='İkinci iptal'),4,bek='DURUM')

    def test_izinde_ik_sirasi_ve_kapanmis_kayit(self):
        """T8 izin: önce yönetici sonra İK; iptal kaydına ret veya ikinci iptal yok."""
        f=Duzenek()
        next(e['girdiler'] for e in f.olaylar if e['eylem_kodu']=='KISI.EKLEDIM' and e['girdiler']['kod']=='K007')['roller']=['YONETICI','IK']
        d=kur(f,t(22,'09:00'))
        key=gonder(f,d,'K017','IZIN.TALEP_ETTIM',t(22,'09:01'),dict(kisi='K017',tur='YILLIK',baslangic=t(23,'08:00'),bitis=t(23,'18:00'),gerekce='İzin'))
        gonder(f,d,'K007','IZIN.IK_ONAYLADIM',t(22,'09:02'),dict(hedef=key),bek='DURUM')
        gonder(f,d,'K017','IZIN.IPTAL_ETTIM',t(22,'09:03'),dict(hedef=key))
        gonder(f,d,'K009','IZIN.IPTAL_ETTIM',t(22,'09:04'),dict(hedef=key),bek='DURUM')
        gonder(f,d,'K009','IZIN.REDDETTIM',t(22,'09:05'),dict(hedef=key,gerekce='Kayıt kapalı'),bek='DURUM')

    def test_kapali_kurulumun_bitis_olayi_aktarimla_tekrarlanamaz(self):
        """Karar 54: kurulum kapandıktan sonra AKTARIM yetkisi kapanır."""
        from .v5_destek import kurulum_paketi
        f=Duzenek(False); events=kurulum_paketi(f); d=Depo(Saat(t(1,'07:00')))
        self.assertEqual(d.kurulum(events,{},servis=True)['sonuc'],'BASARILI')
        e=deepcopy(next(e for e in events if e['eylem_kodu']=='KURULUM.TAMAMLADIM'))
        e['giris_sekli']='AKTARIM'
        self.assertEqual(d.olay_ekle(e,servis=True).get('kod'),'YETKI')

    def test_nesnenin_sorumlusu_firmada_bulunmali(self):
        """T8 nesne güncelleme: sorumlu var olan bir kişidir."""
        from .test_v10_1 import belge_duzenegi
        f,d,n,_=belge_duzenegi()
        gonder(f,d,'K012','NESNE.GUNCELLEDIM',t(22,'10:00'),dict(hedef=n,degisenler=dict(sorumlu='K999')),n,'NESNE',bek='DURUM')

    def test_proje_erisiminin_kisisi_ve_kaldirilacak_kaydi_olmali(self):
        """T9 §6: erişim var olan kişiye verilir; olmayan açık erişim kaldırılamaz."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','PROJE.ERISIM_VERDIM',t(22,'09:01'),dict(proje='2509084',kisi='K999',gerekce='Erişim'),bek='DURUM')
        gonder(f,d,'K001','PROJE.ERISIM_KALDIRDIM',t(22,'09:02'),dict(proje='2509084',kisi='K041',gerekce='Erişim'),bek='DURUM')

    def test_proje_kodu_baska_projenin_koduyla_cakisamaz(self):
        """T9 §1: kod/ek çifti geçmiş dahil tekildir."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','PROJE.KOD_DEGISTIRDIM',t(22,'09:01'),dict(kod='2509091',ek=None,gerekce='Çakışma'),'2509084','PROJE',bek='DURUM')

    def test_sorumlulukta_itiraz_durumu_korunur(self):
        """T8 §9: açılmamış itiraz değerlendirilemez; açık itiraz yeniden açılamaz."""
        f=Duzenek(); g=f.gorev_ata(t(22,'08:00'),onay_gerekli=True,onaylayan='K012')
        f.gorev_olay('KABUL_ETTIM',t(22,'08:10'),g); f.gorev_olay('TAMAMLADIM',t(22,'09:00'),g)
        d=kur(f,t(22,'09:01'))
        key=gonder(f,d,'K012','GOREV.REDDETTIM',t(22,'09:02'),{'not':'Hata','revizyon_ver':False,'sorumlular':[dict(tur='KISI',kimlik='K041',yuzde=100)]},g,'GOREV')+'/1'
        gonder(f,d,'K012','SORUMLULUK.ITIRAZI_DEGERLENDIRDIM',t(22,'09:03'),dict(hedef=key,karar='RET',gerekce='Henüz itiraz yok'),bek='DURUM')
        gonder(f,d,'K041','SORUMLULUK.ITIRAZ_ETTIM',t(22,'09:04'),dict(hedef=key,gerekce='İtiraz'))
        gonder(f,d,'K041','SORUMLULUK.ITIRAZ_ETTIM',t(22,'09:05'),dict(hedef=key,gerekce='İkinci itiraz'),bek='DURUM')

    def test_baslamis_bakim_iptali_ve_bugune_tezgah_takvimi_reddedilir(self):
        """T8 §6: bakım başlamadan iptal; tezgâh takvimi ileri tarihlidir."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K009','TEZGAH.TAKVIM_TANIMLADIM',t(22,'09:01'),dict(tezgah='CNC-02',gecerli_baslangic='2026-10-22',vardiyalar=[dict(bas='08:00',bit='18:00',gunler=[1,2,3,4,5])]),bek='DURUM')
        key=gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(22,'09:02'),dict(tezgah='CNC-02',baslangic=t(23,'09:00'),bitis=t(23,'10:00'),aciklama='Bakım'))
        gonder(f,d,'K009','TEZGAH.BAKIM_IPTAL_ETTIM',t(23,'09:00'),dict(hedef=key),bek='DURUM')

    def test_yetki_tablosuna_bilinmeyen_rol_yazilamaz(self):
        """Karar 57/T3: yetki satırı aktif rol kodu veya tanımlı ilişki kullanır."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','YETKI.TANIMLADIM',t(22,'09:01'),dict(eylem_kodu='IS.ATADIM',kimler=['OLMAYAN_ROL'],kapsam='FIRMA'),bek='DURUM')
