"""Teklifin teknik dosyalarını proje erişimine aktarır; ticari ek/PDF bu kapıya girmez."""
import base64
from psycopg.types.json import Jsonb

TURLER={'SARTNAME','FOTOGRAF','VIDEO','SAHA_NOTU','CIZIM'}


def beklenen(p):
    return [d for d in p['donmus_teklif'].get('dosyalar',[]) if d.get('tur') in TURLER]


def devret(i,p):
    from . import yetki
    i.rol_gerek(yetki.DEVRETME)
    if not i.proje(p['proje']):raise ValueError('Proje erişimi gerekli.')
    for d in beklenen(p):
        ref=d['konum']
        if i.b.execute('SELECT 1 FROM mod_m11a.teknik_dosya_devri WHERE proje=%s AND kaynak=%s',(p['proje'],ref)).fetchone():continue
        # Eski harici dosya bağlantısı dosya yüklenmiş gibi gösterilmez.
        target=dict(d)
        if ref.startswith('irp-dosya:'):
            source=i.oturum.dosya_oku(ref.removeprefix('irp-dosya:'))
            if d.get('parmak_izi') and source['parmak_izi']!=d['parmak_izi']:raise ValueError('Dosya kaynağı değişmiş.')
            target.update(i.oturum.dosya_yukle({'tur':'TEKNIK_GIRDI','kimlik':p['proje']},source['ad'],
                base64.b64decode(source['icerik_base64']),source['tur']))
        i.b.execute('INSERT INTO mod_m11a.teknik_dosya_devri VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',
                    (p['proje'],ref,Jsonb(target)))
    return gorunum(i,p)


def gorunum(i,p):
    rows=i.b.execute('SELECT dosya FROM mod_m11a.teknik_dosya_devri WHERE proje=%s ORDER BY kaynak',(p['proje'],)).fetchall()
    return {'dosyalar':[r['dosya'] for r in rows],'dosya_aktarimi_tamam':len(rows)==len({d['konum'] for d in beklenen(p)})}
