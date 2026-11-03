"""Görev atama ve TGG (SPEC › 8.7). Görev ve durumu çekirdektedir; modülde atamanın kaydı ve kapı sonucu durur."""
import time

from irp_sozlesme.baglanti import CekirdekHatasi

from ..depo import devir as depo_devir
from ..depo import dosya as depo_dosya
from ..depo import kapi as depo_kapi
from ..depo import plan as depo_plan
from . import dosya, yetki
from .devir import devir_gerek
from .gantt import gantt_satirlari
from .hatalar import ModulHatasi, gunluk, olay_reddi
from .kapi import KAPALI, KAPALI_MESAJI, proje_kapisi
from .zaman import an_metni

TGG_ONEKI = 'TGG: '
DENEME = 3


def gorev_satirlari(b, proje_kimligi):
    """Etap → görev satırları, GANTT'tan. Formun etap sürümü bu okumadakidir (bayatlık)."""
    proje = b.proje(proje_kimligi)
    with b.vt.islem() as c:
        devir = devir_gerek(c, proje_kimligi)
        ekler = depo_plan.etap_ekleri(c, proje_kimligi)
        atamalar = {a['gorev']: a for a in depo_kapi.gorev_atamalari(c, proje_kimligi)}
        kapi = proje_kapisi(c, proje_kimligi)
    etaplar = b.oku('ETAPLAR', None, proje=proje_kimligi)
    _, satirlar = gantt_satirlari(b, proje, etaplar, ekler, [devir['baslama_ani']], [])
    for s in satirlar:
        for g in s['gorevler']:
            a = atamalar.get(g['kimlik'])
            g['modulden'] = a is not None
            g['kapi'] = a and a['kapi']
            g['tgg_dosyasi'] = a and a['tgg_dosyasi']
    return {'etaplar': [{k: s[k] for k in ('kimlik', 'ad', 'birim', 'sorumlu', 'surum', 'tasarim_kapisi', 'renk',
                                           'renk_adi', 'gorevler')} for s in satirlar],
            'kapi': kapi, 'form': yetki.izinler(b, proje)['gorev_atayabilir'],
            'atamalar': [{'gorev': a['gorev'], 'etap': a['etap'], 'atayan': a['atayan'],
                          'atama_ani': an_metni(a['atama_ani']), 'kapi': a['kapi'], 'tgg_dosyasi': a['tgg_dosyasi']}
                         for a in atamalar.values()]}


def gorev_ata(b, proje_kimligi, govde):
    proje = b.proje(proje_kimligi)
    etap = _etap(b, proje_kimligi, govde['etap'])
    surum = govde.get('etap_surum') or etap.get('surum')
    tgg = bool(govde.get('tgg'))
    with b.vt.islem() as c:
        devir_gerek(c, proje_kimligi)
        ek = depo_plan.etap_ekleri(c, proje_kimligi).get(etap['kimlik'])
        kapi = 'KAPSAM_DISI'
        if ek and ek['tasarim_kapisi']:
            durum = proje_kapisi(c, proje_kimligi)
            if durum['durum'] == KAPALI:
                raise ModulHatasi(409, 'KAPI_KAPALI', KAPALI_MESAJI, gecebilir=b.sorumlu_mu(proje))
            kapi = durum['neden']
        tgg_dosyasi = _tgg_dosyasi(b, c, proje_kimligi, govde) if tgg else None
    gorev = _gorev_girdisi(b, proje_kimligi, govde, tgg)
    sonuclar = []
    for kisi in govde['kisiler']:
        cevap = b.olay('GOREV.ATADIM', {'gorevler': [{**gorev, 'kisi': kisi}]},
                       neyin_ustunde=[{'tur': 'ETAP', 'kimlik': etap['kimlik'], 'surum': surum}])
        if cevap.basarili:
            gorev_kimligi = f"{cevap['olay_kimligi']}/1"
            tgg_dosyasi = _kaydet(b, proje_kimligi, gorev_kimligi, etap['kimlik'], kapi, tgg_dosyasi, govde, cevap)
            sonuclar.append({'kisi': kisi, 'sonuc': 'BASARILI', 'gorev': gorev_kimligi})
            continue
        hata = olay_reddi(cevap, 'GOREV.ATADIM', _ret_mesajlari(b, kisi))
        sonuclar.append({'kisi': kisi, 'sonuc': 'REDDEDILDI', 'kod': hata.kod, 'mesaj': hata.mesaj,
                         'olay_kimligi': cevap.get('olay_kimligi')})
        if cevap.bayat:
            break           # etap değişmiş: kullanıcıya güncel hali gösterilir, karar yeniden sorulur
    if not any(s['sonuc'] == 'BASARILI' for s in sonuclar):
        hata.ek['sonuclar'] = sonuclar
        raise hata
    return {'sonuclar': sonuclar, 'kapi': kapi, 'tgg_dosyasi': tgg_dosyasi}


def _etap(b, proje, etap):
    try:
        e = b.oku('ETAP', etap)
    except CekirdekHatasi as h:
        if h.tur in ('YETKI', 'BICIM'):
            raise ModulHatasi(404, 'ETAP_YOK', 'Etap bulunamadı.') from None
        raise
    if not e or e.get('proje') != proje:
        raise ModulHatasi(404, 'ETAP_YOK', 'Etap bu projede değil.')
    return e


def _gorev_girdisi(b, proje, govde, tgg):
    """Zorunlular çekirdeğin şemasındandır (olay_semasi.json › GOREV.ATADIM)."""
    ad = govde['ad'].strip()
    if tgg and not ad.startswith(TGG_ONEKI):
        ad = TGG_ONEKI + ad
    onay_gerekli = True if tgg else bool(govde.get('onay_gerekli'))
    onaylayan = govde.get('onaylayan') or (b.kisi if tgg else None)
    if onay_gerekli and not onaylayan:
        raise ModulHatasi(422, 'DOGRULAMA', 'Onay gerekliyse onaylayan seçilmeli.',
                          hatalar=[{'alan': 'onaylayan', 'mesaj': 'Onaylayan gerekli.'}])
    g = {'ad': ad, 'nereye': 'PROJE', 'proje': proje, 'etap': govde['etap'], 'teslim_tarihi': govde['teslim_tarihi'],
         'zaman_degeri': govde['zaman_degeri'], 'zorluk': govde.get('zorluk') or 3,
         'oncelik': govde.get('oncelik') or 'NORMAL', 'onay_gerekli': onay_gerekli,
         'dosya_gerekli': True if tgg else bool(govde.get('dosya_gerekli'))}
    if onay_gerekli:
        g['onaylayan'] = onaylayan
    for k in ('is_tanimi', 'planlanan_baslangic', 'planlanan_bitis'):
        if govde.get(k):
            g[k] = govde[k]
    return g


def _tgg_dosyasi(b, c, proje, govde):
    """TGG görevinde bir TGG dosya kaydı seçmek ya da yeni açmak zorunludur. Yeni kayıt doğrulanır, çekirdek
    görevi kabul edince yazılır."""
    if govde.get('tgg_dosyasi'):
        d = depo_dosya.dosya(c, govde['tgg_dosyasi'])
        if not d or d['proje'] != proje or d['tur'] != 'TGG':
            raise ModulHatasi(422, 'DOGRULAMA', 'Seçilen kayıt bu projenin TGG dosyası değil.',
                              hatalar=[{'alan': 'tgg_dosyasi', 'mesaj': 'TGG dosyası değil.'}])
        return d['kimlik']
    yeni = govde.get('yeni_tgg')
    if not yeni:
        raise ModulHatasi(422, 'DOGRULAMA', 'TGG görevi için bir TGG dosya kaydı seçin ya da açın.',
                          hatalar=[{'alan': 'tgg_dosyasi', 'mesaj': 'Gerekli.'}])
    hatalar = dosya.dogrula({**yeni, 'tur': 'TGG'})
    if hatalar:
        raise ModulHatasi(422, 'DOGRULAMA', 'TGG dosya kaydında eksik alan var.', hatalar=hatalar)
    klasor = next(k for k in depo_devir.klasorler(c, proje) if k['sablon_kodu'] == dosya.VARSAYILAN_KLASOR['TGG'])
    yetki.gerek(yetki.dosya_ekleyebilir(b, b.proje(proje), klasor),
                'TGG dosya kaydını proje sorumlusu, yetkili ya da klasörün sorumlu birimi açar.')
    return None


def _kaydet(b, proje, gorev, etap, kapi, tgg_dosyasi, govde, cevap):
    """Çekirdek kabul ettikten sonra modülün kaydı: birkaç kez denenir, olmazsa olay kimliğiyle günlüğe (SPEC › 10)."""
    for i in range(DENEME):
        try:
            with b.vt.islem() as c:
                if govde.get('tgg') and tgg_dosyasi is None:
                    tgg_dosyasi = dosya.dosya_ekle(b, proje, {**govde['yeni_tgg'], 'tur': 'TGG'}, c=c)['kimlik']
                depo_kapi.gorev_atamasi_ekle(c, gorev, proje, etap, b.kisi, b.simdi(), kapi, tgg_dosyasi)
            return tgg_dosyasi
        except ModulHatasi:
            raise
        except Exception:  # noqa: BLE001
            if i == DENEME - 1:
                gunluk.exception('Görev ataması çekirdekte kabul edildi ama kaydı yazılamadı: olay %s, görev %s',
                                 cevap.get('olay_kimligi'), gorev)
                raise ModulHatasi(500, 'KAYIT', 'Beklenmeyen bir hata oldu.', olay_kimligi=cevap.get('olay_kimligi'))
            time.sleep(0.2 * (i + 1))


def _ret_mesajlari(b, kisi):
    if kisi == b.kisi:
        return {'YETKI': 'Kendinize görev veremezsiniz.'}
    return {'YETKI': 'Görev atanamadı: bu işe yetkiniz yok ya da kişinin birimi projede değil.'}
