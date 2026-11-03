"""A7/A10: görevler, ret, onay ve revizyon zinciri."""
from copy import deepcopy
from math import floor
from .saat import an, gun_ani
from .olay import hedefler


def son_teslim_ani(g, m=None):
    saat = m.takvim(g['teslim_tarihi'],g.get('kisi'))['mesai_bitis'] if m and g.get('teslim_tarihi') else g.get('takvim_teslim_saati', '18:00')
    return gun_ani(g['teslim_tarihi'], g.get('teslim_saati') or saat) if g.get('teslim_tarihi') else None


def puan(g):
    if g['durum'] != 'BITTI':
        return None
    if g['tur'] == 'NOT':
        return 0
    if g['tur'] in ('REVIZYON','DEGISIKLIK') and g.get('sorumlulugu_dogrulandi', False):
        return None
    return g['zaman_degeri'] * (1 if g['tur'] == 'ONAY' else g['zorluk'])


def gorev_dogur(m, e, satir, kimlik, tur='NORMAL'):
    g = dict(deepcopy(satir), kimlik=kimlik, tur=tur, doguran_olay=e['olay_kimligi'], son_olay=e['olay_kimligi'], kural_versiyonu=1, atama_ani=e['oldugu_an'], veren=e['kim'], durum='ACIK' if tur == 'ONAY' else 'ATANDI', kabul_ani=None, ilk_teslim_ani=None, teslim_ani=None, onay_ani=None, bitis_ani=None, is_puani=None)
    g.setdefault('on_kosul', [])
    g.setdefault('onay_gerekli', False)
    g.setdefault('dosya_gerekli', False)
    g.setdefault('zorluk', 1)
    g['kisi_gecmisi'] = [{'kisi':g.get('kisi'), 'baslangic':e['oldugu_an']}]
    g['ilk_kabul_ani'] = None
    g['iptal_ani'] = None
    g['on_kosul'] = [e['olay_kimligi'] + '/' + str(x['satir']) if isinstance(x, dict) else x for x in g['on_kosul']]
    m.gorevler[kimlik] = g
    return g


def kapi(m, g, e):
    kod, d = e['eylem_kodu'], g['durum']
    from .yetki_v6 import ustler
    yapan_uygun = (e.get('adina') or e['kim']) == g['kisi'] or e['kim'] in ustler(m, g['kisi'])
    if kod == 'GOREV.KABUL_ETTIM':
        return d == 'ATANDI' and yapan_uygun
    if kod == 'GOREV.TAMAMLADIM':
        return d in ('ACIK', 'REDDEDILDI') and yapan_uygun and (not g['dosya_gerekli'] or bool(e['kanit']))
    if kod in ('GOREV.ONAYLADIM', 'GOREV.REDDETTIM'):
        return d == 'ONAY_BEKLIYOR'
    if kod in ('GOREV.DEGISTIRDIM', 'GOREV.IPTAL_ETTIM'):
        return d not in ('BITTI', 'IPTAL')
    return True


def bagimliliklari_hesapla(m):
    # Değer değişimi; sürüm yalnız tamamlanan yayında artırılır (B28).
    for tur in range(1,51):
        degisti=False
        for kimlik in sorted(m.gorevler):
            g=m.gorevler[kimlik]; once=deepcopy(g)
            asil=m.gorevler.get(g.get('kaynak'),{})
            if g['tur'] in ('ONAY','REVIZYON') and asil.get('durum')=='IPTAL' and g['durum'] not in ('BITTI','IPTAL'):
                g.update(durum='IPTAL',iptal_ani=asil.get('iptal_ani'))
            if g['durum'] in ('ACIK','ON_IS_BEKLIYOR'):
                g['durum']='ON_IS_BEKLIYOR' if any(m.gorevler.get(x,m.isler.get(x,{})).get('durum') not in ('BITTI', 'IPTAL') for x in g['on_kosul']) else 'ACIK'
            rev=m.gorevler.get(g.get('revizyon_gorevi'),{})
            if g['durum']=='REVIZYONDA' and rev.get('durum')=='BITTI':
                g.update(durum='BITTI',onay_ani=rev['onay_ani'],bitis_ani=rev['bitis_ani'])
            elif g['durum']=='REVIZYONDA' and rev.get('durum')=='IPTAL': g['durum']='REDDEDILDI'
            g['is_puani']=puan(g)
            degisti=degisti or once!=g
        if not degisti:
            m.yakinsama_turlari.append(tur); return
    m.yakinsama_turlari.append(50); m.islenemedi=True
    m.motor_hatalari.append({'hata':'yakinsamadi','kirli':sorted(m.gorevler)})


def bekletme_kayitlari(m,t):
    # Bir sonraki olaydan önce de çağrılır: kapanan bekleme geçmişi kaybolmaz.
    for g in m.gorevler.values():
        if g['durum']!='ON_IS_BEKLIYOR': continue
        for p in g['on_kosul']:
            on=m.gorevler.get(p,{})
            son=son_teslim_ani(on, m)
            if son and t>son and on.get('durum') not in ('BITTI', 'IPTAL'):
                k=p+':'+g['kimlik']
                m.bekletmeler.setdefault(k,{'geciktiren':on['kisi'],'on_kosul':p,'bekleyen':g['kimlik'],'an':max(son,an(g['kabul_ani']))})


def gorev_isle(m, e):
    kod, girdiler = e['eylem_kodu'], e['girdiler']
    bekletme_kayitlari(m,an(e['oldugu_an']))
    if kod == 'GOREV.ATADIM':
        for n, satir in enumerate(girdiler['gorevler'], 1):
            if satir['kisi'] == e['kim']:
                m.supheli(e, 'Kendine gorev')
            gorev_dogur(m, e, satir, e['olay_kimligi'] + '/' + str(n))
        return
    for kimlik in hedefler(e, 'GOREV'):
        if kimlik not in m.gorevler:
            m.supheli(e, 'Hedef gorev yok'); continue
        g = m.gorevler[kimlik]
        if not kapi(m, g, e):
            m.supheli(e, 'Gorev kapisi kapali')
            ortuk = kod == 'GOREV.TAMAMLADIM' and g['durum'] == 'ATANDI' and g['kisi'] == e['kim']
            if not ortuk: continue
        once = g['durum']
        t = e['oldugu_an']
        if kod == 'GOREV.KABUL_ETTIM':
            g['kabul_ani'] = t
            g['ilk_kabul_ani'] = g['ilk_kabul_ani'] or t
            g['durum'] = 'BITTI' if g['tur'] == 'NOT' else 'ACIK'
            if g['durum'] == 'BITTI': g['bitis_ani'] = t
        elif kod == 'GOREV.TAMAMLADIM':
            if g['durum'] == 'ATANDI':
                g['kabul_ani'] = t
                g['ilk_kabul_ani'] = g['ilk_kabul_ani'] or t
            g['ilk_teslim_ani'] = g['ilk_teslim_ani'] or t
            g['teslim_ani'] = t
            g['durum'] = 'ONAY_BEKLIYOR' if g['onay_gerekli'] else 'BITTI'
            if g['onay_gerekli']:
                oran = m.ayar('onay_orani', an(t), 0.1)
                satir = dict(g, ad='Onay: ' + g['ad'], kisi=g['onaylayan'], kaynak=kimlik, zaman_degeri=floor(g['zaman_degeri'] * oran + 1e-12), teslim_tarihi=None, teslim_saati=None, onay_gerekli=False, dosya_gerekli=False, on_kosul=[], zorluk=1)
                gorev_dogur(m, e, satir, e['olay_kimligi'], 'ONAY')
            else: g['bitis_ani'] = t
        elif kod in ('GOREV.ONAYLADIM', 'GOREV.REDDETTIM'):
            for onay in list(m.gorevler.values()):
                if onay['tur'] == 'ONAY' and onay.get('kaynak') == kimlik and onay['durum'] not in ('BITTI','IPTAL'):
                    if e['kim'] == g.get('onaylayan'):
                        onay.update(durum='BITTI', onay_ani=t, bitis_ani=t, son_olay=e['olay_kimligi'])
                    else:
                        onay.update(durum='IPTAL', iptal_ani=t, is_puani=None, son_olay=e['olay_kimligi'])
            if kod == 'GOREV.ONAYLADIM':
                g.update(durum='BITTI', onay_ani=t, bitis_ani=t)
            else:
                g['durum'] = 'REVIZYONDA' if girdiler['revizyon_ver'] else 'REDDEDILDI'
                m.retler.append({'olay': e['olay_kimligi'], 'gorev': kimlik, 'an': t, **deepcopy(girdiler)})
                if girdiler['revizyon_ver']:
                    rev_id = e['olay_kimligi'] + '/1'
                    satir = dict(g, ad='Revizyon: ' + g['ad'], kisi=girdiler['kime'], kaynak=kimlik, zaman_degeri=girdiler['zaman_degeri'], teslim_tarihi=girdiler['yeni_teslim_tarihi'], sebep_olan=girdiler.get('sebep_olan'), revizyon_gorevi=None, on_kosul=[])
                    gorev_dogur(m, e, satir, rev_id, 'REVIZYON')
                    g['revizyon_gorevi'] = rev_id
        elif kod == 'GOREV.DEGISTIRDIM':
            kisi = g['kisi']
            onaylayan=g.get('onaylayan')
            g.update(deepcopy(girdiler['degisenler']))
            if g['kisi'] != kisi:
                g['durum'] = 'ATANDI'
                g['kisi_gecmisi'].append({'kisi':g['kisi'],'baslangic':t})
            if g.get('onaylayan')!=onaylayan:
                for onay in list(m.gorevler.values()):
                    if onay['tur']=='ONAY' and onay.get('kaynak')==kimlik and onay['durum'] not in ('BITTI','IPTAL'):
                        onay.update(durum='IPTAL',iptal_ani=t)
                        satir=dict(onay,kisi=g['onaylayan'])
                        # Karar 49 / A10: degisiklik olayinin ilk cocugu.
                        gorev_dogur(m,e,satir,e['olay_kimligi']+'/1','ONAY')
        elif kod == 'GOREV.IPTAL_ETTIM':
            g['durum'] = 'IPTAL'
            g['iptal_ani'] = t
        g['son_olay'] = e['olay_kimligi']
        m.sonuc(e, 'R15', kimlik, once, g['durum'])
    bagimliliklari_hesapla(m)
