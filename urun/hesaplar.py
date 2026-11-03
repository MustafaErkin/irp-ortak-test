"""Canlı kısmın Supabase hesapları (T19 › 2); sırlar ekrana ve depoya yazılmaz.

Hesap Supabase'in yönetici arayüzüyle açılır (IRP_SB_TEST_URL, IRP_SB_TEST_SERVIS).
Giriş kimliği <kişi kodu küçük harf>@calisan.irp; e-posta doğrulanmış sayılır.
Var olan hesabın şifresine dokunulmaz. Hesap–kişi eşlemesi kisi_hesaplari'na yazılır
(IRP_SB_TEST_DB). İlk şifreler yalnızca ~/irp_gizli/ilk_sifreler.txt dosyasına eklenir.
Tekrar koşulursa yalnız eksik hesabı açar ve eşlemeyi yeniler.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.error
import urllib.request

KISILER = ('K001', 'K004', 'K009', 'K041', 'K017', 'K031')
# Karar 145: altı kişi, webde dört ve telefonda üç geçiş.
GOSTERI = (('CEO', 'K001', 'web'), ('Yönetici', 'K004', 'web'),
           ('Ekip Lideri', 'K009', 'ikisi'), ('Ofis Çalışanı', 'K041', 'web'),
           ('Atölye Çalışanı', 'K017', 'telefon'), ('Saha Çalışanı', 'K031', 'telefon'))
GOSTERI_DOSYASI = Path.home() / 'irp_gizli' / 'gosteri_kisileri.json'
HARFLER = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789'
GIZLI = Path.home() / 'irp_gizli' / 'ilk_sifreler.txt'


def eposta(kisi):
    return kisi.strip().lower() + '@calisan.irp'


def ilk_sifre():
    return ''.join(secrets.choice(HARFLER) for _ in range(8))


class Yonetici:
    """Supabase Auth yönetici arayüzü; servis anahtarı yalnız başlıkta taşınır."""

    def __init__(self, url, servis):
        self.url = url.rstrip('/')
        self.basliklar = {'apikey': servis, 'Content-Type': 'application/json'}
        if not servis.startswith('sb_secret_'):
            # Eski JWT biçimi; yeni gizli anahtar yalnız apikey başlığıyla gider.
            self.basliklar['Authorization'] = 'Bearer ' + servis

    def istek(self, yontem, yol, govde=None):
        veri = None if govde is None else json.dumps(govde).encode()
        r = urllib.request.Request(self.url + yol, data=veri, method=yontem, headers=self.basliklar)
        try:
            with urllib.request.urlopen(r, timeout=30) as cevap:
                return cevap.status, json.loads(cevap.read() or b'null')
        except urllib.error.HTTPError as h:
            try:
                icerik = json.loads(h.read() or b'null')
            except ValueError:
                icerik = None
            return h.code, icerik

    def kullanicilar(self):
        bulunan, sayfa = {}, 1
        while True:
            kod, c = self.istek('GET', f'/auth/v1/admin/users?page={sayfa}&per_page=200')
            if kod != 200:
                raise RuntimeError(f'Hesap listesi alınamadı (HTTP {kod})')
            liste = c.get('users', []) if isinstance(c, dict) else []
            for u in liste:
                if u.get('email'):
                    bulunan[u['email'].lower()] = u['id']
            if len(liste) < 200:
                return bulunan
            sayfa += 1

    def sifre_koy(self, kimlik, sifre):
        kod, c = self.istek('PUT', f'/auth/v1/admin/users/{kimlik}', {'password': sifre})
        if kod != 200:
            raise RuntimeError(f'Şifre konamadı (HTTP {kod}, {(c or {}).get("error_code") or (c or {}).get("msg")})')

    def ac(self, kisi, sifre):
        kod, c = self.istek('POST', '/auth/v1/admin/users', {
            'email': eposta(kisi), 'password': sifre, 'email_confirm': True,
            'user_metadata': {'kisi': kisi}})
        if kod in (200, 201):
            return c['id']
        neden = (c or {}).get('error_code') or (c or {}).get('code') or (c or {}).get('msg')
        raise RuntimeError(f'{kisi}: hesap açılamadı (HTTP {kod}, {neden})')


def esle(dsn, eslemeler):
    import psycopg
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.transaction():
            for kisi, kimlik in eslemeler.items():
                conn.execute('DELETE FROM public.kisi_hesaplari WHERE kisi=%s AND auth_kimligi<>%s', (kisi, kimlik))
                conn.execute('INSERT INTO public.kisi_hesaplari(auth_kimligi,kisi) VALUES(%s,%s) '
                             'ON CONFLICT(auth_kimligi) DO UPDATE SET kisi=excluded.kisi', (kimlik, kisi))
        return conn.execute('SELECT count(*) FROM public.kisi_hesaplari').fetchone()[0]


def calistir(url, servis, dsn, kisiler=KISILER):
    y = Yonetici(url, servis)
    var = y.kullanicilar()
    eslemeler, yeni = {}, []
    for kisi in kisiler:
        e = eposta(kisi)
        if e in var:
            eslemeler[kisi] = var[e]
            continue
        sifre = ilk_sifre()
        eslemeler[kisi] = y.ac(kisi, sifre)
        yeni.append((kisi, e, sifre))
    if yeni:
        GIZLI.parent.mkdir(mode=0o700, exist_ok=True)
        eski = os.umask(0o077)
        try:
            with GIZLI.open('a', encoding='utf-8') as f:
                for kisi, e, sifre in yeni:
                    f.write(f'{kisi}\t{e}\t{sifre}\n')
        finally:
            os.umask(eski)
        GIZLI.chmod(0o600)
    toplam = esle(dsn, eslemeler)
    return {'acilan': [k for k, _, _ in yeni], 'vardi': [k for k in kisiler if k not in {y[0] for y in yeni}],
            'eslenen': len(eslemeler), 'kisi_hesaplari': toplam, 'ilk_sifreler': str(GIZLI) if yeni else None}


def gosteri_kisileri(url, servis):
    """Gösteri kişilerine bilinen (rastgele, kalıcı) şifre koyar ve listeyi yalnız Mac'teki dosyaya yazar.
    Uygulama bu listeyle kayıt sormadan girer; liste depoya ve rapora girmez."""
    y = Yonetici(url, servis)
    var = y.kullanicilar()
    eski = {}
    if GOSTERI_DOSYASI.exists():
        eski = {k['kod']: k['sifre'] for k in json.loads(GOSTERI_DOSYASI.read_text(encoding='utf-8'))}
    liste = []
    for etiket, kod, yer in GOSTERI:
        kimlik = var.get(eposta(kod))
        if not kimlik:
            raise RuntimeError(f'{kod}: hesap yok; önce hesaplar.py')
        sifre = eski.get(kod) or ''.join(secrets.choice(HARFLER) for _ in range(12))
        y.sifre_koy(kimlik, sifre)
        liste.append({'etiket': etiket, 'kod': kod, 'sifre': sifre, 'yer': yer})
    GOSTERI_DOSYASI.parent.mkdir(mode=0o700, exist_ok=True)
    eski_umask = os.umask(0o077)
    try:
        GOSTERI_DOSYASI.write_text(json.dumps(liste, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    finally:
        os.umask(eski_umask)
    GOSTERI_DOSYASI.chmod(0o600)
    return {'gosteri_kisileri': [k['etiket'] for k in liste], 'dosya': str(GOSTERI_DOSYASI)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kisi', help='virgülle; verilmezse T19 › 2 listesi')
    p.add_argument('--gosteri', action='store_true', help='gösteri kişilerine bilinen şifre koy, listeyi ~/irp_gizli\'ye yaz')
    args = p.parse_args()
    eksik = [a for a in ('IRP_SB_TEST_URL', 'IRP_SB_TEST_SERVIS', 'IRP_SB_TEST_DB') if not os.environ.get(a)]
    if eksik:
        p.error('Tanımlı değil: ' + ', '.join(eksik))
    kisiler = tuple(k.strip().upper() for k in args.kisi.split(',')) if args.kisi else KISILER
    try:
        if args.gosteri:
            print(json.dumps(gosteri_kisileri(os.environ['IRP_SB_TEST_URL'], os.environ['IRP_SB_TEST_SERVIS']),
                             ensure_ascii=False))
            raise SystemExit(0)
        print(json.dumps(calistir(os.environ['IRP_SB_TEST_URL'], os.environ['IRP_SB_TEST_SERVIS'],
                                  os.environ['IRP_SB_TEST_DB'], kisiler), ensure_ascii=False))
    except RuntimeError as h:
        print('HATA: ' + str(h), file=sys.stderr)
        raise SystemExit(1)
