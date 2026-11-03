"""Simülatör sürücüsü: çekirdeğin Python modeli modülün yanında, aynı süreçte çalışır.

- Örnek firma (`simulator/ornek_firma.girdi.json`) kurulur, sonra künyeden üretilen kurulum olayları
  yetkili (K001) adına yazılır: modül çekirdekte tanımlı, rolleri ve türleri hazırdır.
- Modülün her yazması ve kullanıcı gözüyle her okuması bir adım olarak kaydedilir. `senaryo_yaz` bunları
  cevap anahtarı biçiminde bir girdi dosyasına yazar: modülün sözleşme senaryosu. Aynı dosyayı biz ürüne oynatırız.
- Saat: her yazmadan sonra bir saniye ilerler (gerçek zaman gibi). `saat(an)` ile elle de kurulabilir.
"""
from copy import deepcopy
from datetime import datetime, timedelta
import importlib.util
import json
from pathlib import Path
import sys

from .cekirdek import PAKET, CekirdekHatasi, jwt_icerigi, kisi_kodu

SIMULATOR = PAKET / 'simulator'
HATA = {'PermissionError': 'YETKI', 'ValueError': 'BICIM', 'KeyError': 'BICIM', 'TypeError': 'BICIM',
        'LookupError': 'DURUM'}
BILDIRIM_ALANLARI = {'birak': ('modul', 'kural', 'kayit', 'alicilar', 'metin', 'onem', 'an'),
                     'kaldir': ('modul', 'kural', 'kayit', 'an')}
SURUMLU = {'NESNE': 'NESNE', 'NESNELER': 'NESNE', 'IS': 'IS', 'GOREV': 'GOREV', 'PROJE': 'PROJE', 'PROJELER': 'PROJE',
           'ETAP': 'ETAP', 'ETAPLAR': 'ETAP'}


def _yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _yurut():
    for yol in (str(SIMULATOR), str(SIMULATOR / 'model')):
        if yol not in sys.path:
            sys.path.insert(0, yol)
    return sys.modules.get('_irp_sozlesme_yurut') or _yukle('_irp_sozlesme_yurut', SIMULATOR / 'yurut.py')


def anahtar_uret(icerik):
    """İmzasız, JWT biçiminde sahte erişim anahtarı (yalnızca simülatör)."""
    import base64
    b = lambda x: base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('=')  # noqa: E731
    return f'{b({"alg": "none", "typ": "JWT"})}.{b(icerik)}.sahte'


def _saat(an):
    return {'demo': False, 'gercek': an, 'simdi': an}


class SimulatorSurucu:
    def modul_dosya(self,anahtar,ad,g):
        raise CekirdekHatasi('URUN_SQL_GEREKLI','Fiziksel dosya izni ve bayt aktarımı gerçek SQL/geçit sınamasında doğrulanır')

    def __init__(self, kunye, zemin=None, oto_saat=True, ortak=None):
        self.Y = _yurut()
        self.kunye, self.oto_saat = kunye, oto_saat
        if ortak is not None:
            self.d=ortak.d
            self._girdi,self._baslangic,self._adimlar=ortak._girdi,ortak._baslangic,ortak._adimlar
            self._zaman=ortak._zaman
            self._kur()
            return
        girdi = json.loads(Path(zemin or SIMULATOR / 'ornek_firma.girdi.json').read_text('utf-8'))
        depo = girdi['depolar'][0]
        self._girdi = {k: v for k, v in girdi.items() if k != 'depolar'}
        self._baslangic, self._adimlar = depo['baslangic'], deepcopy(depo['adimlar'])
        depolar = []
        self.Y.yurut(girdi, denetim_depolari=depolar)
        self.d = depolar[0]
        self._zaman = {'an':self.d.saat.simdi()}
        self._kur()

    @property
    def _an(self):
        return self._zaman['an']

    @_an.setter
    def _an(self,value):
        self._zaman['an']=value

    # ---- saat
    def saat(self, an):
        self._an = datetime.fromisoformat(an)
        self._saati_kur()

    def simdi(self):
        return self._an.isoformat()

    def _saati_kur(self):
        self.d.saat = self.Y.saat_kur(_saat(self.simdi()))
        self.d.gorunum.saat = self.d.saat

    def _ilerle(self, saniye=1):
        if self.oto_saat:
            self._an += timedelta(seconds=saniye)
            self._saati_kur()

    def _kaydet(self, adim):
        self._adimlar.append(dict(adim, saat=_saat(self.simdi()), yontem='kapsamli'))

    def _dene(self, f, *a, **k):
        cevap = self.Y.dene(f, *a, **k)
        if 'hata_turu' in cevap:
            raise CekirdekHatasi(HATA.get(cevap['hata_turu'], 'URUN'), cevap.get('neden'))
        return cevap['deger']

    # ---- kurulum (künyeden; yetkili adına)
    def _kur(self):
        sys.path.insert(0, str(PAKET / 'arac'))
        from kunye_denetle import kurulum_olaylari
        self._ilerle(60)
        for o in kurulum_olaylari(self.kunye):
            cevap = self.yetkili_olay(o['eylem_kodu'], o['girdiler'], ilerle=60)
            if cevap.get('sonuc') != 'BASARILI':
                raise CekirdekHatasi('KUNYE', f'Kurulum olayı reddedildi: {o["eylem_kodu"]} {cevap}')

    def yetkili_olay(self, eylem_kodu, girdiler, kim='K001', neyin_ustunde=(), ilerle=1):
        """Yalnızca sınamada: firmanın yetkilisi (örnek firmada K001) çekirdeğin ekranından bir şey yapar.
        Ör. modülün rolünü bir kişiye vermek: yetkili_olay('KISI.DEGISTIRDIM', {...}). Senaryoya yazılır."""
        gun = self._an.strftime('%y%m%d')
        on = f'{kim}-{gun}'
        sira = 1 + max([int(k.split('-')[1][6:]) for k in self.d._kayitlar
                        if k.startswith(on) and k.endswith('-M')], default=0)
        olay = {'adina': None, 'bildigi_son_hal_ani': self.simdi(), 'cihaz': f'MAS-{kim}', 'duzelttigi_olay': None,
                'eylem_kodu': eylem_kodu, 'eylem_versiyonu': 1, 'girdiler': girdiler,
                'giris_sekli': 'LISTE', 'kanit': [], 'kim': kim, 'neyin_ustunde': list(neyin_ustunde),
                'olay_kimligi': f'{on}{sira:04d}-M', 'oldugu_an': self.simdi(), 'pc_ulasma_ani': None,
                'saat_dilimi': '+03:00', 'uygulama_surumu': 'WEB-0.1.0', 'yol': 'DISARIDA'}
        cevap = self._olay(olay, kim)
        self._ilerle(ilerle)
        return cevap

    # ---- kimlik
    def giris(self, kisi, sifre):
        """Simülatörde şifre denetlenmez; kişi istihdamda olmalı."""
        from irp.yetki_v6 import istihdamda
        if kisi not in self.d.kisiler or not istihdamda(self.d, kisi, self.d.saat.simdi()):
            raise CekirdekHatasi('YETKI', 'Oturum')
        return anahtar_uret({'email': f'{kisi.lower()}@calisan.irp', 'role': 'authenticated'})

    def servis_anahtari(self):
        return anahtar_uret({'role': 'service_role', 'servis_kimligi': self.kunye['servis_kimligi']})

    # ---- kapılar
    def _olay(self, olay, kisi, hassas_ek=None):
        adim = {'tur': 'olay', 'args': [deepcopy(olay)],
                'kwargs': {'hassas_ek': hassas_ek, 'oturum': kisi, 'servis': False}}
        self._kaydet(adim)
        cevap = self._dene(self.d.olay_ekle, olay, oturum=kisi, servis=False, hassas_ek=hassas_ek)
        return dict(cevap, alindi=cevap.get('sonuc') == 'BASARILI', hesap='GUNCEL')

    def olay_ekle(self, anahtar, olay, hassas_ek=None):
        cevap = self._olay(olay, kisi_kodu(anahtar), hassas_ek)
        self._ilerle()
        return cevap

    def oku(self, anahtar, veri, hedef, g):
        kisi = kisi_kodu(anahtar)
        from .okuma_uyarlamasi import oku
        self._kaydet({'tur': 'sorgu', 'modul': 'irp_sozlesme.baglanti.okuma_uyarlamasi', 'ad': 'oku', 'args': [kisi, veri, hedef],
                      'kwargs': deepcopy(g)})
        deger = self._surumle(veri, self._dene(oku, self.d, kisi, veri, hedef, **g))
        return {'deger': deger, 'hesap': 'GUNCEL', 'hesap_ani': self.simdi()}

    def servis_oku(self, servis, veri, hedef, g):
        """Simülatörde yaklaşık: bütün firmayı gören bir yetkilinin gözüyle, yalnızca izinli okumalar.
        Üründe dar giriş rolüyle `public.servis_oku` kullanılır. Senaryoya yazılmaz;
        bu yaklaşım gerçek SQL servis güvenliğinin kabulü değildir."""
        self._servis_denetle(servis)
        izinli=self.kunye.get('kapilar',{}).get('servis_okumalari',[])
        katalog=json.loads((PAKET/'arac/cekirdek_katalogu.json').read_text())
        if veri not in izinli or veri not in katalog['servis_okumalari']:
            raise CekirdekHatasi('YETKI','Servis okumasi kunyede yok veya kisisel/parasal')
        from .okuma_uyarlamasi import oku
        yetkili = next(k for k, p in self.d.kisiler.items() if 'YETKILI' in p.get('roller', []))
        deger = self._surumle(veri, self._dene(oku, self.d, yetkili, veri, hedef, **g))
        alanlar={
            'PROJE':'kimlik kod ad sorumlu aktif ana_proje baslangic_tarihi teslim_tarihi kesin_kabul_tarihi surum',
            'ETAP':'kimlik ad proje birim sorumlu baslangic bitis hedef_saat surum',
            'KISILER':'kimlik birim yaka roller aktif surum',
            'BIRIMLER':'kimlik kod ad ust_birim basi surum',
            'NESNE':'kimlik tur kod ad proje asama sorumlu baglar asama_ani surum',
            'TEZGAHLAR':'kimlik kod ad birim aktif surum',
            'GECERLI_SURUM':'nesne surum_no surum_adi durum dosyalar eklenme_ani onay_ani'}
        alan=alanlar.get({'PROJELER':'PROJE','ETAPLAR':'ETAP','NESNELER':'NESNE'}.get(veri,veri))
        if alan:
            def sec(row):return {k:v for k,v in row.items() if k in alan.split()} if isinstance(row,dict) else row
            deger=[sec(row) for row in deger] if isinstance(deger,list) else sec(deger)
        return {'deger': deger, 'hesap': 'GUNCEL', 'hesap_ani': self.simdi()}

    def bildirim(self, servis, ad, g):
        self._servis_denetle(servis)
        eksik = [k for k in BILDIRIM_ALANLARI[ad] if k not in g]
        if eksik:
            raise CekirdekHatasi('BICIM', 'Eksik alan: ' + ', '.join(eksik))
        kw = dict(servis_kimligi=servis, **{k: g[k] for k in BILDIRIM_ALANLARI[ad]})
        self._kaydet({'tur': 'modul_bildirimi', 'ad': ad, 'args': [], 'kwargs': deepcopy(kw)})
        cevap = self._dene(getattr(self.d, 'modul_bildirimi_' + ad), **kw)
        self._ilerle()
        return cevap

    def _servis_denetle(self, servis):
        if servis != self.kunye['servis_kimligi']:
            raise CekirdekHatasi('YETKI', 'Servis kimliği')

    def _surumle(self, veri, deger):
        """Üründe okunan her kayıt satırı `surum` taşır (T16 › 3); simülatör de ekler."""
        from irp.kabul import nesne
        tur = SURUMLU.get(veri)
        if not tur:
            return deger
        satirlar = deger if isinstance(deger, list) else [deger]
        for x in satirlar:
            if isinstance(x, dict) and x.get('kimlik') and 'surum' not in x:
                s = nesne(self.d, tur, x['kimlik']).get('surum')
                if s:
                    x['surum'] = s
        return deger

    # ---- senaryo
    def senaryo(self, ad):
        """Kaydedilen adımlar, cevap anahtarı girdi biçiminde (KULLANIM.md › Girdi sözleşmesi)."""
        return dict(self._girdi, senaryo=ad, modul=self.kunye['kod'], cihaz_denemeleri=[], saf_sorgular=[],
                    depolar=[{'baslangic': self._baslangic, 'adimlar': deepcopy(self._adimlar),
                              'son_saat': _saat(self.simdi()), 'yontem': 'kapsamli'}])

    def senaryo_yaz(self, yol, ad=None):
        yol = Path(yol)
        yol.parent.mkdir(parents=True, exist_ok=True)
        ad = ad or yol.name.replace('.girdi.json', '')
        yol.write_text(json.dumps(self.senaryo(ad), ensure_ascii=False, indent=1) + '\n', 'utf-8')
        return yol


__all__ = ['SimulatorSurucu', 'anahtar_uret', 'jwt_icerigi']
