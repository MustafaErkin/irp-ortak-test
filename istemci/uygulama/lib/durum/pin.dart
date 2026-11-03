import 'dart:convert';
import 'dart:math';

import 'package:cryptography/cryptography.dart';

import '../bulut/uygulama_bulutu.dart';

class Pin {
  static final _pbkdf = Pbkdf2(
    macAlgorithm: Hmac.sha256(),
    iterations: 210000,
    bits: 256,
  );
  static Future<List<int>> _ozet(String pin, List<int> tuz) async =>
      (await _pbkdf.deriveKey(
        secretKey: SecretKey(utf8.encode(pin)),
        nonce: tuz,
      )).extractBytes();
  static Future<Json> olustur(String pin) async {
    if (!RegExp(r'^\d{6}$').hasMatch(pin)) {
      throw ArgumentError('Şifre 6 rakam olmalı');
    }
    final rastgele = Random.secure();
    final tuz = List.generate(16, (_) => rastgele.nextInt(256));
    return {
      'tuz': base64Encode(tuz),
      'ozet': base64Encode(await _ozet(pin, tuz)),
      'algoritma': 'PBKDF2-HMAC-SHA256',
      'tekrar': 210000,
    };
  }

  static Future<bool> dogrula(String pin, Json kayit) async {
    final gelen = await _ozet(pin, base64Decode(kayit['tuz'] as String));
    final sakli = base64Decode(kayit['ozet'] as String);
    var fark = gelen.length ^ sakli.length;
    for (var i = 0; i < gelen.length && i < sakli.length; i++) {
      fark |= gelen[i] ^ sakli[i];
    }
    return fark == 0;
  }
}
