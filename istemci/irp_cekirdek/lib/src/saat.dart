import 'hata.dart';

const yerelFark = Duration(hours: 3);

String _basamak(int x, int n) => x.toString().padLeft(n, '0');

/// An ile tarih birbirinden ayrıdır. Tarih saat dilimi taşımaz.
class Gun {
  Gun(this.yil, this.ay, this.gun) {
    final d = DateTime.utc(yil, ay, gun);
    if (yil < 1 ||
        yil > 9999 ||
        d.year != yil ||
        d.month != ay ||
        d.day != gun) {
      throw const ModelHatasi('ValueError', 'day is out of range for month');
    }
  }
  factory Gun.parse(String s) {
    final m = RegExp(r'^(\d{4})-?(\d{2})-?(\d{2})$').firstMatch(s);
    if (m == null) {
      throw ModelHatasi('ValueError', "Invalid isoformat string: '$s'");
    }
    return Gun(int.parse(m[1]!), int.parse(m[2]!), int.parse(m[3]!));
  }
  final int yil, ay, gun;
  String isoformat() =>
      '${_basamak(yil, 4)}-${_basamak(ay, 2)}-${_basamak(gun, 2)}';
  @override
  String toString() => isoformat();
  @override
  bool operator ==(Object other) =>
      other is Gun && yil == other.yil && ay == other.ay && gun == other.gun;
  @override
  int get hashCode => Object.hash(yil, ay, gun);
}

/// UTC anını ve metinde korunacak yerel farkı birlikte tutar.
class An implements Comparable<An> {
  An(DateTime utc, [this.fark = yerelFark]) : utc = utc.toUtc();
  final DateTime utc;
  final Duration fark;
  DateTime get yerel => utc.add(fark);
  Gun get tarih => Gun(yerel.year, yerel.month, yerel.day);
  An ekle(Duration sure) => An(utc.add(sure), fark);
  Duration farkAl(An diger) => utc.difference(diger.utc);
  An farkla(Duration yeni) => An(utc, yeni);

  factory An.parse(String s) {
    final m = RegExp(
      r'^(\d{4})-?(\d{2})-?(\d{2})(?:[T ](\d{2}):?(\d{2})(?::?(\d{2})(?:[.,](\d+))?)?)?(Z|[+-]\d{2}:?\d{2})?$',
    ).firstMatch(s);
    if (m == null) {
      throw ModelHatasi('ValueError', "Invalid isoformat string: '$s'");
    }
    final yil = int.parse(m[1]!), ay = int.parse(m[2]!), g = int.parse(m[3]!);
    Gun(yil, ay, g);
    final h = int.parse(m[4] ?? '0'),
        dk = int.parse(m[5] ?? '0'),
        sn = int.parse(m[6] ?? '0');
    if (h > 23) throw const ModelHatasi('ValueError', 'hour must be in 0..23');
    if (dk > 59) {
      throw const ModelHatasi('ValueError', 'minute must be in 0..59');
    }
    if (sn > 59) {
      throw const ModelHatasi('ValueError', 'second must be in 0..59');
    }
    final mikro = int.parse((m[7] ?? '').padRight(6, '0').substring(0, 6));
    final z = m[8];
    var ofset = yerelFark;
    if (z == 'Z') {
      ofset = Duration.zero;
    } else if (z != null) {
      final rakam = z.substring(1).replaceAll(':', '');
      final dakika =
          int.parse(rakam.substring(0, 2)) * 60 + int.parse(rakam.substring(2));
      if (dakika >= 1440) {
        throw const ModelHatasi(
          'ValueError',
          'offset must be strictly between -timedelta(hours=24) and timedelta(hours=24).',
        );
      }
      ofset = Duration(minutes: dakika * (z.startsWith('-') ? -1 : 1));
    }
    return An(
      DateTime.utc(yil, ay, g, h, dk, sn, 0, mikro).subtract(ofset),
      ofset,
    );
  }

  /// Python datetime.isoformat: kesir varsa tam altı basamak yazılır.
  String isoformat() {
    final d = yerel;
    final mikro = d.millisecond * 1000 + d.microsecond;
    final kesir = mikro == 0 ? '' : '.${_basamak(mikro, 6)}';
    final dakika = fark.inMinutes.abs();
    return '${tarih.isoformat()}T${_basamak(d.hour, 2)}:${_basamak(d.minute, 2)}:${_basamak(d.second, 2)}$kesir${fark.isNegative ? '-' : '+'}${_basamak(dakika ~/ 60, 2)}:${_basamak(dakika % 60, 2)}';
  }

  @override
  int compareTo(An other) => utc.compareTo(other.utc);
  @override
  String toString() => isoformat();
  @override
  bool operator ==(Object other) => other is An && utc == other.utc;
  @override
  int get hashCode => utc.hashCode;
}

// Kaynak: referans/cevap_anahtari/model/irp/saat.py:7 (an).
An an(Object deger) {
  if (deger is An) return deger.farkla(yerelFark);
  if (deger is DateTime) {
    if (!deger.isUtc) {
      throw const ModelHatasi('ValueError', 'Saat dilimi zorunlu');
    }
    return An(deger);
  }
  final s = deger as String;
  // SN-1: model negatif fark içeren metnin farkını yerelle değiştirir.
  if (!s.contains('+') && !s.endsWith('Z')) {
    final duz = s.replaceFirst(RegExp(r'-\d{2}:?\d{2}$'), '');
    return An.parse(duz).farkla(yerelFark);
  }
  return An.parse(s).farkla(yerelFark);
}

// Kaynak: referans/cevap_anahtari/model/irp/saat.py:15 (gun).
Gun gun(Object deger) {
  if (deger is An) return an(deger).tarih;
  if (deger is DateTime) return An(deger).tarih;
  return deger is Gun ? deger : Gun.parse(deger as String);
}

// Kaynak: referans/cevap_anahtari/model/irp/saat.py:21 (gun_ani).
An gunAni(Object tarih, [String saat = '00:00']) {
  // combine(..., YEREL) saat üzerindeki farkı da yerelle değiştirir.
  final s = saat.replaceFirst(RegExp(r'(Z|[+-]\d{2}:?\d{2})$'), '');
  return An.parse('${gun(tarih).isoformat()}T$s+03:00');
}

abstract interface class SaatKaynagi {
  An simdi();
}

/// Gerçek saat yalnız bu uygulamadan okunur.
class SistemSaati implements SaatKaynagi {
  @override
  An simdi() => An(DateTime.now().toUtc());
}

class Saat implements SaatKaynagi {
  // Kaynak: referans/cevap_anahtari/model/irp/saat.py:26 (Saat.__init__).
  Saat(Object simdi, {Object? gercek, this.demo = false})
    : isAni = an(simdi),
      gercekAni = an(gercek ?? simdi);
  An isAni, gercekAni;
  final bool demo;
  // Kaynak: referans/cevap_anahtari/model/irp/saat.py:31 (simdi).
  @override
  An simdi() => isAni;
  // Kaynak: referans/cevap_anahtari/model/irp/saat.py:34 (gercek).
  An gercek() => gercekAni;
  // Kaynak: referans/cevap_anahtari/model/irp/saat.py:37 (ilerlet).
  void ilerlet(Object hedef) {
    final t = an(hedef);
    if (t.compareTo(isAni) < 0) {
      throw const ModelHatasi(
        'ValueError',
        'A0: geri almak icin demo_sifirla gerekir',
      );
    }
    isAni = t;
    if (!demo) gercekAni = t;
  }

  // Kaynak: referans/cevap_anahtari/model/irp/saat.py:46 (saat_kaydirma).
  Duration get saatKaydirma => demo ? isAni.farkAl(gercekAni) : Duration.zero;
}

/// timedelta'nın en yakın çift mikrosaniyeye yuvarlaması.
int ciftYuvarla(num sayi) {
  final alt = sayi.floor(), kesir = sayi - sayi.floor();
  return kesir < 0.5
      ? alt
      : kesir > 0.5
      ? alt + 1
      : (alt.isEven ? alt : alt + 1);
}
