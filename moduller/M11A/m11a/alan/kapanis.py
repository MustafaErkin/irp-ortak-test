"""Kesin kabulde bütçe kapanışı ve kapanış sonrası düzeltme (SPEC › 8.8).

Faz 1'de M7 yok: kesin kabul tarihi muhasebe tarafından elle onaylanır (varsayılan çekirdeğin PROJE'sindeki)."""
from datetime import date

from ..api.hatalar import ModulHatasi, dogrulama
from ..depo import butce as depo, projeler
from . import bildirim, proje as proje_kaydi, serit, yetki
from .butce import KALEMLER, para


def farklar(guncel: dict, o: dict) -> list[dict]:
    """Her kalem: bütçe = güncel; gerçekleşen = tahmini gerçekleşen ya da None; fark = bütçe − gerçekleşen."""
    sonuc = []
    for kalem in KALEMLER:
        butce, gerceklesen = guncel[kalem], o['gerceklesen'][kalem]
        sonuc.append({'kalem': kalem, 'butce': butce, 'gerceklesen': gerceklesen,
                      'fark': None if gerceklesen is None else para(butce - gerceklesen),
                      'kaynak': o['kaynaklar'][kalem]})
    return sonuc


def kapat(i, proje: str, kesin_kabul: date | None) -> dict:
    i.rol_gerek(yetki.KAPANIS, 'Bütçeyi muhasebe ya da yetkili kapatır.')
    p = proje_kaydi.kayit(i, proje)
    if p['butce_durumu'] == 'KAPALI':
        raise ModulHatasi(409, 'BUTCE_KAPALI', 'Bütçe zaten kapalı.')
    if kesin_kabul is None and (cekirdekte := i.proje(proje).get('kesin_kabul_tarihi')):
        kesin_kabul = date.fromisoformat(cekirdekte)
    if kesin_kabul is None:
        raise dogrulama([{'alan': 'kesin_kabul_tarihi', 'sira': None, 'mesaj': 'Kesin kabul tarihi zorunlu.'}])
    o = serit.olc(i, p)                                    # son ölçüm, kullanıcının gözüyle
    if o['hesaplaniyor']:
        raise ModulHatasi(409, 'DURUM', 'Çekirdek hâlâ hesaplıyor; biraz sonra yeniden deneyin.')
    guncel = {s['kalem']: s['guncel'] for s in depo.satirlar(i.b, proje)}
    with i.b.transaction():
        for f in farklar(guncel, o):
            i.b.execute("""INSERT INTO mod_m11a.kapanis_farklari (proje, kalem, butce, gerceklesen, fark, kaynak)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (proje, f['kalem'], f['butce'], f['gerceklesen'], f['fark'], f['kaynak']))
        i.b.execute("""UPDATE mod_m11a.projeler SET butce_durumu = 'KAPALI', kapanis_kesin_kabul = %s,
                         kapanis_ani = %s, kapatan = %s, surum = surum + 1 WHERE proje = %s""",
                    (kesin_kabul, i.simdi(), i.kisi, proje))
    for kural in (bildirim.BUTCE_SAPMASI, bildirim.TUTAR_DEGISTI):
        bildirim.kaldir(i.cekirdek, i.b, proje, kural)     # çekirdeğe ulaşılamazsa kural işi kaldırır
    i.onbellek.pop(('olcum', proje), None)
    i._projeler.pop(proje, None)
    return serit.butce(i, proje)


def duzelt(i, proje: str, g) -> dict:
    """Kilitten sonra gelen fatura: gerekçeli satır; farkı yeniden yazmaz."""
    i.rol_gerek(yetki.KAPANIS, 'Kapanış sonrası düzeltmeyi muhasebe ya da yetkili yapar.')
    p = proje_kaydi.kayit(i, proje)
    if p['butce_durumu'] != 'KAPALI':
        raise ModulHatasi(409, 'DURUM', 'Kapanış sonrası düzeltme yalnızca kapalı bütçede yapılır.')
    hatalar = []
    if not g.gerekce.strip():
        hatalar.append({'alan': 'gerekce', 'sira': None, 'mesaj': 'Gerekçe zorunlu.'})
    belge = projeler.dosya(i.b, g.belge) if g.belge is not None else None
    if g.belge is not None and (not belge or belge['proje'] != proje):
        hatalar.append({'alan': 'belge', 'sira': None, 'mesaj': 'Dosya kaydı bu projede yok.'})
    if hatalar:
        raise dogrulama(hatalar)
    an = i.simdi()
    with i.b.transaction():
        belge_kimligi = (projeler.dosya_ekle(i.b, proje, 'FATURA', g.belge_dosyasi.model_dump(), i.kisi, an)
                         if g.belge_dosyasi else g.belge)
        i.b.execute("""INSERT INTO mod_m11a.kapanis_sonrasi_duzeltmeler (proje, kalem, tutar, gerekce, belge, kim, an)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (proje, g.kalem, para(g.tutar), g.gerekce.strip(), belge_kimligi, i.kisi, an))
    return serit.butce(i, proje)
