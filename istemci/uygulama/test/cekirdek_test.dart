import 'package:flutter_test/flutter_test.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';

void main() {
  test('Uygulama yerel çekirdek paketiyle çevrimdışı olay üretir', () async {
    final depo = BellekDeposu();
    final c = Cihaz(
      'K017',
      'T',
      Saat('2026-10-22T09:00:00+03:00'),
      yerelDepo: depo,
    );
    final olay = await c.olayYaz('MESAI.GIRDIM', {}, baglanti: false);
    expect(olay['olay_kimligi'], 'K017-2610220001-T');
    expect(depo.oku()!['gunluk'][olay['olay_kimligi']]['durum'], 'BEKLIYOR');
    expect(c.ekranHali({})['son_hal']['durum'], 'CALISMIYOR');
  });
}
