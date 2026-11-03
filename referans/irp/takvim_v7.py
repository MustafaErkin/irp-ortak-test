"""T8: takvim, kisi pencereleri ve kesinti katmani. Araliklar [bas, bit)."""
from copy import deepcopy
from datetime import timedelta
from .saat import an, gun, gun_ani


def gunler(bas, bit):
    bas = an(bas) if isinstance(bas,str) and 'T' in bas else bas
    bit = an(bit) if isinstance(bit,str) and 'T' in bit else bit
    d = gun(bas)
    while d <= gun(bit):
        yield d
        d += timedelta(days=1)


def saat_ani(tarih, saat):
    return gun_ani(tarih) + timedelta(days=1) if saat == '24:00' else gun_ani(tarih, saat)


def pencere(g):
    return tuple(saat_ani(g['tarih'], g[k]) if 'T' not in g[k] else an(g[k]) for k in ('baslangic', 'bitis'))


def kesisim(a, b, c, d):
    return max(a, c) < min(b, d)


def birlesim(araliklar):
    sonuc = []
    for a, b in sorted(araliklar):
        if a >= b: continue
        if sonuc and a <= sonuc[-1][1]: sonuc[-1] = (sonuc[-1][0], max(b, sonuc[-1][1]))
        else: sonuc.append((a, b))
    return sonuc


def cikar(araliklar, engeller):
    for x, y in birlesim(engeller):
        yeni = []
        for a, b in araliklar:
            if not kesisim(a, b, x, y): yeni.append((a, b)); continue
            if a < x: yeni.append((a, x))
            if y < b: yeni.append((y, b))
        araliklar = yeni
    return araliklar


def saatler(araliklar):
    return sum((b-a).total_seconds()/3600 for a, b in birlesim(araliklar))


def normal(m, tarih, mola=True, kisi=None, birim=None):
    tarih = gun(tarih)
    if not m.is_gunu(tarih,kisi,birim): return []
    t = m.takvim(tarih,kisi,birim)
    araliklar = [(saat_ani(tarih, t['mesai_baslangic']), saat_ani(tarih, t['mesai_bitis']))]
    return cikar(araliklar, [(saat_ani(tarih, x['bas']), saat_ani(tarih, x['bit'])) for x in t['sabit_molalar']]) if mola else araliklar


def izinler(m, kisi):
    return [(an(x['baslangic']), an(x['bitis'])) for x in m.izinler.values() if x['kisi'] == kisi and x['durum'] == 'ONAYLI']


def ekler(m, kisi, tarih=None, gercek=False):
    sonuc = []
    for x in m.ek_mesai_planlari.values():
        if x['kisi'] != kisi or x.get('iptal'): continue
        if gercek and m.kisiler.get(kisi, {}).get('yaka') != 'MAVI': continue
        a, b = pencere(x)
        if tarih is not None:
            a, b = max(a, gun_ani(tarih)), min(b, gun_ani(gun(tarih)+timedelta(days=1)))
        if a < b: sonuc.append((a, b))
    # Takvim sonradan degisirse pencere normal mesaiyle cift sayilmaz.
    sonuc = birlesim(sonuc)
    return cikar(sonuc,[p for a,b in sonuc for tarih in gunler(a,b) for p in normal(m,tarih,False,kisi)])


def kisi_normal(m, kisi, tarih):
    from .yetki_v6 import istihdamda
    if not istihdamda(m, kisi, tarih): return []
    return cikar(normal(m, tarih, kisi=kisi), izinler(m, kisi))


def katsayi(m, tarih):
    tur = 'TATIL' if not m.is_gunu(tarih) and str(tarih) in m.tatiller else 'PAZAR' if gun(tarih).isoweekday() == 7 else 'CUMARTESI' if gun(tarih).isoweekday() == 6 else 'HAFTA_ICI'
    return m.ayar('fazla_mesai_katsayilari', gun_ani(tarih), {'TATIL':2, 'PAZAR':2, 'CUMARTESI':1.5, 'HAFTA_ICI':1.5})[tur]


def kapsamda(m, kisi, kapsam):
    b = m.kisiler.get(kisi, {}).get('birim')
    return birim_kapsamda(m, b, kapsam)


def birim_kapsamda(m, b, kapsam):
    if kapsam == 'FIRMA': return True
    gorulen = set()
    while b and b not in gorulen:
        if b in kapsam: return True
        gorulen.add(b); b = m.birimler.get(b, {}).get('ust_birim')
    return False


def hazirla(m, olaylar):
    """Tarihli onaylar gecmisi yeniden boler; tanikliklar olay aninda islenir."""
    for e in olaylar:
        kod, g, oid = e['eylem_kodu'], e['girdiler'], e['olay_kimligi']
        if kod == 'AYAR.DEGISTIRDIM':
            m.ayarlar.append(dict(g, gecerli_baslangic=g.get('gecerli_baslangic', e['oldugu_an']), doguran_olay=oid))
        if kod == 'GUN.TANIMLADIM':
            m.gun_tanimlari[g['tarih']] = deepcopy(g)
            if g['tur'] == 'TATIL': m.tatiller.add(g['tarih'])
            else: m.tatiller.discard(g['tarih'])
        elif kod in ('GUN.KALDIRDIM', 'TATIL.KALDIRDIM'):
            m.gun_tanimlari.pop(g['tarih'], None); m.tatiller.discard(g['tarih'])
        elif kod == 'TATIL.EKLEDIM':
            m.gun_tanimlari.pop(g['tarih'], None); m.tatiller.add(g['tarih'])
        if kod in ('EK_MESAI.PLANLADIM', 'EK_MESAI.ONAYLADIM'):
            m.ek_mesai_planlari[oid] = dict(deepcopy(g), kimlik=oid, damga=kod.endswith('ONAYLADIM'), hedef=deepcopy(e['neyin_ustunde']), iptal=False)
        elif kod == 'EK_MESAI.IPTAL_ETTIM' and g['hedef'] in m.ek_mesai_planlari:
            m.ek_mesai_planlari[g['hedef']]['iptal'] = True
        elif kod in ('IS.ATADIM', 'GOREV.ATADIM'):
            for n, s in enumerate(g.get('gorevler', [g]), 1):
                if not s.get('ek_mesai'): continue
                for k in s.get('kisiler', [s.get('kisi')]):
                    kimlik = oid + '/ek/' + str(n) + '/' + k
                    hedef = [dict(tur='GOREV', kimlik=oid+'/'+str(n))] if kod.startswith('GOREV') else e['neyin_ustunde']
                    m.ek_mesai_planlari[kimlik] = dict(deepcopy(s['ek_mesai']), kimlik=kimlik, kisi=k, damga=False, hedef=deepcopy(hedef), iptal=False)
        if kod == 'IZIN.TALEP_ETTIM':
            m.izinler[oid] = dict(deepcopy(g), kimlik=oid, durum='TALEP', olay=e)
        elif kod.startswith('IZIN.') and g.get('hedef') in m.izinler:
            x = m.izinler[g['hedef']]
            if kod == 'IZIN.ONAYLADIM':
                x.update(durum='IK_BEKLIYOR' if m.ayar('izin_ik_onayi', an(e['oldugu_an']), {}).get(x['tur'], False) else 'ONAYLI', onaylayan=e['kim'])
            elif kod == 'IZIN.IK_ONAYLADIM': x['durum'] = 'ONAYLI'
            elif kod == 'IZIN.REDDETTIM': x.update(durum='RET' if x['durum']=='IK_BEKLIYOR' else 'REDDEDILDI', gerekce=g['gerekce'])
            elif kod == 'IZIN.IPTAL_ETTIM': x['durum'] = 'IPTAL'


def sistem_noktalari(m, sinir):
    noktalar = set()
    for x in m.ek_mesai_planlari.values():
        if x.get('iptal'): continue
        a, b = pencere(x)
        # Pencere bitisindeki taniklik once; normal PAYDOS'un sirasi korunur.
        noktalar.add((b, 2, 'V7_EK_BITIS', None))
    for x in m.izinler.values():
        if x['durum'] != 'ONAYLI': continue
        a, b = an(x['baslangic']), an(x['bitis'])
        for tarih in gunler(a, min(b, sinir)):
            for bas, bit in normal(m, tarih, False, x['kisi']):
                p, q = max(a, bas), min(b, bit)
                if p < q:
                    noktalar.add((p, 0, 'V7_IZIN', None)); noktalar.add((q, 0, 'V7_IZIN', None))
    return [x for x in noktalar if x[0] <= sinir]


def kesinti(m, kisi, t):
    for a, b in izinler(m, kisi):
        if a <= t < b and normal(m, t.date(), False, kisi) and normal(m, t.date(), False, kisi)[0][0] <= t < normal(m, t.date(), False, kisi)[0][1]: return ('IZIN', None)
    for x in m.duruslar.values():
        if x['baslangic'] <= t and (not x['bitis'] or t < x['bitis']) and kapsamda(m, kisi, x['kapsam']): return ('BEKLEME_DURUS', x['neden'])
    return None


def katman_guncelle(m, t):
    from .kisi_gunu import bos_hal, hal_yaz
    from .yetki_v6 import istihdamda
    for kisi in set(m.kisi_durumu) | {x['kisi'] for x in m.izinler.values() if x['durum'] == 'ONAYLI'}:
        d = m.kisi_durumu.setdefault(kisi, bos_hal())
        if not istihdamda(m,kisi,t): continue
        hedef = kesinti(m, kisi, t)
        if hedef and hedef[0] != 'IZIN' and d['durum'] == 'MESAI_DISI': continue
        # Sabit mola durustan ustundur, izin sabit moladan ustundur.
        if hedef and hedef[0] == 'BEKLEME_DURUS' and m.sabit_molada(t,kisi):
            hedef = ('SABIT_MOLA', None)
        if hedef:
            if '_kesinti_onceki' not in d:
                once = deepcopy(d['mola_onceki'] if d['durum'] == 'SABIT_MOLADA' else d)
            else: once = deepcopy(d['_kesinti_onceki'])
            yeni = dict(d, durum='IZINLI' if hedef[0] == 'IZIN' else 'DURUSTA', kova=hedef[0], aralik_is=None, neden=hedef[1], _kesinti_onceki=once)
            hal_yaz(m, kisi, yeni, t, kural='T8_KESINTI')
        elif '_kesinti_onceki' in d:
            yeni = deepcopy(d['_kesinti_onceki'])
            if yeni['durum'] in ('CALISIYOR', 'MOLADA', 'DEVAM_BEKLIYOR'):
                yeni.update(durum='DEVAM_BEKLIYOR' if yeni['acik_is'] else 'CALISMIYOR', kova='TANIMSIZ', aralik_is=None, neden=None)
            hal_yaz(m, kisi, yeni, t, kural='T8_KESINTI')


def sistem_isle(m, kod, t):
    from .kisi_gunu import uygula
    if kod in ('MOLA_BASI', 'MOLA_SONU'):
        for kisi, d in list(m.kisi_durumu.items()):
            if d['durum'] == 'MESAI_DISI' or '_kesinti_onceki' in d: continue
            from .takvim_v9 import nokta_kisiye_ait
            if not nokta_kisiye_ait(m,kisi,kod,t): continue
            uygula(m, kisi, kod, t)
        katman_guncelle(m, t)
        return
    if kod == 'V7_IZIN': katman_guncelle(m, t); return
    for kisi, d in list(m.kisi_durumu.items()):
        if d['durum'] == 'MESAI_DISI': continue
        from .takvim_v9 import nokta_kisiye_ait
        if not nokta_kisiye_ait(m,kisi,kod,t): continue
        if any(a <= t < b for a, b in ekler(m, kisi, gercek=True)): continue
        if kod == 'V7_EK_BITIS' and not any(b == t for a, b in ekler(m, kisi, gercek=True)): continue
        eski = d['acik_is']
        uygula(m, kisi, 'PAYDOS', t)
        m.kisi_durumu[kisi].pop('_kesinti_onceki', None)
        if eski and m.isler[eski]['durum'] == 'CALISILIYOR': m.isler[eski]['durum'] = 'YARIM'


def aralik_ekle(m, kisi, d, bitis, e, kural, sistem):
    """V6 araligini gercek kisi mesaisine kirp, gun/katsayi sinirinda bol."""
    i = m.isler.get(d['aralik_is'], {})
    bas, son = d['baslangic'], min(bitis or m.saat.simdi(), m.saat.simdi())
    for tarih in gunler(bas, son):
        from .yetki_v6 import istihdamda
        if kisi in m.kisiler and not istihdamda(m,kisi,tarih): continue
        normal_p = normal(m, tarih, False, kisi)
        ek_p = ekler(m, kisi, tarih, True)
        for x, y in birlesim(normal_p + ek_p):
            x, y = max(x, bas), min(y, son)
            if x >= y: continue
            sinirlar = sorted({x, y} | {z for p in normal_p + ek_p for z in p if x < z < y})
            for a, b in zip(sinirlar, sinirlar[1:]):
                fm = d['kova'] in ('CALISMA', 'YENIDEN_ISLEME') and any(p <= a and b <= q for p, q in ek_p)
                acik = bitis is None and b == son and not any(b == q for p, q in birlesim(normal_p+ek_p))
                m.araliklar.append(dict(kisi=kisi, gun=tarih, baslangic=a, bitis=None if acik else b, kova=d['kova'], **{'is':d['aralik_is']}, proje=i.get('proje'), kategori=i.get('kategori'), tezgah=None, neden=d['neden'], plansiz=i.get('plansiz',False), sistem_kapatti=sistem, elle=False, aciklama=None, yazan=None, acan_olay=d['acan_olay'], kapatan_olay=e['olay_kimligi'] if e else None, acan_kural=d['acan_kural'], kapatan_kural=kural, kural_versiyonu=1, fazla_mesai=fm, katsayi=katsayi(m,tarih) if fm else 1))
