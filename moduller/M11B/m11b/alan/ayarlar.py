"""Ayarlar: şablonların birim eşlemesi (SPEC › 2.1 › 11). Yalnızca YETKILI. Birimler çekirdekten okunur;
modül yalnızca birim kodunu değer olarak tutar."""
from ..depo import devir as depo
from . import yetki
from .hatalar import ModulHatasi


def sablonlar(b):
    yetki.gerek(b.yetkili, 'Ayarları yetkili yapar.')
    with b.vt.islem() as c:
        etaplar, klasorler, kategoriler = depo.etap_sablonu(c), depo.klasor_sablonu(c), depo.not_kategorileri(c)
    return {
        'etaplar': [{'kod': e['kod'], 'ad': e['ad'], 'sira': e['sira'], 'paralel_grup': e['paralel_grup'],
                     'varsayilan_birim': e['varsayilan_birim'], 'tasarim_kapisi': e['tasarim_kapisi'],
                     'bas_orani': float(e['bas_orani']), 'bit_orani': float(e['bit_orani']), 'aktif': e['aktif']}
                    for e in etaplar],
        'klasorler': [{'kod': k['kod'], 'ad': k['ad'], 'aciklama': k['aciklama'], 'sorumlu_birim': k['sorumlu_birim']}
                      for k in klasorler],
        'kategoriler': [{'kod': k['kod'], 'ad': k['ad'], 'varsayilan_birim': k['varsayilan_birim'],
                         'acilis_listesinde': k['acilis_listesinde']} for k in kategoriler],
        'birimler': [{'kimlik': x['kimlik'], 'ad': x.get('ad')} for x in b.birimler],
    }


def sablonlari_kaydet(b, govde):
    yetki.gerek(b.yetkili, 'Ayarları yetkili yapar.')
    birimler = {x['kimlik'] for x in b.birimler}
    hatalar = []
    for grup, alan in (('etaplar', 'varsayilan_birim'), ('klasorler', 'sorumlu_birim'),
                       ('kategoriler', 'varsayilan_birim')):
        for x in govde.get(grup) or []:
            if x.get(alan) and x[alan] not in birimler:
                hatalar.append({'alan': f'{grup}.{x["kod"]}', 'mesaj': f'Birim bulunamadı: {x[alan]}'})
    if hatalar:
        raise ModulHatasi(422, 'DOGRULAMA', 'Ayarlarda bulunamayan birim var.', hatalar=hatalar)
    with b.vt.islem() as c:
        for x in govde.get('etaplar') or []:
            _bulundu(depo.etap_sablonu_guncelle(c, x['kod'], x.get('varsayilan_birim'), x['aktif']), 'etaplar', x)
        for x in govde.get('klasorler') or []:
            _bulundu(depo.klasor_sablonu_guncelle(c, x['kod'], x.get('sorumlu_birim')), 'klasorler', x)
        for x in govde.get('kategoriler') or []:
            _bulundu(depo.not_kategorisi_guncelle(c, x['kod'], x.get('varsayilan_birim')), 'kategoriler', x)
    return sablonlar(b)


def _bulundu(sayi, grup, x):
    if not sayi:
        raise ModulHatasi(422, 'DOGRULAMA', 'Şablon bulunamadı.', hatalar=[{'alan': f'{grup}.{x["kod"]}',
                                                                          'mesaj': 'Bulunamadı.'}])
