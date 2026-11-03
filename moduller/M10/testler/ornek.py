"""Testlerin ortak örneği: Ek D.5'in talebi ve V2'si, API üzerinden (K050 satış yöneticisi)."""
TALEP = {'kaynak': 'YENI_IS', 'tur': 'KURUMSAL_SARTNAME', 'makine_turu': 'ROBOTIK_HUCRE',
         'konu': '710 Projesi Burç Çakma Ekipmanı', 'cevap_tarihi': '2026-11-20',
         'gereksinimler': [{'metin': 'Çevrim süresi 45 sn altında'}],
         'kapsam': {'dahil': ['Mekanik ve otomasyon tasarımı', 'Robot ve fikstür', 'FAT'],
                    'haric': ['Saha elektrik altyapısı']}}
DOSYA = {'tur': 'SARTNAME', 'ad': 'Autoliv_710_sartname.pdf', 'konum': '\\\\sunucu\\satis\\T-2026-0012\\sartname.pdf'}


def musteri_ac(istemci, h, kisi='K050', **ek):
    r = istemci.post('/api/musteriler', headers=h(kisi), json={
        'ad': 'Autoliv', 'adres': 'Bursa', 'ulke': 'TR', 'strateji_notu': 'İyi fiyat ver',
        'kisiler': [{'ad': 'Ayşe Demir', 'unvan': 'Satın alma', 'eposta': 'ayse@example.com'}], **ek})
    assert r.status_code == 201, r.text
    return r.json()['kimlik']


def d5_talebi(istemci, h, musteri=None, kisi='K050'):
    musteri = musteri or musteri_ac(istemci, h, kisi)
    r = istemci.post('/api/talepler', headers=h(kisi), json={**TALEP, 'musteri': musteri})
    assert r.status_code == 201, r.text
    talep = r.json()['kimlik']
    assert istemci.post(f'/api/talepler/{talep}/dosyalar', headers=h(kisi), json=DOSYA).status_code == 201
    return talep


def katalog_kimligi(istemci, h, kod='ROB-6E-20'):
    return next(k['kimlik'] for k in istemci.get(f'/api/katalog?q={kod}', headers=h('K050')).json()['kalemler']
                if k['kod'] == kod)


def d5_formu(istemci, h, surum, **ek):
    """Ek D.5'teki V2: kalemler, işçilik birimleri (çekirdeğin BIRIMLER'i), 26 haftalık şablondan takvim, kur."""
    r = istemci.post(f'/api/surumler/{surum}/takvim/sablondan', headers=h('K001'), json={'toplam_hafta': 26})
    # düzenlenemeyen sürümde (gönderilmiş) şablon önerilmez; formu sürümün kendi takvimiyle kur
    takvim = r.json()['satirlar'] if r.status_code == 200 else \
        istemci.get(f'/api/surumler/{surum}', headers=h('K001')).json()['takvim']
    return {
        'para_birimi': 'EUR', 'fiyat_girisi': 'FIYAT', 'fiyat': '56000.00', 'toplam_hafta': 26,
        'teslim_suresi_hafta': 28, 'gecerlilik_gun': 30,
        'teknik_cozum': 'Servo preslerle iki istasyonlu burç çakma hücresi; robotla besleme.',
        'odeme_kosullari': '%40 sipariş ile, %50 sevkten önce, %10 kesin kabulde.',
        'teslim_kosullari': 'Teslim yeri ve şekli sözleşmede belirlenir.', 'notlar': '',
        'kalemler': [
            {'unsur': 'ROBOT', 'katalog_kalemi': katalog_kimligi(istemci, h), 'aciklama': 'Robot, 6 eksen, 20 kg',
             'adet': '1', 'birim_fiyat': '28000.00', 'para_birimi': 'EUR', 'kaynak_etiketi': 'TEDARIKCI_TEKLIFI',
             'temin_hafta': 10, 'kritik': True},
            {'unsur': 'PLC', 'aciklama': 'PLC ve HMI seti', 'adet': '1', 'birim_fiyat': '4500.00', 'para_birimi': 'EUR',
             'kaynak_etiketi': 'GECMIS_PROJE', 'temin_hafta': 6},
            {'unsur': 'ISIL_ISLEM', 'aciklama': 'Fikstür ısıl işlem', 'adet': '1', 'birim_fiyat': '35200.00',
             'para_birimi': 'TRY', 'kaynak_etiketi': 'TAHMIN', 'temin_hafta': 2}],
        'iscilik': [{'birim': 'MEK_TASARIM', 'saat': '120'}, {'birim': 'IMALAT', 'saat': '100'}],
        'takvim': [{k: r[k] for k in ('etap_kodu', 'ad', 'paralel_grup', 'baslangic_hafta', 'sure_hafta')}
                   for r in takvim],
        'kurlar': [{'para_birimi': 'EUR', 'kur_try': '35.2', 'kur_tarihi': '2026-10-20'}],
        **ek}


def yeni_surum(istemci, h, talep, kisi='K050', **govde):
    r = istemci.post(f'/api/talepler/{talep}/surumler', headers=h(kisi), json=govde or {'kaynak': 'BOS'})
    assert r.status_code == 201, r.text
    return r.json()


def kaydet(istemci, h, surum, form, kisi='K050'):
    s = istemci.get(f'/api/surumler/{surum}', headers=h(kisi)).json()
    r = istemci.put(f'/api/surumler/{surum}', headers=h(kisi), json=dict(form, surum=s['surum']))
    assert r.status_code == 200, r.text
    return r.json()


D5_HESAP = {'maliyet': '43500.00', 'kar_orani': '28.74', 'marj_yuzde': '22.32', 'fiyat': '56000.00',
            'kirilim': {'MALZEME': '32500.00', 'ISCILIK': '10000.00', 'FASON': '1000.00', 'GENEL_GIDER': '0.00'},
            'takvim_teslim_hafta': 25, 'kayma_hafta': 2, 'en_erken_teslim_hafta': 27}


def d5_surumu(istemci, h, talep=None, kisi='K050'):
    """D.5 talebi ve formu kaydedilmiş TASLAK sürüm → (talep, sürüm)."""
    talep = talep or d5_talebi(istemci, h, kisi=kisi)
    s = yeni_surum(istemci, h, talep, kisi)['kimlik']
    kaydet(istemci, h, s, d5_formu(istemci, h, s), kisi)
    return talep, s


def gecir(istemci, h, surum, eylem, kisi, beklenen=200, **govde):
    r = istemci.post(f'/api/surumler/{surum}/{eylem}', headers=h(kisi), json=govde)
    assert r.status_code == beklenen, r.text
    return r.json()


def gonderilmis(istemci, h, talep=None, onayci='K001'):
    """Onaya gönderilmiş, onaylanmış ve müşteriye gönderilmiş D.5 sürümü → (talep, sürüm)."""
    talep, s = d5_surumu(istemci, h, talep)
    gecir(istemci, h, s, 'onaya-gonder', 'K050')
    gecir(istemci, h, s, 'onayla', onayci)
    gecir(istemci, h, s, 'gonderildi', 'K050', gonderim_sekli='E_POSTA', **{'not': 'Ayşe Hanım\'a'})
    return talep, s
