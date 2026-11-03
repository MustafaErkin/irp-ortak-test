"""Modülün rol kuralı (SPEC › 6). Görünürlük çekirdeğindir; burada yalnızca modülün kendi işlerinin rolleri durur."""
DONUSTURME = frozenset({'SATIS', 'YETKILI'})
SIPARIS_VE_TICARI = frozenset({'SATIS', 'MUHASEBE', 'YETKILI'})
DEVRETME = frozenset({'SATIS', 'YETKILI'})
MUHASEBE_ISI = frozenset({'MUHASEBE', 'YETKILI'})
TUTAR_DEGISIKLIGI = frozenset({'SATIS', 'YETKILI'})
KAPANIS = frozenset({'MUHASEBE', 'YETKILI'})
TUTAR_GORME = frozenset({'SATIS', 'MUHASEBE', 'YETKILI'})
GELEN_KUTUSU = MUHASEBE_ISI
BUTCELER = TUTAR_GORME
AYARLAR = frozenset({'YETKILI'})

IZINLER = {
    'donusturme': DONUSTURME,
    'siparis_ve_ticari': SIPARIS_VE_TICARI,
    'devretme': DEVRETME,
    'muhasebe_isi': MUHASEBE_ISI,
    'tutar_degisikligi': TUTAR_DEGISIKLIGI,
    'kapanis': KAPANIS,
    'tutar_gorme': TUTAR_GORME,
    'gelen_kutusu': GELEN_KUTUSU,
    'butceler': BUTCELER,
    'ayarlar': AYARLAR,
}

MESAJLAR = {
    DONUSTURME: 'Siparişe dönüştürmeyi satış ya da yetkili yapar.',
    SIPARIS_VE_TICARI: 'Bu işi satış, muhasebe ya da yetkili yapar.',
    MUHASEBE_ISI: 'Bu işi muhasebe ya da yetkili yapar.',
    AYARLAR: 'Ayarları yalnızca yetkili değiştirir.',
}


def izinler(roller) -> dict[str, bool]:
    r = set(roller)
    return {ad: bool(r & kume) for ad, kume in IZINLER.items()}


def var_mi(roller, kume) -> bool:
    return bool(set(roller) & kume)
