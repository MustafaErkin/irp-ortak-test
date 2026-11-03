"""Karar 53/55: kisi beklemesi ile is onayinin ayrilmasi."""
from copy import deepcopy
from .saat import an
from .olay import hedefler
from .liste import yerlestir


def listeden_cikar(m, i):
    sahipler = []
    for k, liste in m.listeler.items():
        if i['kimlik'] in liste:
            sahipler.append((k, liste[0]))
            liste.remove(i['kimlik'])
    # V4'te kisi/sira biten iste saklaniyordu; yeni beklemesiz onayda
    # teslim edenin kimligi tamamlayan alanindadir.
    i['kisi'] = None
    i['sira'] = None
    return sahipler


def isle(m, e):
    from .kisi_gunu import (uygula, kapi, bos_hal, isleri_guncelle,
                            ana_isleri_guncelle, hal_yaz)
    kod, g, t = e['eylem_kodu'], e['girdiler'], an(e['oldugu_an'])
    ids = hedefler(e, 'IS')
    i = m.isler.get(ids[0]) if ids else None
    if not i: return False
    if kod == 'IS.BAGLANTI_DUZELTTIM':
        for x in [i] + [x for x in m.isler.values() if x.get('ana_is') == i['kimlik']]:
            x.update(deepcopy(g['degisenler']))
        return True
    if kod == 'IS.IPTAL_ETTIM':
        altlar = [i] + [x for x in m.isler.values() if x.get('ana_is') == i['kimlik']]
        for x in altlar:
            if x['durum'] == 'IPTAL': continue
            x.update(iptal_oncesi_durum=x['durum'], iptal_eden=e['kim'], iptal_oncesi_bitis_ani=x.get('bitis_ani'))
            x.update(durum='IPTAL', iptal_ani=t, iptal_gerekcesi=g['gerekce'], bitis_ani=None, acik_ariza=None)
            for k, eski_bas in listeden_cikar(m, x):
                h = m.kisi_durumu.get(k, bos_hal())
                once = h.get('mola_onceki') if h['durum'] == 'SABIT_MOLADA' else h
                if once and once['durum'] == 'ONAY_BEKLIYOR' and once.get('aralik_is') == x['kimlik']:
                    uygula(m, k, 'IS.ONAYLADIM', t, e, x)
                    if not m.listeler.get(k): m.bildir(e, 'R08', x['atayan'], t, k)
                elif eski_bas == x['kimlik']:
                    uygula(m, k, 'LISTE_DEGISTI', t, e, x)
        isleri_guncelle(m, t, e); ana_isleri_guncelle(m)
        from .gorev import bagimliliklari_hesapla
        bagimliliklari_hesapla(m)
        return True
    if kod == 'IS.DEGISTIRDIM':
        onceki = {k: m.isler[l[0]].get('kilitli', False) for k, l in m.listeler.items() if l}
        alanlar = deepcopy(g['degisenler'])
        altlar = [x for x in m.isler.values() if x.get('ana_is') == i['kimlik']]
        i.update(alanlar)
        for alt in altlar: alt.update(alanlar)
        if altlar and 'tahmini_sure_dk' in alanlar: i['tahmini_sure_dk'] *= i['kisi_sayisi']
        isleri_guncelle(m, t, e)
        for k, kilitli in onceki.items():
            bas = m.isler[m.listeler[k][0]]
            if not kilitli and bas.get('kilitli'): uygula(m, k, 'LISTE_DEGISTI', t, e, bas)
        return True
    if i.get('onay_beklet') or not i.get('onay_gerekli'): return False
    if kod in ('IS.TAMAMLADIM', 'ELLE_BITIS'):
        k = e.get('adina') or e['kim']
        h = m.kisi_durumu.get(k, bos_hal())
        liste = m.listeler.get(k, [])
        uygun = kod == 'ELLE_BITIS' or kapi(h, kod, i, liste[0] if liste else None, m.sabit_molada(t))
        if not uygun: m.supheli(e, 'Calisan kapisi kapali')
        if i['durum'] not in ('SIRADA', 'YARIM', 'CALISILIYOR', 'REDDEDILDI'): return True
        i.update(durum='ONAY_BEKLIYOR', bitis_ani=None, tamamlayan=k, onay_bekleme_ani=t, acik_ariza=None)
        sahipler = listeden_cikar(m, i)
        # Kapi disi sabit mola ve elle bitis: yalniz bu isin aktif halini temizle.
        for sahibi, eski_bas in sahipler:
            h = m.kisi_durumu.get(sahibi, bos_hal())
            once = h.get('mola_onceki') if h['durum'] == 'SABIT_MOLADA' else h
            if once and (once.get('acik_is') == i['kimlik'] or (uygun and kod != 'ELLE_BITIS' and eski_bas == i['kimlik'])):
                gecis_isi = dict(i, onay_gerekli=False)
                uygula(m, sahibi, 'IS.TAMAMLADIM', t, e, gecis_isi)
            if not m.listeler.get(sahibi): m.bildir(e, 'R08', i['atayan'], t, sahibi)
        m.bildir(e, 'R05', i['atayan'], t, k)
        isleri_guncelle(m, t, e); ana_isleri_guncelle(m)
        return True
    if kod == 'IS.ONAYLADIM':
        i.update(durum='BITTI', bitis_ani=t)
        isleri_guncelle(m, t, e); ana_isleri_guncelle(m)
        return True
    if kod == 'IS.REDDETTIM':
        i['durum'] = 'REDDEDILDI'
        k = i.get('tamamlayan')
        if k and not m.kisiler.get(k, {}).get('ayrilis_tarihi'):
            liste = m.listeler.setdefault(k, [])
            eski = liste[0] if liste else None
            yerlestir(liste, i['kimlik'], 2 if liste else 1)
            if eski != liste[0]: uygula(m, k, 'LISTE_DEGISTI', t, e, i)
        isleri_guncelle(m, t, e); ana_isleri_guncelle(m)
        return True
    return False
