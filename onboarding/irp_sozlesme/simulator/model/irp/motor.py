"""A6/A7: her kabulde olaylardan kurulan belirlenimci başvuru yürütücüsü."""
from copy import deepcopy
from datetime import timedelta
from .saat import an, gun, gun_ani
from .olay import hedefler
from .kisi_gunu import atolye_isle, uygula, mesaiye_kirp, elle_uygula, bos_hal
from .gorev import gorev_isle, gorev_dogur, bagimliliklari_hesapla


class Motor:
    def __init__(self, saat):
        self.saat = saat
        for ad in ('isler', 'gorevler', 'kisiler', 'birimler', 'projeler', 'tezgahlar', 'etaplar', 'notlar', 'yonlendirme', 'listeler', 'kisi_durumu', 'bildirimler', 'supheliler', 'sonuclar', 'olay_nesneleri', 'dosyalar'):
            setattr(self, ad, {})
        self.kod_listesi = {}; self.yetki_kurallari = []; self.kurulum_kaynagi = None; self._an = None
        self.araliklar = []; self.elle_olaylar = []; self.retler = []; self.ayarlar = []
        self.motor_hatalari = []; self.kisi_gecmisi = []; self.takvimler = []; self.tatiller = set()
        self.olaylar = []
        from .kurallar_v7 import TABLOLAR
        from .kurallar_v9 import TABLOLAR as TABLOLAR_V9
        for ad in TABLOLAR + TABLOLAR_V9: setattr(self,ad,{})
        from .kurallar_v10_1 import TABLOLAR as T10
        for ad in T10: setattr(self,ad,{})
        self.bekletmeler = {}; self.yakinsama_turlari = []; self.islenemedi = False
        self.varsayilan_takvim = {'mesai_baslangic': '08:00', 'mesai_bitis': '18:00', 'calisma_gunleri': [1, 2, 3, 4, 5], 'sabit_molalar': [{'ad': 'Cay', 'bas': '10:00', 'bit': '10:15'}, {'ad': 'Yemek', 'bas': '12:00', 'bit': '12:30'}, {'ad': 'Cay', 'bas': '15:00', 'bit': '15:15'}]}

    def takvim(self, tarih, kisi=None, birim=None):
        tanim = self.gun_tanimlari.get(str(gun(tarih)))
        if tanim and tanim['tur'] != 'TATIL':
            return dict(tanim, calisma_gunleri=[gun(tarih).isoweekday()])
        from .takvim_v9 import birim_takvimi
        birim_tak = birim_takvimi(self,tarih,kisi,birim)
        if birim_tak: return birim_tak
        esik = an(tarih) if hasattr(tarih, 'hour') or 'T' in str(tarih) else gun_ani(gun(tarih), '08:00')
        uygun = [t for t in self.takvimler if an(t['gecerli_baslangic']) <= esik]
        return max(uygun, key=lambda t: t['gecerli_baslangic']) if uygun else self.varsayilan_takvim

    def is_gunu(self, tarih, kisi=None, birim=None):
        tarih = gun(tarih)
        return tarih.isoweekday() in self.takvim(tarih,kisi,birim)['calisma_gunleri'] and str(tarih) not in self.tatiller

    def sabit_molada(self, t, kisi=None):
        return self.is_gunu(t,kisi) and any(gun_ani(t.date(), x['bas']) <= t < gun_ani(t.date(), x['bit']) for x in self.takvim(t,kisi)['sabit_molalar'])

    def ayar(self, anahtar, t, varsayilan):
        uygun = [a for a in self.ayarlar if a['anahtar'] == anahtar and an(a['gecerli_baslangic']) <= t]
        return max(uygun, key=lambda a: (a['gecerli_baslangic'], a['doguran_olay']))['deger'] if uygun else varsayilan

    def supheli(self, e, neden):
        self.supheliler[e['olay_kimligi']] = {'olay': e['olay_kimligi'], 'kural': 'R10', 'gerekce': neden}

    def bildir(self, e, kural, alici, t, kisi):
        if not e or not alici: return
        anahtar = e['olay_kimligi'] + ':' + kural + ':' + alici
        self.bildirimler[anahtar] = {'doguran_olay': e['olay_kimligi'], 'kural': kural, 'alici': alici, 'an': t, 'metin': kisi, 'gecerli': True, 'olusma_ani': self.saat.gercek(), 'gorulme_ani': None}

    def sonuc(self, e, kural, nesne, onceki, yeni):
        if onceki != yeni:
            self.sonuclar[e['olay_kimligi'] + ':' + kural + ':' + nesne] = {'doguran_olay': e['olay_kimligi'], 'kural': kural, 'kural_versiyonu': 1, 'nesne_kimlik': nesne, 'onceki_durum': onceki, 'yeni_durum': yeni, 'an': e['oldugu_an']}

    def aralik_ekle(self, kisi, d, bitis, e=None, kural=None, sistem=False):
        from .takvim_v7 import aralik_ekle
        return aralik_ekle(self,kisi,d,bitis,e,kural,sistem)
        i = self.isler.get(d['aralik_is'], {})
        a = {'kisi': kisi, 'gun': d['baslangic'].date(), 'baslangic': d['baslangic'], 'bitis': bitis, 'kova': d['kova'], 'is': d['aralik_is'], 'proje': i.get('proje'), 'kategori': i.get('kategori'), 'tezgah': None, 'neden': d['neden'], 'plansiz': i.get('plansiz', False), 'sistem_kapatti': sistem, 'elle': False, 'aciklama': None, 'yazan': None, 'acan_olay': d['acan_olay'], 'kapatan_olay': e['olay_kimligi'] if e else None, 'acan_kural': d['acan_kural'], 'kapatan_kural': kural, 'kural_versiyonu': 1}
        if not self.is_gunu(a['gun']): return
        a = mesaiye_kirp(a, self.takvim(a['gun']), self.saat.simdi())
        if a: self.araliklar.append(a)

    def ana_veri_isle(self, e):
        kod, g = e['eylem_kodu'], deepcopy(e['girdiler'])
        from .kurallar_v6 import ana_veri
        if ana_veri(self, e): return
        tablo = {'BIRIM.TANIMLADIM': self.birimler, 'PROJE.ACTIM': self.projeler, 'TEZGAH.TANIMLADIM': self.tezgahlar}
        if kod in tablo:
            tablo[kod].setdefault(g['kod'], {}).update(g)
            if kod in ('PROJE.ACTIM', 'TEZGAH.TANIMLADIM'): tablo[kod][g['kod']].setdefault('aktif', True)
        elif kod == 'PROJE.DEGISTIRDIM': self.projeler[hedefler(e, 'PROJE')[0]].update(g['degisenler'])
        elif kod == 'PROJE.KAPATTIM': self.projeler[hedefler(e, 'PROJE')[0]].update(aktif=False, kapanis_ani=an(e['oldugu_an']))
        elif kod == 'ETAP.DEGISTIRDIM': self.etaplar[hedefler(e, 'ETAP')[0]].update(g['degisenler'])
        elif kod == 'KISI.EKLEDIM':
            self.kisiler[g['kod']] = g
            self.kisi_gecmisi.append(dict(g, kisi=g['kod'], gecerli_baslangic=g['giris_tarihi'], gecerli_bitis=None))
        elif kod == 'KISI.DEGISTIRDIM':
            kisi = g['kisi']
            if kisi in self.kisiler:
                self.kisiler[kisi].update(g['degisenler'])
                for gecmis in self.kisi_gecmisi:
                    if gecmis['kisi'] == kisi and gecmis['gecerli_bitis'] is None: gecmis['gecerli_bitis'] = g.get('gecerli_baslangic', e['oldugu_an'])
                gecmis = {k:v for k,v in self.kisiler[kisi].items() if k not in ('istihdam_donemleri', 'ayrilis_tarihi')}
                self.kisi_gecmisi.append(dict(gecmis, kisi=kisi, gecerli_baslangic=g.get('gecerli_baslangic', e['oldugu_an']), gecerli_bitis=None))
        elif kod == 'KISI.AYRILDI': self.kisiler[g['kisi']]['ayrilis_tarihi'] = g['ayrilis_tarihi']
        elif kod == 'TAKVIM.TANIMLADIM': pass  # basta tarihli kuruldu
        elif kod == 'TATIL.EKLEDIM': pass  # tarihli tatil olaylari basta hesaplandi
        elif kod == 'AYAR.ONAY_ORANI': pass  # basta tarihli kuruldu
        elif kod == 'AYAR.YONLENDIRDIM': self.yonlendirme[g['birim']] = g['kisiler']
        elif kod == 'ETAP.TANIMLADIM': self.etaplar[e['olay_kimligi']] = dict(g, kimlik=e['olay_kimligi'], doguran_olay=e['olay_kimligi'])
        elif kod == 'NOT.YAZDIM':
            self.notlar[e['olay_kimligi']] = dict(g, kimlik=e['olay_kimligi'], neyin_ustunde=e['neyin_ustunde'], kanit=e['kanit'], yazan=e['kim'], an=e['oldugu_an'])
            kisiler = sorted({k for b in g.get('etiketler', []) for k in self.yonlendirme.get(b, [])})
            for n, kisi in enumerate(kisiler, 1):
                # Karar 54/55: dolayli NOT dogumu da ayrilisi kayitli
                # kisiye gorev veremez. Taniklik saklanir; eksik alici gorunur.
                from .kurallar_v6 import not_alicisi_ayrilmis
                if not self.kisiler.get(kisi) or self.kisiler[kisi].get('ayrilis_tarihi') or not_alicisi_ayrilmis(self, kisi, e):
                    self.notlar[e['olay_kimligi']].setdefault('atlanan_alicilar', []).append(kisi)
                    continue
                gorev_dogur(self, e, {'ad': g['metin'], 'kisi': kisi, 'kaynak': e['olay_kimligi'], 'zaman_degeri': 0, 'teslim_tarihi': None}, e['olay_kimligi'] + '/' + str(n), 'NOT')

    def yurut(self, olaylar):
        sinir = self.saat.simdi()
        self.hesap_ani = sinir
        olaylar = list(olaylar)
        self._kabul_sirasi = {e['olay_kimligi']:n for n,e in enumerate(olaylar)}
        olaylar = sorted((e for e in olaylar if an(e['oldugu_an']) <= sinir), key=lambda e: (an(e['oldugu_an']), e['olay_kimligi']))
        from .yetki_v6 import varsayilan_kodlar, varsayilan_yetkiler
        # V5 tarihsel aktarim uyarlayicisi; gercek kurulum kendi verisini tasir.
        if not any(e['eylem_kodu'] == 'KURULUM.TAMAMLADIM' for e in olaylar):
            self.kod_listesi = varsayilan_kodlar(surum=9)
            # T9 §14: tablo olayı taşımayan tarihsel ortak veri v9'a sabittir.
            self.yetki_kurallari = [dict(r, gecerli_baslangic=None, gecerli_bitis=None, doguran_olay=None) for r in varsayilan_yetkiler(surum=9)]
        pasif = {e['girdiler']['hedef'] for e in olaylar if e['eylem_kodu']=='KAYIT.GECERSIZ_SAYDIM'}
        olaylar = [e for e in olaylar if e['olay_kimligi'] not in pasif]
        self.olaylar = olaylar
        # A7 doğum hesabı, olay anında geçerli bütün tarihli ayarlara bakar.
        self.ayarlar = [dict(e['girdiler'],gecerli_baslangic=e['girdiler'].get('gecerli_baslangic') or e['oldugu_an'],anahtar='onay_orani',doguran_olay=e['olay_kimligi']) for e in olaylar if e['eylem_kodu']=='AYAR.ONAY_ORANI']
        for kod, anahtar in [('AYAR.MAAS_PAYDASI', 'maas_paydasi_saat'), ('AYAR.PARCA_KODU_DESENI', 'parca_kodu_deseni')]:
            self.ayarlar.extend(dict(e['girdiler'], gecerli_baslangic=e['girdiler'].get('gecerli_baslangic') or e['oldugu_an'], anahtar=anahtar, doguran_olay=e['olay_kimligi']) for e in olaylar if e['eylem_kodu'] == kod)
        # Takvim tarihleri baştan bilinir; her gün kendi geçerli sürümünü kullanır.
        self.takvimler = [dict(deepcopy(e['girdiler']),gecerli_baslangic=e['girdiler'].get('gecerli_baslangic') or gun_ani(an(e['oldugu_an']).date()+timedelta(days=1)).isoformat()) for e in olaylar if e['eylem_kodu'] == 'TAKVIM.TANIMLADIM']
        self.tatiller = set()
        for e in olaylar:
            if e['eylem_kodu'] == 'TATIL.EKLEDIM': self.tatiller.add(e['girdiler']['tarih'])
            if e['eylem_kodu'] == 'TATIL.KALDIRDIM': self.tatiller.discard(e['girdiler']['tarih'])
        from .takvim_v7 import hazirla, sistem_noktalari, sistem_isle
        hazirla(self,olaylar)
        from .takvim_v9 import hazirla as hazirla_v9
        hazirla_v9(self,olaylar)
        gunler = {an(e['oldugu_an']).date() for e in olaylar if e['eylem_kodu'] in ('MESAI.GIRDIM', 'MESAI.CIKTIM')}
        # T11 sıra kapısı T4'ün ortak (an, kimlik) sırasını kabulde güvenceye alır.
        akis = [(an(e['oldugu_an']), 1, e['olay_kimligi'], e) for e in olaylar]
        for e in olaylar:
            if e['eylem_kodu'] == 'KISI.YETKINLIK_TANIMLADIM':
                gecerli = max(an(e['oldugu_an']), an(e['girdiler']['gecerli_baslangic']))
                if an(e['oldugu_an']) < gecerli <= sinir:
                    akis.append((gecerli, 0, 'YETKINLIK_GECERLI:' + e['olay_kimligi'], e))
            if e['eylem_kodu'] == 'KISI.DEGISTIRDIM' and an(e['girdiler']['gecerli_baslangic']) > an(e['oldugu_an']):
                if an(e['girdiler']['gecerli_baslangic']) <= sinir:
                    akis.append((an(e['girdiler']['gecerli_baslangic']), 0, 'KISI_GECERLI:' + e['olay_kimligi'], e))
            if e['eylem_kodu'] == 'IS.SURE_EKLEDIM' and e['girdiler']['is_bitti']:
                nokta = deepcopy(e)
                nokta.update(eylem_kodu='ELLE_BITIS', oldugu_an=e['girdiler']['bitis'])
                akis.append((an(nokta['oldugu_an']), 0, 'ELLE_BITIS:'+e['olay_kimligi'], nokta))
        from .takvim_v9 import sistem_noktalari as noktalar_v9
        akis.extend(noktalar_v9(self,gunler,sinir))
        akis.extend(sistem_noktalari(self,sinir))
        for t, tur, anahtar, e in sorted(akis, key=lambda x: x[:3]):
            self._an = t
            if tur == 0 and e is not None:
                if anahtar.startswith('KISI_GECERLI:'): self.ana_veri_isle(e)
                elif anahtar.startswith('YETKINLIK_GECERLI:'):
                    from .kurallar_v10_2 import isle
                    isle(self, e)
                else: atolye_isle(self,e)
                continue
            if e is None:
                sistem_isle(self,anahtar,t)
                continue
            if tur == 0:
                for kisi, d in list(self.kisi_durumu.items()):
                    if d['durum'] == 'MESAI_DISI': continue
                    eski_is = d['acik_is']
                    uygula(self, kisi, anahtar, t)
                    if anahtar == 'PAYDOS' and eski_is and self.isler[eski_is]['durum'] == 'CALISILIYOR': self.isler[eski_is]['durum'] = 'YARIM'
                continue
            self.olay_nesneleri[e['olay_kimligi']] = ilgili_nesneler(e)
            for dosya in e['kanit']: self.dosyalar[dosya['dosya_kimligi']] = dict(dosya, doguran_olay=e['olay_kimligi'])
            kod = e['eylem_kodu']
            from .kabul import TANIKLIK, durum
            from .kurallar_v7 import isle as isle_v7, sonra as sonra_v7
            from .kurallar_v9 import isle as isle_v9, sonra as sonra_v9
            from .kurallar_v10_1 import isle as isle_v10_1
            from .kurallar_v10_2 import isle as isle_v10_2
            if isle_v10_2(self,e) or isle_v10_1(self,e) or isle_v9(self,e) or isle_v7(self,e):
                sonra_v7(self,e)
                sonra_v9(self,e)
                continue
            if kod not in TANIKLIK and e['giris_sekli'] != 'AKTARIM' and kod not in ('IS.SURE_EKLEDIM','KAYIT.GECERSIZ_SAYDIM') and not durum(self,e):
                self.supheli(e, 'Kabul edilmis karar yeniden hesapta duruma uymuyor')
                continue
            if kod == 'KISI.DEGISTIRDIM' and an(e['girdiler']['gecerli_baslangic']) > t: continue
            if kod.startswith(('IS.', 'MESAI.')): atolye_isle(self, e)
            elif kod.startswith('GOREV.'): gorev_isle(self, e)
            else: self.ana_veri_isle(e)
            sonra_v7(self,e)
            sonra_v9(self,e)
            from .gorev import bekletme_kayitlari
            bekletme_kayitlari(self, t)
        for kisi, d in self.kisi_durumu.items():
            if d['kova'] and d['baslangic']: self.aralik_ekle(kisi, d, None)
            d['son_hesap_ani'] = sinir
        bagimliliklari_hesapla(self)
        elle_uygula(self)
        from .gorev import bekletme_kayitlari
        bekletme_kayitlari(self, sinir)
        from .kisi_gunu import ana_isleri_guncelle, birlestir
        ana_isleri_guncelle(self)
        self.araliklar = birlestir(self.araliklar)
        for d in self.kisi_durumu.values(): d['aktif_is'] = d['acik_is']
        from .is_ import tezgah_saati_hesapla
        self.araliklar.extend(tezgah_saati_hesapla(self))
        self.araliklar.sort(key=lambda a: (a['kisi'] or '', a['baslangic'], a['kova']))
        from .kurallar_v6 import baglantilari_yansit
        baglantilari_yansit(self)
        from .kurallar_v7 import tamamla
        tamamla(self)
        from .kurallar_v9 import tamamla as tamamla_v9
        tamamla_v9(self)
        self._an = None


def ilgili_nesneler(e):
    sonuc = [(x['tur'], x['kimlik']) for x in e['neyin_ustunde']]
    for ad in ('kisi', 'kimden', 'kime'):
        if e['girdiler'].get(ad): sonuc.append(('KISI', e['girdiler'][ad]))
    if e.get('adina'): sonuc.append(('KISI', e['adina']))
    return sorted(set(sonuc))
