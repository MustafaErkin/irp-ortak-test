"""Bütçe satırları, ölçümler, tutar değişiklikleri, kapanış (mod_m11a)."""
from datetime import datetime, timedelta


def satirlar(b, proje: str) -> list[dict]:
    return b.execute("""SELECT kalem, baslangic, guncel FROM mod_m11a.butce_satirlari WHERE proje = %s
                        ORDER BY array_position(ARRAY['MALZEME','ISCILIK','FASON','GENEL_GIDER'], kalem)""",
                     (proje,)).fetchall()


def proje_ucretleri(b, proje: str) -> list[dict]:
    return b.execute('SELECT birim, ucret, para_birimi FROM mod_m11a.proje_saat_ucretleri WHERE proje = %s',
                     (proje,)).fetchall()


def son_olcum(b, proje: str) -> dict | None:
    return b.execute('SELECT * FROM mod_m11a.butce_olcumleri WHERE proje = %s ORDER BY an DESC, kimlik DESC LIMIT 1',
                     (proje,)).fetchone()


def olcum_yaz(b, proje: str, an: str, olcen: str, o: dict) -> bool:
    """Yeni satır yalnızca değerler son ölçümden farklıysa ya da son ölçüm bir saatten eskiyse yazılır."""
    son = son_olcum(b, proje)
    yeni = (o['dolum_yuzde'], o['ilerleme_yuzde'], o['sapma_puan'], list(o['kapsam']), o['esik_puan'],
            o['renk'] == 'KIRMIZI', float(o['bilinmeyen_saat']))
    if son:
        eski = (_f(son['dolum_yuzde']), _f(son['ilerleme_yuzde']), _f(son['sapma_puan']), list(son['kapsam']),
                float(son['esik_puan']), son['uyari'], float(son['bilinmeyen_saat']))
        if eski == yeni and datetime.fromisoformat(an) - son['an'] < timedelta(hours=1):
            return False
    b.execute("""INSERT INTO mod_m11a.butce_olcumleri (proje, an, olcen, dolum_yuzde, ilerleme_yuzde, sapma_puan,
                   kapsam, esik_puan, uyari, bilinmeyen_saat) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
              (proje, an, olcen, *yeni[:3], yeni[3], yeni[4], yeni[5], yeni[6]))
    return True


def _f(x):
    return None if x is None else float(x)


def tutar_degisiklikleri(b, proje: str) -> list[dict]:
    return b.execute('SELECT * FROM mod_m11a.tutar_degisiklikleri WHERE proje = %s ORDER BY kimlik',
                     (proje,)).fetchall()


def kapanis_farklari(b, proje: str) -> list[dict]:
    return b.execute("""SELECT kalem, butce, gerceklesen, fark, kaynak FROM mod_m11a.kapanis_farklari WHERE proje = %s
                        ORDER BY array_position(ARRAY['MALZEME','ISCILIK','FASON','GENEL_GIDER'], kalem)""",
                     (proje,)).fetchall()


def duzeltmeler(b, proje: str) -> list[dict]:
    return b.execute('SELECT * FROM mod_m11a.kapanis_sonrasi_duzeltmeler WHERE proje = %s ORDER BY kimlik',
                     (proje,)).fetchall()
