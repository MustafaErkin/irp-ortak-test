"""İsteğin bağlamı: kullanıcının oturumu, rolleri (KISILER'den, istek başına bir kez), veritabanı bağlantısı."""
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
import psycopg

from .. import vt
from ..alan import yetki
from ..baglanti import Cekirdek, CekirdekHatasi, Oturum
from .hatalar import ModulHatasi, proje_gorunmuyor


@dataclass
class Uygulama:
    """Arka yüzün paylaşılan durumu."""
    cekirdek: Cekirdek | None
    vt_url: str
    saglayici: Any = None
    gelistirme: bool = False


@dataclass
class Istek:
    uyg: Uygulama
    oturum: Oturum
    b: psycopg.Connection
    hesaplaniyor: bool = False
    _kisi_kaydi: dict | None = None
    _projeler: dict = field(default_factory=dict)
    onbellek: dict = field(default_factory=dict)

    @property
    def cekirdek(self) -> Cekirdek:
        return self.uyg.cekirdek

    @property
    def kisi(self) -> str:
        return self.oturum.kisi

    @property
    def anahtar(self) -> str:
        return self.oturum.anahtar

    def simdi(self) -> str:
        return self.cekirdek.simdi()

    def oku(self, veri: str, hedef=None, **g):
        okuma = self.oturum.oku(veri, hedef, **g)
        if not okuma.guncel:
            self.hesaplaniyor = True
        return okuma.deger

    # ---- kişi ve roller
    def kisiler(self) -> list[dict]:
        if 'KISILER' not in self.onbellek:
            self.onbellek['KISILER'] = self.oku('KISILER') or []
        return self.onbellek['KISILER']

    @property
    def kisi_kaydi(self) -> dict:
        if self._kisi_kaydi is None:
            kayit = next((k for k in self.kisiler() if k['kimlik'] == self.kisi), None)
            if not kayit:
                raise ModulHatasi(401, 'OTURUM', 'Oturum bulunamadı; yeniden giriş yapın.')
            self._kisi_kaydi = kayit
        return self._kisi_kaydi

    @property
    def roller(self) -> set[str]:
        return set(self.kisi_kaydi.get('roller') or [])

    def rol_var(self, kume) -> bool:
        return yetki.var_mi(self.roller, kume)

    def rol_gerek(self, kume, mesaj: str | None = None) -> None:
        if not self.rol_var(kume):
            raise ModulHatasi(403, 'YETKI', mesaj or yetki.MESAJLAR.get(kume, 'Bu işe yetkiniz yok.'))

    # ---- proje: modülün her proje işinden önce kullanıcının gözüyle okunur (SPEC › 6)
    def proje(self, proje: str) -> dict | None:
        if proje not in self._projeler:
            try:
                self._projeler[proje] = self.oku('PROJE', proje)
            except CekirdekHatasi as h:
                if h.tur == 'YETKI':
                    raise proje_gorunmuyor() from h
                raise
        return self._projeler[proje]

    def proje_gorur_mu(self, proje: str) -> bool:
        try:
            return self.proje(proje) is not None
        except ModulHatasi:
            return False

    def cevap(self, govde: dict) -> dict:
        if self.hesaplaniyor:
            govde = dict(govde, hesaplaniyor=True)
        return govde


def _bearer(request: Request) -> str:
    deger = request.headers.get('authorization') or ''
    if not deger.lower().startswith('bearer ') or not deger[7:].strip():
        raise ModulHatasi(401, 'OTURUM', 'Oturum yok; giriş yapın.')
    return deger[7:].strip()


def istek(request: Request) -> Iterator[Istek]:
    u: Uygulama = request.app.state.m11a
    try:
        oturum = u.cekirdek.oturum(_bearer(request))
    except CekirdekHatasi as h:
        raise ModulHatasi(401, 'OTURUM', 'Oturum geçersiz; yeniden giriş yapın.') from h
    with vt.baglan(u.vt_url, autocommit=True) as b:
        yield Istek(u, oturum, b)
