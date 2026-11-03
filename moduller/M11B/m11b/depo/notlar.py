"""bilgi_notlari ve not_ekleri. Notun metni çekirdekteki NOT'tadır; burada yalnızca modülün bağları durur."""
from ..ayarlar import SEMA


def notlar(b, proje):
    return b.execute(f'SELECT n.*, k.ad AS kategori_adi FROM {SEMA}.bilgi_notlari n '
                     f'JOIN {SEMA}.not_kategorileri k ON k.kod = n.kategori WHERE n.proje = %s ORDER BY n.yazma_ani',
                     (proje,)).fetchall()


def not_(b, not_kimligi):
    return b.execute(f'SELECT n.*, k.ad AS kategori_adi FROM {SEMA}.bilgi_notlari n '
                     f'JOIN {SEMA}.not_kategorileri k ON k.kod = n.kategori WHERE n.not_kimligi = %s',
                     (not_kimligi,)).fetchone()


def not_ekle(b, not_kimligi, proje, kategori, alici_birim, etap, bagli_gorev, yazan, an, ekler):
    b.execute(f'INSERT INTO {SEMA}.bilgi_notlari (not_kimligi, proje, kategori, alici_birim, etap, bagli_gorev, yazan, '
              'yazma_ani) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (not_kimligi) DO NOTHING',
              (not_kimligi, proje, kategori, alici_birim, etap, bagli_gorev, yazan, an))
    for d in ekler:
        b.execute(f'INSERT INTO {SEMA}.not_ekleri (not_kimligi, dosya) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                  (not_kimligi, d))


def ekler(b, not_kimligi):
    return b.execute(f'SELECT d.kimlik, d.ad, d.konum, d.tur FROM {SEMA}.not_ekleri e '
                     f'JOIN {SEMA}.dosya_kayitlari d ON d.kimlik = e.dosya WHERE e.not_kimligi = %s ORDER BY d.kimlik',
                     (not_kimligi,)).fetchall()


def kategori_kodlari_dolu(b, proje):
    return {r['kategori'] for r in b.execute(f'SELECT DISTINCT kategori FROM {SEMA}.bilgi_notlari WHERE proje = %s',
                                             (proje,)).fetchall()}
