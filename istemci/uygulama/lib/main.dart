import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';

import 'bulut/uygulama_bulutu.dart';
import 'bulut/acilis_ayari.dart';
import 'bulut/supabase_bulutu.dart';
import 'durum/kalici_depo.dart';
import 'durum/platform_deposu.dart';
import 'durum/uygulama_durumu.dart';
import 'ekranlar/telefon/giris.dart';
import 'ekranlar/telefon/telefon.dart';
import 'ekranlar/telefon/ekibim.dart';
import 'ekranlar/kisi_degistir.dart';
import 'ekranlar/telefon/ortak.dart';
import 'sahte/fikstur_bulutu.dart';
import 'sahte/gosterim_bulutu.dart';
import 'ekranlar/web/web.dart';

Future<Json> _json(String yol) async =>
    Json.from(jsonDecode(await rootBundle.loadString(yol)) as Map);

Future<UygulamaDurumu> uygulamayiHazirla({
  String kip = const String.fromEnvironment('KIP'),
  String bulutAdi = const String.fromEnvironment('BULUT'),
  String adres = const String.fromEnvironment('SUPABASE_URL'),
  String anon = const String.fromEnvironment('SUPABASE_ANON'),
  String gosteriKisileri = const String.fromEnvironment('GOSTERI_KISILERI'),
  String gosteriSenaryosu = const String.fromEnvironment('GOSTERI_SENARYOSU'),
  bool mvpMesaiSerbest = const bool.fromEnvironment('MVP_MESAI_SERBEST'),
  Future<Json> Function(String) jsonYukle = _json,
}) async {
  final ayar = await acilisAyariniOku(
    web: kIsWeb,
    sayfa: Uri.base,
    kip: kip,
    bulut: bulutAdi,
    adres: adres,
    anon: anon,
    gosteriKisileri: gosteriKisileri,
  );
  if (ayar.gosterim) {
    final b = GosterimBulutu(await jsonYukle('assets/gosterim.json'));
    final d = UygulamaDurumu(
      bulut: b,
      depo: BellekKaliciDepo(),
      semalar: {},
      saat: Saat(b.bilgi['an'] as String),
      gosterim: b.bilgi,
    );
    await d.yukle();
    return d;
  }
  final UygulamaBulutu bulut;
  if (ayar.supabase) {
    bulut = SupabaseBulutu.ayarli(ayar.adres!, ayar.anon!);
  } else {
    bulut = FiksturBulutu(
      await jsonYukle('test/fikstur/telefon.json'),
      webFikstur: birlestirFikstur(
        await jsonYukle('test/fikstur/web.json'),
        await jsonYukle('test/fikstur/yonetim.json'),
      ),
    );
  }
  final d = UygulamaDurumu(
    bulut: bulut,
    depo: await platformDeposu(
      senaryo: ayar.kisiler.isEmpty ? '' : gosteriSenaryosu,
    ),
    semalar: await jsonYukle('assets/eylem_semalari.json'),
    saat: SistemSaati(),
    mvpSadeceCalisan: const bool.fromEnvironment('MVP_TELEFON_CALISAN'),
    telefonKipi: !kIsWeb && defaultTargetPlatform == TargetPlatform.android,
    gosteriKisileri: ayar.kisiler,
    mvpMesaiSerbest: mvpMesaiSerbest,
  );
  await d.yukle();
  if (bulut is SupabaseBulutu) d.oturumIzle(bulut.oturumlar);
  return d;
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    final harita = Map<String, String>.from(
      jsonDecode(await rootBundle.loadString('assets/cizimler/harita.json'))
          as Map,
    );
    final durum = await uygulamayiHazirla();
    runApp(IrpApp(durum: durum, cizimler: harita, donanim: !durum.gosterimMi));
  } catch (hata) {
    runApp(
      MaterialApp(
        theme: tema(Brightness.light),
        debugShowCheckedModeBanner: false,
        home: Scaffold(
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                hata is BulutAyariHatasi
                    ? 'Bulut ayarı okunamadı. ayar.json dosyasını ve derleme ayarlarını kontrol et.'
                    : 'Uygulama açılamadı. Depolama izinlerini ve derleme ayarlarını kontrol et.',
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class IrpApp extends StatefulWidget {
  const IrpApp({
    super.key,
    required this.durum,
    required this.cizimler,
    this.donanim = true,
  });
  final UygulamaDurumu durum;
  final Map<String, String> cizimler;
  final bool donanim;
  @override
  State<IrpApp> createState() => _IrpAppState();
}

class _IrpAppState extends State<IrpApp> with WidgetsBindingObserver {
  StreamSubscription<List<ConnectivityResult>>? _baglanti;
  final _gezgin = GlobalKey<NavigatorState>();
  bool _onceAcik = false;
  void _kilitDegisti() {
    if (_onceAcik && !widget.durum.acik) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _gezgin.currentState?.popUntil((r) => r.isFirst);
      });
    }
    _onceAcik = widget.durum.acik;
  }

  @override
  void initState() {
    super.initState();
    _onceAcik = widget.durum.acik;
    widget.durum.addListener(_kilitDegisti);
    if (widget.donanim) {
      WidgetsBinding.instance.addObserver(this);
      _baglanti = Connectivity().onConnectivityChanged.listen((r) {
        unawaited(
          widget.durum.baglantiDegisti(!r.contains(ConnectivityResult.none)),
        );
      });
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(widget.durum.oneGeldi());
    // Dosya seçici/kamera da uygulamayı geçici olarak arkaya alır.
    // PIN süreç/sayfa açılışında sorulur; öne geliş yalnız veriyi yeniler.
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    widget.durum.removeListener(_kilitDegisti);
    unawaited(_baglanti?.cancel());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    navigatorKey: _gezgin,
    title: 'Sibernetik IRP',
    locale: const Locale('tr'),
    supportedLocales: const [Locale('tr')],
    localizationsDelegates: GlobalMaterialLocalizations.delegates,
    debugShowCheckedModeBanner: false,
    theme: tema(Brightness.light),
    darkTheme: tema(Brightness.dark),
    builder: (context, child) => ListenableBuilder(
      listenable: widget.durum,
      builder: (context, _) => ColoredBox(
        color: Theme.of(context).scaffoldBackgroundColor,
        child: Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth:
                  widget.durum.acik &&
                      !widget.durum.telefonKipi &&
                      widget.durum.webDuzeni
                  ? double.infinity
                  : 480,
            ),
            child: child,
          ),
        ),
      ),
    ),
    home: ListenableBuilder(
      listenable: widget.durum,
      builder: (context, _) => KeyedSubtree(
        key: ValueKey(
          widget.durum.kayit?['cihaz_kimligi'] ?? widget.durum.kisi,
        ),
        child: widget.durum.acik
            ? widget.durum.telefonKipi &&
                      widget.durum.liderMi &&
                      !widget.durum.mvpSadeceCalisan
                  ? Ekibim(durum: widget.durum)
                  : widget.durum.telefonKipi &&
                        widget.durum.bilgisayardanKullanilir
                  ? BilgisayarHesabi(durum: widget.durum)
                  : !widget.durum.telefonKipi && widget.durum.webDuzeni
                  ? WebEkrani(durum: widget.durum)
                  : Telefon(durum: widget.durum, cizimler: widget.cizimler)
            : widget.durum.gosteriKisileri.isNotEmpty
            ? GosteriGirisi(durum: widget.durum)
            : Giris(durum: widget.durum),
      ),
    ),
  );
}
