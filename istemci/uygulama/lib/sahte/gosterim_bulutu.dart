import 'package:flutter/foundation.dart';

import '../bulut/uygulama_bulutu.dart';

/// Hazır okuma zarfları. Auth, ağ, çekirdek ve olay günlüğü kullanılmaz.
class GosterimBulutu implements UygulamaBulutu {
  GosterimBulutu(this.fikstur);
  @override
  Future<Json> olayAkisi({int sonra = 0, int adet = 200}) async => _yazilamaz();
  final Json fikstur;
  Json get bilgi => Json.from(fikstur['gosterim']);
  @override
  bool get gosteriMi => false;
  Never _yazilamaz() => throw StateError('Gösterim salt okunurdur');
  @override
  Future<Json> oku(String veri, {String? hedef, Json? g}) async {
    final qs = fikstur['anlar']['gosterim']['K001']['okumalar'] as List;
    final q = qs
        .cast<Map>()
        .where(
          (q) =>
              q['veri'] == veri &&
              q['hedef'] == hedef &&
              mapEquals(q['g'] as Map?, g),
        )
        .firstOrNull;
    if (q == null) {
      throw StateError('Gösterim okuması bulunamadı: $veri / $hedef / $g');
    }
    return Json.from(q['cevap']);
  }

  @override
  Stream<String> sinyaller(String kisi, {Set<String> ekKanallar = const {}}) =>
      const Stream.empty();
  @override
  Future<Json> giris(String kod, String parola) async => _yazilamaz();
  @override
  Future<void> parolaDegistir(String pin) async => _yazilamaz();
  @override
  Future<Json> oturumYenile(String refreshToken) async => _yazilamaz();
  @override
  Future<String> simdi() async => bilgi['an'] as String;
  @override
  Future<String> cihazKaydol(String cihaz) async => _yazilamaz();
  @override
  Future<List<String>> cihazEsitle(String cihaz, {String? harf}) async =>
      _yazilamaz();
  @override
  Future<Json> olayEkle(
    Json olay, {
    required String oturum,
    Json? hassasEk,
  }) async => _yazilamaz();
  @override
  Future<void> kanitYukle(String kimlik, Uint8List bytes, String tur) async =>
      _yazilamaz();
  @override
  Future<void> gosteriSifirla() async => _yazilamaz();
}
