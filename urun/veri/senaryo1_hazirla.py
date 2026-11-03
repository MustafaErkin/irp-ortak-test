"""Yalnız açıkça --temiz-baslat ile Senaryo 1 firmasını hazırlar.

Mevcut test projesindeki iş verisini değiştirir; Auth kullanıcılarını silmez.
Önce iş olayları/hassas ücret ekleri özel yerel klasöre yedeklenir. Bağlantı
bilgisi, Auth jetonu, parola veya anahtar yedeğe/çıktıya yazılmaz.
"""
import argparse
from datetime import date,datetime
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse,unquote

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


class ModulluFirmaHatasi(RuntimeError):
    pass


def modul_korumasi(conn):
    """Eski tek-çekirdek sıfırlayıcı, modüllü firmanın ilişkilerini bozamaz."""
    if conn.execute("SELECT to_regclass('eklenti.kurulumlar')").fetchone()[0]:
        if conn.execute('SELECT 1 FROM eklenti.kurulumlar LIMIT 1').fetchone():
            raise ModulluFirmaHatasi('Modüllü firma bu eski komutla sıfırlanamaz. Bütünleşik yedek ve başlangıç hazırlığı gerekli.')


def prepare(dsn,today):
    import psycopg
    from urun.kur import supabase_projesi,zamanlayici
    from urun.veri.senaryo1 import uret,KISILER
    from urun.hesaplar import calistir,gosteri_kisileri
    from test.oynatici.akis import yurut
    from test.oynatici.urun_surucu import UrunSurucu
    ref=unquote(urlparse(dsn).username or '').split('.',1)[-1]
    supabase_projesi(dsn,ref)
    # Girdi ve model denetimi, mevcut firma değişmeden önce tamamlanır.
    _,_,data=uret(today)
    with psycopg.connect(dsn,autocommit=True) as conn:
        if conn.execute('SELECT test.ortam()').fetchone()[0]!='TEST':
            raise RuntimeError('TEST ortamı gerekli')
        modul_korumasi(conn)
        snapshot={
            'olaylar':conn.execute("SELECT coalesce(jsonb_agg(icerik ORDER BY kabul_no),'[]') FROM public.olaylar").fetchone()[0],
            'hassas_ekler':conn.execute("SELECT coalesce(jsonb_agg(to_jsonb(h)),'[]') FROM public.hassas_ekler h").fetchone()[0],
            'modul_bildirimleri':conn.execute("SELECT coalesce(jsonb_agg(hal),'[]') FROM public.modul_bildirimleri").fetchone()[0],
        }
    folder=Path.home()/'irp_gizli'/'senaryo1_yedekler'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=folder/('is_verisi_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.json')
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(snapshot,stream,ensure_ascii=False,default=str)
    zamanlayici(dsn,ac=False)
    driver=UrunSurucu(baglanti_fabrikasi=lambda:psycopg.connect(dsn,autocommit=True))
    try:
        result=yurut(data,driver)
        failed=[r for r in result.cikti['depolar'][0]['cevaplar'] if 'hata_turu' in r or isinstance(r.get('deger'),dict) and r['deger'].get('sonuc') not in (None,'BASARILI')]
        if failed:raise RuntimeError('Ana veri kabulü başarısız')
        driver._cagir('SELECT test.saat_birak()',kontrol=True)
        driver._cagir('SELECT motor.saat_isi()',kontrol=True)
    finally:driver.kapat()
    calistir(os.environ['IRP_SB_TEST_URL'],os.environ['IRP_SB_TEST_SERVIS'],dsn,tuple(p[0] for p in KISILER))
    gosteri_kisileri(os.environ['IRP_SB_TEST_URL'],os.environ['IRP_SB_TEST_SERVIS'])
    with psycopg.connect(dsn,autocommit=True) as conn:
        counts=conn.execute("SELECT (SELECT count(*) FROM public.kisiler),(SELECT count(*) FROM public.projeler),(SELECT count(*) FROM public.etaplar),(SELECT count(*) FROM public.isler),(SELECT count(*) FROM public.gorevler)").fetchone()
        if counts!=(6,0,0,0,0):raise RuntimeError('Temiz başlangıç sayıları uyuşmuyor')
    state={'senaryo':'senaryo1-'+datetime.now().strftime('%Y%m%d%H%M%S'),'baslangic':today.isoformat(),'kisiler':6,'projeler':0,'etaplar':0,'isler':0,'gorevler':0}
    fd=os.open(Path.home()/'irp_gizli'/'senaryo1_durum.json',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(state,stream)
    zamanlayici(dsn,ac=True)
    print('Senaryo 1 hazır: 6 kişi; 0 proje, etap, iş ve görev. Hesaplar korundu. Önceki iş verisi özel klasöre yedeklendi.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--temiz-baslat',action='store_true',required=True)
    p.add_argument('--bugun',type=date.fromisoformat,default=date.today())
    args=p.parse_args()
    try:prepare(os.environ['IRP_SB_TEST_DB'],args.bugun)
    except Exception as error:
        if isinstance(error,ModulluFirmaHatasi):print(str(error),file=sys.stderr)
        print('Senaryo 1 hazırlığı tamamlanamadı ('+type(error).__name__+'). Sır değerleri yazdırılmadı.',file=sys.stderr)
        raise SystemExit(1)
