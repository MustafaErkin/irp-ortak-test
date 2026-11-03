"""PLAN_YAYIMLANDI bildirimi (SPEC › 8.12). Bildirim olay değildir; servis gözüyle çekirdeğin bildirim kapısına
bırakılır. Metin yalnızca bu projenin bilgisini taşır."""
from ..depo import plan as depo_plan
from .hatalar import gunluk
from .plan import NEDENLER

KURAL = 'PLAN_YAYIMLANDI'


def kayit(proje, surum_no):
    return {'tur': 'PROJE', 'kimlik': proje, 'modul_kaydi': f'plan B{surum_no}' if surum_no is not None else 'plan'}


def alicilar(etaplar):
    """Her etabın birimi için birimin yöneticileri; sorumlusu olan her etap için ayrıca sorumlusu. Tekrarlar ayıklanır."""
    sonuc = []
    for e in etaplar:
        for a in ({'tur': 'BIRIM_YONETICILERI', 'kimlik': e.get('birim')},
                  {'tur': 'KISI', 'kimlik': e.get('sorumlu')}):
            if a['kimlik'] and a not in sonuc:
                sonuc.append(a)
    return sonuc


def metin(proje, surum_no, tur, neden):
    surum = f'Plan B{surum_no}' if surum_no is not None else 'Plan'
    m = f"{proje.get('kod')} {proje.get('ad')} · {surum} yayımlandı"
    if tur == 'DEGISIKLIK' and neden in NEDENLER:
        m += f' · {NEDENLER[neden]}'
    return m + ". Etap hedefleriniz Gantt'ta."


def birak(servis, proje, etaplar, degisiklik):
    cevap = servis.bildirim_birak(KURAL, kayit(proje['kimlik'], degisiklik['surum_no']), alicilar(etaplar),
                                  metin(proje, degisiklik['surum_no'], degisiklik['tur'], degisiklik['neden']), 'BILGI')
    if cevap.get('suzulenler'):
        gunluk.info('PLAN_YAYIMLANDI (proje %s) süzülenler: %s', proje['kimlik'], cevap['suzulenler'])
    if cevap.get('alici_kalmadi'):
        gunluk.warning('PLAN_YAYIMLANDI (proje %s): alıcı kalmadı', proje['kimlik'])
    return cevap


def plan_yayimlandi_birak(b, proje_kimligi, degisiklik):
    """Onaydan hemen sonra. Etaplar onaylayan kullanıcının gözüyle okunur."""
    etaplar = b.oku('ETAPLAR', None, proje=proje_kimligi)
    cevap = birak(b.cekirdek.servis(), b.proje(proje_kimligi), etaplar, degisiklik)
    with b.vt.islem() as c:
        depo_plan.bildirim_isaretle(c, proje_kimligi)
    return {k: cevap.get(k) for k in ('alicilar', 'suzulenler', 'yeni', 'guncellenen', 'alici_kalmadi')}
