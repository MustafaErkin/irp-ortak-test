"""Gerçek Safari'de yalnız yerel örnek sayfanın menü/pencere davranışını sınar.

Kişisel oturum okunmaz, canlıya bağlanılmaz. Safari'nin otomasyon ayarı kapalıysa
ayar değiştirilmez; doğrulamanın yapılamadığı açıkça bildirilir.
"""
import base64
import functools
import json
from pathlib import Path
import socket
import sys
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0,str(Path(__file__).resolve().parent))
from tarayici import StaticHandler, StaticServer, WEB, ROOT


def run():
    server = StaticServer(('127.0.0.1', 0), functools.partial(StaticHandler, directory=str(WEB / 'build')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    driver = subprocess.Popen(['/usr/bin/safaridriver', '-p', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = 'http://127.0.0.1:' + str(port)
    session = None

    def call(method, path, value=None):
        request = urllib.request.Request(base + path, data=None if value is None else json.dumps(value).encode(), method=method, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)['value']
        except urllib.error.HTTPError as error:
            raise RuntimeError(json.load(error).get('value', {}).get('message', 'Safari isteği reddedildi')) from None

    def command(name, value=None, method='POST'):
        return call(method, '/session/' + session + '/' + name, value)

    def js(source):
        return command('execute/sync', {'script': source, 'args': []})

    def click(query):
        element = command('element', {'using': 'css selector', 'value': query})
        identifier = element['element-6066-11e4-a52e-4f735466cecf']
        command('element/' + identifier + '/click', {})

    def wait(source):
        until = time.monotonic() + 45
        while time.monotonic() < until:
            if js('return ' + source):
                return
            time.sleep(.15)
        raise AssertionError('Safari ekranı beklenen duruma gelmedi: ' + source)

    try:
        until = time.monotonic() + 10
        while True:
            try:
                call('GET', '/status')
                break
            except (OSError, RuntimeError):
                if time.monotonic() >= until:
                    print('Safari: otomasyon sunucusu açılamadı; gerçek Safari doğrulaması yapılamadı.', flush=True)
                    return
                time.sleep(.2)
        try:
            session = call('POST', '/session', {'capabilities': {'alwaysMatch': {'browserName': 'safari'}}})['sessionId']
        except RuntimeError:
            print('Safari: otomasyon oturumu açılamadı; tarayıcı ayarı değiştirilmedi, gerçek Safari doğrulaması yapılamadı.', flush=True)
            return
        command('url', {'url': 'http://127.0.0.1:' + str(server.server_port) + '/?kip=gosterim'})
        wait("!!document.querySelector('#main h1')&&!document.querySelector('.loading-line')")
        js("""window.safariUiReady=false;
          Promise.all([import('./pages.js'),import('./ui.js')]).then(([pages,ui])=>{
            window.safariUi=ui;
            document.querySelector('.page-heading .toolbar').innerHTML=pages.Workspace.prototype.more.call({},[{title:'Deneme İşlemi',code:'SAFARI'}],'Proje İşlemleri');
            const filter=document.createElement('div');filter.className='filter-bar';filter.innerHTML='<label class="search-box"><input id="safari-search" type="search" placeholder="Bu projede ara…"></label>';
            document.querySelector('.page-heading').after(filter);window.safariUiReady=true;
          });return true;""")
        wait('window.safariUiReady===true')
        click('[data-menu-toggle]')
        assert js("return document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded')") == 'true'
        click('[data-menu-toggle]')
        assert not js("return !!document.querySelector('.overflow-menu.is-open')")
        click('[data-menu-toggle]')
        assert js("const e=document.querySelector('.menu-items .btn'),r=e.getBoundingClientRect();return e===document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)")
        point=js("const r=document.querySelector('#safari-search').getBoundingClientRect();return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}")
        command('actions', {'actions': [{'type': 'pointer', 'id': 'hover', 'parameters': {'pointerType': 'mouse'}, 'actions': [{'type': 'pointerMove', 'duration': 0, 'origin': 'viewport', **point}]}]})
        assert js("const e=document.querySelector('.menu-items .btn'),r=e.getBoundingClientRect();return e===document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)")
        click('#main h1')
        assert not js("return !!document.querySelector('.overflow-menu.is-open')")
        js("safariUi.modal('Pencere Kontrolü','<div style=\"height:1800px\">Yerel pencere denemesi</div>');document.querySelector('.dialog-body').scrollTop=1000;return true;")
        assert js("const e=document.querySelector('dialog[open] [data-close]'),r=e.getBoundingClientRect();return e===document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)")
        click('dialog[open] [data-close]')
        js("safariUi.modal('Dışarı Tıklama Kontrolü','Yerel pencere denemesi');return true;")
        command('actions', {'actions': [{'type': 'pointer', 'id': 'mouse', 'parameters': {'pointerType': 'mouse'}, 'actions': [{'type': 'pointerMove', 'duration': 0, 'origin': 'viewport', 'x': 3, 'y': 3}, {'type': 'pointerDown', 'button': 0}, {'type': 'pointerUp', 'button': 0}]}]})
        wait("!document.querySelector('dialog[open]')")
        target=ROOT/'codex/sonuclar/test2_ekranlar/safari_menu.png'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(base64.b64decode(command('screenshot', method='GET')))
        print('Safari: menü aç/kapat/dışarı tıklama, katman sırası, kaydırmada kapatma ve pencere dışına tıklama geçti.', flush=True)
    finally:
        if session:
            try:
                call('DELETE', '/session/' + session)
            except (OSError, RuntimeError):
                pass
        driver.terminate()
        try:
            driver.wait(timeout=5)
        except subprocess.TimeoutExpired:
            driver.kill()
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    run()
