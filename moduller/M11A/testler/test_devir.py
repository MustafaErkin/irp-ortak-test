"""PO ve sözleşme, ticari form, eksikler, muhasebeye devir, gelen kutusu, VEGA (SPEC › 8.2–8.4; senaryo M11A03)."""
from m11a.alan import kurallar
from m11a.baglanti import CekirdekHatasi
from testler.akis import PO_DOSYASI, SOZLESME, ac
from testler.conftest import retler, senaryo_kaydet
from testler.ornek import kazanan_surum

YARIM_FORM = {'faturalama_bicimi': 'KADEMELI', 'teslim_sekli': 'DAP',
              'odeme_satirlari': [{'kosul': 'SIPARIS', 'tutar': '16800.00', 'para_birimi': 'EUR'},
                                  {'kosul': 'TARIH', 'tarih': '2026-11-20', 'tutar': '39200.00', 'para_birimi': 'EUR'}]}


def _form(api, kisi='K050', proje='2611001', **alanlar):
    surum = api('GET', kisi, f'/projeler/{proje}/ticari').json()['surum']
    return api('PUT', kisi, f'/projeler/{proje}/ticari', json={'surum': surum, **YARIM_FORM, **alanlar})


def _erisim_ver(api, kisi, proje='2611001'):
    c = api.c.surucu.yetkili_olay('PROJE.ERISIM_VERDIM', {'proje': proje, 'kisi': kisi, 'gerekce': 'muhasebe'})
    assert c['sonuc'] == 'BASARILI', c


def _kutu(api, kisi):
    return [(x['kaynak'], x['kural']) for x in api.c.giris(kisi, 'deneme').oku('BILDIRIMLER', kisi).deger
            if x.get('kaynak') == 'M11A']


def test_M11A03_muhasebeye_devir(api):
    ac(api, po_no='PO1246789', po_dosyasi=PO_DOSYASI)
    r = _form(api)
    assert r.status_code == 200, r.json()
    assert {e['alan'] for e in r.json()['eksik_alanlar']} == {'SOZLESME', 'IHRACAT', 'TESVIK', 'TEMINAT'}
    assert r.json()['eksik_bilgiler'] == [] and r.json()['uyarilar'] == []

    r = api('POST', 'K050', '/projeler/2611001/devir')
    assert r.status_code == 200, r.json()
    d = r.json()
    assert d['devir']['durum'] == 'DEVREDILDI' and d['acik_eksik'] == 4
    assert d['devir']['son_suzulenler'] == [{'kisi': 'K060', 'neden': 'PROJEYI_GOREMEZ'}]
    assert d['uyari'].startswith('Muhasebede bu projeyi gören kimse yok (K060: projeyi göremiyor).')

    assert api('GET', 'K060', '/gelen-kutusu').json()['satirlar'] == []     # PROJE okuması: YETKI

    _erisim_ver(api, 'K060')
    assert kurallar.calistir(api.c, api.vt) == {'birakilan': 1}
    d = api('GET', 'K050', '/projeler/2611001/ticari').json()['devir']
    assert d['son_alicilar'] == ['K060'] and d['son_suzulenler'] == []
    assert _kutu(api, 'K060') == [('M11A', 'TICARI_DEVIR')]
    assert kurallar.calistir(api.c, api.vt) == {}                            # alıcı ulaştı; yeniden bırakılmaz

    kutu = api('GET', 'K060', '/gelen-kutusu').json()['satirlar']
    assert [(s['proje'], s['devir_durumu'], s['eksik_sayisi']) for s in kutu] == [('2611001', 'DEVREDILDI', 4)]
    assert kutu[0]['yaklasan_tarihler'] == [{'tur': 'ODEME', 'tarih': '2026-11-20', 'tutar': '39200.00',
                                             'para_birimi': 'EUR', 'aciklama': None, 'gecmis': False}]

    r = api('POST', 'K060', '/projeler/2611001/devir/aldim').json()
    assert r['devir']['durum'] == 'EKSIK_VAR' and r['devir']['goren'] == 'K060'
    tesvik = next(e for e in r['eksik_bilgiler'] if e['alan'] == 'TESVIK')
    r = api('PUT', 'K060', f'/projeler/2611001/eksikler/{tesvik["kimlik"]}', json={'durum': 'ISTENDI',
                                                                                 'kimden': 'MUSTERI'})
    assert r.status_code == 200 and r.json()['acik_eksik'] == 4

    assert api('PUT', 'K060', '/projeler/2611001/siparis', json={'sozlesme_dosyasi': SOZLESME}).status_code == 200
    r = _form(api, 'K060', ihracat=False, tesvik='YOK', teminat_gerekli='YOK')
    assert r.json()['eksik_alanlar'] == []
    assert {e['durum'] for e in r.json()['eksik_bilgiler']} == {'ALINDI'}
    assert r.json()['devir']['durum'] == 'MUHASEBE_GORDU'

    r = api('POST', 'K060', '/projeler/2611001/devir/tamamla')
    assert (r.status_code, r.json()['mesaj']) == (409, 'VEGA kodları boş.')
    r = api('PUT', 'K060', '/projeler/2611001/vega', json={'vega_cari_kodu': '120.01.0042',
                                                          'vega_proje_kodu': 'P-2611001'})
    assert r.status_code == 200
    r = api('POST', 'K060', '/projeler/2611001/devir/tamamla').json()
    assert r['devir']['durum'] == 'TAMAM' and r['devir']['tamamlayan'] == 'K060'
    assert _kutu(api, 'K060') == []
    assert api.vt.execute('SELECT count(*) AS n FROM mod_m11a.acik_bildirimler').fetchone()['n'] == 0

    # TAMAM geri alınmaz: sonradan çıkan eksik görünür, durum değişmez
    r = _form(api, 'K060', ihracat=None, tesvik='YOK', teminat_gerekli='YOK')
    assert r.json()['devir']['durum'] == 'TAMAM' and [e['alan'] for e in r.json()['eksik_alanlar']] == ['IHRACAT']

    assert retler(senaryo_kaydet(api.c, 'M11A03_muhasebeye_devir')) == {'sorgu: hata PermissionError': 1}


def test_eksik_satirlari_devirden_once_acilmaz_sonra_esitlenir(api):
    ac(api)
    _form(api)
    assert api.vt.execute('SELECT count(*) AS n FROM mod_m11a.eksik_bilgiler').fetchone()['n'] == 0
    r = api('POST', 'K050', '/projeler/2611001/devir').json()
    assert {e['alan'] for e in r['eksik_bilgiler']} == {'PO', 'SOZLESME', 'IHRACAT', 'TESVIK', 'TEMINAT'}
    r = api('PUT', 'K050', '/projeler/2611001/siparis', json={'po_no': 'PO1'}).json()
    assert r['po_bekleniyor'] is False and r['siparis_adi'].endswith('_PO1')
    po = lambda: next(e for e in api('GET', 'K050', '/projeler/2611001/ticari').json()['eksik_bilgiler']  # noqa: E731
                      if e['alan'] == 'PO')
    assert po()['durum'] == 'ALINDI'
    api('PUT', 'K050', '/projeler/2611001/siparis', json={'po_no': ''})
    assert po()['durum'] == 'EKSIK'
    # Otomatik satır elle kapatılmaz; elle satırı muhasebe kapatır
    r = api('PUT', 'K001', f'/projeler/2611001/eksikler/{po()["kimlik"]}', json={'durum': 'ALINDI'})
    assert (r.status_code, r.json()['kod']) == (409, 'DURUM')
    r = api('PUT', 'K001', f'/projeler/2611001/eksikler/{po()["kimlik"]}', json={'durum': 'ISTENDI'})
    assert (r.status_code, r.json()['kod']) == (422, 'DOGRULAMA')
    r = api('POST', 'K001', '/projeler/2611001/eksikler', json={'ne': 'Teşvik satır numarası müşteriden istenecek'})
    elle = next(e for e in r.json()['eksik_bilgiler'] if e['alan'] is None)
    r = api('PUT', 'K001', f'/projeler/2611001/eksikler/{elle["kimlik"]}', json={'durum': 'ALINDI'})
    assert r.status_code == 200


def test_ticari_form_dogrulama_ve_eszamanlilik(api):
    ac(api)
    surum = api('GET', 'K050', '/projeler/2611001/ticari').json()['surum']
    r = api('PUT', 'K050', '/projeler/2611001/ticari', json={
        'surum': surum, 'odeme_satirlari': [{'kosul': 'SIPARIS', 'tutar': '1.00', 'para_birimi': 'EUR'},
                                            {'kosul': 'TARIH', 'tutar': '1.00', 'para_birimi': 'EUR'}]})
    assert r.status_code == 422 and r.json()['hatalar'] == [
        {'alan': 'odeme_satirlari.tarih', 'sira': 2, 'mesaj': 'TARIH koşulunda tarih zorunlu.'}]
    assert _form(api).status_code == 200
    r = api('PUT', 'K050', '/projeler/2611001/ticari', json={'surum': surum, **YARIM_FORM})
    assert (r.status_code, r.json()['kod']) == (409, 'DEGISTI') and r.json()['guncel']['surum'] == surum + 1
    r = _form(api, odeme_satirlari=[{'kosul': 'SIPARIS', 'tutar': '1000.00', 'para_birimi': 'EUR'},
                                    {'kosul': 'SEVK', 'tutar': '35200.00', 'para_birimi': 'TRY'}])
    assert r.json()['odeme_toplami'] == '2000.00' and r.json()['uyarilar'] == ['Ödeme takvimi güncel tutarla tutmuyor.']


def test_teminat_dosyasi(api):
    ac(api)
    dosya = api('POST', 'K050', '/projeler/2611001/dosyalar',
                json={'tur': 'TEMINAT', 'ad': 'mektup.pdf', 'konum': '\\\\sunucu\\m.pdf'}).json()['dosya']
    r = _form(api, teminat_gerekli='VAR', teminatlar=[{'tur': 'AVANS', 'tutar': '5600.00', 'para_birimi': 'EUR',
                                                       'banka': 'X Bankası', 'bitis_tarihi': '2027-06-30',
                                                       'dosya': dosya['kimlik']}])
    assert r.status_code == 200 and r.json()['teminatlar'][0]['dosya'] == dosya['kimlik']
    assert 'TEMINAT' not in {e['alan'] for e in r.json()['eksik_alanlar']}
    r = _form(api, teminat_gerekli='VAR', teminatlar=[{'tur': 'AVANS', 'tutar': '1.00', 'para_birimi': 'EUR',
                                                       'dosya': 9999}])
    assert r.status_code == 422


def test_roller(api):
    ac(api)
    _erisim_ver(api, 'K060')
    # K012 projeyi görür (projenin etabı olmadığı için yetkili erişim verir), tutarları görmez
    _erisim_ver(api, 'K012')
    assert api('GET', 'K012', '/projeler/2611001').status_code == 200
    for kisi, yontem, yol, govde, beklenen in [
        ('K012', 'GET', '/projeler/2611001/ticari', None, 403),
        ('K017', 'GET', '/projeler/2611001/ticari', None, 403),
        ('K060', 'GET', '/projeler/2611001/ticari', None, 200),
        ('K012', 'PUT', '/projeler/2611001/siparis', {'po_no': 'X'}, 403),
        ('K060', 'PUT', '/projeler/2611001/siparis', {'po_no': 'PO9'}, 200),
        ('K060', 'POST', '/projeler/2611001/devir', None, 403),
        ('K060', 'POST', '/projeler/2611001/devir/aldim', None, 409),     # henüz devir yok
        ('K050', 'POST', '/projeler/2611001/devir', None, 200),
        ('K050', 'POST', '/projeler/2611001/devir', None, 409),
        ('K050', 'POST', '/projeler/2611001/devir/aldim', None, 403),
        ('K050', 'PUT', '/projeler/2611001/vega', {'vega_cari_kodu': 'C'}, 403),
        ('K050', 'POST', '/projeler/2611001/eksikler', {'ne': 'x'}, 403),
        ('K050', 'GET', '/gelen-kutusu', None, 403),
        ('K001', 'GET', '/gelen-kutusu', None, 200),
        ('K060', 'POST', '/projeler/2611001/devir/aldim', None, 200),
    ]:
        r = api(yontem, kisi, yol, json=govde)
        assert r.status_code == beklenen, (kisi, yol, r.json())
    assert api('GET', 'K017', '/projeler/2611001').json() == {'kod': 'YETKI', 'mesaj': 'Bu projeyi göremiyorsunuz.'}


def test_vega_cari_onerisi(api):
    ac(api)
    api('PUT', 'K001', '/projeler/2611001/vega', json={'vega_cari_kodu': '120.01.0042', 'vega_proje_kodu': 'P1'})
    api.m10.ekle(kazanan_surum(surum=63, etiket='T-63'))
    assert ac(api, surum=63) == '2611002'
    assert api('GET', 'K050', '/projeler/2611002/ticari').json()['vega_cari_onerisi'] == '120.01.0042'


def test_bildirim_basarisizsa_devir_geri_alinmaz(api, monkeypatch):
    ac(api)
    _erisim_ver(api, 'K060')

    def kopuk(*a, **k):
        raise CekirdekHatasi('BAGLANTI', 'ağ')
    monkeypatch.setattr(api.c.surucu, 'bildirim', kopuk)
    r = api('POST', 'K050', '/projeler/2611001/devir')
    assert r.status_code == 200 and r.json()['devir']['bildirim_birakildi'] is False
    monkeypatch.undo()
    assert kurallar.calistir(api.c, api.vt) == {'birakilan': 1}
    assert _kutu(api, 'K060') == [('M11A', 'TICARI_DEVIR')]


def test_gelen_kutusu_sirasi(api):
    ac(api)
    api.m10.ekle(kazanan_surum(surum=64, etiket='T-64'))
    ac(api, surum=64)
    for p in ('2611001', '2611002'):
        _erisim_ver(api, 'K060', p)
        api('POST', 'K050', f'/projeler/{p}/devir')
    api('POST', 'K060', '/projeler/2611001/devir/aldim')
    api.c.surucu.saat('2026-12-01T09:00:00+03:00')
    _form(api, proje='2611002', odeme_satirlari=[{'kosul': 'TARIH', 'tarih': '2026-11-20', 'tutar': '1.00',
                                                   'para_birimi': 'EUR'}])
    kutu = api('GET', 'K060', '/gelen-kutusu').json()['satirlar']
    assert [(s['proje'], s['devir_durumu']) for s in kutu] == [('2611002', 'DEVREDILDI'), ('2611001', 'EKSIK_VAR')]
    assert kutu[0]['yaklasan_tarihler'][0]['gecmis'] is True
