import 'veri.dart';

// Kaynak: referans/cevap_anahtari/model/irp/kapilar_v3.py:33 (liste_hedefleri).
List<String> listeHedefleri(Sozluk e) {
  final kod = e['eylem_kodu'], g = e['girdiler'] as Map;
  if (kod == 'IS.DEVRETTIM') return [g['kimden'], g['kime']];
  if (const {
    'IS.ATADIM',
    'IS.PLANSIZ_TANIMLADIM',
    'IS.SIRALADIM',
  }.contains(kod)) {
    return dolu(g['kisiler']) ? List<String>.from(g['kisiler']) : [g['kisi']];
  }
  return [];
}
