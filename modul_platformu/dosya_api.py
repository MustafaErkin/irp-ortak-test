"""Normal modül API'sine aynı dosya uçlarını ekler. İş nesnesi iznini modül verir."""
import base64
import binascii
import json
from fastapi import Depends,HTTPException
from pydantic import BaseModel

class Yukleme(BaseModel):
    kayit:dict
    ad:str
    icerik_base64:str
    tur:str='application/octet-stream'


def kur(app,baglam,izin):
    @app.get('/api/dosya-yetkisi')
    def denetle(kayit:str,yazma:bool=False,b=Depends(baglam)):
        try:target=json.loads(kayit)
        except (ValueError,TypeError):raise HTTPException(422,'Dosya nesnesi uygun değil.') from None
        if not isinstance(target,dict):raise HTTPException(422,'Dosya nesnesi uygun değil.')
        izin(b,target,yazma)
        return {'izin':True}

    @app.post('/api/ortak-dosyalar')
    def yukle(g:Yukleme,b=Depends(baglam)):
        izin(b,g.kayit,True)
        try:data=base64.b64decode(g.icerik_base64,validate=True)
        except (ValueError,binascii.Error):raise HTTPException(422,'Dosya okunamadı.') from None
        if not data:raise HTTPException(422,'Dosya boş olamaz.')
        if len(data)>1048576:raise HTTPException(413,'Dosya en fazla 1 MB olabilir.')
        return b.oturum.dosya_yukle(g.kayit,g.ad,data,g.tur)

    @app.get('/api/ortak-dosyalar/{kimlik}')
    def oku(kimlik:str,b=Depends(baglam)):
        return b.oturum.dosya_oku(kimlik)
