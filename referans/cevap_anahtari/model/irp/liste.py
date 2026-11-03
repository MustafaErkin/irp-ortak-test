"""A11: listelerde sıra, devir ve bitiş."""


def yerlestir(liste, is_kimligi, sira):
    if is_kimligi in liste:
        liste.remove(is_kimligi)
    liste.insert(max(0, min(len(liste), sira - 1)), is_kimligi)


def liste_hesapla(depo, kisi, an=None):
    if an is None or an == depo.saat.simdi():
        return list(depo.listeler.get(kisi, []))
    from .motor import Motor
    from .saat import Saat
    g = Motor(Saat(an))
    g.yurut(list(depo.olaylar.values()))
    return g.listeler.get(kisi, [])
