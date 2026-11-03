"""Yeni sürümün başlangıcı (SPEC › 8.3). Saf: ayarlar ve kaynak sürüm verilir, yeni sürümün içeriği döner.

- BOS: para birimi, geçerlilik ve metinler varsayılanlardan; kurlar son_kurlar'dan.
- Bu talebin sürümünden: kalemler, işçilik, takvim, metinler, para birimi, kurlar, kâr ve fiyat girişi.
- Eski bir talebin sürümünden ("benzer işi bulmak"): kalemler, işçilik, takvim ve metinler. Müşteri talebe aittir,
  gelmez; kalemin kaynak dosyası öbür talebin kaydıdır, gelmez.
- İki kopyada da saat ücretleri o anki ayardan yeniden okunur.
"""
METINLER = ('teknik_cozum', 'odeme_kosullari', 'teslim_kosullari', 'notlar')
KALEM = ('unsur', 'katalog_kalemi', 'aciklama', 'adet', 'olcu_birimi', 'birim_fiyat', 'para_birimi', 'kaynak_etiketi',
         'kaynak_notu', 'kaynak_tarihi', 'kaynak_dosyasi', 'temin_hafta', 'kritik')
TAKVIM = ('etap_kodu', 'ad', 'paralel_grup', 'baslangic_hafta', 'sure_hafta')


def son_kurlar(ayar):
    return [{'para_birimi': p, 'kur_try': k['kur_try'], 'kur_tarihi': k['kur_tarihi']}
            for p, k in sorted((ayar or {}).items()) if p != 'TRY']


def ucretle(birim, saat, aciklama, ucretler):
    """İşçilik satırı: ücret ve para birimi ayardan gelir, satırda donar; tanımlı değilse boş."""
    u = ucretler.get(birim)
    return {'birim': birim, 'saat': saat, 'aciklama': aciklama,
            'saat_ucreti': u['ucret'] if u else None, 'para_birimi': u['para_birimi'] if u else None}


def bos(ayarlar):
    metinler = ayarlar.get('varsayilan_metinler') or {}
    genel = {'para_birimi': ayarlar.get('varsayilan_para_birimi') or 'TRY', 'fiyat_girisi': 'KAR',
             'gecerlilik_gun': ayarlar.get('varsayilan_gecerlilik_gun'),
             **{m: metinler.get(m) or None for m in METINLER if m != 'teknik_cozum'}}
    return {'genel': genel, 'kalemler': [], 'iscilik': [], 'takvim': [], 'kurlar': son_kurlar(ayarlar.get('son_kurlar'))}


def kopya(kaynak, ayarlar, ucretler, ayni_talep):
    """kaynak: {genel, kalemler, iscilik, takvim, kurlar}; ucretler: {birim: {ucret, para_birimi}}."""
    g = kaynak['genel']
    if ayni_talep:
        genel = {a: g.get(a) for a in ('para_birimi', 'fiyat_girisi', 'kar_orani', 'fiyat', 'toplam_hafta',
                                       'teslim_suresi_hafta', 'gecerlilik_gun', *METINLER)}
        kurlar = [{a: k[a] for a in ('para_birimi', 'kur_try', 'kur_tarihi')} for k in kaynak['kurlar']]
    else:
        genel = dict(bos(ayarlar)['genel'], toplam_hafta=g.get('toplam_hafta'), **{m: g.get(m) for m in METINLER})
        kurlar = son_kurlar(ayarlar.get('son_kurlar'))
    kalemler = [{a: k.get(a) for a in KALEM} for k in kaynak['kalemler']]
    if not ayni_talep:
        for k in kalemler:
            k['kaynak_dosyasi'] = None
    iscilik = [ucretle(s['birim'], s['saat'], s.get('aciklama'), ucretler) for s in kaynak['iscilik']]
    takvim = [{a: t.get(a) for a in TAKVIM} for t in kaynak['takvim']]
    return {'genel': genel, 'kalemler': kalemler, 'iscilik': iscilik, 'takvim': takvim, 'kurlar': kurlar}
