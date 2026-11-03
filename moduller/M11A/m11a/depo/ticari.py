"""Ticari devir formu, muhasebeye devir ve eksik bilgi (mod_m11a.ticari_kosullar, odeme_satirlari, teminatlar,
devirler, eksik_bilgiler)."""
from psycopg.types.json import Jsonb

FORM_ALANLARI = ('faturalama_bicimi', 'faturalama_notu', 'teslim_sekli', 'ihracat', 'tesvik', 'tesvik_belge_no',
                 'teminat_gerekli', 'notlar')


def kosullar(b, proje: str) -> dict:
    return b.execute('SELECT * FROM mod_m11a.ticari_kosullar WHERE proje = %s', (proje,)).fetchone()


def odemeler(b, proje: str) -> list[dict]:
    return b.execute('SELECT * FROM mod_m11a.odeme_satirlari WHERE proje = %s ORDER BY sira', (proje,)).fetchall()


def teminatlar(b, proje: str) -> list[dict]:
    return b.execute('SELECT * FROM mod_m11a.teminatlar WHERE proje = %s ORDER BY kimlik', (proje,)).fetchall()


def form_yaz(b, proje: str, surum: int, form: dict, odemeler_: list[dict], teminatlar_: list[dict], kim: str,
             an: str) -> bool:
    """Eşzamanlılık: surum tutmuyorsa False (çağıran 409 DEGISTI döner)."""
    r = b.execute(f"""UPDATE mod_m11a.ticari_kosullar SET {', '.join(f'{a} = %s' for a in FORM_ALANLARI)},
                        guncelleyen = %s, guncelleme_ani = %s, surum = surum + 1
                      WHERE proje = %s AND surum = %s""",
                  [form.get(a) for a in FORM_ALANLARI] + [kim, an, proje, surum])
    if r.rowcount != 1:
        return False
    b.execute('DELETE FROM mod_m11a.odeme_satirlari WHERE proje = %s', (proje,))
    for n, o in enumerate(odemeler_, 1):
        b.execute("""INSERT INTO mod_m11a.odeme_satirlari (proje, sira, kosul, tarih, tutar, para_birimi, aciklama)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                  (proje, n, o['kosul'], o.get('tarih'), o['tutar'], o['para_birimi'], o.get('aciklama')))
    b.execute('DELETE FROM mod_m11a.teminatlar WHERE proje = %s', (proje,))
    for t in teminatlar_:
        b.execute("""INSERT INTO mod_m11a.teminatlar (proje, tur, tutar, para_birimi, banka, bitis_tarihi, dosya, aciklama)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                  (proje, t['tur'], t['tutar'], t['para_birimi'], t.get('banka'), t.get('bitis_tarihi'), t.get('dosya'),
                   t.get('aciklama')))
    return True


def siparis_yaz(b, proje: str, po_no, po_dosyasi, sozlesme_dosyasi) -> None:
    b.execute("""UPDATE mod_m11a.projeler SET po_no = %s, po_dosyasi = %s, sozlesme_dosyasi = %s, surum = surum + 1
                 WHERE proje = %s""", (po_no, po_dosyasi, sozlesme_dosyasi, proje))


def vega_yaz(b, proje: str, cari, proje_kodu) -> None:
    b.execute('UPDATE mod_m11a.projeler SET vega_cari_kodu = %s, vega_proje_kodu = %s, surum = surum + 1 '
              'WHERE proje = %s', (cari, proje_kodu, proje))


def vega_cari_onerisi(b, proje: str, m10_musteri) -> str | None:
    """Aynı M1.0 müşterisinin önceki projesinde cari kodu varsa öneri olarak gelir."""
    if m10_musteri is None:
        return None
    r = b.execute("""SELECT vega_cari_kodu FROM mod_m11a.projeler WHERE m10_musteri = %s AND proje <> %s
                       AND vega_cari_kodu IS NOT NULL AND btrim(vega_cari_kodu) <> '' ORDER BY acilis_ani DESC LIMIT 1""",
                  (m10_musteri, proje)).fetchone()
    return r['vega_cari_kodu'] if r else None


# ---- devir
def devir(b, proje: str) -> dict | None:
    return b.execute('SELECT * FROM mod_m11a.devirler WHERE proje = %s', (proje,)).fetchone()


def devirler(b) -> list[dict]:
    return b.execute("""SELECT d.* FROM mod_m11a.devirler d JOIN mod_m11a.projeler p USING (proje)
                        WHERE p.durum = 'ACIK' ORDER BY d.devir_ani""").fetchall()


def devir_ac(b, proje: str, kim: str, an: str) -> None:
    b.execute("INSERT INTO mod_m11a.devirler (proje, durum, devreden, devir_ani) VALUES (%s, 'DEVREDILDI', %s, %s)",
              (proje, kim, an))


def devir_durumu_yaz(b, proje: str, durum: str, **alanlar) -> None:
    ek = ''.join(f', {a} = %s' for a in alanlar)
    b.execute(f'UPDATE mod_m11a.devirler SET durum = %s{ek} WHERE proje = %s', [durum, *alanlar.values(), proje])


def devir_bildirimi_yaz(b, proje: str, birakildi: bool, alicilar=None, suzulenler=None) -> None:
    if alicilar is None:
        b.execute('UPDATE mod_m11a.devirler SET bildirim_birakildi = %s WHERE proje = %s', (birakildi, proje))
        return
    b.execute("""UPDATE mod_m11a.devirler SET bildirim_birakildi = %s, son_alicilar = %s, son_suzulenler = %s
                 WHERE proje = %s""", (birakildi, Jsonb(alicilar), Jsonb(suzulenler), proje))


# ---- eksik bilgi
def eksikler(b, proje: str) -> list[dict]:
    return b.execute('SELECT * FROM mod_m11a.eksik_bilgiler WHERE proje = %s ORDER BY kimlik', (proje,)).fetchall()


def eksik(b, proje: str, kimlik: int) -> dict | None:
    return b.execute('SELECT * FROM mod_m11a.eksik_bilgiler WHERE proje = %s AND kimlik = %s',
                     (proje, kimlik)).fetchone()


def eksik_ac(b, proje: str, alan: str | None, ne: str, kim: str, an: str, aciklama: str | None = None) -> int:
    return b.execute("""INSERT INTO mod_m11a.eksik_bilgiler (proje, alan, ne, aciklama, olusturan, olusturma_ani)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING kimlik""",
                     (proje, alan, ne, aciklama, kim, an)).fetchone()['kimlik']


def eksik_durumu(b, kimlik: int, durum: str, kim: str, an: str, kimden=None, aciklama=None) -> None:
    b.execute("""UPDATE mod_m11a.eksik_bilgiler SET durum = %s, kimden = COALESCE(%s, kimden),
                   aciklama = COALESCE(%s, aciklama), guncelleyen = %s, guncelleme_ani = %s WHERE kimlik = %s""",
              (durum, kimden, aciklama, kim, an, kimlik))
