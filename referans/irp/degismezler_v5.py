"""I59-I66: v5 verisinden bagimsiz tutarlilik denetimleri."""
from .saat import an
from .kapilar_v3 import dongusuz

TANIMLAR = {
    'I59': 'Beklemesiz onayli isin BEKLEME_ONAY araligi yoktur.',
    'I60': 'Iptal is listede degildir ve bitis ani yoktur.',
    'I61': 'Ayrilis gununden sonraki anli normal kabul edilmis olay yoktur.',
    'I62': 'Isler atolye birimine, etaplar mevcut projeye baglidir; birim agaci dongusuzdur.',
    'I63': 'Beklemesiz onay bekleyen yaprak is listede degildir ve tamamlayani vardir.',
    'I64': 'Kapali projede acik is veya gorev kalmaz.',
    'I65': 'Her is en cok bir listede ve iptal olmayan atamasi bir kisiye baglidir.',
    'I66': 'Kurulum sonrasinda kabul edilen aktarim olayi yoktur.'
}

def denetle(d):
    liste = [i for l in d.listeler.values() for i in l]
    beklemesiz = {k for k, i in d.isler.items() if i.get('onay_gerekli') and not i.get('onay_beklet')}
    def bekletiyordu(k, t):
        i = d.isler[k]; kok = i.get('ana_is') or k
        ana = d.isler[kok]; e = d.olaylar[ana['doguran_olay']]
        satirlar = e['girdiler'].get('isler', [e['girdiler']])
        sira = int(kok[len(e['olay_kimligi'])+1:])-1 if kok.startswith(e['olay_kimligi']+'/') else 0
        deger = satirlar[sira].get('onay_beklet', False)
        for x in sorted(d.olaylar.values(), key=lambda x:(an(x['oldugu_an']),x['olay_kimligi'])):
            if x['eylem_kodu']=='IS.DEGISTIRDIM' and an(x['oldugu_an'])<=t and any(h['tur']=='IS' and h['kimlik'] in (k,kok) for h in x['neyin_ustunde']):
                deger=x['girdiler']['degisenler'].get('onay_beklet',deger)
        return deger
    sonuc = {'I59': all(bekletiyordu(a['is'],a['baslangic']) for a in d.araliklar if a['kova']=='BEKLEME_ONAY'),
             'I60': all(k not in liste and i.get('bitis_ani') is None for k,i in d.isler.items() if i['durum']=='IPTAL'),
             'I61': True, 'I62': True,
             'I63': all(k not in liste and i.get('tamamlayan') in d.kisiler for k,i in d.isler.items() if k in beklemesiz and i['durum']=='ONAY_BEKLIYOR' and i.get('kisi_sayisi',1)==1),
             'I64': all(not any(x.get('proje')==p and x['durum'] not in ('BITTI','IPTAL') for tablo in (d.isler,d.gorevler) for x in tablo.values()) for p,v in d.projeler.items() if not v.get('aktif',True)),
             'I65': len(liste)==len(set(liste)) and all(k in d.kisiler and all(i in d.isler for i in l) for k,l in d.listeler.items()),
             'I66': True}
    for e in d.olaylar.values():
        if e['giris_sekli']=='AKTARIM': continue
        for k in (e['kim'], e.get('adina')):
            p=d.kisiler.get(k,{})
            from .yetki_v6 import istihdamda
            if k and not istihdamda(d, k, an(e['oldugu_an']).date()): sonuc['I61']=False
    agac={k:[v['ust_birim']] if v.get('ust_birim') else [] for k,v in d.birimler.items()}
    sonuc['I62']=(dongusuz(agac) and all(d.birimler.get(i.get('birim'),{}).get('tur')=='ATOLYE' for i in d.isler.values())
                   and all(e['proje'] in d.projeler for e in d.etaplar.values())
                   and all(p in d.birimler for ps in agac.values() for p in ps))
    if d.kurulum_tamamlandi:
        aktarim=[e for e in d.olaylar.values() if e['giris_sekli']=='AKTARIM']
        normal=[e for e in d.olaylar.values() if e['giris_sekli']!='AKTARIM']
        sonuc['I66']=not aktarim or not normal or max(an(e['oldugu_an']) for e in aktarim)<min(an(e['oldugu_an']) for e in normal)
    return sonuc
