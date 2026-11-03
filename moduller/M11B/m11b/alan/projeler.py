"""Projeler listesi ve satırı (SPEC › 8.10). Satır M11B.PROJE_SATIRI'nın da cevabıdır."""
from ..depo import devir as depo
from ..depo import plan as depo_plan
from .acilis import acilis
from .gantt import gantt_satirlari, kirmizi_sayisi
from .hatalar import ModulHatasi


def projeler_listesi(b):
    """Yeni projeler dahil kullanıcının izinli çekirdek listesi; modül devri hazır varsayılmaz."""
    with b.vt.islem() as c:
        devirler = depo.devirler(c)
    satirlar = []
    by_project={d['proje']:d for d in devirler}
    for p in b.oku('PROJELER'):
        d=by_project.get(p['kimlik'])
        if d is None:
            satirlar.append({'proje':p['kimlik'],'kod':p.get('kod'),'ad':p['ad'],
                'teslim_tarihi':p.get('teslim_tarihi'),'kirmizi_etap_sayisi':0,
                'plan_var':False,'devir_basladi':False})
            continue
        try:
            satirlar.append({**proje_satiri(b, d['proje'], d),'devir_basladi':True})
        except ModulHatasi as e:
            if e.kod != 'PROJE_GORUNMUYOR':
                raise
    satirlar.sort(key=lambda s: (-s['kirmizi_etap_sayisi'], s['teslim_tarihi'] or '9999-12-31'))
    return satirlar


def proje_satiri(b, proje_kimligi, devir=None):
    proje = b.proje(proje_kimligi)
    if devir is None:
        with b.vt.islem() as c:
            devir = depo.devir(c, proje_kimligi)
        if devir is None:
            raise ModulHatasi(404, 'DEVIR_YOK', 'Bu projenin devri başlatılmadı.')
    with b.vt.islem() as c:
        ekler = depo_plan.etap_ekleri(c, proje_kimligi)
    # Proje başına bir GANTT okuması; renkler ve "plan var mı" oradan. Etapların adı ETAPLAR'dan (ipucu için).
    etaplar = b.oku('ETAPLAR', None, proje=proje_kimligi)
    _, satirlar = gantt_satirlari(b, proje, etaplar, ekler, [devir['baslama_ani']], [])
    liste = acilis(b, proje_kimligi, plan_var=any(x['planlanan_bitis'] for x in satirlar))
    return {
        'proje': proje['kimlik'], 'kod': proje.get('kod'), 'ad': proje.get('ad'), 'musteri': proje.get('musteri'),
        'sorumlu': {'kimlik': proje.get('sorumlu'), 'ad': b.kisi_adi(proje.get('sorumlu'))},
        'teslim_tarihi': proje.get('teslim_tarihi'),
        'etaplar': [{'kimlik': x['kimlik'], 'ad': x['ad'], 'renk': x['renk'], 'renk_adi': x['renk_adi']}
                    for x in satirlar],
        'kirmizi_etap_sayisi': kirmizi_sayisi(satirlar),
        'plan_var': any(x['planlanan_bitis'] for x in satirlar),
        'acilis': {'tamam_sayisi': liste['tamam_sayisi'], 'toplam': liste['toplam']},
        'devir_tamamlandi': liste['tamamlanma_ani'] is not None,
    }
