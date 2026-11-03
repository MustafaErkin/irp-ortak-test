"""Müşteriler ve iletişim kişileri (SPEC › 8.1). Müşteri silinmez, pasifleştirilir; kişiler de öyle."""
from ..alan.arama import arama_metni, kelimeler

ALANLAR = ('ad', 'kisa_ad', 'adres', 'ulke', 'vergi_dairesi', 'vergi_no', 'strateji_notu', 'aktif')
KISI_ALANLARI = ('ad', 'unvan', 'telefon', 'eposta', 'aktif')


def _arama(m):
    return arama_metni(m.get('ad'), m.get('kisa_ad'), m.get('vergi_no'))


def liste(b, q=None, yalniz_aktif=False):
    kosul, p = ['TRUE'], []
    for k in kelimeler(q or ''):
        kosul.append('arama LIKE %s')
        p.append(f'%{k}%')
    if yalniz_aktif:
        kosul.append('aktif')
    return b.execute('SELECT kimlik, ad, kisa_ad, ulke, aktif FROM musteriler WHERE ' + ' AND '.join(kosul)
                     + ' ORDER BY ad', p).fetchall()


def ayni_adli(b, ad, haric=None):
    """Normal adı aynı olan müşteriler (uyarı için)."""
    n = arama_metni(ad)
    return [m for m in b.execute('SELECT kimlik, ad, kisa_ad FROM musteriler WHERE kimlik IS DISTINCT FROM %s',
                                 (haric,)) if arama_metni(m['ad']) == n]


def bul(b, kimlik, kilitle=False):
    return b.execute('SELECT kimlik, ad, kisa_ad, adres, ulke, vergi_dairesi, vergi_no, strateji_notu, aktif, '
                     'olusturan, olusturma_ani FROM musteriler WHERE kimlik = %s' + (' FOR UPDATE' if kilitle else ''),
                     (kimlik,)).fetchone()


def kisiler(b, musteri, yalniz_aktif=False):
    return b.execute('SELECT kimlik, ad, unvan, telefon, eposta, aktif FROM musteri_kisileri WHERE musteri = %s'
                     + (' AND aktif' if yalniz_aktif else '') + ' ORDER BY kimlik', (musteri,)).fetchall()


def ekle(b, m, kim, an):
    kimlik = b.execute('INSERT INTO musteriler (ad, kisa_ad, adres, ulke, vergi_dairesi, vergi_no, strateji_notu, '
                       'aktif, olusturan, olusturma_ani, arama) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) '
                       'RETURNING kimlik', (*(m[a] for a in ALANLAR), kim, an, _arama(m))).fetchone()['kimlik']
    kisileri_yaz(b, kimlik, m.get('kisiler', []))
    return kimlik


def guncelle(b, kimlik, m):
    atama = ', '.join(f'{a} = %s' for a in ALANLAR)
    b.execute(f'UPDATE musteriler SET {atama}, arama = %s WHERE kimlik = %s',
              (*(m[a] for a in ALANLAR), _arama(m), kimlik))
    kisileri_yaz(b, kimlik, m.get('kisiler', []))


def kisileri_yaz(b, musteri, kisiler_):
    """Kimliği olan kişi güncellenir, olmayan eklenir; listede olmayan kişi pasifleşir (silinmez)."""
    tutulan = []
    for k in kisiler_:
        if k.get('kimlik'):
            b.execute('UPDATE musteri_kisileri SET ad = %s, unvan = %s, telefon = %s, eposta = %s, aktif = %s '
                      'WHERE kimlik = %s AND musteri = %s', (*(k[a] for a in KISI_ALANLARI), k['kimlik'], musteri))
            tutulan.append(k['kimlik'])
        else:
            tutulan.append(b.execute('INSERT INTO musteri_kisileri (musteri, ad, unvan, telefon, eposta, aktif) '
                                     'VALUES (%s, %s, %s, %s, %s, %s) RETURNING kimlik',
                                     (musteri, *(k[a] for a in KISI_ALANLARI))).fetchone()['kimlik'])
    b.execute('UPDATE musteri_kisileri SET aktif = false WHERE musteri = %s AND NOT (kimlik = ANY(%s))',
              (musteri, tutulan))
