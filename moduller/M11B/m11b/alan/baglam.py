"""İsteğin bağlamı: kullanıcının oturumu, modülün veritabanı ve istek boyunca bir kez okunan çekirdek verisi."""
from functools import cached_property

from irp_sozlesme.baglanti import CekirdekHatasi

from .hatalar import ModulHatasi, gunluk


class Baglam:
    """Ekrandan gelen her istek bir Baglam'la çalışır. Okumalar kullanıcının gözüyledir (BASLA › Kural 6)."""

    def __init__(self, cekirdek, oturum, vt, ayarlar):
        self.cekirdek, self.oturum, self.vt, self.ayarlar = cekirdek, oturum, vt, ayarlar
        self.hesaplaniyor = False
        self._projeler = {}

    @property
    def kisi(self):
        return self.oturum.kisi

    def simdi(self):
        return self.cekirdek.simdi()

    # ---- okuma
    def oku(self, veri, hedef=None, **g):
        okuma = self.oturum.oku(veri, hedef, **g)
        if not okuma.guncel:
            self.hesaplaniyor = True
        return okuma.deger

    def proje(self, kimlik):
        """Projeye ait her işten önce (SPEC › 6). Göremeyene modülün o projeye ait hiçbir kaydı gösterilmez."""
        if kimlik not in self._projeler:
            try:
                self._projeler[kimlik] = self.oku('PROJE', kimlik)
            except CekirdekHatasi as e:
                if e.tur == 'YETKI':
                    raise ModulHatasi(403, 'PROJE_GORUNMUYOR', 'Bu projeyi göremiyorsunuz.') from None
                raise
        return self._projeler[kimlik]

    def proje_yenile(self, kimlik):
        self._projeler.pop(kimlik, None)
        return self.proje(kimlik)

    @cached_property
    def kisiler(self):
        return self.oku('KISILER')

    @cached_property
    def birimler(self):
        return self.oku('BIRIMLER')

    @cached_property
    def ben(self):
        return next((k for k in self.kisiler if k['kimlik'] == self.kisi),
                    {'kimlik': self.kisi, 'ad': self.kisi, 'birim': None, 'roller': []})

    def kisi_adi(self, kod):
        return next((k['ad'] for k in self.kisiler if k['kimlik'] == kod), kod) if kod else None

    def rolu_var(self, *roller):
        return any(r in self.ben.get('roller', []) for r in roller)

    @property
    def yetkili(self):
        return self.rolu_var('YETKILI')

    def sorumlu_mu(self, proje):
        return proje.get('sorumlu') == self.kisi

    # ---- olay
    def olay(self, eylem, girdiler, neyin_ustunde=()):
        cevap = self.oturum.olay_gonder(eylem, girdiler, neyin_ustunde=list(neyin_ustunde))
        gunluk.info('olay %s %s → %s %s', eylem, cevap.get('olay_kimligi'), cevap.get('sonuc'), cevap.get('kod') or '')
        return cevap

    def yanit(self, veri):
        """Okumalardan biri güncel değilse ekran "hesaplanıyor" yazar (SPEC › 9)."""
        if self.hesaplaniyor and isinstance(veri, dict):
            return {**veri, 'hesaplaniyor': True}
        return veri
