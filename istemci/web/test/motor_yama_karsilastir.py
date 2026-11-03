"""157 ile 158 ürün çıktısını bütün alanlarıyla karşılaştır; hakeme dokunma.

İki ayrı yerel TEST veritabanı kullanır. IRP_YAMA_ESKI_DB / IRP_YAMA_YENI_DB.
--dayaniklilik: D1/D2/D3 ek varyantları; normal seçim K0/A/B, 69 senaryo.
"""
import os,sys,json,hashlib,argparse
from pathlib import Path
from time import perf_counter
import psycopg
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from test.oynatici.akis import yurut
from test.oynatici.hakem import karsilastirici
from test.oynatici.secim import sec
from test.oynatici.urun_surucu import UrunSurucu
from test.oynatici.dayaniklilik import varyant

args=argparse.ArgumentParser();args.add_argument('--dayaniklilik',action='store_true');args.add_argument('--devam',action='store_true');args.add_argument('--senaryo');args=args.parse_args()
out=Path(os.environ.get('IRP_MOTOR_TEST_OUT','/tmp/irp_motor_yama'));out.mkdir(parents=True,exist_ok=True)
class DevamSurucu(UrunSurucu):
    def bekle(self):
        total=0
        while self._cagir('SELECT test.bekleyen()',kontrol=True):
            n=self._cagir('SELECT motor.bekleyen_isi()',kontrol=True)
            assert n==1,'Ayrı test motoru ilerlemiyor'
            total+=n
        return total
def driver(key):
    dsn=os.environ[key];assert dsn.startswith('postgresql://postgres@localhost:5433/') and dsn.endswith('_test')
    cls=DevamSurucu if args.dayaniklilik and key=='IRP_YAMA_YENI_DB' else UrunSurucu
    return cls(baglanti_fabrikasi=lambda:psycopg.connect(dsn,autocommit=True))
old,new=driver('IRP_YAMA_ESKI_DB'),driver('IRP_YAMA_YENI_DB')
report=out/('eski_yeni_'+('dayaniklilik' if args.dayaniklilik else 'normal')+'.json')
rows=json.loads(report.read_text()) if args.devam and report.exists() else []
try:
    for scenario in sec(None if args.senaryo else 'K0,A,B',args.senaryo,None,False,False):
        original=karsilastirici().oku(scenario.yol)
        variants=['D1','D2','D3'] if args.dayaniklilik else ['NORMAL']
        for mode in variants:
            if any(r['senaryo']==scenario.ad and r['varyant']==mode for r in rows):continue
            data=original
            if mode!='NORMAL':
                data=varyant(original,mode,1)
                if mode in ('D1','D2') and not data['dayaniklilik']['degisiklikler']:continue
            start=perf_counter()
            for d in (old,new):d.dayaniklilik_turu=mode if mode!='NORMAL' else None
            a=yurut(data,old);b=yurut(data,new)
            # Hiçbir iş alanını silme veya eski referans farklarını maskeleme.
            same=a.cikti==b.cikti and a.hatalar==b.hatalar and a.atlananlar==b.atlananlar
            failures=[r for r in a.dayaniklilik+b.dayaniklilik if r.get('sonuc')=='KALDI']
            row={'senaryo':scenario.ad,'varyant':mode,'esit':same,'eski_hata':len(a.hatalar),'yeni_hata':len(b.hatalar),'atlanan':len(b.atlananlar),'yeniden_kurma_farki':len(failures),'saniye':round(perf_counter()-start,3),'cikti_sha256':hashlib.sha256(json.dumps(b.cikti,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
            rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
            report.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
            if not same:
                (out/'eski_yeni_fark.json').write_text(json.dumps({'eski':a.cikti,'yeni':b.cikti,'hatalar':[a.hatalar,b.hatalar],'atlanan':[a.atlananlar,b.atlananlar]},ensure_ascii=False,default=str))
                raise AssertionError((scenario.ad,mode,'Tam ürün çıktıları farklı'))
            # Bu bir yama öncesi/sonrası karşılaştırmasıdır. Her iki tarafta
            # aynı mevcut hata varsa sayısı raporda kalır; ürün geçti denmez.
            if b.hatalar:
                (out/(scenario.ad+'_'+mode+'_mevcut_hata.json')).write_text(json.dumps({'eski':a.hatalar,'yeni':b.hatalar},ensure_ascii=False,indent=2))
            assert not failures,(scenario.ad,'Yeniden kurma farklı')
finally:old.kapat();new.kapat()
