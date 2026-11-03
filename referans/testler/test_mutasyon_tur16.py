"""Mutasyonların gösterdiği tasarım sınırları; beklenenler yorumlarda kaynaklıdır."""
import unittest
from irp import an
from irp import Depo,Saat
from datetime import timedelta
from irp.gorunumler import adil_performans
from irp.gorunum_v10_1 import gantt,pencere,sapma
from .ortak import Duzenek,t,is_id
from .test_v7 import kur,gonder
from . import test_tur16 as destek


class MutasyonBosluklari(unittest.TestCase):
    def test_M024_parca_deseni_gecmise_yazilamaz(self):
        """Karar 46/56, T4 A17: ayar geçerliliği olay anından önce olamaz."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K001','AYAR.PARCA_KODU_DESENI',t(22,'09:00'),
               dict(deger='',gecerli_baslangic=t(22,'08:59')),bek='DURUM')

    def test_M027_bakim_baslangici_simdiden_sonra_olmali(self):
        """T8 §6: bakım ilerisi için planlanır; tam olay anında başlayamaz."""
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        g=dict(tezgah='CNC-02',baslangic=t(22,'09:00'),bitis=t(22,'10:00'),aciklama='Bakım')
        gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(22,'09:00'),g,bek='DURUM')
        gonder(f,d,'K009','TEZGAH.BAKIM_PLANLADIM',t(22,'09:00'),dict(g,baslangic=t(22,'09:01')))

    def test_M032_izin_okumasi_yalniz_hedef_kisinin_kayitlari(self):
        """Karar 63, T8 §1/5: kişisel izin görünümü başka kişiyi içermez."""
        from irp.gorunum_v7 import oku
        f=Duzenek(); d=kur(f,t(22,'09:00')); ids={}
        for k in ('K041','K044'):
            ids[k]=gonder(f,d,k,'IZIN.TALEP_ETTIM',t(22,'09:00'),
                          dict(kisi=k,tur='YILLIK',baslangic=t(26,'08:00'),bitis=t(26,'18:00'),gerekce='İzin'))
        for k in ids:
            self.assertEqual({x['kimlik'] for x in oku(d,k,'IZIN',k)},{ids[k]})

    def test_M033_mesainin_tam_bitisinde_gun_onayi_isi(self):
        """Karar 84/T9 §8: yöneticinin gün onayı işi mesai bitişinde açılır."""
        from irp.gorunum_v9 import gun_isleri
        f=Duzenek(); d=kur(f,t(22,'08:00'))
        birim=d.kisiler['K017']['birim']
        gonder(f,d,'K001','GUN_ONAYI.AYARLADIM',t(22,'08:01'),dict(birim=birim,gerekli=True,gecerli_baslangic='2026-10-22'))
        d.ilerlet(t(22,'17:59:59'))
        def var(): return any(x['tur']=='GUN_ONAYI' and x['birim']==birim and x['gun']=='2026-10-22' for x in gun_isleri(d,'K009'))
        self.assertFalse(var()); d.ilerlet(t(22,'18:00')); self.assertTrue(var())

    def test_M054_plan_baslangicinda_gecikme_yok(self):
        """T10 §1: başlamadı işareti plan başlangıcı geçince doğar."""
        d=Depo(Saat(t(22,'10:00'))); p,q=an(t(22,'10:00')),an(t(22,'11:00'))
        self.assertIsNone(sapma(d,'ACIK',p,q,None,None))
        d.saat.ilerlet(p+timedelta(microseconds=1))
        self.assertEqual(sapma(d,'ACIK',p,q,None,None),{'tur':'BASLAMADI'})

    def test_M095_gunluk_saat_is_gunu_ve_tatil(self):
        """Karar 56/T8 §2: 08–18 eksi bir saat mola = 9; tatil 0."""
        from irp.gorunumler import gunluk_saat
        f=Duzenek(); d=kur(f,t(22,'09:00'))
        self.assertEqual(gunluk_saat(d,'2026-10-26','K017'),9)
        self.assertEqual(gunluk_saat(d,'2026-10-29','K017'),0)

    def test_M112_acik_nesne_asamasinin_dakikalari(self):
        """T8 §12: top kimde görünümü mevcut aşamada geçen süreyi de toplar."""
        from .test_v10_1 import belge_duzenegi
        from irp.gorunum_v7 import top_kimde
        _,d,n,_=belge_duzenegi(); d.ilerlet(t(22,'09:52'))
        self.assertEqual(top_kimde(d,n)['asama_dakikalari'],{'CALISILIYOR':52})

    def test_M025_plan_yetki_tablosunda_uc_rol(self):
        """T10 olay tablosu: YONETICI, EKIP_LIDERI, YETKILI; kapsam FIRMA."""
        from irp.yetki_v6 import varsayilan_yetkiler
        row=next(x for x in varsayilan_yetkiler(10.1) if x['eylem_kodu']=='PLAN.TARIHLEDIM')
        self.assertEqual(set(row['kimler']),{'YONETICI','EKIP_LIDERI','YETKILI'})
        self.assertEqual(row['kapsam'],'FIRMA')

    def test_B59_davranis_kilidi_gantt_penceresinin_ucu(self):
        """DAVRANIS_KILIDI: T10 Gantt süzgecinin uç eşitliğini açıkça tanımlamaz."""
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58')
        f.is_olay('BASLADIM','08:00',4); f.is_olay('TAMAMLADIM','09:00',4)
        d=kur(f,t(22,'09:01'))
        self.assertNotIn(is_id(4),{x['kimlik'] for x in gantt(d,'2509084',t(22,'09:00'),t(22,'10:00'))})
        self.assertIn(is_id(4),{x['kimlik'] for x in gantt(d,'2509084',t(22,'08:59'),t(22,'09:01'))})
        self.assertEqual(pencere(t(22,'09:00'),t(22,'10:00')),(an(t(22,'09:00')),an(t(22,'10:00'))))

    def test_M002_elle_surenin_bitisi_olay_ani_olabilir(self):
        """T3/T4 elle süre: gelecekte olamaz; tam şimdi geçmiş pencerenin sonudur."""
        f=Duzenek(); f.ata(4); f.is_olay('MESAI.GIRDIM','07:58'); d=kur(f,t(22,'09:00'))
        gonder(f,d,'K009','IS.SURE_EKLEDIM',t(22,'09:00'),
               dict(baslangic=t(22,'08:45'),bitis=t(22,'09:00'),aciklama='Elle kayıt',is_bitti=False),
               4,adina='K017',giris_sekli='ELLE')
        rows=[x for x in d.araliklar if x['kisi']=='K017' and x.get('elle')]
        self.assertEqual([(x['baslangic'],x['bitis']) for x in rows],[(an(t(22,'08:45')),an(t(22,'09:00')))])

    def test_M003_onay_beklerken_arkadaki_isler_siralanabilir(self):
        """Karar 37.8/43/53: kilit yalnız ilk iş içindir; arka sıralar değişebilir."""
        f=Duzenek(); f.ata(9); f.ata(4,'K017',2); f.ata(5,'K017',3)
        f.is_olay('MESAI.GIRDIM','07:58'); f.is_olay('BASLADIM','08:00',9); f.is_olay('TAMAMLADIM','09:00',9)
        d=kur(f,t(22,'09:10'))
        self.assertEqual(d.isler[is_id(9)]['durum'],'ONAY_BEKLIYOR')
        gonder(f,d,'K009','IS.SIRALADIM',t(22,'09:11'),dict(kisi='K017',yeni_sira=2),5)
        self.assertEqual(d.listeler['K017'],[is_id(9),is_id(5),is_id(4)])

    def test_M015_onaylayanin_cozum_suresi_dogustan_onaya(self):
        """Karar 4.3; T4 A16: teslim 09:00, onay 09:01, süre 1/60 saattir."""
        destek.OnayGoreviMaliyeti.setUp(self)
        self.assertEqual(adil_performans(self.d,'K012','2026-10-22','2026-10-22')['cozum_saatleri'],[1/60])
