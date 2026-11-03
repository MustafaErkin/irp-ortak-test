"""Gerçek cron açıkken veri geri yüklemesi kapalı kalır; iş verisine dokunmaz."""
from motor_yama_ortami import *
from unittest.mock import patch
from urun.veri.gosteri_yedegi import geri_yukle,YedekHatasi
from urun.kur import zamanlayici

names=['irp-motor-saat','irp-motor-bekleyen','irp-motor-log-temizle'];results=[]
before=sqlrun('SELECT count(*),max(kabul_no) FROM public.olaylar')[0]
try:
    for name in names:
        sqlrun('UPDATE cron.job SET active=jobname=%s',(name,))
        # Dosya bütünlüğü ayrı backup testiyle sınanır; burada canlı SQL koruması.
        with patch('urun.veri.gosteri_yedegi.denetle',return_value={}):
            try:
                geri_yukle(DSN,OUT/'olmayan_yedek',OUT,servisler_durdu=True,yerine_koy=True)
                raise AssertionError('Açık cron ile geri yükleme geçildi')
            except YedekHatasi as e:assert 'zamanlayıcısı kapatılmalı' in str(e),str(e)
        results.append({'is':name,'geri_yukleme_engellendi':True})
    # Yamanın işletim geri dönüşü: yeni işler kapanır, özgün saat işi geri gelir.
    assert zamanlayici(DSN,False)==[]
    sqlrun((ROOT/'urun/veritabani/zamanlayici/900_pg_cron.sql').read_text())
    assert sqlrun('SELECT jobname FROM cron.job')==[('irp-motor-saat',)]
    assert isinstance(DB().rpc('K001','oku',{'veri':'PROJELER'})['deger'],list)
    assert sqlrun('SELECT count(*),max(kabul_no) FROM public.olaylar')[0]==before
    results.append({'geri_donus':'özgün dakika işi ve okuma','olay_degisimi':0})
finally:zamanlayici(DSN)
(OUT/'motor_yama_isletim.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('Dört işletim/geri dönüş kontrolü geçti.',flush=True)
