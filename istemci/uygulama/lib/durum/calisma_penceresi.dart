/// Sunucunun hesapladığı yarı açık aralıklar. Yerel sabit mesai varsayılmaz.
class CalismaPenceresi {
  CalismaPenceresi(Map? veri, DateTime simdi)
    : biliniyor =
          veri?['gun'] ==
          simdi
              .toUtc()
              .add(const Duration(hours: 3))
              .toIso8601String()
              .substring(0, 10),
      mesaide = _icinde(veri?['mesai'], simdi),
      calisabilir = _icinde(veri?['calisma'], simdi),
      kaynakAni = DateTime.tryParse('${veri?['kaynak_ani'] ?? ''}');

  final bool biliniyor, mesaide, calisabilir;
  final DateTime? kaynakAni;

  static bool _icinde(dynamic araliklar, DateTime simdi) {
    if (araliklar is! List) return false;
    return araliklar.any((a) {
      if (a is! List || a.length != 2) return false;
      final bas = DateTime.tryParse('${a[0]}');
      final bit = DateTime.tryParse('${a[1]}');
      return bas != null &&
          bit != null &&
          !simdi.isBefore(bas) &&
          simdi.isBefore(bit);
    });
  }
}
