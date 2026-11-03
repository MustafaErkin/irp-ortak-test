"""B36 is alanlarini karsilastir; liste sirasi anlamlidir. Standart kutuphane."""
import argparse
import json
import math
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

HARIC = {'surum', 'son_hesap_ani', 'son_olay', 'olusma_ani', 'kural_versiyonu'}
KUME_DIZILERI = {'araliklar', 'hassas_ekler', 'kisi_gecmisi', 'olay_kimlikleri'}
YEREL = timezone(timedelta(hours=3))


def oku(yol):
    """Büyük ara görüntüleri sıra kaybetmeden parça dosyalarından birleştirir."""
    yol=Path(yol)
    veri=json.loads(yol.read_text('utf-8-sig'))
    for depo in veri.get('depolar',[]):
        parcalar=depo.pop('ara_haller_dosyalari',[])
        if not parcalar: continue
        if depo.get('ara_haller'): raise ValueError('Ara görüntü iki yerde tanımlı')
        depo['ara_haller']=[]
        for ad in parcalar:
            parca=(yol.parent/ad).resolve()
            if not parca.is_relative_to(yol.parent.resolve()):
                raise ValueError('Parça paket dışına çıkamaz')
            depo['ara_haller'].extend(json.loads(parca.read_text('utf-8-sig')))
    return veri


def kanonik(x, alan=''):
    if isinstance(x, dict):
        return {k: kanonik(v, k) for k, v in sorted(x.items()) if k not in HARIC}
    if isinstance(x, (list, tuple, set)):
        sonuc = [kanonik(v) for v in x]
        if alan in KUME_DIZILERI or isinstance(x, set):
            sonuc.sort(key=lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True))
        return sonuc
    if isinstance(x, datetime): return x.astimezone(YEREL).isoformat()
    if isinstance(x, date): return x.isoformat()
    if isinstance(x, Decimal): return format(x, '.2f')
    if isinstance(x, float) and not math.isfinite(x): raise ValueError('Sonlu olmayan sayi')
    if isinstance(x, str) and len(x) >= 19 and x[4:5]=='-' and x[10:11]=='T':
        try:
            t = datetime.fromisoformat(x.replace('Z','+00:00'))
            if t.tzinfo is not None: return t.astimezone(YEREL).isoformat()
        except ValueError: pass
    return x


def farklar(beklenen, bulunan, yol='$', sinir=100):
    sonuc=[]
    def ekle(y, a, b):
        if len(sonuc)<sinir: sonuc.append({'yol':y, 'beklenen':a, 'bulunan':b})
    def gez(a,b,y):
        if isinstance(a,dict) and isinstance(b,dict):
            for k in sorted(a.keys() | b.keys()):
                if k not in a or k not in b: ekle(y+'/'+k, a.get(k,'<ALAN YOK>'), b.get(k,'<ALAN YOK>'))
                else: gez(a[k],b[k],y+'/'+k)
        elif isinstance(a,list) and isinstance(b,list):
            if len(a)!=len(b): ekle(y+'/uzunluk',len(a),len(b))
            for i,(v,w) in enumerate(zip(a,b)): gez(v,w,y+'/'+str(i))
        elif type(a) in (int,float) and type(b) in (int,float):
            if not math.isclose(a,b,rel_tol=0,abs_tol=1e-6): ekle(y,a,b)
        elif type(a) != type(b) or a!=b: ekle(y,a,b)
    gez(kanonik(beklenen),kanonik(bulunan),yol)
    return sonuc


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('beklenen',type=Path); p.add_argument('bulunan',type=Path)
    p.add_argument('--sinir',type=int,default=100)
    a=p.parse_args()
    try:
        fark=farklar(oku(a.beklenen),oku(a.bulunan),sinir=a.sinir)
    except (ValueError,OSError) as h:
        print(str(h)); return 2
    if not fark: print('ESIT'); return 0
    for f in fark: print(f["yol"]+'\n  beklenen: '+str(f['beklenen'])+'\n  bulunan:  '+str(f['bulunan']))
    return 1


if __name__=='__main__': raise SystemExit(main())
