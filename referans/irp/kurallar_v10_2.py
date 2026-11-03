"""T11: nesne projesi, karar sırası, yetkinlik ve modül cihaz alanı."""
from copy import deepcopy
import re
from .saat import an, gun

SEMALAR = {'KISI.YETKINLIK_TANIMLADIM': ('kisi', 'yetkinlikler', 'gecerli_baslangic')}


def nesne_projesi(g):
    ps = [x['kimlik'] for x in g.get('baglar', []) if x['tur'] == 'PROJE']
    return g.get('proje') or (ps[0] if len(ps) == 1 else None)


def bicim(d, e):
    kod, g = e['eylem_kodu'], e['girdiler']
    if kod in ('NESNE.ACTIM', 'NESNE.GUNCELLEDIM'):
        s = g if kod == 'NESNE.ACTIM' else g['degisenler']
        if 'baglar' in s and (not isinstance(s['baglar'], list) or any(
                not isinstance(x, dict) or not isinstance(x.get('tur'), str)
                or not isinstance(x.get('kimlik'), str) or not x['kimlik'] for x in s['baglar'])):
            raise ValueError('Nesne baglari')
        ps = [x['kimlik'] for x in s.get('baglar', []) if x['tur'] == 'PROJE']
        p = g.get('proje') if kod == 'NESNE.ACTIM' else d.nesneler.get(g['hedef'], {}).get('proje')
        if kod == 'NESNE.ACTIM':
            if p is not None and (not isinstance(p, str) or not p): raise ValueError('Nesne projesi')
            if (not p and len(ps) > 1) or (p and any(x != p for x in ps)):
                raise ValueError('Nesne proje baglari uyusmuyor')
        elif any(x != p for x in ps) or 'proje' in s:
            raise ValueError('Nesnenin projesi degismez')
    if kod == 'MODUL.TANIMLADIM' and 'cihaz_harfi' in g:
        if not isinstance(g['cihaz_harfi'], str) or not re.fullmatch('[A-Z]', g['cihaz_harfi']):
            raise ValueError('Modul cihaz harfi tek buyuk harf')
    if kod in SEMALAR:
        ys = g['yetkinlikler']
        if not isinstance(g['kisi'], str) or not isinstance(ys, list) or any(
                not isinstance(x, str) or not x for x in ys) or len(set(ys)) != len(ys):
            raise ValueError('Yetkinlikler tekil kod dizisi')
        gun(g['gecerli_baslangic'])
        if an(e['oldugu_an']) > d.saat.simdi(): raise ValueError('Yonetim olayi gelecekte olamaz')
    if kod in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM', 'IS.DEGISTIRDIM'):
        for s in g.get('isler', [g.get('degisenler', g)]):
            if s.get('yetkinlik') is not None and (not isinstance(s['yetkinlik'], str) or not s['yetkinlik']):
                raise ValueError('Is yetkinligi tek kod')


def yetki(d, e):
    if e['eylem_kodu'] not in SEMALAR: return None
    from .yetki_v6 import istihdamda, simdi
    from .kurallar_v7 import rol_izni
    if e.get('adina') or not istihdamda(d, e['kim'], simdi(d)): return False
    b = d.kisiler.get(e['girdiler']['kisi'], {}).get('birim')
    return any(r['eylem_kodu'] == e['eylem_kodu'] and not r.get('gecerli_bitis')
               and rol_izni(d, e['kim'], r, b) for r in d.yetki_kurallari)


def durum(d, e):
    kod, g = e['eylem_kodu'], e['girdiler']
    from .kurallar_v6 import kod_aktif
    if kod in SEMALAR:
        return (g['kisi'] in d.kisiler and gun(g['gecerli_baslangic']) >= an(e['oldugu_an']).date()
                and all(kod_aktif(d, 'YETKINLIK', x) for x in g['yetkinlikler']))
    if kod in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM', 'IS.DEGISTIRDIM'):
        if any(s.get('yetkinlik') and not kod_aktif(d, 'YETKINLIK', s['yetkinlik'])
               for s in g.get('isler', [g.get('degisenler', g)])): return False
    if kod == 'MODUL.TANIMLADIM':
        once = d.moduller.get(g['kod'], {}).get('cihaz_harfi')
        if once and once != g.get('cihaz_harfi'): return False
    if kod == 'MODUL.TANIMLADIM' and g.get('cihaz_harfi'):
        h = g['cihaz_harfi']
        if any(x['kod'] != g['kod'] and x.get('cihaz_harfi') == h for x in d.moduller.values()): return False
        if h in getattr(d, 'cihaz_harfleri', {}).values(): return False
        # Tarihsel normal cihaz olayları da ayrılmış harfin üstüne yazılamaz.
        es = getattr(d, '_kayitlar', {})
        if any(x['olay_kimligi'].endswith('-' + h) and not x['cihaz'].startswith('MODUL-') for x in es.values()): return False
    return None


def isle(m, e):
    if e['eylem_kodu'] not in SEMALAR: return False
    g = e['girdiler']; k = g['kisi']
    if k not in m.kisiler: return True
    if gun(g['gecerli_baslangic']) > m._an.date(): return True
    m.kisiler[k]['yetkinlikler'] = deepcopy(g['yetkinlikler'])
    for x in m.kisi_gecmisi:
        if x['kisi'] == k and x['gecerli_bitis'] is None: x['gecerli_bitis'] = g['gecerli_baslangic']
    s = {a: deepcopy(v) for a, v in m.kisiler[k].items() if a not in ('istihdam_donemleri', 'ayrilis_tarihi')}
    m.kisi_gecmisi.append(dict(s, kisi=k, gecerli_baslangic=g['gecerli_baslangic'], gecerli_bitis=None))
    return True


def bir_basamak(d, hedef):
    sonuc = {hedef}
    for k, x in d.nesneler.items():
        baglar = {b['kimlik'] for b in x.get('baglar', []) if b['tur'] == 'NESNE'}
        if k == hedef: sonuc.update(baglar)
        if hedef in baglar: sonuc.add(k)
    return sonuc


def cihaz_izni(d, e):
    h = e['olay_kimligi'][-1]
    m = next((x for x in d.moduller.values() if x.get('cihaz_harfi') == h), None)
    if m: return m['aktif'] and e['cihaz'] == 'MODUL-' + m['kod']
    return not e['cihaz'].startswith('MODUL-')


# Durum kapısının hedef tabloları. Ek girdiler ve toplu hedefler aşağıda çözülür.
HEDEF_TABLOLARI = {
    'IZIN': 'izinler', 'EK_MESAI': 'ek_mesai_planlari', 'DURUS': 'duruslar',
    'BAKIM': 'bakimlar', 'SORUMLULUK': 'sorumluluklar', 'ITIRAZ': 'itirazlar',
    'NESNE': 'nesneler', 'IS': 'isler', 'GOREV': 'gorevler', 'PROJE': 'projeler',
    'ETAP': 'etaplar', 'KISI': 'kisiler', 'BIRIM': 'birimler', 'TEZGAH': 'tezgahlar',
    'NESNE_TURU': 'nesne_turleri', 'MODUL': 'moduller', 'NOT': 'notlar',
    'KOD': 'kod_listesi', 'DOSYA': 'dosyalar',
}


def kayit_turu(d, key):
    for tur, tablo in HEDEF_TABLOLARI.items():
        if key in getattr(d, tablo, {}): return tur
    return 'OLAY'


def dayandigi_kayitlar(d, e):
    """Açık hedefler ile durum kapısının okuduğu dolaylı kayıtlar."""
    kod, g = e['eylem_kodu'], e['girdiler']
    hs = {(h['tur'], h['kimlik']) for h in e['neyin_ustunde']}
    def ek(tur, key):
        if isinstance(key, str) and key: hs.add((tur, key))
    def ic_basvurular(s):
        # İç içe değişiklik/sorumluluk girdileri de gerçek kayıt başvurusudur.
        for alan,tur in [('ana_proje','PROJE'),('sebep_olan','KISI'),('basi','KISI')]:ek(tur,s.get(alan))
        for x in s.get('sorumlular',[]):
            if x['tur'] in ('KISI','BIRIM'):ek(x['tur'],x['kimlik'])
        deg=s.get('degisiklik')
        if deg:
            if deg.get('kaynak'):ek(kayit_turu(d,deg['kaynak']),deg['kaynak'])
            ic_basvurular(deg)
    ic_basvurular(g)
    ek('KISI',e.get('adina'))
    if g.get('hedef') and kod != 'AYAR.SAAT_KAYDIRDIM':
        key = g['hedef']; ek(kayit_turu(d, key), key)
        if kod.startswith('SORUMLULUK.'):
            from .kurallar_v9 import sorumluluk_satiri
            s = sorumluluk_satiri(d, g)
            ek('OLAY', s.get('ret'))
            for k, x in d.sorumluluklar.items():
                if s and x['ret'] == s['ret']: ek('SORUMLULUK', k)
    for h in g.get('hedefler', []): ek(h['tur'], h['kimlik'])
    for s in g.get('isler', g.get('gorevler', [g.get('degisenler', g)])):
        ic_basvurular(s)
        for alan, tur in [('proje','PROJE'),('etap','ETAP'),('birim','BIRIM'),('tezgah','TEZGAH'),
                          ('nesne','NESNE'),('kisi','KISI'),('sorumlu','KISI'),('onaylayan','KISI')]: ek(tur, s.get(alan))
        for key in s.get('on_isler', []) + s.get('on_kosul', []):
            if isinstance(key, str): ek(kayit_turu(d, key), key)
        for b in s.get('baglar', []): ek(b['tur'], b['kimlik'])
        for r in s.get('roller', []): ek('KOD', 'ROL:'+r)
        if s.get('kategori'): ek('KOD','PD:'+s['kategori'])
        if s.get('yetkinlik'): ek('KOD','YETKINLIK:'+s['yetkinlik'])
    for alan in ('kisi', 'kimden', 'kime'): ek('KISI', g.get(alan))
    for k in g.get('kisiler', []): ek('KISI', k)
    for k in g.get('yetkinlikler', []): ek('KOD','YETKINLIK:'+k)
    for k in g.get('dosyalar', []): ek('DOSYA',k)
    for k in g.get('kimler', []): ek('KOD','ROL:'+k)
    if kod=='KOD.TANIMLADIM':ek('KOD',g['liste']+':'+g['kod'])
    if kod=='KOD.TANIMLADIM' and g['liste']=='DURUS_NEDENI':
        if g.get('ust'):ek('KOD','DURUS_NEDENI:'+g['ust'])
        for key,x in d.kod_listesi.items():
            if x.get('liste')=='DURUS_NEDENI' and x.get('ust')==g['kod']:ek('KOD',key)
    if kod=='YETKI.TANIMLADIM':ek('YETKI',g['eylem_kodu'])
    if kod.startswith('AYAR.') and kod!='AYAR.SAAT_KAYDIRDIM':
        ek('AYAR',g.get('anahtar') or kod.split('.')[1])
    if kod=='TAKVIM.TANIMLADIM':ek('TAKVIM','FIRMA')
    if kod=='GUN_ONAYI.AYARLADIM':ek('GUN_ONAY_AYARI',g['birim'])
    if kod.startswith(('GUN.','TATIL.')):ek('TAKVIM_GUNU',g['tarih'])
    if kod=='PROJE.ACTIM':ek('PROJE',g['kod'])
    if kod == 'MAAS.GUNCELLEDIM' and g.get('kisi') in d.tezgahlar: ek('TEZGAH',g['kisi'])
    if kod == 'BIRIM.TANIMLADIM':
        key=g.get('ust_birim'); seen=set()
        while key and key not in seen:
            seen.add(key); ek('BIRIM',key); key=d.birimler.get(key,{}).get('ust_birim')
        ek('KISI',g.get('basi'))
    from .kapilar_v3 import liste_hedefleri
    for k in liste_hedefleri(e): ek('LISTE', k)
    for tur, key in list(hs):
        if tur == 'LISTE':
            for k in d.listeler.get(key, []): ek('IS', k)
        x = getattr(d, HEDEF_TABLOLARI.get(tur, ''), {}).get(key, {})
        if tur in ('IS', 'GOREV'):
            for a, t in [('proje','PROJE'),('etap','ETAP'),('birim','BIRIM'),('tezgah','TEZGAH'),('nesne','NESNE'),('kisi','KISI'),('onaylayan','KISI')]: ek(t, x.get(a))
            if kod=='IS.DEVAM_ONAYLADIM' and x.get('kisi'):ek('KISI_GUNU',x['kisi']+':'+str(d.saat.simdi().date()))
            todo=list(x.get('on_isler',[]))+list(x.get('on_kosul',[])); seen=set()
            while todo:
                k=todo.pop()
                if not isinstance(k,str) or k in seen: continue
                seen.add(k); t=kayit_turu(d,k); ek(t,k)
                y=getattr(d,HEDEF_TABLOLARI.get(t,''),{}).get(k,{})
                todo.extend(y.get('on_isler',[])); todo.extend(y.get('on_kosul',[]))
            if tur=='IS' and kod=='IS.DEGISTIRDIM':
                for k,y in d.isler.items():
                    if y.get('ana_is')==key: ek('IS',k)
    if kod == 'NESNE.ACTIM': ek('NESNE_TURU', g['tur'])
    if kod.startswith('NESNE.') and g.get('hedef'):
        ek('NESNE_TURU', d.nesneler.get(g['hedef'], {}).get('tur'))
    if kod=='NESNE_TURU.TANIMLADIM':
        for k,x in d.nesneler.items():
            if x['tur']==g['kod']: ek('NESNE',k)
    if kod=='MODUL.TANIMLADIM':
        for k in d.moduller: ek('MODUL',k)
    if kod=='KISI.AYRILDI' or kod=='KISI.DEGISTIRDIM' and 'roller' in g['degisenler']:
        # En az bir yetkili kalması, açık işler/görevler ve yönlendirme bağı.
        for k in d.kisiler: ek('KISI',k)
        if kod=='KISI.AYRILDI':
            ek('LISTE',g['kisi'])
            for k,x in d.gorevler.items():
                if g['kisi'] in (x.get('kisi'),x.get('onaylayan')): ek('GOREV',k)
            for k in d.birimler: ek('BIRIM',k)
        ek('AYAR','izin_ik_onayi')
    if kod=='AYAR.DEGISTIRDIM' and g['anahtar']=='izin_ik_onayi':
        for k in d.kisiler:ek('KISI',k)
    if kod=='KOD.TANIMLADIM' and (g['liste'],g['kod'])==('ROL','IK'):ek('AYAR','izin_ik_onayi')
    if kod.startswith(('EK_MESAI.','IZIN.')):
        from .kurallar_v7 import hedef_satir
        k=hedef_satir(d,e).get('kisi',g.get('kisi')); ek('KISI',k)
        for tur,table in [('IZIN',d.izinler),('EK_MESAI',d.ek_mesai_planlari)]:
            for key,x in table.items():
                if x['kisi']==k: ek(tur,key)
    def takvim_kayitlari(kisi,bas,bit):
        from .takvim_v7 import gunler
        from datetime import timedelta
        ek('TAKVIM','FIRMA');ek('KISI',kisi)
        birim=d.kisiler.get(kisi,{}).get('birim');seen=set()
        while birim and birim not in seen:
            seen.add(birim);ek('BIRIM',birim);birim=d.birimler.get(birim,{}).get('ust_birim')
        for tarih in gunler(bas,an(bit)-timedelta(microseconds=1)):ek('TAKVIM_GUNU',str(tarih))
    if kod in ('EK_MESAI.PLANLADIM','EK_MESAI.ONAYLADIM'):
        from .takvim_v7 import pencere
        takvim_kayitlari(g['kisi'],*pencere(g))
    if kod in ('IS.ATADIM','GOREV.ATADIM'):
        from .takvim_v7 import pencere
        for s in g.get('gorevler',[g]):
            if s.get('ek_mesai'):
                for kisi in s.get('kisiler',[s.get('kisi')]):
                    takvim_kayitlari(kisi,*pencere(s['ek_mesai']))
                    for tur,table in [('IZIN',d.izinler),('EK_MESAI',d.ek_mesai_planlari)]:
                        for key,x in table.items():
                            if x['kisi']==kisi:ek(tur,key)
    if kod=='IS.SURE_EKLEDIM':takvim_kayitlari(e['adina'],g['baslangic'],g['bitis'])
    if kod in ('TATIL.KALDIRDIM','GUN.KALDIRDIM'): ek('TAKVIM_GUNU',g['tarih'])
    if kod == 'PLAN.ONAYLADIM' or kod == 'PROJE.KAPATTIM':
        ps = {k for t, k in hs if t == 'PROJE'}
        for tur in ('ETAP', 'IS', 'GOREV'):
            for key, x in getattr(d, HEDEF_TABLOLARI[tur]).items():
                if x.get('proje') in ps: ek(tur, key)
    if kod.startswith('GUN_SONU.'):
        ss = g.get('gunler', [g])
        for s in ss:
            kisi=s.get('kisi') or e.get('adina') or e['kim'];ek('KISI',kisi)
            ek('KISI_GUNU',kisi+':'+s['gun'])
    if kod in ('BIRIM.TANIMLADIM','TEZGAH.TANIMLADIM','KISI.EKLEDIM','NESNE_TURU.TANIMLADIM','MODUL.TANIMLADIM'):
        ek(kod.split('.')[0], g['kod'])
    return hs


def kaydin_olaylari(d, tur, key):
    """Kayıt doğumu, kendi olayları ve doğrudan hedeflenen etkin olaylar."""
    from .kurallar_v9 import olaylar
    x = getattr(d, HEDEF_TABLOLARI.get(tur, ''), {}).get(key, {})
    dogum = x.get('doguran_olay') or (key.split('/')[0] if key.startswith('K') and '-' in key else None)
    for e in olaylar(d):
        kod, g = e['eylem_kodu'], e['girdiler']
        ait = e['olay_kimligi'] == dogum or (tur == 'OLAY' and e['olay_kimligi'] == key)
        ait |= any(h['tur'] == tur and h['kimlik'] == key for h in e['neyin_ustunde'])
        ait |= g.get('hedef') == key and kod != 'AYAR.SAAT_KAYDIRDIM'
        ait |= any(h['tur'] == tur and h['kimlik'] == key for h in g.get('hedefler', []))
        if tur in ('KISI','BIRIM','TEZGAH','NESNE_TURU','MODUL','PROJE'):
            ait |= kod.startswith(tur + '.') and any(g.get(a)==key for a in ('kisi','kod','proje','kimlik','tezgah','birim'))
        if tur=='PROJE':ait |= kod=='PLAN.ONAYLADIM' and g['proje']==key
        if tur == 'KISI_GUNU':
            k, tarih = key.split(':', 1)
            ait |= (e.get('adina') or e['kim']) == k and str(an(e['oldugu_an']).date()) == tarih
            ait |= kod.startswith('GUN_SONU.') and any(s.get('kisi') == k and s.get('gun') == tarih for s in g.get('gunler', [g]))
        if tur=='LISTE':
            from .kapilar_v3 import liste_hedefleri
            ait |= key in liste_hedefleri(e)
        if tur=='KOD': ait |= kod=='KOD.TANIMLADIM' and g['liste']+':'+g['kod']==key
        if tur=='YETKI':ait |= kod=='YETKI.TANIMLADIM' and g['eylem_kodu']==key
        if tur=='AYAR':ait |= kod.startswith('AYAR.') and (g.get('anahtar') or kod.split('.')[1])==key
        if tur=='TAKVIM':ait |= kod=='TAKVIM.TANIMLADIM'
        if tur=='GUN_ONAY_AYARI':ait |= kod=='GUN_ONAYI.AYARLADIM' and g['birim']==key
        if tur=='DOSYA': ait |= any(x['dosya_kimligi']==key for x in e['kanit'])
        if tur=='TAKVIM_GUNU': ait |= kod.startswith(('GUN.','TATIL.')) and g['tarih']==key
        if tur=='BIRIM': ait |= kod=='AYAR.YONLENDIRDIM' and g['birim']==key
        if ait: yield e


def sira_siniri(d, e):
    # Sonraki olay yoksa pahalı kayıt çözümüne gerek yoktur; eşit an kimlikle karşılaştırılır.
    from .kurallar_v9 import olaylar
    es = olaylar(d); sinir = (an(e['oldugu_an']), e['olay_kimligi'])
    sonra = {x['olay_kimligi'] for x in es if (an(x['oldugu_an']), x['olay_kimligi']) > sinir}
    if not sonra: return None
    for tur, key in sorted(dayandigi_kayitlar(d, e)):
        for x in kaydin_olaylari(d, tur, key):
            if x['olay_kimligi'] in sonra: return x['olay_kimligi']
    return None
