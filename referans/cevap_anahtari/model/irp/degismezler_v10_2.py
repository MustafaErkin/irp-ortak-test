"""I127–I131: kabul sırası, nesne projesi, gizlilik ve cihaz ayrımı."""
from .saat import an, Saat

TANIMLAR = {
    'I127': 'Kullanıcının yönetim kararı kabul anında dayandığı etkin kaydın olaylarından sonra sıralanır; AKTARIM muaftır.',
    'I128': 'Nesnenin her PROJE bağı nesnenin değişmez projesine eşittir.',
    'I129': 'Kaynak yükü ve plan çakışması görünmeyen proje kimliği veya adı döndürmez.',
    'I130': 'Modül cihaz harfi tekildir ve hiçbir kayıtlı cihaza verilmez.',
    'I131': 'Kişi yetkinlikleri tekil kodlardır; işteki yetkinlik tek koddur.',
}


def denetle(d, derin=False):
    from .kabul import TANIKLIK
    from .kurallar_v10_2 import dayandigi_kayitlar, kaydin_olaylari
    s = dict.fromkeys(TANIMLAR, True)
    es = list(d._kayitlar.values()) if hasattr(d, '_kayitlar') else list(d.olaylar)
    once = []; son = None
    for e in es:
        key = (an(e['oldugu_an']), e['olay_kimligi'])
        if e['eylem_kodu'] not in TANIKLIK and e.get('giris_sekli') != 'AKTARIM' and son and key < son:
            # Yalnız sırası geri gelen karar için kabul öncesi bağımsız durum kurulur.
            from .motor import Motor
            m = Motor(Saat(e.get('bulut_ulasma_ani', e['oldugu_an'])))
            m.yurut(once)
            for tur, kayit in dayandigi_kayitlar(m, e):
                s['I127'] &= all((an(x['oldugu_an']),x['olay_kimligi']) < key for x in kaydin_olaylari(m,tur,kayit))
        once.append(e); son = max(son, key) if son else key
    for x in d.nesneler.values():
        s['I128'] &= all(b['kimlik'] == x.get('proje') for b in x.get('baglar',[]) if b['tur']=='PROJE')
    hs = [x['cihaz_harfi'] for x in d.moduller.values() if x.get('cihaz_harfi')]
    s['I130'] &= len(hs) == len(set(hs)) and not set(hs).intersection(getattr(d,'cihaz_harfleri',{}).values())
    for e in es:
        if e['olay_kimligi'][-1] in hs:
            s['I130'] &= any(e['cihaz']=='MODUL-'+m['kod'] and e['olay_kimligi'][-1]==m.get('cihaz_harfi') for m in d.moduller.values())
    for x in d.kisiler.values():
        ys = x.get('yetkinlikler', [])
        s['I131'] &= len(ys)==len(set(ys)) and all('YETKINLIK:'+y in d.kod_listesi for y in ys)
    s['I131'] &= all(not x.get('yetkinlik') or 'YETKINLIK:'+x['yetkinlik'] in d.kod_listesi for x in d.isler.values())
    if derin:
        from .gorunum_v10_2 import kaynak_yuku, kaynak_satirlari
        from .gorunum_v10_1 import plan_cakismalari
        from .gorunum_v9 import proje_gorebilir_mi, gorebilir_mi
        from .yetki_v6 import istihdamda
        for tur,tablo in [('TEZGAH',d.tezgahlar),('KISI',d.kisiler)]:
            for key in tablo:
                rows=list(kaynak_satirlari(d,tur,key,'1900-01-01','2100-01-01'))
                if not rows: continue
                for kim in d.kisiler:
                    if not istihdamda(d,kim,d.saat.simdi()): continue
                    result=kaynak_yuku(d,kim,tur,key,'1900-01-01','2100-01-01')
                    for (_,k,x,_,_),r in zip(rows,result):
                        if tur=='KISI' and not gorebilir_mi(d,kim,'IS',key):
                            s['I129'] &= set(r)=={'durum','bas','bit'} and r['durum']=='MESGUL'
                        elif x.get('proje') and not proje_gorebilir_mi(d,kim,x['proje']):
                            s['I129'] &= set(r)=={'proje','planlanan_baslangic','planlanan_bitis'} and r['proje']=='ERISIM_DISI'
                    for c in plan_cakismalari(d,dict(tur=tur,kimlik=key),'1900-01-01','2100-01-01',cagiran=kim):
                        for h in c['hedefler']:
                            s['I129'] &= h=={'tur':'ERISIM_DISI'} or (set(h)=={'tur','kimlik'} and gorebilir_mi(d,kim,h['tur'],h['kimlik']))
    return {k:bool(v) for k,v in s.items()}
