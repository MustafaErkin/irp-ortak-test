"""Projenin M1.1A kaydı ve donmuş çocukları (mod_m11a.projeler ve bağlı tablolar)."""
from psycopg.types.json import Jsonb

COCUKLAR = ('acik_bildirimler', 'butce_olcumleri', 'kapanis_farklari', 'kapanis_sonrasi_duzeltmeler',
            'tutar_degisiklikleri', 'eksik_bilgiler', 'devirler', 'teminatlar', 'odeme_satirlari', 'ticari_kosullar',
            'baslangic_plani', 'proje_saat_ucretleri', 'butce_satirlari')


def getir(b, proje: str) -> dict | None:
    return b.execute('SELECT * FROM mod_m11a.projeler WHERE proje = %s', (proje,)).fetchone()


def surumden(b, teklif_surumu: int) -> dict | None:
    return b.execute('SELECT * FROM mod_m11a.projeler WHERE teklif_surumu = %s', (teklif_surumu,)).fetchone()


def kod_var_mi(b, kod: str) -> bool:
    return b.execute('SELECT 1 FROM mod_m11a.projeler WHERE proje = %s', (kod,)).fetchone() is not None


def acik_projeler(b) -> list[dict]:
    return b.execute("SELECT * FROM mod_m11a.projeler WHERE durum = 'ACIK' ORDER BY proje").fetchall()


def sayac_degeri(b, ad: str, donem: str) -> int:
    r = b.execute('SELECT son FROM mod_m11a.sayaclar WHERE ad = %s AND donem = %s', (ad, donem)).fetchone()
    return r['son'] if r else 0


def sayac_ilerlet(b, ad: str, donem: str) -> int:
    return b.execute('SELECT mod_m11a.sayac_ilerlet(%s, %s) AS n', (ad, donem)).fetchone()['n']


def sayac_geri_al(b, ad: str, donem: str, n: int) -> None:
    """Açılış geri alınınca sıra, başkası ilerletmediyse geri verilir (sırada boşluk kalmasın)."""
    b.execute('UPDATE mod_m11a.sayaclar SET son = son - 1 WHERE ad = %s AND donem = %s AND son = %s', (ad, donem, n))


def dosya_ekle(b, proje: str, tur: str, dosya: dict, kim: str, an: str) -> int:
    return b.execute("""INSERT INTO mod_m11a.dosya_kayitlari (proje, tur, ad, konum, aciklama, parmak_izi, ekleyen,
                          ekleme_ani) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING kimlik""",
                     (proje, tur, dosya['ad'], dosya['konum'], dosya.get('aciklama'), dosya.get('parmak_izi'), kim,
                      an)).fetchone()['kimlik']


def dosya(b, kimlik: int | None) -> dict | None:
    if kimlik is None:
        return None
    return b.execute('SELECT kimlik, proje, tur, ad, konum, aciklama, parmak_izi, ekleyen, ekleme_ani '
                     'FROM mod_m11a.dosya_kayitlari WHERE kimlik = %s', (kimlik,)).fetchone()


def dosyalar(b,proje):
    return b.execute('SELECT kimlik,proje,tur,ad,konum,aciklama,parmak_izi,ekleyen,ekleme_ani '
                     'FROM mod_m11a.dosya_kayitlari WHERE proje=%s ORDER BY ekleme_ani DESC',(proje,)).fetchall()


def ac(b, p: dict, butce: dict, ucretler: list[dict], plan: list[dict]) -> None:
    """Niyet: proje ACILIYOR durumunda, donmuş kopyası ve çocuklarıyla (çağıran tek işlemde tutar)."""
    alanlar = ('proje', 'durum', 'teklif_surumu', 'teklif_etiketi', 'talep_no', 'm10_musteri', 'musteri_adi',
               'proje_adi', 'kaynak', 'ana_proje', 'sorumlu', 'satis_yoneticisi', 'siparis_tarihi', 'teslim_tarihi',
               'kesin_kabul_tarihi', 'yil', 'yillik_sira', 'po_no', 'para_birimi', 'sozlesme_tutari', 'guncel_tutar',
               'kurlar', 'teslim_suresi_hafta', 'donmus_teklif', 'pdf', 'pdf_ad', 'pdf_parmak_izi', 'acan',
               'acilis_ani')
    degerler = [Jsonb(p[a]) if a in ('kurlar', 'donmus_teklif') else p[a] for a in alanlar]
    b.execute(f"INSERT INTO mod_m11a.projeler ({', '.join(alanlar)}) VALUES ({', '.join(['%s'] * len(alanlar))})",
              degerler)
    for kalem, tutar in butce.items():
        b.execute('INSERT INTO mod_m11a.butce_satirlari (proje, kalem, baslangic, guncel) VALUES (%s, %s, %s, %s)',
                  (p['proje'], kalem, tutar, tutar))
    for u in ucretler:
        b.execute('INSERT INTO mod_m11a.proje_saat_ucretleri (proje, birim, ucret, para_birimi) VALUES (%s, %s, %s, %s)',
                  (p['proje'], u['birim'], u['ucret'], u['para_birimi']))
    for s in plan:
        b.execute("""INSERT INTO mod_m11a.baslangic_plani (proje, sira, etap_kodu, ad, paralel_grup, baslangic_hafta,
                       sure_hafta, baslangic, bitis) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                  (p['proje'], s['sira'], s['etap_kodu'], s['ad'], s['paralel_grup'], s['baslangic_hafta'],
                   s['sure_hafta'], s['baslangic'], s['bitis']))
    b.execute('INSERT INTO mod_m11a.ticari_kosullar (proje) VALUES (%s)', (p['proje'],))


def dosyalari_bagla(b, proje: str, po_dosyasi: int | None, sozlesme_dosyasi: int | None) -> None:
    b.execute('UPDATE mod_m11a.projeler SET po_dosyasi = %s, sozlesme_dosyasi = %s WHERE proje = %s',
              (po_dosyasi, sozlesme_dosyasi, proje))


def acildi(b, proje: str, acilis_olayi: str | None) -> None:
    b.execute("UPDATE mod_m11a.projeler SET durum = 'ACIK', acilis_olayi = %s, surum = surum + 1 WHERE proje = %s",
              (acilis_olayi, proje))


def sil(b, proje: str) -> None:
    """Açılış geri alınınca satır ve çocukları (yalnızca ACILIYOR kayıt)."""
    for t in COCUKLAR:
        b.execute(f'DELETE FROM mod_m11a.{t} WHERE proje = %s', (proje,))
    b.execute('UPDATE mod_m11a.projeler SET po_dosyasi = NULL, sozlesme_dosyasi = NULL WHERE proje = %s', (proje,))
    b.execute('DELETE FROM mod_m11a.dosya_kayitlari WHERE proje = %s', (proje,))
    b.execute("DELETE FROM mod_m11a.projeler WHERE proje = %s AND durum = 'ACILIYOR'", (proje,))


def baslangic_plani(b, proje: str) -> list[dict]:
    return b.execute('SELECT sira, etap_kodu, ad, paralel_grup, baslangic_hafta, sure_hafta, baslangic, bitis '
                     'FROM mod_m11a.baslangic_plani WHERE proje = %s ORDER BY sira', (proje,)).fetchall()
