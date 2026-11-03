import 'saat.dart';
import 'veri.dart';

abstract interface class TakvimKaynagi {
  Sozluk takvim(Object tarih, String? kisi);
}

// Kaynak: referans/cevap_anahtari/model/irp/gorev.py:8 (son_teslim_ani).
An? sonTeslimAni(Sozluk g, [TakvimKaynagi? m]) {
  final saat = m != null && dolu(g['teslim_tarihi'])
      ? m.takvim(g['teslim_tarihi'], g['kisi'])['mesai_bitis']
      : al(g, 'takvim_teslim_saati', '18:00');
  return dolu(g['teslim_tarihi'])
      ? gunAni(
          g['teslim_tarihi'],
          dolu(g['teslim_saati']) ? g['teslim_saati'] : saat,
        )
      : null;
}
