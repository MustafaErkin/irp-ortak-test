"""Özel teklif onayı → ortak kutu. Kalıcı kuyruk; tekrar aynı bildirimi günceller."""
import threading
from . import baglanti,vt

_lock=threading.Lock()

def sirala(c,s,yeni,an):
    konu=c.execute('SELECT konu FROM talepler WHERE kimlik=%s',(s['talep'],)).fetchone()['konu']
    c.execute('INSERT INTO bildirim_kuyrugu VALUES(%s,%s,%s,%s,true) ON CONFLICT(surum) '
              'DO UPDATE SET acik=excluded.acik,metin=excluded.metin,an=excluded.an,bekliyor=true',
              (s['kimlik'],yeni=='ONAY_BEKLIYOR',f'Teklif onayınızı bekliyor: {konu}',an))

def esitle():
    if not _lock.acquire(blocking=False):return
    try:
        with vt.islem() as c:
            jobs=c.execute('SELECT * FROM bildirim_kuyrugu WHERE bekliyor ORDER BY an LIMIT 30').fetchall()
        for job in jobs:
            try:
                service=baglanti.cekirdek().servis()
                target={'tur':'MODUL','modul':'M10','kimlik':str(job['surum'])}
                at=job['an'].isoformat()
                if job['acik']:
                    result=service.bildirim_birak('TEKLIF_ONAYI',target,[{'tur':'ROL','kimlik':'YETKILI'}],job['metin'],an=at)
                else:result=service.bildirim_kaldir('TEKLIF_ONAYI',target,an=at)
                if result.get('sonuc')!='BASARILI':continue
                with vt.islem() as c:
                    c.execute('UPDATE bildirim_kuyrugu SET bekliyor=false WHERE surum=%s AND an=%s',(job['surum'],job['an']))
            except Exception:
                continue  # Kuyruk korunur; sonraki istek/kural turu aynı bildirimi yeniden dener.
    finally:_lock.release()
