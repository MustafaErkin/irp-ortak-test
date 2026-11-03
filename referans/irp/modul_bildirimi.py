"""Olay olmayan, kilit altında çalışan kalıcı modül bildirim kapısı."""
from copy import copy, deepcopy
from urllib.parse import quote
from .saat import an, Saat
from .kurallar_v10_1 import dolu


def kimlik(modul, kural, kayit, alici):
    # Tür anahtara dahildir; '/' ve '%' çakışma yaratamaz.
    return '/'.join(quote(x, safe='') for x in (modul, kural, kayit['tur'] + ':' + kayit['kimlik'], alici))


def alici_gorebilir(d, kisi, kayit):
    from .yetki_v6 import istihdamda, simdi
    from .gorunum_v9 import bagli_projeler, proje_gorebilir_mi
    if not istihdamda(d, kisi, simdi(d)) or d.kisiler.get(kisi, {}).get('aktif') is False: return False
    # Motor bildirimi hesaplanırken alıcı olay anındaki durumla süzülür.
    z = copy(d); z.saat = Saat(simdi(d))
    return all(proje_gorebilir_mi(z, kisi, p) for p in bagli_projeler(d, kayit['tur'], kayit['kimlik']))


def kapilar(d, servis, modul, kural, kayit, zaman, birak):
    if getattr(d.gorunum, 'hesap_ani', None) != d.saat.simdi(): d.yeniden_kur()
    m = d.moduller.get(modul, {}) if isinstance(modul, str) else {}
    if not m or m['servis_kimligi'] != servis or (birak and not m['aktif']):
        return d.red('YETKI', 'Modul servis kimligi veya etkinligi')
    if not dolu(kural) or not isinstance(kayit, dict) or kayit.get('tur') not in ('PROJE', 'IS', 'GOREV', 'NESNE') or not dolu(kayit.get('kimlik')):
        return d.red('BICIM', 'Modul bildirim kaydi')
    if kayit.get('modul_kaydi') is not None and not isinstance(kayit['modul_kaydi'], str): return d.red('BICIM', 'Modul kaydi metin')
    try: t = an(zaman)
    except (ValueError, TypeError, AttributeError): return d.red('BICIM', 'Bildirim ani')
    if t > d.saat.simdi(): return d.red('BICIM', 'Bildirim ani gelecekte olamaz')
    from .kabul import nesne
    if not nesne(d, kayit['tur'], kayit['kimlik']): return d.red('DURUM', 'Bildirim kaydi yok')
    return None


def alicilari_coz(d, alicilar):
    from .yetki_v6 import yoneticiler
    from .kurallar_v10 import projede_yetkili
    if not isinstance(alicilar, list) or not alicilar: raise ValueError('Alici tanimi gerekli')
    sonuc = set()
    for a in alicilar:
        if not isinstance(a, dict) or not dolu(a.get('kimlik')): raise ValueError('Alici bicimi')
        tur, key = a.get('tur'), a['kimlik']
        if tur == 'KISI': sonuc.add(key)
        elif tur == 'BIRIM_YONETICILERI': sonuc.update(yoneticiler(d, key))
        elif tur == 'ROL': sonuc.update(k for k, p in d.kisiler.items() if key in p.get('roller', []))
        elif tur == 'PROJEDE_YETKILILER': sonuc.update(k for k in d.kisiler if projede_yetkili(d, k, key))
        elif tur == 'NESNE_SORUMLUSU': sonuc.add(d.nesneler.get(key, {}).get('sorumlu'))
        else: raise ValueError('Alici turu')
    return sonuc - {None}


def birak(d, servis_kimligi, modul, kural, kayit, alicilar, metin, onem, zaman):
    with d._kilit:
        hata = kapilar(d, servis_kimligi, modul, kural, kayit, zaman, True)
        if hata: return hata
        if not dolu(metin) or onem not in ('BILGI', 'UYARI'): return d.red('BICIM', 'Bildirim metni veya onemi')
        try: adaylar = alicilari_coz(d, alicilar)
        except ValueError as h: return d.red('BICIM', str(h))
        ks = sorted(k for k in adaylar if alici_gorebilir(d, k, kayit))
        from .saat import gun
        suzulenler = []
        for k in sorted(adaylar - set(ks)):
            p = d.kisiler.get(k, {})
            ayrildi = p.get('aktif') is False or (p.get('ayrilis_tarihi') and gun(p['ayrilis_tarihi']) < d.saat.simdi().date())
            from .yetki_v6 import istihdamda
            neden = 'AYRILDI' if ayrildi else 'ISTIHDAM_DISI' if not istihdamda(d, k, d.saat.simdi()) else 'PROJEYI_GOREMEZ'
            suzulenler.append(dict(kisi=k, neden=neden))
        if not ks: return dict(sonuc='BASARILI', alici_kalmadi=True, alicilar=[], yeni=0, guncellenen=0, suzulenler=suzulenler)
        yeni = 0; simdi = d.saat.simdi()
        for k in ks:
            key = kimlik(modul, kural, kayit, k)
            x = d.modul_bildirimleri.get(key)
            if x is None:
                yeni += 1
                x = d.modul_bildirimleri[key] = dict(kimlik=key, kaynak=modul, kural=kural, kayit=deepcopy(kayit),
                    alici=k, an=an(zaman), birakma_ani=simdi, gorulme_ani=None, gecerli=False, etkinlik_araliklari=[])
            if not x['gecerli']: x['etkinlik_araliklari'].append(dict(bas=simdi, bit=None))
            x.update(metin=metin, onem=onem, gecerli=True, guncelleme_ani=simdi, son_kaynak_ani=an(zaman),
                alici_tanimlari=deepcopy(alicilar), cozulmus_alicilar=ks[:], kayit=deepcopy(kayit))
        return dict(sonuc='BASARILI', alici_kalmadi=False, alicilar=ks, yeni=yeni, guncellenen=len(ks)-yeni, suzulenler=suzulenler)


def kaldir(d, servis_kimligi, modul, kural, kayit, zaman):
    with d._kilit:
        hata = kapilar(d, servis_kimligi, modul, kural, kayit, zaman, False)
        if hata: return hata
        sayi = 0
        for x in d.modul_bildirimleri.values():
            if (x['kaynak'], x['kural'], x['kayit']['tur'], x['kayit']['kimlik']) != (modul, kural, kayit['tur'], kayit['kimlik']): continue
            if x['gecerli']:
                sayi += 1; x['etkinlik_araliklari'][-1]['bit'] = d.saat.simdi()
                x.update(gecerli=False, kaldirma_ani=d.saat.simdi(), son_kaynak_ani=an(zaman))
        return dict(sonuc='BASARILI', kaldirilan=sayi)


def gorulmeleri_yansit(d):
    # Görülme, insan olayıdır. Kapı tablosu ve önceki görülme hiçbir zaman sıfırlanmaz.
    for e in sorted(d.bildirim_gorulmeleri.values(), key=lambda x: x['an']):
        for key in e['bildirimler']:
            x = d.modul_bildirimleri.get(key)
            if not x or e['kim'] != x['alici']: continue
            if not any(a['bas'] <= e['an'] and (a['bit'] is None or e['an'] <= a['bit']) for a in x['etkinlik_araliklari']): continue
            if x['gorulme_ani'] is None or e['an'] < x['gorulme_ani']: x['gorulme_ani'] = e['an']


def kutu(d, kisi):
    sonuc = [deepcopy(x) for x in d.bildirimler.values() if x['alici'] == kisi and x['gecerli']]
    sonuc.extend(deepcopy(x) for x in d.modul_bildirimleri.values() if x['alici'] == kisi and x['gecerli'] and alici_gorebilir(d, kisi, x['kayit']))
    return sonuc
