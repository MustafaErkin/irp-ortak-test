/// Şifre yalnız bellekte kalır; nesne günlük veya yerel depoya çevrilmez.
class GosteriKisisi {
  const GosteriKisisi({
    required this.etiket,
    required this.kod,
    required this.sifre,
    required this.yer,
  });
  final String etiket, kod, sifre, yer;
  bool uygun(bool telefon) =>
      yer == 'ikisi' || yer == (telefon ? 'telefon' : 'web');
}

List<GosteriKisisi> gosteriKisileriniCoz(dynamic veri) {
  if (veri == null) return const [];
  if (veri is! List) throw const FormatException('Gösteri kişileri okunamadı');
  final sonuc = <GosteriKisisi>[];
  final kodlar = <String>{};
  for (final k in veri) {
    if (k is! Map ||
        k['etiket'] is! String ||
        (k['etiket'] as String).trim().isEmpty ||
        k['kod'] is! String ||
        !RegExp(r'^K\d{3}$').hasMatch(k['kod']) ||
        k['sifre'] is! String ||
        (k['sifre'] as String).isEmpty ||
        !const ['telefon', 'web', 'ikisi'].contains(k['yer']) ||
        !kodlar.add(k['kod'])) {
      throw const FormatException('Gösteri kişileri okunamadı');
    }
    sonuc.add(
      GosteriKisisi(
        etiket: k['etiket'],
        kod: k['kod'],
        sifre: k['sifre'],
        yer: k['yer'],
      ),
    );
  }
  return List.unmodifiable(sonuc);
}
