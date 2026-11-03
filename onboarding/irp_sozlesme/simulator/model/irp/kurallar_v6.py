"""Karar 57-61: veri kapilari ve olaylardan uretilen ana veri."""
from copy import deepcopy
from datetime import timedelta
from .saat import an, gun
from .olay import EYLES, hedefler
from .yetki_v6 import istihdamda, yoneticiler, simdi


def kod_aktif(d, liste, kod):
    return d.kod_listesi.get(liste + ':' + str(kod), {}).get('aktif', False)


def yetkili_kalir(d, e):
    """Planlanmis terfilerin tum sinirlarinda en az bir istihdamli yetkili."""
    es = list(d.olaylar.values()) if hasattr(d.olaylar, 'values') else list(d.olaylar)
    es = [x for x in es if x['eylem_kodu'].startswith('KISI.') and x['olay_kimligi'] != e['olay_kimligi']
          and (not getattr(d, '_an', None) or (an(x['oldugu_an']), x['olay_kimligi']) < (an(e['oldugu_an']), e['olay_kimligi']))] + [e]
    roller, donemler, sinirlar = {}, {}, {simdi(d)}
    for x in sorted(es, key=lambda x: (an(x['oldugu_an']), x['olay_kimligi'])):
        g, kod = x['girdiler'], x['eylem_kodu']; k = g.get('kisi') or g.get('kod')
        if kod == 'KISI.EKLEDIM':
            donemler.setdefault(k, []).append([gun(g['giris_tarihi']), None])
            roller.setdefault(k, []).append((an(g['giris_tarihi']), x['olay_kimligi'], g['roller']))
            sinirlar.add(an(g['giris_tarihi']))
        elif kod == 'KISI.AYRILDI' and donemler.get(k):
            tarih = None if g.get('iptal') else gun(g['ayrilis_tarihi'])
            donemler[k][-1][1] = tarih
            if tarih: sinirlar.add(an(str(tarih + timedelta(days=1))))
        elif kod == 'KISI.DEGISTIRDIM' and 'roller' in g['degisenler']:
            t = an(g['gecerli_baslangic']); sinirlar.add(t)
            roller.setdefault(k, []).append((t, x['olay_kimligi'], g['degisenler']['roller']))
    for t in sorted(x for x in sinirlar if x >= simdi(d)):
        sayi = 0
        for k, rs in roller.items():
            uygun = [r for r in rs if r[0] <= t]
            if uygun and 'YETKILI' in max(uygun) [2] and any(a <= t.date() and (b is None or t.date() <= b) for a, b in donemler.get(k, [])): sayi += 1
        if not sayi: return False
    return True


def kapilar(d, e):
    """None: eski kapi uygulanir; bool: bu surumun kapisi sonuctur."""
    from .kapilar_v5 import aktif_kisi, proje_etap
    kod, g, t = e['eylem_kodu'], e['girdiler'], an(e['oldugu_an'])
    if kod in ('KISI.EKLEDIM', 'KISI.DEGISTIRDIM'):
        if kod == 'KISI.EKLEDIM':
            once = d.kisiler.get(g['kod'])
            if once and (not once.get('ayrilis_tarihi') or gun(once['ayrilis_tarihi']) >= t.date() or gun(g['giris_tarihi']) <= gun(once['ayrilis_tarihi'])): return False
            s = g
        else:
            if not aktif_kisi(d, g['kisi']) or an(g['gecerli_baslangic']) < t: return False
            if set(g['degisenler']) - {'ad', 'birim', 'yaka', 'roller'}: return False
            s = dict(d.kisiler[g['kisi']], **g['degisenler'])
            if 'roller' in g['degisenler'] and not yetkili_kalir(d, e): return False
        return s.get('birim') in d.birimler and s.get('yaka') in ('MAVI', 'BEYAZ') and bool(s.get('roller')) and all(kod_aktif(d, 'ROL', r) for r in s['roller'])
    if kod == 'KISI.AYRILDI':
        k = g['kisi']; p = d.kisiler.get(k, {})
        if not p: return False
        if p.get('ayrilis_tarihi'):
            if t.date() >= gun(p['ayrilis_tarihi']): return False
            if g.get('iptal'): return True
        elif g.get('iptal'): return False
        return (gun(g['ayrilis_tarihi']) >= max(t.date(), gun(p['giris_tarihi'])) and not d.listeler.get(k)
                and not any(x['durum'] not in ('BITTI', 'IPTAL') and k in (x.get('kisi'), x.get('onaylayan')) for x in d.gorevler.values())
                and not any(x.get('basi') == k for x in d.birimler.values())
                and not any(k in ks for ks in d.yonlendirme.values()) and yetkili_kalir(d, e))
    if kod == 'IS.BAGLANTI_DUZELTTIM':
        i = d.isler.get(hedefler(e, 'IS')[0], {})
        s = dict(i, **g['degisenler'])
        return bool(i) and i['durum'] != 'IPTAL' and s.get('nereye') in ('PROJE', 'PROJE_DISI') and proje_etap(d, s) and (s.get('nereye') != 'PROJE_DISI' or kod_aktif(d, 'PD', s.get('kategori')))
    if kod == 'IS.IPTAL_ETTIM': return d.isler.get(hedefler(e, 'IS')[0], {}).get('durum') not in (None, 'IPTAL')
    if kod == 'YETKI.TANIMLADIM':
        return (g['eylem_kodu'] in EYLES or g['eylem_kodu']=='PROJE.HEPSINI_GORUR') and g['kapsam'] in ('BIRIM', 'FIRMA') and all(r in ('BIRIM_YONETICISI', 'BIRIM_BASI','BIRIM_UYESI','PROJE_SORUMLUSU') or kod_aktif(d, 'ROL', r) for r in g['kimler'])
    if kod == 'KOD.TANIMLADIM':
        if g['liste'] == 'ROL' and g['kod'] == 'YETKILI' and not g['aktif']: return False
        return True
    if kod == 'TATIL.KALDIRDIM': return g['tarih'] in d.tatiller and gun(g['tarih']) > t.date()
    if kod == 'KURULUM.TAMAMLADIM': return False
    satirlar = g.get('gorevler', g.get('isler', []))
    if kod == 'IS.PLANSIZ_TANIMLADIM': satirlar = [g]
    if kod in ('GOREV.DEGISTIRDIM', 'IS.DEGISTIRDIM'):
        alanlar = g['degisenler']
        satirlar = [alanlar] if 'kategori' in alanlar else []
    if any(s.get('nereye') == 'PROJE_DISI' and not kod_aktif(d, 'PD', s.get('kategori')) for s in satirlar): return False
    return None


def ana_veri(m, e):
    kod, g, t = e['eylem_kodu'], deepcopy(e['girdiler']), an(e['oldugu_an'])
    if kod == 'KOD.TANIMLADIM': m.kod_listesi[g['liste'] + ':' + g['kod']] = g
    elif kod == 'YETKI.TANIMLADIM':
        for r in m.yetki_kurallari:
            if r['eylem_kodu'] == g['eylem_kodu'] and not r.get('gecerli_bitis'): r['gecerli_bitis'] = t
        m.yetki_kurallari.append(dict(g, gecerli_baslangic=t, gecerli_bitis=None, doguran_olay=e['olay_kimligi']))
    elif kod == 'KURULUM.TAMAMLADIM': m.kurulum_kaynagi = e['olay_kimligi']
    elif kod == 'TATIL.KALDIRDIM': pass  # takvim bastan, acik gunleri yeniden boler
    elif kod == 'KISI.EKLEDIM':
        once = m.kisiler.get(g['kod'], {})
        donemler = deepcopy(once.get('istihdam_donemleri', []))
        if once:
            for r in m.kisi_gecmisi:
                if r['kisi'] == g['kod'] and r['gecerli_bitis'] is None: r['gecerli_bitis'] = g['giris_tarihi']
        donemler.append({'giris': g['giris_tarihi'], 'ayrilis': None})
        m.kisiler[g['kod']] = dict(g, ayrilis_tarihi=None, istihdam_donemleri=donemler)
        m.kisi_gecmisi.append(dict(g, kisi=g['kod'], gecerli_baslangic=g['giris_tarihi'], gecerli_bitis=None))
        if e['giris_sekli'] != 'AKTARIM':
            for k in sorted(yoneticiler(m, g['birim']) - {g['kod']}): m.bildir(e, 'R28', k, t, g['kod'])
    elif kod == 'KISI.AYRILDI':
        p = m.kisiler[g['kisi']]
        p['ayrilis_tarihi'] = None if g.get('iptal') else g['ayrilis_tarihi']
        p['istihdam_donemleri'][-1]['ayrilis'] = p['ayrilis_tarihi']
        alicilar = yoneticiler(m, p['birim']) | {k for k, x in m.kisiler.items() if 'YETKILI' in x.get('roller', []) and istihdamda(m, k, t)}
        if e['giris_sekli'] != 'AKTARIM':
            for k in sorted(alicilar): m.bildir(e, 'R29', k, t, g['kisi'])
    else: return False
    return True


def baglantilari_yansit(m):
    for a in m.araliklar:
        i = m.isler.get(a['is'], {})
        if i:
            for alan in ('proje', 'kategori', 'parca_kodu'): a[alan] = i.get(alan)
            a['is_iptal'] = i['durum'] == 'IPTAL'
    for g in m.gorevler.values():
        if g.get('teslim_tarihi') and not g.get('teslim_saati'):
            g['takvim_teslim_saati'] = m.takvim(g['teslim_tarihi'],g.get('kisi'))['mesai_bitis']


def not_alicisi_ayrilmis(m, kisi, e):
    """C38: gec gelen notun alicisi, not buluta geldiginde ayrilisi kayitli olabilir.

    Olay zamanindaki yonlendirme korunur; kabulden once bilinen son istihdam
    karari kullanilir. Ulasma ani esitse kaynak kabul sirasi baglayicidir;
    gec notun eski olay ani daha once kabul edildigi anlamina gelmez.
    """
    if e['giris_sekli'] == 'AKTARIM': return bool(m.kisiler.get(kisi, {}).get('ayrilis_tarihi'))
    def sira(x): return (an(x.get('bulut_ulasma_ani', x['oldugu_an'])), m._kabul_sirasi[x['olay_kimligi']])
    ilgili = [x for x in m.olaylar if sira(x) < sira(e)
              and (x['eylem_kodu'] == 'KISI.EKLEDIM' and x['girdiler']['kod'] == kisi
                   or x['eylem_kodu'] == 'KISI.AYRILDI' and x['girdiler']['kisi'] == kisi)]
    ayrildi = False
    for x in sorted(ilgili, key=sira):
        ayrildi = x['eylem_kodu'] == 'KISI.AYRILDI' and not x['girdiler'].get('iptal', False)
    return ayrildi
