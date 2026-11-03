import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';
import 'web.dart';
import 'yonetim_formlari.dart';

const yonetimSayfalari = [
  'Projeler',
  'Personel dağılımı',
  'Raporlar',
  'Maaş dağılımı',
  'Adil Performans',
  'Parçalar ve belgeler',
  'Görev Atama',
  'Gösteri saati',
  'Yönetim',
];
const donem = {'bas': '2026-10-01', 'bit': '2026-10-31'};
const ay = {'ay': '2026-10-01'};
String sayi(dynamic v) => v == null || v == 'VERI_EKSIK'
    ? 'Veri eksik'
    : v is num
    ? NumberFormat('#,##0.##', 'tr').format(v)
    : '$v';
String para(dynamic v) {
  final n = v is num ? v : num.tryParse('$v');
  return n == null ? 'Veri eksik' : '${sayi(n)} TL';
}

String sa(dynamic v) => v == null ? '' : '${sayi(v)} sa';
String adBul(UygulamaDurumu d, String veri, dynamic k) =>
    d
        .satirlar(veri)
        .where((p) => p['kimlik'] == k || p['kod'] == k)
        .firstOrNull?['ad'] ??
    '$k';
String kalemAdi(UygulamaDurumu d, String k) => switch (k) {
  'TEKLIF_ARGE' => 'Teklif ve Ar-Ge',
  'IZIN' => 'İzin',
  'KAYDEDILMEYEN' => 'Görev olarak kaydedilmeyen',
  'PROJE_DISI' => 'Proje dışı',
  'ERISIM_DISI_PROJE' => 'Erişim dışı proje',
  _ => adBul(d, 'PROJELER', k),
};

class VeriTablosu extends StatelessWidget {
  const VeriTablosu(this.basliklar, this.satirlar, {super.key});
  final List<String> basliklar;
  final List<List<String>> satirlar;
  @override
  Widget build(BuildContext context) => satirlar.isEmpty
      ? const Padding(
          padding: EdgeInsets.all(12),
          child: Text('Bu dönemde kayıt yok.'),
        )
      : LayoutBuilder(
          builder: (context, c) => SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(minWidth: c.maxWidth),
              child: DataTable(
                columnSpacing: 12,
                horizontalMargin: 0,
                headingRowHeight: 42,
                dataRowMinHeight: 46,
                dataRowMaxHeight: 58,
                columns: [
                  for (final x in basliklar)
                    DataColumn(
                      label: Text(
                        x,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                ],
                rows: [
                  for (final r in satirlar)
                    DataRow(
                      cells: [
                        for (final s in r)
                          DataCell(
                            ConstrainedBox(
                              constraints: BoxConstraints(
                                maxWidth:
                                    ((c.maxWidth -
                                                12 * (basliklar.length - 1)) /
                                            basliklar.length)
                                        .clamp(90, 260),
                              ),
                              child: Text(
                                s,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        );
}

class YonetimSayfa extends StatefulWidget {
  const YonetimSayfa({
    super.key,
    required this.durum,
    required this.sayfa,
    required this.sonraki,
    this.baslangic,
  });
  final UygulamaDurumu durum;
  final String sayfa;
  final Json? baslangic;
  final void Function(Json) sonraki;
  @override
  State<YonetimSayfa> createState() => _YonetimSayfaState();
}

class _YonetimSayfaState extends State<YonetimSayfa> {
  UygulamaDurumu get d => widget.durum;
  String? proje, kisi, nesne;
  String? raporAyi;
  List<String> get raporAylari =>
      List<String>.from(d.gosterim?['aylar'][proje] ?? []);
  Json get donem {
    if (!d.gosterimMi) return const {'bas': '2026-10-01', 'bit': '2026-10-31'};
    if (widget.sayfa != 'Raporlar') {
      return Json.from(d.gosterim!['personel_donemi']);
    }
    final bas = DateTime.parse('${raporAyi!}-01');
    final son = DateTime(bas.year, bas.month + 1, 0);
    return {
      'bas': '${raporAyi!}-01',
      'bit': DateFormat('yyyy-MM-dd').format(son),
    };
  }

  Json get ay => {'ay': d.gosterimMi ? '${raporAyi!}-01' : '2026-10-01'};
  Json get projeDonemi =>
      d.gosterimMi ? Json.from(d.gosterim!['proje_donemleri'][proje]) : donem;
  bool bekle = true;
  dynamic veri(String v, {String? h, Json? g}) =>
      d.okunmus(v, hedef: h, g: g)?['deger'];
  List<Json> liste(String v, {String? h, Json? g}) =>
      d.satirlar(v, hedef: h, g: g);
  Json harita(String v, {String? h, Json? g}) => d.nesne(v, hedef: h, g: g);
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(yukle());
    });
  }

  Future<void> yukle() async {
    setState(() => bekle = true);
    await d.ekranOku([
      const Okuma('PROJELER'),
      const Okuma('KISILER'),
      const Okuma('BIRIMLER'),
    ]);
    proje ??=
        liste('PROJELER')
            .where((p) => p['kimlik'] == '2509084')
            .firstOrNull?['kimlik'] ??
        liste('PROJELER').firstOrNull?['kimlik'];
    kisi ??= d.yetkiliMi ? 'K041' : d.kisi;
    if (d.gosterimMi && !raporAylari.contains(raporAyi)) {
      raporAyi = raporAylari.last;
    }
    final qs = <Okuma>[
      const Okuma('PROJELER'),
      const Okuma('KISILER'),
      const Okuma('BIRIMLER'),
    ];
    switch (widget.sayfa) {
      case 'Projeler':
        if (proje != null) {
          qs.addAll([
            Okuma('PROJE_DURUM', hedef: proje),
            Okuma('ETAPLAR', hedef: proje),
          ]);
        }
      case 'Raporlar':
        qs.add(const Okuma('TEZGAHLAR'));
        if (proje != null) {
          qs.addAll([
            Okuma('PROJE_MALIYETI', hedef: proje, g: ay),
            Okuma(
              'PROJE_ISCILIGI',
              hedef: proje,
              g: {...donem, 'kirilim': 'BIRIM'},
            ),
            Okuma('TAHMIN_GERCEK', hedef: proje, g: projeDonemi),
            if (d.gosterimMi) ...[
              Okuma('PROJE_DURUM', hedef: proje),
              Okuma(
                'PROJE_ISCILIGI',
                hedef: proje,
                g: {...projeDonemi, 'kirilim': 'BIRIM'},
              ),
            ],
          ]);
        }
      case 'Personel dağılımı':
        qs.addAll([
          for (final v in [
            'KIM_NEREDE',
            'BIRIM_DOLULUGU',
            'SAAT_NEREYE_GITTI',
            'PERSONEL_DAGILIMI',
          ])
            Okuma(v, g: donem),
          for (final p in liste('PROJELER'))
            Okuma('PROJE_DURUM', hedef: p['kimlik']),
        ]);
      case 'Maaş dağılımı':
        if (d.yetkiliMi) {
          qs.addAll([
            Okuma('MAAS_DAGILIMI', hedef: kisi, g: ay),
            Okuma('MAAS', hedef: kisi, g: ay),
          ]);
        }
      case 'Adil Performans':
        qs.add(Okuma('PERFORMANS', hedef: kisi, g: donem));
      case 'Parçalar ve belgeler':
        if (proje != null) qs.add(Okuma('NESNELER', g: {'proje': proje}));
      case 'Onaylar':
        qs.add(const Okuma('ONAY_LISTESI'));
      case 'Görev Atama':
        if (proje != null) qs.add(Okuma('ETAPLAR', hedef: proje));
      case 'Yönetim':
        qs.addAll([
          const Okuma('TEZGAHLAR'),
          const Okuma('YONLENDIRME'),
          const Okuma('KODLAR'),
          const Okuma('SUPHELILER'),
          if (proje != null) Okuma('ETAPLAR', hedef: proje),
        ]);
    }
    d.acikProje =
        [
          'Projeler',
          'Raporlar',
          'Parçalar ve belgeler',
          'Görev Atama',
          'Yönetim',
        ].contains(widget.sayfa)
        ? proje
        : null;
    await d.ekranOku(qs);
    if (widget.sayfa == 'Projeler') {
      qs.addAll([
        for (final e in liste('ETAPLAR', h: proje))
          Okuma('ETAP_DURUM', hedef: e['kimlik']),
      ]);
      await d.ekranOku(qs);
    }
    if (widget.sayfa == 'Parçalar ve belgeler') {
      final ns = liste('NESNELER', g: {'proje': proje});
      nesne ??= ns.firstOrNull?['kimlik'];
      qs.addAll([
        for (final n in ns)
          for (final v in ['TOP_KIMDE', 'GECERLI_SURUM', 'SURUMLER'])
            Okuma(v, hedef: n['kimlik']),
      ]);
      await d.ekranOku(qs);
    }
    if (mounted) setState(() => bekle = false);
  }

  Widget filtre({bool insan = false}) => Padding(
    padding: const EdgeInsets.only(bottom: 22),
    child: Wrap(
      spacing: 20,
      runSpacing: 12,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        SizedBox(
          width: 340,
          child: DropdownButtonFormField<String>(
            key: ValueKey('${widget.sayfa}-$insan-${insan ? kisi : proje}'),
            initialValue: insan ? kisi : proje,
            isExpanded: true,
            decoration: InputDecoration(labelText: insan ? 'Kişi' : 'Proje'),
            items: [
              for (final p in liste(insan ? 'KISILER' : 'PROJELER').where(
                (p) =>
                    !insan ||
                    !d.gosterimMi ||
                    (d.gosterim!['performans_kisileri'] as List).contains(
                      p['kimlik'],
                    ),
              ))
                DropdownMenuItem(
                  value: p['kimlik'] as String,
                  child: Text(
                    '${p['ad']}${p['kaynak'] == null ? '' : ' · Belge örneği'}',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (v) {
              if (insan) {
                kisi = v;
              } else {
                proje = v;
                nesne = null;
              }
              unawaited(yukle());
            },
          ),
        ),
        if (d.gosterimMi && widget.sayfa == 'Raporlar')
          SizedBox(
            width: 190,
            child: DropdownButtonFormField<String>(
              key: ValueKey('rapor-ayi-$proje-$raporAyi'),
              initialValue: raporAyi,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Maliyet dönemi'),
              items: [
                for (final a in raporAylari)
                  DropdownMenuItem(
                    value: a,
                    child: Text(
                      DateFormat.yMMMM('tr').format(DateTime.parse('$a-01')),
                    ),
                  ),
              ],
              onChanged: (v) {
                raporAyi = v;
                unawaited(yukle());
              },
            ),
          )
        else
          Text(
            d.gosterimMi
                ? (insan ? 'Kasım 2026' : '15 Aralık 2026')
                : 'Ekim 2026',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
      ],
    ),
  );
  @override
  Widget build(BuildContext context) {
    if (bekle) {
      return const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (!d.baglanti) {
      return const Kutu(
        'Veri okunamadı',
        children: [Text('Bağlantıyı kontrol edip Yenile düğmesine bas.')],
      );
    }
    return switch (widget.sayfa) {
      'Projeler' => projeler(),
      'Raporlar' => raporlar(),
      'Personel dağılımı' => personel(),
      'Maaş dağılımı' => maas(),
      'Adil Performans' => performans(),
      'Parçalar ve belgeler' => belgeler(),
      'Görev Atama' => GorevAtamaForm(
        durum: d,
        proje: proje,
        baslangic: widget.baslangic,
      ),
      'Onaylar' => GorevOnaylari(durum: d, sonraki: widget.sonraki),
      'Gösteri saati' => GosteriSaati(durum: d),
      'Yönetim' => YonetimFormlari(durum: d, proje: proje),
      _ => const SizedBox(),
    };
  }

  Widget projeler() {
    final p = harita('PROJE_DURUM', h: proje), es = liste('ETAPLAR', h: proje);
    es.sort((a, b) {
      final tarih = (a['baslangic'] as String? ?? '9999-12-31').compareTo(
        b['baslangic'] as String? ?? '9999-12-31',
      );
      return tarih != 0 ? tarih : '${a['kimlik']}'.compareTo('${b['kimlik']}');
    });
    final etaplar = [for (final e in es) harita('ETAP_DURUM', h: e['kimlik'])];
    num topla(String k) =>
        etaplar.fold<num>(0, (a, e) => a + (e[k] is num ? e[k] as num : 0));
    num geride = etaplar.fold<num>(
      0,
      (a, e) => a + ((e['dort_kategori'] as Map?)?['geride'] as num? ?? 0),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        filtre(),
        if (d.gosterimMi)
          Padding(
            padding: const EdgeInsets.only(bottom: 20),
            child: Text(
              '${p['yuzde'] == null ? 'Sürekli' : '%${sayi(p['yuzde'])} tamamlandı'} · '
              '${p['durum'] == 'KAPALI' ? 'Kapalı proje' : 'Sürüyor'} · ${p['hikaye']}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            Olcu('Geride', sa(geride), 'teslim tarihi geçmiş işler'),
            Olcu(
              'Teslim edilen',
              sa(p['tamamlanan']),
              'tamamlanan zaman değeri',
            ),
            Olcu(
              'Tanımlı işler',
              sa(topla('planli_toplam')),
              'görevler ve atölye',
            ),
            Olcu(
              'Harcanan emek',
              sa(p['harcanan_emek']),
              'görev ve atölye toplamı',
            ),
          ],
        ),
        const SizedBox(height: 24),
        Kutu(
          'Proje nerede?',
          children: [
            for (final e in es)
              Padding(
                padding: const EdgeInsets.only(bottom: 18),
                child: Builder(
                  builder: (_) {
                    final x = harita('ETAP_DURUM', h: e['kimlik']);
                    final oran = x['yuzde'] is num
                        ? (x['yuzde'] as num).toDouble()
                        : 0.0;
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                adBul(d, 'BIRIMLER', e['ad']),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            Text(
                              d.gosterimMi && x['yuzde'] == null
                                  ? 'Sürekli'
                                  : '%${sayi(x['yuzde'])}',
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        if (!d.gosterimMi || x['yuzde'] != null)
                          LinearProgressIndicator(
                            value: (oran / 100).clamp(0, 1),
                            minHeight: 9,
                            borderRadius: BorderRadius.circular(8),
                          ),
                        const SizedBox(height: 7),
                        Text(
                          '${e['baslangic']} – ${e['bitis']} · Hedef ${sa(x['hedef'])} · Harcanan ${sa(x['harcanan_emek'])} · Bütçe tüketimi %${sayi(x['butce_tuketimi'])}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        if (d.gosterimMi && e['not'] != null)
                          Text(
                            e['not'],
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.primary,
                            ),
                          ),
                      ],
                    );
                  },
                ),
              ),
            if (p['iptal_edilenler'] is Map)
              Text(
                'İptal edilen ${p['iptal_edilenler']['sayi']} iş · ${sa(p['iptal_edilenler']['emek_saat'])}',
              ),
            if (d.yetkiliMi && p.containsKey('maliyet'))
              Text('Toplam maliyet · ${para(p['maliyet'])}'),
          ],
        ),
      ],
    );
  }

  Widget raporlar() {
    final m = harita('PROJE_MALIYETI', h: proje, g: ay),
        rows = List<Json>.from(
          (m['satirlar'] as List? ?? []).map((x) => Json.from(x)),
        );
    final tutar = d.yetkiliMi && rows.any((x) => x.containsKey('tutar'));
    final iscilik = liste(
          'PROJE_ISCILIGI',
          h: proje,
          g: {...donem, 'kirilim': 'BIRIM'},
        ),
        tg = liste('TAHMIN_GERCEK', h: proje, g: projeDonemi);
    final icinde = d.gosterimMi
        ? liste(
            'PROJE_ISCILIGI',
            h: proje,
            g: {...projeDonemi, 'kirilim': 'BIRIM'},
          )
        : iscilik;
    final iscilikTutari =
        d.yetkiliMi &&
        (d.gosterimMi || iscilik.any((x) => x.containsKey('tutar')));
    dynamic topla(String alan) {
      final sayilar = icinde.map((x) => num.tryParse('${x[alan]}')).toList();
      return sayilar.any((x) => x == null)
          ? 'VERI_EKSIK'
          : sayilar.fold<num>(0, (a, x) => a + x!);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        filtre(),
        IkiSutun(
          sol: Kutu(
            'Proje maliyeti',
            children: [
              if (d.gosterimMi) ...[
                Text(
                  'Proje toplamı · ${para(harita('PROJE_DURUM', h: proje)['maliyet'])}',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                Text('${projeDonemi['bas']} – ${projeDonemi['bit']}'),
                if (harita('PROJE_DURUM', h: proje)['butce'] != null)
                  Text(
                    'Bütçe · ${para(harita('PROJE_DURUM', h: proje)['butce'])}',
                  ),
                const SizedBox(height: 16),
                Text(
                  '${DateFormat.yMMMM('tr').format(DateTime.parse('${raporAyi!}-01'))} maliyeti',
                ),
              ],
              VeriTablosu(
                ['Kalem', 'Saat', if (tutar) 'Tutar'],
                [
                  for (final r in rows)
                    [r['ad'], sa(r['saat']), if (tutar) para(r['tutar'])],
                ],
              ),
              const SizedBox(height: 12),
              for (final r in m['ek'] as List? ?? [])
                Text('${r['ad']}${tutar ? ' · ${para(r['tutar'])}' : ''}'),
              if (m['eksik_veri'] == true)
                const Text('Veri eksik · Ücreti bilinmeyen kalemler var.'),
            ],
          ),
          sag: Kutu(
            'Proje işçiliği',
            children: [
              VeriTablosu(
                ['Birim', 'Saat', if (iscilikTutari) 'Tutar'],
                [
                  for (final r in iscilik)
                    [
                      adBul(d, 'BIRIMLER', r['birim']),
                      sa(r['saat']),
                      if (iscilikTutari) para(r['tutar']),
                    ],
                ],
              ),
              const SizedBox(height: 12),
              Text(
                d.gosterimMi ? 'Bunun içinde · Proje boyunca' : 'Bunun içinde',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              VeriTablosu(
                ['Kalem', 'Saat', if (iscilikTutari) 'Tutar'],
                [
                  for (final e in {
                    'yeniden': 'Yeniden işleme',
                    'plansiz': 'Plansız',
                    'bekleme': 'Bekleme',
                  }.entries)
                    [
                      e.value,
                      sa(topla(e.key)),
                      if (iscilikTutari) para(topla('${e.key}_tutar')),
                    ],
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        Kutu(
          d.gosterimMi
              ? 'Tahmin ile gerçek · Proje boyunca'
              : 'Tahmin ile gerçek',
          children: [
            VeriTablosu(
              [
                'Parça · İş',
                'Kişi / Tezgâh',
                'Tahmin',
                'Gerçek',
                'Fark',
                'Durum',
              ],
              [
                for (final r in tg)
                  [
                    [
                      r['parca'],
                      r['islem'],
                    ].where((x) => x != null).join(' · '),
                    '${(r['kisiler'] as List).map((k) => adBul(d, 'KISILER', k)).join(', ')}${r['tezgah'] == null ? '' : ' · ${adBul(d, 'TEZGAHLAR', r['tezgah'])}'}',
                    r['tahmin'] == null ? 'Hesaplanamaz' : dakika(r['tahmin']),
                    dakika(r['gercek']),
                    r['fark'] == null ? 'Hesaplanamaz' : '%${sayi(r['fark'])}',
                    r['suruyor'] == true ? 'Sürüyor' : durumAdi(r['durum']),
                  ],
              ],
            ),
          ],
        ),
      ],
    );
  }

  Widget personel() {
    final kn = harita('KIM_NEREDE', g: donem),
        bd = harita('BIRIM_DOLULUGU', g: donem),
        pd = liste('PERSONEL_DAGILIMI', g: donem);
    final insanlar = <String, Map<String, num>>{};
    Widget panel(Widget child) =>
        SizedBox(height: 260, child: SingleChildScrollView(child: child));
    for (final e in kn.entries) {
      final k = e.key.split(':').first;
      final pay = insanlar.putIfAbsent(k, () => {});
      for (final s in (e.value as Map).entries) {
        pay[s.key] = (pay[s.key] ?? 0) + (s.value as num);
      }
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Text(
            d.gosterimMi
                ? 'Kasım 2026 · Toplam 3.528 sa · Kişi payları birim toplamından eşit dağıtılmıştır'
                : 'Ekim 2026 · Kayıtlardan hesaplanan dağılım',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
        IkiSutun(
          sol: Kutu(
            'Kim nerede',
            children: [
              panel(
                VeriTablosu(
                  ['Kişi', 'Proje / çalışma', 'Saat'],
                  [
                    for (final e in insanlar.entries)
                      [
                        adBul(d, 'KISILER', e.key),
                        e.value.keys.map((k) => kalemAdi(d, k)).join(', '),
                        sa(e.value.values.fold<num>(0, (a, b) => a + b)),
                      ],
                  ],
                ),
              ),
            ],
          ),
          sag: Kutu(
            'Birim doluluğu',
            children: [
              panel(
                Column(
                  children: [
                    for (final e in bd.entries)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(adBul(d, 'BIRIMLER', e.key)),
                            const SizedBox(height: 6),
                            LinearProgressIndicator(
                              minHeight: 8,
                              borderRadius: BorderRadius.circular(6),
                              value:
                                  ((e.value['kapasite'] as num) == 0
                                          ? 0
                                          : (e.value['planli'] as num) /
                                                (e.value['kapasite'] as num))
                                      .clamp(0, 1)
                                      .toDouble(),
                            ),
                            Text(
                              '${sa(e.value['planli'])} / ${sa(e.value['kapasite'])} · Boş ${sa(e.value['bos'])}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        IkiSutun(
          sol: Kutu(
            'Proje durumu',
            children: [
              VeriTablosu(
                ['Proje', 'Harcanan emek', 'İlerleme'],
                [
                  for (final p in liste('PROJELER'))
                    [
                      p['ad'],
                      sa(
                        harita('PROJE_DURUM', h: p['kimlik'])['harcanan_emek'],
                      ),
                      d.gosterimMi &&
                              harita('PROJE_DURUM', h: p['kimlik'])['yuzde'] ==
                                  null
                          ? 'Sürekli'
                          : '%${sayi(harita('PROJE_DURUM', h: p['kimlik'])['yuzde'])}',
                    ],
                ],
              ),
            ],
          ),
          sag: Kutu(
            'Çalışma saati nereye gitti',
            children: [
              for (final r in pd)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${kalemAdi(d, r['kalem'])} · ${sa(r['saat'])} · %${sayi(r['yuzde'])}',
                      ),
                      const SizedBox(height: 5),
                      LinearProgressIndicator(
                        value: ((r['yuzde'] as num) / 100)
                            .clamp(0, 1)
                            .toDouble(),
                        minHeight: 7,
                        borderRadius: BorderRadius.circular(5),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget maas() {
    if (!d.yetkiliMi) return const Text('Bu ekran için yetkin yok.');
    final m = harita('MAAS_DAGILIMI', h: kisi, g: ay),
        pay = Map<String, dynamic>.from(m['paylar'] as Map? ?? {}),
        t = Map<String, dynamic>.from(m['tutarlar'] as Map? ?? {});
    final payda = m['payda'] as num? ?? 0;
    final tutar = m.containsKey('tutarlar');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        filtre(insan: true),
        Kutu(
          'Maaş projeye nasıl yazılır?',
          children: [
            VeriTablosu(
              ['Nereye', 'Zaman değeri', 'Pay', if (tutar) 'Tutar'],
              [
                for (final e in pay.entries)
                  [
                    kalemAdi(d, e.key),
                    sa(e.value),
                    payda == 0
                        ? 'Hesaplanamaz'
                        : '%${sayi((e.value as num) / payda * 100)}',
                    if (tutar) para(t[e.key]),
                  ],
              ],
            ),
            const SizedBox(height: 20),
            if (m.containsKey('maas'))
              Text(
                'Maaş · ${para(m['maas'])}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            const SizedBox(height: 8),
            if (m.containsKey('dagitilamayan'))
              Text('Dağıtılamayan · ${para(m['dagitilamayan'])}'),
            if (m.containsKey('onay_bekleyen'))
              Text('Onay bekleyen · ${para(m['onay_bekleyen'])}'),
            const SizedBox(height: 12),
            const Text('Süren görevlerin zaman değeri iş günlerine yayılır.'),
          ],
        ),
      ],
    );
  }

  Widget performans() {
    final x = harita('PERFORMANS', h: kisi, g: donem);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        filtre(insan: true),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            Olcu(
              'Zaman',
              '${sayi(x['zamaninda'])} / ${sayi(x['teslim'])}',
              'zamanında teslim',
            ),
            Olcu(
              'Kalite',
              '${d.gosterimMi ? '%' : ''}${sayi(x['kalite_ret'])}',
              'ret sorumluluğu',
            ),
            Olcu(
              'Çözüm',
              d.gosterimMi
                  ? sa(x['cozum_saat'])
                  : '${(x['cozum_saatleri'] as List? ?? []).length}',
              d.gosterimMi ? 'ortanca çözüm süresi' : 'tamamlanan çözüm',
            ),
            Olcu('Katkı', sa(x['katki_saat']), 'proje dışı'),
          ],
        ),
        const SizedBox(height: 24),
        Kutu(
          'Kayıtlardan gelen göstergeler',
          children: [
            if (d.gosterimMi)
              Text('Gerçek / tahmin zaman oranı · ${sayi(x['zaman_orani'])}'),
            Text(
              'Sebep olunan proje gecikmesi · ${sa(x['sebep_olunan_gecikme'])}',
            ),
            Text('Bekletme · ${sayi(x['bekletme'])}'),
            if (x['kesinlesmedi'] == true)
              const Text(
                'Onay bekleyen kayıtlar var; sonuç henüz kesinleşmedi.',
              ),
            const SizedBox(height: 12),
            const Text(
              'Kişiler sıralanmaz; her gösterge kendi kaydıyla değerlendirilir.',
            ),
          ],
        ),
      ],
    );
  }

  Widget belgeler() {
    final ns = liste('NESNELER', g: {'proje': proje});
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        filtre(),
        Kutu(
          'Parçalar ve belgeler',
          children: [
            for (final n in ns)
              ListTile(
                contentPadding: EdgeInsets.zero,
                selected: nesne == n['kimlik'],
                title: Text(n['ad'] ?? n['kod'] ?? n['kimlik']),
                subtitle: Text(
                  '${belgeDurumu(n['asama'])} · ${adBul(d, 'KISILER', n['sorumlu'])}',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => setState(() => nesne = n['kimlik']),
              ),
            if (ns.isEmpty) const Text('Bu projede parça veya belge yok.'),
          ],
        ),
        if (nesne != null) ...[
          const SizedBox(height: 22),
          Kutu(
            'Geçerli sürüm ve geçmiş',
            children: [
              Text(surumMetni(veri('GECERLI_SURUM', h: nesne))),
              const SizedBox(height: 12),
              for (final s in (veri('SURUMLER', h: nesne) as List? ?? []))
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.description_outlined),
                  title: Text(
                    '${s['surum_adi'] ?? s['surum_no'] ?? s['kimlik']}',
                  ),
                  subtitle: Text(
                    '${belgeDurumu(s['durum'])} · ${adBul(d, 'KISILER', s['ekleyen'])}${s['gerekce'] == null ? '' : ' · ${s['gerekce']}'}',
                  ),
                ),
              Text('Top kimde: ${topMetni(veri('TOP_KIMDE', h: nesne))}'),
            ],
          ),
        ],
      ],
    );
  }

  String surumMetni(dynamic x) => x == null
      ? 'Henüz geçerli resim yok.'
      : x is Map
      ? 'Geçerli: ${x['surum_adi'] ?? x['ad'] ?? x['kimlik'] ?? 'Onaylı sürüm'}'
      : 'Geçerli: $x';
  String topMetni(dynamic x) => x is Map
      ? '${belgeDurumu(x['asama'])} · ${adBul(d, 'KISILER', x['sorumlu'] ?? x['kisi'])}'
      : metin(x);
}

String belgeDurumu(dynamic x) =>
    const {
      'SIPARISTE': 'Siparişte',
      'SIPARIS_VERILMELI': 'Sipariş verilmeli',
      'CALISILIYOR': 'İşlemde',
      'FASONDA': 'Fasonda',
      'ONAYLI': 'Onaylı',
      'TASLAK': 'Taslak',
      'GERI_CEKILDI': 'Geri çekildi',
    }[x] ??
    durumAdi(x);
