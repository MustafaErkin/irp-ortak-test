import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import '../bulut/uygulama_bulutu.dart';
import '../durum/kalici_depo.dart';

Json birlestirFikstur(Json a, Json b) => {
  ...a,
  'kisiler': <String>{
    ...List<String>.from(a['kisiler']),
    ...List<String>.from(b['kisiler']),
  }.toList(),
  'kabul_cevaplari': <String, dynamic>{
    ...a['kabul_cevaplari'],
    ...b['kabul_cevaplari'],
  },
  'anlar': {
    for (final an in {...(a['anlar'] as Map).keys, ...(b['anlar'] as Map).keys})
      an: <String, dynamic>{...?a['anlar'][an], ...?b['anlar'][an]},
  },
};

/// Yalnız üretilmiş model okumaları ve kabul yanıtları. Hiçbir ağ çağrısı yok.
class FiksturBulutu implements UygulamaBulutu {
  FiksturBulutu(
    this.fikstur, {
    String durum = 'calisiyor',
    this.webFikstur,
    this.webKisi,
  }) {
    sec(durum);
  }
  final List<Json> akisOlaylari = List.generate(
    3,
    (i) => {
      'sira': i + 1,
      'an': '2026-10-30T10:20:0$i+03:00',
      'ulasma': '2026-10-30T10:20:0$i+03:00',
      'kim': 'K017',
      'ad': 'Örnek çalışan',
      'adina': null,
      'eylem': 'IS.BASLADIM',
      'cihaz': i == 1 ? 'MAS-K017' : 'TEL-K017',
      'neyin_ustunde': [
        {
          'tur': 'IS',
          'kimlik': 'IS-001',
          'surum': '1',
          'etiket': '20 CNC Torna · 2509084_02_02-01',
        },
      ],
      'girdiler': {'aciklama': 'Sentetik gösteri'},
      'kisi_ad': null,
      'hedef_etiket': null,
      'olay': 'K017-ornek-$i',
      'hata': i == 0,
    },
  );
  @override
  Future<Json> olayAkisi({int sonra = 0, int adet = 200}) async {
    _baglanti();
    final liste = akisOlaylari.where((x) => (x['sira'] as int) > sonra).toList()
      ..sort((a, b) => (b['sira'] as int).compareTo(a['sira'] as int));
    return {
      'olaylar': liste.take(adet.clamp(1, 500)).map(kopya).toList(),
      'son': akisOlaylari.fold<int>(
        0,
        (s, x) => x['sira'] > s ? x['sira'] as int : s,
      ),
    };
  }

  final Json fikstur;
  @override
  bool get gosteriMi => true;
  final Map<String, Json> hassasEkler = {};
  String? gosteriAni;
  final Json? webFikstur;
  String? webKisi;
  String webAni = '1040';
  List<Json> get webOkumalar =>
      (webFikstur?['anlar'][webAni][webKisi]?['okumalar'] as List? ?? [])
          .map((x) => Json.from(x as Map))
          .toList();
  String get etkinKisi => webKisi ?? fikstur['kisi'] as String;
  String get gosteriIpucu => webFikstur == null
      ? 'Gösteri hesabı: K017\nİlk şifre: 123456'
      : 'Çalışan: K017 · Lider: K009 · Beyaz yaka: K041\nYönetici: K004 · Yetkili: K001 · İlk şifre: 123456';
  late Json okumalar;
  late String durum;
  bool cevrimici = true;
  Json? sonrakiCevap;
  int zamanAsimiAdedi = 0;
  final List<Json> cagrilar = [], olaylar = [];
  final Map<String, Uint8List> dosyalar = {};
  final Map<String, String> _icerikler = {};
  final StreamController<String> _sinyal = StreamController.broadcast();
  int _harf = 0;
  void _baglanti() {
    if (!cevrimici) throw const BaglantiYok();
  }

  void sec(String ad) {
    durum = ad;
    okumalar = kopya(
      Json.from((fikstur['durumlar'][ad] ?? fikstur['anlar'][ad]) as Map),
    );
  }

  void sinyalVer(String kanal) => _sinyal.add(kanal);
  @override
  Future<Json> giris(String kod, String parola) async {
    _baglanti();
    if ((kod != fikstur['kisi'] &&
            !(webFikstur?['kisiler'] as List? ?? []).contains(kod)) ||
        parola != '123456') {
      throw ArgumentError('Kişi kodu veya ilk şifre yanlış');
    }
    cagrilar.add({'kapi': 'giris', 'kisi': kod});
    webKisi = kod == fikstur['kisi'] ? null : kod;
    return {
      'refresh_token': 'sentetik-$kod',
      'access_token': 'sentetik-erisim',
    };
  }

  @override
  Future<void> parolaDegistir(String pin) async {
    _baglanti();
    cagrilar.add({'kapi': 'parolaDegistir'});
  }

  @override
  Future<Json> oturumYenile(String refreshToken) async {
    _baglanti();
    cagrilar.add({'kapi': 'oturumYenile'});
    final kod = refreshToken.replaceFirst('sentetik-', '');
    if ((webFikstur?['kisiler'] as List? ?? []).contains(kod)) webKisi = kod;
    return {'refresh_token': refreshToken, 'access_token': 'sentetik-erisim'};
  }

  @override
  Future<String> simdi() async {
    _baglanti();
    return gosteriAni ??
        (webKisi == null
            ? okumalar['TELEFON']['hesap_ani'] as String
            : webOkumalar.first['cevap']['hesap_ani'] as String);
  }

  @override
  Future<String> cihazKaydol(String cihaz) async {
    _baglanti();
    cagrilar.add({'kapi': 'cihaz_kaydol', 'cihaz': cihaz});
    if (_harf == 26) throw StateError('Cihaz harfleri doldu');
    return 'TUVWXYZABCDEFGHIJKLMNOPQRS'[_harf++];
  }

  @override
  Future<List<String>> cihazEsitle(String cihaz, {String? harf}) async {
    _baglanti();
    cagrilar.add({'kapi': 'cihaz_esitle', 'cihaz': cihaz, 'harf': harf});
    return [
      ...List<String>.from(
        webKisi == null
            ? okumalar['BUGUNKU_KIMLIKLER']['deger']
            : webOkumalar.firstWhere(
                (x) => x['veri'] == 'BUGUNKU_KIMLIKLER',
              )['cevap']['deger'],
      ),
      ..._icerikler.keys,
    ];
  }

  @override
  Future<Json> oku(String veri, {String? hedef, Json? g}) async {
    _baglanti();
    cagrilar.add({'kapi': 'oku', 'veri': veri, 'hedef': hedef, 'g': g});
    if (webKisi != null) {
      if (veri == 'ATAMA_UYARILARI') {
        final profil = webFikstur!['anlar'][webAni][webKisi];
        final kaynak = profil['uyari_kaynaklari'] as Map? ?? {};
        final satirlar = g?['satirlar'] as List? ?? [];
        final sonuc = <Json>[];
        for (var n = 0; n < satirlar.length; n++) {
          final s = satirlar[n];
          final teslim = DateTime.parse(s['teslim_tarihi']);
          final bas = teslim.subtract(Duration(days: teslim.weekday - 1));
          final bit = bas.add(const Duration(days: 6));
          final hb = bas.toIso8601String().substring(0, 10);
          final k = kaynak[s['kisi']];
          final hafta = k?['haftalar'][hb];
          if (hafta == null) {
            throw StateError('Bu teslim haftası için gösteri verisi yok.');
          }
          final etaplar = webOkumalar
              .where((x) => x['veri'] == 'ETAPLAR')
              .expand((x) => x['cevap']['deger'] as List);
          final etap = etaplar
              .where((e) => e['kimlik'] == s['etap'])
              .firstOrNull;
          if (etap != null && teslim.isAfter(DateTime.parse(etap['bitis']))) {
            sonuc.add({
              'satir': n + 1,
              'kural': 'R24',
              'metin': 'Teslim etabın bitişini aşıyor',
            });
          }
          var yeniYuk = 0.0;
          for (final aday in satirlar.where((a) => a['kisi'] == s['kisi'])) {
            final gunler = (k['gunler'] as List)
                .map((x) => DateTime.parse(x))
                .where((x) => !x.isAfter(DateTime.parse(aday['teslim_tarihi'])))
                .toList();
            if (gunler.isNotEmpty) {
              yeniYuk +=
                  (aday['zaman_degeri'] as num) *
                  gunler
                      .where((x) => !x.isBefore(bas) && !x.isAfter(bit))
                      .length /
                  gunler.length;
            }
          }
          if ((hafta['yuk'] as num) + yeniYuk > (hafta['kapasite'] as num)) {
            sonuc.add({
              'satir': n + 1,
              'kural': 'R23',
              'metin': 'Teslim haftasının kapasitesi aşılıyor',
            });
          }
        }
        return {'deger': sonuc, 'hesap': 'GUNCEL', 'hesap_ani': await simdi()};
      }
      final satir = webOkumalar.where(
        (x) =>
            x['veri'] == veri &&
            x['hedef'] == hedef &&
            jsonEncode(x['g']) == jsonEncode(g),
      );
      if (satir.isEmpty) {
        throw StateError(
          'IRP|YETKI|Bu okuma gösteri oturumuna açık değil: $veri/$hedef',
        );
      }
      return kopya(Json.from(satir.first['cevap'] as Map));
    }
    if (hedef != null && hedef != fikstur['kisi']) {
      throw StateError('Yalnız kendi telefonun okunabilir');
    }
    return kopya(Json.from(okumalar[veri] as Map));
  }

  @override
  Future<Json> olayEkle(
    Json olay, {
    required String oturum,
    Json? hassasEk,
  }) async {
    _baglanti();
    olaylar.add(kopya(olay));
    cagrilar.add({'kapi': 'olay_ekle', 'kimlik': olay['olay_kimligi']});
    if (zamanAsimiAdedi > 0) {
      zamanAsimiAdedi--;
      throw TimeoutException('Sentetik zaman aşımı');
    }
    if (sonrakiCevap != null) {
      final c = sonrakiCevap!;
      sonrakiCevap = null;
      return c;
    }
    final id = olay['olay_kimligi'] as String, icerik = jsonEncode(olay);
    if (_icerikler.containsKey(id)) {
      return _icerikler[id] == icerik
          ? {'sonuc': 'BASARILI', 'tekrar': true}
          : {'sonuc': 'CAKISMA'};
    }
    if (oturum != etkinKisi || olay['kim'] != oturum) {
      return {'sonuc': 'REDDEDILDI', 'kod': 'YETKI'};
    }
    final kod = olay['eylem_kodu'] as String;
    // Yalnız kaynaktan alınmış cevaplar oynatılır; bilinmeyen kod kabul edilmez.
    final c = kopya(
      Json.from(
        (webKisi == null ? fikstur : webFikstur!)['kabul_cevaplari'][kod] ??
            {
              'sonuc': 'REDDEDILDI',
              'kod': 'BICIM',
              'neden': 'Bu eylem için gösteri cevabı yok',
            },
      ),
    );
    if (c['sonuc'] == 'BASARILI') {
      if (hassasEk != null) hassasEkler[id] = kopya(hassasEk);
      if (kod == 'AYAR.SAAT_KAYDIRDIM') {
        gosteriAni = olay['girdiler']['hedef'];
        final anlar = webFikstur?['anlar'] as Map? ?? {};
        final uygun = anlar.keys
            .where(
              (a) =>
                  anlar[a][webKisi] != null &&
                  (anlar[a][webKisi]['okumalar'].first['cevap']['hesap_ani']
                              as String)
                          .compareTo(gosteriAni!) <=
                      0,
            )
            .toList();
        uygun.sort(
          (a, b) =>
              (anlar[a][webKisi]['okumalar'].first['cevap']['hesap_ani']
                      as String)
                  .compareTo(
                    anlar[b][webKisi]['okumalar'].first['cevap']['hesap_ani'],
                  ),
        );
        if (uygun.isNotEmpty) webAni = uygun.last;
      }
      _icerikler[id] = icerik;
      final gecis = webKisi == null ? fikstur['gecisler']['$durum|$kod'] : null;
      if (gecis != null) {
        okumalar = kopya(Json.from(gecis['okumalar'] as Map));
        durum = gecis['sonraki'] as String? ?? durum;
      }
      if (kod == 'BILDIRIM.GORDUM') {
        for (final b
            in (webKisi == null
                    ? okumalar['BILDIRIMLER']['deger']
                    : webOkumalar.firstWhere(
                        (x) => x['veri'] == 'BILDIRIMLER',
                      )['cevap']['deger'])
                as List) {
          if ((olay['girdiler']['bildirimler'] as List).contains(
            bildirimKimligi(Json.from(b)),
          )) {
            b['gorulme_ani'] = olay['oldugu_an'];
          }
        }
      }
      sinyalVer('kisi:$oturum');
    }
    return c;
  }

  @override
  Stream<String> sinyaller(String kisi, {Set<String> ekKanallar = const {}}) {
    cagrilar.add({
      'kapi': 'sinyaller',
      'kanallar': ['kisi:$kisi', 'firma', ...ekKanallar],
    });
    return _sinyal.stream.where(
      (k) => k == 'kisi:$kisi' || k == 'firma' || ekKanallar.contains(k),
    );
  }

  @override
  Future<void> kanitYukle(String kimlik, Uint8List bytes, String tur) async {
    _baglanti();
    dosyalar[kimlik] = Uint8List.fromList(bytes);
    cagrilar.add({'kapi': 'kanit_yukle', 'yol': kimlik});
  }

  @override
  Future<void> gosteriSifirla() async {
    _baglanti();
    if (etkinKisi != 'K001') throw StateError('Bu işlem için yetkin yok');
    cagrilar.add({'kapi': 'gosteri_sifirla'});
    webAni = '1040';
    gosteriAni = null;
    hassasEkler.clear();
    sec('calisiyor');
    _icerikler.clear();
    olaylar.clear();
    dosyalar.clear();
    sinyalVer('firma');
  }

  Future<void> dispose() => _sinyal.close();
}
