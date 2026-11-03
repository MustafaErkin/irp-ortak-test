"""Uygulamanın yönlendiricileri."""


def hepsi(ayarlar):
    from . import ben, gelistirme, genel, notlar, plan, projeler
    yonlendiriciler = [ben.yonlendirici, projeler.yonlendirici, plan.yonlendirici, notlar.yonlendirici,
                       genel.yonlendirici]
    if ayarlar.gelistirme:
        yonlendiriciler.append(gelistirme.yonlendirici)
    return yonlendiriciler
