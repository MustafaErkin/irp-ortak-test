"""Sürümün ve talebin durumları ve geçişleri (SPEC › 8.10, 8.11, 8.12). Saf; tablolar testle sınanır.

Geçiş verilen kişiye göre denetlenir: önce yetki (403), sonra durum (409 DURUM; onaysız gönderimde 409 KAPI).
"""
from .. import hatalar

# ---- sürüm

TASLAK, ONAY_BEKLIYOR, ONAYLANDI, GONDERILDI = 'TASLAK', 'ONAY_BEKLIYOR', 'ONAYLANDI', 'GONDERILDI'
SURUM_DURUMLARI = (TASLAK, ONAY_BEKLIYOR, ONAYLANDI, GONDERILDI)

# eylem → (geçerli olduğu durum, yeni durum, kim)
SURUM_GECISLERI = {
    'ONAYA_GONDER': (TASLAK, ONAY_BEKLIYOR, 'DUZENLEYICI'),
    'ONAYLA': (ONAY_BEKLIYOR, ONAYLANDI, 'ONAYCI'),
    'GERI_GONDER': (ONAY_BEKLIYOR, TASLAK, 'ONAYCI'),
    'DUZENLEMEYE_AC': (ONAYLANDI, TASLAK, 'HAZIRLAYAN_YA_DA_YETKILI'),
    'GONDERILDI': (ONAYLANDI, GONDERILDI, 'DUZENLEYICI'),
}

YETKI_MESAJI = {
    'DUZENLEYICI': 'Bu işi satış yöneticisi ya da yetkili yapar.',
    'ONAYCI': 'Teklifi yalnızca onaycı (yetkili) onaylar ya da geri gönderir.',
    'HAZIRLAYAN_YA_DA_YETKILI': 'Sürümü yalnızca hazırlayan ya da yetkili düzenlemeye açar.',
    'YETKILI': 'Bu işi yalnızca yetkili yapar.',
}


def _izinli(kim, kisi, hazirlayan=None):
    if kim == 'DUZENLEYICI':
        return kisi.duzenleyici
    if kim == 'ONAYCI':
        return kisi.onayci
    if kim == 'HAZIRLAYAN_YA_DA_YETKILI':
        return kisi.duzenlemeye_acabilir(hazirlayan)
    if kim == 'YETKILI':
        return kisi.yetkili
    raise ValueError(kim)


def surum_gecisi(durum, eylem, kisi, hazirlayan=None):
    """Sürümün yeni durumu; geçersizse ModulHatasi."""
    gecerli, yeni, kim = SURUM_GECISLERI[eylem]
    if not _izinli(kim, kisi, hazirlayan):
        raise hatalar.yetki(YETKI_MESAJI[kim])
    if durum != gecerli:
        if eylem == 'GONDERILDI':
            # Kapı: yalnızca onaylı sürüm gönderilir; geçiş yolu yok.
            raise hatalar.kapi()
        raise hatalar.durum('Bu sürüm bu durumda değiştirilemez.')
    return yeni


def surum_duzenlenebilir(durum, kisi):
    """Formu kim düzenler: TASLAK'ta düzenleyici; ONAY_BEKLIYOR'da yalnızca onaycı ("Kendim düzelt").
    ONAYLANDI ve GONDERILDI düzenlenmez (önce düzenlemeye açılır ya da yeni sürüm açılır)."""
    if durum == TASLAK:
        if not kisi.duzenleyici:
            raise hatalar.yetki(YETKI_MESAJI['DUZENLEYICI'])
        return 'HAZIRLAYAN'
    if durum == ONAY_BEKLIYOR:
        if not kisi.onayci:
            raise hatalar.durum('Sürüm onay bekliyor; yalnızca onaycı düzeltebilir.')
        return 'ONAYCI'
    if not kisi.duzenleyici:
        raise hatalar.yetki(YETKI_MESAJI['DUZENLEYICI'])
    raise hatalar.durum('Bu sürüm bu durumda değiştirilemez.')


# ---- talep

ACIK, TEKLIF_VERILDI, KAZANILDI, KAYBEDILDI, BEKLEMEDE, KAPATILDI = (
    'ACIK', 'TEKLIF_VERILDI', 'KAZANILDI', 'KAYBEDILDI', 'BEKLEMEDE', 'KAPATILDI')
TALEP_DURUMLARI = (ACIK, TEKLIF_VERILDI, KAZANILDI, KAYBEDILDI, BEKLEMEDE, KAPATILDI)
KAYIP_NEDENLERI = ('FIYAT', 'TEKNIK_COZUM', 'TESLIM_SURESI')

# eylem → ({geçerli durumlar}, yeni durum, kim). GERI_AC'ın yeni durumu gönderilmiş sürüme bağlıdır.
TALEP_GECISLERI = {
    'GONDERIM': ({ACIK, BEKLEMEDE, TEKLIF_VERILDI}, TEKLIF_VERILDI, 'DUZENLEYICI'),
    'KAPAT': ({ACIK, BEKLEMEDE}, KAPATILDI, 'DUZENLEYICI'),
    'KAZANILDI': ({TEKLIF_VERILDI, BEKLEMEDE}, KAZANILDI, 'DUZENLEYICI'),
    'KAYBEDILDI': ({TEKLIF_VERILDI, BEKLEMEDE}, KAYBEDILDI, 'DUZENLEYICI'),
    'BEKLEMEDE': ({TEKLIF_VERILDI}, BEKLEMEDE, 'DUZENLEYICI'),
    'BEKLENIYOR': ({BEKLEMEDE}, TEKLIF_VERILDI, 'DUZENLEYICI'),
    'GERI_AC': ({KAYBEDILDI, KAPATILDI}, None, 'YETKILI'),
}

# Yeni sürüm yalnızca bu durumlarda açılır (8.3)
SURUM_ACILABILIR = {ACIK, TEKLIF_VERILDI, BEKLEMEDE}


def talep_gecisi(durum, eylem, kisi, gonderilmis_var=False):
    gecerli, yeni, kim = TALEP_GECISLERI[eylem]
    if not _izinli(kim, kisi):
        raise hatalar.yetki(YETKI_MESAJI[kim])
    if durum not in gecerli:
        raise hatalar.durum('Talep bu durumda bu işe uygun değil.')
    if eylem == 'GERI_AC':
        return TEKLIF_VERILDI if gonderilmis_var else ACIK
    return yeni


def talep_duzenlenebilir(kisi):
    """Talebin alanları, dosyaları, gereksinim ve kapsamı. Gönderilmiş sürüm onay anındaki özetle kalır (8.10)."""
    if not kisi.duzenleyici:
        raise hatalar.yetki(YETKI_MESAJI['DUZENLEYICI'])


def yeni_surum_acilabilir(talep_durumu, acik_surum_var, kisi):
    if not kisi.duzenleyici:
        raise hatalar.yetki(YETKI_MESAJI['DUZENLEYICI'])
    if talep_durumu not in SURUM_ACILABILIR:
        raise hatalar.durum('Bu talepte yeni sürüm açılamaz.')
    if acik_surum_var:
        raise hatalar.durum('Talepte gönderilmemiş bir sürüm var; yeni sürüm ondan sonra açılır.')


# ---- liste

ACIK_DURUMLAR = (ACIK, TEKLIF_VERILDI, BEKLEMEDE)


def cevap_isareti(talep_durumu, gonderilmis_var, cevap_tarihi, bugun, uyari_gun):
    """▲ "Cevap tarihi yaklaşıyor / geçti" (8.13): ACIK ya da BEKLEMEDE, gönderilmiş sürümü yok ve cevap tarihine
    uyari_gun ya da daha az gün kalmış ya da geçmiş. Çekirdeğin hatırlatması istek M10-01'dedir."""
    if talep_durumu not in (ACIK, BEKLEMEDE) or gonderilmis_var or cevap_tarihi is None:
        return None
    kalan = (cevap_tarihi - bugun).days
    if kalan < 0:
        return {'tur': 'GECTI', 'metin': 'Cevap tarihi geçti', 'kalan_gun': kalan}
    if kalan <= uyari_gun:
        return {'tur': 'YAKLASIYOR', 'metin': 'Cevap tarihi yaklaşıyor', 'kalan_gun': kalan}
    return None
