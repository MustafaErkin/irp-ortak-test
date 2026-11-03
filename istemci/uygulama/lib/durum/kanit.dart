import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:image/image.dart' as im;

import '../bulut/uygulama_bulutu.dart';

class HazirFoto {
  HazirFoto(this.bytes, this.ad);
  final Uint8List bytes;
  final String ad;
  Json alanlar(String olay, int sira) => {
    'dosya_kimligi': 'F-$olay/$sira',
    'parmak_izi': sha256.convert(bytes).toString(),
    'ad': ad,
    'boyut': bytes.length,
    'tur': 'image/jpeg',
  };
  static HazirFoto hazirla(Uint8List bytes, String ad) {
    var resim = im.decodeImage(bytes);
    if (resim == null) throw const FormatException('Fotoğraf açılamadı');
    resim = im.bakeOrientation(resim);
    if (resim.width > 1600 || resim.height > 1600) {
      resim = im.copyResize(
        resim,
        width: resim.width >= resim.height ? 1600 : null,
        height: resim.height > resim.width ? 1600 : null,
      );
    }
    final temizAd = ad
        .split(RegExp(r'[/\\]'))
        .last
        .replaceAll(RegExp(r'[^\w.-]'), '_');
    return HazirFoto(
      Uint8List.fromList(im.encodeJpg(resim, quality: 85)),
      '${temizAd.replaceFirst(RegExp(r'\.[^.]*$'), '')}.jpg',
    );
  }
}

/// Teslim belgesi; görüntüler fotoğraf yolunda küçültülür, diğer baytlar korunur.
class HazirDosya extends HazirFoto {
  HazirDosya(super.bytes, super.ad, this.tur);
  final String tur;
  @override
  Json alanlar(String olay, int sira) => {
    ...super.alanlar(olay, sira),
    'tur': tur,
  };
  static HazirFoto dosya(Uint8List bytes, String ad) {
    if (bytes.isEmpty) throw const FormatException('Dosya boş');
    final temiz = ad
        .split(RegExp(r'[/\\]'))
        .last
        .replaceAll(RegExp(r'[^\w.-]'), '_');
    final uzanti = temiz.split('.').last.toLowerCase();
    if (const ['jpg', 'jpeg', 'png', 'webp'].contains(uzanti)) {
      return HazirFoto.hazirla(bytes, temiz);
    }
    return HazirDosya(bytes, temiz, switch (uzanti) {
      'pdf' => 'application/pdf',
      'txt' => 'text/plain',
      'csv' => 'text/csv',
      _ => 'application/octet-stream',
    });
  }
}
