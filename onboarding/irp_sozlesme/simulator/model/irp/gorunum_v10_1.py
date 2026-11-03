"""T10 sorguları. Çağıran verilmeyen biçimler yalnız iç hesap içindir."""
from copy import deepcopy
from datetime import timedelta
from itertools import combinations
from .saat import an, gun, gun_ani
from .kurallar_v10_1 import gecerli, surum_satirlari, onaylayabilir


def surum_gorebilir(d, kim, s):
    from .gorunum_v9 import gorebilir_mi
    from .yetki_v6 import ustler
    x = d.nesneler.get(s['nesne'], {})
    if not x or not gorebilir_mi(d, kim, 'NESNE', s['nesne']): return False
    # Karar 99: üstlerin okuma hakkı türün onay yetkisinden bağımsızdır.
    return (s['durum'] != 'TASLAK' or kim in (s['ekleyen'], x['sorumlu'])
            or kim in ustler(d, x['sorumlu']) or onaylayabilir(d, kim, x, s))


def surumler(d, nesne, cagiran=None):
    return [deepcopy(s) for s in surum_satirlari(d, nesne) if cagiran is None or surum_gorebilir(d, cagiran, s)]


def gecerli_surum(d, nesne, t=None, cagiran=None):
    if cagiran is not None:
        from .gorunum_v9 import gorebilir_mi
        if not gorebilir_mi(d,cagiran,'NESNE',nesne): return None
    if t is not None:
        from .gorunum_v7 import durum
        d = durum(d, t)
    s = gecerli(d, nesne)
    return deepcopy(s) if s and (cagiran is None or surum_gorebilir(d, cagiran, s)) else None


def dosya_gorebilir(d, kim, dosya):
    ss = [s for s in d.nesne_surumleri.values() if dosya in s['dosyalar']]
    return not ss or any(surum_gorebilir(d, kim, s) for s in ss)


def surum_olayi_gorebilir(d, kim, e):
    if not e['eylem_kodu'].startswith('NESNE.SURUM_'): return True
    ss = surum_satirlari(d, e['girdiler']['hedef'])
    s = next((s for s in ss if s['doguran_olay'] == e['olay_kimligi'] or s['surum_no'] == e['girdiler'].get('surum_no')), None)
    return bool(s) and surum_gorebilir(d, kim, s)


def pencere(bas, bit=None):
    a = an(bas) if hasattr(bas,'hour') or 'T' in str(bas) else gun_ani(gun(bas))
    b = an(bit) if bit is not None and (hasattr(bit,'hour') or 'T' in str(bit)) else gun_ani(gun(bit if bit is not None else bas) + timedelta(days=1))
    if a >= b: raise ValueError('Gorunum araligi')
    return a, b


def plan_araligi(d, tur, x):
    a, b = x.get('planlanan_baslangic'), x.get('planlanan_bitis')
    if tur == 'GOREV' and not b:
        from .gorev import son_teslim_ani
        b = son_teslim_ani(x, d)
    return an(a) if a else None, an(b) if b else None


def sapma(d, durum, p, q, bas, bit):
    if durum == 'IPTAL': return None
    if bit and q: return dict(tur='BITIS',dakika=(bit-q).total_seconds()/60)
    if q and q < d.saat.simdi(): return dict(tur='GERIDE')
    if p and p < d.saat.simdi() and not bas: return dict(tur='BASLAMADI')
    return None


def plan_cakismalari(d, kaynak, bas, bit=None, cagiran=None):
    from .gorunum_v9 import gorebilir_mi
    a, b = pencere(bas, bit)
    if isinstance(kaynak, str): kaynak = dict(tur='KISI' if kaynak in d.kisiler else 'TEZGAH', kimlik=kaynak)
    tur, key = kaynak['tur'], kaynak['kimlik']
    if cagiran:
        from .yetki_v6 import istihdamda
        if not istihdamda(d,cagiran,d.saat.simdi()): raise PermissionError('Gorunurluk')
    adaylar = []
    for cins, tablo in [('IS', d.isler), ('GOREV', d.gorevler)]:
        for k, x in tablo.items():
            if x['durum'] in ('BITTI', 'IPTAL'): continue
            uygun = (k in d.listeler.get(key, []) if cins == 'IS' else x.get('kisi') == key) if tur == 'KISI' else cins == 'IS' and x.get('tezgah') == key
            if not uygun: continue
            p, q = plan_araligi(d, cins, x)
            if p and q and max(a, p) < min(b, q): adaylar.append((cins, k, p, q))
    sonuc = []
    for x, y in combinations(sorted(adaylar), 2):
        p, q = max(a, x[2], y[2]), min(b, x[3], y[3])
        if p < q: sonuc.append(dict(hedefler=[dict(tur='ERISIM_DISI') if cagiran and not gorebilir_mi(d,cagiran,z[0],z[1]) else dict(tur=z[0], kimlik=z[1]) for z in (x, y)], baslangic=p, bitis=q))
    return sonuc


def gantt(d, proje, bas, bit=None, cagiran=None):
    from .gorunum_v9 import gorebilir_mi, proje_gorebilir_mi
    from .kurallar_v9 import olaylar
    if cagiran and not proje_gorebilir_mi(d, cagiran, proje): raise PermissionError('Proje gorunurlugu')
    a, b = pencere(bas, bit); sonuc = []; es = olaylar(d)
    def satir(tur, key, x):
        from .gorunum_v10_2 import gecikme_olculeri
        p, q = plan_araligi(d, tur, x)
        if tur == 'IS':
            ts = [an(e['oldugu_an']) for e in es if e['eylem_kodu'] == 'IS.BASLADIM' and e['olay_kimligi'] not in d.supheliler and any(h['tur'] == 'IS' and h['kimlik'] == key for h in e['neyin_ustunde'])]
            r = min(ts, default=None)
        else: r = an(x['ilk_kabul_ani'] or x['kabul_ani']) if x.get('ilk_kabul_ani') or x.get('kabul_ani') else None
        s = an(x['bitis_ani']) if x['durum'] == 'BITTI' and x.get('bitis_ani') else None
        return dict(tur=tur, kimlik=key, etap=x.get('etap'), tezgah=x.get('tezgah'), kisi=x.get('kisi'), planlanan_baslangic=p, planlanan_bitis=q,
            gerceklesen_baslangic=r, gerceklesen_bitis=s, durum=x['durum'], ilerleme=100 if x['durum']=='BITTI' else 0, sapma=sapma(d,x['durum'],p,q,r,s),**gecikme_olculeri(d,tur,x))
    def aralikta(s):
        p,q=s['planlanan_baslangic'],s['planlanan_bitis']; r,v=s['gerceklesen_baslangic'],s['gerceklesen_bitis']
        return bool(((p or q) and max(a,p or a)<min(b,q or b)) or (r and max(a,r)<min(b,v or d.saat.simdi())))
    satirlar = []
    for tur, tablo in [('IS', d.isler), ('GOREV', d.gorevler)]:
        for k, x in sorted(tablo.items()):
            if x.get('proje') != proje or (cagiran and not gorebilir_mi(d, cagiran, tur, k)): continue
            s = satir(tur, k, x)
            if s: satirlar.append(s)
    planlar = d.plan_surumleri.get(proje, [])
    plan = planlar[-1]['etaplar'] if planlar else {}
    for k, x in sorted(d.etaplar.items()):
        if x['proje'] != proje: continue
        alt = [s for s in satirlar if s['etap'] == k]
        p = plan.get(k, {}); z = gun_ani(p['baslangic']) if p else None; v = gun_ani(gun(p['bitis']) + timedelta(days=1)) if p else None
        gorunen=[s for s in alt if aralikta(s)]
        if not gorunen and not (z and max(a,z)<min(b,v)): continue
        etkin=[s for s in alt if s['durum']!='IPTAL']
        sonuc.append(dict(tur='ETAP', kimlik=k, etap=None, tezgah=None, kisi=None, planlanan_baslangic=z, planlanan_bitis=v,
            gerceklesen_baslangic=min((s['gerceklesen_baslangic'] for s in etkin if s['gerceklesen_baslangic']),default=None),
            gerceklesen_bitis=max((s['gerceklesen_bitis'] for s in etkin),default=None) if etkin and all(s['gerceklesen_bitis'] for s in etkin) else None,
            durum='BITTI' if etkin and all(s['durum']=='BITTI' for s in etkin) else 'ACIK',ilerleme=0,sapma=None,gecikme_takvim_dk=None,gecikme_mesai_dk=None))
        etap_satiri=sonuc[-1]
        from .gorunumler import etap_gostergesi
        etap_satiri['ilerleme']=etap_gostergesi(d,k)['yuzde']
        etap_satiri['sapma']=sapma(d,etap_satiri['durum'],z,v,etap_satiri['gerceklesen_baslangic'],etap_satiri['gerceklesen_bitis'])
        sonuc.extend(gorunen)
    sonuc.extend(s for s in satirlar if s['etap'] not in d.etaplar and aralikta(s))
    return sonuc


def bildirim_kutusu(d, kisi, cagiran=None):
    if cagiran is not None and cagiran != kisi: raise PermissionError('Bildirim kutusu aliciya aittir')
    from .modul_bildirimi import kutu
    return kutu(d, kisi)
