"""Teklif sürümü ve dört bölümü: maliyet kalemleri, işçilik, takvim; fiyat sürümün kendisinde (SPEC › 8.3).

Çocuk satırları tek işlemde bütün olarak yazılır. Gönderilmiş sürümün satırını veritabanının tetikleyicisi,
çocuk satırlarını modülün kuralı korur (alan/durum.surum_duzenlenebilir).
"""
from psycopg.types.json import Jsonb

GENEL = ('para_birimi', 'fiyat_girisi', 'kar_orani', 'fiyat', 'toplam_hafta', 'teslim_suresi_hafta', 'gecerlilik_gun',
         'teknik_cozum', 'odeme_kosullari', 'teslim_kosullari', 'notlar')
METINLER = ('teknik_cozum', 'odeme_kosullari', 'teslim_kosullari', 'notlar')
KALEM = ('unsur', 'katalog_kalemi', 'aciklama', 'adet', 'olcu_birimi', 'birim_fiyat', 'para_birimi', 'kaynak_etiketi',
         'kaynak_notu', 'kaynak_tarihi', 'kaynak_dosyasi', 'temin_hafta', 'kritik')
ISCILIK = ('birim', 'saat', 'saat_ucreti', 'para_birimi', 'aciklama')
TAKVIM = ('etap_kodu', 'ad', 'paralel_grup', 'baslangic_hafta', 'sure_hafta')

SECIM = ('SELECT s.kimlik, s.talep, s.no, s.durum, s.kaynak_surum, s.para_birimi, s.kar_orani, s.fiyat, s.fiyat_girisi, '
         's.toplam_hafta, s.teslim_suresi_hafta, s.gecerlilik_gun, s.teknik_cozum, s.odeme_kosullari, '
         's.teslim_kosullari, s.notlar, s.hazirlayan, s.olusturma_ani, s.onaya_gonderen, s.onaya_gonderim_ani, '
         's.onaylayan, s.onay_ani, s.gonderen, s.gonderim_ani, s.gonderim_sekli, s.gonderim_notu, s.pdf_parmak_izi, '
         's.donmus_ozet, s.surum, t.talep_no, t.durum AS talep_durumu '
         'FROM teklif_surumleri s JOIN talepler t ON t.kimlik = s.talep ')


def bul(b, kimlik, kilitle=False):
    if kilitle:
        b.execute('SELECT 1 FROM teklif_surumleri WHERE kimlik = %s FOR UPDATE', (kimlik,))
    return b.execute(SECIM + 'WHERE s.kimlik = %s', (kimlik,)).fetchone()


def pdf(b, kimlik):
    return b.execute('SELECT pdf, pdf_parmak_izi FROM teklif_surumleri WHERE kimlik = %s', (kimlik,)).fetchone()


def son_no(b, talep):
    return b.execute('SELECT coalesce(max(no), 0) AS n FROM teklif_surumleri WHERE talep = %s', (talep,)).fetchone()['n']


def acik_surum(b, talep):
    return b.execute("SELECT kimlik, no FROM teklif_surumleri WHERE talep = %s AND durum <> 'GONDERILDI'",
                     (talep,)).fetchone()


def ekle(b, talep, no, genel, kaynak_surum, hazirlayan, an):
    return b.execute(f'INSERT INTO teklif_surumleri (talep, no, kaynak_surum, hazirlayan, olusturma_ani, '
                     f'{", ".join(GENEL)}) VALUES (%s, %s, %s, %s, %s, {", ".join(["%s"] * len(GENEL))}) '
                     'RETURNING kimlik', (talep, no, kaynak_surum, hazirlayan, an,
                                          *(genel.get(a) for a in GENEL))).fetchone()['kimlik']


def guncelle(b, kimlik, degerler):
    """Sürüm satırını değiştirir; eşzamanlılık sayacı bir artar."""
    atama = ', '.join(f'{a} = %s' for a in degerler)
    deger = [Jsonb(v) if a == 'donmus_ozet' and v is not None else v for a, v in degerler.items()]
    b.execute(f'UPDATE teklif_surumleri SET {atama}, surum = surum + 1 WHERE kimlik = %s', (*deger, kimlik))


# ---- çocuk satırları

def kalemler(b, surum):
    return b.execute('SELECT m.kimlik, m.sira, m.unsur, u.ad AS unsur_adi, u.butce_kalemi, m.katalog_kalemi, '
                     'k.kod AS katalog_kodu, k.tipik_temin_hafta AS katalog_temin_hafta, m.aciklama, m.adet, '
                     'm.olcu_birimi, m.birim_fiyat, m.para_birimi, m.kaynak_etiketi, m.kaynak_notu, m.kaynak_tarihi, '
                     'm.kaynak_dosyasi, m.temin_hafta, m.kritik '
                     'FROM maliyet_kalemleri m JOIN maliyet_unsurlari u ON u.kod = m.unsur '
                     'LEFT JOIN katalog_kalemleri k ON k.kimlik = m.katalog_kalemi '
                     'WHERE m.surum = %s ORDER BY m.sira', (surum,)).fetchall()


def iscilik(b, surum):
    return b.execute('SELECT birim, saat, saat_ucreti, para_birimi, aciklama FROM iscilik_satirlari WHERE surum = %s '
                     'ORDER BY sira NULLS LAST, birim', (surum,)).fetchall()


def takvim(b, surum):
    return b.execute('SELECT sira, etap_kodu, ad, paralel_grup, baslangic_hafta, sure_hafta FROM takvim_satirlari '
                     'WHERE surum = %s ORDER BY sira', (surum,)).fetchall()


def kurlar(b, surum):
    return b.execute('SELECT para_birimi, kur_try, kur_tarihi FROM surum_kurlari WHERE surum = %s '
                     'ORDER BY para_birimi', (surum,)).fetchall()


def cocuklari_yaz(b, surum, kalemler_, iscilik_, takvim_, kurlar_):
    """Dört bölümün satırları tek işlemde, bütün olarak (8.3)."""
    for tablo in ('maliyet_kalemleri', 'iscilik_satirlari', 'takvim_satirlari', 'surum_kurlari'):
        b.execute(f'DELETE FROM {tablo} WHERE surum = %s', (surum,))
    for sira, k in enumerate(kalemler_, 1):
        b.execute(f'INSERT INTO maliyet_kalemleri (surum, sira, {", ".join(KALEM)}) '
                  f'VALUES (%s, %s, {", ".join(["%s"] * len(KALEM))})', (surum, sira, *(k.get(a) for a in KALEM)))
    for sira, s in enumerate(iscilik_, 1):
        b.execute(f'INSERT INTO iscilik_satirlari (surum, sira, {", ".join(ISCILIK)}) '
                  f'VALUES (%s, %s, {", ".join(["%s"] * len(ISCILIK))})', (surum, sira, *(s.get(a) for a in ISCILIK)))
    for sira, t in enumerate(takvim_, 1):
        b.execute(f'INSERT INTO takvim_satirlari (surum, sira, {", ".join(TAKVIM)}) '
                  f'VALUES (%s, %s, {", ".join(["%s"] * len(TAKVIM))})', (surum, sira, *(t.get(a) for a in TAKVIM)))
    for k in kurlar_:
        b.execute('INSERT INTO surum_kurlari (surum, para_birimi, kur_try, kur_tarihi) VALUES (%s, %s, %s, %s)',
                  (surum, k['para_birimi'], k['kur_try'], k['kur_tarihi']))


def onay_kaydi(b, surum, karar, kim, an, gerekce=None):
    b.execute('INSERT INTO onay_kayitlari (surum, karar, gerekce, kim, an) VALUES (%s, %s, %s, %s, %s)',
              (surum, karar, gerekce, kim, an))


def onay_kayitlari(b, surum):
    return b.execute('SELECT karar, gerekce, kim, an FROM onay_kayitlari WHERE surum = %s ORDER BY an, kimlik',
                     (surum,)).fetchall()
