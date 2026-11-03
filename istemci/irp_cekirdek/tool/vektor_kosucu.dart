import 'dart:convert';
import 'dart:io';

import 'package:irp_cekirdek/irp_cekirdek.dart';
import 'package:irp_cekirdek/src/veri.dart';

/// Referans dosyaları doğrudan okunur; Python veya ağ çalıştırılmaz.
Directory referansKoku() => Directory('../../referans/cevap_anahtari');

// Kaynak: referans/cevap_anahtari/yurut.py:43 (coz).
dynamic coz(dynamic x) {
  if (x is Map) {
    if (x.length == 1) {
      if (x.containsKey(r'$an')) return an(x[r'$an']);
      if (x.containsKey(r'$gun')) return gun(x[r'$gun']);
      if (x.containsKey(r'$kume')) return Set<String>.from(x[r'$kume']);
      if (x.containsKey(r'$ondalik')) return _Ondalik(x[r'$ondalik']);
    }
    return <String, dynamic>{
      for (final e in x.entries) e.key as String: coz(e.value),
    };
  }
  return x is List ? x.map(coz).toList() : x;
}

/// Decimal'ın iki ondalıklı, en yakın çifte yuvarlanan test temsili.
class _Ondalik {
  _Ondalik(this.metin);
  final String metin;
  String para() {
    final m = RegExp(r'^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$')
        .firstMatch(metin);
    if (m == null) throw const ModelHatasi('ValueError', 'Gecersiz ondalik');
    final kesir = m[3] ?? '';
    var rakam = BigInt.parse('${m[2]}$kesir');
    final kayma = 2 + int.parse(m[4] ?? '0') - kesir.length;
    if (kayma >= 0) {
      rakam *= BigInt.from(10).pow(kayma);
    } else {
      final bolen = BigInt.from(10).pow(-kayma);
      final kalan = rakam % bolen;
      rakam ~/= bolen;
      if (kalan * BigInt.two > bolen ||
          (kalan * BigInt.two == bolen && rakam.isOdd)) {
        rakam += BigInt.one;
      }
    }
    final s = rakam.toString().padLeft(3, '0');
    return '${m[1] == '-' ? '-' : ''}${s.substring(0, s.length - 2)}.${s.substring(s.length - 2)}';
  }
}

// Kaynak: referans/cevap_anahtari/karsilastir.py:31 (kanonik).
dynamic kanonik(dynamic x, [String alan = '']) {
  if (x is Map) {
    final keys = x.keys.cast<String>().toList()..sort(metinSirasi);
    return <String, dynamic>{
      for (final k in keys)
        if (!meta.contains(k)) k: kanonik(x[k], k),
    };
  }
  if (x is List || x is Set) {
    final sonuc = (x as Iterable).map((v) => kanonik(v)).toList();
    if (x is Set ||
        const {
          'araliklar',
          'hassas_ekler',
          'kisi_gecmisi',
          'olay_kimlikleri',
        }.contains(alan)) {
      sonuc.sort((a, b) => metinSirasi(_siraliJson(a), _siraliJson(b)));
    }
    return sonuc;
  }
  if (x is An) return x.farkla(yerelFark).isoformat();
  if (x is DateTime) return an(x).isoformat();
  if (x is Gun) return x.isoformat();
  if (x is _Ondalik) return x.para();
  if (x is double && !x.isFinite) {
    throw const ModelHatasi('ValueError', 'Sonlu olmayan sayi');
  }
  if (x is String &&
      x.length >= 19 &&
      x[4] == '-' &&
      x[10] == 'T' &&
      RegExp(r'(Z|[+-]\d{2}:?\d{2})$').hasMatch(x)) {
    try {
      return An.parse(x).farkla(yerelFark).isoformat();
    } on ModelHatasi {
      /* Tarih olmayan metin korunur. */
    }
  }
  return x;
}

// Python json.dumps'ın sıralama için kullandığı boşluklar.
String _siraliJson(dynamic x) {
  if (x is Map) {
    return '{${x.entries.map((e) => '${kodla(e.key)}: ${_siraliJson(e.value)}').join(', ')}}';
  }
  if (x is List) return '[${x.map(_siraliJson).join(', ')}]';
  return kodla(x);
}

// Kaynak: referans/cevap_anahtari/karsilastir.py:51 (farklar).
List<Sozluk> farklar(dynamic beklenen, dynamic bulunan, {int sinir = 100}) {
  final sonuc = <Sozluk>[];
  void ekle(String yol, dynamic a, dynamic b) {
    if (sonuc.length < sinir) {
      sonuc.add({'yol': yol, 'beklenen': a, 'bulunan': b});
    }
  }

  void gez(dynamic a, dynamic b, String yol) {
    if (a is Map && b is Map) {
      final keys = {...a.keys, ...b.keys}.cast<String>().toList()
        ..sort(metinSirasi);
      for (final k in keys) {
        if (!a.containsKey(k) || !b.containsKey(k)) {
          ekle('$yol/$k', al(a, k, '<ALAN YOK>'), al(b, k, '<ALAN YOK>'));
        } else {
          gez(a[k], b[k], '$yol/$k');
        }
      }
    } else if (a is List && b is List) {
      if (a.length != b.length) ekle('$yol/uzunluk', a.length, b.length);
      for (var i = 0; i < a.length && i < b.length; i++) {
        gez(a[i], b[i], '$yol/$i');
      }
    } else if (a is num && b is num) {
      if ((a - b).abs() > 1e-6) ekle(yol, a, b);
    } else if (a != b) {
      ekle(yol, a, b);
    }
  }

  gez(kanonik(beklenen), kanonik(bulunan), r'$');
  return sonuc;
}

// Kaynak: referans/cevap_anahtari/yurut.py:74 (dene).
Sozluk dene(dynamic Function() f) {
  try {
    return {'deger': kanonik(f())};
  } on ModelHatasi catch (h) {
    return {'hata_turu': h.hataTuru, 'neden': h.neden};
  }
}

// Kaynak: referans/cevap_anahtari/yurut.py:58 (saat_kur).
Saat saatKur(Sozluk v) =>
    Saat(v['simdi'], gercek: v['gercek'], demo: v['demo']);

// Kaynak: referans/cevap_anahtari/yurut.py:145 (cihaz_denemeleri).
Sozluk cihazDenemesi(Sozluk kayit) {
  final c = Cihaz(kayit['kisi'], kayit['harf'], saatKur(kayit['saat']));
  c.veri = coz(kayit['veri']);
  final args = coz(kayit['args'] ?? []) as List;
  final kwargs = coz(kayit['kwargs'] ?? {}) as Sozluk;
  dynamic arg(int i, String ad, [dynamic varsayilan]) =>
      i < args.length ? args[i] : al(kwargs, ad, varsayilan);
  final cevap = dene(() {
    switch (kayit['ad']) {
      case 'olay_kimligi_uret':
        return c.olayKimligiUret();
      case 'sayaci_esitle':
        c.sayaciEsitle(List<String>.from(kayit['bulut_kimlikleri']));
        return null;
      case 'depo_kayboldu':
        c.depoKayboldu();
        return null;
      case 'yeniden_kaydol':
        return c.yenidenKaydol(
          arg(0, 'kullanilan_harfler'),
          baglanti: arg(1, 'baglanti', true),
        );
      case 'tazelik':
        return c.tazelik(arg(0, 'baglanti'), arg(1, 'son_esitleme'));
      case 'ekran_hali':
        return c.ekranHali(
          arg(0, 'son_hal'),
          isler: (arg(1, 'isler') as Map?)?.cast<String, Sozluk>(),
          liste: (arg(2, 'liste') as List?)?.cast<String>(),
        );
      default:
        throw StateError('Bilinmeyen cihaz islemi: ${kayit['ad']}');
    }
  });
  return {'cevap': cevap, 'veri': kanonik(c.veri), 'harf': c.harf};
}

// Kaynak: referans/cevap_anahtari/yurut.py:155 (saf_sorgular).
Sozluk safSorgu(Sozluk s) {
  final args = coz(s['args']) as List, kwargs = coz(s['kwargs']) as Sozluk;
  dynamic arg(int i, String ad, [dynamic varsayilan]) =>
      i < args.length ? args[i] : al(kwargs, ad, varsayilan);
  return dene(
    () => switch ('${s['modul']}.${s['ad']}') {
      'irp.kisi_gunu.kapi' => kapi(
        arg(0, 'd'),
        arg(1, 'kod'),
        arg(2, 'is_'),
        arg(3, 'bas'),
        sabit: arg(4, 'sabit', false),
      ),
      'irp.gorev.son_teslim_ani' => sonTeslimAni(arg(0, 'g')),
      _ => throw StateError('Bilinmeyen saf sorgu: $s'),
    },
  );
}

class Vektor {
  Vektor(this.dosya, this.bolum, this.sira, this.girdi, this.beklenen);
  final String dosya, bolum;
  final int sira;
  final Sozluk girdi;
  final dynamic beklenen;
  String get ad => '$dosya/$bolum/$sira/${girdi['ad']}';
  Sozluk calistir() =>
      bolum == 'cihaz_denemeleri' ? cihazDenemesi(girdi) : safSorgu(girdi);
}

List<Vektor> vektorleriOku() {
  final sonuc = <Vektor>[];
  for (final dizin in ['senaryolar', 'modul_sozlesmeleri/modul3']) {
    final dosyalar =
        Directory('${referansKoku().path}/$dizin')
            .listSync()
            .whereType<File>()
            .where((f) => f.path.endsWith('.girdi.json'))
            .toList()
          ..sort((a, b) => a.path.compareTo(b.path));
    for (final f in dosyalar) {
      final g = jsonDecode(f.readAsStringSync()) as Sozluk;
      final cihaz = g['cihaz_denemeleri'] as List? ?? [],
          saf = g['saf_sorgular'] as List? ?? [];
      if (cihaz.isEmpty && saf.isEmpty) continue;
      final bek = jsonDecode(
        File(f.path.replaceFirst('.girdi.json', '.beklenen.json'))
            .readAsStringSync(),
      ) as Sozluk;
      for (final bolum in ['cihaz_denemeleri', 'saf_sorgular']) {
        final girdiler = g[bolum] as List? ?? [];
        final beklenenler = bek[bolum] as List;
        if (girdiler.length != beklenenler.length) {
          throw StateError('${f.path}/$bolum vektör sayısı farklı');
        }
        for (var i = 0; i < girdiler.length; i++) {
          sonuc.add(
            Vektor(
              f.uri.pathSegments.last,
              bolum,
              i,
              girdiler[i],
              beklenenler[i],
            ),
          );
        }
      }
    }
  }
  return sonuc;
}

void main(List<String> args) {
  final sayilar = {'cihaz_denemeleri': 0, 'saf_sorgular': 0};
  final sonuclar = <Sozluk>[];
  for (final v in vektorleriOku()) {
    final fark = farklar(v.beklenen, v.calistir());
    if (fark.isEmpty) {
      sayilar[v.bolum] = sayilar[v.bolum]! + 1;
    } else {
      stderr.writeln('${v.ad}: ${jsonEncode(fark)}');
      exitCode = 1;
    }
    sonuclar.add({'vektor': v.ad, 'gecti': fark.isEmpty, 'farklar': fark});
  }
  final rapor = {
    'gecen': sayilar,
    'toplam': sonuclar.length,
    'sonuclar': sonuclar,
  };
  stdout.writeln(jsonEncode({'gecen': sayilar, 'toplam': sonuclar.length}));
  if (args.length == 1) {
    File(args[0]).writeAsStringSync(
      '${const JsonEncoder.withIndent('  ').convert(rapor)}\n',
    );
  }
}
