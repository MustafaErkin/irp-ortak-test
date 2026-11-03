"""Muhasebeye devir (SPEC › 8.4): durum geçişleri (saf) ve devrin akışı.

DEVREDILDI → (devri aldım) MUHASEBE_GORDU | EKSIK_VAR → (devri tamamla) TAMAM. TAMAM geri alınmaz."""
from ..api.hatalar import ModulHatasi, dogrulama
from ..depo import projeler, ticari as depo
from . import bildirim, eksik, proje as proje_kaydi, yetki


def durum(mevcut: str, acik_eksik: int) -> str:
    """Her değişiklikte yeniden hesaplanır; devir alınmadıysa ya da TAMAM'sa değişmez."""
    if mevcut in ('DEVREDILDI', 'TAMAM'):
        return mevcut
    return 'EKSIK_VAR' if acik_eksik else 'MUHASEBE_GORDU'


def aldim(mevcut: str, acik_eksik: int) -> str:
    if mevcut == 'TAMAM':
        return mevcut
    return 'EKSIK_VAR' if acik_eksik else 'MUHASEBE_GORDU'


def tamamlama_engeli(mevcut: str, acik_eksik: int, vega_cari_kodu, vega_proje_kodu) -> str | None:
    if mevcut == 'TAMAM':
        return 'Devir zaten tamam.'
    if acik_eksik:
        return 'Açık eksik var.'
    if not (vega_cari_kodu or '').strip() or not (vega_proje_kodu or '').strip():
        return 'VEGA kodları boş.'
    return None


# ------------------------------------------------------------------ akış (veritabanı ve bildirim)

def durumu_yenile(b, proje: str) -> None:
    d = depo.devir(b, proje)
    if d:
        yeni = durum(d['durum'], eksik.acik_sayisi(depo.eksikler(b, proje)))
        if yeni != d['durum']:
            depo.devir_durumu_yaz(b, proje, yeni)


def eksikleri_esitle(i, p: dict) -> None:
    """Devirden sonra her kayıtta eksik satırları yeniden hesaplanır; devirden önce satır açılmaz."""
    proje = p['proje']
    if not depo.devir(i.b, proje):
        return
    eksikler = eksik.eksik_alanlar(p['po_no'], p['sozlesme_dosyasi'], depo.kosullar(i.b, proje),
                                   len(depo.odemeler(i.b, proje)), len(depo.teminatlar(i.b, proje)))
    acilacak, degisen = eksik.esitle(depo.eksikler(i.b, proje), eksikler)
    an = i.simdi()
    for alan in acilacak:
        depo.eksik_ac(i.b, proje, alan, eksik.ALANLAR[alan], i.kisi, an)
    for kimlik, yeni in degisen:
        depo.eksik_durumu(i.b, kimlik, yeni, i.kisi, an)
    durumu_yenile(i.b, proje)


def ozet(i, proje: str) -> dict:
    from .ticari import devir_ozeti, eksik_satiri
    d = depo.devir(i.b, proje)
    satirlar = depo.eksikler(i.b, proje)
    return i.cevap({'proje': proje, 'devir': devir_ozeti(d), 'acik_eksik': eksik.acik_sayisi(satirlar),
                    'eksik_bilgiler': [eksik_satiri(e) for e in satirlar],
                    'uyari': bildirim.suzulen_uyarisi(d['son_alicilar'], d['son_suzulenler']) if d else None})


def devret(i, proje: str) -> dict:
    i.rol_gerek(yetki.DEVRETME, 'Muhasebeye devri satış ya da yetkili yapar.')
    p = proje_kaydi.kayit(i, proje)
    if depo.devir(i.b, proje):
        raise ModulHatasi(409, 'DURUM', 'Proje zaten muhasebeye devredildi.')
    with i.b.transaction():
        depo.devir_ac(i.b, proje, i.kisi, i.simdi())
        eksikleri_esitle(i, p)
    bildirim.ticari_devir_birak(i.cekirdek, i.b, p, eksik.acik_sayisi(depo.eksikler(i.b, proje)))
    return ozet(i, proje)


def _devir_gerek(i, proje: str) -> dict:
    i.rol_gerek(yetki.MUHASEBE_ISI)
    proje_kaydi.kayit(i, proje)
    d = depo.devir(i.b, proje)
    if not d:
        raise ModulHatasi(409, 'DURUM', 'Proje muhasebeye devredilmedi.')
    return d


def devri_aldim(i, proje: str) -> dict:
    d = _devir_gerek(i, proje)
    yeni = aldim(d['durum'], eksik.acik_sayisi(depo.eksikler(i.b, proje)))
    if d['durum'] == 'DEVREDILDI':
        depo.devir_durumu_yaz(i.b, proje, yeni, goren=i.kisi, gorme_ani=i.simdi())
    elif yeni != d['durum']:
        depo.devir_durumu_yaz(i.b, proje, yeni)
    return ozet(i, proje)


def devri_tamamla(i, proje: str) -> dict:
    d = _devir_gerek(i, proje)
    p = projeler.getir(i.b, proje)
    engel = tamamlama_engeli(d['durum'], eksik.acik_sayisi(depo.eksikler(i.b, proje)), p['vega_cari_kodu'],
                             p['vega_proje_kodu'])
    if engel:
        raise ModulHatasi(409, 'DURUM', engel)
    an = i.simdi()
    ek = {'goren': i.kisi, 'gorme_ani': an} if d['durum'] == 'DEVREDILDI' else {}
    depo.devir_durumu_yaz(i.b, proje, 'TAMAM', tamamlayan=i.kisi, tamamlanma_ani=an, **ek)
    bildirim.kaldir(i.cekirdek, i.b, proje, bildirim.TICARI_DEVIR)
    return ozet(i, proje)


def eksik_ekle(i, proje: str, ne: str, aciklama: str | None) -> dict:
    _devir_gerek(i, proje)
    if not (ne or '').strip():
        raise dogrulama([{'alan': 'ne', 'sira': None, 'mesaj': 'Ne eksik, yazılmalı.'}])
    depo.eksik_ac(i.b, proje, None, ne.strip(), i.kisi, i.simdi(), aciklama)
    durumu_yenile(i.b, proje)
    return ozet(i, proje)


def eksik_guncelle(i, proje: str, kimlik: int, yeni: str, kimden: str | None, aciklama: str | None) -> dict:
    _devir_gerek(i, proje)
    satir = depo.eksik(i.b, proje, kimlik)
    if not satir:
        raise ModulHatasi(404, 'BULUNAMADI', 'Eksik satırı yok.')
    hata = eksik.gecis_hatasi(satir, yeni, kimden)
    if hata and yeni == 'ISTENDI' and satir['durum'] == 'EKSIK':
        raise dogrulama([{'alan': 'kimden', 'sira': None, 'mesaj': hata}])
    if hata:
        raise ModulHatasi(409, 'DURUM', hata)
    depo.eksik_durumu(i.b, kimlik, yeni, i.kisi, i.simdi(), kimden, aciklama)
    durumu_yenile(i.b, proje)
    return ozet(i, proje)


# ------------------------------------------------------------------ muhasebe gelen kutusu

SIRA = {'DEVREDILDI': 0, 'EKSIK_VAR': 1}


def yaklasan_tarihler(b, proje: str, bugun, gun: int) -> list[dict]:
    """Koşulu TARIH olan ödeme satırları ve teminat bitişleri, bugünden ±gun içinde; en yakın üçü.
    Geçmiş tarih ayrıca işaretlenir (ekranda kırmızı ▲)."""
    from datetime import timedelta
    from .butce import metin
    bas, bit = bugun - timedelta(days=gun), bugun + timedelta(days=gun)
    tarihler = [{'tur': 'ODEME', 'tarih': o['tarih'], 'tutar': metin(o['tutar']), 'para_birimi': o['para_birimi'],
                 'aciklama': o['aciklama']} for o in depo.odemeler(b, proje)
                if o['kosul'] == 'TARIH' and o['tarih'] and bas <= o['tarih'] <= bit]
    tarihler += [{'tur': 'TEMINAT', 'tarih': t['bitis_tarihi'], 'tutar': metin(t['tutar']),
                  'para_birimi': t['para_birimi'], 'aciklama': t['banka']} for t in depo.teminatlar(b, proje)
                 if t['bitis_tarihi'] and bas <= t['bitis_tarihi'] <= bit]
    tarihler.sort(key=lambda x: abs((x['tarih'] - bugun).days))
    return [dict(x, tarih=x['tarih'].isoformat(), gecmis=x['tarih'] < bugun) for x in tarihler[:3]]


def gelen_kutusu(i) -> dict:
    from datetime import date
    from ..depo import ayarlar
    from .donusturme import siparis_adi
    i.rol_gerek(yetki.GELEN_KUTUSU)
    a = ayarlar.oku(i.b)
    bugun = date.fromisoformat(i.simdi()[:10])
    satirlar = []
    for d in depo.devirler(i.b):
        if not i.proje_gorur_mu(d['proje']):
            continue                  # kullanıcının PROJE okumasıyla görmediği satır listelenmez
        p = projeler.getir(i.b, d['proje'])
        eksikler = [e for e in depo.eksikler(i.b, d['proje']) if e['durum'] in eksik.ACIK_DURUMLAR]
        tarihler = yaklasan_tarihler(i.b, d['proje'], bugun, int(a['yaklasan_tarih_gun']))
        satirlar.append({
            'proje': p['proje'], 'siparis_adi': siparis_adi(a, p), 'musteri': p['musteri_adi'],
            'devir_durumu': d['durum'], 'devir_ani': d['devir_ani'].isoformat(), 'po_bekleniyor': p['po_no'] is None,
            'eksik_sayisi': len(eksikler),
            'eksikler': [{'kimlik': e['kimlik'], 'alan': e['alan'], 'ne': e['ne'], 'durum': e['durum'],
                          'kimden': e['kimden']} for e in eksikler],
            'vega_cari_kodu': p['vega_cari_kodu'], 'vega_proje_kodu': p['vega_proje_kodu'],
            'yaklasan_tarihler': tarihler})
    satirlar.sort(key=lambda s: (SIRA.get(s['devir_durumu'], 2),
                                 min((abs((date.fromisoformat(t['tarih']) - bugun).days)
                                      for t in s['yaklasan_tarihler']), default=10 ** 6)))
    return i.cevap({'satirlar': satirlar, 'yaklasan_tarih_gun': int(a['yaklasan_tarih_gun'])})
