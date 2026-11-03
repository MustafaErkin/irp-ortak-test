"""T3 sürüm 3 ortak yönetim kapıları; yalnız belge kuralları."""
from .saat import an, gun_ani
from .olay import hedefler
from datetime import timedelta

def dongusuz(graf):
    renk = {}
    def gez(n):
        if renk.get(n) == 1: return False
        if renk.get(n) == 2: return True
        renk[n] = 1
        if any(not gez(p) for p in graf.get(n, [])): return False
        renk[n] = 2
        return True
    return all(gez(n) for n in graf)

def on_kosul_kapisi(d,e):
    kod,g,k = e['eylem_kodu'],e['girdiler'],e['olay_kimligi']
    if kod not in ('GOREV.ATADIM','GOREV.DEGISTIRDIM','IS.TANIMLADIM'): return True
    graf = {k:list(v.get('on_kosul',v.get('on_isler',[]))) for tablo in (d.gorevler,d.isler) for k,v in tablo.items()}
    yeniler = {}
    if kod == 'GOREV.DEGISTIRDIM':
        if 'on_kosul' not in g['degisenler']: return True
        yeniler[hedefler(e,'GOREV')[0]] = g['degisenler']['on_kosul']
    else:
        satirlar=g['gorevler' if kod.startswith('GOREV') else 'isler']
        for n,s in enumerate(satirlar,1):
            kimlik=k+'/'+str(n) if kod.startswith('GOREV') or len(satirlar)>1 else k
            yeniler[kimlik]=[k+'/'+str(p['satir']) if isinstance(p,dict) else p for p in s.get('on_kosul',s.get('on_isler',[]))]
    graf.update(yeniler)
    return all(p in graf for ps in yeniler.values() for p in ps) and dongusuz(graf)

def liste_hedefleri(e):
    kod,g=e['eylem_kodu'],e['girdiler']
    if kod=='IS.DEVRETTIM': return [g['kimden'],g['kime']]
    if kod in ('IS.ATADIM','IS.PLANSIZ_TANIMLADIM','IS.SIRALADIM'): return g.get('kisiler') or [g['kisi']]
    return []

def liste_kapisi(d,e):
    kod,g=e['eylem_kodu'],e['girdiler']; ids=hedefler(e,'IS')
    for kisi in liste_hedefleri(e):
        l=d.listeler.get(kisi,[])
        if not l or d.isler[l[0]]['durum']!='ONAY_BEKLIYOR' or not d.isler[l[0]].get('onay_beklet'): continue
        if kod=='IS.DEVRETTIM' and kisi==g['kimden']:
            if (ids and ids[0]==l[0]) or (g.get('kimden_yeni_is') and g['kimden_yeni_is']!=l[0]): return False
            continue
        n=g.get('sira',g.get('yeni_sira',g.get('kime_sira',1)))
        if (ids and ids[0]==l[0] and n!=1) or ((not ids or ids[0]!=l[0]) and n==1): return False
    return True

def ek_kapilar(d,e):
    kod,g,t=e['eylem_kodu'],e['girdiler'],an(e['oldugu_an'])
    if not liste_kapisi(d,e) or not on_kosul_kapisi(d,e): return False
    if kod == 'AYAR.ONAY_ORANI':
        gecerli=an(g.get('gecerli_baslangic') or e['oldugu_an'])
        if gecerli<t: return False
    if kod == 'TAKVIM.TANIMLADIM':
        yarin = gun_ani(t.date() + timedelta(days=1))
        gecerli = an(g.get('gecerli_baslangic') or yarin)
        if gecerli < yarin or gecerli != gun_ani(gecerli.date()): return False
    if kod == 'TATIL.EKLEDIM':
        if gun_ani(g['tarih']) < gun_ani(t.date() + timedelta(days=1)): return False
        if an(g.get('gecerli_baslangic') or t) < t: return False
    if kod=='MAAS.GUNCELLEDIM':
        ay=an(g['gecerli_baslangic']).date().replace(day=1).isoformat()
        if any(k.startswith(ay+':') for k in getattr(d,'ay_kapanislari',{})): return False
    if kod=='IS.ATADIM':
        kisiler=g.get('kisiler') or [g.get('kisi')]
        if len(kisiler)!=len(set(kisiler)): return False
        for k in kisiler:
            p=d.kisiler.get(k)
            if not p or p.get('ayrilis_tarihi'): return False
    if kod=='IS.SURE_EKLEDIM' and g['is_bitti']:
        ids=set(hedefler(e,'IS'))
        es=d.olaylar.values() if hasattr(d.olaylar,'values') else d.olaylar
        from .kabul import TANIKLIK
        if any(x['eylem_kodu'] in TANIKLIK and ids.intersection(hedefler(x,'IS')) and an(x['oldugu_an'])>an(g['bitis']) for x in es): return False
    return True
