"""T10: plan tarihleri ve nesne sürümleri. Modül kapısı ayrı kaynaktır."""
from copy import deepcopy
from .saat import an

SEMALAR = {
    'PLAN.TARIHLEDIM': ('hedefler',),
    'NESNE.SURUM_EKLEDIM': ('hedef', 'dosyalar'),
    'NESNE.SURUM_ONAYLADIM': ('hedef', 'surum_no'),
    'NESNE.SURUM_GERI_CEKTIM': ('hedef', 'surum_no', 'gerekce'),
    'MODUL.TANIMLADIM': ('kod', 'ad', 'servis_kimligi', 'aktif'),
}
TABLOLAR = ('nesne_surumleri', 'moduller')
PLAN_ALANLARI = ('planlanan_baslangic', 'planlanan_bitis')


def dolu(x):
    return isinstance(x, str) and bool(x.strip())


def bicim(d, e):
    kod, g = e['eylem_kodu'], e['girdiler']
    if kod in SEMALAR and an(e['oldugu_an']) > d.saat.simdi(): raise ValueError('T10 yonetim olayi gelecekte olamaz')
    if kod == 'PLAN.TARIHLEDIM':
        ss = g['hedefler']
        if not isinstance(ss, list) or not ss: raise ValueError('Plan hedefleri gerekli')
        for s in ss:
            if not isinstance(s, dict) or s.get('tur') not in ('IS', 'GOREV') or not dolu(s.get('kimlik')):
                raise ValueError('Plan hedefi')
            if any(not s.get(a) for a in PLAN_ALANLARI): raise ValueError('Iki plan tarihi gerekli')
        if len({(s['tur'], s['kimlik']) for s in ss}) != len(ss): raise ValueError('Plan hedefi tekil')
    elif kod in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM', 'GOREV.ATADIM'):
        ss = g.get('isler', g.get('gorevler', [g]))
    else: ss = []
    for s in ss:
        a, b = (an(s[k]) if s.get(k) is not None else None for k in PLAN_ALANLARI)
        if a and not b and kod == 'GOREV.ATADIM':
            from .gorev import son_teslim_ani
            b = son_teslim_ani(s, d)
        if a and b and a >= b: raise ValueError('Plan baslangici bitisten once olmali')
    for a in ('kaynak', 'gerekce'):
        if kod == 'PLAN.TARIHLEDIM' and a in g and not isinstance(g[a], str): raise ValueError('Plan metin alani')
    if kod.startswith('NESNE.SURUM_'):
        if not dolu(g['hedef']): raise ValueError('Surum hedefi')
        if kod.endswith('EKLEDIM'):
            if not isinstance(g['dosyalar'], list) or not g['dosyalar'] or not all(dolu(x) for x in g['dosyalar']):
                raise ValueError('En az bir dosya kimligi gerekli')
            if len(set(g['dosyalar'])) != len(g['dosyalar']): raise ValueError('Dosya kimlikleri tekil')
            if g.get('surum_adi') is not None and not isinstance(g['surum_adi'], str): raise ValueError('Surum adi metin')
            if 'aciklama' in g and not isinstance(g['aciklama'], str): raise ValueError('Aciklama metin')
        elif type(g['surum_no']) is not int or g['surum_no'] < 1: raise ValueError('Pozitif surum numarasi')
        if kod.endswith('GERI_CEKTIM') and not dolu(g['gerekce']): raise ValueError('Geri cekme gerekcesi gerekli')
    if kod == 'NESNE_TURU.TANIMLADIM' and g.get('surum_onaylayanlar') is not None:
        r = g['surum_onaylayanlar']
        if not isinstance(r, dict) or (r and (not isinstance(r.get('kimler'), list) or not all(dolu(x) for x in r['kimler']) or r.get('kapsam') not in ('BIRIM', 'FIRMA'))):
            raise ValueError('Surum onaylayanlar yetki satiri')
    if kod == 'MODUL.TANIMLADIM':
        if any(not dolu(g[a]) for a in ('kod', 'ad', 'servis_kimligi')) or type(g['aktif']) is not bool:
            raise ValueError('Modul tanimi')
        if g['kod'] == 'CEKIRDEK': raise ValueError('CEKIRDEK kaynak adi ayrilmistir')


def satir(d, h):
    return (d.isler if h['tur'] == 'IS' else d.gorevler).get(h['kimlik'], {})


def surum_satirlari(d, hedef):
    return sorted((x for x in d.nesne_surumleri.values() if x['nesne'] == hedef), key=lambda x: x['surum_no'])


def gecerli(d, hedef):
    return max((x for x in surum_satirlari(d, hedef) if x['durum'] == 'ONAYLI'), key=lambda x: x['surum_no'], default=None)


def bagli_nesneler(d, tur, key, x):
    from .kurallar_v9 import olaylar
    from .yetki_v6 import simdi
    baglar = {x['nesne']} if x.get('nesne') else set()
    for e in olaylar(d):
        if an(e['oldugu_an']) > simdi(d): continue
        dogum = e['olay_kimligi'] == x.get('doguran_olay')
        duzeltme = e['eylem_kodu'] == 'IS.BAGLANTI_DUZELTTIM' and any(h['tur']==tur and h['kimlik']==key for h in e['neyin_ustunde'])
        if not (dogum or duzeltme): continue
        hs = {h['kimlik'] for h in e['neyin_ustunde'] if h['tur']=='NESNE'}
        if hs: baglar = hs
        if duzeltme and 'nesne' in e['girdiler']['degisenler']:
            n=e['girdiler']['degisenler']['nesne']; baglar={n} if n else set()
    return baglar


def onaylayabilir(d, kim, nesne, surum=None):
    from .yetki_v6 import ustler, istihdamda, simdi
    from .kurallar_v7 import rol_izni
    if not istihdamda(d, kim, simdi(d)) or (surum and kim == surum['ekleyen']): return False
    r = d.nesne_turleri.get(nesne.get('tur'), {}).get('surum_onaylayanlar')
    if not r: return kim in ustler(d, nesne.get('sorumlu'))
    return rol_izni(d, kim, r, d.kisiler.get(nesne.get('sorumlu'), {}).get('birim'))


def yetki(d, e):
    from .yetki_v6 import ustler, istihdamda, simdi
    from .kurallar_v7 import rol_izni
    from .kurallar_v10 import projede_yetkili, proje_yazma_kapisi
    kod, g, kim = e['eylem_kodu'], e['girdiler'], e['kim']
    if kod not in SEMALAR: return None
    if e.get('adina') or not istihdamda(d, kim, simdi(d)): return False
    roller = d.kisiler[kim].get('roller', [])
    if kod == 'MODUL.TANIMLADIM': return 'YETKILI' in roller
    if kod == 'PLAN.TARIHLEDIM':
        rs = [r for r in d.yetki_kurallari if r['eylem_kodu'] == kod and not r.get('gecerli_bitis')]
        for h in g['hedefler']:
            x = satir(d, h)
            if not x: continue  # Olmayan hedef DURUM tanısı alır.
            if h['tur'] == 'GOREV' and not x.get('proje'):
                if kim != x.get('veren') and kim not in ustler(d, x.get('veren')): return False
            elif not any(rol_izni(d, kim, r, x.get('birim') or d.kisiler.get(x.get('kisi'), {}).get('birim')) for r in rs): return False
            if x.get('proje') and d.ayar('proje_gorunurlugu', simdi(d), 'HERKES') == 'UYELER' and not projede_yetkili(d, kim, x['proje']): return False
        return True
    x = d.nesneler.get(g['hedef'], {})
    if not proje_yazma_kapisi(d, e):
        # Karar 99: yalnız sorumlunun kendi belgesine taslak ekleme istisnası.
        if kod != 'NESNE.SURUM_EKLEDIM' or kim != x.get('sorumlu'): return False
        from .gorunum_v9 import proje_gorebilir_mi
        from .kurallar_v10 import olay_projeleri
        if not all(proje_gorebilir_mi(d, kim, p) if p == x.get('proje') else projede_yetkili(d, kim, p)
                   for p in olay_projeleri(d, e)): return False
    if not x: return True
    if kod.endswith('EKLEDIM'):
        return kim == x.get('sorumlu') or kim in ustler(d, x.get('sorumlu')) or 'YETKILI' in roller
    s = next((s for s in surum_satirlari(d, g['hedef']) if s['surum_no'] == g['surum_no']), None)
    return onaylayabilir(d, kim, x, s)


def zorunlu_hedefler(e):
    if e['eylem_kodu'] == 'PLAN.TARIHLEDIM': return {(x['tur'], x['kimlik']) for x in e['girdiler']['hedefler']}
    if e['eylem_kodu'].startswith('NESNE.SURUM_'): return {('NESNE', e['girdiler']['hedef'])}
    return set()


def durum(d, e):
    kod, g = e['eylem_kodu'], e['girdiler']
    if kod == 'PLAN.TARIHLEDIM': return all(satir(d, h) and satir(d, h)['durum'] not in ('BITTI', 'IPTAL') for h in g['hedefler'])
    if kod == 'MODUL.TANIMLADIM':
        return not any(x['kod'] != g['kod'] and x['servis_kimligi'] == g['servis_kimligi'] for x in d.moduller.values())
    if not kod.startswith('NESNE.SURUM_'): return None
    if g['hedef'] not in d.nesneler: return False
    t=an(e['oldugu_an'])
    if t < d.nesneler[g['hedef']]['olusma_ani']: return False
    ss = surum_satirlari(d, g['hedef'])
    if kod.endswith('EKLEDIM'):
        no=e.get('nesne_surum_no',len(ss)+1)
        ad = (g.get('surum_adi') or '').strip() or str(no)
        dosyalar = set(d.dosyalar) | {x['dosya_kimligi'] for x in e['kanit']}
        return all(x['surum_adi'] != ad and x['surum_no'] != no for x in ss) and set(g['dosyalar']) <= dosyalar
    s = next((x for x in ss if x['surum_no'] == g['surum_no']), {})
    son=max((s[k] for k in ('eklenme_ani','onay_ani','geri_cekme_ani') if s.get(k)),default=t)
    return t>=son and s.get('durum') in (('TASLAK',) if kod.endswith('ONAYLADIM') else ('TASLAK', 'ONAYLI'))


def isle(m, e):
    kod, g, oid = e['eylem_kodu'], e['girdiler'], e['olay_kimligi']
    if kod not in SEMALAR: return False
    if not durum(m, e):
        m.supheli(e, 'T10 karari yeniden hesapta duruma uymuyor'); return True
    if kod == 'MODUL.TANIMLADIM': m.moduller[g['kod']] = deepcopy(g)
    elif kod == 'PLAN.TARIHLEDIM':
        for h in g['hedefler']: satir(m, h).update({a: an(h[a]) for a in PLAN_ALANLARI})
    else:
        hedef, t = g['hedef'], an(e['oldugu_an'])
        once = gecerli(m, hedef)
        once_no = once['surum_no'] if once else None
        ss = surum_satirlari(m, hedef)
        if kod.endswith('EKLEDIM'):
            no = e.get('nesne_surum_no',len(ss) + 1)
            key = hedef + '/surum/' + str(no)
            m.nesne_surumleri[key] = dict(kimlik=key, nesne=hedef, surum_no=no,
                surum_adi=(g.get('surum_adi') or '').strip() or str(no), dosyalar=deepcopy(g['dosyalar']),
                aciklama=g.get('aciklama', ''), durum='TASLAK', ekleyen=e['kim'], eklenme_ani=t,
                onaylayan=None, onay_ani=None, geri_ceken=None, geri_cekme_ani=None, gerekce=None, doguran_olay=oid)
        else:
            s = next(x for x in ss if x['surum_no'] == g['surum_no'])
            if kod.endswith('ONAYLADIM'): s.update(durum='ONAYLI', onaylayan=e['kim'], onay_ani=t)
            else: s.update(durum='GERI_CEKILDI', geri_ceken=e['kim'], geri_cekme_ani=t, gerekce=g['gerekce'])
        m.nesneler[hedef]['olaylar'].append(oid)  # Sürüm yarışı nesnenin tazelik özetini değiştirir.
        sonra = gecerli(m, hedef)
        if once_no != (sonra['surum_no'] if sonra else None):
            from .modul_bildirimi import alici_gorebilir
            alicilar = set()
            from .kurallar_v10_2 import bir_basamak
            bagli = bir_basamak(m, hedef)
            for tur, tablo in [('IS', m.isler), ('GOREV', m.gorevler)]:
                for key, x in tablo.items():
                    if x['durum'] in ('BITTI', 'IPTAL') or not bagli.intersection(bagli_nesneler(m,tur,key,x)): continue
                    ks = {k for k, liste in m.listeler.items() if key in liste} if tur == 'IS' else {x.get('kisi')}
                    alicilar.update(k for k in ks if k != e['kim'] and alici_gorebilir(m, k, dict(tur=tur, kimlik=key)))
            for k in sorted(alicilar): m.bildir(e, 'R43', k, t, hedef)
    return True
