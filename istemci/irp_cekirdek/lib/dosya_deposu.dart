/// Yalnız dosya sistemi bulunan hedefler bu dosyayı içe aktarır.
library;

import 'dart:convert';
import 'dart:io';

import 'src/olay.dart';
import 'src/veri.dart';
import 'src/yerel_depo.dart';

class DosyaDeposu implements YerelDepo {
  DosyaDeposu(String yol) : dosya = File(yol);
  final File dosya;

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:13 (__init__ okuma).
  @override
  Sozluk? oku() => dosya.existsSync()
      ? jsonDecode(dosya.readAsStringSync(encoding: utf8)) as Sozluk
      : null;

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:20 (kaydet).
  @override
  void yaz(Sozluk veri) {
    dosya.parent.createSync(recursive: true);
    final ad = dosya.uri.pathSegments.last;
    final nokta = ad.lastIndexOf('.');
    final geciciAd = '${nokta > 0 ? ad.substring(0, nokta) : ad}.tmp';
    // .tmp adlı ana dosyada da eski veri yarım yazımdan korunur.
    final gecici = File(
      '${dosya.parent.path}${Platform.pathSeparator}${geciciAd == ad ? '$ad.tmp' : geciciAd}',
    );
    gecici.writeAsStringSync(kodla(veri), encoding: utf8, flush: true);
    gecici.renameSync(dosya.path);
  }
}
