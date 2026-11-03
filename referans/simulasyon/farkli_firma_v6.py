"""Depoya taşınmamış eski üreticinin yerine donmuş firma akışını yürütür."""
import json
from pathlib import Path


def calistir():
    # Kaynak model önce yüklenir; paket oynatıcısı başka model seçemez.
    import irp
    from cevap_anahtari.yurut import yurut
    from cevap_anahtari.karsilastir import farklar
    paket = Path(__file__).resolve().parents[1] / 'cevap_anahtari/simulasyon'
    girdi = json.loads((paket / 'farkli_firma.girdi.json').read_text('utf-8'))
    beklenen = json.loads((paket / 'farkli_firma.beklenen.json').read_text('utf-8'))
    depolar = []
    sonuc = yurut(girdi, tam_kontrol=True, denetim_depolari=depolar)
    assert not farklar(beklenen, sonuc), 'Farklı firma donmuş sonucu değişti'
    d = next(d for d in depolar if d.kurulum_tamamlandi)
    assert not any(d.isleme_hatalari for d in depolar)
    return girdi, d, {'yetki_satiri': len(d.yetki_kurallari)}
