"""Geçmiş proje formu (SPEC › 8.14): kapanmış projelerin birim bazında gerçek saatleri, elle (8b)."""


def liste(b):
    projeler = b.execute('SELECT kimlik, proje_kodu, ad, makine_turu, kapanis_tarihi, aciklama, giren, giris_ani '
                         'FROM gecmis_projeler ORDER BY kapanis_tarihi DESC NULLS LAST, proje_kodu').fetchall()
    saatler = {}
    for s in b.execute('SELECT gecmis_proje, birim, gercek_saat FROM gecmis_proje_saatleri ORDER BY birim'):
        saatler.setdefault(s['gecmis_proje'], []).append({'birim': s['birim'], 'gercek_saat': s['gercek_saat']})
    return [dict(p, saatler=saatler.get(p['kimlik'], [])) for p in projeler]


def bul(b, kimlik):
    return next((p for p in liste(b) if p['kimlik'] == kimlik), None)


def kod_var(b, proje_kodu, haric=None):
    return b.execute('SELECT 1 FROM gecmis_projeler WHERE proje_kodu = %s AND kimlik IS DISTINCT FROM %s',
                     (proje_kodu, haric)).fetchone() is not None


def ekle(b, p, kim, an):
    kimlik = b.execute('INSERT INTO gecmis_projeler (proje_kodu, ad, makine_turu, kapanis_tarihi, aciklama, giren, '
                       'giris_ani) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING kimlik',
                       (p['proje_kodu'], p['ad'], p['makine_turu'], p.get('kapanis_tarihi'), p.get('aciklama'), kim,
                        an)).fetchone()['kimlik']
    _saatleri_yaz(b, kimlik, p['saatler'])
    return kimlik


def guncelle(b, kimlik, p):
    n = b.execute('UPDATE gecmis_projeler SET proje_kodu = %s, ad = %s, makine_turu = %s, kapanis_tarihi = %s, '
                  'aciklama = %s WHERE kimlik = %s', (p['proje_kodu'], p['ad'], p['makine_turu'], p.get('kapanis_tarihi'),
                                                      p.get('aciklama'), kimlik)).rowcount
    if n:
        _saatleri_yaz(b, kimlik, p['saatler'])
    return n


def _saatleri_yaz(b, kimlik, saatler):
    b.execute('DELETE FROM gecmis_proje_saatleri WHERE gecmis_proje = %s', (kimlik,))
    for s in saatler:
        b.execute('INSERT INTO gecmis_proje_saatleri (gecmis_proje, birim, gercek_saat) VALUES (%s, %s, %s)',
                  (kimlik, s['birim'], s['gercek_saat']))


def oneri_gecmisi(b):
    """Önerinin geçmiş ayağı: proje başına bir satır (makine türü, birim, gerçek saat)."""
    return b.execute('SELECT p.makine_turu, s.birim, s.gercek_saat FROM gecmis_proje_saatleri s '
                     'JOIN gecmis_projeler p ON p.kimlik = s.gecmis_proje').fetchall()
