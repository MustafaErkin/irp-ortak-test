"""Tutar değişikliği: güncel tutar ve güncel bütçe gerekçe ve belgeyle değişir (SPEC › 8.5).

Sözleşme tutarı ve başlangıç bütçesi değişmez (tetikleyici korur)."""
import logging

from psycopg.types.json import Jsonb

from ..api.hatalar import ModulHatasi, dogrulama
from ..baglanti import CekirdekHatasi
from ..depo import butce as depo, projeler
from . import bildirim, proje as proje_kaydi, yetki
from .butce import KALEMLER, metin, para

gunluk = logging.getLogger('m11a.tutar')


def tutar_degisti_metni(p: dict, n: int) -> str:
    return f'{p["proje"]} {p["proje_adi"]} · Güncel tutar ve bütçe değişti (değişiklik #{n})'


def tutar_degisti_birak(cekirdek, b, p: dict, degisiklik: dict) -> bool:
    n = b.execute('SELECT count(*) AS n FROM mod_m11a.tutar_degisiklikleri WHERE proje = %s AND kimlik <= %s',
                  (p['proje'], degisiklik['kimlik'])).fetchone()['n']
    try:
        bildirim.birak(cekirdek, b, p['proje'], bildirim.TUTAR_DEGISTI, [{'tur': 'ROL', 'kimlik': 'MUHASEBE'}],
                       tutar_degisti_metni(p, n), 'BILGI')
    except CekirdekHatasi as h:
        gunluk.warning('%s TUTAR_DEGISTI bırakılamadı: %s', p['proje'], h)
        return False
    b.execute('UPDATE mod_m11a.tutar_degisiklikleri SET bildirim_birakildi = true WHERE kimlik = %s',
              (degisiklik['kimlik'],))
    return True


def degistir(i, proje: str, g) -> dict:
    i.rol_gerek(yetki.TUTAR_DEGISIKLIGI, 'Tutar değişikliğini satış ya da yetkili yapar.')
    p = proje_kaydi.kayit(i, proje)
    if p['butce_durumu'] == 'KAPALI':
        raise ModulHatasi(409, 'BUTCE_KAPALI', 'Bütçe kapalı; tutar değişikliği yapılmaz.')
    hatalar = []
    if not g.gerekce.strip():
        hatalar.append({'alan': 'gerekce', 'sira': None, 'mesaj': 'Gerekçe zorunlu.'})
    if set(g.butce) != set(KALEMLER):
        hatalar.append({'alan': 'butce', 'sira': None, 'mesaj': 'Dört kalemin güncel bütçesi verilmeli.'})
    hatalar += [{'alan': f'butce.{k}', 'sira': None, 'mesaj': 'Bütçe eksi olamaz.'} for k, v in g.butce.items() if v < 0]
    belge = projeler.dosya(i.b, g.belge) if g.belge is not None else None
    if g.belge_dosyasi is None and (not belge or belge['proje'] != proje):
        hatalar.append({'alan': 'belge', 'sira': None, 'mesaj': 'Belge (dosya kaydı) zorunlu.'})
    if hatalar:
        raise dogrulama(hatalar)
    an = i.simdi()
    eski = {s['kalem']: s['guncel'] for s in depo.satirlar(i.b, proje)}
    yeni = {k: para(v) for k, v in g.butce.items()}
    with i.b.transaction():
        belge_kimligi = (projeler.dosya_ekle(i.b, proje, 'TUTAR_DEGISIKLIGI', g.belge_dosyasi.model_dump(), i.kisi, an)
                         if g.belge_dosyasi else g.belge)
        degisiklik = i.b.execute(
            """INSERT INTO mod_m11a.tutar_degisiklikleri (proje, eski_tutar, yeni_tutar, butce_eski, butce_yeni, gerekce,
                 belge, kim, an) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING kimlik""",
            (proje, p['guncel_tutar'], para(g.yeni_tutar), Jsonb({k: metin(v) for k, v in eski.items()}),
             Jsonb({k: metin(v) for k, v in yeni.items()}), g.gerekce.strip(), belge_kimligi, i.kisi, an)).fetchone()
        i.b.execute('UPDATE mod_m11a.projeler SET guncel_tutar = %s, surum = surum + 1 WHERE proje = %s',
                    (para(g.yeni_tutar), proje))
        for kalem, tutar in yeni.items():
            i.b.execute('UPDATE mod_m11a.butce_satirlari SET guncel = %s WHERE proje = %s AND kalem = %s',
                        (tutar, proje, kalem))
    if i.proje(proje).get('aktif', True):
        tutar_degisti_birak(i.cekirdek, i.b, p, degisiklik)
    from . import serit
    return serit.butce(i, proje)
