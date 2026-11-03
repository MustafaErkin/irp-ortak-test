import 'bulut.dart';
import 'hata.dart';
import 'kabul.dart';
import 'kapilar_v3.dart';
import 'kisi_gunu.dart';
import 'olay.dart';
import 'saat.dart';
import 'surum.dart';
import 'veri.dart';
import 'yerel_depo.dart';

class Cihaz {
  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:13 (__init__).
  Cihaz(
    this.kisi,
    this.harf,
    this.saat, {
    YerelDepo? yerelDepo,
    this.telefon = false,
    this.teslimiKoru = false,
  }) : yerelDepo = yerelDepo ?? BellekDeposu() {
    veri =
        this.yerelDepo.oku() ??
        {
          'sayaclar': <String, dynamic>{},
          'gunluk': <String, dynamic>{},
          'fark_saniye': 0,
        };
  }
  final bool telefon;
  final bool teslimiKoru;
  String get cihazAdi => "${telefon ? 'TEL' : 'MAS'}-$kisi";
  final String kisi;
  String? harf;
  final SaatKaynagi saat;
  final YerelDepo yerelDepo;
  late Sozluk veri;

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:20 (kaydet).
  void kaydet() => yerelDepo.yaz(veri);

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:27 (simdi_duzeltilmis).
  An simdiDuzeltilmis() => saat.simdi().ekle(
    Duration(microseconds: ciftYuvarla((veri['fark_saniye'] as num) * 1000000)),
  );

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:30 (saat_farki_olc).
  void saatFarkiOlc(Object t0, Object sunucu, Object t1) {
    final bas = an(t0);
    final orta = bas.ekle(
      Duration(
        microseconds: ciftYuvarla(an(t1).farkAl(bas).inMicroseconds / 2),
      ),
    );
    veri['fark_saniye'] = an(sunucu).farkAl(orta).inMicroseconds / 1000000;
    kaydet();
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:34 (olay_kimligi_uret).
  String olayKimligiUret() {
    // Tek isolate içinde sayaç ile kalıcı yazım arasında await yoktur.
    if (!dolu(harf)) {
      throw const ModelHatasi(
        'ConnectionError',
        'Yeni cihaz kaydi cevrimici ister',
      );
    }
    return _kimlikUret();
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:39 (depo_kayboldu).
  void depoKayboldu() {
    harf = null;
    veri = {
      'sayaclar': <String, dynamic>{},
      'gunluk': <String, dynamic>{},
      'fark_saniye': 0,
    };
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:43 (yeniden_kaydol).
  String yenidenKaydol(Set<String> kullanilanHarfler, {bool baglanti = true}) {
    if (!baglanti) {
      throw const ModelHatasi('ConnectionError', 'Cihaz kaydi cevrimici ister');
    }
    harf = null;
    for (final h in 'TUVWXYZABCDEFGHIJKLMNOPQRS'.split('')) {
      if (!kullanilanHarfler.contains(h)) {
        harf = h;
        break;
      }
    }
    if (harf == null) {
      throw const ModelHatasi('OverflowError', 'Cihaz harfleri doldu');
    }
    kullanilanHarfler.add(harf!);
    kaydet();
    return harf!;
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:52 (_kimlik_uret).
  String _kimlikUret() {
    final tarih = simdiDuzeltilmis().tarih
        .isoformat()
        .replaceAll('-', '')
        .substring(2);
    final sayaclar = veri['sayaclar'] as Map;
    final sayac = (sayaclar[tarih] as int? ?? 0) + 1;
    if (sayac > 9999) {
      throw const ModelHatasi('OverflowError', 'A1 kimlik alani doldu');
    }
    sayaclar[tarih] = sayac;
    kaydet();
    return '$kisi-$tarih${sayac.toString().padLeft(4, '0')}-$harf';
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:60 (sayaci_esitle).
  void sayaciEsitle(Iterable<String> bulutKimlikleri) {
    final tarih = simdiDuzeltilmis().tarih
        .isoformat()
        .replaceAll('-', '')
        .substring(2);
    final bas = '$kisi-$tarih';
    final sayaclar = veri['sayaclar'] as Map;
    var enBuyuk = sayaclar[tarih] as int? ?? 0;
    for (final k in bulutKimlikleri) {
      if (k.startsWith(bas) && k.endsWith('-${harf!}')) {
        final n = int.parse(k.split('-')[1].substring(6));
        if (n > enBuyuk) enBuyuk = n;
      }
    }
    sayaclar[tarih] = enBuyuk;
    kaydet();
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:68 (gunluk_ekle).
  void gunlukEkle(Sozluk e) {
    veri['gunluk'][e['olay_kimligi']] = {
      'olay': e,
      'durum': 'BEKLIYOR',
      if (teslimiKoru) 'yerel_etki': true,
    };
    kaydet();
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:72 (gonderim_dongusu).
  Future<Sozluk?> gonderimDongusu(Bulut depo, {bool baglanti = true}) async {
    if (!baglanti) return {'bekle_saniye': 2, 'bekleyen': bekleyenSayisi()};
    final kayitlar = (veri['gunluk'] as Map).values.cast<Sozluk>().toList()
      ..sort((a, b) {
        final siralama = metinSirasi(
          a['olay']['oldugu_an'],
          b['olay']['oldugu_an'],
        );
        return siralama != 0
            ? siralama
            : metinSirasi(a['olay']['olay_kimligi'], b['olay']['olay_kimligi']);
      });
    for (final kayit in kayitlar) {
      if (kayit['durum'] != 'BEKLIYOR') continue;
      final sonuc = await depo.olayEkle(kayit['olay'], oturum: kisi);
      kayit['durum'] = sonuc['sonuc'] == 'BASARILI' ? 'GONDERILDI' : 'HATA';
      kayit['sonuc'] = sonuc;
    }
    kaydet();
    return null;
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:81 (bekleyen_sayisi).
  int bekleyenSayisi() => (veri['gunluk'] as Map).values
      .where((k) => k['durum'] == 'BEKLIYOR')
      .length;

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:84 (gunluk_temizle).
  void gunlukTemizle() {
    final sinir = simdiDuzeltilmis().ekle(const Duration(days: -30));
    veri['gunluk'] = <String, dynamic>{
      for (final e in (veri['gunluk'] as Map).entries)
        if (e.value['durum'] != 'GONDERILDI' ||
            e.value['yerel_etki'] == true ||
            an(e.value['olay']['oldugu_an']).compareTo(sinir) >= 0)
          e.key as String: e.value,
    };
    kaydet();
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:89 (ekran_hali).
  Sozluk ekranHali(
    Sozluk sonHal, {
    Map<String, Sozluk>? isler,
    List<String>? liste,
  }) {
    var d = Sozluk.from(sonHal);
    if (!dolu(d['son_hesap_ani']) ||
        an(d['son_hesap_ani']).tarih != simdiDuzeltilmis().tarih) {
      d = bosHal();
    }
    final bekleyen =
        [
          for (final k in (veri['gunluk'] as Map).values)
            if (k['durum'] == 'BEKLIYOR' ||
                (teslimiKoru &&
                    k['yerel_etki'] == true &&
                    k['durum'] == 'GONDERILDI'))
              k['olay'] as Sozluk,
        ]..sort((a, b) {
          final s = an(a['oldugu_an']).compareTo(an(b['oldugu_an']));
          return s != 0 ? s : metinSirasi(a['olay_kimligi'], b['olay_kimligi']);
        });
    isler ??= {};
    liste ??= [];
    if (teslimiKoru) {
      isler = {for (final e in isler.entries) e.key: Sozluk.from(e.value)};
      liste = List<String>.from(liste);
    }
    for (final e in bekleyen) {
      if (an(e['oldugu_an']).tarih != simdiDuzeltilmis().tarih) continue;
      final ids = hedefler(e, 'IS');
      var is_ = ids.isNotEmpty ? isler[ids[0]] : null;
      if (teslimiKoru &&
          is_ != null &&
          const {'BITTI', 'IPTAL'}.contains(is_['durum'])) {
        continue;
      }
      if (ids.isEmpty || dolu(is_)) {
        if (teslimiKoru &&
            e['eylem_kodu'] == 'IS.TAMAMLADIM' &&
            is_ != null &&
            (!dolu(is_['onay_gerekli']) || is_['onay_beklet'] == false)) {
          liste.remove(is_['kimlik']);
          isler[is_['kimlik']] = {
            ...is_,
            'durum': dolu(is_['onay_gerekli']) ? 'ONAY_BEKLIYOR' : 'BITTI',
          };
          // Aynı mevcut kural: bekletmeyen onay kişi gününü boşaltır (SQL056).
          is_ = {...is_, 'onay_gerekli': false};
        }
        d = gecis(
          d,
          e['eylem_kodu'],
          is_: is_,
          basIs: liste.isNotEmpty ? isler[liste[0]] : null,
          neden: e['girdiler']['neden'],
        ).$1;
        if (teslimiKoru && calisan.contains(e['eylem_kodu'])) {
          d['baslangic'] = e['oldugu_an'];
          d['acan_olay'] = e['olay_kimligi'];
          d['son_olay_ani'] = e['oldugu_an'];
        }
      }
    }
    return {
      'son_hal': d,
      'bekleyen': bekleyen,
      if (teslimiKoru) 'liste': liste,
      if (teslimiKoru) 'isler': isler,
    };
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:102 (tazelik).
  bool tazelik(bool baglanti, Object? sonEsitleme) {
    if (!baglanti || !dolu(sonEsitleme)) return false;
    final fark = simdiDuzeltilmis().farkAl(an(sonEsitleme!)).inMicroseconds;
    return fark >= 0 && fark <= 30000000;
  }

  // Kaynak: referans/cevap_anahtari/model/irp/cihaz.py:105 (olay_yaz).
  Future<Sozluk> olayYaz(
    String kod,
    Sozluk sonHal, {
    Map<String, Sozluk>? isler,
    List<String>? liste,
    String? isKimligi,
    Sozluk? girdiler,
    List<dynamic>? kanit,
    bool sabitMola = false,
    Bulut? depo,
    bool baglanti = true,
  }) async {
    if (!taniklik.contains(kod) &&
        !tazelik(baglanti, sonHal['son_hesap_ani'])) {
      throw const ModelHatasi(
        'ValueError',
        'Yonetim icin taze baglanti gerekli',
      );
    }
    isler ??= {};
    liste ??= [];
    final ekran = ekranHali(sonHal, isler: isler, liste: liste);
    if (!kapi(
      ekran['son_hal'],
      kod,
      teslimiKoru ? ekran['isler'][isKimligi] : isler[isKimligi],
      teslimiKoru
          ? ((ekran['liste'] as List).firstOrNull as String?)
          : (liste.isNotEmpty ? liste[0] : null),
      sabit: sabitMola,
    )) {
      throw const ModelHatasi('ValueError', 'Cihaz kapisi kapali');
    }
    final e = _zarf(
      kod,
      sonHal,
      hedefler: [
        if (dolu(isKimligi)) {'tur': 'IS', 'kimlik': isKimligi, 'surum': null},
      ],
      girdiler: girdiler,
      kanit: kanit,
    );
    final kimlik = e['olay_kimligi'];
    if (taniklik.contains(kod)) {
      gunlukEkle(e);
    } else {
      for (final x in e['neyin_ustunde']) {
        x['surum'] = al(isler[x['kimlik']] ?? {}, 'surum', 0);
      }
      for (final k in listeHedefleri(e)) {
        e['neyin_ustunde'].add({
          'tur': 'LISTE',
          'kimlik': k,
          'surum': al(
            al(sonHal, 'liste_surumleri', {}),
            k,
            k == kisi ? ozet(liste) : null,
          ),
        });
      }
      final sonuc = depo != null && baglanti
          ? await depo.olayEkle(e, oturum: kisi)
          : <String, dynamic>{'sonuc': 'BAGLANTI_YOK'};
      veri['gunluk'][kimlik] = {
        'olay': e,
        'durum': sonuc['sonuc'] == 'BASARILI'
            ? 'GONDERILDI'
            : sonuc['sonuc'] == 'BAGLANTI_YOK'
            ? 'GONDERILEMEDI'
            : 'RED',
        'sonuc': sonuc,
      };
      kaydet();
    }
    return e;
  }

  /// T17 §4.2: kişi günü dışındaki tanıklıklar aynı sayaç ve günlüğü kullanır.
  /// Sınıf, çağıranın yüklediği yetkili eylem kataloğundan gelir.
  Sozluk tanikliYaz(
    String kod,
    Sozluk sonHal, {
    required Sozluk eylemSemalari,
    List<Sozluk>? hedefler,
    Sozluk? girdiler,
    List<dynamic>? kanit,
  }) {
    if (eylemSemalari[kod]?['sinif'] != 'TANIKLIK' || calisan.contains(kod)) {
      throw const ModelHatasi(
        'ValueError',
        'Bu eylem tanikliYaz kapısından geçemez',
      );
    }
    final e = _zarf(
      kod,
      sonHal,
      hedefler: hedefler ?? [],
      girdiler: girdiler,
      kanit: kanit,
    );
    gunlukEkle(e);
    return e;
  }

  /// T17 §4.3: okunan sürümleri taşıyan yönetim zarfı. Tanıklık kuyruğuna
  /// girmez; çağıran kalıcılaştırdıktan sonra doğrudan gönderir.
  Sozluk yonetimHazirla(
    String kod,
    Sozluk sonHal, {
    required Sozluk eylemSemalari,
    required bool baglanti,
    required dynamic okumaAni,
    required List<Sozluk> hedefler,
    required Sozluk girdiler,
    String? adina,
  }) {
    if (eylemSemalari[kod] == null ||
        eylemSemalari[kod]['sinif'] == 'TANIKLIK' ||
        !tazelik(baglanti, okumaAni)) {
      throw const ModelHatasi(
        'ValueError',
        'Yönetim için taze bağlantı gerekli',
      );
    }
    if (hedefler.any((h) => h['surum'] == null)) {
      throw const ModelHatasi('ValueError', 'Okunan nesnenin sürümü gerekli');
    }
    final gerekli = eylemSemalari[kod]['zorunlu_hedef_turu'];
    if (gerekli != null && !hedefler.any((h) => h['tur'] == gerekli)) {
      throw const ModelHatasi('ValueError', 'Bağlı kayıt seçilmeli');
    }
    final listeler = listeHedefleri({'eylem_kodu': kod, 'girdiler': girdiler});
    if (listeler.any(
      (k) => !hedefler.any((h) => h['tur'] == 'LISTE' && h['kimlik'] == k),
    )) {
      throw const ModelHatasi('ValueError', 'Okunan liste sürümü gerekli');
    }
    final e = _zarf(kod, sonHal, hedefler: hedefler, girdiler: girdiler);
    e['adina'] = adina;
    e['eylem_versiyonu'] = eylemSemalari[kod]['eylem_versiyonu'];
    veri['gunluk'][e['olay_kimligi']] = {'olay': e, 'durum': 'GONDERILEMEDI'};
    kaydet();
    return e;
  }

  Sozluk _zarf(
    String kod,
    Sozluk sonHal, {
    required List<Sozluk> hedefler,
    Sozluk? girdiler,
    List<dynamic>? kanit,
  }) {
    final t = simdiDuzeltilmis().isoformat();
    final kimlik = olayKimligiUret();
    final e = <String, dynamic>{
      'olay_kimligi': kimlik,
      'eylem_kodu': kod,
      'eylem_versiyonu': 1,
      'neyin_ustunde': hedefler,
      'giris_sekli': 'LISTE',
      'kim': kisi,
      'adina': null,
      'cihaz': cihazAdi,
      'uygulama_surumu': telefon ? 'AND-0.1.0' : 'WEB-0.1.0',
      'oldugu_an': t,
      'saat_dilimi': '+03:00',
      'bildigi_son_hal_ani': al(sonHal, 'son_hesap_ani', t),
      'girdiler': dolu(girdiler) ? girdiler : <String, dynamic>{},
      'kanit': dolu(kanit) ? kanit : <dynamic>[],
      'duzelttigi_olay': null,
      'yol': 'DISARIDA',
      'pc_ulasma_ani': null,
    };
    return e;
  }
}
