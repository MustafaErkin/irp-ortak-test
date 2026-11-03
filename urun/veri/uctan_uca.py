"""Uçtan uca deneme (T19 › 6): istemcinin yolu, Supabase'in kendi uçlarıyla.

Bir hesapla giriş (/auth/v1/token, ilk şifreyle; şifre değiştirilmez), saat, cihaz kaydı, bir okuma,
bir olay (/rest/v1/rpc/olay_ekle) ve olaydan sonra kişinin kanalında değişim sinyali (kullanıcının
kendi oturumuyla, satır kuralından geçerek). Sırlar ekrana yazılmaz.

Ortam: IRP_SB_TEST_URL, IRP_SB_TEST_ANON; ilk şifre ~/irp_gizli/ilk_sifreler.txt.
Yazılan olay canlı veriye girer; gösteriden önce canlı veri yeniden yüklenir.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

GIZLI = Path.home() / 'irp_gizli' / 'ilk_sifreler.txt'


def istek(url, yontem='GET', govde=None, basliklar=None):
    veri = None if govde is None else json.dumps(govde).encode()
    r = urllib.request.Request(url, data=veri, method=yontem,
                               headers={'Content-Type': 'application/json', **(basliklar or {})})
    bas = time.perf_counter()
    try:
        with urllib.request.urlopen(r, timeout=30) as c:
            return c.status, json.loads(c.read() or b'null'), time.perf_counter() - bas
    except urllib.error.HTTPError as h:
        try:
            icerik = json.loads(h.read() or b'null')
        except ValueError:
            icerik = None
        return h.code, icerik, time.perf_counter() - bas


def ilk_sifre(kisi):
    for satir in GIZLI.read_text(encoding='utf-8').splitlines():
        p = satir.split('\t')
        if p and p[0] == kisi:
            return p[2]
    raise SystemExit(f'{kisi} için ilk şifre {GIZLI} içinde yok')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--kisi', default='K009')
    p.add_argument('--okuma', default='EKIP')
    p.add_argument('--hedef', default='IMALAT')
    a = p.parse_args(argv)
    url, anon = os.environ.get('IRP_SB_TEST_URL', '').rstrip('/'), os.environ.get('IRP_SB_TEST_ANON')
    if not url or not anon:
        p.error('IRP_SB_TEST_URL ve IRP_SB_TEST_ANON tanımlı olmalı')
    rapor = {}
    kod, c, sn = istek(url + '/auth/v1/token?grant_type=password', 'POST',
                       {'email': a.kisi.lower() + '@calisan.irp', 'password': ilk_sifre(a.kisi)}, {'apikey': anon})
    rapor['giris'] = {'http': kod, 'saniye': round(sn, 3)}
    if kod != 200:
        rapor['giris']['neden'] = (c or {}).get('error_code') or (c or {}).get('msg')
        print(json.dumps(rapor, ensure_ascii=False, indent=1))
        raise SystemExit(1)
    b = {'apikey': anon, 'Authorization': 'Bearer ' + c['access_token']}
    rpc = lambda ad, g: istek(f'{url}/rest/v1/rpc/{ad}', 'POST', g, b)  # noqa: E731

    kod, simdi, sn = rpc('simdi', {})
    rapor['simdi'] = {'http': kod, 'deger': simdi, 'saniye': round(sn, 3)}
    cihaz = f'MAS-{a.kisi}'
    kod, harf, sn = rpc('cihaz_kaydol', {'cihaz': cihaz})
    rapor['cihaz_kaydol'] = {'http': kod, 'harf': harf, 'saniye': round(sn, 3)}
    kod, oku, sn = rpc('oku', {'veri': a.okuma, 'hedef': a.hedef, 'g': {}})
    rapor['oku'] = {'http': kod, 'veri': a.okuma, 'hedef': a.hedef, 'saniye': round(sn, 3),
                    'alanlar': sorted(oku)[:6] if isinstance(oku, dict) else str(oku)[:200]}
    kod, yetkisiz, sn = rpc('oku', {'veri': 'MAAS_DAGILIMI', 'hedef': 'K001', 'g': {}})
    rapor['oku_yetkisiz'] = {'http': kod, 'mesaj': (yetkisiz or {}).get('message') if isinstance(yetkisiz, dict) else None}

    kanal = f'kisi:{a.kisi}'
    sinyal = lambda: istek(f'{url}/rest/v1/degisim_sinyalleri?kanal=eq.{kanal}&order=kimlik.desc&limit=1',  # noqa: E731
                           'GET', None, b)
    _, onceki, _ = sinyal()
    onceki_kimlik = onceki[0]['kimlik'] if isinstance(onceki, list) and onceki else 0
    an = datetime.fromisoformat(simdi.replace('Z', '+00:00')).astimezone().replace(microsecond=0)
    an = an.astimezone(datetime.now().astimezone().tzinfo)
    olay = {'adina': None, 'bildigi_son_hal_ani': (oku or {}).get('hesap_ani') if isinstance(oku, dict) else None,
            'cihaz': cihaz, 'duzelttigi_olay': None, 'eylem_kodu': 'MESAI.GIRDIM', 'eylem_versiyonu': 1,
            'girdiler': {}, 'giris_sekli': 'LISTE', 'kanit': [], 'kim': a.kisi, 'neyin_ustunde': [],
            'olay_kimligi': f'{a.kisi}-{an:%y%m%d}{9000 + (an.hour * 60 + an.minute) % 1000:04d}-{harf}',
            'oldugu_an': an.isoformat(), 'pc_ulasma_ani': None, 'saat_dilimi': an.strftime('%z')[:3] + ':' + an.strftime('%z')[3:],
            'uygulama_surumu': 'WEB-0.1.0', 'yol': 'DISARIDA'}
    olay['bildigi_son_hal_ani'] = olay['bildigi_son_hal_ani'] or olay['oldugu_an']
    kod, cevap, sn = rpc('olay_ekle', {'olay': olay, 'hassas_ek': None})
    rapor['olay_ekle'] = {'http': kod, 'cevap': {k: cevap.get(k) for k in ('sonuc', 'kod', 'neden', 'tekrar')}
                          if isinstance(cevap, dict) else cevap, 'saniye': round(sn, 3)}
    yeni = None
    for _ in range(10):
        _, son, _ = sinyal()
        if isinstance(son, list) and son and son[0]['kimlik'] > onceki_kimlik:
            yeni = son[0]
            break
        time.sleep(1)
    rapor['sinyal'] = {'kanal': kanal, 'geldi': yeni is not None}
    print(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    tamam = (rapor['giris']['http'] == 200 and rapor['oku']['http'] == 200 and rapor['olay_ekle']['http'] == 200
             and isinstance(cevap, dict) and cevap.get('sonuc') == 'BASARILI' and yeni is not None)
    raise SystemExit(0 if tamam else 1)


if __name__ == '__main__':
    main()
