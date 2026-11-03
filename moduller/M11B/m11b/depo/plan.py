"""plan_degisiklikleri, plan_satirlari, plan_kanitlari, etap_ekleri."""
from psycopg.types.json import Jsonb

from ..ayarlar import SEMA

ACIK = ('TASLAK', 'GONDERILIYOR', 'YARIM')


def acik_degisiklik(b, proje, kilitle=False):
    """Projenin açık değişikliği. kilitle: satırı FOR UPDATE NOWAIT ile kilitler; kilit alınamazsa
    psycopg.errors.LockNotAvailable (başka bir gönderim sürüyor)."""
    kilit = ' FOR UPDATE NOWAIT' if kilitle else ''
    return b.execute(f'SELECT * FROM {SEMA}.plan_degisiklikleri WHERE proje = %s AND durum = ANY(%s){kilit}',
                     (proje, list(ACIK))).fetchone()


def degisiklik_ekle(b, proje, tur, hazirlayan, an, neden, gerekce):
    return b.execute(
        f"INSERT INTO {SEMA}.plan_degisiklikleri (proje, tur, durum, hazirlayan, hazirlama_ani, neden, gerekce) "
        "VALUES (%s, %s, 'TASLAK', %s, %s, %s, %s) RETURNING *", (proje, tur, hazirlayan, an, neden, gerekce)).fetchone()


def degisiklik_guncelle(b, kimlik, **alanlar):
    atama = ', '.join(f'{k} = %s' for k in alanlar)
    return b.execute(f'UPDATE {SEMA}.plan_degisiklikleri SET {atama} WHERE kimlik = %s RETURNING *',
                     (*alanlar.values(), kimlik)).fetchone()


def degisiklik_sil(b, kimlik):
    b.execute(f"DELETE FROM {SEMA}.plan_degisiklikleri WHERE kimlik = %s AND durum = 'TASLAK'", (kimlik,))


def onaylananlar(b, proje):
    return b.execute(f"SELECT * FROM {SEMA}.plan_degisiklikleri WHERE proje = %s AND durum = 'ONAYLANDI' "
                     'ORDER BY onay_ani, kimlik', (proje,)).fetchall()


def surum_no_sonraki(b, proje, tur):
    """SPEC › 8.2.4: modülün başlangıç planı B0'dır; sonrakiler birer artar. B0 modül dışında onaylanmışsa numara yok."""
    if tur == 'BASLANGIC':
        return 0
    r = b.execute(f"SELECT max(surum_no) AS son, bool_or(tur = 'BASLANGIC') AS b0 FROM {SEMA}.plan_degisiklikleri "
                  "WHERE proje = %s AND durum = 'ONAYLANDI'", (proje,)).fetchone()
    return r['son'] + 1 if r['b0'] and r['son'] is not None else None


def satirlar(b, degisiklik):
    return b.execute(f'SELECT * FROM {SEMA}.plan_satirlari WHERE degisiklik = %s ORDER BY sira', (degisiklik,)).fetchall()


def satir(b, degisiklik, sira):
    return b.execute(f'SELECT * FROM {SEMA}.plan_satirlari WHERE degisiklik = %s AND sira = %s',
                     (degisiklik, sira)).fetchone()


def satirlari_sil(b, degisiklik, yalniz_gonderilmemis=False):
    kosul = " AND sonuc IS DISTINCT FROM 'BASARILI'" if yalniz_gonderilmemis else ''
    b.execute(f'DELETE FROM {SEMA}.plan_satirlari WHERE degisiklik = %s{kosul}', (degisiklik,))


def satir_ekle(b, degisiklik, s):
    b.execute(f'INSERT INTO {SEMA}.plan_satirlari (degisiklik, sira, islem, etap, okunan_surum, girdiler, etap_eki) '
              'VALUES (%s, %s, %s, %s, %s, %s, %s)',
              (degisiklik, s['sira'], s['islem'], s.get('etap'), s.get('okunan_surum'), Jsonb(s['girdiler']),
               Jsonb(s['etap_eki'])))


def satir_sonucu(b, degisiklik, sira, sonuc, olay_kimligi, red_kodu=None, red_nedeni=None, etap=None):
    b.execute(f'UPDATE {SEMA}.plan_satirlari SET sonuc = %s, olay_kimligi = %s, red_kodu = %s, red_nedeni = %s, '
              'etap = coalesce(%s, etap) WHERE degisiklik = %s AND sira = %s',
              (sonuc, olay_kimligi, red_kodu, red_nedeni, etap, degisiklik, sira))


def satir_surumu(b, degisiklik, sira, surum):
    b.execute(f'UPDATE {SEMA}.plan_satirlari SET okunan_surum = %s, sonuc = NULL, red_kodu = NULL, red_nedeni = NULL '
              'WHERE degisiklik = %s AND sira = %s', (surum, degisiklik, sira))


def kanitlar(b, degisiklik):
    return [r['dosya'] for r in b.execute(f'SELECT dosya FROM {SEMA}.plan_kanitlari WHERE degisiklik = %s '
                                          'ORDER BY dosya', (degisiklik,)).fetchall()]


def kanitlari_yaz(b, degisiklik, dosyalar):
    b.execute(f'DELETE FROM {SEMA}.plan_kanitlari WHERE degisiklik = %s', (degisiklik,))
    for d in dosyalar:
        b.execute(f'INSERT INTO {SEMA}.plan_kanitlari (degisiklik, dosya) VALUES (%s, %s)', (degisiklik, d))


def etap_ekleri(b, proje):
    return {r['etap']: r for r in b.execute(f'SELECT * FROM {SEMA}.etap_ekleri WHERE proje = %s', (proje,)).fetchall()}


def etap_eki_yaz(b, etap, proje, ek):
    b.execute(f'INSERT INTO {SEMA}.etap_ekleri (etap, proje, sablon_kodu, sira, paralel_grup, tasarim_kapisi) '
              'VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (etap) DO UPDATE SET sablon_kodu = EXCLUDED.sablon_kodu, '
              'sira = EXCLUDED.sira, paralel_grup = EXCLUDED.paralel_grup, tasarim_kapisi = EXCLUDED.tasarim_kapisi',
              (etap, proje, ek.get('sablon_kodu'), ek['sira'], ek.get('paralel_grup'), bool(ek.get('tasarim_kapisi'))))


def bildirim_bekleyenler(b, proje):
    return b.execute(f"SELECT * FROM {SEMA}.plan_degisiklikleri WHERE proje = %s AND durum = 'ONAYLANDI' "
                     'AND NOT bildirim_birakildi ORDER BY onay_ani, kimlik', (proje,)).fetchall()


def son_onaylanan(b, proje):
    return b.execute(f"SELECT * FROM {SEMA}.plan_degisiklikleri WHERE proje = %s AND durum = 'ONAYLANDI' "
                     'ORDER BY onay_ani DESC, kimlik DESC LIMIT 1', (proje,)).fetchone()


def bildirim_isaretle(b, proje):
    """Aynı bildirim B0, B1, B2… için güncellenir; en son sürümün bildirimi bırakılınca hepsi işaretlenir."""
    b.execute(f"UPDATE {SEMA}.plan_degisiklikleri SET bildirim_birakildi = true WHERE proje = %s "
              "AND durum = 'ONAYLANDI' AND NOT bildirim_birakildi", (proje,))
