"""dosya_kayitlari: dosyanın kaydı modülde, dosyanın kendisi şirket sunucusunda. Kayıt silinmez, düzenlenmez."""
from ..ayarlar import SEMA


def dosyalar(b, proje, tur=None):
    kosul, p = ('AND tur = %s', (proje, tur)) if tur else ('', (proje,))
    return b.execute(f'SELECT * FROM {SEMA}.dosya_kayitlari WHERE proje = %s {kosul} ORDER BY kimlik', p).fetchall()


def dosya(b, kimlik):
    return b.execute(f'SELECT * FROM {SEMA}.dosya_kayitlari WHERE kimlik = %s', (kimlik,)).fetchone()


def dosya_sayisi(b, proje, tur):
    return b.execute(f'SELECT count(*) AS n FROM {SEMA}.dosya_kayitlari WHERE proje = %s AND tur = %s',
                     (proje, tur)).fetchone()['n']


def dosya_ekle(b, proje, klasor, tur, ad, konum, parmak_izi, aciklama, kaydeden, an):
    return b.execute(
        f'INSERT INTO {SEMA}.dosya_kayitlari (proje, klasor, tur, ad, konum, parmak_izi, aciklama, kaydeden, kayit_ani) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *',
        (proje, klasor, tur, ad, konum, parmak_izi, aciklama, kaydeden, an)).fetchone()
