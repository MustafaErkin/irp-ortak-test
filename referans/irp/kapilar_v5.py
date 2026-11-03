"""T3 §5: normal yolun basvuru ve yasam dongusu kapilari."""
from datetime import timedelta
from copy import deepcopy
import re
from .saat import an, gun_ani
from .olay import hedefler
from .kapilar_v3 import dongusuz

ROLLER = {'YETKILI', 'YONETICI', 'EKIP_LIDERI', 'CALISAN', 'BEYAZ_YAKA'}
BITEN = {'BITTI', 'IPTAL'}


def aktif_kisi(d, k):
    return bool(d.kisiler.get(k)) and not d.kisiler[k].get('ayrilis_tarihi')


def proje_etap(d, s):
    p, et = s.get('proje'), s.get('etap')
    if s.get('nereye') == 'PROJE' and not p: return False
    if p and (p not in d.projeler or not d.projeler[p].get('aktif', True)): return False
    return not et or (et in d.etaplar and d.etaplar[et]['proje'] == p)


def is_basvurulari(d, s):
    b = d.birimler.get(s.get('birim'), {})
    te = s.get('tezgah')
    return (proje_etap(d, s) and b.get('tur') == 'ATOLYE'
            and (not te or (te in d.tezgahlar and d.tezgahlar[te].get('aktif', True))))


def bicim(d, e):
    if e['eylem_kodu']=='PLAN.ONAYLADIM' and d.plan_surumleri.get(e['girdiler']['proje']) and not e['girdiler'].get('gerekce','').strip():
        raise ValueError('B1 ve sonrasi gerekce zorunlu')
    """Sirket ayarina bagli bicim denetimi (aktarimda da ayni desen)."""
    g, kod = e['girdiler'], e['eylem_kodu']
    satirlar = g['isler'] if kod == 'IS.TANIMLADIM' else [g] if kod == 'IS.PLANSIZ_TANIMLADIM' else []
    if kod in ('IS.DEGISTIRDIM', 'IS.BAGLANTI_DUZELTTIM') and 'parca_kodu' in g['degisenler']: satirlar = [g['degisenler']]
    desen = d.ayar('parca_kodu_deseni', an(e['oldugu_an']), '')
    for s in satirlar:
        if desen and s.get('parca_kodu') and not re.fullmatch(desen, s['parca_kodu']):
            raise ValueError('Parca kodu sirket desenine uymuyor')


def kapilar(d, e):
    kod, g, t = e['eylem_kodu'], e['girdiler'], an(e['oldugu_an'])
    from .kurallar_v6 import kapilar as yeni_kapilar
    sonuc = yeni_kapilar(d, e)
    if sonuc is not None: return sonuc
    if kod == 'BIRIM.TANIMLADIM':
        b = d.birimler.get(g['kod'], {})
        if g['tur'] not in ('ATOLYE', 'MASA_BASI') or (b and b['tur'] != g['tur']): return False
        if g.get('ust_birim') and g['ust_birim'] not in d.birimler: return False
        if g.get('basi') and not aktif_kisi(d, g['basi']): return False
        agac = {k: [v['ust_birim']] if v.get('ust_birim') else [] for k, v in d.birimler.items()}
        agac[g['kod']] = [g['ust_birim']] if g.get('ust_birim') else []
        return dongusuz(agac)
    if kod in ('KISI.EKLEDIM', 'KISI.DEGISTIRDIM'):
        if kod == 'KISI.EKLEDIM':
            if g['kod'] in d.kisiler: return False
            s = g
        else:
            if not aktif_kisi(d, g['kisi']): return False
            if set(g['degisenler']) - {'ad', 'birim', 'ust', 'yaka', 'roller'}: return False
            s = dict(d.kisiler[g['kisi']], **g['degisenler'])
            # A20: yetki degisimi olay aninda; gelecek/gecmis icin ayri karar yok.
            if an(g['gecerli_baslangic']) != t: return False
        return (s.get('birim') in d.birimler and s.get('yaka') in ('MAVI', 'BEYAZ')
                and bool(s.get('roller')) and set(s['roller']) <= ROLLER
                and (not s.get('ust') or aktif_kisi(d, s['ust'])))
    if kod == 'KISI.AYRILDI':
        k = g['kisi']
        return (aktif_kisi(d, k) and an(g['ayrilis_tarihi']).date() >= t.date()
                and not d.listeler.get(k)
                and not any(x['durum'] not in BITEN and k in (x.get('kisi'), x.get('onaylayan')) for x in d.gorevler.values())
                and not any(x.get('basi') == k for x in d.birimler.values()))
    if kod == 'TEZGAH.TANIMLADIM': return d.birimler.get(g['birim'], {}).get('tur') == 'ATOLYE'
    if kod == 'PROJE.ACTIM': return g['kod'] not in d.projeler
    if kod in ('PROJE.DEGISTIRDIM', 'PROJE.KAPATTIM'):
        ids = hedefler(e, 'PROJE'); p = ids[0]
        if not d.projeler.get(p, {}).get('aktif', False): return False
        if kod == 'PROJE.DEGISTIRDIM': return set(g['degisenler']) <= {'ad', 'musteri', 'teslim_tarihi'}
        return not any(x.get('proje') == p and x['durum'] not in BITEN for tablo in (d.isler, d.gorevler) for x in tablo.values())
    if kod in ('ETAP.TANIMLADIM', 'ETAP.DEGISTIRDIM'):
        if kod == 'ETAP.TANIMLADIM': s = g
        else:
            et = d.etaplar.get(hedefler(e, 'ETAP')[0])
            if not et or set(g['degisenler']) - {'ad', 'baslangic', 'bitis', 'hedef_saat', 'sorumlu'}: return False
            s = dict(et, **g['degisenler'])
        return (s['proje'] in d.projeler and d.projeler[s['proje']].get('aktif', True)
                and s['birim'] in d.birimler and an(s['baslangic']) <= an(s['bitis']) and s['hedef_saat'] >= 0)
    if kod in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM'):
        satirlar = g['isler'] if kod == 'IS.TANIMLADIM' else [dict(g, birim=g.get('birim') or d.kisiler[e['kim']]['birim'])]
        if not all(is_basvurulari(d, s) for s in satirlar): return False
        if kod == 'IS.PLANSIZ_TANIMLADIM' and not aktif_kisi(d, g['kisi']): return False
    if kod == 'IS.DEVRETTIM' and not aktif_kisi(d, g['kime']): return False
    if kod in ('IS.DEGISTIRDIM', 'IS.IPTAL_ETTIM'):
        i = d.isler.get(hedefler(e, 'IS')[0])
        if not i or i['durum'] in BITEN: return False
        if kod == 'IS.IPTAL_ETTIM': return True
        alanlar = g['degisenler']
        if set(alanlar) - {'islem', 'tahmini_sure_dk', 'teslim_tarihi', 'tezgah', 'tezgah_rolu', 'on_isler', 'onay_gerekli', 'onay_beklet', 'yetkinlik'}: return False
        if not is_basvurulari(d, dict(i, **alanlar)): return False
        if i['durum'] == 'ONAY_BEKLIYOR' and {'onay_gerekli', 'onay_beklet'} & set(alanlar): return False
        altlar = [i] + [v for v in d.isler.values() if v.get('ana_is') == i['kimlik']]
        if any(x['durum'] in BITEN | {'ONAY_BEKLIYOR'} for x in altlar[1:]): return False
        if 'on_isler' in alanlar:
            yeniler = set(alanlar['on_isler']) - set(i['on_isler'])
            kimlikler = {x['kimlik'] for x in altlar}
            if yeniler and (any(h.get('acik_is') in kimlikler for h in d.kisi_durumu.values())
                           or any(a['is'] in kimlikler and a['kova'] in ('CALISMA', 'YENIDEN_ISLEME') for a in d.araliklar)):
                return False
            graf = {k: list(v.get('on_isler', [])) for k, v in d.isler.items()}
            for x in altlar: graf[x['kimlik']] = alanlar['on_isler']
            if any(p not in graf for p in alanlar['on_isler']) or not dongusuz(graf): return False
    if kod == 'GOREV.ATADIM':
        return all(proje_etap(d, s) and aktif_kisi(d, s['kisi'])
                   and (not s.get('onay_gerekli') or aktif_kisi(d, s.get('onaylayan'))) for s in g['gorevler'])
    if kod == 'GOREV.DEGISTIRDIM':
        s = dict(d.gorevler.get(hedefler(e, 'GOREV')[0], {}), **g['degisenler'])
        if not proje_etap(d, s): return False
        for alan in ('kisi', 'onaylayan'):
            if alan in g['degisenler'] and s.get(alan) and not aktif_kisi(d, s[alan]): return False
    if kod == 'GOREV.REDDETTIM' and g.get('revizyon_ver'):
        if not aktif_kisi(d, g['kime']): return False
    if kod == 'AYAR.YONLENDIRDIM':
        return g['birim'] in d.birimler and all(aktif_kisi(d, k) for k in g['kisiler'])
    if kod == 'MAAS.GUNCELLEDIM': return g['kisi'] in d.kisiler or g['kisi'] in d.tezgahlar
    if kod == 'AYAR.MAAS_PAYDASI':
        v = an(g.get('gecerli_baslangic') or t)
        return g['deger'] > 0 and v.day == 1 and v == gun_ani(v.date()) and v.date().replace(day=1) > t.date().replace(day=1)
    if kod == 'AYAR.PARCA_KODU_DESENI': return an(g.get('gecerli_baslangic') or t) >= t
    return True
