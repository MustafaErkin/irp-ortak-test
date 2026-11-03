"""A8: kronolojik saf geçişler, mola katmanı ve A8b aralık kesişimi."""
from copy import deepcopy
from .saat import an, gun_ani
from .olay import hedefler
from .liste import yerlestir

CALISAN = {'MESAI.GIRDIM', 'MESAI.CIKTIM', 'IS.BASLADIM', 'IS.MOLA_VERDIM', 'IS.ARIZA_BILDIRDIM', 'IS.DEVAM_ETTIM', 'IS.TAMAMLADIM'}
KISISEL = {'MOLA', 'GECIS', 'TANIMSIZ', 'SABIT_MOLA'}


def bos_hal():
    return {'durum': 'MESAI_DISI', 'kova': None, 'acik_is': None, 'aralik_is': None, 'neden': None, 'onceki_kova': 'CALISMA', 'devam_izni': False, 'mola_onceki': None, 'baslangic': None, 'acan_olay': None, 'acan_kural': None, 'son_olay_ani': None}


def kapi(d, kod, is_, bas, sabit=False):
    if sabit and kod in CALISAN: return False
    durum = d['durum']
    if kod == 'MESAI.GIRDIM': return durum == 'MESAI_DISI'
    if kod == 'MESAI.CIKTIM': return durum != 'MESAI_DISI'
    if not is_: return False
    ayni = d['acik_is'] == is_['kimlik']
    if kod == 'IS.BASLADIM':
        return durum == 'CALISMIYOR' and bas == is_['kimlik'] and is_['tur'] == 'SURELI' and is_['durum'] in ('SIRADA', 'YARIM') and not is_.get('kilitli', False)
    if kod == 'IS.MOLA_VERDIM': return durum == 'CALISIYOR' and ayni
    if kod == 'IS.ARIZA_BILDIRDIM':
        return (durum == 'CALISIYOR' and ayni) or (is_['tur'] == 'ANLIK' and bas == is_['kimlik'] and durum != 'MESAI_DISI')
    if kod == 'IS.DEVAM_ETTIM':
        if is_['durum'] == 'BITTI': return False
        return (ayni and (durum in ('MOLADA', 'DEVAM_BEKLIYOR') or (durum == 'ARIZADA' and d['devam_izni']))) or (durum == 'CALISMIYOR' and bas == is_['kimlik'] and is_['durum'] == 'REDDEDILDI')
    if kod == 'IS.TAMAMLADIM':
        return (is_['tur'] == 'SURELI' and ayni and durum in ('CALISIYOR', 'DEVAM_BEKLIYOR')) or (is_['tur'] == 'ANLIK' and durum == 'CALISMIYOR' and bas == is_['kimlik'] and is_['durum'] == 'SIRADA' and not is_.get('kilitli'))
    return True


def gecis(hal, kod, is_=None, bas_is=None, neden=None):
    """Saf A8 geçişi: yan etki kimlikleri döner; depo yazmaz."""
    d = deepcopy(hal)
    yan = []
    def ac(durum, kova, is_kimligi=None):
        d.update(durum=durum, kova=kova, aralik_is=is_kimligi, neden=neden)
    def bosalt():
        d['acik_is'] = None
        if bas_is and bas_is.get('kilitli', bas_is['durum']=='ON_IS_BEKLIYOR'):
            ac('ON_IS_BEKLIYOR', 'BEKLEME_ON_IS', bas_is['kimlik']); yan.append('R04')
        else:
            ac('CALISMIYOR', 'TANIMSIZ')
    if kod == 'MESAI.GIRDIM':
        bosalt()
        if bas_is and bas_is['durum']=='ONAY_BEKLIYOR': ac('ONAY_BEKLIYOR','BEKLEME_ONAY',bas_is['kimlik'])
        elif bas_is and bas_is.get('acik_ariza'):
            d['acik_is']=bas_is['kimlik']; d['devam_izni']=bas_is.get('devam_izni',False); d['onceki_kova']=bas_is.get('calisma_kovasi','CALISMA')
            ac('ARIZADA','BEKLEME_ARIZA',bas_is['kimlik']); d['neden']=bas_is['acik_ariza']
    elif kod in ('MESAI.CIKTIM', 'PAYDOS'):
        ac('MESAI_DISI', None); d['acik_is'] = None
    elif kod == 'MOLA_BASI':
        if d['durum'] != 'MESAI_DISI':
            d['mola_onceki'] = deepcopy(hal)
            ac('SABIT_MOLADA', 'SABIT_MOLA')
    elif kod == 'MOLA_SONU':
        if d['durum'] == 'SABIT_MOLADA':
            once = d['mola_onceki']
            d = deepcopy(once)
            if once['durum'] in ('CALISIYOR', 'MOLADA', 'DEVAM_BEKLIYOR'):
                ac('DEVAM_BEKLIYOR' if once['acik_is'] else 'CALISMIYOR', 'TANIMSIZ')
            d['mola_onceki'] = None
    elif kod == 'IS.BASLADIM':
        d['acik_is'] = is_['kimlik']; d['onceki_kova'] = 'CALISMA'
        ac('CALISIYOR', 'CALISMA', is_['kimlik'])
    elif kod == 'IS.MOLA_VERDIM': ac('MOLADA', 'MOLA')
    elif kod == 'IS.ARIZA_BILDIRDIM':
        d['acik_is'] = is_['kimlik']; d['devam_izni'] = False
        ac('ARIZADA', 'BEKLEME_ARIZA', is_['kimlik']); yan.append('R07')
    elif kod == 'IS.DEVAM_ONAYLADIM': d['devam_izni'] = True
    elif kod == 'IS.DEVAM_ETTIM':
        d['acik_is'] = is_['kimlik']
        if is_['durum'] == 'REDDEDILDI': d['onceki_kova'] = 'YENIDEN_ISLEME'
        if is_['tur'] == 'ANLIK':
            ac('CALISMIYOR', 'TANIMSIZ'); d['acik_is'] = None
        else: ac('CALISIYOR', d['onceki_kova'], is_['kimlik'])
    elif kod == 'IS.TAMAMLADIM':
        if is_['onay_gerekli']:
            d['acik_is'] = None; ac('ONAY_BEKLIYOR', 'BEKLEME_ONAY', is_['kimlik']); yan.append('R05')
        elif is_['tur'] != 'ANLIK': bosalt()
    elif kod == 'IS.ONAYLADIM': bosalt()
    elif kod == 'IS.REDDETTIM':
        d['acik_is'] = None; ac('CALISMIYOR', 'GECIS')
    elif kod == 'LISTE_DEGISTI':
        if d['durum']!='MESAI_DISI' and not bas_is:
            d['acik_is']=None; ac('CALISMIYOR','TANIMSIZ'); yan.append('R08')
        elif d['durum'] in ('CALISIYOR','MOLADA','ARIZADA','DEVAM_BEKLIYOR','ON_IS_BEKLIYOR') and (not bas_is or bas_is['kimlik']!=d['acik_is']):
            d['acik_is']=None
            if bas_is and bas_is.get('kilitli'): ac('ON_IS_BEKLIYOR','BEKLEME_ON_IS',bas_is['kimlik']); yan.append('R04')
            else: ac('CALISMIYOR','GECIS')
            yan.append('R01')
        elif d['durum']=='CALISMIYOR' and bas_is and bas_is.get('kilitli'):
            ac('ON_IS_BEKLIYOR','BEKLEME_ON_IS',bas_is['kimlik']); yan.append('R04')
    elif kod == 'ON_IS_BITTI' and d['durum'] == 'ON_IS_BEKLIYOR': d['durum'] = 'CALISMIYOR'
    return d, yan


def mesaiye_kirp(a, takvim, simdi):
    if a['gun'].isoweekday() not in takvim['calisma_gunleri']:
        return None
    bas = max(a['baslangic'], gun_ani(a['gun'], takvim['mesai_baslangic']))
    son = min(a['bitis'] or simdi, gun_ani(a['gun'], takvim['mesai_bitis']), simdi)
    if son <= bas: return None
    a = dict(a, baslangic=bas)
    a['bitis'] = None if a['bitis'] is None and son == simdi and simdi < gun_ani(a['gun'], takvim['mesai_bitis']) else son
    return a


def hal_yaz(m, kisi, yeni, t, e=None, kural=None, sistem=False, zorla=False):
    eski = m.kisi_durumu.setdefault(kisi, bos_hal())
    degisti = any(eski[x] != yeni[x] for x in ('kova', 'aralik_is', 'neden')) or zorla
    if degisti and eski['kova'] and eski['baslangic']:
        m.aralik_ekle(kisi, eski, t, e, kural, sistem)
    if degisti:
        yeni['baslangic'] = t if yeni['kova'] else None
        yeni['acan_olay'] = e['olay_kimligi'] if e else None
        yeni['acan_kural'] = kural
    m.kisi_durumu[kisi] = yeni


def uygula(m, kisi, kod, t, e=None, is_=None, neden=None):
    d = m.kisi_durumu.setdefault(kisi, bos_hal())
    if '_kesinti_onceki' in d and kod not in ('PAYDOS','MOLA_BASI','MOLA_SONU'):
        once=d['_kesinti_onceki']; m.kisi_durumu[kisi]=once
        uygula(m,kisi,kod,t,e,is_,neden)
        d['_kesinti_onceki']=m.kisi_durumu[kisi]; d['acik_is']=m.kisi_durumu[kisi]['acik_is']
        m.kisi_durumu[kisi]=d
        return
    liste = m.listeler.get(kisi, [])
    bas_is = m.isler.get(liste[0]) if liste else None
    # Lider olayları molanın görünmeyen önceki durumuna uygulanır.
    if d['durum'] == 'SABIT_MOLADA' and kod not in ('MOLA_SONU', 'PAYDOS', 'MOLA_BASI'):
        once, yan = gecis(d['mola_onceki'], kod, is_, bas_is, neden)
        yeni = deepcopy(d); yeni['mola_onceki'] = once
        yeni['acik_is'] = once['acik_is']
    else:
        yeni, yan = gecis(d, kod, is_, bas_is, neden)
    kural = 'R03' if kod.startswith('MOLA_') else 'R13' if kod == 'PAYDOS' else 'R02'
    hal_yaz(m, kisi, yeni, t, e, kural, kod == 'PAYDOS')
    for k in yan:
        if k != 'R01': m.bildir(e, k, (is_ or bas_is or {}).get('atayan'), t, kisi)
    if e and e['eylem_kodu'] in CALISAN:
        m.kisi_durumu[kisi]['son_olay_ani'] = t


def is_dogur(m, e, satir, kimlik, plansiz=False):
    i = dict(deepcopy(satir), kimlik=kimlik, doguran_olay=e['olay_kimligi'], son_olay=e['olay_kimligi'], kural_versiyonu=1, durum='HAVUZDA', plansiz=plansiz, bitis_ani=None, kisi=None, sira=None, atayan=None)
    i.setdefault('iptal_oncesi_durum', None); i.setdefault('iptal_eden', None)
    i.setdefault('onay_beklet', False); i.setdefault('tamamlayan', None); i.setdefault('onay_bekleme_ani', None); i.setdefault('iptal_ani', None)
    i.setdefault('on_isler', []); i.setdefault('onay_gerekli', False)
    i.setdefault('tahmini_sure_dk', 0); i.setdefault('tur', 'SURELI')
    i['on_isler'] = [e['olay_kimligi'] + '/' + str(x['satir']) if isinstance(x, dict) else x for x in i['on_isler']]
    i.setdefault('kisi_sayisi',1); i['kilitli']=bool(i['on_isler']); i['acik_ariza']=None; i['devam_izni']=False
    m.isler[kimlik] = i
    if i['kisi_sayisi']>1:
        for n in range(1,i['kisi_sayisi']+1): is_dogur(m,e,dict(satir,kisi_sayisi=1,ana_is=kimlik),kimlik+'/k'+str(n))
        i['tahmini_sure_dk'] *= i['kisi_sayisi']
    return i


def isleri_guncelle(m, t, e=None):
    for kisi, liste in m.listeler.items():
        for sira, kimlik in enumerate(liste, 1):
            i = m.isler[kimlik]; i.update(kisi=kisi, sira=sira)
            i['kilitli']=any(m.isler.get(x,{}).get('durum') not in ('BITTI', 'IPTAL') for x in i['on_isler'])
            if i['durum'] in ('SIRADA','ON_IS_BEKLIYOR'):
                i['durum']='ON_IS_BEKLIYOR' if i['kilitli'] else 'SIRADA'
        d = m.kisi_durumu.get(kisi)
        if d and liste and m.isler[liste[0]]['durum'] != 'ON_IS_BEKLIYOR':
            durum = d['mola_onceki']['durum'] if d['durum'] == 'SABIT_MOLADA' else d['durum']
            if durum == 'ON_IS_BEKLIYOR' and (not e or e['eylem_kodu'] not in ('IS.ATADIM','IS.SIRALADIM','IS.DEVRETTIM','IS.PLANSIZ_TANIMLADIM')): uygula(m, kisi, 'ON_IS_BITTI', t, e)


def atolye_isle(m, e):
    kod, g, t = e['eylem_kodu'], e['girdiler'], an(e['oldugu_an'])
    from .yasam_v5 import isle
    if isle(m, e): return
    if kod == 'IS.TANIMLADIM':
        for n, satir in enumerate(g['isler'], 1):
            kimlik = e['olay_kimligi'] + '/' + str(n) if len(g['isler']) > 1 else e['olay_kimligi']
            is_dogur(m, e, satir, kimlik)
        return
    if kod == 'IS.SURE_EKLEDIM':
        m.elle_olaylar.append(e)
        return
    if kod == 'ELLE_BITIS':
        if g['is_bitti']:
            i = m.isler.get(hedefler(e, 'IS')[0])
            if i:
                i.update(tamamlayan=e['adina'], onay_bekleme_ani=t if i['onay_gerekli'] else None)
                i.update(durum='ONAY_BEKLIYOR' if i['onay_gerekli'] else 'BITTI', bitis_ani=an(g['bitis']))
                for liste in m.listeler.values():
                    if i['durum'] == 'BITTI' and i['kimlik'] in liste: liste.remove(i['kimlik'])
                # Karar 43/51, A8b/A11: onayli is listede kalir.
                kisi = e['adina']
                if m.kisi_durumu.get(kisi, bos_hal())['durum'] != 'MESAI_DISI':
                    uygula(m, kisi, 'IS.TAMAMLADIM', t, e, i)
                isleri_guncelle(m, t, e)
        return
    kimlikler = hedefler(e, 'IS')
    i = m.isler.get(kimlikler[0]) if kimlikler else None
    if kod == 'IS.PLANSIZ_TANIMLADIM':
        i = is_dogur(m, e, dict(g,birim=g.get('birim') or m.kisiler[e['kim']]['birim']), e['olay_kimligi'], True)
    if kod in ('IS.ATADIM', 'IS.SIRALADIM', 'IS.DEVRETTIM', 'IS.PLANSIZ_TANIMLADIM'):
        if not i: m.supheli(e, 'Is yok'); return
        if kod=='IS.ATADIM' and (g.get('kisi_sayisi',i.get('kisi_sayisi',1))>1):
            if i.get('kisi_sayisi',1)==1:
                i['kisi_sayisi']=g['kisi_sayisi']
                for n in range(1,i['kisi_sayisi']+1): is_dogur(m,e,dict(i,kisi_sayisi=1,ana_is=i['kimlik']),i['kimlik']+'/k'+str(n))
                i['tahmini_sure_dk']*=i['kisi_sayisi']
            for n,k in enumerate(g['kisiler'],1):
                alt=deepcopy(e); alt['neyin_ustunde']=[{'tur':'IS','kimlik':i['kimlik']+'/k'+str(n)}]; alt['girdiler']={'kisi':k,'sira':g['sira']}
                atolye_isle(m,alt)
            ana_isleri_guncelle(m); return
        kisiler = [g['kimden'], g['kime']] if kod == 'IS.DEVRETTIM' else [g['kisi']]
        for eski_k,eski_l in m.listeler.items():
            if i['kimlik'] in eski_l and eski_k not in kisiler: kisiler.append(eski_k)
        onceki = {k: list(m.listeler.get(k, [])) for k in kisiler}
        if kod=='IS.ATADIM':
            for eski_l in m.listeler.values():
                if i['kimlik'] in eski_l: eski_l.remove(i['kimlik'])
        if kod == 'IS.DEVRETTIM':
            kaynak = m.listeler.setdefault(g['kimden'], [])
            if i['kimlik'] not in kaynak or g['kimden'] == g['kime']: m.supheli(e, 'Devir kapisi')
            if i['kimlik'] in kaynak: kaynak.remove(i['kimlik'])
            if g.get('kimden_yeni_is'): yerlestir(kaynak, g['kimden_yeni_is'], 1)
            yerlestir(m.listeler.setdefault(g['kime'], []), i['kimlik'], g.get('kime_sira', 1))
            emek_var=any(a['is']==i['kimlik'] and a['kova'] in ('CALISMA','YENIDEN_ISLEME') for a in m.araliklar) or i['durum'] in ('CALISILIYOR','YARIM')
            i['durum'] = 'YARIM' if emek_var else 'SIRADA'; i['atayan'] = e['kim']
            i['acik_ariza'] = None; i['devam_izni'] = False
        else:
            liste = m.listeler.setdefault(g['kisi'], [])
            if kod == 'IS.SIRALADIM' and i['kimlik'] not in liste: m.supheli(e, 'Siralama kapisi')
            if kod == 'IS.ATADIM' and i['durum'] not in ('HAVUZDA', 'REDDEDILDI'): m.supheli(e, 'Atama kapisi')
            yerlestir(liste, i['kimlik'], g.get('sira', g.get('yeni_sira', 1)))
            if kod != 'IS.SIRALADIM': i.update(durum='REDDEDILDI' if i['durum']=='REDDEDILDI' else 'SIRADA', atayan=e['kim'])
        isleri_guncelle(m, t, e)
        for kisi in kisiler:
            eski = onceki[kisi][0] if onceki[kisi] else None
            yeni = m.listeler[kisi][0] if m.listeler[kisi] else None
            if eski != yeni:
                d = m.kisi_durumu.get(kisi, bos_hal())
                acik = d.get('acik_is')
                if acik and m.isler[acik]['durum'] == 'CALISILIYOR': m.isler[acik]['durum'] = 'YARIM'
                uygula(m, kisi, 'LISTE_DEGISTI', t, e, i)
        ana_isleri_guncelle(m)
        return
    if kod in CALISAN:
        kisi = e.get('adina') or e['kim']
        d = m.kisi_durumu.setdefault(kisi, bos_hal())
        liste = m.listeler.get(kisi, [])
        bas = liste[0] if liste else None
        from .takvim_v7 import kesinti, izinler, normal, ekler
        engel=kesinti(m,kisi,t)
        # Erken GIRIS de o gunun tam izinli olmasinda suphelidir.
        if kod=='MESAI.GIRDIM' and any(a<=gun_ani(t.date(),m.takvim(t,kisi)['mesai_baslangic'])<b for a,b in izinler(m,kisi)):
            engel=('IZIN',None)
        if engel:
            m.supheli(e,'Izin/durus araliginda calisan olayi'); d['son_olay_ani']=t
            return
        uygun = kapi(d, kod, i, bas, m.sabit_molada(t,kisi))
        if not uygun and kod!='MESAI.GIRDIM' and not any(a<=t<=b for a,b in normal(m,t.date(),False,kisi)+ekler(m,kisi,gercek=True)):
            m.mesai_sonrasi_isaretleri[e['olay_kimligi']]=dict(kisi=kisi,an=t,olay=e['olay_kimligi'])
            from .yetki_v6 import yoneticiler
            for alici in yoneticiler(m,m.kisiler.get(kisi,{}).get('birim')): m.bildir(e,'R31',alici,t,kisi)
        if not uygun:
            m.supheli(e, 'Calisan kapisi kapali')
            d['son_olay_ani'] = t
            if kod != 'IS.TAMAMLADIM' or not i or i['durum'] not in ('SIRADA','YARIM','CALISILIYOR','REDDEDILDI'): return
            onay = i['onay_gerekli'] or i['durum'] == 'REDDEDILDI'
            i.update(tamamlayan=kisi, onay_bekleme_ani=t if onay else None)
            i.update(durum='ONAY_BEKLIYOR' if onay else 'BITTI', bitis_ani=None if onay else t)
            for l in m.listeler.values():
                if not onay and i['kimlik'] in l: l.remove(i['kimlik'])
            for sahibi, h in list(m.kisi_durumu.items()):
                aktif_bu = h.get('acik_is') == i['kimlik']
                if aktif_bu and onay and h['durum'] != 'SABIT_MOLADA':
                    yeni = dict(h, acik_is=None, durum='ONAY_BEKLIYOR',
                                kova='BEKLEME_ONAY', aralik_is=i['kimlik'], neden=None)
                    hal_yaz(m, sahibi, yeni, t, e, 'R05')
                elif aktif_bu: h['acik_is']=None
                once=h.get('mola_onceki')
                if once and once.get('acik_is')==i['kimlik']:
                    once.update(acik_is=None, durum='ONAY_BEKLIYOR' if onay else 'CALISMIYOR',
                                kova='BEKLEME_ONAY' if onay else 'TANIMSIZ',
                                aralik_is=i['kimlik'] if onay else None)
            if onay: m.bildir(e, 'R05', i['atayan'], t, kisi)
            isleri_guncelle(m,t,e); ana_isleri_guncelle(m); return
        if kod == 'IS.TAMAMLADIM' and i:
            i.update(tamamlayan=kisi, onay_bekleme_ani=t if i['onay_gerekli'] else None)
            i['durum'] = 'ONAY_BEKLIYOR' if i['onay_gerekli'] else 'BITTI'
            if i['durum'] == 'BITTI':
                i['bitis_ani'] = t
                for l in m.listeler.values():
                    if i['kimlik'] in l: l.remove(i['kimlik'])
                if not m.listeler.get(kisi): m.bildir(e, 'R08', i['atayan'], t, kisi)
        if uygun:
            if i and kod=='IS.ARIZA_BILDIRDIM': i['acik_ariza']=g.get('neden') or 'BELIRTILMEDI'; i['devam_izni']=False
            if i and kod=='IS.DEVAM_ETTIM': i['acik_ariza']=None
            if i and kod=='IS.TAMAMLADIM': i['acik_ariza']=None
            uygula(m, kisi, kod, t, e, i, (g.get('neden') or 'BELIRTILMEDI') if kod=='IS.ARIZA_BILDIRDIM' else g.get('neden'))
            if i and kod in ('IS.BASLADIM', 'IS.DEVAM_ETTIM') and i['tur'] != 'ANLIK': i['durum'] = 'CALISILIYOR'
            if kod == 'MESAI.CIKTIM':
                for is_ in m.isler.values():
                    if is_.get('kisi') == kisi and is_['durum'] == 'CALISILIYOR': is_['durum'] = 'YARIM'
        isleri_guncelle(m, t, e)
        ana_isleri_guncelle(m)
        return
    if i and kod in ('IS.ONAYLADIM', 'IS.REDDETTIM', 'IS.DEVAM_ONAYLADIM'):
        kisi = i.get('kisi')
        if not kisi: m.supheli(e, 'Atanan kisi yok'); return
        from .kabul import lider
        if e['kim'] != i['atayan'] and not lider(m,e['kim'],i.get('birim')): m.supheli(e, 'Atayan/lider farkli')
        if kod == 'IS.ONAYLADIM':
            if i['durum'] != 'ONAY_BEKLIYOR': m.supheli(e, 'Onay kapisi')
            i.update(durum='BITTI', bitis_ani=t)
            for l in m.listeler.values():
                if i['kimlik'] in l: l.remove(i['kimlik'])
            if not m.listeler.get(kisi): m.bildir(e, 'R08', i['atayan'], t, kisi)
        elif kod == 'IS.REDDETTIM': i['durum'] = 'REDDEDILDI'
        elif kod=='IS.DEVAM_ONAYLADIM': i['devam_izni']=True
        uygula(m, kisi, kod, t, e, i)
        isleri_guncelle(m, t, e)
        ana_isleri_guncelle(m)


def elle_uygula(m):
    for e in m.elle_olaylar:
        g, kisi = e['girdiler'], e['adina']
        bas, bit = an(g['baslangic']), min(an(g['bitis']), m.saat.simdi())
        if bas.isocalendar()[:2] != an(e['oldugu_an']).isocalendar()[:2]: m.supheli(e, 'Ayni hafta disinda')
        yeni = []
        for a in m.araliklar:
            son = a['bitis'] or m.saat.simdi()
            x, y = max(a['baslangic'], bas), min(son, bit)
            if a['kisi'] != kisi or a['kova'] not in ('TANIMSIZ', 'GECIS') or x >= y:
                yeni.append(a); continue
            if a['baslangic'] < x: yeni.append(dict(a, bitis=x))
            i = m.isler.get(hedefler(e, 'IS')[0], {})
            yeni.append(dict(a, baslangic=x, bitis=y, kova='CALISMA', is_=None, **{'is': i.get('kimlik'), 'proje': i.get('proje'), 'kategori': i.get('kategori'), 'plansiz': i.get('plansiz', False), 'elle': True, 'aciklama': g['aciklama'], 'yazan': e['kim'], 'acan_olay': e['olay_kimligi']}))
            if y < son: yeni.append(dict(a, baslangic=y))
        m.araliklar = yeni


def kisi_gunu_hesapla(depo, kisi, tarih):
    from .motor import Motor
    m = Motor(depo.saat)
    m.yurut(list(depo.olaylar.values()))
    return [a for a in m.araliklar if a['kisi'] == kisi and str(a['gun']) == str(tarih)]


def gun_akisi(depo, kisi, tarih):
    from .saat import gun
    tarih = gun(tarih)
    ilgili_isler = set()
    for e in depo.olaylar.values():
        g = e['girdiler']
        if kisi in (g.get('kisi'), g.get('kimden'), g.get('kime')):
            ilgili_isler.update(hedefler(e, 'IS'))
            if e['eylem_kodu'] == 'IS.PLANSIZ_TANIMLADIM': ilgili_isler.add(e['olay_kimligi'])
    sonuc = []
    for e in depo.olaylar.values():
        t = an(e['oldugu_an'])
        if t.date() != tarih or t > depo.saat.simdi(): continue
        calisan = e['eylem_kodu'] in CALISAN and (e.get('adina') or e['kim']) == kisi
        lider = e['eylem_kodu'] not in CALISAN and (bool(set(hedefler(e, 'IS')) & ilgili_isler) or kisi in (e['girdiler'].get('kisi'), e['girdiler'].get('kimden'), e['girdiler'].get('kime')))
        if calisan or lider: sonuc.append({'an': t, 'oncelik': 1, 'kimlik': e['olay_kimligi'], 'olay': e})
    takvim = depo.takvim(tarih,kisi)
    noktalar = [(x['bas'], 'MOLA_BASI') for x in takvim['sabit_molalar']] + [(x['bit'], 'MOLA_SONU') for x in takvim['sabit_molalar']] + [(takvim['mesai_bitis'], 'PAYDOS')]
    for saat, kod in noktalar:
        t = gun_ani(tarih, saat)
        if t <= depo.saat.simdi(): sonuc.append({'an': t, 'oncelik': 0, 'kimlik': kod, 'olay': None})
    on_isler = {on for kimlik in ilgili_isler if kimlik in depo.isler for on in depo.isler[kimlik]['on_isler']}
    for on in on_isler:
        t = depo.isler.get(on, {}).get('bitis_ani')
        if t and t.date() == tarih and t <= depo.saat.simdi(): sonuc.append({'an': t, 'oncelik': 0, 'kimlik': 'ON_IS_BITTI:' + on, 'olay': None})
    return sorted(sonuc, key=lambda x: (x['an'], x['oncelik'], x['kimlik']))


def ana_isleri_guncelle(m):
    for i in m.isler.values():
        if i.get('kisi_sayisi',1)<=1 or i['durum']=='IPTAL': continue
        alt=[x for x in m.isler.values() if x.get('ana_is')==i['kimlik']]
        kalan = [x for x in alt if x['durum'] != 'IPTAL']
        if not kalan:
            i.update(durum='IPTAL', bitis_ani=None, iptal_ani=max(x['iptal_ani'] for x in alt))
            continue
        durumlar=[x['durum'] for x in kalan]
        i['durum']=('BITTI' if all(x=='BITTI' for x in durumlar) else 'CALISILIYOR' if 'CALISILIYOR' in durumlar else 'ONAY_BEKLIYOR' if set(durumlar)<={'BITTI','ONAY_BEKLIYOR'} else 'HAVUZDA' if set(durumlar)=={'HAVUZDA'} else 'YARIM' if any(x in ('YARIM','BITTI') for x in durumlar) else 'SIRADA')
        i['kisi']=None; i['sira']=None
        i['bitis_ani']=max((an(x['bitis_ani'] or x.get('iptal_ani')) for x in alt),default=None) if i['durum']=='BITTI' else None

def birlestir(araliklar):
    sonuc=[]
    for a in sorted(araliklar,key=lambda x:(x['kisi'] or '',x['baslangic'])):
        once=sonuc[-1] if sonuc else None
        alanlar=('kisi','gun','kova','is','neden','elle','yazan','aciklama','plansiz','fazla_mesai','katsayi')
        if once and once['bitis']==a['baslangic'] and all(once.get(k)==a.get(k) for k in alanlar):
            once.update(bitis=a['bitis'],kapatan_olay=a.get('kapatan_olay'),kapatan_kural=a.get('kapatan_kural'),sistem_kapatti=a.get('sistem_kapatti',False))
        else: sonuc.append(dict(a))
    return sonuc
