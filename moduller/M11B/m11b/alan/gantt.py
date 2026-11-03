"""Gantt ve etap renkleri (SPEC › 8.3).

Gerçekleşen, durum ve ilerleme çekirdeğin GANTT okumasından gelir; modül yeniden hesaplamaz. Renk modülün kuralıdır.
"""
from datetime import timedelta

from ..depo import plan as depo_plan
from . import yetki
from .devir import devir_gerek
from .plan import ONAYSIZ_UYARISI, cekirdek_defteri
from .zaman import an, gun

GRI, YESIL, SARI, KIRMIZI = 'GRI', 'YESIL', 'SARI', 'KIRMIZI'
RENK_ADLARI = {GRI: 'Plan onaylanmadı', YESIL: 'Yolunda', SARI: 'Gecikme riski', KIRMIZI: 'Gecikti'}
SABIT_NOT = 'Etap özeti projenin gerçekleşenini gösterir; görev ayrıntıları yetkinize göre görünür.'
TAHMIN_LEJANTI = 'Tahmin: sonraki faz'
HESAPLANIYOR = 'Çekirdek hâlâ hesaplıyor; gösterilen bilgi birkaç saniye eski olabilir.'


def etap_rengi(satir, simdi, tahmin_bitis=None):
    """GANTT'ın ETAP satırından renk. planlanan_bitis dışlayıcıdır: bitiş gününün ertesi günü 00:00."""
    if not satir or not satir.get('planlanan_bitis'):
        return GRI
    plan_bitis = an(satir['planlanan_bitis'])
    if satir.get('durum') == 'BITTI':
        gb = satir.get('gerceklesen_bitis')
        return KIRMIZI if gb and an(gb) > plan_bitis else YESIL
    if an(simdi) >= plan_bitis:
        return KIRMIZI
    if tahmin_bitis and an(tahmin_bitis) > plan_bitis:
        return SARI
    return YESIL


def pencere(baslangiclar, bitisler):
    """bas = en erken − 7 gün, bit = en geç + 14 gün. GANTT'ın `bas`'ı zorunludur."""
    bas = [gun(x) for x in baslangiclar if x]
    bit = [gun(x) for x in bitisler if x]
    if not bas:
        return None, None
    return (min(bas) - timedelta(days=7)).isoformat(), (max(bit or bas) + timedelta(days=14)).isoformat()


def sirala(etaplar, ekler):
    """Sıra etap_ekleri.sira'ya göre; eki olmayanlar sonda, başlangıç tarihine göre."""
    return sorted(etaplar, key=lambda e: (0, ekler[e['kimlik']]['sira'], '') if e['kimlik'] in ekler
                  else (1, 0, e.get('baslangic') or ''))


def gantt_satirlari(b, proje, etaplar, ekler, adaylar_bas, adaylar_bit):
    """Bir GANTT okumasıyla etap satırları ve renkleri; projeler listesi de bunu kullanır."""
    bas, bit = pencere(adaylar_bas + [e.get('baslangic') for e in etaplar],
                       adaylar_bit + [e.get('bitis') for e in etaplar] +
                       [proje.get('teslim_tarihi'), proje.get('kesin_kabul_tarihi')])
    okunan = b.oku('GANTT', proje['kimlik'], bas=bas, bit=bit, adlar=True) if bas else []
    gantt_etap = {x['kimlik']: x for x in okunan if x.get('tur') == 'ETAP'}
    alt = {}
    for x in okunan:
        if x.get('tur') in ('GOREV', 'IS') and x.get('etap'):
            alt.setdefault(x['etap'], []).append(x)
    simdi = b.simdi()
    satirlar = []
    for e in sirala(etaplar, ekler):
        g, ek = gantt_etap.get(e['kimlik']), ekler.get(e['kimlik'], {})
        renk = etap_rengi(g, simdi)
        satirlar.append({
            'kimlik': e['kimlik'], 'ad': e.get('ad'), 'birim': e.get('birim'), 'sorumlu': e.get('sorumlu'),
            'surum': e.get('surum'), 'sira': ek.get('sira'), 'paralel_grup': ek.get('paralel_grup'),
            'sablon_kodu': ek.get('sablon_kodu'), 'tasarim_kapisi': bool(ek.get('tasarim_kapisi')),
            'planlanan_baslangic': g and g.get('planlanan_baslangic'), 'planlanan_bitis': g and g.get('planlanan_bitis'),
            'gerceklesen_baslangic': g and g.get('gerceklesen_baslangic'),
            'gerceklesen_bitis': g and g.get('gerceklesen_bitis'),
            'durum': g and g.get('durum'), 'ilerleme': g.get('ilerleme') if g else None,
            'renk': renk, 'renk_adi': RENK_ADLARI[renk],
            'benim': e.get('birim') == b.ben.get('birim') or (e.get('sorumlu') is not None and e['sorumlu'] == b.kisi),
            'gorevler': [_alt_satir(x) for x in sorted(alt.get(e['kimlik'], []),
                                                       key=lambda x: x.get('planlanan_bitis') or '')],
        })
    return {'bas': bas, 'bit': bit, 'simdi': simdi}, satirlar


def _alt_satir(x):
    return {k: x.get(k) for k in ('kimlik', 'ad', 'tur', 'durum', 'kisi', 'planlanan_baslangic', 'planlanan_bitis',
                                  'gerceklesen_baslangic', 'gerceklesen_bitis', 'ilerleme')}


def gantt(b, proje_kimligi):
    proje = b.proje(proje_kimligi)
    with b.vt.islem() as c:
        devir = devir_gerek(c, proje_kimligi)
        ekler = depo_plan.etap_ekleri(c, proje_kimligi)
    plan = b.oku('PLAN', proje_kimligi, surumler=True)
    etaplar = b.oku('ETAPLAR', None, proje=proje_kimligi)
    b0, son = plan.get('B0') or {}, plan.get('son_onayli') or {}
    pen, satirlar = gantt_satirlari(
        b, proje, etaplar, ekler,
        [x.get('baslangic') for x in [*b0.values(), *son.values()]] + [devir['baslama_ani']],
        [x.get('bitis') for x in [*b0.values(), *son.values()]])
    for s in satirlar:
        s['b0'] = _b0_izi(b0.get(s['kimlik']), son.get(s['kimlik']))
    uyarilar = [ONAYSIZ_UYARISI] if plan.get('onaysiz_degisti') else []
    if b.hesaplaniyor:
        uyarilar.append(HESAPLANIYOR)
    return {
        'pencere': pen, 'etaplar': satirlar, 'uyarilar': uyarilar, 'sabit_not': SABIT_NOT,
        'lejant': {**RENK_ADLARI, 'TAHMIN': TAHMIN_LEJANTI}, 'surum_defteri': cekirdek_defteri(plan),
        'surum_notu': None, 'plan_degistirebilir': yetki.sorumlu_ya_da_yetkili(b, proje),
        'cekirdek_surumleri': plan.get('surumler', []),
        'onaysiz_degisti': bool(plan.get('onaysiz_degisti')),
    }


def _b0_izi(b0, son):
    """B0'daki tarihler son onaylıdan farklıysa ince bir çerçeve çizilir."""
    if not b0 or not son or (b0.get('baslangic'), b0.get('bitis')) == (son.get('baslangic'), son.get('bitis')):
        return None
    return {'baslangic': b0['baslangic'], 'bitis': b0['bitis']}


def kirmizi_sayisi(satirlar):
    return sum(1 for s in satirlar if s['renk'] == KIRMIZI)
