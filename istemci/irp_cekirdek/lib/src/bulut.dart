import 'dart:async';

import 'veri.dart';

abstract interface class Bulut {
  Future<Sozluk> olayEkle(Sozluk olay, {required String oturum});
}

/// Ağ kullanmaz; verilen cevapları ve çağrı sırasını testte görünür kılar.
class SahteBulut implements Bulut {
  SahteBulut({this.cevapla});
  final FutureOr<Sozluk> Function(Sozluk olay, String oturum)? cevapla;
  final List<Sozluk> cagrilar = [];

  @override
  Future<Sozluk> olayEkle(Sozluk olay, {required String oturum}) async {
    cagrilar.add({'olay': kopyala(olay), 'oturum': oturum});
    return cevapla == null
        ? {'sonuc': 'BASARILI'}
        : await cevapla!(olay, oturum);
  }
}
