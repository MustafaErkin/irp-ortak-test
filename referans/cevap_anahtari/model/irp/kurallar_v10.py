"""T9 sürüm 2: proje kararları ile kişisel tanıklık ayrı kapılardır."""
from datetime import timedelta
from decimal import Decimal
from .saat import an
from .yetki_v6 import ustler, yoneticiler, birim_ustleri, istihdamda, simdi


def genel_yonetim(d, kim):
    return (istihdamda(d, kim, simdi(d)) and
            ('YETKILI' in d.kisiler.get(kim, {}).get('roller', []) or
             any(kim in yoneticiler(d, b) for b, x in d.birimler.items()
                 if not x.get('ust_birim'))))


def projede_yetkili(d, kim, proje, t=None):
    if t is not None:
        from .gorunum_v7 import durum
        return projede_yetkili(durum(d, t), kim, proje)
    if proje not in d.projeler or not istihdamda(d, kim, simdi(d)):
        return False
    if genel_yonetim(d, kim): return True
    sorumlu = d.projeler[proje].get('sorumlu')
    if sorumlu and (kim == sorumlu or kim in ustler(d, sorumlu)): return True
    for etap in d.etaplar.values():
        if etap['proje'] != proje: continue
        b = etap['birim']
        s = etap.get('sorumlu') or d.birimler.get(b, {}).get('basi')
        if kim in yoneticiler(d, b) | birim_ustleri(d, b): return True
        if s and (kim == s or kim in ustler(d, s)): return True
    return False


def ek_erisim(d, kim, proje):
    ss = [x for x in d.proje_erisimleri.values()
          if x['proje'] == proje and x['kisi'] == kim and x['an'] <= simdi(d)]
    return bool(ss) and max(ss, key=lambda x: (x['an'], x['kimlik']))['acik']


def birim_dahil(d, birim, proje):
    # Tarihler plan aralığıdır. Etabın bitişi üyeliği veya açık işi kapatmaz.
    return any(x['proje'] == proje and x['birim'] == birim for x in d.etaplar.values())


def kisi_dahil(d, kim, proje):
    return birim_dahil(d, d.kisiler.get(kim, {}).get('birim'), proje) or ek_erisim(d, kim, proje)


def olay_projeleri(d, e):
    """Eski ve yeni bağlar birlikte; toplu hedefte tek izin diğerini açmaz.

    Sorumluluk olayları kişisel paya bağlıdır: kendi sabit ilişkileri denetlenir.
    Bunlar projeyi yönetme/okuma hakkı kazandırmaz (karar 92, yorum B49).
    """
    from .gorunum_v9 import bagli_projeler
    kod, g = e['eylem_kodu'], e['girdiler']
    sonuc = set()
    if kod == 'PROJE.ACTIM': return sonuc
    if kod == 'PLAN.TARIHLEDIM':
        for h in g['hedefler']: sonuc.update(bagli_projeler(d, h['tur'], h['kimlik']))
    for h in e['neyin_ustunde']:
        sonuc.update(bagli_projeler(d, h['tur'], h['kimlik']))
    for s in g.get('gorevler', g.get('isler', [g])):
        if s.get('proje'): sonuc.add(s['proje'])
    if g.get('degisenler', {}).get('proje'): sonuc.add(g['degisenler']['proje'])
    for s in (g, g.get('degisenler', {})):
        sonuc.update(x['kimlik'] for x in s.get('baglar', []) if x['tur'] == 'PROJE')
    if kod.startswith('NESNE.') and g.get('hedef'):
        sonuc.update(bagli_projeler(d, 'NESNE', g['hedef']))
    if kod == 'GECIKME.DEGERLENDIRDIM':
        from .kurallar_v9 import gecikme_hedefi
        p = gecikme_hedefi(d, g['hedef']).get('proje')
        if p: sonuc.add(p)
    return sonuc


def proje_yazma_kapisi(d, e):
    from .kabul import TANIKLIK
    from .gorunum_v9 import proje_gorebilir_mi
    kod, g, kim = e['eylem_kodu'], e['girdiler'], e['kim']
    if kod == 'NOT.YAZDIM':
        from .gorunum_v9 import gorebilir_mi
        if any(h['tur']=='NESNE' and (h['kimlik'] not in d.nesneler or not gorebilir_mi(d,kim,'NESNE',h['kimlik'])) for h in e['neyin_ustunde']): return False
    if d.ayar('proje_gorunurlugu', an(e.get('oldugu_an') or simdi(d)), 'HERKES') != 'UYELER': return True
    ps = olay_projeleri(d, e)
    if kod == 'NOT.YAZDIM': return all(proje_gorebilir_mi(d, kim, p) for p in ps)
    if kod in TANIKLIK: return True
    if kod == 'NESNE.ASAMA_GECIRDIM':
        x = d.nesneler.get(g['hedef'], {})
        if kim == x.get('sorumlu'):
            return all(proje_gorebilir_mi(d, kim, p) if p == x.get('proje')
                       else projede_yetkili(d, kim, p) for p in ps)
    if not all(projede_yetkili(d, kim, p) for p in ps): return False
    if kod in ('GOREV.ATADIM', 'IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM'):
        for s in g.get('gorevler', g.get('isler', [g])):
            p = s.get('proje')
            if not p: continue
            if kod.startswith('IS.'):
                b = s.get('birim') or d.kisiler.get(kim, {}).get('birim')
                if not birim_dahil(d, b, p): return False
            if s.get('kisi') and not kisi_dahil(d, s['kisi'], p): return False
    yeni_atama = kod in ('IS.ATADIM','IS.DEVRETTIM') or (kod=='GOREV.REDDETTIM' and g.get('revizyon_ver')) or (kod in ('GOREV.DEGISTIRDIM','IS.BAGLANTI_DUZELTTIM') and bool(set(g.get('degisenler',{})) & {'kisi','proje'}))
    if yeni_atama:
        for h in e['neyin_ustunde']:
            if h['tur'] not in ('IS', 'GOREV'): continue
            x = (d.isler if h['tur'] == 'IS' else d.gorevler).get(h['kimlik'], {})
            s = dict(x, **g.get('degisenler', {})); p = s.get('proje')
            if not p: continue
            ks = g.get('kisiler', [g.get('kime') or g.get('kisi') or s.get('kisi')])
            if any(k and not kisi_dahil(d, k, p) for k in ks): return False
            if h['tur'] == 'IS' and not birim_dahil(d, s.get('birim'), p): return False
    return True


def yetki(d, e):
    """Ek kapı; None eski eylemin mevcut yetki denetimini sürdürür."""
    from .kurallar_v9 import hedef_proje
    from .kurallar_v7 import rol_izni
    kod, g, kim = e['eylem_kodu'], e['girdiler'], e['kim']
    if not proje_yazma_kapisi(d, e): return False
    if kod.startswith('PROJE.ERISIM_') and d.ayar('proje_gorunurlugu', simdi(d), 'HERKES') == 'UYELER':
        return projede_yetkili(d, kim, g['proje'])
    if kod in ('ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM', 'PLAN.ONAYLADIM'):
        if not istihdamda(d, kim, simdi(d)): return False
        p = hedef_proje(e)
        if kod == 'ETAP.DEGISTIRDIM':
            p = d.etaplar.get(e['neyin_ustunde'][0]['kimlik'], {}).get('proje')
        s = d.projeler.get(p, {}).get('sorumlu')
        iliski = bool(s) and (kim == s or kim in ustler(d, s))
        kurallar = [r for r in d.yetki_kurallari if r['eylem_kodu'] == kod and not r.get('gecerli_bitis')]
        # HERKES/eski tablo eski plan kabulünü korur. Yeni varsayılanda YONETICI yoktur.
        if kod == 'PLAN.ONAYLADIM':
            if d.ayar('proje_gorunurlugu', simdi(d), 'HERKES') == 'UYELER':
                return iliski or 'YETKILI' in d.kisiler[kim].get('roller', [])
            if iliski: return True
        for r in kurallar:
            if 'PROJE_SORUMLUSU' in r['kimler'] and iliski: return True
            # Karar 91: CEO yetkisinin kök yönetimine mirası, başka projeye devir değildir.
            if 'YETKILI' in r['kimler'] and genel_yonetim(d, kim): return True
            if rol_izni(d, kim, r): return True
        return False
    return None


def sessiz_kabul_siniri(d, x):
    if x.get('kaynak_turu') != 'GECIKME' or x['tur'] == 'DIS': return None
    t = an(x['an']); n = d.ayar('sessiz_kabul_is_gunu', t, 0)
    if not n: return None
    # Süresiz kapalı takvimde bitiş yok; döngü mevcut görünümün ufkuyla sınırlı.
    son = max(simdi(d), d.saat.simdi())
    while n and t <= son:
        t += timedelta(days=1)
        if d.is_gunu(t, **({'kisi': x['kimlik']} if x['tur'] == 'KISI' else {'birim': x['kimlik']})):
            n -= 1
    return t if not n else None


def etkin_pay(d, x):
    """Zamanla türeyen durum; kaynak yüzdeyi veya olay günlüğünü değiştirmez."""
    if x['yuzde'] <= 0: return False
    if x.get('itirazda'): return False
    if x.get('dogrulandi') or x['tur'] == 'DIS': return True
    if x.get('kaynak_turu') != 'GECIKME': return False
    gecmis = x.get('gecmis', [])
    if any(e['eylem_kodu'].startswith('SORUMLULUK.') for e in gecmis): return False
    sinir = sessiz_kabul_siniri(d, x)
    return sinir is not None and sinir <= d.saat.simdi()


def bekleyen_pay(d, x):
    return x['yuzde'] > 0 and (x.get('itirazda') or not etkin_pay(d, x))


def kredi(d, gorev):
    from .gorunum_v9 import son_degerlendirme
    ev = son_degerlendirme(d, gorev['kimlik'])
    if not ev: return 0.0
    toplam = sum((Decimal(str(x['yuzde'])) for x in d.sorumluluklar.values()
                  if x['ret'] == ev['kimlik'] and etkin_pay(d, x)
                  and not (x['tur'] == 'KISI' and x['kimlik'] == gorev['kisi'])), Decimal(0))
    return float(toplam / 100)


def kesinlesme(d, gorevler):
    from .gorunum_v9 import son_degerlendirme
    ids = {ev['kimlik'] for g in gorevler if (ev := son_degerlendirme(d, g['kimlik']))}
    n = sum(bekleyen_pay(d, x) for x in d.sorumluluklar.values() if x['ret'] in ids)
    return dict(kesinlesmedi=bool(n), bekleyen_satir_sayisi=n)
