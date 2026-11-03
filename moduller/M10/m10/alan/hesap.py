"""Maliyet, kur ve fiyat hesabı (SPEC › 8.4, 8.5, 8.7, 8.8). Saf: veritabanına ve çekirdeğe dokunmaz.

- Para Decimal'dir; float yok. Yuvarlama iki ondalığa yarım yukarı, her satırda ayrı; toplam yuvarlanmış
  satırların toplamıdır (Ek D.2).
- Bilinmeyen tutar sıfır sayılmaz: VERI_EKSIK.
"""
from decimal import ROUND_HALF_UP, Decimal

VERI_EKSIK = 'VERI_EKSIK'
TL = 'TRY'
BUTCE_KALEMLERI = ('MALZEME', 'ISCILIK', 'FASON', 'GENEL_GIDER')
YUZ = Decimal(100)
SIFIR = Decimal('0.00')


def yuvarla(x, hane='0.01'):
    return Decimal(x).quantize(Decimal(hane), rounding=ROUND_HALF_UP)


def eksik(x):
    return x is None or x == VERI_EKSIK


def kur(kurlar, para_birimi):
    """1 birim kaç TL. TL'nin kuru 1; bilinmeyen kur None."""
    if para_birimi == TL:
        return Decimal(1)
    k = (kurlar or {}).get(para_birimi)
    return None if k is None else Decimal(k)


def cevir(tutar, kaynak, hedef, kurlar):
    """tutar_teklif = tutar × kur(kaynak) ÷ kur(hedef), iki ondalığa yarım yukarı. Kur eksikse VERI_EKSIK."""
    if eksik(tutar):
        return VERI_EKSIK
    if kaynak == hedef:
        return yuvarla(tutar)
    k1, k2 = kur(kurlar, kaynak), kur(kurlar, hedef)
    if k1 is None or k2 is None:
        return VERI_EKSIK
    return yuvarla(Decimal(tutar) * k1 / k2)


def kalem_tutari(k, para_birimi, kurlar):
    """Maliyet kalemi: tutar = adet × birim fiyat (kalemin para biriminde) ve teklif para birimine çevrilmişi."""
    if k.get('birim_fiyat') is None or not k.get('para_birimi'):
        return {'tutar': VERI_EKSIK, 'tutar_teklif': VERI_EKSIK, 'eksik_nedeni': 'FIYAT'}
    tutar = yuvarla(Decimal(k['adet']) * Decimal(k['birim_fiyat']))
    teklif = cevir(tutar, k['para_birimi'], para_birimi, kurlar)
    return {'tutar': tutar, 'tutar_teklif': teklif, 'eksik_nedeni': 'KUR' if teklif == VERI_EKSIK else None}


def iscilik_tutari(s, para_birimi, kurlar):
    """İşçilik: saat × saat ücreti (satırın para biriminde). Ücret tanımlı değilse VERI_EKSIK."""
    if s.get('saat_ucreti') is None or not s.get('para_birimi'):
        return {'tutar': VERI_EKSIK, 'tutar_teklif': VERI_EKSIK, 'eksik_nedeni': 'UCRET'}
    tutar = yuvarla(Decimal(s['saat']) * Decimal(s['saat_ucreti']))
    teklif = cevir(tutar, s['para_birimi'], para_birimi, kurlar)
    return {'tutar': tutar, 'tutar_teklif': teklif, 'eksik_nedeni': 'KUR' if teklif == VERI_EKSIK else None}


def topla(tutarlar):
    tutarlar = list(tutarlar)
    if any(eksik(t) for t in tutarlar):
        return VERI_EKSIK
    return sum(tutarlar, SIFIR)


def fiyat_ve_kar(maliyet, fiyat_girisi, kar_orani, fiyat):
    """Biri girilir, öbürü hesaplanır (8.8). Girilmiş olan sabit kalır.
    Kâr: maliyetin üstüne (S-5a, Faz 1). Marj: fiyatın yüzdesi olarak."""
    m = None if eksik(maliyet) else Decimal(maliyet)
    if fiyat_girisi == 'FIYAT':
        f = None if fiyat is None else yuvarla(fiyat)
        k = yuvarla((f / m - 1) * YUZ) if (f is not None and m) else None
    else:
        k = None if kar_orani is None else yuvarla(kar_orani)
        f = yuvarla(m * (1 + k / YUZ)) if (m is not None and k is not None) else None
    marj = yuvarla((f - m) / f * YUZ) if (f and m is not None) else None
    sonuc = {'kar_orani': k, 'fiyat': f, 'marj_yuzde': marj, 'fiyatin_yuzdesi_olsaydi': None}
    if fiyat_girisi != 'FIYAT' and m is not None and k is not None and k < YUZ:
        # "Kâr %20 fiyatın yüzdesi olsaydı fiyat … olurdu" (S-5a): maliyet ÷ (1 − kâr ÷ 100)
        sonuc['fiyatin_yuzdesi_olsaydi'] = yuvarla(m / (1 - k / YUZ))
    return sonuc


def kullanilan_yabanci_paralar(para_birimi, kalemler, iscilik):
    paralar = {para_birimi} | {x.get('para_birimi') for x in [*kalemler, *iscilik]}
    return sorted(p for p in paralar if p and p != TL)


def surum_hesabi(para_birimi, kurlar, kalemler, iscilik, fiyat_girisi='KAR', kar_orani=None, fiyat=None):
    """Sürümün bütün hesabı.

    kalemler: [{butce_kalemi, adet, birim_fiyat, para_birimi, ...}]
    iscilik: [{birim, saat, saat_ucreti, para_birimi, ...}]
    kurlar: {para_birimi: kur_try}
    """
    kalem_satirlari = [dict(k, **kalem_tutari(k, para_birimi, kurlar)) for k in kalemler]
    iscilik_satirlari = [dict(s, **iscilik_tutari(s, para_birimi, kurlar)) for s in iscilik]
    kirilim = {b: topla(k['tutar_teklif'] for k in kalem_satirlari if k['butce_kalemi'] == b) for b in BUTCE_KALEMLERI}
    kirilim['ISCILIK'] = topla([*(k['tutar_teklif'] for k in kalem_satirlari if k['butce_kalemi'] == 'ISCILIK'),
                                *(s['tutar_teklif'] for s in iscilik_satirlari)])
    maliyet = topla(kirilim.values())
    eksik_kurlar = [p for p in kullanilan_yabanci_paralar(para_birimi, kalemler, iscilik) if kur(kurlar, p) is None]
    return {'kalemler': kalem_satirlari, 'iscilik': iscilik_satirlari, 'kirilim': kirilim, 'maliyet': maliyet,
            'eksik_kurlar': eksik_kurlar, **fiyat_ve_kar(maliyet, fiyat_girisi, kar_orani, fiyat)}
