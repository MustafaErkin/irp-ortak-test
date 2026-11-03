"""A0: iş saati ve teslim damgası ayrıdır; her ikisi de dışarıdan verilir."""
from datetime import datetime, date, time, timedelta, timezone

YEREL = timezone(timedelta(hours=3))


def an(deger):
    if isinstance(deger, datetime):
        if deger.tzinfo is None:
            raise ValueError('Saat dilimi zorunlu')
        return deger.astimezone(YEREL)
    return datetime.fromisoformat(deger).replace(tzinfo=YEREL) if '+' not in deger and not deger.endswith('Z') else datetime.fromisoformat(deger.replace('Z', '+00:00')).astimezone(YEREL)


def gun(deger):
    if isinstance(deger, datetime):
        return deger.astimezone(YEREL).date()
    return deger if isinstance(deger, date) else date.fromisoformat(deger)


def gun_ani(tarih, saat='00:00'):
    return datetime.combine(gun(tarih), time.fromisoformat(saat), YEREL)


class Saat:
    def __init__(self, simdi, gercek=None, demo=False):
        self.is_ani = an(simdi)
        self.gercek_ani = an(gercek) if gercek else self.is_ani
        self.demo = demo

    def simdi(self):
        return self.is_ani

    def gercek(self):
        return self.gercek_ani

    def ilerlet(self, hedef):
        hedef = an(hedef)
        if hedef < self.is_ani:
            raise ValueError('A0: geri almak icin demo_sifirla gerekir')
        self.is_ani = hedef
        if not self.demo:
            self.gercek_ani = hedef

    @property
    def saat_kaydirma(self):
        return self.is_ani - self.gercek_ani if self.demo else timedelta(0)
