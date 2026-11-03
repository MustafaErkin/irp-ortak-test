typedef Sozluk = Map<String, dynamic>;

/// Python'un doğruluk ve kopyalama davranışı için dil uyarlaması.
bool dolu(Object? x) => switch (x) {
  null => false,
  bool b => b,
  num n => n != 0,
  String s => s.isNotEmpty,
  Iterable i => i.isNotEmpty,
  Map m => m.isNotEmpty,
  _ => true,
};

dynamic kopyala(dynamic x) => switch (x) {
  Map m => <String, dynamic>{
    for (final e in m.entries) e.key as String: kopyala(e.value),
  },
  List l => l.map(kopyala).toList(),
  Set s => s.map(kopyala).toSet(),
  _ => x,
};

/// Python get: açık null ile eksik alanı ayırır.
dynamic al(Map m, String k, dynamic varsayilan) =>
    m.containsKey(k) ? m[k] : varsayilan;

/// Python metin sırası Unicode kod noktası sırasıdır.
int metinSirasi(String a, String b) {
  final aa = a.runes.toList(), bb = b.runes.toList();
  for (var i = 0; i < aa.length && i < bb.length; i++) {
    final s = aa[i].compareTo(bb[i]);
    if (s != 0) return s;
  }
  return aa.length.compareTo(bb.length);
}
