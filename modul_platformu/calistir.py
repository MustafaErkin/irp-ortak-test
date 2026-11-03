"""Tek modülün arka yüzünü yalnız yerel ortak geçitten erişilir biçimde çalıştırır."""
import importlib
import logging
import os
from pathlib import Path
import secrets
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.runtime/python'),str(ROOT/'onboarding')]

def main():
    from .kayit import oku
    row=oku()[os.environ['IRP_MODUL_KOD']]
    sys.path.insert(0,str(row['klasor']))
    module,attribute=row['arka_yuz'].split(':')
    target=getattr(importlib.import_module(module),attribute)
    secret=os.environ['IRP_MODUL_IC_ANAHTAR']
    logging.disable(logging.CRITICAL)  # SQL/ağ hata ayrıntıları sır veya iş içeriği taşıyabilir.
    async def app(scope,receive,send):
        if scope['type']=='websocket':
            await send({'type':'websocket.close','code':1008})
            return
        if scope['type']=='http':
            headers=dict(scope.get('headers',[]))
            if not secrets.compare_digest(headers.get(b'x-irp-gecit',b'').decode(),secret):
                await send({'type':'http.response.start','status':403,'headers':[(b'content-type',b'application/json')]})
                await send({'type':'http.response.body','body':b'{"mesaj":"Ortak uygulama girisi gerekli."}'})
                return
            if scope['path']=='/irp-saglik':
                await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'application/json')]})
                await send({'type':'http.response.body','body':b'{"ok":true}'})
                return
        await target(scope,receive,send)
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=int(os.environ['IRP_MODUL_PORT']),access_log=False,log_level='critical')

if __name__=='__main__':
    main()
