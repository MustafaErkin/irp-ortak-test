"""devirler, klasorler ve şablon tabloları."""
from ..ayarlar import SEMA


def devir(b, proje):
    return b.execute(f'SELECT * FROM {SEMA}.devirler WHERE proje = %s', (proje,)).fetchone()


def devirler(b):
    return b.execute(f'SELECT * FROM {SEMA}.devirler ORDER BY baslama_ani').fetchall()


def devir_ekle(b, proje, baslatan, an):
    b.execute(f'INSERT INTO {SEMA}.devirler (proje, baslatan, baslama_ani) VALUES (%s, %s, %s) '
              'ON CONFLICT (proje) DO NOTHING', (proje, baslatan, an))
    return devir(b, proje)


def sunum_yaz(b, proje, an, kaydeden):
    b.execute(f'UPDATE {SEMA}.devirler SET sunum_ani = %s, sunumu_kaydeden = %s WHERE proje = %s', (an, kaydeden, proje))


def tamamlandi_yaz(b, proje, an):
    """Bir kez yazılır, geri alınmaz (SPEC › 8.9)."""
    b.execute(f'UPDATE {SEMA}.devirler SET tamamlanma_ani = %s WHERE proje = %s AND tamamlanma_ani IS NULL', (an, proje))


def klasor_sablonu(b):
    return b.execute(f'SELECT * FROM {SEMA}.klasor_sablonu ORDER BY sira').fetchall()


def etap_sablonu(b, yalniz_aktif=False):
    kosul = 'WHERE aktif' if yalniz_aktif else ''
    return b.execute(f'SELECT * FROM {SEMA}.etap_sablonu {kosul} ORDER BY sira').fetchall()


def not_kategorileri(b):
    return b.execute(f'SELECT * FROM {SEMA}.not_kategorileri ORDER BY sira').fetchall()


def klasor_ekle(b, proje, sablon_kodu, ad, sorumlu_birim):
    b.execute(f'INSERT INTO {SEMA}.klasorler (proje, sablon_kodu, ad, sorumlu_birim) VALUES (%s, %s, %s, %s) '
              'ON CONFLICT (proje, sablon_kodu) DO NOTHING', (proje, sablon_kodu, ad, sorumlu_birim))


def klasorler(b, proje):
    return b.execute(f'SELECT k.*, s.aciklama, s.sira FROM {SEMA}.klasorler k '
                     f'JOIN {SEMA}.klasor_sablonu s ON s.kod = k.sablon_kodu WHERE k.proje = %s ORDER BY s.sira',
                     (proje,)).fetchall()


def klasor_sayisi(b, proje):
    return b.execute(f'SELECT count(*) AS n FROM {SEMA}.klasorler WHERE proje = %s', (proje,)).fetchone()['n']


def etap_sablonu_guncelle(b, kod, varsayilan_birim, aktif):
    return b.execute(f'UPDATE {SEMA}.etap_sablonu SET varsayilan_birim = %s, aktif = %s WHERE kod = %s',
                     (varsayilan_birim, aktif, kod)).rowcount


def klasor_sablonu_guncelle(b, kod, sorumlu_birim):
    return b.execute(f'UPDATE {SEMA}.klasor_sablonu SET sorumlu_birim = %s WHERE kod = %s',
                     (sorumlu_birim, kod)).rowcount


def not_kategorisi_guncelle(b, kod, varsayilan_birim):
    return b.execute(f'UPDATE {SEMA}.not_kategorileri SET varsayilan_birim = %s WHERE kod = %s',
                     (varsayilan_birim, kod)).rowcount
