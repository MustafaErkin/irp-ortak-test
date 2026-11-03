"""A9 ve R11: iş görünümü, emek ve makine aralıkları."""


def is_hesapla(depo, kimlik):
    return dict(depo.isler[kimlik])


def emek(depo, kimlik):
    if depo.isler.get(kimlik,{}).get('kisi_sayisi',1)>1: return sum(emek(depo,x['kimlik']) for x in depo.isler.values() if x.get('ana_is')==kimlik)
    return sum(((a['bitis'] or depo.saat.simdi()) - a['baslangic']).total_seconds() / 60 for a in depo.araliklar if a['is'] == kimlik and a['kova'] in ('CALISMA', 'YENIDEN_ISLEME'))


def tezgah_saati_hesapla(m):
    def bitis(i): return i.get('bitis_ani') or i.get('iptal_oncesi_bitis_ani')
    es = m.olaylar.values() if hasattr(m.olaylar, 'values') else m.olaylar
    dogumlar = {e['olay_kimligi']: e for e in es if e['eylem_kodu'] in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM')}
    def parca(i):
        e = dogumlar.get(i['doguran_olay'], {})
        ss = e.get('girdiler', {}).get('isler', [e.get('girdiler', {})])
        n = int(i['kimlik'].split('/')[-1])-1 if len(ss) > 1 else 0
        return ss[n].get('parca_kodu', i.get('parca_kodu'))
    araliklar = []
    for i in m.isler.values():
        if i.get('tezgah_rolu') != 'AL' or not bitis(i): continue
        aday = [b for b in m.isler.values() if b.get('tezgah_rolu') == 'BASLAT' and b.get('tezgah') == i.get('tezgah') and parca(b) == parca(i) and bitis(b) and bitis(b) <= bitis(i)]
        if not aday: continue
        bas = bitis(max(aday, key=bitis))
        if bas < bitis(i):
            araliklar.append({'kisi': None, 'gun': bas.date(), 'is': i['kimlik'], 'proje': i.get('proje'), 'kategori': i.get('kategori'), 'tezgah': i['tezgah'], 'kova': 'TEZGAH', 'baslangic': bas, 'bitis': i.get('makine_bitis_ani') or bitis(i), 'elle': False, 'plansiz': False, 'sistem_kapatti': False, 'acan_kural': 'R11', 'kapatan_kural': 'R11'})
    return araliklar
