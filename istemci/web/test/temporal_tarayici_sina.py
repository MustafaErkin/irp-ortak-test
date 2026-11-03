"""Tarih bileşeni: gerçek fare/klavye girdisi; firma verisine bağlanmaz."""
import functools
import json
from pathlib import Path
import threading
from tarayici import Browser,StaticServer,StaticHandler

def run():
 s=StaticServer(('127.0.0.1',0),functools.partial(StaticHandler,directory=str(Path(__file__).resolve().parents[1])))
 threading.Thread(target=s.serve_forever,daemon=True).start();b=Browser();checks=[]
 def mount(kind,value):
  b.js("(async()=>{document.body.innerHTML='<input id=t style=\"font:20px monospace\" data-temporal=\"'+"+json.dumps(kind)+"+'\"><button id=away>Sonraki</button>';t.value="+json.dumps(value)+";(await import('/temporal.js')).bindTemporalInput(t)})()")
 def click_at(position):
  x=11+12*position
  for typ in ['mousePressed','mouseReleased']:b.call('Input.dispatchMouseEvent',type=typ,x=x,y=20,button='left',clickCount=1)
 def type_text(text):
  for ch in text:b.call('Input.insertText',text=ch)
 def expect(value):assert b.js('t.value')==value,(b.js('t.value'),value)
 def ok(name):checks.append(name);print('GEÇTİ: '+name,flush=True)
 try:
  b.navigate('http://127.0.0.1:'+str(s.server_port)+'/test/');b.wait("document.readyState==='complete'")
  mount('date','');click_at(0);type_text('02112026');expect('02.11.2026');ok('Sekiz rakam tarih olur')
  click_at(1);type_text('12');expect('12.11.2026');ok('Gün üzerine yazılır; ay/yıl korunur')
  click_at(4);type_text('12');expect('12.12.2026');ok('Ay üzerine yazılır; gün/yıl korunur')
  click_at(8);type_text('2027');expect('12.12.2027');ok('Yıl üzerine yazılır')
  click_at(1);type_text('3');b.js('away.focus()');expect('03.12.2027');ok('Tek rakamlı gün diğer bölümleri bozmaz')
  mount('time','09:30');click_at(1);type_text('1');b.js('away.focus()');expect('01:30');ok('Saat düzenleme dakikayı korur')
  mount('datetime-local','01.11.2026 09:30');click_at(1);type_text('12');expect('12.11.2026 09:30');ok('Tarih-saat birlikte düzenlenirken saat korunur')
  assert not b.errors,b.errors
 finally:b.close();s.shutdown();s.server_close()
 return checks
if __name__=='__main__':run()
