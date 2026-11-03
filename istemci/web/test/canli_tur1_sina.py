"""Tur 1 canlı hazırlık/okuma. İş firması sıfırlanmaz, test işi oluşturulmaz.

--hazirla yalnız eksik üç izin kodunu ve BELGE türünü CEO'nun normal olaylarıyla
tamamlar. Ayar/parola/jetonlar sadece tarayıcının belleğinde kalır, basılmaz.
"""
import json
import sys
from tarayici import Browser


def run(prepare=False):
    b=Browser()
    b.ws.settimeout(90)
    try:
        b.navigate('http://localhost:8080/?kip=gosterim')
        b.wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')",45)
        result=b.js("""(async()=>{
          const {BrowserStore,IrpClient}=await import('./client.js');
          const config=await (await fetch('ayar.json')).json();
          const schemas=await (await fetch('assets/eylem_semalari.json')).json();
          const store=await BrowserStore.open('irp-tur1-canli-kabul');
          await store.put('installation','T20-READ-CHECK');
          const c=new IrpClient(store,schemas,config);window.tur1Canli=c;
          const idle=async()=>{const until=Date.now()+30000;while((c.writing||c.flushing||c.pending)&&Date.now()<until)await new Promise(r=>setTimeout(r,100));if(c.writing||c.flushing||c.pending)throw Error('İşlem bitmedi');};
          const ceo=config.gosteri_kisileri.find(x=>x.kod==='K001');
          window.tur1Phase='CEO girişi';await c.signIn(ceo.kod,ceo.sifre);await idle();
          window.tur1Phase='Tanımları okuma';const definitions=await (await fetch('cekirdek_onkosullari.json')).json();
          const firm=(await c.read('WEB_FIRMA',null,{},true)).deger;
          const existing=Object.values(firm.kodlar??{});
          const missing=definitions.izinler.filter(x=>!existing.some(y=>y.liste===x.liste&&y.kod===x.kod)).map(g=>['KOD.TANIMLADIM',g]);
          if(!c.context.nesne_turleri?.some(x=>(x.kod??x.kimlik)==='BELGE'))missing.push(['NESNE_TURU.TANIMLADIM',definitions.belge]);
          if("""+json.dumps(prepare)+""")for(const [code,g] of missing){window.tur1Phase=code;try{await c.write(code,g);}catch(e){window.tur1ErrorCode=/^[A-Z0-9_]+$/.test(e.code??'')?e.code:'BELIRSIZ';window.tur1ErrorName=e.name;throw e;}}
          window.tur1Phase='Tanımları doğrulama';const context=(await c.read('WEB_BAGLAM',null,{},true)).deger;
          if(!context.nesne_turleri.some(x=>(x.kod??x.kimlik)==='BELGE'))throw Error('Temel belge türü eksik');
          const codes=(await c.read('KODLAR',null,{},true)).deger;
          if(!definitions.izinler.every(x=>codes.some(y=>y.liste===x.liste&&y.kod===x.kod)))throw Error('İzin türü eksik');
          window.tur1Phase='CEO ücret okuma';const person=(await c.read('WEB_KISI','K017',{},true)).deger;
          if(person.brut_maas==null)throw Error('CEO ücret ayrıntısı eksik');
          // Var olan çekirdek eklerini normal kişi izni ve imzalı URL ile indir.
          window.tur1Phase='Dosya okuma';let files=0;
          for(const task of (await c.read('WEB_GOREVLER',null,{},true)).deger){
            for(const f of (await c.read('WEB_DOSYALAR',task.kimlik,{tur:'GOREV'},true)).deger){
              const response=await fetch(await c.fileUrl(f.kimlik));
              if(!response.ok)throw Error('Canlı dosya indirilemedi');
              const bytes=await response.arrayBuffer();
              if(f.boyut!=null&&bytes.byteLength!==f.boyut)throw Error('Canlı dosya boyutu farklı');
              if(f.parmak_izi){const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==f.parmak_izi)throw Error('Canlı dosya özeti farklı');}
              files++;
            }
          }
          const manager=config.gosteri_kisileri.find(x=>x.kod==='K004');
          window.tur1Phase='Yönetici girişi';await idle();await c.signIn(manager.kod,manager.sifre);await idle();
          if('brut_maas' in (await c.read('WEB_KISI','K017',{},true)).deger)throw Error('Maaş yetkisi genişlemiş');
          await idle();await c.signOut();
          return {hazirlanan:"""+json.dumps(prepare)+"""?missing.length:0,canli_indirilen_dosya:files};
        })().catch(e=>{window.tur1ErrorCode=/^[A-Z0-9_]+$/.test(e.code??'')?e.code:'BELIRSIZ';window.tur1ErrorName=e.name;window.tur1Flags={writing:window.tur1Canli?.writing,flushing:window.tur1Canli?.flushing,pending:window.tur1Canli?.pending};throw e;})""")
        assert not b.errors,'Canlı tarayıcı hatası'
        print('Tur 1 canlı: temel türler ve CEO/yönetici ücret sınırı geçti. '+json.dumps(result,ensure_ascii=False),flush=True)
    except Exception as error:
        # Canlı hata metninde adres veya oturum bilgisi olabileceğinden basılmaz.
        phase=b.js("[window.tur1Phase??'Sayfa açılışı',window.tur1ErrorCode,window.tur1ErrorName].filter(Boolean).join(' / ')")
        print(b.js('JSON.stringify(window.tur1Flags??{})'),flush=True)
        print('Tur 1 canlı kabul tamamlanamadı: '+type(error).__name__+' / '+str(phase),flush=True)
        raise SystemExit(1)
    finally:b.close()


if __name__=='__main__':run('--hazirla' in sys.argv)
