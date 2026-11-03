import 'package:test/test.dart';

import '../tool/vektor_kosucu.dart';

void main() {
  final vektorler = vektorleriOku();
  test('Referans kapsamı: 29 cihaz ve 13 saf sorgu', () {
    expect(
      vektorler.where((v) => v.bolum == 'cihaz_denemeleri'),
      hasLength(29),
    );
    expect(vektorler.where((v) => v.bolum == 'saf_sorgular'), hasLength(13));
  });
  for (final v in vektorler) {
    test(v.ad, () => expect(farklar(v.beklenen, v.calistir()), isEmpty));
  }
}
