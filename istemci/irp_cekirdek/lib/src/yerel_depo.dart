import 'veri.dart';

/// Bir cihazın tek sahipli yerel deposu. Yazma dönmeden veri kalıcı olmalıdır.
abstract interface class YerelDepo {
  Sozluk? oku();
  void yaz(Sozluk veri);
}

class BellekDeposu implements YerelDepo {
  BellekDeposu([Sozluk? veri]) : _veri = kopyala(veri);
  Sozluk? _veri;
  @override
  Sozluk? oku() => kopyala(_veri);
  @override
  void yaz(Sozluk veri) {
    _veri = kopyala(veri);
  }
}
