import 'dart:convert';

import 'package:http/http.dart' as http;

import 'supabase_bulutu.dart';
import 'gosteri_kisisi.dart';

class BulutAyariHatasi implements Exception {
  const BulutAyariHatasi();
  @override
  String toString() => 'Bulut ayarı okunamadı';
}

/// Anahtarı ve gösteri şifrelerini günlük/hata metnine dönüştürmez.
class AcilisAyari {
  const AcilisAyari({
    this.gosterim = false,
    this.adres,
    this.anon,
    this.kisiler = const [],
  });
  final bool gosterim;
  final String? adres, anon;
  final List<GosteriKisisi> kisiler;
  bool get supabase => adres != null;
}

Future<AcilisAyari> acilisAyariniOku({
  required bool web,
  required Uri sayfa,
  String kip = '',
  String bulut = '',
  String adres = '',
  String anon = '',
  String gosteriKisileri = '',
  http.Client? istemci,
}) async {
  if (kip == 'GOSTERIM' ||
      (web && sayfa.queryParameters['kip'] == 'gosterim')) {
    return const AcilisAyari(gosterim: true);
  }
  List<GosteriKisisi> telefonKisileri = const [];
  try {
    if (!web && gosteriKisileri.isNotEmpty) {
      telefonKisileri = gosteriKisileriniCoz(jsonDecode(gosteriKisileri));
    }
  } catch (_) {
    throw const BulutAyariHatasi();
  }
  AcilisAyari dogrula(dynamic b, dynamic a, dynamic k, [dynamic kisiler]) {
    if (b != 'SUPABASE' || a is! String || k is! String) {
      throw const BulutAyariHatasi();
    }
    try {
      SupabaseBulutu.ayarlariDogrula(a, k);
      return AcilisAyari(
        adres: a,
        anon: k,
        kisiler: web ? gosteriKisileriniCoz(kisiler) : telefonKisileri,
      );
    } catch (_) {
      throw const BulutAyariHatasi();
    }
  }

  if (bulut.isNotEmpty || adres.isNotEmpty || anon.isNotEmpty) {
    return dogrula(bulut, adres, anon);
  }
  if (!web) return AcilisAyari(kisiler: telefonKisileri);
  final c = istemci ?? http.Client();
  try {
    final r = await c
        .get(sayfa.resolve('ayar.json'), headers: {'Cache-Control': 'no-cache'})
        .timeout(const Duration(seconds: 5));
    if (r.statusCode == 404) return const AcilisAyari();
    if (r.statusCode != 200) throw const BulutAyariHatasi();
    final veri = jsonDecode(utf8.decode(r.bodyBytes));
    if (veri is! Map) throw const BulutAyariHatasi();
    return dogrula(
      veri['bulut'],
      veri['supabase_url'],
      veri['supabase_anon'],
      veri['gosteri_kisileri'],
    );
  } catch (_) {
    // HTTP/JSON hatasının gövdesi anahtar içerebilir; dışarı taşınmaz.
    throw const BulutAyariHatasi();
  } finally {
    if (istemci == null) c.close();
  }
}
