"""Kişi ve M1.0'a erişim (SPEC › 6). Saf: kişinin kaydı çekirdeğin KISILER okumasından gelir.

M1.0 çekirdeğe olay yazmaz; bütün yetki modülün kendi kuralıdır.
"""
from dataclasses import dataclass

SATIS = 'SATIS'
YETKILI = 'YETKILI'


@dataclass(frozen=True)
class Kisi:
    kimlik: str
    ad: str
    birim: str
    roller: tuple
    yonetim: bool          # birimi yonetim_birimleri ayarında

    @property
    def satis(self):
        return SATIS in self.roller

    @property
    def yetkili(self):
        return YETKILI in self.roller

    @property
    def erisim(self):
        """Talepleri, sürümleri, maliyeti ve kârı görmek."""
        return self.satis or self.yetkili or self.yonetim

    @property
    def duzenleyici(self):
        """Müşteri, talep, TASLAK sürüm; onaya göndermek; gönderildi; müşterinin cevabı; kapatmak."""
        return self.satis or self.yetkili

    @property
    def onayci(self):
        """Onaylamak, kendim düzeltmek, geri göndermek. S-8b cevaplanana kadar YETKILI (SPEC › 18)."""
        return self.yetkili

    def duzenlemeye_acabilir(self, hazirlayan):
        return self.yetkili or (self.duzenleyici and self.kimlik == hazirlayan)

    @property
    def geri_acabilir(self):
        return self.yetkili

    @property
    def ayarlayabilir(self):
        """Ayarlar ve geçmiş proje formu: SATIS, YETKILI, yönetim birimleri."""
        return self.erisim

    @property
    def yonetim_birimlerini_degistirebilir(self):
        return self.yetkili


def kisi_kur(kayit, yonetim_birimleri):
    return Kisi(kimlik=kayit['kimlik'], ad=kayit.get('ad') or kayit['kimlik'], birim=kayit.get('birim') or '',
                roller=tuple(kayit.get('roller') or ()), yonetim=(kayit.get('birim') in set(yonetim_birimleri or ())))
