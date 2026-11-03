"""Modülün hataları ve çekirdeğin retlerinin kullanıcıya dönük karşılığı (SPEC › 10)."""
import logging

gunluk = logging.getLogger('m11b')

# Çekirdeğin bilinen ret nedenleri, anlaşılır cümleyle. Bilinmeyen neden olduğu gibi gösterilir.
NEDENLER = {
    'T3 yetki matrisi': 'Rolünüz ya da projedeki yeriniz bu işe izin vermiyor.',
    'Gorunurluk': 'Bu kaydı göremiyorsunuz.',
    'Nesne surumu degisti': 'Kayıt siz bakarken değişti.',
    'B1 ve sonrasi gerekce zorunlu': 'Plan değişikliğinde gerekçe zorunludur.',
}


class ModulHatasi(Exception):
    """Kullanıcıya dönen hata: HTTP durumu, makinenin okuyacağı kod, insanın okuyacağı mesaj ve ekler."""

    def __init__(self, durum, kod, mesaj, **ek):
        super().__init__(f'{durum} {kod}: {mesaj}')
        self.durum, self.kod, self.mesaj, self.ek = durum, kod, mesaj, ek

    def govde(self):
        return {'kod': self.kod, 'mesaj': self.mesaj, **self.ek}


def neden_cumlesi(neden):
    return NEDENLER.get(neden, neden) if neden else None


def olay_reddi(cevap, eylem, mesajlar=None):
    """Reddedilen olayın ModulHatasi karşılığı. `mesajlar` eyleme özgü daha açık cümleler verebilir: {kod: mesaj}."""
    kod, neden = cevap.get('kod'), cevap.get('neden')
    ozel = (mesajlar or {}).get(kod)
    if kod == 'YETKI':
        return ModulHatasi(403, 'YETKI', ozel or 'Bu işe yetkiniz yok.', neden=neden_cumlesi(neden))
    if kod == 'DURUM':
        return ModulHatasi(409, 'DURUM', ozel or neden_cumlesi(neden) or 'Bu iş kaydın şimdiki durumunda yapılamaz.')
    if kod == 'BAYAT':
        return ModulHatasi(409, 'BAYAT', 'Kayıt siz bakarken değişti.', guncel=cevap.get('guncel'))
    gunluk.error('Çekirdek %s olayını reddetti: %s (olay %s)', eylem, dict(cevap), cevap.get('olay_kimligi'))
    if kod == 'BICIM':
        return ModulHatasi(400, 'BICIM', 'Beklenmeyen bir hata oldu.')
    return ModulHatasi(500, kod or 'URUN', 'Beklenmeyen bir hata oldu.')


def cekirdek_hatasi(hata):
    """CekirdekHatasi (okuma ya da bağlantı) → ModulHatasi."""
    tur, neden = hata.tur, hata.neden
    if tur == 'YETKI':
        return ModulHatasi(403, 'YETKI', 'Bu bilgiyi görme yetkiniz yok.')
    if tur == 'DURUM':
        return ModulHatasi(409, 'DURUM', neden_cumlesi(neden) or 'Kayıt bu durumda değil.')
    if tur == 'BAGLANTI':
        gunluk.warning('Çekirdeğe ulaşılamadı: %s', neden)
        return ModulHatasi(503, 'BAGLANTI', 'Çekirdeğe ulaşılamıyor, biraz sonra yeniden deneyin.')
    if tur == 'URUN':
        gunluk.error('Çekirdekte beklenmeyen hata: %s', neden)
        return ModulHatasi(502, 'URUN', 'Çekirdekte beklenmeyen hata.')
    gunluk.error('Modülün hatası (%s): %s', tur, neden)
    if tur == 'BICIM':
        return ModulHatasi(400, 'BICIM', 'Beklenmeyen bir hata oldu.')
    return ModulHatasi(500, tur, 'Beklenmeyen bir hata oldu.')
