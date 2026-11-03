"""Kaynaklar, A5 kabul kapısı ve A6 kapsamlı yeniden hesap."""
import json
from hashlib import sha256
from copy import deepcopy
from threading import RLock
from types import MappingProxyType
from .olay import kodla, bicim_kontrol, yetki_kontrol
from .saat import an
from .kabul import TANIKLIK, yetki, durum, nesne

class Depo:
    def __init__(self,saat,yontem='kapsamli'):
        self.saat=saat; self.yontem=yontem
        self._olaylar={}; self._icerikler={}; self._kayitlar={}
        self.modul_bildirimleri={}  # Motorun yeniden kurduğu tablolardan bağımsız kalıcı kaynak.
        self.isleme_hatalari=[]; self.hassas_ekler=[]; self.ay_kapanislari={}
        self.cihaz_esitlemeleri={}
        self.cihaz_harfleri={}
        self.kurulum_tamamlandi = False; self.kod_listeleri = {}
        self.gorunum=None; self._kilit=RLock(); self._surumler={}; self.olcumler=[]
        self.yeniden_kur()

    @property
    def olaylar(self): return MappingProxyType(deepcopy(self._kayitlar))

    def olay_ekle(self,olay,oturum=None,servis=False,hassas_ek=None):
        with self._kilit: return self._ekle(olay,oturum,servis,hassas_ek)

    def red(self,kod,neden): return {'sonuc':'REDDEDILDI','kod':kod,'neden':neden}

    def _ekle(self,olay,oturum,servis,hassas_ek):
        e=deepcopy(olay)
        e.pop('kabul_sirasi', None)  # Yalnız sunucu yazar.
        e.pop('nesne_surum_no', None)
        try:
            bicim_kontrol(e)
            from .kapilar_v5 import bicim
            bicim(self, e)
            from .kurallar_v9 import bicim as bicim_v9
            bicim_v9(self, e)
            from .kurallar_v10_1 import bicim as bicim_v10_1
            bicim_v10_1(self, e)
            from .kurallar_v10_2 import bicim as bicim_v10_2
            bicim_v10_2(self, e)
        except (ValueError,TypeError,KeyError) as h: return self.red('BICIM',str(h))
        if (self.kurulum_tamamlandi or getattr(self.gorunum, 'kurulum_kaynagi', None)) and e['giris_sekli'] == 'AKTARIM' and not self.saat.demo:
            return self.red('YETKI', 'Kurulum tamamlandi; normal yol gerekli')
        if e['eylem_kodu'] == 'KURULUM.TAMAMLADIM' and not getattr(self, '_kurulum_isle', False) and not self.saat.demo:
            return self.red('DURUM', 'Kurulum kapanisi yalniz atomik kurulum icinde')
        try:
            yetki_hali = self
            # Saat ilerlemisken gelecege planlanmis personel degisimi de yetkiye yansir.
            hesap_ani = getattr(self.gorunum, 'hesap_ani', self.saat.simdi())
            if any(x['eylem_kodu'] == 'KISI.DEGISTIRDIM' and hesap_ani < an(x['girdiler']['gecerli_baslangic']) <= self.saat.simdi() for x in self._kayitlar.values()):
                self.yeniden_kur()
            if e['eylem_kodu'] in TANIKLIK and e['giris_sekli'] != 'AKTARIM' and e['eylem_kodu'] != 'BILDIRIM.GORDUM':
                from .motor import Motor
                from .saat import Saat
                yetki_hali = Motor(Saat(e['oldugu_an']))
                sinir = (an(e['oldugu_an']),e['olay_kimligi'])
                yetki_hali.yurut([x for x in self._kayitlar.values() if (an(x['oldugu_an']),x['olay_kimligi']) < sinir])
            elif e['giris_sekli'] != 'AKTARIM' and an(e['oldugu_an']) != self.saat.simdi() and self.ayar('proje_gorunurlugu', an(e['oldugu_an']), 'HERKES') == 'UYELER':
                # Proje yönetim kapısı olay anındaki üyelikle de sınanır.
                from .motor import Motor
                from .saat import Saat
                from .kurallar_v10 import yetki as proje_yetkisi
                tarihsel = Motor(Saat(e['oldugu_an']))
                sinir = (an(e['oldugu_an']),e['olay_kimligi'])
                tarihsel.yurut([x for x in self._kayitlar.values() if (an(x['oldugu_an']),x['olay_kimligi']) < sinir])
                if proje_yetkisi(tarihsel,e) is False: raise PermissionError('Olay aninda proje yetkisi yok')
            kisi=yetki_hali.kisiler.get(oturum or e['kim'],{})
            yetki_kontrol(e,oturum or e['kim'],kisi.get('roller',[]),servis)
            from .kurallar_v10_2 import cihaz_izni
            if not cihaz_izni(self, e): raise PermissionError('Modul cihaz harfi')
            if not yetki(yetki_hali,e,servis):
                # V5 tarihsel aktarimin tanisi korunur. Gercek V6 kurulumu
                # kendi tablo olaylarini tasir ve genel yetki tanisini alir.
                if e.get('adina') and 'EKIP_LIDERI' not in kisi.get('roller', []) and not any(r.get('doguran_olay') for r in yetki_hali.yetki_kurallari):
                    raise PermissionError('Adina yalniz ekip lideri')
                raise PermissionError('T3 yetki matrisi')
            if self.saat.demo and not servis and e['eylem_kodu']!='AYAR.SAAT_KAYDIRDIM': raise PermissionError('Demo yeni girdi almaz')
            if hassas_ek is not None and not servis and 'YETKILI' not in kisi.get('roller',[]): raise PermissionError('Hassas ek')
            if e['eylem_kodu']=='AYAR.SAAT_KAYDIRDIM' and not self.saat.demo: raise PermissionError('Yalniz demo')
        except PermissionError as h: return self.red('YETKI',str(h))
        e.pop('bulut_ulasma_ani',None); icerik=kodla(e); kimlik=e['olay_kimligi']
        if kimlik in self._icerikler:
            if self._icerikler[kimlik]!=icerik:
                self.isleme_hatalari.append({'olay':kimlik,'hata':'ayni kimlik, farkli icerik','an':self.saat.gercek().isoformat(),'cozuldu':False})
                return {'sonuc':'CAKISMA','kod':'CAKISMA'}
            return {'sonuc':'BASARILI','tekrar':True}
        if e['eylem_kodu'] not in TANIKLIK and e['giris_sekli']!='AKTARIM':
            from .kurallar_v10_2 import sira_siniri
            if sira_siniri(self, e): return self.red('BAYAT','SIRA')
        if e['eylem_kodu'] not in TANIKLIK and e['giris_sekli']!='AKTARIM':
            from .kurallar_v10_1 import zorunlu_hedefler
            if zorunlu_hedefler(e) - {(x['tur'],x['kimlik']) for x in e['neyin_ustunde']}:
                return self.red('BAYAT','T10 hedef surumu eksik')
            from .kapilar_v3 import liste_hedefleri
            tasinan={x['kimlik'] for x in e['neyin_ustunde'] if x['tur']=='LISTE'}
            if set(liste_hedefleri(e))-tasinan: return self.red('BAYAT','Hedef liste surumu eksik')
            for x in e['neyin_ustunde']:
                mevcut=nesne(self,x['tur'],x['kimlik'])
                if not mevcut: return self.red('DURUM','Yonetim hedefi bulutta yok')
                if x.get('surum')!=mevcut.get('surum',0): return dict(self.red('BAYAT','Nesne surumu degisti'),guncel=deepcopy(mevcut))
            if not durum(self,e): return self.red('DURUM','Bulut kapisi kapali')
        if e['eylem_kodu']=='BILDIRIM.GORDUM':
            from .kurallar_v9 import durum as durum_v9
            if not durum_v9(self,e): return self.red('DURUM','Bildirim hic var olmadi')
        if e['eylem_kodu']=='AYAR.SAAT_KAYDIRDIM':
            if an(e['girdiler']['hedef'])<self.saat.simdi(): return self.red('DURUM','Geri saat icin demo sifirla')
            self.saat.ilerlet(e['girdiler']['hedef'])
        e['bulut_ulasma_ani']=self.saat.gercek().isoformat()
        from .kurallar_v10_1 import SEMALAR
        if e['eylem_kodu'] in SEMALAR: e['kabul_sirasi'] = len(self._kayitlar) + 1
        if e['eylem_kodu'] == 'NESNE.SURUM_EKLEDIM':
            from .kurallar_v10_1 import surum_satirlari
            e['nesne_surum_no'] = len(surum_satirlari(self,e['girdiler']['hedef'])) + 1
        self._icerikler[kimlik]=icerik; self._olaylar[kimlik]=kodla(e); self._kayitlar[kimlik]=e
        if hassas_ek is not None: self.hassas_ekler.append(dict(hassas_ek,olay=kimlik))
        try: self.olay_isle(e)
        except Exception as h: self.isleme_hatalari.append({'olay':kimlik,'hata':repr(h),'an':self.saat.gercek().isoformat(),'cozuldu':False})
        return {'sonuc':'BASARILI','tekrar':False}

    def yayinla(self,yeni):
        eski=self.gorunum
        if eski:
            for k,v in eski.bildirimler.items():
                if k in yeni.bildirimler: yeni.bildirimler[k]['olusma_ani']=v['olusma_ani']
                else: yeni.bildirimler[k]=dict(v,gecerli=False)
        for ad in ('isler','gorevler','kisiler','birimler','etaplar','projeler','notlar','tezgahlar','kisi_durumu','bildirimler','supheliler','sonuclar','bekletmeler','dosyalar'):
            for k,v in getattr(yeni,ad).items():
                if eski and getattr(eski,ad).get(k) is v: continue
                from .surum import is_alanlari, ozet
                v['surum'] = ozet(is_alanlari(v))
        self.gorunum=yeni
        self.kurulum_tamamlandi = bool(getattr(yeni, 'kurulum_kaynagi', None))
        from .gorunum_v7 import gun_sonu_raporu,hatirlatmalar
        for k,r in list(yeni.gun_sonu_raporlari.items()):
            yeni.gun_sonu_raporlari[k]=gun_sonu_raporu(self,r['kisi'],r['gun'])
        for r in hatirlatmalar(self):
            key='GUN_SONU:'+r['kisi']+':'+r['gun']+':'+r['kural']+':'+r['alici']
            yeni.bildirimler[key]=dict(r,doguran_olay='GUN_SONU:'+r['kisi']+':'+r['gun'],gecerli=True,metin=r['kisi'],olusma_ani=self.saat.gercek())
        from .surum import is_alanlari,ozet
        from .kurallar_v9 import gorulmeleri_yansit
        gorulmeleri_yansit(yeni)
        from .modul_bildirimi import gorulmeleri_yansit as modul_gorulmeleri
        modul_gorulmeleri(self)
        for s in yeni.bildirimler.values():
            s.setdefault('kaynak', 'CEKIRDEK'); s.setdefault('onem', 'BILGI')
        for ad in ('nesneler','nesne_turleri','gun_sonu_raporlari'):
            for v in getattr(yeni,ad).values(): v['surum']=ozet(is_alanlari(v))

    def olay_isle(self,e):
        from .kapsam import hesapla
        from .motor import Motor
        if self.yontem=='tam':
            yeni=Motor(self.saat); yeni.yurut(list(self._kayitlar.values())); kapsam={'olay':len(self._kayitlar),'tum':True}
        else: yeni,kapsam=hesapla(self,e)
        kapsam['tur']=max(yeni.yakinsama_turlari,default=1); self.olcumler.append(kapsam)
        if yeni.islenemedi:
            self.isleme_hatalari.append({'olay':e['olay_kimligi'],'hata':'yakinsamadi','islenemedi':True,'cozuldu':False}); return
        self.yayinla(yeni)

    def yeniden_kur(self):
        from .motor import Motor
        with self._kilit:
            yeni=Motor(self.saat); yeni.yurut(list(self._kayitlar.values())); self.yayinla(yeni)

    def modul_bildirimi_birak(self, servis_kimligi, modul, kural, kayit, alicilar, metin, onem, an):
        from .modul_bildirimi import birak
        return birak(self, servis_kimligi, modul, kural, kayit, alicilar, metin, onem, an)

    def modul_bildirimi_kaldir(self, servis_kimligi, modul, kural, kayit, an):
        from .modul_bildirimi import kaldir
        return kaldir(self, servis_kimligi, modul, kural, kayit, an)

    def kurulum(self, olaylar, kod_listeleri, servis=False):
        """A19: tek atomik servis paketi. Basarisiz paket kaynak birakmaz.

        Eski cevap anahtarinin servis yukleyicisi ayri test/demo yoludur.
        Gercek firma bu fonksiyonla acilir; aktarim bundan sonra kilitlenir.
        """
        with self._kilit:
            if not servis: return self.red('YETKI', 'Kurulum yalniz servis')
            if self._kayitlar or self.kurulum_tamamlandi: return self.red('DURUM', 'Kurulum yalniz bos firmada')
            gerekli = {'KOD.TANIMLADIM', 'YETKI.TANIMLADIM', 'KURULUM.TAMAMLADIM', 'AYAR.ONAY_ORANI', 'AYAR.MAAS_PAYDASI', 'AYAR.PARCA_KODU_DESENI', 'TAKVIM.TANIMLADIM', 'BIRIM.TANIMLADIM', 'KISI.EKLEDIM'}
            izin = gerekli | {'TATIL.EKLEDIM'}
            if not olaylar or {x.get('eylem_kodu') for x in olaylar} - izin or not gerekli <= {x.get('eylem_kodu') for x in olaylar}:
                return self.red('BICIM', 'Kurulum olaylari eksik ya da kapsam disi')
            if not isinstance(kod_listeleri, dict) or not all(isinstance(v, list) for v in kod_listeleri.values()):
                return self.red('BICIM', 'Kod listeleri gerekli')
            if olaylar[-1].get('eylem_kodu') != 'KURULUM.TAMAMLADIM': return self.red('BICIM', 'Kurulumun son olayi eksik')
            gecici = Depo(self.saat, self.yontem)
            gecici._kurulum_isle = True
            for e in olaylar:
                if e.get('giris_sekli') != 'AKTARIM': return self.red('BICIM', 'Kurulum AKTARIM olmali')
                s = gecici.olay_ekle(e, oturum='SERVIS', servis=True)
                if s['sonuc'] != 'BASARILI': return s
            if gecici.isleme_hatalari or len(gecici.kisiler) != 1 or len(gecici.birimler) != 1:
                return self.red('DURUM', 'Tek kok ve ilk yetkili gerekli')
            k, kisi = next(iter(gecici.kisiler.items()))
            b, birim = next(iter(gecici.birimler.items()))
            if kisi.get('birim') != b or not {'YETKILI', 'YONETICI'} <= set(kisi.get('roller', [])) or birim.get('basi') != k or birim.get('ust_birim'):
                return self.red('DURUM', 'Kurulum kok/yetkili baglantisi gecersiz')
            from .kurallar_v6 import kod_aktif
            if not all(kod_aktif(gecici, 'ROL', r) for r in kisi['roller']): return self.red('DURUM', 'Kurulum rolleri eksik')
            if not gecici.kurulum_tamamlandi: return self.red('DURUM', 'Kurulum kapanmadi')
            self._kayitlar = deepcopy(gecici._kayitlar); self._olaylar = deepcopy(gecici._olaylar); self._icerikler = deepcopy(gecici._icerikler)
            self.kod_listeleri = deepcopy(kod_listeleri); self.kurulum_tamamlandi = True
            self.yeniden_kur()
            return {'sonuc': 'BASARILI', 'tekrar': False}

    def yeniden_isle(self,kimlik):
        self.olay_isle(self._kayitlar[kimlik])
        for h in self.isleme_hatalari:
            if h['olay']==kimlik and not self.gorunum.islenemedi: h['cozuldu']=True

    def ilerlet(self,hedef): self.saat.ilerlet(hedef); self.yeniden_kur()
    def cihaz_esitle(self,kim,cihaz):
        if kim not in self.kisiler: raise PermissionError('Cihaz oturumu')
        self.cihaz_esitlemeleri[cihaz]={'kisi':kim,'son_esitleme':self.saat.gercek()}

    def cihaz_kaydol(self, kim, cihaz):
        """Bulut cihaz kaydı: modüllerin harfleri bütün kişiler için ayrıdır."""
        from .yetki_v6 import istihdamda
        if not istihdamda(self, kim, self.saat.simdi()): raise PermissionError('Oturum')
        with self._kilit:
            key = kim + ':' + cihaz
            if key in self.cihaz_harfleri: return self.cihaz_harfleri[key]
            dolu = {x.get('cihaz_harfi') for x in self.moduller.values()}
            dolu.update(v for k, v in self.cihaz_harfleri.items() if k.startswith(kim + ':'))
            dolu.update(e['olay_kimligi'][-1] for e in self._kayitlar.values() if e['kim'] == kim)
            h = next((x for x in 'TUVWXYZABCDEFGHIJKLMNOPQRS' if x not in dolu), None)
            if h is None: raise OverflowError('Cihaz harfleri doldu')
            self.cihaz_harfleri[key] = h
            return h
    def olay_koru(self,islem='GUNCELLE'): raise PermissionError('A5: olaylar yalniz eklenir: '+islem)

    def demo_sifirla(self,baslangic):
        if not self.saat.demo: raise PermissionError('Yalniz demo')
        self._olaylar.clear(); self._icerikler.clear(); self._kayitlar.clear(); self._surumler.clear()
        self.hassas_ekler.clear(); self.ay_kapanislari.clear(); self.isleme_hatalari.clear()
        self.modul_bildirimleri.clear()
        self.gorunum=None; self.saat.is_ani=an(baslangic); self.yeniden_kur()

    def son_hal(self):
        # I18/I41 iş sonucu; sürüm/gerçek teslim anı işletim metaverisidir (B28).
        def temiz(x):
            if isinstance(x,dict): return {k:temiz(v) for k,v in x.items() if k not in ('surum','olusma_ani')}
            if isinstance(x,list): return [temiz(v) for v in x]
            return x
        veri={k:getattr(self.gorunum,k) for k in ('isler','gorevler','listeler','kisi_durumu','araliklar','bildirimler','supheliler','notlar','etaplar','bekletmeler')}
        veri['bildirimler']={k:v for k,v in veri['bildirimler'].items() if v['gecerli']}
        from .kurallar_v7 import TABLOLAR
        from .kurallar_v9 import TABLOLAR as TABLOLAR_V9
        veri.update({k:getattr(self.gorunum,k) for k in TABLOLAR + TABLOLAR_V9})
        from .kurallar_v10_1 import TABLOLAR as T10
        veri.update({k:getattr(self.gorunum,k) for k in T10})
        veri['modul_bildirimleri']=self.modul_bildirimleri
        return kodla(temiz(veri))

    def __getattr__(self,ad):
        g=self.__dict__.get('gorunum')
        if g is not None and hasattr(g,ad): return getattr(g,ad)
        raise AttributeError(ad)
