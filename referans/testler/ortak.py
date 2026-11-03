"""Ortak veri de olaydır. Hassas tutarlar ayrı kabul ekidir (karar 15)."""
from collections import defaultdict
from copy import deepcopy
from irp import Depo, Saat, an

IS_OLAYI = 'K004-2610200031-M'


def is_id(n): return IS_OLAYI + '/' + str(n)


def t(gun, saat='08:00', ay=10):
    return '2026-{:02d}-{:02d}T{}:00+03:00'.format(ay, gun, saat)


class Duzenek:
    def __init__(self, ortak=True):
        self.olaylar = []; self.sayaclar = defaultdict(int); self.hassas = {}; self.etap = {}
        if ortak: self.ortak_veri()

    def olay(self, kim, kod, zaman, hedef=None, girdiler=None, tur=None, **alanlar):
        harf = alanlar.pop('harf', 'T' if kim in ('K017', 'K023', 'K045') else 'M')
        tarih = an(zaman).strftime('%y%m%d')
        self.sayaclar[(kim, tarih, harf)] += 1
        kimlik = alanlar.pop('olay_kimligi', '{}-{}{:04d}-{}'.format(kim, tarih, self.sayaclar[(kim, tarih, harf)], harf))
        if hedef is None: nesneler = []
        elif isinstance(hedef, list) and (not hedef or isinstance(hedef[0], dict)): nesneler = hedef
        else:
            if not isinstance(hedef, list): hedef = [hedef]
            nesneler = [{'tur': tur or ('IS' if kod.startswith('IS.') else 'GOREV'), 'kimlik': is_id(x) if isinstance(x, int) else x, 'surum': None} for x in hedef]
        e = {'olay_kimligi': kimlik, 'eylem_kodu': kod, 'eylem_versiyonu': 1, 'neyin_ustunde': nesneler, 'giris_sekli': 'LISTE', 'kim': kim, 'adina': None, 'cihaz': ('TEL-' if harf in ('T', 'U', 'V') else 'MAS-') + kim, 'uygulama_surumu': 'AND-0.1.0' if harf == 'T' else 'WEB-0.1.0', 'oldugu_an': zaman, 'saat_dilimi': '+03:00', 'bildigi_son_hal_ani': zaman, 'girdiler': girdiler or {}, 'kanit': [], 'duzelttigi_olay': None, 'yol': 'DISARIDA', 'pc_ulasma_ani': None}
        e.update(alanlar)
        if kod in ('IS.TANIMLADIM', 'IS.PLANSIZ_TANIMLADIM'):
            for s in e['girdiler'].get('isler', [e['girdiler']]):
                if s.get('onay_gerekli'): s.setdefault('onay_beklet', True)
        self.olaylar.append(e)
        return kimlik

    def ortak_veri(self):
        for kod, basi, tur in [('IMALAT', 'K009', 'ATOLYE'), ('PLANLAMA', 'K004', 'MASA_BASI'), ('MEK_TASARIM', 'K012', 'MASA_BASI'), ('OTO_TASARIM', 'K012', 'MASA_BASI'), ('MUHASEBE', 'K007', 'MASA_BASI'), ('YONETIM', 'K001', 'MASA_BASI')]:
            self.olay('K001', 'BIRIM.TANIMLADIM', t(1, '07:00'), girdiler={'kod': kod, 'ad': kod, 'tur': tur, 'basi': basi, 'ust_birim': 'PLANLAMA' if kod == 'IMALAT' else 'YONETIM' if kod != 'YONETIM' else None})
        kisiler = [('K001', 'YONETIM', 'YETKILI'), ('K004', 'PLANLAMA', 'YONETICI'), ('K006', 'PLANLAMA', 'BEYAZ_YAKA'), ('K009', 'IMALAT', 'EKIP_LIDERI'), ('K017', 'IMALAT', 'CALISAN'), ('K023', 'IMALAT', 'CALISAN'), ('K041', 'MEK_TASARIM', 'BEYAZ_YAKA'), ('K012', 'MEK_TASARIM', 'YONETICI'), ('K044', 'OTO_TASARIM', 'BEYAZ_YAKA'), ('K045', 'PLANLAMA', 'BEYAZ_YAKA'), ('K052', 'MUHASEBE', 'BEYAZ_YAKA'), ('K007', 'MUHASEBE', 'YONETICI'), ('K060', 'MEK_TASARIM', 'BEYAZ_YAKA')]
        for kisi, birim, rol in kisiler:
            yaka = 'MAVI' if birim == 'IMALAT' else 'BEYAZ'
            self.olay('K001', 'KISI.EKLEDIM', t(1, '07:01'), girdiler={'kod': kisi, 'ad': kisi, 'birim': birim, 'yaka': yaka, 'roller': [rol], 'giris_tarihi': '2026-10-01'})
            e = self.olay('K001', 'MAAS.GUNCELLEDIM', t(1, '07:02'), girdiler={'kisi': kisi, 'gecerli_baslangic': '2026-10-01'})
            self.hassas[e] = {'nesne_tur': 'KISI', 'nesne_kimlik': kisi, 'tur': 'MAAS_AYLIK', 'tutar': 20000, 'gecerli_baslangic': '2026-10-01'}
            if yaka == 'MAVI':
                e = self.olay('K001', 'MAAS.GUNCELLEDIM', t(1, '07:03'), girdiler={'kisi': kisi, 'gecerli_baslangic': '2026-10-01'})
                self.hassas[e] = {'nesne_tur': 'KISI', 'nesne_kimlik': kisi, 'tur': 'SAAT_UCRETI', 'tutar': 100, 'gecerli_baslangic': '2026-10-01'}
        self.olay('K001', 'TAKVIM.TANIMLADIM', t(1, '07:04'), girdiler={'gecerli_baslangic': '2026-10-01', 'mesai_baslangic': '08:00', 'mesai_bitis': '18:00', 'calisma_gunleri': [1, 2, 3, 4, 5], 'sabit_molalar': [{'ad': 'Cay', 'bas': '10:00', 'bit': '10:15'}, {'ad': 'Yemek', 'bas': '12:00', 'bit': '12:30'}, {'ad': 'Cay', 'bas': '15:00', 'bit': '15:15'}]})
        self.olay('K001', 'TATIL.EKLEDIM', t(1, '07:04'), girdiler={'tarih': '2026-10-29', 'ad': '29 Ekim'})
        self.olay('K001', 'AYAR.ONAY_ORANI', t(1, '07:05'), girdiler={'deger': .1, 'gecerli_baslangic': t(1, '00:00')})
        self.olay('K012', 'AYAR.YONLENDIRDIM', t(1, '07:05'), girdiler={'birim': 'MEK_TASARIM', 'kisiler': ['K012']})
        for kod, ad, teslim in [('2509084', 'Rulman cakma', '2027-01-29'), ('2509091', 'Elektro-pres', '2027-03-05')]:
            self.olay('K001', 'PROJE.ACTIM', t(1, '07:06'), girdiler={'kod': kod, 'ad': ad, 'teslim_tarihi': teslim})
        for ad, birim, bas, bit, hedef in [('E-TAS', 'MEK_TASARIM', '2026-10-01', '2026-11-20', 400), ('E-SAT', 'PLANLAMA', '2026-10-15', '2026-12-04', 0), ('E-IML', 'IMALAT', '2026-11-02', '2026-12-25', 1200)]:
            self.etap[ad] = self.olay('K004', 'ETAP.TANIMLADIM', t(1), girdiler={'proje': '2509084', 'ad': ad, 'birim': birim, 'baslangic': bas, 'bitis': bit, 'hedef_saat': hedef})
        self.olay('K001', 'TEZGAH.TANIMLADIM', t(1, '07:07'), girdiler={'kod': 'CNC-02', 'ad': 'CNC', 'birim': 'IMALAT'})
        e = self.olay('K001', 'MAAS.GUNCELLEDIM', t(1, '07:08'), girdiler={'kisi': 'CNC-02', 'gecerli_baslangic': '2026-10-01'})
        self.hassas[e] = {'nesne_tur': 'TEZGAH', 'nesne_kimlik': 'CNC-02', 'tur': 'SAAT_UCRETI', 'tutar': 200, 'gecerli_baslangic': '2026-10-01'}
        satirlar = []
        for n, dakika in enumerate([180, 120, 240, 300, 60, 120, 0, 0, 300], 1):
            satirlar.append({'nereye': 'PROJE', 'proje': '2509084', 'etap': self.etap['E-IML'], 'parca_kodu': '2509084_07_04-' + ('52' if n in (7, 8) else '{:02d}'.format(n)), 'islem': 'Is ' + str(n), 'tur': 'ANLIK' if n in (7, 8) else 'SURELI', 'tahmini_sure_dk': dakika, 'onay_gerekli': n in (3, 9), 'on_isler': [is_id(7)] if n == 3 else [is_id(8)] if n == 7 else [], 'birim': 'IMALAT', 'tezgah': 'CNC-02' if n in (7, 8) else None, 'tezgah_rolu': 'AL' if n == 7 else 'BASLAT' if n == 8 else None})
        self.olay('K004', 'IS.TANIMLADIM', t(20, '08:31'), girdiler={'isler': satirlar}, olay_kimligi=IS_OLAYI)

    def ata(self, n, kisi='K017', sira=1, zaman=None):
        return self.olay('K009', 'IS.ATADIM', zaman or t(21, '16:{:02d}'.format(sira)), n, {'kisi': kisi, 'sira': sira})

    def is_olay(self, kod, saat, n=None, kisi='K017', gun=22, ay=10, **girdiler):
        return self.olay(kisi, kod if '.' in kod else 'IS.' + kod, t(gun, saat, ay), n, girdiler)

    def gorev_satiri(self, **alanlar):
        g = {'ad': 'Teknik resim', 'nereye': 'PROJE', 'proje': '2509084', 'etap': self.etap['E-TAS'], 'teslim_tarihi': '2026-10-22', 'zaman_degeri': 1, 'zorluk': 2, 'kisi': 'K041', 'onay_gerekli': False, 'dosya_gerekli': False, 'on_kosul': []}
        g.update(alanlar); return g

    def gorev_ata(self, zaman=None, veren='K012', satirlar=None, **alanlar):
        e = self.olay(veren, 'GOREV.ATADIM', zaman or t(21, '17:40'), girdiler={'gorevler': satirlar or [self.gorev_satiri(**alanlar)]})
        return e + '/1'

    def gorev_olay(self, kod, zaman, hedef, kim='K041', kanit=0, **girdiler):
        return self.olay(kim, 'GOREV.' + kod, zaman, hedef, girdiler, kanit=[{'dosya_kimligi': 'F-test/' + str(n), 'parmak_izi': 'abc' + str(n)} for n in range(kanit)])

    def yeniden_hesapla(self, simdi, olaylar):
        """T11: kabul edilmiş kaynağın sırası değişebilir; yeni kabul sırası ayrı sözleşmedir."""
        d = self.calistir(simdi)
        kaynak = d._kayitlar
        d._kayitlar = {e['olay_kimligi']: kaynak[e['olay_kimligi']] for e in olaylar}
        d.yeniden_kur()
        return d

    def calistir(self, simdi, olaylar=None, demo=False, yontem='kapsamli'):
        # Tarihsel senaryo izdüşümü: yetkili AKTARIM; canlı kabul ayrı yaz() ile sınanır.
        depo = Depo(Saat(simdi, demo=demo),yontem=yontem)
        for e in (olaylar if olaylar is not None else sorted(self.olaylar, key=lambda e: (e['oldugu_an'], e['olay_kimligi']))):
            e['giris_sekli']='AKTARIM'
            sonuc = depo.olay_ekle(e, oturum=e['kim'], servis=True, hassas_ek=self.hassas.get(e['olay_kimligi']))
            if sonuc['sonuc'] != 'BASARILI': raise AssertionError((e['eylem_kodu'], sonuc))
        if depo.isleme_hatalari: raise AssertionError(depo.isleme_hatalari)
        return depo


def yaz(d,e,taze=True,servis=False,hassas=None):
    """Gerçek kabul yolu: rol, durum ve sürüm denetimleri etkin."""
    from irp.kabul import nesne
    e=deepcopy(e); e['giris_sekli']='ELLE' if e['eylem_kodu']=='IS.SURE_EKLEDIM' else 'LISTE'
    from irp.kapilar_v3 import liste_hedefleri
    mevcut={x['kimlik'] for x in e['neyin_ustunde'] if x['tur']=='LISTE'}
    for k in liste_hedefleri(e):
        if k not in mevcut: e['neyin_ustunde'].append({'tur':'LISTE','kimlik':k,'surum':nesne(d,'LISTE',k).get('surum',0)})
    if taze:
        for x in e['neyin_ustunde']: x['surum']=nesne(d,x['tur'],x['kimlik']).get('surum',0)
    return d.olay_ekle(e,oturum=e['kim'],servis=servis,hassas_ek=hassas)


def s1():
    f = Duzenek(); f.ata(1); f.ata(2, sira=2)
    for kod, saat, n in [('MESAI.GIRDIM', '07:58', None), ('BASLADIM', '08:05', 1), ('DEVAM_ETTIM', '10:17', 1), ('MOLA_VERDIM', '10:40', 1), ('DEVAM_ETTIM', '10:52', 1), ('TAMAMLADIM', '11:40', 1), ('BASLADIM', '11:42', 2)]: f.is_olay(kod, saat, n)
    return f


def s13():
    f = Duzenek()
    veriler = [('a', 20, '23', 'K041', True), ('b', 40, '16', 'K041', True), ('c', 16, '20', 'K041', True), ('d', 10, '22', 'K041', True), ('e', 8, '21', 'K060', True), ('f', 8, '23', 'K044', False), ('g', 3, '26', 'K044', False), ('h', 24, '2026-11-06', 'K044', False), ('i', 24, '30', 'K044', False)]
    satirlar = [f.gorev_satiri(ad=ad, zaman_degeri=z, teslim_tarihi=teslim if len(teslim) > 2 else '2026-10-' + teslim, kisi=kisi, onay_gerekli=onay, onaylayan='K012', teslim_saati='10:00' if ad == 'g' else None, on_kosul=[{'satir': 3}] if ad == 'h' else []) for ad, z, teslim, kisi, onay in veriler]
    ilk = f.gorev_ata(t(1, '09:00'), satirlar=satirlar); kok = ilk.rsplit('/', 1)[0]
    ids = {v[0]: kok + '/' + str(n) for n, v in enumerate(veriler, 1)}
    for kisi in ('K041', 'K060', 'K044'):
        f.gorev_olay('KABUL_ETTIM', t(1, '10:00'), [ids[v[0]] for v in veriler if v[3] == kisi], kisi)
    for ad, teslim_gun, teslim_saat, onay_gun, onay_saat in [('a', 22, '15:00', 23, '09:00'), ('b', 15, '16:00', 16, '10:00'), ('c', 23, '10:00', None, None), ('d', 22, '11:00', 22, '14:00'), ('e', 21, '17:00', 22, '09:00')]:
        f.gorev_olay('TAMAMLADIM', t(teslim_gun, teslim_saat), ids[ad], 'K060' if ad == 'e' else 'K041')
        if onay_gun: f.gorev_olay('ONAYLADIM', t(onay_gun, onay_saat), ids[ad], 'K012')
    return f, ids
