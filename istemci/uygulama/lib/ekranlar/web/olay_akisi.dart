import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';
import '../../ortak/eylem_adlari.dart';
import '../telefon/ortak.dart';

/// Yalnız açık ekran yoklanır; süzgeçler sunucudaki imleci değiştirmez.
class OlayAkisi extends StatefulWidget {
  const OlayAkisi({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  State<OlayAkisi> createState() => _OlayAkisiState();
}

class _OlayAkisiState extends State<OlayAkisi> {
  final List<Json> satirlar = [];
  final Map<int, DateTime> yeniler = {};
  Timer? timer;
  int son = 0;
  bool durdu = false, mesgul = false, baglanti = true;
  String? hata;
  String kisi = '';
  bool telefon = false;
  Json? secili;
  final ayrintiAnahtari = GlobalKey();
  UygulamaDurumu get d => widget.durum;

  @override
  void initState() {
    super.initState();
    unawaited(yokla());
    timer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (!durdu) unawaited(yokla());
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Future<void> yokla() async {
    if (mesgul) return;
    mesgul = true;
    try {
      final r = await d.bulut.olayAkisi(sonra: son);
      if (!mounted) return;
      final gelen = (r['olaylar'] as List).map((x) => Json.from(x as Map));
      setState(() {
        final mevcut = satirlar.map((x) => x['sira']).toSet();
        for (final x in gelen) {
          if (mevcut.add(x['sira'])) {
            satirlar.add(x);
            if (son > 0) yeniler[x['sira'] as int] = DateTime.now();
          }
        }
        satirlar.sort((a, b) => (b['sira'] as int).compareTo(a['sira'] as int));
        if (satirlar.length > 500) satirlar.removeRange(500, satirlar.length);
        yeniler.removeWhere(
          (s, an) => DateTime.now().difference(an).inSeconds >= 4,
        );
        son = r['son'] as int;
        baglanti = true;
        hata = null;
      });
    } on BaglantiYok {
      if (mounted) setState(() => baglanti = false);
    } catch (e) {
      if (mounted) setState(() => hata = 'Olay akışı alınamadı: $e');
    } finally {
      mesgul = false;
    }
  }

  String ad(dynamic kod) =>
      d.satirlar('KISILER').where((x) => x['kimlik'] == kod).firstOrNull?['ad']
          as String? ??
      '$kod';
  String eylem(Json x) {
    final temel = eylemAdi('${x['eylem']}');
    final g = x['girdiler'] as Map? ?? {};
    final ek = switch (x['eylem']) {
      'NESNE.ASAMA_GECIRDIM' => g['yeni_asama'],
      'IS.ARIZA_BILDIRDIM' || 'TEZGAH.DURUS_BILDIRDIM' => g['neden'],
      _ => x['kisi_ad'] ?? x['hedef_etiket'],
    };
    // Uzun açıklamalar yalnız ayrıntıda kalır.
    if (ek is! String ||
        ek.trim().isEmpty ||
        ek.length > 60 ||
        ek.contains('\n') ||
        ek.contains('\r')) {
      return temel;
    }
    return '$temel → ${ek.trim()}';
  }

  String saat(dynamic an) {
    final t = DateTime.tryParse('$an')?.toLocal();
    if (t == null) return '$an';
    String iki(int n) => '$n'.padLeft(2, '0');
    final simdi = DateTime.now();
    final bugun =
        t.year == simdi.year && t.month == simdi.month && t.day == simdi.day;
    return '${bugun ? '' : '${iki(t.day)}.${iki(t.month)} '}${iki(t.hour)}:${iki(t.minute)}:${iki(t.second)}';
  }

  String hedefler(Json x) => (x['neyin_ustunde'] as List? ?? [])
      .map((h) {
        final etiket = h['etiket'];
        if (etiket is String && etiket.trim().isNotEmpty) return etiket;
        final id = '${h['kimlik']}';
        final isler = [
          'GUN_ISLERI',
          'HAVUZ',
          'EKIP',
        ].expand((v) => d.satirlar(v));
        final is_ = h['tur'] == 'IS'
            ? isler.where((i) => i['kimlik'] == id).firstOrNull
            : null;
        final adlar = [
          is_?['islem'],
          is_?['parca_adi'],
        ].whereType<String>().join(' · ');
        return '${h['tur']} · ${adlar.isEmpty ? (id.length > 18 ? '${id.substring(0, 18)}…' : id) : adlar}';
      })
      .join('\n');

  @override
  Widget build(BuildContext context) {
    final kisiler = <String, String>{
      for (final p in d.satirlar('KISILER')) '${p['kimlik']}': '${p['ad']}',
      for (final x in satirlar) '${x['kim']}': '${x['ad'] ?? ad(x['kim'])}',
    };
    final gorunen = satirlar.where(
      (x) =>
          (kisi.isEmpty || x['kim'] == kisi) &&
          (!telefon || '${x['cihaz']}'.startsWith('TEL-')),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 20,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            FilledButton.icon(
              onPressed: () {
                setState(() => durdu = !durdu);
                if (!durdu) unawaited(yokla());
              },
              icon: Icon(durdu ? Icons.play_arrow : Icons.pause),
              label: Text(durdu ? 'Sürdür' : 'Durdur'),
            ),
            DropdownButton<String>(
              value: kisi,
              items: [
                const DropdownMenuItem(value: '', child: Text('Herkes')),
                for (final p in kisiler.entries)
                  DropdownMenuItem(value: p.key, child: Text(p.value)),
              ],
              onChanged: (v) => setState(() => kisi = v!),
            ),
            SizedBox(
              width: 210,
              child: CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Yalnız telefon'),
                value: telefon,
                onChanged: (v) => setState(() => telefon = v!),
              ),
            ),
            Text('${satirlar.length} olay · ${durdu ? 'Durduruldu' : 'Canlı'}'),
          ],
        ),
        if (!baglanti) const Bant('Bağlantı yok · Liste korunuyor'),
        if (hata != null) Bant(hata!),
        const SizedBox(height: 16),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            showCheckboxColumn: false,
            dataTextStyle: Theme.of(context).textTheme.bodyLarge,
            headingRowHeight: 48,
            dataRowMinHeight: 60,
            dataRowMaxHeight: 84,
            columnSpacing: 16,
            columns: [
              for (final s in [
                'Saat',
                'Kim',
                'Ne',
                'Neyin üstünde',
                'Cihaz',
                'Hata',
              ])
                DataColumn(label: Text(s)),
            ],
            rows: [
              for (final x in gorunen)
                DataRow(
                  key: ValueKey('olay-${x['sira']}'),
                  color: WidgetStatePropertyAll(
                    yeniler.containsKey(x['sira'])
                        ? Colors.amber.withValues(alpha: .15)
                        : null,
                  ),
                  onSelectChanged: (_) {
                    setState(() => secili = x);
                    WidgetsBinding.instance.addPostFrameCallback((_) {
                      final ctx = ayrintiAnahtari.currentContext;
                      if (ctx != null) unawaited(Scrollable.ensureVisible(ctx));
                    });
                  },
                  cells: [
                    DataCell(
                      Text(saat(x['an']), key: ValueKey('olay-${x['sira']}')),
                    ),
                    DataCell(
                      Text(
                        '${x['ad'] ?? ad(x['kim'])}${x['adina'] == null ? '' : '\n${ad(x['adina'])} adına'}',
                      ),
                    ),
                    // Uzun sütunlar sabit genişlikte ve en çok iki satır: altı sütun 1280 piksele sığar.
                    DataCell(_sinirli(eylem(x), 230)),
                    DataCell(_sinirli(hedefler(x), 240)),
                    DataCell(
                      Text(
                        '${x['cihaz']}'.startsWith('TEL-')
                            ? 'Telefon'
                            : '${x['cihaz']}'.startsWith('MAS-')
                            ? 'Web'
                            : '${x['cihaz']}'.startsWith('M3-')
                            ? 'Modül 3'
                            : '${x['cihaz']}',
                      ),
                    ),
                    DataCell(
                      Text(
                        x['hata'] == true ? 'hesap hatası' : '',
                        style: const TextStyle(color: Colors.red, fontSize: 12),
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
        if (satirlar.isEmpty)
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(mesgul ? 'Olaylar yükleniyor…' : 'Henüz olay yok.'),
          ),
        if (secili != null)
          Card(
            key: ayrintiAnahtari,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      const Expanded(
                        child: Text(
                          'Olay ayrıntısı',
                          style: TextStyle(
                            fontSize: 21,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: 'Ayrıntıyı kapat',
                        onPressed: () => setState(() => secili = null),
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                  SelectableText(
                    'Olay: ${secili!['olay']}\nOluş: ${secili!['an']}\nBuluta ulaşma: ${secili!['ulasma']}\nCihaz: ${secili!['cihaz']}',
                  ),
                  const SizedBox(height: 12),
                  SelectableText(
                    const JsonEncoder.withIndent('  ').convert({
                      'neyin_ustunde': secili!['neyin_ustunde'],
                      'girdiler': secili!['girdiler'],
                      'kisi_ad': secili!['kisi_ad'],
                      'hedef_etiket': secili!['hedef_etiket'],
                    }),
                    style: const TextStyle(fontSize: 15),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

Widget _sinirli(String metin, double genislik) => SizedBox(
  width: genislik,
  child: Text(metin, maxLines: 2, overflow: TextOverflow.ellipsis),
);
