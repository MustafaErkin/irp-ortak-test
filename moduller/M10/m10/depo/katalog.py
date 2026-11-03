"""Ayarlar ekranının katalogları: para birimleri, maliyet unsurları, kalem kataloğu, makine türleri,
başlangıç tablosu, saat ücretleri, takvim şablonu (SPEC › 8.14)."""


# ---- para birimleri

def para_birimleri(b):
    return b.execute('SELECT kod, ad, sembol, aktif FROM para_birimleri ORDER BY kod').fetchall()


def para_birimi_aktif(b, kod, aktif):
    return b.execute('UPDATE para_birimleri SET aktif = %s WHERE kod = %s', (aktif, kod)).rowcount


# ---- maliyet unsurları

def unsurlar(b, yalniz_aktif=False):
    return b.execute('SELECT kod, ad, butce_kalemi, sik, aktif, sira FROM maliyet_unsurlari '
                     + ('WHERE aktif ' if yalniz_aktif else '') + 'ORDER BY sira, ad').fetchall()


def unsur(b, kod):
    return b.execute('SELECT kod, ad, butce_kalemi, sik, aktif, sira FROM maliyet_unsurlari WHERE kod = %s',
                     (kod,)).fetchone()


def unsur_ekle(b, u, kim, an):
    b.execute('INSERT INTO maliyet_unsurlari (kod, ad, butce_kalemi, sik, aktif, sira, ekleyen, ekleme_ani) '
              'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
              (u['kod'], u['ad'], u['butce_kalemi'], u.get('sik', False), u.get('aktif', True), u.get('sira', 100),
               kim, an))


def unsur_guncelle(b, u):
    return b.execute('UPDATE maliyet_unsurlari SET ad = %s, butce_kalemi = %s, sik = %s, aktif = %s, sira = %s '
                     'WHERE kod = %s', (u['ad'], u['butce_kalemi'], u['sik'], u['aktif'], u['sira'], u['kod'])).rowcount


def kullanilmis_unsurlar(b, kodlar):
    return {r['unsur'] for r in b.execute('SELECT DISTINCT unsur FROM maliyet_kalemleri WHERE unsur = ANY(%s)',
                                          (list(kodlar),))}


# ---- kalem kataloğu

KATALOG = ('SELECT k.kimlik, k.kod, k.ad, k.unsur, u.ad AS unsur_adi, u.butce_kalemi, k.olcu_birimi, k.birim_fiyat, '
           'k.para_birimi, k.fiyat_tarihi, k.fiyat_kaynagi, k.tipik_temin_hafta, k.kritik, k.aktif '
           'FROM katalog_kalemleri k JOIN maliyet_unsurlari u ON u.kod = k.unsur ')


def katalog(b, yalniz_aktif=False):
    return b.execute(KATALOG + ('WHERE k.aktif ' if yalniz_aktif else '') + 'ORDER BY k.kod').fetchall()


def katalog_kalemi(b, kimlik):
    return b.execute(KATALOG + 'WHERE k.kimlik = %s', (kimlik,)).fetchone()


KATALOG_ALANLARI = ('kod', 'ad', 'unsur', 'olcu_birimi', 'birim_fiyat', 'para_birimi', 'fiyat_tarihi', 'fiyat_kaynagi',
                    'tipik_temin_hafta', 'kritik', 'aktif')


def katalog_ekle(b, k):
    alanlar = ', '.join(KATALOG_ALANLARI)
    yer = ', '.join(['%s'] * len(KATALOG_ALANLARI))
    return b.execute(f'INSERT INTO katalog_kalemleri ({alanlar}) VALUES ({yer}) RETURNING kimlik',
                     [k[a] for a in KATALOG_ALANLARI]).fetchone()['kimlik']


def katalog_guncelle(b, kimlik, k):
    atama = ', '.join(f'{a} = %s' for a in KATALOG_ALANLARI)
    return b.execute(f'UPDATE katalog_kalemleri SET {atama} WHERE kimlik = %s',
                     [*(k[a] for a in KATALOG_ALANLARI), kimlik]).rowcount


def katalog_kodu_var(b, kod, haric=None):
    return b.execute('SELECT 1 FROM katalog_kalemleri WHERE kod = %s AND kimlik IS DISTINCT FROM %s',
                     (kod, haric)).fetchone() is not None


# ---- makine türleri ve başlangıç tablosu

def makine_turleri(b, yalniz_aktif=False):
    return b.execute('SELECT kod, ad, tipik_toplam_hafta, aktif FROM makine_turleri '
                     + ('WHERE aktif ' if yalniz_aktif else '') + 'ORDER BY ad').fetchall()


def makine_turu(b, kod):
    return b.execute('SELECT kod, ad, tipik_toplam_hafta, aktif FROM makine_turleri WHERE kod = %s', (kod,)).fetchone()


def makine_turu_kaydet(b, m):
    b.execute('INSERT INTO makine_turleri (kod, ad, tipik_toplam_hafta, aktif) VALUES (%s, %s, %s, %s) '
              'ON CONFLICT (kod) DO UPDATE SET ad = EXCLUDED.ad, tipik_toplam_hafta = EXCLUDED.tipik_toplam_hafta, '
              'aktif = EXCLUDED.aktif', (m['kod'], m['ad'], m.get('tipik_toplam_hafta'), m.get('aktif', True)))


def baslangic_tablosu(b, makine_turu=None):
    return b.execute('SELECT makine_turu, birim, tipik_saat, tipik_sure_hafta FROM baslangic_tablosu '
                     'WHERE %s::text IS NULL OR makine_turu = %s ORDER BY makine_turu, birim',
                     (makine_turu, makine_turu)).fetchall()


def baslangic_tablosu_yaz(b, satirlar):
    """Izgaranın tamamı yeniden yazılır (tabloya bağlı kayıt yoktur)."""
    b.execute('DELETE FROM baslangic_tablosu')
    for s in satirlar:
        b.execute('INSERT INTO baslangic_tablosu (makine_turu, birim, tipik_saat, tipik_sure_hafta) '
                  'VALUES (%s, %s, %s, %s)', (s['makine_turu'], s['birim'], s['tipik_saat'], s.get('tipik_sure_hafta')))


# ---- saat ücretleri

def saat_ucretleri(b):
    return b.execute('SELECT birim, ucret, para_birimi, guncelleyen, guncelleme_ani FROM saat_ucretleri '
                     'ORDER BY birim').fetchall()


def saat_ucreti(b, birim):
    return b.execute('SELECT birim, ucret, para_birimi FROM saat_ucretleri WHERE birim = %s', (birim,)).fetchone()


def saat_ucretleri_yaz(b, satirlar, kim, an):
    """Değişiklik yalnızca yeni işçilik satırlarını etkiler: ücret satırda donar (8.5)."""
    birimler = [s['birim'] for s in satirlar]
    b.execute('DELETE FROM saat_ucretleri WHERE NOT (birim = ANY(%s))', (birimler,))
    for s in satirlar:
        b.execute('INSERT INTO saat_ucretleri (birim, ucret, para_birimi, guncelleyen, guncelleme_ani) '
                  'VALUES (%s, %s, %s, %s, %s) ON CONFLICT (birim) DO UPDATE SET ucret = EXCLUDED.ucret, '
                  'para_birimi = EXCLUDED.para_birimi, guncelleyen = EXCLUDED.guncelleyen, '
                  'guncelleme_ani = EXCLUDED.guncelleme_ani '
                  'WHERE (saat_ucretleri.ucret, saat_ucretleri.para_birimi) IS DISTINCT FROM (EXCLUDED.ucret, EXCLUDED.para_birimi)',
                  (s['birim'], s['ucret'], s['para_birimi'], kim, an))


# ---- takvim şablonu

def takvim_sablonu(b, yalniz_aktif=False):
    return b.execute('SELECT kod, ad, sira, paralel_grup, birim, bas_orani, bit_orani, aktif FROM takvim_sablonu '
                     + ('WHERE aktif ' if yalniz_aktif else '') + 'ORDER BY sira').fetchall()


def sablon_guncelle(b, kod, birim, aktif):
    """Yalnızca birim ve aktiflik; kod, ad, sıra ve oranlar M1.1B ile ortaktır (Ek D.2)."""
    return b.execute('UPDATE takvim_sablonu SET birim = %s, aktif = %s WHERE kod = %s', (birim, aktif, kod)).rowcount
