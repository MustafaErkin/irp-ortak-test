"""İsteğin bağlamını kuran FastAPI bağımlılıkları."""
from fastapi import Depends, Header, Request

from irp_sozlesme.baglanti import CekirdekHatasi

from ..alan.baglam import Baglam
from ..alan.hatalar import ModulHatasi


def kaynaklar(request: Request):
    return request.app.state.kaynaklar


def baglam(authorization: str | None = Header(default=None), k=Depends(kaynaklar)) -> Baglam:
    """Ekran kullanıcının erişim anahtarını iletir; arka yüz onunla oturum açar. Modül şifre görmez, saklamaz."""
    if not authorization or not authorization.startswith('Bearer '):
        raise ModulHatasi(401, 'OTURUM_YOK', 'Oturum açın.')
    try:
        oturum = k.cekirdek.oturum(authorization.removeprefix('Bearer ').strip())
    except CekirdekHatasi:
        raise ModulHatasi(401, 'OTURUM_YOK', 'Oturumunuz geçersiz; yeniden girin.') from None
    return Baglam(k.cekirdek, oturum, k.vt, k.ayarlar)
