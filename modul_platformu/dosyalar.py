"""MVP'nin mevcut webindeki özel küçük dosya deposu. Yeni dış servis kullanmaz.

Metadata mevcut SQL'de; baytlar webin .runtime/modul_dosyalari dizininde kalır.
Her okumada gerçek kişi ve sahibi modülün nesne izni yeniden denetlenir.
"""
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode
from .gecit import Hata,http

MAX_BYTES=1048576


def _izin(platform,owner,kayit,authorization,write):
    if owner not in platform.addresses:
        raise Hata(503,'IRP|SAGLAYICI_YOK|Dosyanin modulu devrede degil')
    platform.proof(authorization,owner)
    query=urlencode({'kayit':json.dumps(kayit),'yazma':str(bool(write)).lower()})
    status,_,_=http(platform.addresses[owner]+'/api/dosya-yetkisi?'+query,method='GET',
          headers={'Authorization':authorization,'X-IRP-Gecit':platform.secrets[owner]})
    if status!=200:
        raise Hata(403,'IRP|YETKI|Bu dosya icin yetkiniz yok')


def _conn(platform):
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(platform.env['IRP_SB_TEST_DB'],autocommit=True,prepare_threshold=None,row_factory=dict_row)


def _folder(platform):
    return Path(platform.env.get('IRP_MODUL_DOSYA_DIZINI') or platform.root/'.runtime/modul_dosyalari')


def islem(platform,consumer,name,body,authorization):
    proof=platform.proof(authorization,consumer['kod'])
    if not consumer['kunye']['kapilar'].get('dosyalar'):
        raise Hata(403,'IRP|YETKI|Dosya kapisi kunyede yok')
    if name=='modul_dosya_yukle':
        target=body.get('kayit')
        filename=body.get('ad')
        if not isinstance(target,dict) or not isinstance(target.get('tur'),str) or not str(target.get('kimlik','')):
            raise Hata(400,'IRP|BICIM|Dosyanin nesnesi gerekli')
        if not isinstance(filename,str) or not 0<len(filename)<=200 or re.search(r'[\\/\x00-\x1f]',filename):
            raise Hata(400,'IRP|BICIM|Dosya adi uygun degil')
        _izin(platform,consumer['kod'],target,authorization,True)
        try:
            data=base64.b64decode(body.get('icerik_base64',''),validate=True)
        except (ValueError,TypeError,binascii.Error):
            raise Hata(400,'IRP|BICIM|Dosya icerigi okunamadi') from None
        if not 0<len(data)<=MAX_BYTES:
            raise Hata(413,'IRP|BICIM|Dosya en fazla 1 MB olabilir')
        digest=hashlib.sha256(data).hexdigest()
        identity='MF-'+hashlib.sha256(json.dumps([consumer['kod'],target,filename,digest],sort_keys=True).encode()).hexdigest()[:40]
        folder=_folder(platform);folder.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as temp:
            temp.write(data);tmp=Path(temp.name)
        try:
            tmp.replace(folder/identity)
            with _conn(platform) as c:
                c.execute('INSERT INTO eklenti.dosyalar(kimlik,modul,kayit,ad,boyut,tur,parmak_izi,olusturan) '
                          'VALUES(%s,%s,%s::jsonb,%s,%s,%s,%s,%s) ON CONFLICT(kimlik) DO NOTHING',
                          (identity,consumer['kod'],json.dumps(target),filename,len(data),
                           str(body.get('tur') or 'application/octet-stream')[:100],digest,proof['kisi']))
        finally:
            tmp.unlink(missing_ok=True)
        return {'kimlik':identity,'ad':filename,'konum':'irp-dosya:'+identity,'boyut':len(data),'parmak_izi':digest}
    identity=body.get('kimlik','')
    if not isinstance(identity,str) or not re.fullmatch(r'MF-[0-9a-f]{40}',identity):
        raise Hata(400,'IRP|BICIM|Dosya kimligi uygun degil')
    with _conn(platform) as c:
        record=c.execute('SELECT * FROM eklenti.dosyalar WHERE kimlik=%s',(identity,)).fetchone()
    if not record:
        raise Hata(404,'IRP|BILGI_YOK|Dosya bulunamadi')
    owner=record['modul']
    if owner!=consumer['kod'] and not any(d['modul']==owner for d in consumer['kunye'].get('bagimliliklar',[])):
        raise Hata(403,'IRP|YETKI|Dosya kaynagi bagimlilikta yok')
    _izin(platform,owner,record['kayit'],authorization,False)
    path=_folder(platform)/identity
    if not path.is_file():
        raise Hata(503,'IRP|BAGLANTI|Dosyanin icerigine ulasilamadi')
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=record['parmak_izi']:
        raise Hata(503,'IRP|URUN|Dosya butunlugu dogrulanamadi')
    return {'kimlik':identity,'ad':record['ad'],'tur':record['tur'],'boyut':record['boyut'],
            'parmak_izi':record['parmak_izi'],'icerik_base64':base64.b64encode(data).decode()}
