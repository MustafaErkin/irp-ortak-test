import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';

import '../bulut/uygulama_bulutu.dart';
import '../bulut/gosteri_kisisi.dart';
import 'gonderici.dart';
import 'kalici_depo.dart';
import 'kanit.dart';
import 'pin.dart';
import 'calisma_penceresi.dart';

class Okuma {
  const Okuma(this.veri, {this.hedef, this.g});
  final String veri;
  final String? hedef;
  final Json? g;
}

/// Tek durum sahibi. Bellekteki çekirdek işlemi kalıcı yazımla tamamlanır;
/// diske/IndexedDB'ye yazma bitmeden kullanıcıya başarı veya ağa olay verilmez.
class UygulamaDurumu extends ChangeNotifier {
  UygulamaDurumu({
    required this.bulut,
    required this.depo,
    required this.semalar,
    required this.saat,
    this.gosterim,
    this.telefonKipi = false,
    this.mvpMesaiSerbest = false,
    this.mvpSadeceCalisan = false,
    List<GosteriKisisi> gosteriKisileri = const [],
    DateTime Function()? guvenlikSaati,
  }) : guvenlikSaati = guvenlikSaati ?? DateTime.now,
       gosteriKisileri = List.unmodifiable(
         gosteriKisileri.where(
           (k) =>
               k.uygun(telefonKipi) &&
               (!telefonKipi || !mvpSadeceCalisan || k.yer == 'telefon'),
         ),
       ) {
    if (telefonKipi) {
      _mesaiSaati = Timer.periodic(const Duration(seconds: 30), (_) {
        if (acik) _bildir();
      });
    }
    gonderici = Gonderici(
      gonder: _gonder,
      bekleyen: () =>
          !kaliciHata &&
          (bekleyen > 0 ||
              (calisanEsitlemesi &&
                  gunluk.any(
                    (k) =>
                        k['yerel_etki'] == true && k['durum'] == 'GONDERILDI',
                  )) ||
              yuklemeler.any(
                (y) =>
                    y['kisi'] == kisi &&
                    cihaz?.veri['gunluk'][y['olay']]?['durum'] == 'GONDERILDI',
              )),
      hata: (e) {
        if (calisanEsitlemesi && (e is BaglantiYok || e is TimeoutException)) {
          baglanti = false;
        }
        mesaj = calisanEsitlemesi
            ? 'Bağlantı yenilenince işlem otomatik gönderilecek.'
            : e.toString();
        _bildir();
      },
    );
  }
  final UygulamaBulutu bulut;
  final KaliciDepo depo;
  final Json semalar;
  final SaatKaynagi saat;
  final Json? gosterim;
  final bool telefonKipi;

  /// Yalnız açıkça etkinleştirilmiş MVP derlemesindeki gösteri kişileri.
  /// Takvimi, olay saatini veya hesaplanan emeği değiştirmez.
  final bool mvpMesaiSerbest;
  final bool mvpSadeceCalisan;
  bool get calisanEsitlemesi =>
      telefonKipi &&
      mvpSadeceCalisan &&
      !gosterimMi &&
      !liderMi &&
      !bilgisayardanKullanilir &&
      bulut is TelefonEsitlemeBulutu;
  Future<void> _telefonAgSirasi = Future.value();
  Future<void>? _telefonYenilemesi;
  Future<void> _telefonAg(Future<void> Function() islem) {
    final f = _telefonAgSirasi.then((_) => islem());
    _telefonAgSirasi = f.then<void>(
      (_) {},
      onError: (Object _, StackTrace _) {},
    );
    return f;
  }

  final List<GosteriKisisi> gosteriKisileri;
  bool get gosterimMi => gosterim != null;
  final DateTime Function() guvenlikSaati;
  late final Gonderici gonderici;
  Json yerel = {};
  Cihaz? cihaz;
  bool acik = false, baglanti = true, mesgul = false, kaliciHata = false;
  String? mesaj;
  String? islemHatasi;
  bool _kapali = false;
  Future<void> _sira = Future.value();
  StreamSubscription<String>? _sinyal;
  StreamSubscription<Json>? _oturumDegisimi;
  // SDK'nın yenilediği refresh token da mevcut kalıcı kayıtla birlikte saklanır.
  void oturumIzle(Stream<Json> oturumlar) {
    _oturumDegisimi = oturumlar.listen((oturum) {
      unawaited(
        _sirala(() async {
          if (kayit == null || _kapali) return;
          kayit!['oturum'] = oturum;
          await _sakla();
        }),
      );
    });
  }

  String? _dinlenenKanallar;
  Timer? _debounce, _hesap, _mesaiSaati;
  List<Okuma> ekranOkumalari = [];
  Duration yonetimZamanAsimi = const Duration(seconds: 15);

  Json? get kayit => yerel['kayit'] as Json?;
  String get kisi => kayit?['kisi'] as String? ?? '';
  String get ad =>
      gosteriKisileri.where((k) => k.kod == kisi).firstOrNull?.etiket ??
      kayit?['ad'] as String? ??
      kisi;
  List<Json> satirlar(String veri, {String? hedef, Json? g}) =>
      (okunmus(veri, hedef: hedef, g: g)?['deger'] as List? ?? [])
          .map((x) => Json.from(x as Map))
          .toList();
  Json nesne(String veri, {String? hedef, Json? g}) =>
      Json.from(okunmus(veri, hedef: hedef, g: g)?['deger'] as Map? ?? {});
  Json get kisiBilgisi => telefonKipi && telefon['kisi'] is Map
      ? Json.from(telefon['kisi'] as Map)
      : satirlar('KISILER').where((x) => x['kimlik'] == kisi).firstOrNull ??
            Json.from(telefon['kisi'] as Map? ?? {});
  bool get liderMi =>
      (kisiBilgisi['roller'] as List? ?? []).contains('EKIP_LIDERI');
  bool get yetkiliMi =>
      (kisiBilgisi['roller'] as List? ?? []).contains('YETKILI');
  bool get yoneticiMi =>
      yetkiliMi || (kisiBilgisi['roller'] as List? ?? []).contains('YONETICI');
  String? acikProje;
  bool get webDuzeni => liderMi || kisiBilgisi['yaka'] == 'BEYAZ';
  bool get bilgisayardanKullanilir =>
      (mvpSadeceCalisan && telefonKipi && liderMi) ||
      (!liderMi && (kisiBilgisi['yaka'] == 'BEYAZ' || yoneticiMi));
  int get gonderilmemisKayitSayisi => {
    for (final k in gunluk)
      if (!const ['GONDERILDI', 'RED'].contains(k['durum']))
        k['olay']['olay_kimligi'],
    for (final y in yuklemeler) y['olay'],
  }.length;
  String get birim => kisiBilgisi['birim'] as String? ?? '';
  String get bugun => gosterimMi
      ? (gosterim!['an'] as String).substring(0, 10)
      : cihaz!.simdiDuzeltilmis().tarih.isoformat();
  Set<String> get birimKanallari => {
    if (liderMi) 'birim:$birim',
    for (final b in satirlar('BIRIMLER'))
      if (yetkiliMi || (b['yoneticileri'] as List? ?? []).contains(kisi))
        'birim:${b['kimlik']}',
  };
  bool get yonetimAcik =>
      !gosterimMi &&
      acik &&
      baglanti &&
      !mesgul &&
      !kaliciHata &&
      ekranOkumalari.isNotEmpty &&
      ekranOkumalari.every((q) => taze(q.veri, hedef: q.hedef, g: q.g));
  String get kilitAciklamasi {
    final beklenen = is_?['beklenen_isler'] as List? ?? [];
    if (beklenen.isNotEmpty) {
      final b = beklenen.first;
      return 'Önce ${b['ad'] ?? b['islem'] ?? b['kimlik']} bitmeli${b['kisi_adi'] == null ? '' : ' · ${b['kisi_adi']}'}';
    }
    for (final id in is_?['on_isler'] as List? ?? []) {
      final b = isler[id];
      if (b != null && b['durum'] != 'BITTI') {
        final p = satirlar('KISILER')
            .where((p) => p['kimlik'] == b['kisi'])
            .firstOrNull;
        return 'Önce ${b['islem'] ?? b['kimlik']} bitmeli${p == null ? '' : ' · ${p['ad']}'}';
      }
    }
    return 'Önceki işin bitmesi bekleniyor';
  }

  Map get onbellek => yerel['onbellek'] as Map? ?? {};
  List get yuklemeler => yerel['yuklemeler'] as List? ?? [];
  int get bekleyen => cihaz?.bekleyenSayisi() ?? 0;
  List<Json> get gunluk => (cihaz?.veri['gunluk'] as Map? ?? {}).values
      .map((e) => Json.from(e as Map))
      .toList();
  Json get telefon => Json.from((okunmus('TELEFON')?['deger'] as Map?) ?? {});
  Json get sonHal => Json.from(telefon['son_hal'] as Map? ?? bosHal());
  Json get _ekran => cihaz == null
      ? {
          'son_hal': sonHal,
          'liste': telefon['liste'] ?? [],
          'isler': telefon['isler'] ?? {},
        }
      : cihaz!.ekranHali(
          sonHal,
          isler: {
            for (final e in (telefon['isler'] as Map? ?? {}).entries)
              e.key as String: Json.from(e.value as Map),
          },
          liste: List<String>.from(telefon['liste'] as List? ?? []),
        );
  List<String> get liste =>
      List<String>.from((_ekran['liste'] ?? telefon['liste'] ?? []) as List);
  Map<String, Json> get isler => {
    for (final e
        in ((_ekran['isler'] ?? telefon['isler'] ?? {}) as Map).entries)
      e.key as String: Json.from(e.value as Map),
  };
  Json get hal => Json.from(_ekran['son_hal'] as Map);
  Json? get is_ =>
      isler[hal['acik_is'] ??
          hal['aralik_is'] ??
          (liste.isEmpty ? null : liste.first)];
  CalismaPenceresi get calismaPenceresi => CalismaPenceresi(
    telefon['calisma_penceresi'] as Map?,
    DateTime.parse(cihaz!.simdiDuzeltilmis().isoformat()),
  );
  bool get mesaiDenetimi =>
      telefonKipi &&
      !gosterimMi &&
      !liderMi &&
      !bilgisayardanKullanilir &&
      !(mvpMesaiSerbest && gosteriKisileri.any((k) => k.kod == kisi));
  bool get mesaiBiliniyor => !mesaiDenetimi || calismaPenceresi.biliniyor;
  bool get mesaiIcinde =>
      !mesaiDenetimi ||
      (calismaPenceresi.biliniyor && calismaPenceresi.mesaide);
  bool get calismaIcinde =>
      !mesaiDenetimi ||
      (calismaPenceresi.biliniyor && calismaPenceresi.calisabilir);
  bool get sabitMola => hal['durum'] == 'SABIT_MOLADA';
  List<Json> get kodlar => (okunmus('KODLAR')?['deger'] as List? ?? [])
      .map((e) => Json.from(e as Map))
      .toList();
  List<Json> get bildirimler =>
      (okunmus('BILDIRIMLER')?['deger'] as List? ?? [])
          .map((e) => Json.from(e as Map))
          .where(
            (e) =>
                e['gorulme_ani'] == null &&
                e['gecerli'] != false &&
                !gunluk.any(
                  (k) =>
                      k['durum'] == 'BEKLIYOR' &&
                      k['olay']['eylem_kodu'] == 'BILDIRIM.GORDUM' &&
                      (k['olay']['girdiler']['bildirimler'] as List).contains(
                        bildirimKimligi(e),
                      ),
                ),
          )
          .toList();
  bool get hesapBekliyor =>
      okunmus('TELEFON')?['hesap'] == 'BEKLIYOR' ||
      ekranOkumalari.any(
        (q) => okunmus(q.veri, hedef: q.hedef, g: q.g)?['hesap'] == 'BEKLIYOR',
      );
  int get kilitSaniye {
    final bitis = DateTime.tryParse(kayit?['kilit_bitis'] as String? ?? '');
    if (bitis == null) return 0;
    final kalan = bitis.difference(guvenlikSaati()).inMilliseconds;
    return kalan <= 0 ? 0 : (kalan / 1000).ceil();
  }

  String? _hedef(String veri, String? hedef) =>
      hedef ??
      (const {
            'KISILER',
            'KODLAR',
            'BIRIMLER',
            'PROJELER',
            'TEZGAHLAR',
            'NESNELER',
            'KIM_NEREDE',
            'BIRIM_DOLULUGU',
            'SAAT_NEREYE_GITTI',
            'PERSONEL_DAGILIMI',
            'ATAMA_UYARILARI',
            'YONLENDIRME',
            'SUPHELILER',
          }.contains(veri)
          ? null
          : kisi);
  String _anahtar(String veri, String? hedef, Json? g) =>
      jsonEncode([veri, _hedef(veri, hedef), g]);
  Json? okunmus(String veri, {String? hedef, Json? g}) =>
      (onbellek[_anahtar(veri, hedef, g)] as Map?)?['cevap'] as Json?;
  bool taze(String veri, {String? hedef, Json? g}) {
    final ani = (onbellek[_anahtar(veri, hedef, g)] as Map?)?['an'];
    return cihaz?.tazelik(baglanti, ani) ?? false;
  }

  bool kapiAcik(String kod) =>
      acik &&
      !mesgul &&
      !kaliciHata &&
      cihaz != null &&
      (kod != 'MESAI.GIRDIM' || mesaiIcinde) &&
      (!const ['IS.BASLADIM', 'IS.DEVAM_ETTIM'].contains(kod) ||
          calismaIcinde) &&
      kapi(hal, kod, is_, liste.isEmpty ? null : liste.first, sabit: sabitMola);
  void _bildir() {
    if (!_kapali) notifyListeners();
  }

  Future<T> _sirala<T>(Future<T> Function() islem) {
    final sonuc = _sira.then((_) => islem());
    _sira = sonuc.then<void>((_) {}, onError: (Object _, StackTrace _) {});
    return sonuc;
  }

  Future<void> _sakla() async {
    if (gosterimMi) return;
    if (cihaz != null) {
      (yerel['cihazlar'] as Map).putIfAbsent(
        cihaz!.kisi,
        () => <String, dynamic>{},
      );
      yerel['cihazlar'][cihaz!.kisi] = kopya(cihaz!.veri);
    }
    try {
      await depo.yaz(kopya(yerel));
    } catch (_) {
      kaliciHata = true;
      mesaj = 'Kayıt cihazda saklanamadı. Sayfayı kapatmadan depolama alanını kontrol et';
      rethrow;
    }
  }

  void _cihazAc() {
    if (kayit == null) return;
    cihaz = Cihaz(
      kisi,
      kayit!['harf'] as String,
      saat,
      telefon: telefonKipi,
      teslimiKoru:
          telefonKipi && mvpSadeceCalisan && bulut is TelefonEsitlemeBulutu,
      yerelDepo: BellekDeposu(
        (yerel['cihazlar'][kisi] as Map?)?.cast<String, dynamic>(),
      ),
    );
  }

  Future<void> yukle() async {
    if (gosterimMi) {
      yerel = {
        'kayit': {'kisi': 'K001', 'ad': 'Kemal Aksoy'},
        'onbellek': {},
      };
      acik = true;
      await yenile();
      return;
    }
    yerel = await depo.oku();
    yerel.putIfAbsent('cihazlar', () => <String, dynamic>{});
    yerel.putIfAbsent('onbellek', () => <String, dynamic>{});
    yerel.putIfAbsent('yuklemeler', () => <dynamic>[]);
    _cihazAc();
    if (gosteriKisileri.isNotEmpty) {
      if (kayit != null &&
          gosteriKisileri.any((k) => k.kod == kisi) &&
          kayit!['gosteri_kisisi'] == true) {
        acik = true;
        if (calisanEsitlemesi && telefon.isNotEmpty) {
          // Kalıcı hal hazırken ilk çizim ağ/oturum yenilemesini beklemez.
          unawaited(oneGeldi());
        } else {
          await oneGeldi();
        }
      } else {
        await gosteriKisisiniDegistir(gosteriKisileri.first);
      }
    } else if (kayit?['gosteri_kisisi'] == true) {
      // Liste kaldırıldıysa PIN'siz gösteri oturumu normal girişe taşınmaz.
      yerel.remove('kayit');
      cihaz = null;
      await _sakla();
    }
    _bildir();
  }

  Future<void> _kaydiOlustur(String kod, Json oturum, {Json? pin}) async {
    // Her kurulum kendi kayıt anahtarıyla ayrı bir cihaz harfi alır.
    final rastgele = Random.secure();
    final cihazKimligi = yerel.putIfAbsent(
      'kurulum_kimligi',
      () =>
          'IRP-${List.generate(16, (_) => rastgele.nextInt(256).toRadixString(16).padLeft(2, '0')).join()}',
    ) as String;
    await _sakla();
    final harf = await bulut.cihazKaydol(cihazKimligi);
    yerel['kayit'] = {
      'kisi': kod,
      'ad': kod,
      'harf': harf,
      'cihaz_kimligi': cihazKimligi,
      if (pin != null) 'pin': pin else 'gosteri_kisisi': true,
      'oturum': oturum,
      'yanlis': 0,
      'kilit_bitis': null,
    };
    _cihazAc();
    await _sakla();
    await _cevrimiciHazirla();
    acik = true;
    await _okumalariYenile();
    kayit!['ad'] = kisiBilgisi['ad'] ?? kod;
    await _sabah();
    await _sakla();
    _dinle();
  }

  Future<void> gosteriKisisiniDegistir(GosteriKisisi secilen) async {
    if (!gosteriKisileri.contains(secilen)) {
      throw ArgumentError('Kişi listede yok');
    }
    await _yereliSifirla();
    mesgul = true;
    _bildir();
    try {
      await _sirala(() async {
        final oturum = await bulut.giris(secilen.kod, secilen.sifre);
        await _kaydiOlustur(secilen.kod, oturum);
      });
    } catch (_) {
      acik = false;
      mesaj = 'Gösteri hesabına giriş yapılamadı. Bağlantıyı kontrol edip yeniden dene.';
    } finally {
      mesgul = false;
      _bildir();
    }
    if (acik) unawaited(gonderici.tetikle());
  }

  Future<void> kaydol(
    String kod,
    String ilkParola,
    String pin,
    String tekrar,
  ) async {
    if (mesgul) return;
    mesgul = true;
    mesaj = null;
    _bildir();
    try {
      await _sirala(() async {
        kod = kod.trim().toUpperCase();
        if (!RegExp(r'^K\d{3}$').hasMatch(kod)) {
          throw ArgumentError('Kişi kodu K017 gibi olmalı');
        }
        if (pin != tekrar) throw ArgumentError('Şifreler aynı olmalı');
        final ozet = await Pin.olustur(pin);
        final oturum = await bulut.giris(kod, ilkParola);
        await bulut.parolaDegistir(pin);
        await _kaydiOlustur(kod, oturum, pin: ozet);
      });
    } finally {
      mesgul = false;
      _bildir();
    }
    unawaited(gonderici.tetikle());
  }

  Future<bool> kilitAc(String pin) async {
    if (mesgul || kayit == null || kilitSaniye > 0) return false;
    mesgul = true;
    mesaj = null;
    _bildir();
    var dogru = false;
    try {
      await _sirala(() async {
        dogru = await Pin.dogrula(pin, Json.from(kayit!['pin'] as Map));
        if (!dogru) {
          final yanlis = (kayit!['yanlis'] as int? ?? 0) + 1;
          kayit!['yanlis'] = yanlis;
          if (yanlis >= 10) {
            yerel.remove('kayit');
            cihaz = null;
            acik = false;
            mesaj = '10 yanlış deneme. Bu telefonu yeniden kaydet';
          } else if (yanlis >= 5) {
            kayit!['kilit_bitis'] = guvenlikSaati()
                .add(const Duration(seconds: 30))
                .toIso8601String();
            mesaj = '30 saniye bekle';
          } else {
            mesaj = 'Şifre yanlış';
          }
          await _sakla();
          return;
        }
        kayit!['yanlis'] = 0;
        kayit!['kilit_bitis'] = null;
        acik = true;
        try {
          await _cevrimiciHazirla();
          await _okumalariYenile();
        } catch (_) {
          baglanti = false;
        }
        await _sabah();
        await _sakla();
        _dinle();
      });
    } finally {
      mesgul = false;
      _bildir();
    }
    if (dogru) unawaited(gonderici.tetikle());
    return dogru;
  }

  Future<void> _cevrimiciHazirla() async {
    kayit!['oturum'] = await bulut.oturumYenile(
      kayit!['oturum']['refresh_token'] as String,
    );
    final t0 = saat.simdi();
    final sunucu = await bulut.simdi();
    cihaz!.saatFarkiOlc(t0, sunucu, saat.simdi());
    final harf = kayit!['harf'] as String;
    cihaz!.sayaciEsitle(await bulut.cihazEsitle(cihaz!.cihazAdi, harf: harf));
    baglanti = true;
  }

  Future<void> _sabah() async {
    // Telefonda mesai düğmeleri yalnız çalışan ekranındadır.
    if (telefonKipi && (liderMi || bilgisayardanKullanilir)) return;
    if (!mesaiIcinde) return;
    final bugun = cihaz!.simdiDuzeltilmis().tarih.isoformat();
    if (kayit!['ilk_acilis'] != bugun && hal['durum'] == 'MESAI_DISI') {
      await _yaz('MESAI.GIRDIM', {}, [], []);
    }
    kayit!['ilk_acilis'] = bugun;
  }

  void _dinle() {
    if (gosterimMi) return;
    final ekler = {
      ...birimKanallari,
      if (acikProje != null) 'proje:$acikProje',
    };
    final kanallar = [kisi, ...ekler].join('|');
    if (_dinlenenKanallar == kanallar) return;
    _dinlenenKanallar = kanallar;
    unawaited(_sinyal?.cancel());
    _sinyal = bulut
        .sinyaller(kisi, ekKanallar: ekler)
        .listen(
          (_) {
            _debounce?.cancel();
            _debounce = Timer(const Duration(milliseconds: 300), yenile);
          },
          onError: (Object _) {
            baglanti = false;
            _bildir();
          },
        );
  }

  Future<Json> _oku(String veri, {String? hedef, Json? g}) async {
    final cevap = await bulut.oku(veri, hedef: _hedef(veri, hedef), g: g);
    yerel['onbellek'][_anahtar(veri, hedef, g)] = {
      'cevap': cevap,
      'an': gosterimMi
          ? gosterim!['an']
          : cihaz!.simdiDuzeltilmis().isoformat(),
    };
    return cevap;
  }

  Future<void> _okumalariYenile() async {
    if (gosterimMi) {
      for (final q in [
        const Okuma('KISILER'),
        const Okuma('BIRIMLER'),
        const Okuma('PROJELER'),
        ...ekranOkumalari,
      ]) {
        await _oku(q.veri, hedef: q.hedef, g: q.g);
      }
      baglanti = true;
      return;
    }
    await _oku('KISILER');
    kayit?['ad'] = kisiBilgisi['ad'] ?? kisi;
    if (telefonKipi && bilgisayardanKullanilir) {
      ekranOkumalari = [];
      baglanti = true;
      return;
    }
    if (telefonKipi && liderMi) {
      await _oku('BILDIRIMLER');
      await _oku('ONAY_LISTESI');
      final ekip = Okuma('EKIP', hedef: birim);
      final havuz = Okuma('HAVUZ', hedef: birim);
      await _oku(ekip.veri, hedef: ekip.hedef);
      await _oku(havuz.veri, hedef: havuz.hedef);
      final listeler = [
        for (final p in satirlar('EKIP', hedef: birim))
          Okuma('LISTE', hedef: p['kisi'] as String),
      ];
      for (final q in listeler) {
        await _oku(q.veri, hedef: q.hedef);
      }
      ekranOkumalari = [ekip, havuz, ...listeler, const Okuma('ONAY_LISTESI')];
      await _isBaglaminiOku();
      baglanti = true;
      return;
    }
    for (final veri in ['BILDIRIMLER', 'KODLAR']) {
      await _oku(veri);
    }
    if (calisanEsitlemesi) {
      final ids = _esitlenecekOlaylar(cihaz!);
      final paket = await (bulut as TelefonEsitlemeBulutu)
          .telefonEsitle(ids)
          .timeout(const Duration(seconds: 15));
      _telefonPaketiniUygula(cihaz!, ids, paket);
    } else {
      await _oku('TELEFON');
    }
    if (webDuzeni) {
      await _oku('BIRIMLER');
    } else {
      await _oku('LISTE');
    }
    // Açık web ekranı, kişinin yaka/rolünden bağımsız olarak yeniden okunur.
    for (final q in ekranOkumalari) {
      await _oku(q.veri, hedef: q.hedef, g: q.g);
    }
    if (telefonKipi) await _isBaglaminiOku();
    kayit?['ad'] = kisiBilgisi['ad'] ?? telefon['kisi']?['ad'] ?? kisi;
    baglanti = true;
  }

  Future<void> _isBaglaminiOku() async {
    // İsim yardımcıları iş kapısını kapatmaz; kimlik yerine eksik bilgi metni gösterilir.
    try {
      await _oku('PROJELER');
      final ids = <String>{
        for (final i in isler.values)
          if (i['proje'] is String) i['proje'] as String,
        for (final i in satirlar('HAVUZ', hedef: birim))
          if (i['proje'] is String) i['proje'] as String,
        for (final p in satirlar('EKIP', hedef: birim))
          for (final i
              in nesne('LISTE', hedef: p['kisi'] as String)['isler'] as List? ??
                  [])
            if (i['proje'] is String) i['proje'] as String,
      };
      for (final id in ids) {
        await _oku('ETAPLAR', hedef: id);
      }
    } catch (_) {
      /* Tazelik ve iş sonucu ayrı zorunlu okumalardan denetlenir. */
    }
  }

  Future<Json> listeOnizlemesi(String kisi) => _sirala(() async {
    final cevap = await _oku('LISTE', hedef: kisi);
    await _sakla();
    _bildir();
    return Json.from(cevap['deger'] as Map);
  });

  Future<void> ekranOku(List<Okuma> okumalar) async {
    ekranOkumalari = okumalar;
    await yenile();
  }

  Future<void> _yereliSifirla() async {
    if (mesgul) throw StateError('İşlem bitince yeniden dene');
    mesgul = true;
    _bildir();
    try {
      gonderici.beklemeyiDurdur();
      await _telefonAgSirasi;
      await _sirala(() async {
        // Devam eden kalıcı yazım/gönderim tamamlanır; bulutta silme yapılmaz.
        await depo.yaz({});
        gonderici.beklemeyiDurdur();
        _debounce?.cancel();
        _hesap?.cancel();
        await _sinyal?.cancel();
        _sinyal = null;
        _dinlenenKanallar = null;
        yerel = {
          'cihazlar': <String, dynamic>{},
          'onbellek': <String, dynamic>{},
          'yuklemeler': <dynamic>[],
        };
        cihaz = null;
        acik = false;
        acikProje = null;
        ekranOkumalari = [];
        kaliciHata = false;
        mesaj = null;
        islemHatasi = null;
      });
    } finally {
      mesgul = false;
      _bildir();
    }
  }

  Future<void> ekOku(Okuma q) async {
    ekranOkumalari = [...ekranOkumalari.where((x) => x.veri != q.veri), q];
    await yenile();
  }

  Future<Json> yonetim(
    String kod, {
    Json girdiler = const {},
    List<Json> hedefler = const [],
    String? adina,
    Json? hassasEk,
    Map<String, dynamic> beklenenListeler = const {},
    bool sonucuBekle = false,
  }) async {
    if (!yonetimAcik) throw StateError('Bağlantı bekleniyor');
    mesgul = true;
    mesaj = null;
    _bildir();
    try {
      return await _sirala(() async {
        // Sıra beklerken yaşlanan okumalar da kapıyı kapatır.
        if (!baglanti ||
            !ekranOkumalari.every(
              (q) => taze(q.veri, hedef: q.hedef, g: q.g),
            )) {
          throw StateError('Bağlantı bekleniyor');
        }
        final hs = hedefler.map((h) => Json.from(h)).toList();
        for (final k in listeHedefleri({
          'eylem_kodu': kod,
          'girdiler': girdiler,
        })) {
          if (!taze('LISTE', hedef: k)) throw StateError('Liste yenilenmeli');
          if (beklenenListeler.containsKey(k) &&
              jsonEncode(beklenenListeler[k]) !=
                  jsonEncode(nesne('LISTE', hedef: k)['surum'])) {
            throw StateError(
              'İş sırası değişmiş. Güncel sırayı inceleyip tekrar deneyin.',
            );
          }
          hs.add({
            'tur': 'LISTE',
            'kimlik': k,
            'surum': nesne('LISTE', hedef: k)['surum'],
          });
        }
        final q = ekranOkumalari.first;
        final cache = onbellek[_anahtar(q.veri, q.hedef, q.g)];
        final e = cihaz!.yonetimHazirla(
          kod,
          {'son_hesap_ani': cache['cevap']['hesap_ani']},
          eylemSemalari: semalar,
          baglanti: baglanti,
          okumaAni: cache['an'],
          hedefler: hs,
          girdiler: girdiler,
          adina: adina,
        );
        // A20: kişi/yetki değişikliği olay anında geçerlidir.
        if (kod == 'KISI.DEGISTIRDIM') {
          e['girdiler']['gecerli_baslangic'] = e['oldugu_an'];
          cihaz!.kaydet();
        }
        await _sakla();
        Json c;
        try {
          try {
            c = await bulut
                .olayEkle(e, oturum: kisi, hassasEk: hassasEk)
                .timeout(yonetimZamanAsimi);
          } on TimeoutException {
            c = await bulut
                .olayEkle(e, oturum: kisi, hassasEk: hassasEk)
                .timeout(yonetimZamanAsimi);
          }
          // Önceki hesabın bitmesini aynı olayla bekle; yeni olay üretme.
          final son = DateTime.now().add(const Duration(seconds: 12));
          while (c['kod'] == 'HESAP_BEKLIYOR' && DateTime.now().isBefore(son)) {
            await Future<void>.delayed(const Duration(milliseconds: 750));
            c = await bulut
                .olayEkle(e, oturum: kisi, hassasEk: hassasEk)
                .timeout(yonetimZamanAsimi);
          }
        } catch (error) {
          if (error.toString().contains('IRP|BICIM|')) {
            c = {
              'sonuc': 'REDDEDILDI',
              'kod': 'BICIM',
              'neden': error.toString(),
            };
          } else {
            c = {'sonuc': 'BAGLANTI_YOK', 'neden': error.toString()};
            baglanti = false;
          }
        }
        cihaz!.veri['gunluk'][e['olay_kimligi']] = {
          'olay': e,
          'sonuc': c,
          'durum': c['sonuc'] == 'BASARILI'
              ? 'GONDERILDI'
              : c['sonuc'] == 'BAGLANTI_YOK'
              ? 'GONDERILEMEDI'
              : 'RED',
        };
        cihaz!.kaydet();
        await _sakla();
        mesaj = c['sonuc'] == 'BASARILI'
            ? null
            : c['sonuc'] == 'BAGLANTI_YOK'
            ? 'Bağlantı bekleniyor'
            : cevapMetni(c);
        if (c['sonuc'] == 'BASARILI' ||
            const ['BAYAT', 'DURUM'].contains(c['kod'])) {
          try {
            await _okumalariYenile();
          } catch (_) {
            baglanti = false;
          }
        }
        if (c['kod'] == 'HESAP_BEKLIYOR') {
          _hesap?.cancel();
          _hesap = Timer(const Duration(seconds: 5), yenile);
        }
        await _sakla();
        if (sonucuBekle) {
          if (c['sonuc'] == 'BASARILI') {
            return _yayinSonucu(e['olay_kimligi'] as String);
          }
          return {...c, 'olay_kimligi': e['olay_kimligi']};
        }
        return c;
      });
    } finally {
      mesgul = false;
      _bildir();
    }
  }

  // Bu kapı yeni olay üretmez. Yanıt kaybolduysa aynı kalıcı olay yeniden gönderilir.
  Future<Json> yonetimSonucunuKontrolEt(String olay) async {
    if (mesgul) throw StateError('İşlem Sürüyor');
    mesgul = true;
    _bildir();
    try {
      return await _sirala(() async {
        final entry = cihaz?.veri['gunluk'][olay];
        if (entry == null) throw StateError('İşlem bu cihazda bulunamadı.');
        if (entry['durum'] == 'GONDERILEMEDI') {
          Json sonuc;
          try {
            sonuc = await bulut
                .olayEkle(Json.from(entry['olay']), oturum: kisi)
                .timeout(yonetimZamanAsimi);
          } catch (_) {
            return {'sonuc': 'BEKLIYOR', 'olay_kimligi': olay};
          }
          entry['sonuc'] = sonuc;
          entry['durum'] = sonuc['sonuc'] == 'BASARILI' ? 'GONDERILDI' : 'RED';
          cihaz!.kaydet();
          await _sakla();
          if (sonuc['sonuc'] != 'BASARILI') {
            return {...sonuc, 'olay_kimligi': olay};
          }
        }
        return _yayinSonucu(olay);
      });
    } finally {
      mesgul = false;
      _bildir();
    }
  }

  Duration yayinZamanAsimi = const Duration(seconds: 15);
  Future<Json> _yayinSonucu(String olay) async {
    final kapi = bulut;
    var durum = 'TAMAMLANDI';
    if (kapi is IslemSonucuBulutu) {
      final sure = Stopwatch()..start();
      do {
        try {
          final kalan = yayinZamanAsimi - sure.elapsed;
          final r = await (kapi as IslemSonucuBulutu)
              .islemSonucu(olay)
              .timeout(
                kalan > Duration.zero ? kalan : const Duration(milliseconds: 1),
              );
          durum = r['durum'] as String? ?? 'DOGRULANAMADI';
        } catch (_) {
          durum = 'DOGRULANAMADI';
        }
        if (durum != 'BEKLIYOR' || sure.elapsed >= yayinZamanAsimi) break;
        await Future<void>.delayed(const Duration(milliseconds: 500));
      } while (sure.elapsed < yayinZamanAsimi);
    }
    if (durum == 'TAMAMLANDI') {
      try {
        await _okumalariYenile();
        await _sakla();
        return {
          'sonuc': 'BASARILI',
          'islem_durumu': durum,
          'olay_kimligi': olay,
        };
      } catch (_) {
        durum = 'EKRAN_BEKLIYOR';
      }
    }
    final bekliyor = const [
      'BEKLIYOR',
      'DOGRULANAMADI',
      'EKRAN_BEKLIYOR',
    ].contains(durum);
    mesaj = bekliyor
        ? 'İşlemin sonucu henüz doğrulanamadı. Sonucu kontrol edin; aynı işlem yeniden oluşturulmaz.'
        : 'İşlem tamamlanmadı. Güncel işi kontrol edin.';
    return {
      'sonuc': bekliyor ? 'BEKLIYOR' : 'REDDEDILDI',
      'islem_durumu': durum,
      'olay_kimligi': olay,
    };
  }

  Future<void> yenile() async {
    if (!acik || _kapali || kaliciHata) return;
    if (calisanEsitlemesi) {
      return _telefonYenilemesi ??= _telefonAg(() async {
        try {
          await _calisaniOku();
        } catch (e) {
          if (e is BaglantiYok) baglanti = false;
        }
        _bildir();
      }).whenComplete(() => _telefonYenilemesi = null);
    }
    await _sirala(() async {
      if (!acik) return;
      try {
        await _okumalariYenile();
        await _sakla();
        _dinle();
      } catch (e) {
        baglanti = false;
        mesaj = e.toString();
      }
      _bildir();
    });
  }

  Future<void> oneGeldi() async {
    if (gosterimMi) return yenile();
    if (!acik) return;
    if (calisanEsitlemesi) {
      await _telefonAg(() async {
        try {
          await _cevrimiciHazirla();
          await _sirala(_sakla);
        } catch (e) {
          if (e is BaglantiYok) baglanti = false;
        }
      });
      await yenile();
      unawaited(gonderici.tetikle());
      return;
    }
    await _sirala(() async {
      try {
        await _cevrimiciHazirla();
        await _sakla();
      } catch (_) {
        baglanti = false;
      }
    });
    await yenile();
    await gonderici.tetikle();
  }

  Future<void> baglantiDegisti(bool varMi) async {
    baglanti = varMi;
    _bildir();
    if (varMi) await oneGeldi();
  }

  void kilitle() {
    if (gosterimMi || gosteriKisileri.isNotEmpty) return;
    acik = false;
    _bildir();
  }

  Future<Json> olay(
    String kod, {
    Json? girdiler,
    List<Json>? hedefler,
    List<HazirFoto> fotograflar = const [],
  }) async {
    if (gosterimMi || mesgul || !acik || kaliciHata) {
      throw StateError('Kayıt şu anda yazılamıyor');
    }
    islemHatasi = null;
    mesgul = true;
    mesaj = null;
    _bildir();
    late Json e;
    try {
      e = await _sirala(
        () => _yaz(kod, girdiler ?? {}, hedefler ?? [], fotograflar),
      );
    } finally {
      mesgul = false;
      _bildir();
    }
    unawaited(gonderici.tetikle());
    return e;
  }

  Future<Json> _yaz(
    String kod,
    Json girdiler,
    List<Json> hedefler,
    List<HazirFoto> fotograflar,
  ) async {
    if (semalar[kod]?['sinif'] != 'TANIKLIK') {
      throw ArgumentError('Bu ekranda tanıklık yazılır');
    }
    if (!calisan.contains(kod)) {
      final izinli = semalar[kod]['izinli_hedef_turleri'] as List?;
      final zorunlu = semalar[kod]['zorunlu_hedef_turu'];
      if (izinli != null &&
          (hedefler.isEmpty ||
              hedefler.any((h) => !izinli.contains(h['tur'])))) {
        throw ArgumentError('Notun bağlı olduğu kayıt türü geçersiz');
      }
      if (zorunlu != null && !hedefler.any((h) => h['tur'] == zorunlu)) {
        throw ArgumentError('Bağlı kayıt seçilmeli');
      }
      if (semalar[kod]['tek_gorev_hedefi'] == true &&
          hedefler.where((h) => h['tur'] == 'GOREV').length != 1) {
        throw ArgumentError('Tek görev seçilmeli');
      }
    }
    final bilinen = {
      ...sonHal,
      'son_hesap_ani':
          sonHal['son_hesap_ani'] ?? cihaz!.simdiDuzeltilmis().isoformat(),
    };
    final e = calisan.contains(kod)
        ? await cihaz!.olayYaz(
            kod,
            bilinen,
            isler: {
              for (final e in (telefon['isler'] as Map? ?? {}).entries)
                e.key as String: Json.from(e.value as Map),
            },
            liste: List<String>.from(telefon['liste'] as List? ?? []),
            isKimligi: kod.startsWith('IS.')
                ? (is_?['kimlik'] as String?)
                : null,
            girdiler: girdiler,
            sabitMola: sabitMola,
          )
        : cihaz!.tanikliYaz(
            kod,
            bilinen,
            eylemSemalari: semalar,
            girdiler: girdiler,
            hedefler: hedefler,
          );
    e['eylem_versiyonu'] = semalar[kod]['eylem_versiyonu'];
    for (var i = 0; i < fotograflar.length; i++) {
      final foto = fotograflar[i], sira = i + 1;
      final alanlar = foto.alanlar(e['olay_kimligi'] as String, sira);
      (e['kanit'] as List).add(alanlar);
      yuklemeler.add({
        'kisi': kisi,
        'olay': e['olay_kimligi'],
        'alanlar': alanlar,
        'yol': '${e['olay_kimligi']}/$sira-${foto.ad}',
        'bytes': base64Encode(foto.bytes),
      });
    }
    cihaz!.kaydet();
    await _sakla();
    return e;
  }

  // Ağ işlemleri yerel yazım sırasını tutmaz. Yalnız aynı oturumun
  // tutarlı paketi kısa yerel sıra içinde uygulanır.
  Future<void> _calisaniOku() async {
    final c = cihaz;
    if (c == null || !acik || _kapali) return;
    final ids = _esitlenecekOlaylar(c);
    final paket = await (bulut as TelefonEsitlemeBulutu)
        .telefonEsitle(ids)
        .timeout(const Duration(seconds: 15));
    await _sirala(() async {
      if (_kapali || !identical(cihaz, c) || !acik) return;
      _telefonPaketiniUygula(c, ids, paket);
      _dinle();
      await _sakla();
      _bildir();
    });
  }

  List<String> _esitlenecekOlaylar(Cihaz c) => (c.veri['gunluk'] as Map).entries
      .where(
        (e) => e.value['yerel_etki'] == true || e.value['durum'] == 'BEKLIYOR',
      )
      .map((e) => e.key as String)
      .toList();

  void _telefonPaketiniUygula(Cihaz c, List<String> ids, Json paket) {
    final telefonCevabi = Json.from(paket['telefon'] as Map);
    final sonuclar = paket['olay_sonuclari'] as Map;
    for (final id in ids) {
      final k = c.veri['gunluk'][id];
      if (k == null) continue;
      final sonuc = sonuclar[id];
      if (const [
        'TAMAMLANDI',
        'INCELEME_GEREKIYOR',
        'GECERSIZ',
      ].contains(sonuc)) {
        k['yerel_etki'] = false;
        k['durum'] = sonuc == 'TAMAMLANDI' ? 'GONDERILDI' : 'RED';
        k['yayin_sonucu'] = sonuc;
        if (sonuc != 'TAMAMLANDI') {
          islemHatasi =
              'Son işlem uygulanamadı. Güncel iş durumunu kontrol edin.';
        }
      }
    }
    yerel['onbellek'][_anahtar('TELEFON', null, null)] = {
      'cevap': telefonCevabi,
      'an': c.simdiDuzeltilmis().isoformat(),
    };
    baglanti = true;
    c.kaydet();
  }

  Future<void> _gonderCalisan() => _telefonAg(() async {
    final c = cihaz;
    if (c == null || !acik || _kapali || kaliciHata || mesgul) return;
    final olaylar = await _sirala(
      () async => [
        for (final k in (c.veri['gunluk'] as Map).values)
          if (k['durum'] == 'BEKLIYOR') kopya(Json.from(k['olay'] as Map)),
      ],
    );
    olaylar.sort((a, b) {
      final s = an(a['oldugu_an']).compareTo(an(b['oldugu_an']));
      return s != 0
          ? s
          : (a['olay_kimligi'] as String).compareTo(
              b['olay_kimligi'] as String,
            );
    });
    for (final e in olaylar) {
      if (!identical(c, cihaz) || _kapali) return;
      final cevap = await _CevapKapisi(
        bulut,
        (_) {},
      ).olayEkle(e, oturum: c.kisi);
      await _sirala(() async {
        if (!identical(c, cihaz) || _kapali) return;
        final k = c.veri['gunluk'][e['olay_kimligi']];
        if (k['yayin_sonucu'] != null) return;
        if (cevap['sonuc'] == 'BASARILI') {
          k['durum'] = 'GONDERILDI';
          k['yerel_etki'] = true;
        } else if (!const [
          'HESAP_BEKLIYOR',
          'BAKIMDA',
        ].contains(cevap['kod'])) {
          k['durum'] = 'RED';
          k['yerel_etki'] = false;
          islemHatasi = cevapMetni(cevap);
        }
        k['sonuc'] = cevap;
        await _sakla();
        _bildir();
      });
      if (cevap['sonuc'] != 'BASARILI') break;
    }
    // Fotoğraf teslimi olay tesliminden ayrı, aynı kişi ve aynı kimlikle.
    for (final yuk in List.from(yuklemeler)) {
      if (!identical(c, cihaz) || _kapali) return;
      if (yuk['kisi'] != c.kisi ||
          c.veri['gunluk'][yuk['olay']]?['durum'] != 'GONDERILDI') {
        continue;
      }
      await bulut.kanitYukle(
        yuk['yol'] as String,
        base64Decode(yuk['bytes'] as String),
        yuk['alanlar']['tur'] as String,
      );
      await _sirala(() async {
        yuklemeler.remove(yuk);
        await _sakla();
      });
    }
    await _calisaniOku();
  });

  Future<void> _gonder() => calisanEsitlemesi
      ? _gonderCalisan()
      : _sirala(() async {
          if (kayit == null || cihaz == null || kaliciHata) return;
          // Olay daha önce kalıcılaştırılmış olmalı; yarıda kesilen yanıttan sonra
          // aynı kimliğin tekrarı bulutta idempotenttir.
          try {
            await cihaz!.gonderimDongusu(
              _CevapKapisi(bulut, (c) {
                baglanti = true;
                if (c['sonuc'] != 'BASARILI') {
                  mesaj = cevapMetni(c);
                  if (c['kod'] == 'HESAP_BEKLIYOR') {
                    _hesap?.cancel();
                    _hesap = Timer(const Duration(seconds: 5), yenile);
                  }
                }
              }),
            );
            await _sakla();
            for (final yuk in List.from(yuklemeler)) {
              if (yuk['kisi'] != kisi ||
                  cihaz!.veri['gunluk'][yuk['olay']]?['durum'] !=
                      'GONDERILDI') {
                continue;
              }
              await bulut.kanitYukle(
                yuk['yol'] as String,
                base64Decode(yuk['bytes'] as String),
                yuk['alanlar']['tur'] as String,
              );
              yuklemeler.remove(yuk);
              await _sakla();
            }
            await _okumalariYenile();
          } on BaglantiYok {
            baglanti = false;
            rethrow;
          } on TimeoutException {
            baglanti = false;
            rethrow;
          } finally {
            cihaz!.kaydet();
            await _sakla();
            _bildir();
          }
        });
  @override
  void dispose() {
    _kapali = true;
    gonderici.dispose();
    _debounce?.cancel();
    _hesap?.cancel();
    _mesaiSaati?.cancel();
    unawaited(_sinyal?.cancel());
    unawaited(_oturumDegisimi?.cancel());
    super.dispose();
  }
}

class _CevapKapisi implements Bulut {
  _CevapKapisi(this.bulut, this.cevap);
  final UygulamaBulutu bulut;
  final void Function(Json) cevap;
  @override
  Future<Json> olayEkle(Json olay, {required String oturum}) async {
    Json c;
    try {
      c = await bulut
          .olayEkle(olay, oturum: oturum)
          .timeout(const Duration(seconds: 15));
    } catch (e) {
      if (!e.toString().contains('IRP|BICIM|')) rethrow;
      c = {'sonuc': 'REDDEDILDI', 'kod': 'BICIM', 'neden': e.toString()};
    }
    cevap(c);
    if (c['sonuc'] == 'BAKIMDA') throw const Bakimda();
    return c;
  }
}
