"""Modülün çekirdekle konuştuğu tek yer (sozlesme/01_baglanti.md).

Modülün geri kalanı çekirdeğe yalnızca bu dosyadaki sınıflardan ulaşır. Bu dosya ve sürücüler
değiştirilmez: çekirdek değişirse paketin yeni sürümü gelir, modülün kodu değişmez.

    from irp_sozlesme.baglanti import Cekirdek

    cekirdek = Cekirdek.ac('kunye.json')            # ortam değişkenlerine göre sürücüyü seçer
    oturum = cekirdek.giris('K006', 'sifre')         # ya da cekirdek.oturum(kullanicinin_erisim_anahtari)
    parca = oturum.oku('NESNE', 'K006-2610280001-P').deger
    cevap = oturum.olay_gonder('NESNE.ASAMA_GECIRDIM',
                               {'hedef': parca['kimlik'], 'yeni_asama': 'SIPARISTE', 'gerekce': 'sipariş verildi'},
                               neyin_ustunde=[oturum.hedef('NESNE', parca)])
    cekirdek.servis().bildirim_birak('SIPARIS_GECIKTI', {'tur': 'NESNE', 'kimlik': parca['kimlik']},
                                      [{'tur': 'NESNE_SORUMLUSU', 'kimlik': parca['kimlik']}], 'Termin geçti')
"""
import base64
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import threading

PAKET = Path(__file__).resolve().parents[1]
GUN_DILIMI = '+03:00'


class CekirdekHatasi(Exception):
    """Çekirdek isteği yapamadı. tur: YETKI, BICIM, DURUM, BAGLANTI, URUN, KUNYE."""

    def __init__(self, tur, neden):
        super().__init__(f'{tur}: {neden}')
        self.tur, self.neden = tur, neden


class Cevap(dict):
    """olay_gonder'in cevabı: {sonuc, kod, neden, tekrar, alindi, hesap, olay_kimligi}."""

    @property
    def basarili(self):
        return self.get('sonuc') == 'BASARILI'

    @property
    def tekrar(self):
        return bool(self.get('tekrar'))

    @property
    def bayat(self):
        """Okuduğun kayıt sen karar verirken değişti: yeniden oku, kullanıcıya göster, yeniden sor."""
        return self.get('kod') == 'BAYAT'

    @property
    def kod(self):
        return self.get('kod')


class Okuma:
    """oku'nun cevabı. deger: okunan veri; hesap: GUNCEL ya da BEKLIYOR (çekirdek hâlâ hesaplıyor)."""

    def __init__(self, deger, hesap='GUNCEL', hesap_ani=None):
        self.deger, self.hesap, self.hesap_ani = deger, hesap, hesap_ani

    @property
    def guncel(self):
        return self.hesap == 'GUNCEL'

    def __repr__(self):
        return f'Okuma(hesap={self.hesap}, deger={self.deger!r:.120})'


def jwt_icerigi(anahtar):
    """Erişim anahtarının içeriği (imza burada denetlenmez; denetimi çekirdek yapar)."""
    try:
        parca = anahtar.split('.')[1]
        return json.loads(base64.urlsafe_b64decode(parca + '=' * (-len(parca) % 4)))
    except Exception as e:  # noqa: BLE001
        raise CekirdekHatasi('YETKI', 'Erişim anahtarı okunamadı') from e


def kisi_kodu(anahtar):
    """Supabase girişinde e-posta <kişi kodu küçük harf>@calisan.irp biçimindedir (T16 › 2)."""
    eposta = jwt_icerigi(anahtar).get('email') or ''
    if not eposta.endswith('@calisan.irp'):
        raise CekirdekHatasi('YETKI', 'Erişim anahtarı bir çalışana ait değil')
    return eposta.split('@')[0].upper()


# ------------------------------------------------------------------ olay kimliği

class BellekSayac:
    """Kişi ve gün başına sıra; yalnızca geliştirme için. Üründe modülün kendi tablosu kullanılır
    (sozlesme/04_veritabani.md › olay_sayaci). Sıra kaybolursa CAKISMA gelir, katman ilerleyip yeniden dener."""

    def __init__(self):
        self._sira, self._kilit = {}, threading.Lock()

    def sonraki(self, kisi, gun):
        with self._kilit:
            self._sira[(kisi, gun)] = self._sira.get((kisi, gun), 0) + 1
            return self._sira[(kisi, gun)]


class DosyaSayac(BellekSayac):
    """Sırayı bir JSON dosyasında tutar (geliştirme ve deneme)."""

    def __init__(self, yol):
        super().__init__()
        self.yol = Path(yol)
        if self.yol.exists():
            self._sira = {tuple(k.split('|')): v for k, v in json.loads(self.yol.read_text('utf-8')).items()}

    def sonraki(self, kisi, gun):
        n = super().sonraki(kisi, gun)
        self.yol.write_text(json.dumps({'|'.join(k): v for k, v in self._sira.items()}), 'utf-8')
        return n


# ------------------------------------------------------------------ çekirdek

class Cekirdek:
    def __init__(self, surucu, kunye, sayac=None):
        self.surucu, self.kunye = surucu, kunye
        self.sayac = sayac or BellekSayac()
        self._son_an = None
        self._kilit = threading.Lock()
        sema = json.loads((PAKET / 'arac' / 'cekirdek_katalogu.json').read_text('utf-8'))
        self._eylemler = sema['eylemler']

    @classmethod
    def ac(cls, kunye_yolu='kunye.json', sayac=None, **secenek):
        """Sürücüyü ortam değişkenlerinden seçer. Modülün kodu bunu değiştirmez; bağlanmayı biz ayarlarız.
        IRP_CEKIRDEK=simulator (varsayılan) | http
        http için: IRP_TABAN (ör. https://<proje>.supabase.co), IRP_ANON (anon anahtarı), IRP_SERVIS (servis anahtarı)"""
        kunye = json.loads(Path(kunye_yolu).read_text('utf-8'))
        tur = os.environ.get('IRP_CEKIRDEK', 'simulator')
        if tur == 'simulator':
            from .surucu_simulator import SimulatorSurucu
            surucu = SimulatorSurucu(kunye, **secenek)
        elif tur == 'http':
            from .surucu_http import HttpSurucu
            surucu = HttpSurucu(os.environ['IRP_TABAN'], os.environ['IRP_ANON'], os.environ.get('IRP_SERVIS'))
        else:
            raise CekirdekHatasi('KUNYE', f'Bilinmeyen IRP_CEKIRDEK: {tur}')
        return cls(surucu, kunye, sayac)

    # ---- kimlik ve saat
    def giris(self, kisi, sifre):
        """Geliştirme ve deneme içindir. Üründe kullanıcı çekirdeğin girişiyle girer; modül anahtarı alır."""
        return self.oturum(self.surucu.giris(kisi, sifre))

    def oturum(self, erisim_anahtari):
        return Oturum(self, erisim_anahtari)

    def servis(self):
        return Servis(self)

    def simdi(self):
        return self.surucu.simdi()

    def _olay_ani(self):
        """Çekirdeğin saatine göre; aynı kaynaktan iki karar aynı ana düşmez (K-24)."""
        with self._kilit:
            an = datetime.fromisoformat(self.surucu.simdi())
            if self._son_an and an <= self._son_an:
                an = self._son_an + timedelta(milliseconds=1)
            self._son_an = an
            return an

    def _kimlik(self, kisi, an):
        harf = self.kunye.get('cihaz_harfi')
        gun = an.strftime('%y%m%d')
        return f'{kisi}-{gun}{self.sayac.sonraki(kisi, gun):04d}-{harf}'


class Oturum:
    """Kullanıcının gözü: okuma ve olay kullanıcının yetkisiyle yapılır (K-13, K-21)."""

    def __init__(self, cekirdek, erisim_anahtari):
        self.cekirdek, self.anahtar = cekirdek, erisim_anahtari
        self.kisi = kisi_kodu(erisim_anahtari)

    def oku(self, veri, hedef=None, **g):
        cevap = self.cekirdek.surucu.oku(self.anahtar, veri, hedef, g)
        return Okuma(cevap.get('deger'), cevap.get('hesap', 'GUNCEL'), cevap.get('hesap_ani'))

    def dosya_yukle(self, kayit, ad, icerik, tur='application/octet-stream'):
        """Paket 1.2: en fazla 1 MB gerçek bayt; normal kullanıcı ve sahibi modülün izniyle."""
        if not isinstance(icerik,bytes) or not 0<len(icerik)<=1048576:
            raise CekirdekHatasi('BICIM','Dosya 1 MB sınırında, boş olmayan bayt olmalı')
        return self.cekirdek.surucu.modul_dosya(self.anahtar,'yukle',{
            'kayit':kayit,'ad':ad,'tur':tur,'icerik_base64':base64.b64encode(icerik).decode()})

    def dosya_oku(self, kimlik):
        """Kaynak modülün güncel izniyle gerçek dosya ve metadata; servis gözü kullanılamaz."""
        return self.cekirdek.surucu.modul_dosya(self.anahtar,'oku',{'kimlik':kimlik})

    @staticmethod
    def hedef(tur, kayit):
        """Yönetim kararının dayandığı kayıt; okunduğu andaki sürümüyle (bayatlık, K-15)."""
        return {'tur': tur, 'kimlik': kayit['kimlik'], 'surum': kayit.get('surum')}

    def olay_gonder(self, eylem_kodu, girdiler, neyin_ustunde=(), giris_sekli='LISTE', adina=None,
                    kanit=(), duzelttigi_olay=None, hassas_ek=None, istek_kimligi=None):
        """Olayı kullanıcının adına gönderir. Ağ kesilirse aynı zarf yeniden gider (tekrar güvenli, K-17).
        Yalnızca künyesinde olay_yolu ARKA_YUZ olan modül kullanır."""
        c, k = self.cekirdek, self.cekirdek.kunye
        if k.get('olay_yolu') != 'ARKA_YUZ' or not k.get('cihaz_harfi'):
            raise CekirdekHatasi('KUNYE', 'Olayı arka yüz yazmıyor (olay_yolu ARKA_YUZ ve cihaz_harfi gerekli)')
        if eylem_kodu not in k.get('kapilar', {}).get('olaylar', []):
            raise CekirdekHatasi('KUNYE', f'{eylem_kodu} künyenin kapilar.olaylar listesinde yok')
        if giris_sekli not in ('LISTE', 'ELLE', 'QR'):
            raise CekirdekHatasi('BICIM', 'Giriş şekli LISTE, ELLE ya da QR')
        an = c._olay_ani()
        olay = {
            'adina': adina, 'bildigi_son_hal_ani': an.isoformat(), 'cihaz': f'MODUL-{k["kod"]}',
            'duzelttigi_olay': duzelttigi_olay, 'eylem_kodu': eylem_kodu,
            'eylem_versiyonu': c._eylemler.get(eylem_kodu, {}).get('eylem_versiyonu', 1),
            'girdiler': girdiler, 'giris_sekli': giris_sekli, 'kanit': list(kanit), 'kim': self.kisi,
            'neyin_ustunde': list(neyin_ustunde), 'olay_kimligi': c._kimlik(self.kisi, an),
            'oldugu_an': an.isoformat(), 'pc_ulasma_ani': None, 'saat_dilimi': GUN_DILIMI,
            'uygulama_surumu': f'{k["kod"]}-{k.get("surum", "0.0.0")}', 'yol': 'DISARIDA'}
        if istek_kimligi is not None:
            if hassas_ek is not None or not isinstance(istek_kimligi,str) or not 0<len(istek_kimligi)<=200:
                raise CekirdekHatasi('BICIM','Kalıcı istek kimliği geçersiz veya hassas ek desteklenmiyor')
            if not callable(getattr(c.sayac,'zarf',None)):
                raise CekirdekHatasi('KUNYE','Kalıcı istek için modülün işlemsel zarf deposu gerekli')
            olay=c.sayac.zarf(self.kisi,istek_kimligi,olay)
        for _ in range(3):
            cevap = Cevap(c.surucu.olay_ekle(self.anahtar, olay, hassas_ek), olay_kimligi=olay['olay_kimligi'])
            if cevap.get('sonuc') != 'CAKISMA':
                return cevap
            if istek_kimligi is not None:
                raise CekirdekHatasi('DURUM','Kalıcı olay kimliği çakıştı; istek korunuyor, yeni olay üretilmedi')
            # Sıra başka bir zarfa verilmiş (ör. sayaç kaybı): ilerle, yeni kimlikle yeniden dene.
            olay = dict(olay, olay_kimligi=c._kimlik(self.kisi, an))
        return cevap


class Servis:
    """Servis gözü: yalnızca bildirim kapısı ve kişisel olmayan okumalar (K-6, T18 › 4.3).
    Servis gözüyle okunan veri kullanıcıya gösterilmez; kural içindir."""

    def __init__(self, cekirdek):
        self.cekirdek = cekirdek
        k = cekirdek.kunye
        self.modul, self.servis_kimligi = k['kod'], k['servis_kimligi']
        if not k.get('arka_yuz'):
            raise CekirdekHatasi('KUNYE', 'Servis yalnızca arka yüzü olan modülde vardır')

    def _an(self, an):
        return an or self.cekirdek.simdi()

    def bildirim_birak(self, kural, kayit, alicilar, metin, onem='BILGI', an=None):
        """Aynı kural ve kayıt için yeniden bırakmak günceller (tekrar güvenli, K-9)."""
        kurallar = {x['kural'] for x in self.cekirdek.kunye.get('kapilar', {}).get('bildirimler', [])}
        if kural not in kurallar:
            raise CekirdekHatasi('KUNYE', f'{kural} künyenin bildirim kurallarında yok')
        g = {'modul': self.modul, 'kural': kural, 'kayit': kayit, 'alicilar': alicilar, 'metin': metin,
             'onem': onem, 'an': self._an(an)}
        return self.cekirdek.surucu.bildirim(self.servis_kimligi, 'birak', g)

    def bildirim_kaldir(self, kural, kayit, an=None):
        g = {'modul': self.modul, 'kural': kural, 'kayit': kayit, 'an': self._an(an)}
        return self.cekirdek.surucu.bildirim(self.servis_kimligi, 'kaldir', g)

    def oku(self, veri, hedef=None, **g):
        izinli = self.cekirdek.kunye.get('kapilar', {}).get('servis_okumalari', [])
        if veri not in izinli:
            raise CekirdekHatasi('KUNYE', f'{veri} künyenin servis_okumalari listesinde yok')
        cevap = self.cekirdek.surucu.servis_oku(self.servis_kimligi, veri, hedef, g)
        return Okuma(cevap.get('deger'), cevap.get('hesap', 'GUNCEL'), cevap.get('hesap_ani'))
