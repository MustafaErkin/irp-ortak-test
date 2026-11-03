"""Talep: tek kayıt, altında gereksinimler, kapsam, dosya kayıtları ve sürümler (SPEC › 8.2)."""
import re

from ..alan.arama import arama_metni

ALANLAR = ('musteri', 'kaynak', 'bagli_proje', 'tur', 'makine_turu', 'konu', 'aciklama', 'gelis_tarihi', 'cevap_tarihi')
SONUC_ALANLARI = ('durum', 'kazanan_surum', 'kayip_nedeni', 'kayip_aciklamasi', 'kapatma_gerekcesi', 'sonuc_ani',
                  'sonucu_yazan')

SECIM = ('SELECT t.kimlik, t.talep_no, t.musteri, m.ad AS musteri_adi, m.kisa_ad AS musteri_kisa_adi, t.kaynak, '
         't.bagli_proje, t.tur, t.makine_turu, mt.ad AS makine_turu_adi, t.konu, t.aciklama, t.gelis_tarihi, '
         't.cevap_tarihi, t.durum, t.kazanan_surum, t.kayip_nedeni, t.kayip_aciklamasi, t.kapatma_gerekcesi, '
         't.sonuc_ani, t.sonucu_yazan, t.olusturan, t.olusturma_ani, t.surum '
         'FROM talepler t JOIN musteriler m ON m.kimlik = t.musteri '
         'LEFT JOIN makine_turleri mt ON mt.kod = t.makine_turu ')


def talep_no(b, desen, yil):
    """Talep numarası: deseni (`T-{YYYY}-{SIRA4}`) yıl ve yıl başına tek işlemde artan sırayla doldurur."""
    sira = b.execute('SELECT sayac_ilerlet(%s, %s) AS n', ('TALEP', str(yil))).fetchone()['n']
    no = desen.replace('{YYYY}', str(yil))
    return re.sub(r'\{SIRA(\d+)\}', lambda m: f'{sira:0{m.group(1)}d}', no)


def ekle(b, t, no, kim, an):
    alanlar = ', '.join(ALANLAR)
    yer = ', '.join(['%s'] * len(ALANLAR))
    return b.execute(f'INSERT INTO talepler (talep_no, {alanlar}, olusturan, olusturma_ani) '
                     f'VALUES (%s, {yer}, %s, %s) RETURNING kimlik',
                     (no, *(t.get(a) for a in ALANLAR), kim, an)).fetchone()['kimlik']


def bul(b, kimlik, kilitle=False):
    if kilitle:
        b.execute('SELECT 1 FROM talepler WHERE kimlik = %s FOR UPDATE', (kimlik,))
    return b.execute(SECIM + 'WHERE t.kimlik = %s', (kimlik,)).fetchone()


def guncelle(b, kimlik, degerler):
    """Talep satırını değiştirir; eşzamanlılık sayacı bir artar (8.3)."""
    atama = ', '.join(f'{a} = %s' for a in degerler)
    b.execute(f'UPDATE talepler SET {atama}, surum = surum + 1 WHERE kimlik = %s', (*degerler.values(), kimlik))


# ---- gereksinimler ve kapsam

def gereksinimler(b, talep):
    return b.execute('SELECT sira, metin, belirsiz, soru, cevap, cevap_ani FROM gereksinimler WHERE talep = %s '
                     'ORDER BY sira', (talep,)).fetchall()


def gereksinimleri_yaz(b, talep, satirlar, an):
    """Liste bütün olarak yazılır. Cevap değişmeyen satır eski cevap anını korur."""
    eski = {(g['metin'], g['cevap']): g['cevap_ani'] for g in gereksinimler(b, talep)}
    b.execute('DELETE FROM gereksinimler WHERE talep = %s', (talep,))
    for sira, g in enumerate(satirlar, 1):
        cevap = (g.get('cevap') or '').strip() or None
        cevap_ani = eski.get((g['metin'], cevap)) or (an if cevap else None)
        b.execute('INSERT INTO gereksinimler (talep, sira, metin, belirsiz, soru, cevap, cevap_ani) '
                  'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  (talep, sira, g['metin'], g.get('belirsiz', False), g.get('soru'), cevap, cevap_ani))


def kapsam(b, talep):
    k = {'dahil': [], 'haric': []}
    for s in b.execute('SELECT tur, metin FROM kapsam_satirlari WHERE talep = %s ORDER BY tur, sira', (talep,)):
        k['dahil' if s['tur'] == 'DAHIL' else 'haric'].append(s['metin'])
    return k


def kapsam_yaz(b, talep, k):
    b.execute('DELETE FROM kapsam_satirlari WHERE talep = %s', (talep,))
    for tur, anahtar in (('DAHIL', 'dahil'), ('HARIC', 'haric')):
        for sira, metin in enumerate(k.get(anahtar, []), 1):
            b.execute('INSERT INTO kapsam_satirlari (talep, tur, sira, metin) VALUES (%s, %s, %s, %s)',
                      (talep, tur, sira, metin))


# ---- dosyalar (kayıt; dosyanın kendisi şirket sunucusunda; istek M10-05)

def dosyalar(b, talep):
    return b.execute('SELECT kimlik, tur, ad, konum, aciklama, parmak_izi, ekleyen, ekleme_ani FROM talep_dosyalari '
                     'WHERE talep = %s ORDER BY kimlik', (talep,)).fetchall()


def dosya_ekle(b, talep, d, kim, an):
    return b.execute('INSERT INTO talep_dosyalari (talep, tur, ad, konum, aciklama, parmak_izi, ekleyen, ekleme_ani) '
                     'VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING kimlik',
                     (talep, d['tur'], d['ad'], d['konum'], d.get('aciklama'), d.get('parmak_izi'), kim,
                      an)).fetchone()['kimlik']


# ---- sürümlerin özeti

def surum_ozetleri(b, talep):
    return b.execute('SELECT kimlik, no, durum, para_birimi, fiyat, kar_orani, teslim_suresi_hafta, hazirlayan, '
                     'olusturma_ani, onaylayan, onay_ani, gonderim_ani, kaynak_surum FROM teklif_surumleri '
                     'WHERE talep = %s ORDER BY no', (talep,)).fetchall()


# ---- arama metni (8.13)

def arama_yenile(b, talep):
    """Talep no, müşteri adı ve kısa adı, konu, açıklama, makine türünün adı, gereksinimler, kapsam ve en son
    sürümün kalem açıklamaları."""
    t = bul(b, talep)
    parcalar = [t['talep_no'], t['musteri_adi'], t['musteri_kisa_adi'], t['konu'], t['aciklama'], t['makine_turu_adi']]
    parcalar += [g['metin'] for g in gereksinimler(b, talep)]
    k = kapsam(b, talep)
    parcalar += k['dahil'] + k['haric']
    parcalar += [r['aciklama'] for r in b.execute(
        'SELECT aciklama FROM maliyet_kalemleri WHERE surum = (SELECT kimlik FROM teklif_surumleri WHERE talep = %s '
        'ORDER BY no DESC LIMIT 1) ORDER BY sira', (talep,))]
    b.execute('UPDATE talepler SET arama = %s WHERE kimlik = %s', (arama_metni(*parcalar), talep))


# ---- liste ve sayaç şeridi (8.13)

def liste(b, kelimeler_=(), musteri=None, makine_turu=None, durum=None, yil=None):
    """Açık olanlar önce, cevap tarihi yakın olan önce. Son sürümün no'su, durumu ve fiyatı."""
    kosul, p = ['TRUE'], []
    for k in kelimeler_:
        kosul.append('t.arama LIKE %s')
        p.append(f'%{k}%')
    for alan, deger in (('t.musteri', musteri), ('t.makine_turu', makine_turu), ('t.durum', durum)):
        if deger is not None:
            kosul.append(f'{alan} = %s')
            p.append(deger)
    if yil is not None:
        kosul.append('extract(year FROM t.gelis_tarihi) = %s')
        p.append(yil)
    return b.execute(
        'SELECT t.kimlik, t.talep_no, t.musteri, m.ad AS musteri_adi, t.konu, t.makine_turu, mt.ad AS makine_turu_adi, '
        't.kaynak, t.tur, t.durum, t.gelis_tarihi, t.cevap_tarihi, '
        's.kimlik AS son_surum, s.no AS son_surum_no, s.durum AS son_surum_durumu, s.fiyat, s.para_birimi, '
        "EXISTS (SELECT 1 FROM teklif_surumleri g WHERE g.talep = t.kimlik AND g.durum = 'GONDERILDI') AS gonderilmis "
        'FROM talepler t JOIN musteriler m ON m.kimlik = t.musteri LEFT JOIN makine_turleri mt ON mt.kod = t.makine_turu '
        'LEFT JOIN LATERAL (SELECT kimlik, no, durum, fiyat, para_birimi FROM teklif_surumleri '
        '                   WHERE talep = t.kimlik ORDER BY no DESC LIMIT 1) s ON TRUE '
        'WHERE ' + ' AND '.join(kosul) +
        " ORDER BY (t.durum IN ('ACIK', 'TEKLIF_VERILDI', 'BEKLEMEDE')) DESC, t.cevap_tarihi ASC NULLS LAST, "
        't.talep_no DESC', p).fetchall()


def sayac(b, yil):
    """Seçili yılın (sonuc_ani yılı) kazanılan, kaybedilen ve kayıp nedenleri; şu anki açık talep sayısı."""
    r = b.execute(
        "SELECT count(*) FILTER (WHERE durum = 'KAZANILDI' AND extract(year FROM sonuc_ani) = %(y)s) AS kazanilan, "
        "count(*) FILTER (WHERE durum = 'KAYBEDILDI' AND extract(year FROM sonuc_ani) = %(y)s) AS kaybedilen, "
        "count(*) FILTER (WHERE durum = 'KAYBEDILDI' AND extract(year FROM sonuc_ani) = %(y)s "
        "                 AND kayip_nedeni = 'FIYAT') AS fiyat, "
        "count(*) FILTER (WHERE durum = 'KAYBEDILDI' AND extract(year FROM sonuc_ani) = %(y)s "
        "                 AND kayip_nedeni = 'TEKNIK_COZUM') AS teknik_cozum, "
        "count(*) FILTER (WHERE durum = 'KAYBEDILDI' AND extract(year FROM sonuc_ani) = %(y)s "
        "                 AND kayip_nedeni = 'TESLIM_SURESI') AS teslim_suresi, "
        "count(*) FILTER (WHERE durum IN ('ACIK', 'TEKLIF_VERILDI', 'BEKLEMEDE')) AS acik "
        'FROM talepler', {'y': yil}).fetchone()
    return r


def onay_bekleyenler(b):
    return b.execute(
        'SELECT s.kimlik, s.no, t.kimlik AS talep, t.talep_no, m.ad AS musteri_adi, t.konu, s.fiyat, s.para_birimi, '
        "s.hazirlayan, s.onaya_gonderen, s.onaya_gonderim_ani FROM teklif_surumleri s "
        'JOIN talepler t ON t.kimlik = s.talep JOIN musteriler m ON m.kimlik = t.musteri '
        "WHERE s.durum = 'ONAY_BEKLIYOR' ORDER BY s.onaya_gonderim_ani, s.kimlik").fetchall()
