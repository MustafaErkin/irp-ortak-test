import 'dart:async';

import 'package:flutter/material.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';
import '../telefon/ortak.dart';
import '../telefon/qr_cizim.dart';
import 'web.dart';
import 'yonetim.dart';

Widget secim(
  String etiket,
  String? deger,
  Map<String, String> secenekler,
  ValueChanged<String?> degis,
) => DropdownButtonFormField<String>(
  key: ValueKey('$etiket-$deger'),
  initialValue: secenekler.containsKey(deger) ? deger : null,
  isExpanded: true,
  decoration: InputDecoration(labelText: etiket),
  items: [
    for (final e in secenekler.entries)
      DropdownMenuItem(
        value: e.key,
        child: Text(e.value, overflow: TextOverflow.ellipsis),
      ),
  ],
  onChanged: degis,
);
Map<String, String> secenek(UygulamaDurumu d, String veri) => {
  for (final p in d.satirlar(veri))
    '${p['kimlik'] ?? p['kod']}': '${p['ad'] ?? p['kimlik'] ?? p['kod']}',
};
Widget alan(
  String etiket,
  String deger,
  ValueChanged<String> degis, {
  bool sayisal = false,
  Key? key,
}) => TextFormField(
  key: key ?? ValueKey('$etiket-$deger'),
  initialValue: deger,
  decoration: InputDecoration(labelText: etiket),
  keyboardType: sayisal ? TextInputType.number : TextInputType.text,
  onChanged: degis,
);
Future<bool> yonetimYaz(
  BuildContext context,
  UygulamaDurumu d,
  String kod, {
  Json g = const {},
  List<Json> hs = const [],
  Json? hassas,
}) async {
  var basarili = false;
  await isle(context, () async {
    final c = await d.yonetim(kod, girdiler: g, hedefler: hs, hassasEk: hassas);
    basarili = c['sonuc'] == 'BASARILI';
  });
  if (basarili && context.mounted) {
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Kaydedildi')));
  }
  return basarili;
}

Json yeniGorev(UygulamaDurumu d, String? proje) => {
  'ad': '',
  'nereye': 'PROJE',
  'proje': proje,
  'etap': d.satirlar('ETAPLAR', hedef: proje).firstOrNull?['kimlik'],
  'kisi': d.kisi,
  'teslim_tarihi': '2026-10-30',
  'zaman_degeri': 1,
  'zorluk': 2,
  'onay_gerekli': true,
  'onaylayan': d.kisi,
  'dosya_gerekli': true,
  'on_kosul': <dynamic>[],
  'olcum': 'ZAMAN',
};

/// Yalnız form alanlarını sözleşmeye çevirir; iş hesabı yapmaz.
Json atamaGirdisi(List<Json> satirlar, List uyarilar, {bool saat = false}) {
  final rows = <Json>[];
  final secilen = satirlar
      .where((s) => (s['olcum'] == 'SAAT') == saat)
      .toList();
  final grupUyarilari = [
    for (final u in uyarilar)
      if (secilen.contains(satirlar[(u['satir'] as int) - 1]))
        {
          ...Json.from(u),
          'satir': secilen.indexOf(satirlar[(u['satir'] as int) - 1]) + 1,
        },
  ];
  for (final s in satirlar.where((s) => (s['olcum'] == 'SAAT') == saat)) {
    final r = Json.from(s)..remove('olcum');
    r['uyarilar'] = grupUyarilari
        .where((u) => u['satir'] == secilen.indexOf(s) + 1)
        .toList();
    r['on_kosul'] = [
      for (final h in s['on_kosul'] as List? ?? [])
        if (h is Map)
          {'satir': secilen.indexOf(satirlar[(h['satir'] as int) - 1]) + 1}
        else
          h,
    ];
    r.removeWhere((k, v) => v == null);
    if (r['nereye'] == 'PROJE_DISI') {
      r.remove('proje');
      r.remove('etap');
    } else {
      r.remove('kategori');
    }
    if (saat) {
      r['islem'] = r.remove('ad');
      r['tur'] = 'SURELI';
      r['tahmini_sure_dk'] = ((r.remove('zaman_degeri') as num) * 60).round();
      r['on_isler'] = r.remove('on_kosul');
      r['onay_beklet'] = true;
      r.remove('kisi');
      r.remove('zorluk');
      r.remove('dosya_gerekli');
      r.remove('onaylayan');
    }
    rows.add(r);
  }
  return {saat ? 'isler' : 'gorevler': rows, 'uyarilar': grupUyarilari};
}

class GorevAtamaForm extends StatefulWidget {
  const GorevAtamaForm({
    super.key,
    required this.durum,
    required this.proje,
    this.baslangic,
  });
  final UygulamaDurumu durum;
  final String? proje;
  final Json? baslangic;
  @override
  State<GorevAtamaForm> createState() => _GorevAtamaFormState();
}

class _GorevAtamaFormState extends State<GorevAtamaForm> {
  UygulamaDurumu get d => widget.durum;
  final rows = <Json>[];
  int secili = 0;
  bool ozet = false;
  String? hata;
  List uyarilar = [];
  Json get s => rows[secili];
  @override
  void initState() {
    super.initState();
    rows.add({...yeniGorev(d, widget.proje), ...?widget.baslangic});
  }

  void degis(String k, dynamic v) {
    s[k] = v;
  }

  Future<void> hazirla() async {
    if (rows.any(
      (s) =>
          (s['ad'] as String).trim().isEmpty ||
          (s['zaman_degeri'] as num) <= 0 ||
          DateTime.tryParse('${s['teslim_tarihi']}') == null ||
          (s['nereye'] == 'PROJE' &&
              (s['proje'] == null || s['etap'] == null)) ||
          (s['nereye'] == 'PROJE_DISI' && s['kategori'] == null),
    )) {
      setState(
        () => hata = 'Görev adı, proje/etap, geçerli teslim tarihi ve pozitif zaman değeri gerekli.',
      );
      return;
    }
    final normal = rows.where((s) => s['olcum'] != 'SAAT').toList();
    final qs = [
      ...d.ekranOkumalari.where(
        (q) => !['YUK', 'KAPASITE', 'ATAMA_UYARILARI'].contains(q.veri),
      ),
      for (final k in normal.map((s) => s['kisi']).toSet()) ...[
        Okuma('YUK', hedef: k, g: donem),
        Okuma('KAPASITE', hedef: k, g: donem),
      ],
      Okuma(
        'ATAMA_UYARILARI',
        g: {
          'satirlar': normal.map((s) => Json.from(s)..remove('olcum')).toList(),
        },
      ),
    ];
    await d.ekranOku(qs);
    uyarilar = [
      for (final u
          in d.okunmus('ATAMA_UYARILARI', g: qs.last.g)?['deger'] as List? ??
              [])
        {
          ...Json.from(u),
          'satir': rows.indexOf(normal[(u['satir'] as int) - 1]) + 1,
        },
    ];
    if (mounted) {
      setState(() {
        ozet = d.baglanti;
        hata = null;
      });
    }
  }

  Future<void> ata() async {
    for (final saat in [false, true]) {
      if (!rows.any((s) => (s['olcum'] == 'SAAT') == saat)) continue;
      final ok = await yonetimYaz(
        context,
        d,
        saat ? 'IS.TANIMLADIM' : 'GOREV.ATADIM',
        g: atamaGirdisi(rows, uyarilar, saat: saat),
      );
      if (!ok) return;
      // Başarılı grup yeniden gönderilmez; kalan grup ayrıca gözden geçirilebilir.
      final eski = List<Json>.from(rows);
      rows.removeWhere((s) => (s['olcum'] == 'SAAT') == saat);
      for (final r in rows) {
        r['on_kosul'] = [
          for (final h in r['on_kosul'] as List? ?? [])
            if (h is Map)
              {'satir': rows.indexOf(eski[(h['satir'] as int) - 1]) + 1}
            else
              h,
        ];
      }
      uyarilar = [
        for (final u in uyarilar)
          if (rows.contains(eski[(u['satir'] as int) - 1]))
            {
              ...Json.from(u),
              'satir': rows.indexOf(eski[(u['satir'] as int) - 1]) + 1,
            },
      ];
      if (mounted) setState(() => secili = 0);
    }
    if (mounted) {
      setState(() {
        rows.add(yeniGorev(d, widget.proje));
        secili = 0;
        ozet = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (ozet) {
      return Kutu(
        'Atama özeti',
        children: [
          VeriTablosu(
            ['Görev', 'Kişi / havuz', 'Zaman', 'Teslim'],
            [
              for (final r in rows)
                [
                  r['ad'],
                  adBul(
                    d,
                    r['olcum'] == 'SAAT' ? 'BIRIMLER' : 'KISILER',
                    r['olcum'] == 'SAAT' ? r['birim'] : r['kisi'],
                  ),
                  sa(r['zaman_degeri']),
                  r['teslim_tarihi'],
                ],
            ],
          ),
          const SizedBox(height: 18),
          for (final k
              in rows
                  .where((s) => s['olcum'] != 'SAAT')
                  .map((s) => s['kisi'])
                  .toSet())
            Text(
              '${adBul(d, 'KISILER', k)} · Ekim yükü ${sa(d.okunmus('YUK', hedef: k, g: donem)?['deger'])} / kapasite ${sa(d.okunmus('KAPASITE', hedef: k, g: donem)?['deger'])}',
            ),
          for (final u in uyarilar)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Satır ${u['satir']} · ${u['metin']}',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 12,
            children: [
              OutlinedButton(
                onPressed: () => setState(() => ozet = false),
                child: const Text('Geri dön'),
              ),
              YonetimDugmesi(
                durum: d,
                onPressed: ata,
                child: const Text('Ata'),
              ),
            ],
          ),
        ],
      );
    }
    final etaplar = d.satirlar('ETAPLAR', hedef: s['proje']);
    return IkiSutun(
      sol: Kutu(
        'Bu atamadaki görevler',
        children: [
          Wrap(
            spacing: 8,
            children: [
              TextButton.icon(
                onPressed: () => setState(() {
                  rows.add(yeniGorev(d, widget.proje));
                  secili = rows.length - 1;
                }),
                icon: const Icon(Icons.add),
                label: const Text('Yeni görev'),
              ),
              TextButton(
                onPressed: () => setState(() {
                  rows.add({...s, 'on_kosul': List.from(s['on_kosul'] ?? [])});
                  secili = rows.length - 1;
                }),
                child: const Text('Çoğalt'),
              ),
              TextButton(
                onPressed: rows.length == 1
                    ? null
                    : () => setState(() {
                        for (final r in rows) {
                          r['on_kosul'] = [
                            for (final h in r['on_kosul'] as List? ?? [])
                              if (h is! Map)
                                h
                              else if (h['satir'] != secili + 1)
                                {
                                  'satir': (h['satir'] as int) > secili + 1
                                      ? h['satir'] - 1
                                      : h['satir'],
                                },
                          ];
                        }
                        rows.removeAt(secili);
                        secili = 0;
                      }),
                child: const Text('Sil'),
              ),
            ],
          ),
          for (var i = 0; i < rows.length; i++)
            ListTile(
              contentPadding: EdgeInsets.zero,
              selected: i == secili,
              leading: CircleAvatar(radius: 15, child: Text('${i + 1}')),
              title: Text(
                (rows[i]['ad'] as String).isEmpty
                    ? 'Yeni görev'
                    : rows[i]['ad'],
              ),
              subtitle: Text(
                '${adBul(d, 'KISILER', rows[i]['kisi'])} · ${sa(rows[i]['zaman_degeri'])}',
              ),
              onTap: () => setState(() => secili = i),
            ),
          const SizedBox(height: 20),
          if (hata != null)
            Text(
              hata!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          FilledButton(
            onPressed: d.mesgul ? null : hazirla,
            child: const Text('Onayla · Özeti gör'),
          ),
        ],
      ),
      sag: Kutu(
        'Satır ${secili + 1}',
        form: true,
        children: [
          alan(
            'Görev adı',
            '${s['ad']}',
            (v) => degis('ad', v),
            key: ValueKey('gorev-adi-$secili'),
          ),
          secim(
            'Ölçüm',
            s['olcum'],
            const {'ZAMAN': 'Zaman değeri', 'SAAT': 'Saat ölçümlü'},
            (v) => setState(() {
              s['olcum'] = v;
              s['birim'] = 'IMALAT';
              s['on_kosul'] = <dynamic>[];
              for (final r in rows) {
                (r['on_kosul'] as List?)?.removeWhere(
                  (h) => h is Map && h['satir'] == secili + 1,
                );
              }
            }),
          ),
          secim('Nereye yazılır', s['nereye'], const {
            'PROJE': 'Proje',
            'PROJE_DISI': 'Proje dışı',
          }, (v) => setState(() => s['nereye'] = v)),
          if (s['nereye'] == 'PROJE') ...[
            secim('Proje', s['proje'], secenek(d, 'PROJELER'), (v) async {
              s['proje'] = v;
              s['etap'] = null;
              await d.ekOku(Okuma('ETAPLAR', hedef: v));
              if (mounted) {
                setState(() {
                  s['etap'] = d
                      .satirlar('ETAPLAR', hedef: v)
                      .firstOrNull?['kimlik'];
                });
              }
            }),
            secim('Etap', s['etap'], {
              for (final e in etaplar)
                '${e['kimlik']}': adBul(d, 'BIRIMLER', e['ad']),
            }, (v) => degis('etap', v)),
          ] else
            secim('Kategori', s['kategori'], {
              for (final k in d.kodlar.where((k) => k['liste'] == 'PD'))
                '${k['kod']}': '${k['ad']}',
            }, (v) => degis('kategori', v)),
          if (s['olcum'] == 'SAAT')
            secim(
              'Havuz birimi',
              s['birim'],
              secenek(d, 'BIRIMLER'),
              (v) => degis('birim', v),
            )
          else
            secim(
              'Kime',
              s['kisi'],
              secenek(d, 'KISILER'),
              (v) => degis('kisi', v),
            ),
          alan(
            'Teslim tarihi (YYYY-AA-GG)',
            s['teslim_tarihi'],
            (v) => degis('teslim_tarihi', v),
            key: ValueKey('teslim-$secili'),
          ),
          alan(
            'Zaman değeri · saat',
            '${s['zaman_degeri']}',
            (v) => degis('zaman_degeri', int.tryParse(v) ?? 0),
            sayisal: true,
            key: ValueKey('zaman-$secili'),
          ),
          if (s['olcum'] != 'SAAT')
            secim('Zorluk', '${s['zorluk']}', {
              for (var i = 1; i <= 5; i++) '$i': '$i',
            }, (v) => degis('zorluk', int.parse(v!))),
          if (secili > 0)
            secim(
              'Ön koşul',
              null,
              {
                'yok': 'Yok',
                for (var i = 0; i < secili; i++)
                  if (rows[i]['olcum'] == s['olcum'])
                    '$i': 'Satır ${i + 1} · ${rows[i]['ad']}',
              },
              (v) => s['on_kosul'] = v == 'yok'
                  ? []
                  : [
                      {'satir': int.parse(v!) + 1},
                    ],
            ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Dosya gerekli'),
            value: s['dosya_gerekli'],
            onChanged: (v) => setState(() => s['dosya_gerekli'] = v),
          ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Onay gerekli'),
            value: s['onay_gerekli'],
            onChanged: (v) => setState(() => s['onay_gerekli'] = v),
          ),
          if (s['onay_gerekli'] == true && s['olcum'] != 'SAAT')
            secim(
              'Onaylayan',
              s['onaylayan'],
              secenek(d, 'KISILER'),
              (v) => degis('onaylayan', v),
            ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Sorun kaynaklı'),
            value: s['sorun_kaynakli'] == true,
            onChanged: (v) => setState(() => s['sorun_kaynakli'] = v),
          ),
        ],
      ),
    );
  }
}

class GorevOnaylari extends StatefulWidget {
  const GorevOnaylari({super.key, required this.durum, required this.sonraki});
  final UygulamaDurumu durum;
  final void Function(Json) sonraki;
  @override
  State<GorevOnaylari> createState() => _GorevOnaylariState();
}

class _GorevOnaylariState extends State<GorevOnaylari> {
  Json? secili;
  final devam = <String>{};
  bool revizyon = false;
  String not = '', sebep = '', tarih = '2026-10-30';
  int yuzde = 100, sure = 1;
  UygulamaDurumu get d => widget.durum;
  @override
  Widget build(BuildContext context) {
    final gs = d.satirlar('ONAY_LISTESI');
    secili =
        gs.where((x) => x['kimlik'] == secili?['kimlik']).firstOrNull ??
        gs.firstOrNull;
    final g = secili;
    sebep = sebep.isEmpty ? '${g?['kisi'] ?? d.kisi}' : sebep;
    return IkiSutun(
      sol: Kutu(
        'Onay bekleyen görevler',
        children: [
          if (gs.isEmpty) const Text('Onay bekleyen teslim yok.'),
          for (final x in gs)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Checkbox(
                value: devam.contains(x['kimlik']),
                onChanged: (v) => setState(() {
                  if (v == true) {
                    devam.add(x['kimlik']);
                  } else {
                    devam.remove(x['kimlik']);
                  }
                }),
              ),
              title: Text(x['ad']),
              subtitle: Text(
                '${adBul(d, 'KISILER', x['kisi'])} · ${x['teslim_tarihi']}',
              ),
              onTap: () => setState(() => secili = x),
            ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: devam.isEmpty
                ? null
                : () {
                    final x = gs.firstWhere((g) => devam.contains(g['kimlik']));
                    widget.sonraki({
                      ...yeniGorev(d, x['proje']),
                      'ad': '${x['ad']} · sonraki iş',
                      'kisi': x['kisi'],
                      'etap': x['etap'],
                      'on_kosul': devam.toList(),
                    });
                  },
            child: const Text('Devam Et · Sonraki iş'),
          ),
        ],
      ),
      sag: g == null
          ? const Kutu(
              'Teslim',
              children: [Text('İncelemek için bir görev seç.')],
            )
          : Kutu(
              'Onay · ${g['ad']}',
              form: true,
              children: [
                for (final f in g['kanit'] as List? ?? [])
                  TextButton.icon(
                    onPressed: () async {
                      final id = f is Map ? f['dosya_kimligi'] : f;
                      await d.ekOku(Okuma('DOSYA', hedef: id));
                      if (!context.mounted) return;
                      final x = d.nesne('DOSYA', hedef: id);
                      if (x['yerel_cizim'] != null) {
                        await cizimAc(context, {
                          'dosya': x['yerel_cizim'],
                        }, 'dosya');
                      } else {
                        await guvenliDialog<void>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: Text(x['ad'] ?? 'Dosya'),
                            content: Text(
                              'Dosya: $id\n${x['boyut'] ?? ''} bayt',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx),
                                child: const Text('Kapat'),
                              ),
                            ],
                          ),
                        );
                      }
                    },
                    icon: const Icon(Icons.description_outlined),
                    label: Text(
                      f is Map ? f['ad'] ?? 'Dosyayı aç' : 'Dosyayı aç',
                    ),
                  ),
                alan(
                  'Not / ret gerekçesi',
                  not,
                  (v) => not = v,
                  key: const Key('gorev-ret-not'),
                ),
                secim(
                  'Sebep olan',
                  sebep,
                  secenek(d, 'KISILER'),
                  (v) => sebep = v!,
                ),
                alan(
                  'Sorumluluk yüzdesi',
                  '$yuzde',
                  (v) => yuzde = int.tryParse(v) ?? 100,
                  sayisal: true,
                  key: const Key('ret-yuzde'),
                ),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Revizyon görevi verilsin'),
                  value: revizyon,
                  onChanged: (v) => setState(() => revizyon = v!),
                ),
                if (revizyon) ...[
                  alan(
                    'Yeni teslim tarihi',
                    tarih,
                    (v) => tarih = v,
                    key: const Key('revizyon-tarih'),
                  ),
                  alan(
                    'Revizyon · saat',
                    '$sure',
                    (v) => sure = int.tryParse(v) ?? 1,
                    key: const Key('revizyon-saat'),
                  ),
                ],
                YonetimDugmesi(
                  durum: d,
                  onPressed: () async {
                    if (not.trim().isEmpty ||
                        yuzde < 0 ||
                        yuzde > 100 ||
                        (revizyon &&
                            (sure <= 0 || DateTime.tryParse(tarih) == null))) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Ret gerekçesini, yüzdeyi ve revizyon bilgilerini kontrol et.',
                          ),
                        ),
                      );
                      return;
                    }
                    await yonetimYaz(
                      context,
                      d,
                      'GOREV.REDDETTIM',
                      g: {
                        'not': not,
                        'revizyon_ver': revizyon,
                        'sorumlular': [
                          {'tur': 'KISI', 'kimlik': sebep, 'yuzde': yuzde},
                        ],
                        if (revizyon) ...{
                          'kime': g['kisi'],
                          'yeni_teslim_tarihi': tarih,
                          'zaman_degeri': sure,
                        },
                      },
                      hs: [hedef(g, 'GOREV')],
                    );
                  },
                  child: const Text('Reddet'),
                ),
                YonetimDugmesi(
                  durum: d,
                  onPressed: () => yonetimYaz(
                    context,
                    d,
                    'GOREV.ONAYLADIM',
                    g: {if (not.isNotEmpty) 'not': not},
                    hs: [hedef(g, 'GOREV')],
                  ),
                  child: const Text('Onayla'),
                ),
              ],
            ),
    );
  }
}

class GosteriSaati extends StatelessWidget {
  const GosteriSaati({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  Widget build(BuildContext context) {
    final d = durum;
    if (!d.yetkiliMi || !d.bulut.gosteriMi) {
      return const Text('Bu ekran yalnız gösteri ortamında yetkiliye açıktır.');
    }
    final simdi = d.cihaz!.simdiDuzeltilmis();
    Future<void> kaydir(String hedef) async {
      if (await yonetimYaz(
        context,
        d,
        'AYAR.SAAT_KAYDIRDIM',
        g: {'hedef': hedef},
      )) {
        await d.oneGeldi();
      }
    }

    return Kutu(
      'Gösteri saati',
      children: [
        Text(
          simdi.isoformat().substring(0, 16).replaceFirst('T', '  '),
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 24),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            YonetimDugmesi(
              durum: d,
              onPressed: () =>
                  kaydir(simdi.ekle(const Duration(minutes: 15)).isoformat()),
              child: const Text('+15 dk'),
            ),
            YonetimDugmesi(
              durum: d,
              onPressed: () =>
                  kaydir(simdi.ekle(const Duration(hours: 1)).isoformat()),
              child: const Text('+1 sa'),
            ),
            YonetimDugmesi(
              durum: d,
              onPressed:
                  simdi.isoformat().substring(11, 16).compareTo('18:00') >= 0
                  ? null
                  : () => kaydir('${d.bugun}T18:00:00+03:00'),
              child: const Text('Gün sonuna'),
            ),
            YonetimDugmesi(
              durum: d,
              onPressed: () => kaydir(
                '${simdi.ekle(const Duration(days: 1)).tarih.isoformat()}T08:00:00+03:00',
              ),
              child: const Text('Ertesi sabah'),
            ),
            OutlinedButton(
              onPressed: !d.yonetimAcik
                  ? null
                  : () async {
                      final ok = await guvenliDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: const Text('Gösteriyi başa döndür'),
                          content: const Text(
                            'Bu gösteride yaptığın işlemler temizlenecek.',
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(ctx, false),
                              child: const Text('Vazgeç'),
                            ),
                            FilledButton(
                              onPressed: () => Navigator.pop(ctx, true),
                              child: const Text('Sıfırla'),
                            ),
                          ],
                        ),
                      );
                      if (ok == true && context.mounted) {
                        await isle(context, () async {
                          await d.bulut.gosteriSifirla();
                          await d.oneGeldi();
                        });
                      }
                    },
              child: const Text('Sıfırla'),
            ),
          ],
        ),
        const SizedBox(height: 20),
        const Text('Gösteri verisi · İlk ay simülasyonu'),
      ],
    );
  }
}

const yonetimSekmeleri = [
  'Kişiler',
  'Projeler',
  'Etap tanımlama',
  'Maaş ve ücret',
  'Ayarlar',
  'Şüpheli olaylar',
];

class YonetimFormlari extends StatefulWidget {
  const YonetimFormlari({super.key, required this.durum, required this.proje});
  final UygulamaDurumu durum;
  final String? proje;
  @override
  State<YonetimFormlari> createState() => _YonetimFormlariState();
}

class _YonetimFormlariState extends State<YonetimFormlari> {
  UygulamaDurumu get d => widget.durum;
  String sekme = 'Kişiler', islem = 'KISI.EKLEDIM';
  Json? secili;
  final g = <String, dynamic>{};
  List<List<String>> kapasiteSatirlari = [];
  Future<void> kapasiteOku() async {
    final ps = kisiler.where((p) => p['birim'] == g['birim']).toList();
    final tarih = {'bas': g['baslangic'], 'bit': g['bitis']};
    await d.ekranOku([
      ...d.ekranOkumalari.where((q) => !['YUK', 'KAPASITE'].contains(q.veri)),
      for (final p in ps) ...[
        Okuma('YUK', hedef: p['kimlik'], g: tarih),
        Okuma('KAPASITE', hedef: p['kimlik'], g: tarih),
      ],
    ]);
    if (!mounted) return;
    setState(
      () => kapasiteSatirlari = [
        for (final p in ps)
          [
            p['ad'],
            sa(d.okunmus('KAPASITE', hedef: p['kimlik'], g: tarih)?['deger']),
            sa(d.okunmus('YUK', hedef: p['kimlik'], g: tarih)?['deger']),
            sa(
              (d.okunmus('KAPASITE', hedef: p['kimlik'], g: tarih)?['deger']
                          as num? ??
                      0) -
                  (d.okunmus('YUK', hedef: p['kimlik'], g: tarih)?['deger']
                          as num? ??
                      0),
            ),
          ],
      ],
    );
  }

  String? hata;
  List<Json> get kisiler => d.satirlar('KISILER');
  void baslat(String kod, [Json? x]) {
    setState(() {
      islem = kod;
      secili = x;
      g.clear();
      g.addAll(yonetimVarsayilan(kod, d, widget.proje, x));
      hata = null;
      kapasiteSatirlari = [];
    });
  }

  @override
  void initState() {
    super.initState();
    g.addAll(yonetimVarsayilan(islem, d, widget.proje, null));
  }

  @override
  Widget build(BuildContext context) {
    if (!d.yetkiliMi) return const Text('Bu ekran için yetkin yok.');
    final liste = sekme == 'Kişiler'
        ? kisiler
        : sekme == 'Projeler'
        ? d.satirlar('PROJELER')
        : sekme == 'Etap tanımlama'
        ? d.satirlar('ETAPLAR', hedef: g['proje'] ?? widget.proje)
        : <Json>[];
    final guncel = liste
        .where((x) => x['kimlik'] == secili?['kimlik'])
        .firstOrNull;
    if (secili != null &&
        guncel != null &&
        secili!['surum'] != guncel['surum']) {
      // BAYAT sonrası yenilenen kayıt formu ve hedef sürümü birlikte günceller.
      secili = guncel;
      g
        ..clear()
        ..addAll(yonetimVarsayilan(islem, d, widget.proje, guncel));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final s in yonetimSekmeleri)
              ChoiceChip(
                label: Text(s),
                selected: sekme == s,
                onSelected: (_) {
                  sekme = s;
                  baslat(switch (s) {
                    'Kişiler' => 'KISI.EKLEDIM',
                    'Projeler' => 'PROJE.ACTIM',
                    'Etap tanımlama' => 'ETAP.TANIMLADIM',
                    'Maaş ve ücret' => 'MAAS.GUNCELLEDIM',
                    _ => 'AYAR.ONAY_ORANI',
                  });
                },
              ),
          ],
        ),
        const SizedBox(height: 24),
        if (sekme == 'Şüpheli olaylar')
          Kutu(
            'İşleme hataları',
            children: [
              for (final alan in ['supheliler', 'isleme_hatalari'])
                VeriTablosu(
                  ['Olay', 'Açıklama', 'Tarih'],
                  [
                    for (final x
                        in (d.nesne('SUPHELILER')[alan] is Map
                            ? (d.nesne('SUPHELILER')[alan] as Map).values
                            : d.nesne('SUPHELILER')[alan] as List? ?? []))
                      [
                        metin(x['olay'] ?? x['olay_kimligi']),
                        metin(x['neden'] ?? x['hata']),
                        metin(x['an']),
                      ],
                  ],
                ),
            ],
          )
        else
          IkiSutun(
            sol: Kutu(
              sekme,
              children: [
                if (liste.isNotEmpty)
                  for (final x in liste)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        sekme == 'Etap tanımlama'
                            ? adBul(d, 'BIRIMLER', x['ad'])
                            : x['ad'] ?? x['kimlik'],
                      ),
                      subtitle: Text(
                        sekme == 'Kişiler'
                            ? '${adBul(d, 'BIRIMLER', x['birim'])} · ${x['yaka'] == 'MAVI' ? 'Mavi yaka' : 'Beyaz yaka'}'
                            : x['kimlik'],
                      ),
                      trailing: const Icon(Icons.edit_outlined, size: 18),
                      onTap: () => baslat(
                        sekme == 'Kişiler'
                            ? 'KISI.DEGISTIRDIM'
                            : sekme == 'Projeler'
                            ? 'PROJE.DEGISTIRDIM'
                            : 'ETAP.DEGISTIRDIM',
                        x,
                      ),
                    ),
                if (sekme == 'Kişiler')
                  TextButton(
                    onPressed: () => baslat('KISI.EKLEDIM'),
                    child: const Text('+ Yeni çalışan'),
                  ),
                if (sekme == 'Projeler')
                  TextButton(
                    onPressed: () => baslat('PROJE.ACTIM'),
                    child: const Text('+ Proje aç'),
                  ),
                if (sekme == 'Etap tanımlama') ...[
                  TextButton(
                    onPressed: () => baslat('ETAP.TANIMLADIM'),
                    child: const Text('+ Yeni etap'),
                  ),
                  const Text(
                    'Etap: birim, başlangıç/bitiş, hedef saat ve sorumlu ile tanımlanır.',
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton(
                    onPressed: d.mesgul ? null : kapasiteOku,
                    child: const Text('Birim kapasitesini gör'),
                  ),
                  if (kapasiteSatirlari.isNotEmpty)
                    VeriTablosu([
                      'Kişi',
                      'Kapasite',
                      'Planlı',
                      'Boş',
                    ], kapasiteSatirlari),
                ],
                if (sekme == 'Maaş ve ücret')
                  const Text('Kişiyi ve ücretin geçerli olacağı tarihi seç.'),
                if (sekme == 'Ayarlar') ...[
                  for (final e in {
                    'AYAR.ONAY_ORANI': 'Onay oranı',
                    'GUN_ONAYI.AYARLADIM': 'Gün onayı',
                    'AYAR.YONLENDIRDIM': '@ kime düşer',
                  }.entries)
                    ListTile(title: Text(e.value), onTap: () => baslat(e.key)),
                ],
                if (secili != null && sekme == 'Kişiler')
                  TextButton(
                    onPressed: () => baslat('KISI.AYRILDI', secili),
                    child: const Text('Ayrılış kaydı'),
                  ),
                if (secili != null && sekme == 'Projeler')
                  TextButton(
                    onPressed: () => baslat('PROJE.KAPATTIM', secili),
                    child: const Text('Projeyi kapat'),
                  ),
              ],
            ),
            sag: Kutu(
              yonetimBasliklari[islem] ?? 'Düzenle',
              form: true,
              children: [
                for (final e in g.entries) formAlani(e.key, e.value),
                if (hata != null) Text(hata!),
                YonetimDugmesi(
                  durum: d,
                  onPressed: () async {
                    try {
                      final girdiler = yonetimGirdisi(islem, g);
                      Json? hassas;
                      if (islem == 'MAAS.GUNCELLEDIM') {
                        hassas = {
                          'nesne_kimlik': g['kisi'],
                          'tur': g['hassas_tur'],
                          'tutar': num.parse('${g['tutar']}'),
                          'gecerli_baslangic': g['gecerli_baslangic'],
                        };
                      }
                      if (await yonetimYaz(
                        context,
                        d,
                        islem,
                        g: girdiler,
                        hs:
                            secili != null &&
                                [
                                  'PROJE.DEGISTIRDIM',
                                  'PROJE.KAPATTIM',
                                  'ETAP.DEGISTIRDIM',
                                ].contains(islem)
                            ? [
                                hedef(
                                  secili!,
                                  islem.startsWith('PROJE') ? 'PROJE' : 'ETAP',
                                ),
                              ]
                            : [],
                        hassas: hassas,
                      )) {
                        if (mounted) setState(() => hata = null);
                      }
                    } catch (_) {
                      setState(
                        () => hata = 'Alanları kontrol et; sayı ve tarihleri geçerli biçimde gir.',
                      );
                    }
                  },
                  child: Text(islem == 'PROJE.KAPATTIM' ? 'Kapat' : 'Kaydet'),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget formAlani(String k, dynamic v) {
    final ad = alanAdlari[k] ?? k;
    if (islem == 'ETAP.DEGISTIRDIM' && ['proje', 'birim'].contains(k)) {
      return InputDecorator(
        decoration: InputDecoration(labelText: ad),
        child: Text(adBul(d, k == 'proje' ? 'PROJELER' : 'BIRIMLER', v)),
      );
    }
    if (islem == 'KISI.DEGISTIRDIM' && k == 'gecerli_baslangic') {
      return const Text('Değişiklik kaydedildiği anda geçerli olur.');
    }
    if (k == 'hassas_tur') {
      return secim(
        'Ücret türü',
        v,
        const {'MAAS_AYLIK': 'Aylık maaş', 'SAAT_UCRETI': 'Saat ücreti'},
        (x) => setState(() {
          g[k] = x;
          g['kisi'] = d.kisi;
        }),
      );
    }
    if (k == 'kisi' &&
        islem == 'MAAS.GUNCELLEDIM' &&
        g['hassas_tur'] == 'SAAT_UCRETI') {
      return secim('Çalışan / Tezgâh', v, {
        ...secenek(d, 'KISILER'),
        ...secenek(d, 'TEZGAHLAR'),
      }, (x) => g[k] = x);
    }
    if (k == 'proje') {
      return secim(ad, v, secenek(d, 'PROJELER'), (x) async {
        g[k] = x;
        d.acikProje = x;
        await d.ekOku(Okuma('ETAPLAR', hedef: x));
        if (mounted) setState(() {});
      });
    }
    if (v is bool) {
      return CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        title: Text(ad),
        value: v,
        onChanged: (x) => setState(() => g[k] = x),
      );
    }
    final veri = k == 'kisi' || k == 'sorumlu'
        ? 'KISILER'
        : k == 'birim'
        ? 'BIRIMLER'
        : k == 'proje'
        ? 'PROJELER'
        : null;
    if (veri != null) return secim(ad, v, secenek(d, veri), (x) => g[k] = x);
    if (k == 'yaka') {
      return secim(ad, v, const {
        'MAVI': 'Mavi yaka',
        'BEYAZ': 'Beyaz yaka',
      }, (x) => g[k] = x);
    }
    return alan(
      ad,
      '$v',
      (x) => g[k] = x,
      key: ValueKey('$islem-${secili?['kimlik']}-${secili?['surum']}-$k'),
    );
  }
}

const yonetimBasliklari = {
  'KISI.EKLEDIM': 'Yeni çalışan',
  'KISI.DEGISTIRDIM': 'Kişiyi düzenle',
  'KISI.AYRILDI': 'Ayrılış kaydı',
  'PROJE.ACTIM': 'Proje aç',
  'PROJE.DEGISTIRDIM': 'Projeyi düzenle',
  'PROJE.KAPATTIM': 'Projeyi kapat',
  'ETAP.TANIMLADIM': 'Etap tanımla',
  'ETAP.DEGISTIRDIM': 'Etap düzenle',
  'MAAS.GUNCELLEDIM': 'Maaş güncelle',
  'AYAR.ONAY_ORANI': 'Onay oranı',
  'GUN_ONAYI.AYARLADIM': 'Gün onayı',
  'AYAR.YONLENDIRDIM': 'Bildirim yönlendirme',
};
const alanAdlari = {
  'ad': 'Ad',
  'kod': 'Kod',
  'birim': 'Birim',
  'yaka': 'Yaka',
  'roller': 'Roller (virgülle)',
  'giris_tarihi': 'Giriş tarihi',
  'kisi': 'Kişi',
  'gecerli_baslangic': 'Geçerlilik tarihi',
  'ayrilis_tarihi': 'Ayrılış tarihi',
  'teslim_tarihi': 'Teslim tarihi',
  'proje': 'Proje',
  'baslangic': 'Başlangıç tarihi',
  'bitis': 'Bitiş tarihi',
  'hedef_saat': 'Hedef saat',
  'sorumlu': 'Sorumlu',
  'tutar': 'Tutar · TL',
  'deger': 'Onay oranı (0–1)',
  'gerekli': 'Gün onayı gerekli',
  'kisiler': 'Kişi kodları (virgülle)',
};
Json yonetimVarsayilan(String kod, UygulamaDurumu d, String? proje, Json? x) =>
    switch (kod) {
      'KISI.EKLEDIM' => {
        'kod': '',
        'ad': '',
        'birim': d.birim,
        'yaka': 'BEYAZ',
        'roller': 'CALISAN',
        'giris_tarihi': d.bugun,
      },
      'KISI.DEGISTIRDIM' => {
        'kisi': x!['kimlik'],
        'ad': x['ad'],
        'birim': x['birim'],
        'yaka': x['yaka'],
        'roller': (x['roller'] as List).join(','),
        'gecerli_baslangic': d.bugun,
      },
      'KISI.AYRILDI' => {'kisi': x!['kimlik'], 'ayrilis_tarihi': d.bugun},
      'PROJE.ACTIM' => {'kod': '', 'ad': '', 'teslim_tarihi': '2026-12-31'},
      'PROJE.DEGISTIRDIM' => {
        'ad': x!['ad'],
        'teslim_tarihi': x['teslim_tarihi'] ?? '2026-12-31',
      },
      'PROJE.KAPATTIM' => {},
      'ETAP.TANIMLADIM' || 'ETAP.DEGISTIRDIM' => {
        'proje': proje,
        'ad': x?['ad'] ?? '',
        'birim': x?['birim'] ?? d.birim,
        'baslangic': x?['baslangic'] ?? '2026-10-01',
        'bitis': x?['bitis'] ?? '2026-10-31',
        'hedef_saat': x?['hedef_saat'] ?? 40,
        'sorumlu': x?['sorumlu'] ?? d.kisi,
      },
      'MAAS.GUNCELLEDIM' => {
        'hassas_tur': 'MAAS_AYLIK',
        'kisi': d.kisi,
        'gecerli_baslangic': d.bugun,
        'tutar': '',
      },
      'AYAR.ONAY_ORANI' => {
        'deger': 0.1,
        'gecerli_baslangic': DateTime.parse(d.bugun)
            .add(const Duration(days: 1))
            .toIso8601String()
            .substring(0, 10),
      },
      'GUN_ONAYI.AYARLADIM' => {
        'birim': d.birim,
        'gerekli': true,
        'gecerli_baslangic': d.bugun,
      },
      'AYAR.YONLENDIRDIM' => {'birim': d.birim, 'kisiler': d.kisi},
      _ => {},
    };
Json yonetimGirdisi(String kod, Json form) {
  final g = Json.from(form)
    ..remove('tutar')
    ..remove('hassas_tur');
  for (final k in ['ad', 'kod']) {
    if (g.containsKey(k) && '${g[k]}'.trim().isEmpty) {
      throw const FormatException('Boş alan');
    }
  }
  for (final k in [
    'giris_tarihi',
    'gecerli_baslangic',
    'ayrilis_tarihi',
    'teslim_tarihi',
    'baslangic',
    'bitis',
  ]) {
    if (g[k] != null && DateTime.tryParse('${g[k]}') == null) {
      throw const FormatException('Tarih');
    }
  }
  for (final k in ['roller', 'kisiler']) {
    if (g[k] is String) {
      g[k] = (g[k] as String)
          .split(',')
          .map((x) => x.trim())
          .where((x) => x.isNotEmpty)
          .toList();
    }
  }
  if (g['hedef_saat'] != null) {
    g['hedef_saat'] = int.parse('${g['hedef_saat']}');
    if (g['hedef_saat'] < 0) throw const FormatException('Hedef saat');
  }
  if (g['deger'] != null) g['deger'] = num.parse('${g['deger']}');
  if (g['deger'] != null && (g['deger'] < 0 || g['deger'] > 1)) {
    throw const FormatException('Onay oranı');
  }
  if (g['baslangic'] != null &&
      '${g['baslangic']}'.compareTo('${g['bitis']}') > 0) {
    throw const FormatException('Tarih aralığı');
  }
  if (kod == 'MAAS.GUNCELLEDIM' && num.parse('${form['tutar']}') <= 0) {
    throw const FormatException('Ücret');
  }
  if (kod == 'KISI.DEGISTIRDIM') {
    final k = g.remove('kisi'), t = g.remove('gecerli_baslangic');
    return {'kisi': k, 'gecerli_baslangic': t, 'degisenler': g};
  }
  if (kod == 'PROJE.DEGISTIRDIM' || kod == 'ETAP.DEGISTIRDIM') {
    if (kod == 'ETAP.DEGISTIRDIM') {
      g.remove('proje');
      g.remove('birim');
    }
    return {'degisenler': g};
  }
  return g;
}
