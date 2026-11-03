""""Onaya gönder"in doğrulaması (SPEC › 8.10). Saf: hesaplanmış sürümden hatalar ve uyarılar.

Her hata {alan, sira, mesaj}; uyarılar durdurmaz.
"""
from ..hatalar import hata
from .hesap import eksik


def onaya_gonderim(surum, hesap, takvim_hesap, talep):
    """surum: genel alanlar (teslim_suresi_hafta, gecerlilik_gun) ve takvim satırları;
    hesap: hesap.surum_hesabi; takvim_hesap: takvim.takvim_hesabi;
    talep: {kapsam: [...], gereksinimler: [...]}.
    → (hatalar, uyarilar)"""
    hatalar, uyarilar = [], []
    kalemler, iscilik = hesap['kalemler'], hesap['iscilik']
    if not kalemler and not iscilik:
        hatalar.append(hata('kalemler', 'En az bir maliyet kalemi ya da işçilik satırı olmalı.'))
    for k in kalemler:
        if k.get('birim_fiyat') is None or not k.get('para_birimi'):
            hatalar.append(hata('kalemler.birim_fiyat', f'"{k.get("aciklama")}" kaleminin birim fiyatı ve para birimi yok.',
                                k.get('sira')))
    for i, s in enumerate(iscilik, 1):
        if s.get('saat_ucreti') is None or not s.get('para_birimi'):
            hatalar.append(hata('iscilik.saat_ucreti', f'{s["birim"]} biriminin saat ücreti tanımlı değil.', i))
    for p in hesap['eksik_kurlar']:
        hatalar.append(hata('kurlar', f'{p} kuru girilmeli.'))
    if eksik(hesap['fiyat']) or eksik(hesap['kar_orani']) or not hesap['fiyat'] or hesap['fiyat'] <= 0:
        hatalar.append(hata('fiyat', 'Fiyat ve kâr hesaplanmış olmalı; fiyat sıfırdan büyük olmalı.'))
    if not surum.get('takvim'):
        hatalar.append(hata('takvim', 'Takvimde en az bir satır olmalı.'))
    teslim, en_erken = surum.get('teslim_suresi_hafta'), takvim_hesap['en_erken_teslim_hafta']
    if teslim is None:
        hatalar.append(hata('teslim_suresi_hafta', 'Teslim süresi girilmeli.'))
    elif teslim < en_erken:
        hatalar.append(hata('teslim_suresi_hafta',
                            f'Teslim süresi ({teslim} hafta) en erken teslimden ({en_erken} hafta) kısa olamaz.'))
    if not surum.get('gecerlilik_gun'):
        hatalar.append(hata('gecerlilik_gun', 'Geçerlilik günü girilmeli.'))
    if not talep.get('kapsam'):
        uyarilar.append(hata('kapsam', 'Kapsam boş.'))
    acik = [g for g in talep.get('gereksinimler', []) if g.get('belirsiz') and not (g.get('cevap') or '').strip()]
    if acik:
        uyarilar.append(hata('gereksinimler', f'{len(acik)} belirsiz ve cevapsız gereksinim var.'))
    return hatalar, uyarilar
