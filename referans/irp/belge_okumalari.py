"""Sözde kodun sorunlu satırlarının birebir küçük yürütmeleri.

Bunlar ana modelin seçtiği düzeltmeler değildir. Karşı örnekler belge
satırını bağımsız, küçük ve incelemeye açık biçimde çalıştırır.
"""


def a8_cikti(araliklar, acik, gecmis_gun=False):
    sonuc = list(araliklar)
    if gecmis_gun and acik: sonuc.append(acik)
    # A8'de bugün açık aralığı listeye ekleyen satır yok.
    return sonuc


def a9_durum(durum, acik_is_mi, herhangi_aralik_var_mi):
    if durum not in ('BITTI', 'ONAY_BEKLIYOR', 'REDDEDILDI', 'HAVUZDA'):
        if acik_is_mi: return 'CALISILIYOR'
        if herhangi_aralik_var_mi: return 'YARIM'
    return durum


def a12_kalan(tahmini_dk, calisilan_dk):
    return (tahmini_dk - calisilan_dk) / 60


def a1_acilis_ve_uret(sayac_gunu, bugun, yerel_sayac, bulut_sayac):
    sayac = max(yerel_sayac, bulut_sayac)  # uygulama_acilisi
    if sayac_gunu != bugun: sayac = 0     # olay_kimligi_uret
    return sayac + 1


def a10_asli_yeniden_hesapla(olay_kodlari):
    d = 'ATANDI'
    for kod in olay_kodlari:
        if kod == 'KABUL': d = 'ACIK'
        if kod == 'TAMAMLA': d = 'ONAY_BEKLIYOR'
        if kod == 'REVIZYON_VER': d = 'REVIZYONDA'
        if kod == 'ONAY': d = 'BITTI'
    return d


def a7_bir_kez_dogur(olaylar):
    gorevler = {}; onaylar = set()
    for e in olaylar:
        if e['kod'] == 'ATADIM': gorevler[e['gorev']] = True
        elif e['kod'] == 'TAMAMLADIM' and e['gorev'] in gorevler: onaylar.add(e['id'])
    return onaylar


def a6_bildirim_yaz(kume, olay, kural, alici):
    return kume | {(olay, kural, alici)}


def a13_kategorisi(durum):
    return {'BITTI': 'tamamlandi', 'ONAY_BEKLIYOR': 'onay_bekliyor', 'REDDEDILDI': 'revizyonda', 'REVIZYONDA': 'revizyonda', 'ATANDI': 'geride', 'ACIK': 'geride', 'ON_IS_BEKLIYOR': 'geride'}.get(durum)


def a6_dallar(derinlik, sinir=5):
    """Çevrimsiz, farklı uzunluktaki bağımlılık dalları ortak G'ye bağlanır."""
    bagimliliklar = {'G': ['{}:0'.format(n) for n in range(1, derinlik + 1)]}
    for n in range(1, derinlik + 1):
        for k in range(n):
            bagimliliklar['{}:{}'.format(n, k)] = ['{}:{}'.format(n, k + 1)] if k < n - 1 else []
    degerler = dict.fromkeys(bagimliliklar, 0)
    kuyruk = list(bagimliliklar); sayac = {}; atlanan = []
    while kuyruk:
        nesne = kuyruk.pop(0)
        sayac[nesne] = sayac.get(nesne, 0) + 1
        if sayac[nesne] > sinir:
            atlanan.append(nesne); continue
        deps = bagimliliklar[nesne]
        yeni = sum(degerler[x] for x in deps) if deps else 1
        if yeni != degerler[nesne]:
            degerler[nesne] = yeni
            for bagli, kaynaklar in bagimliliklar.items():
                if nesne in kaynaklar and bagli not in kuyruk: kuyruk.append(bagli)
    return degerler['G'], sayac, atlanan
