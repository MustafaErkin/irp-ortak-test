import 'dart:async';

import 'package:flutter/material.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';
import '../telefon/ortak.dart';
import '../kisi_degistir.dart';
import 'teslim.dart';
import 'olay_akisi.dart';
import 'yonetim.dart';

/// Denetleyiciler, kapanış animasyonu bitip alanlar ayrıldıktan sonra bırakılır.
Future<T?> guvenliDialog<T>({
  required BuildContext context,
  required WidgetBuilder builder,
}) async {
  final r = DialogRoute<T>(context: context, builder: builder);
  final sonuc = await Navigator.of(context).push(r);
  await r.completed;
  return sonuc;
}

String metin(dynamic x) => x == null ? '—' : '$x';
String baslik(Json x) =>
    '${x['islem'] ?? x['is_tanimi'] ?? x['ad'] ?? x['kimlik']}';
String dakika(dynamic x) {
  final n = (x as num? ?? 0).round();
  return '${n ~/ 60} sa ${n % 60} dk';
}

String zaman(dynamic x) => x == null ? '—' : '$x'.substring(11, 16);
String durumAdi(dynamic x) =>
    const {
      'CALISIYOR': 'Çalışıyor',
      'CALISILIYOR': 'Çalışıyor',
      'CALISMIYOR': 'Başlamadı',
      'MESAI_DISI': 'Mesai dışı',
      'ONAY_BEKLIYOR': 'Onay bekliyor',
      'ARIZADA': 'Duruş',
      'MOLADA': 'Molada',
      'SABIT_MOLADA': 'Sabit mola',
      'SABIT_MOLA': 'Sabit mola',
      'ACIK': 'Açık',
      'ATANDI': 'Atandı',
      'GONDERILDI': 'Gönderildi',
      'DEGISTI': 'Değişti',
      'DEVAM_BEKLIYOR': 'Devam bekliyor',
      'SIRADA': 'Sırada',
      'YARIM': 'Yarım',
      'BITTI': 'Tamamlandı',
      'BEKLIYOR': 'Bekliyor',
      'KABUL_BEKLIYOR': 'Kabul bekliyor',
      'KABUL_EDILDI': 'Kabul edildi',
      'TASLAK': 'Taslak',
      'ONAY_GEREKMIYOR': 'Onay gerekmiyor',
      'ONAYLANDI': 'Onaylandı',
      'IADE': 'İade',
      'CALISMA': 'Çalışma',
      'MOLA': 'Mola',
      'GECIS': 'Geçiş',
      'TANIMSIZ': 'Tanımsız',
      'YENIDEN_ISLEME': 'Yeniden işleme',
      'BEKLEME_ARIZA': 'Duruşta bekleme',
      'BEKLEME_ONAY': 'Onay bekleme',
      'BEKLEME_ON_IS': 'Ön iş bekleme',
    }[x] ??
    metin(x);
Json hedef(Json x, [String tur = 'IS']) => {
  'tur': tur,
  'kimlik': x['kimlik'],
  'surum': x['surum'],
};

class WebEkrani extends StatefulWidget {
  const WebEkrani({super.key, required this.durum, this.ilkSayfa});
  final UygulamaDurumu durum;
  final String? ilkSayfa;
  @override
  State<WebEkrani> createState() => _WebEkraniState();
}

class _WebEkraniState extends State<WebEkrani> {
  UygulamaDurumu get d => widget.durum;
  String kisiAdi(dynamic kimlik) =>
      d
          .satirlar('KISILER')
          .where((p) => p['kimlik'] == kimlik)
          .firstOrNull?['ad'] ??
      metin(kimlik);
  late String sayfa, gun, kisi;
  String seciliBirim = 'IMALAT';
  String get ekipBirimi => d.yetkiliMi ? seciliBirim : d.birim;
  bool get birimSecimi =>
      d.yetkiliMi &&
      [
        'İş Ataması',
        'Plansız iş',
        'Takip',
        'Kişinin günü',
        'Gün sonu onayı',
      ].contains(sayfa);
  String? proje;
  bool yukleniyor = true;
  Timer? timer;
  List<Json> get ekipKisileri => d
      .satirlar('KISILER')
      .where(
        (x) =>
            x['birim'] == ekipBirimi &&
            x['aktif'] == true &&
            x['kimlik'] != d.kisi,
      )
      .toList();
  bool get ustSayfa =>
      d.yoneticiMi && (yonetimSayfalari.contains(sayfa) || sayfa == 'Onaylar');
  Json? sonrakiGorev;
  List<String> get rolMenuleri => d.gosterimMi
      ? ['Projeler', 'Raporlar', 'Personel dağılımı', 'Adil Performans']
      : d.yoneticiMi
      ? [
          'Personel dağılımı',
          'Projeler',
          'Görev Atama',
          'Onaylar',
          'Raporlar',
          'Adil Performans',
          'Parçalar ve belgeler',
          if (d.yetkiliMi) ...['Maaş dağılımı', 'Yönetim'],
          'İşlerim',
          'Bildirimler',
          if (d.yetkiliMi) ...[
            'İş Ataması',
            'Takip',
            'Kişinin günü',
            'Gün sonu onayı',
          ],
        ]
      : d.liderMi
      ? [
          'İş Ataması',
          'Takip',
          'Onaylar',
          'Kişinin günü',
          'Gün sonu onayı',
          'Bildirimler',
        ]
      : ['İşlerim', 'Benim performansım', 'Bildirimler'];
  List<String> get menuler => [
    ...rolMenuleri,
    if (!d.gosterimMi && d.gosteriKisileri.isNotEmpty) 'Olay akışı',
  ];
  @override
  void initState() {
    super.initState();
    sayfa =
        widget.ilkSayfa ??
        (d.gosterimMi
            ? 'Projeler'
            : d.yetkiliMi
            ? 'Personel dağılımı'
            : d.yoneticiMi
            ? 'Onaylar'
            : d.liderMi
            ? 'Takip'
            : 'İşlerim');
    if (d.gosterimMi && !menuler.contains(sayfa)) sayfa = 'Projeler';
    gun = d.bugun;
    kisi = ekipKisileri.firstOrNull?['kimlik'] as String? ?? d.kisi;
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
    unawaited(yukle());
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  List<Okuma> okumalar() {
    final ekip = Okuma('EKIP', hedef: ekipBirimi);
    final listeler = [
      for (final p in ekipKisileri) Okuma('LISTE', hedef: p['kimlik']),
    ];
    return switch (sayfa) {
      'İş Ataması' => [
        Okuma('HAVUZ', hedef: ekipBirimi),
        const Okuma('KISILER'),
        ekip,
        ...listeler,
      ],
      'Plansız iş' => [
        const Okuma('PROJELER'),
        const Okuma('KISILER'),
        const Okuma('KODLAR'),
        ...listeler,
        if (proje != null) Okuma('ETAPLAR', hedef: proje),
      ],
      'Onaylar' => [const Okuma('ONAY_LISTESI'), ekip],
      'Takip' => [ekip, const Okuma('BILDIRIMLER')],
      'Kişinin günü' => [
        Okuma('KISININ_GUNU', hedef: kisi, g: {'tarih': gun}),
      ],
      'Gün sonu onayı' => [
        const Okuma('GUN_ISLERI'),
        for (final p in ekipKisileri)
          Okuma('GUN', hedef: p['kimlik'], g: {'gun': gun}),
      ],
      'İşlerim' => [const Okuma('GOREV'), const Okuma('GUN_ISLERI')],
      'Benim performansım' => [
        Okuma('PERFORMANS', g: {'bas': '${gun.substring(0, 8)}01', 'bit': gun}),
        Okuma(
          'BIRIM_PERFORMANS',
          hedef: d.birim,
          g: {'bas': '${gun.substring(0, 8)}01', 'bit': gun},
        ),
      ],
      _ => [const Okuma('BILDIRIMLER')],
    };
  }

  Future<void> yukle() async {
    if (sayfa == 'Olay akışı') {
      if (mounted) setState(() => yukleniyor = false);
      return;
    }
    if (ustSayfa) {
      yukleniyor = false;
      await d.yenile();
      return;
    }
    d.acikProje = null;
    if (mounted) setState(() => yukleniyor = true);
    await d.ekranOku(okumalar());
    if (sayfa == 'Plansız iş' && proje == null) {
      proje = d
          .satirlar('PROJELER')
          .where((x) => x['aktif'] == true)
          .firstOrNull?['kimlik'];
      if (proje != null) await d.ekranOku(okumalar());
    }
    if (mounted) setState(() => yukleniyor = false);
    if (sayfa == 'Bildirimler' && d.bildirimler.isNotEmpty) {
      await d.olay(
        'BILDIRIM.GORDUM',
        girdiler: {'bildirimler': d.bildirimler.map(bildirimKimligi).toList()},
      );
    }
  }

  void sec(String s) {
    setState(() => sayfa = s);
    unawaited(yukle());
  }

  bool get acik => !yukleniyor && d.yonetimAcik;
  Widget dugme(
    String yazi,
    VoidCallback bas, {
    bool yonetim = true,
    Key? key,
  }) => FilledButton(
    key: key,
    onPressed: (!yonetim || acik) && !d.mesgul ? bas : null,
    child: Text(yazi),
  );
  Future<void> yaz(
    String kod, {
    Json girdiler = const {},
    List<Json> hedefler = const [],
    String? adina,
  }) async {
    await isle(context, () async {
      await d.yonetim(
        kod,
        girdiler: girdiler,
        hedefler: hedefler,
        adina: adina,
      );
    });
  }

  Future<void> gerekce(
    String title,
    String kod,
    Json girdiler,
    List<Json> hs,
    String alan,
  ) async {
    final c = TextEditingController();
    await guvenliDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 400,
          child: TextField(
            key: const Key('gerekce'),
            controller: c,
            decoration: const InputDecoration(labelText: 'Açıklama'),
            maxLines: 3,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Vazgeç'),
          ),
          ListenableBuilder(
            listenable: d,
            builder: (_, _) => YonetimDugmesi(
              durum: d,
              onPressed: acik
                  ? () async {
                      if (c.text.trim().isEmpty) return;
                      await yaz(
                        kod,
                        girdiler: {...girdiler, alan: c.text.trim()},
                        hedefler: hs,
                      );
                      if (ctx.mounted) Navigator.pop(ctx);
                    }
                  : null,
              child: const Text('Kaydet'),
            ),
          ),
        ],
      ),
    );
    c.dispose();
  }

  Future<void> ata(Json is_, {String? kime, bool devir = false}) async {
    var secilen =
        kime ??
        ekipKisileri
                .where((p) => !devir || p['kimlik'] != is_['kisi'])
                .firstOrNull?['kimlik']
            as String?;
    if (secilen == null) return;
    if (kime == null) {
      final sonuc = await guvenliDialog<String>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, degistir) => AlertDialog(
            title: Text(devir ? 'İşi devret' : 'Kişi seç'),
            content: SizedBox(
              width: 360,
              child: DropdownButtonFormField<String>(
                initialValue: secilen,
                decoration: const InputDecoration(labelText: 'Kişi'),
                items: [
                  for (final p in ekipKisileri.where(
                    (p) => !devir || p['kimlik'] != is_['kisi'],
                  ))
                    DropdownMenuItem(
                      value: p['kimlik'] as String,
                      child: Text(p['ad'] as String),
                    ),
                ],
                onChanged: (v) => degistir(() => secilen = v),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Vazgeç'),
              ),
              YonetimDugmesi(
                durum: d,
                onPressed: () => Navigator.pop(ctx, secilen),
                child: Text(devir ? 'Devret' : 'Ata'),
              ),
            ],
          ),
        ),
      );
      if (sonuc == null) return;
      secilen = sonuc;
    }
    await yaz(
      devir ? 'IS.DEVRETTIM' : 'IS.ATADIM',
      hedefler: [hedef(is_)],
      girdiler: devir
          ? {'kimden': is_['kisi'], 'kime': secilen, 'kime_sira': 1}
          : {
              'kisi': secilen,
              'sira':
                  (d.nesne('LISTE', hedef: secilen)['isler'] as List? ?? [])
                      .length +
                  1,
            },
    );
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: d,
    builder: (context, _) => LayoutBuilder(
      builder: (context, o) {
        final genis = o.maxWidth >= 900;
        final nav = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 28, 20, 32),
              child: Text(
                'SİBERNETİK\nIRP',
                style: TextStyle(
                  fontSize: 21,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 2,
                ),
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    for (final m in menuler)
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 3,
                        ),
                        child: ListTile(
                          key: Key('menu-$m'),
                          selected: sayfa == m,
                          selectedTileColor: Theme.of(context)
                              .colorScheme
                              .primaryContainer,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          dense: true,
                          title: Text(m, style: const TextStyle(fontSize: 14)),
                          onTap: () {
                            if (!genis) Navigator.pop(context);
                            sec(m);
                          },
                        ),
                      ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Text(
                d.ad,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            if (!d.gosterimMi && d.gosteriKisileri.isEmpty)
              TextButton.icon(
                onPressed: d.kilitle,
                icon: const Icon(Icons.lock_outline, size: 18),
                label: const Text('Kilitle'),
              ),
            const SizedBox(height: 20),
          ],
        );
        final govde = Scaffold(
          appBar: AppBar(
            title: Text(sayfa),
            actions: [
              if (d.gosteriKisileri.isNotEmpty) KisiDegistirMenusu(durum: d),
              if (d.gosterimMi)
                Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: Center(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerLow,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Padding(
                        padding: EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        child: Text(
                          'Örnek veri',
                          style: TextStyle(fontSize: 12),
                        ),
                      ),
                    ),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Center(
                  child: Text(
                    d.gosterimMi
                        ? '15 Aralık 2026'
                        : ustSayfa
                        ? d.bugun
                        : gun,
                    style: const TextStyle(fontSize: 14),
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Yenile',
                onPressed: () => yukle(),
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          drawer: genis ? null : Drawer(child: SafeArea(child: nav)),
          body: Column(
            children: [
              if (yukleniyor) const LinearProgressIndicator(),
              if (d.mesaj != null) Bant(d.mesaj!),
              if (d.hesapBekliyor) const Bant('Hesaplanıyor'),
              if (!d.baglanti || d.bekleyen > 0)
                Bant(
                  '${d.baglanti ? 'Bağlantı var' : 'Bağlantı yok'} · ${d.bekleyen} kayıt bekliyor',
                ),
              if (d.liderMi && !acik && !yukleniyor && sayfa != 'Olay akışı')
                const Bant('Bağlantı bekleniyor · İşlem yapmak için yenile'),
              if (birimSecimi)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: SizedBox(
                      width: 340,
                      child: DropdownButtonFormField<String>(
                        initialValue: ekipBirimi,
                        isExpanded: true,
                        decoration: const InputDecoration(labelText: 'Birim'),
                        items: [
                          for (final b in d.satirlar('BIRIMLER'))
                            DropdownMenuItem(
                              value: b['kimlik'] as String,
                              child: Text(b['ad']),
                            ),
                        ],
                        onChanged: (v) {
                          setState(() {
                            seciliBirim = v!;
                            kisi =
                                ekipKisileri.firstOrNull?['kimlik'] ?? d.kisi;
                          });
                          unawaited(yukle());
                        },
                      ),
                    ),
                  ),
                ),
              Expanded(
                child: SingleChildScrollView(
                  padding: EdgeInsets.all(genis ? 28 : 16),
                  child: ustSayfa
                      ? YonetimSayfa(
                          key: ValueKey(sayfa),
                          durum: d,
                          sayfa: sayfa,
                          baslangic: sonrakiGorev,
                          sonraki: (g) {
                            sonrakiGorev = g;
                            sec('Görev Atama');
                          },
                        )
                      : switch (sayfa) {
                          'Olay akışı' =>
                            menuler.contains('Olay akışı')
                                ? OlayAkisi(durum: d)
                                : const SizedBox(),
                          'İş Ataması' => atama(),
                          'Plansız iş' => PlansizForm(
                            durum: d,
                            birim: ekipBirimi,
                            kisiler: ekipKisileri,
                            proje: proje,
                            projeSec: (v) {
                              proje = v;
                              unawaited(yukle());
                            },
                          ),
                          'Onaylar' => onaylar(),
                          'Takip' => takip(),
                          'Kişinin günü' => kisininGunu(),
                          'Gün sonu onayı' => gunSonu(),
                          'İşlerim' => Islerim(durum: d),
                          'Benim performansım' => performans(),
                          _ => bildirimler(),
                        },
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 12),
                child: Row(
                  children: [
                    Icon(
                      Icons.circle,
                      size: 7,
                      color: d.baglanti ? Colors.green : Colors.orange,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${d.gosterimMi
                            ? 'Gösterim'
                            : d.baglanti
                            ? 'Bağlı'
                            : 'Çevrimdışı'} · ${d.ad}',
                        style: const TextStyle(fontSize: 12),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (genis)
                      Text(
                        d.yetkiliMi
                            ? 'Yetkili'
                            : d.yoneticiMi
                            ? 'Yönetici'
                            : d.liderMi
                            ? 'Ekip lideri'
                            : 'İşlerim',
                        style: const TextStyle(fontSize: 12),
                      ),
                  ],
                ),
              ),
            ],
          ),
        );
        return genis
            ? Row(
                children: [
                  SizedBox(
                    width: 210,
                    child: Material(
                      color: Theme.of(context).colorScheme.surface,
                      child: nav,
                    ),
                  ),
                  const VerticalDivider(width: 1),
                  Expanded(child: govde),
                ],
              )
            : govde;
      },
    ),
  );
  Widget atama() {
    final havuz = d.satirlar('HAVUZ', hedef: ekipBirimi);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'İşi sürükle veya çift tıklayıp kişi seç.',
                style: TextStyle(fontSize: 14),
              ),
            ),
            dugme('+ Plansız iş', () => sec('Plansız iş'), yonetim: false),
          ],
        ),
        const SizedBox(height: 20),
        IkiSutun(
          sol: Kutu(
            'İş havuzu',
            children: [
              if (havuz.isEmpty) const Text('Havuzda bekleyen iş yok.'),
              for (final i in havuz)
                Draggable<Json>(
                  data: i,
                  maxSimultaneousDrags: acik ? 1 : 0,
                  feedback: Material(
                    elevation: 8,
                    borderRadius: BorderRadius.circular(8),
                    child: SizedBox(
                      width: 260,
                      child: ListTile(title: Text(baslik(i))),
                    ),
                  ),
                  childWhenDragging: Opacity(opacity: .35, child: isKart(i)),
                  child: GestureDetector(
                    key: Key('havuz-${i['kimlik']}'),
                    onDoubleTap: acik ? () => ata(i) : null,
                    child: isKart(i),
                  ),
                ),
            ],
          ),
          sag: Column(
            children: [
              for (final p in ekipKisileri)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: DragTarget<Json>(
                    key: Key('liste-${p['kimlik']}'),
                    onWillAcceptWithDetails: (_) => acik,
                    onAcceptWithDetails: (x) => ata(x.data, kime: p['kimlik']),
                    builder: (ctx, aday, _) => Kutu(
                      p['ad'] as String,
                      vurgu: aday.isNotEmpty,
                      children: [
                        ReorderableListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount:
                              (d.nesne('LISTE', hedef: p['kimlik'])['isler']
                                          as List? ??
                                      [])
                                  .length,
                          buildDefaultDragHandles: acik,
                          onReorderItem: (eski, yeni) {
                            final xs =
                                d.nesne('LISTE', hedef: p['kimlik'])['isler']
                                    as List;
                            if (yeni == eski) return;
                            yaz(
                              'IS.SIRALADIM',
                              hedefler: [hedef(Json.from(xs[eski]))],
                              girdiler: {
                                'kisi': p['kimlik'],
                                'yeni_sira': yeni + 1,
                              },
                            );
                          },
                          itemBuilder: (ctx, n) {
                            final i = Json.from(
                              d.nesne('LISTE', hedef: p['kimlik'])['isler'][n],
                            );
                            return ListTile(
                              key: ValueKey(i['kimlik']),
                              contentPadding: const EdgeInsets.only(right: 28),
                              leading: Text('${n + 1}'),
                              title: Text(
                                baslik(i),
                                style: const TextStyle(fontSize: 15),
                              ),
                              subtitle: Text(
                                '${durumAdi(i['durum'])} · ${i['tahmini_sure_dk'] ?? '—'} dk',
                              ),
                              trailing: PopupMenuButton<String>(
                                enabled: acik,
                                tooltip: 'İş işlemleri',
                                onSelected: (v) => v == 'devir'
                                    ? ata(i, devir: true)
                                    : yaz(
                                        'IS.SIRALADIM',
                                        hedefler: [hedef(i)],
                                        girdiler: {
                                          'kisi': p['kimlik'],
                                          'yeni_sira': 1,
                                        },
                                      ),
                                itemBuilder: (_) => [
                                  const PopupMenuItem(
                                    value: 'one',
                                    child: Text('Öne al'),
                                  ),
                                  const PopupMenuItem(
                                    value: 'devir',
                                    child: Text('Devret'),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                        if ((d.nesne('LISTE', hedef: p['kimlik'])['isler']
                                    as List? ??
                                [])
                            .isEmpty)
                          const Padding(
                            padding: EdgeInsets.all(16),
                            child: Text('İşi buraya bırak'),
                          ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget isKart(Json i) => Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: ListTile(
      leading: const Icon(Icons.drag_indicator),
      title: Text(baslik(i)),
      subtitle: Text(
        '${i['proje'] ?? 'Proje dışı'} · ${i['parca_kodu'] ?? ''}',
      ),
      trailing: Text('${i['tahmini_sure_dk'] ?? '—'} dk'),
    ),
  );
  Widget takip() => Kutu(
    'Ekip şu an',
    children: [
      for (final p in d.satirlar('EKIP', hedef: ekipBirimi))
        ListTile(
          contentPadding: const EdgeInsets.symmetric(vertical: 10),
          title: Text(kisiAdi(p['kisi'])),
          subtitle: Text(takipMetni(p)),
          isThreeLine: true,
          trailing: IconButton(
            tooltip: 'Kişinin günü',
            onPressed: () {
              kisi = p['kisi'];
              sec('Kişinin günü');
            },
            icon: const Icon(Icons.arrow_forward),
          ),
        ),
      if (d.bildirimler.isNotEmpty)
        Bant(bildirimMetni(d.bildirimler.first), bas: () => sec('Bildirimler')),
    ],
  );
  String bildirimMetni(Json b) {
    final kod = b['metin'];
    final p = d
        .satirlar('KISILER')
        .where((p) => p['kimlik'] == kod)
        .firstOrNull;
    return p == null ? metin(kod) : '${p['ad']} · Yeni bildirim';
  }

  String takipMetni(Json p) {
    final h = Json.from(p['hal']);
    final bos = h['durum'] == 'CALISMIYOR';
    final calisti = (p['calisma_dk'] as num? ?? 0) > 0;
    final parcalar = <String>[
      bos && calisti ? 'Boşta' : durumAdi(h['durum']),
      if (p['is_'] != null) baslik(Json.from(p['is_'])),
      if (h['baslangic'] != null && bos && calisti)
        "son iş ${zaman(h['baslangic'])}'da bitti"
      else if (h['baslangic'] != null)
        '${zaman(h['baslangic'])} itibarıyla',
    ];
    return '${parcalar.join(' · ')}\nBugün çalışma ${dakika(p['calisma_dk'])}';
  }

  Widget onaylar() => IkiSutun(
    sol: Kutu(
      'Onay bekleyen işler',
      children: [
        if (d.satirlar('ONAY_LISTESI').isEmpty)
          const Text('Onay bekleyen iş yok.'),
        for (final i in d.satirlar('ONAY_LISTESI'))
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  baslik(i),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                Text(
                  '${kisiAdi(i['tamamlayan'] ?? i['kisi'])} · ${zaman(i['onay_bekleme_ani'])} itibarıyla',
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  children: [
                    dugme(
                      'Reddet',
                      () => gerekce('Reddet', 'IS.REDDETTIM', {}, [
                        hedef(i),
                      ], 'not'),
                    ),
                    dugme(
                      'Onayla',
                      () => yaz('IS.ONAYLADIM', hedefler: [hedef(i)]),
                      key: Key('onay-${i['kimlik']}'),
                    ),
                  ],
                ),
              ],
            ),
          ),
      ],
    ),
    sag: Kutu(
      'Duruştan dönüş bekleyenler',
      children: [
        if (!d
            .satirlar('EKIP', hedef: ekipBirimi)
            .any(
              (p) =>
                  p['hal']['durum'] == 'ARIZADA' &&
                  p['hal']['devam_izni'] != true,
            ))
          const Text('Dönüş bekleyen kişi yok.'),
        for (final p
            in d
                .satirlar('EKIP', hedef: ekipBirimi)
                .where(
                  (p) =>
                      p['hal']['durum'] == 'ARIZADA' &&
                      p['hal']['devam_izni'] != true &&
                      p['is_'] != null,
                ))
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(p['ad']),
              Text(baslik(Json.from(p['is_']))),
              Text(
                '${p['hal']['neden'] ?? 'Duruş'} · ${zaman(p['hal']['baslangic'])}',
              ),
              const SizedBox(height: 12),
              dugme(
                'Devam onayı',
                () => yaz(
                  'IS.DEVAM_ONAYLADIM',
                  hedefler: [hedef(Json.from(p['is_']))],
                ),
              ),
              TextButton(
                onPressed: () => sec('İş Ataması'),
                child: const Text('Başka iş ver'),
              ),
            ],
          ),
      ],
    ),
  );
  Widget kisiSecici() => Wrap(
    spacing: 16,
    runSpacing: 12,
    children: [
      SizedBox(
        width: 260,
        child: DropdownButtonFormField<String>(
          key: ValueKey('kisi-$kisi'),
          isExpanded: true,
          initialValue: kisi,
          items: [
            for (final p
                in d.satirlar('KISILER').where((p) => p['birim'] == ekipBirimi))
              DropdownMenuItem(
                value: p['kimlik'] as String,
                child: Text(p['ad']),
              ),
          ],
          onChanged: (v) {
            kisi = v!;
            unawaited(yukle());
          },
          decoration: const InputDecoration(labelText: 'Kişi'),
        ),
      ),
      TextButton.icon(
        onPressed: () async {
          final x = await showDatePicker(
            context: context,
            initialDate: DateTime.parse(gun),
            firstDate: DateTime(2020),
            lastDate: DateTime.parse(d.bugun),
          );
          if (x != null) {
            gun = x.toIso8601String().substring(0, 10);
            unawaited(yukle());
          }
        },
        icon: const Icon(Icons.calendar_month),
        label: Text(gun),
      ),
    ],
  );
  Widget kisininGunu() {
    final x = d.nesne('KISININ_GUNU', hedef: kisi, g: {'tarih': gun});
    final kovalar = Json.from(x['kovalar'] as Map? ?? {});
    final araliklar = x['araliklar'] as List? ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        kisiSecici(),
        const SizedBox(height: 24),
        IkiSutun(
          sol: Kutu(
            'Günün özeti',
            children: [
              for (final e in kovalar.entries)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(durumAdi(e.key)),
                  trailing: Text(dakika(e.value)),
                ),
              if (kovalar.isEmpty) const Text('Bu gün için süre kaydı yok.'),
            ],
          ),
          sag: Kutu(
            'Zaman çizelgesi',
            children: [
              for (final a in araliklar)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.schedule),
                  title: Text(
                    '${zaman(a['baslangic'])} – ${zaman(a['bitis'])}',
                  ),
                  subtitle: Text(
                    '${durumAdi(a['kova'])} · ${a['parca_kodu'] ?? ''}',
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 12,
          children: [
            dugme('Günü tamamla', () => sureEkle(x)),
            dugme('Kaydı geçersiz say', () => gecersiz(x)),
          ],
        ),
      ],
    );
  }

  Future<void> sureEkle(Json x) async {
    final isler = Json.from(x['isler'] as Map? ?? {}).values
        .map((v) => Json.from(v as Map))
        .toList();
    if (isler.isEmpty) return;
    final bas = TextEditingController(text: '08:00'),
        bit = TextEditingController(text: '09:00'),
        aciklama = TextEditingController();
    var isId = isler.last['kimlik'] as String;
    var bitti = false;
    await guvenliDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, degistir) => AlertDialog(
          title: const Text('Günü tamamla'),
          content: SizedBox(
            width: 440,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: isId,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'İş'),
                    items: [
                      for (final i in isler)
                        DropdownMenuItem(
                          value: i['kimlik'] as String,
                          child: Text(
                            baslik(i),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                    ],
                    onChanged: (v) => isId = v!,
                  ),
                  TextField(
                    key: const Key('sure-bas'),
                    controller: bas,
                    decoration: const InputDecoration(
                      labelText: 'Başlangıç · SS:DD',
                    ),
                  ),
                  TextField(
                    key: const Key('sure-bit'),
                    controller: bit,
                    decoration: const InputDecoration(
                      labelText: 'Bitiş · SS:DD',
                    ),
                  ),
                  TextField(
                    key: const Key('sure-aciklama'),
                    controller: aciklama,
                    decoration: const InputDecoration(labelText: 'Açıklama'),
                  ),
                  CheckboxListTile(
                    title: const Text('İş bitti'),
                    value: bitti,
                    onChanged: (v) => degistir(() => bitti = v!),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Vazgeç'),
            ),
            YonetimDugmesi(
              durum: d,
              onPressed: () async {
                if (!RegExp(r'^([01]\d|2[0-3]):[0-5]\d$').hasMatch(bas.text) ||
                    !RegExp(r'^([01]\d|2[0-3]):[0-5]\d$').hasMatch(bit.text) ||
                    bas.text.compareTo(bit.text) >= 0 ||
                    aciklama.text.trim().isEmpty) {
                  return;
                }
                await yaz(
                  'IS.SURE_EKLEDIM',
                  adina: kisi,
                  hedefler: [
                    hedef(isler.firstWhere((i) => i['kimlik'] == isId)),
                  ],
                  girdiler: {
                    'baslangic': '${gun}T${bas.text}:00+03:00',
                    'bitis': '${gun}T${bit.text}:00+03:00',
                    'aciklama': aciklama.text.trim(),
                    'is_bitti': bitti,
                  },
                );
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: const Text('Kaydet'),
            ),
          ],
        ),
      ),
    );
    bas.dispose();
    bit.dispose();
    aciklama.dispose();
  }

  Future<void> gecersiz(Json x) async {
    final kayitlar = x['kayitlar'] as List? ?? [];
    final secilen = await guvenliDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('Kaydı seç'),
        children: [
          for (final k in kayitlar)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(ctx, k['kimlik']),
              child: Text('${zaman(k['an'])} · ${k['eylem']}'),
            ),
        ],
      ),
    );
    if (secilen != null) {
      await gerekce(
        'Kaydı geçersiz say',
        'KAYIT.GECERSIZ_SAYDIM',
        {'hedef': secilen},
        [],
        'gerekce',
      );
    }
  }

  Widget gunSonu() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      kisiSecici(),
      const SizedBox(height: 24),
      Kutu(
        'Gün sonu onayı',
        children: [
          for (final p in ekipKisileri)
            Builder(
              builder: (ctx) {
                final r = d.nesne('GUN', hedef: p['kimlik'], g: {'gun': gun});
                final k = r['ozet']?['kovalar'] ?? {};
                final gerekli =
                    r['onay_durumu'] != 'ONAY_GEREKMIYOR' && r.isNotEmpty;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Wrap(
                    spacing: 20,
                    runSpacing: 12,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      SizedBox(
                        width: 210,
                        child: Text(
                          p['ad'],
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                      Text('Çalışma ${dakika(k['CALISMA'])}'),
                      Text('Tanımsız ${dakika(k['TANIMSIZ'])}'),
                      Text(durumAdi(r['onay_durumu'])),
                      if (gerekli) ...[
                        if (p['yaka'] != 'MAVI')
                          dugme(
                            'İade et',
                            () => gerekce(
                              'Günü iade et',
                              'GUN_SONU.IADE_ETTIM',
                              {'kisi': p['kimlik'], 'gun': gun},
                              [],
                              'gerekce',
                            ),
                          ),
                        dugme(
                          'Onayla',
                          () => yaz(
                            'GUN_SONU.ONAYLADIM',
                            girdiler: {
                              'kisi': p['kimlik'],
                              'gun': gun,
                              'ozet_surumu': r['ozet_surumu'],
                            },
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    ],
  );
  Widget performans() {
    final g = {'bas': '${gun.substring(0, 8)}01', 'bit': gun};
    final x = d.nesne('PERFORMANS', g: g),
        b = d.nesne('BIRIM_PERFORMANS', hedef: d.birim, g: g);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '$gun itibarıyla bu ay',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            Olcu(
              'Zaman',
              '${x['zamaninda'] ?? 0} / ${x['teslim'] ?? 0}',
              'zamanında teslim',
            ),
            Olcu('Kalite', '${x['kalite_ret'] ?? 0}', 'ret'),
            Olcu(
              'Çözüm',
              '${(x['cozum_saatleri'] as List? ?? []).length}',
              'tamamlanan çözüm',
            ),
            Olcu('Katkı', '${x['katki_saat'] ?? 0} sa', 'proje dışı'),
          ],
        ),
        const SizedBox(height: 28),
        Kutu(
          'Birimim · Genel performans',
          children: [
            Text(
              '${b['zamaninda'] ?? 0} / ${b['teslim'] ?? 0} zamanında teslim · ${b['kalite_ret'] ?? 0} ret',
            ),
            const SizedBox(height: 8),
            const Text(
              'Yalnızca birimin toplam göstergeleri gösterilir.',
              style: TextStyle(fontSize: 13),
            ),
          ],
        ),
      ],
    );
  }

  Widget bildirimler() => Kutu(
    'Bildirimler',
    children: [
      if (d.satirlar('BILDIRIMLER').isEmpty) const Text('Bildirimin yok.'),
      for (final b in d.satirlar('BILDIRIMLER'))
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.notifications_none),
          title: Text(bildirimMetni(b)),
          subtitle: Text(metin(b['an'] ?? b['olusturma_ani'])),
          trailing: Icon(
            b['gorulme_ani'] == null ? Icons.circle_outlined : Icons.done,
            size: 18,
          ),
        ),
    ],
  );
}

class YonetimDugmesi extends StatefulWidget {
  const YonetimDugmesi({
    super.key,
    required this.durum,
    required this.onPressed,
    required this.child,
  });
  final UygulamaDurumu durum;
  final VoidCallback? onPressed;
  final Widget child;
  @override
  State<YonetimDugmesi> createState() => _YonetimDugmesiState();
}

class _YonetimDugmesiState extends State<YonetimDugmesi> {
  Timer? timer;
  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.durum,
    builder: (_, _) => FilledButton(
      onPressed: widget.durum.yonetimAcik ? widget.onPressed : null,
      child: widget.child,
    ),
  );
}

class IkiSutun extends StatelessWidget {
  const IkiSutun({super.key, required this.sol, required this.sag});
  final Widget sol, sag;
  @override
  Widget build(BuildContext context) => MediaQuery.sizeOf(context).width >= 900
      ? Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: sol),
            const SizedBox(width: 22),
            Expanded(child: sag),
          ],
        )
      : Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [sol, const SizedBox(height: 20), sag],
        );
}

class Kutu extends StatelessWidget {
  const Kutu(
    this.baslik, {
    super.key,
    required this.children,
    this.vurgu = false,
    this.form = false,
  });
  final String baslik;
  final List<Widget> children;
  final bool vurgu;
  final bool form;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surface,
      border: Border.all(
        color: vurgu
            ? Theme.of(context).colorScheme.primary
            : Theme.of(context).colorScheme.outline,
      ),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Material(
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            baslik,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 18),
          if (form)
            LayoutBuilder(
              builder: (context, o) {
                final alanlar = children.where((w) => w is! SizedBox).toList();
                return Wrap(
                  spacing: 16,
                  runSpacing: 16,
                  children: [
                    for (var i = 0; i < alanlar.length; i++)
                      SizedBox(
                        width:
                            MediaQuery.sizeOf(context).width >= 900 &&
                                i != 0 &&
                                i != alanlar.length - 1
                            ? (o.maxWidth - 16) / 2
                            : o.maxWidth,
                        child: alanlar[i],
                      ),
                  ],
                );
              },
            )
          else
            ...children,
        ],
      ),
    ),
  );
}

class Olcu extends StatelessWidget {
  const Olcu(this.ad, this.deger, this.alt, {super.key});
  final String ad, deger, alt;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 210,
    child: Kutu(
      ad,
      children: [
        Text(
          deger,
          style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
        ),
        Text(alt, style: const TextStyle(fontSize: 13)),
      ],
    ),
  );
}

class PlansizForm extends StatefulWidget {
  const PlansizForm({
    super.key,
    required this.durum,
    this.birim,
    required this.kisiler,
    required this.proje,
    required this.projeSec,
  });
  final UygulamaDurumu durum;
  final String? birim;
  final List<Json> kisiler;
  final String? proje;
  final void Function(String?) projeSec;
  @override
  State<PlansizForm> createState() => _PlansizFormState();
}

class _PlansizFormState extends State<PlansizForm> {
  final ad = TextEditingController(),
      sure = TextEditingController(text: '30'),
      sira = TextEditingController(text: '1');
  String? kisi, etap, kategori;
  bool projeDisi = false, onay = false, beklet = false;
  String tur = 'SURELI';
  @override
  void dispose() {
    ad.dispose();
    sure.dispose();
    sira.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.durum;
    kisi ??= widget.kisiler.firstOrNull?['kimlik'];
    final etaplar = d.satirlar('ETAPLAR', hedef: widget.proje);
    if (!etaplar.any((x) => x['kimlik'] == etap)) {
      etap = etaplar.firstOrNull?['kimlik'];
    }
    final kategoriler = d.kodlar
        .where((x) => x['liste'] == 'PD' && x['aktif'] == true)
        .toList();
    kategori ??= kategoriler.firstOrNull?['kod'];
    return Kutu(
      'Plansız iş tanımla',
      form: true,
      children: [
        TextField(
          key: const Key('plansiz-ad'),
          controller: ad,
          decoration: const InputDecoration(labelText: 'İş tanımı'),
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Proje dışı'),
          value: projeDisi,
          onChanged: (v) => setState(() => projeDisi = v),
        ),
        if (!projeDisi) ...[
          DropdownButtonFormField<String>(
            key: ValueKey(widget.proje),
            initialValue: widget.proje,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Proje'),
            items: [
              for (final p
                  in d.satirlar('PROJELER').where((x) => x['aktif'] == true))
                DropdownMenuItem(
                  value: p['kimlik'] as String,
                  child: Text('${p['kod']} · ${p['ad']}'),
                ),
            ],
            onChanged: widget.projeSec,
          ),
          DropdownButtonFormField<String>(
            key: ValueKey('etap-$etap'),
            initialValue: etap,
            decoration: const InputDecoration(labelText: 'Etap'),
            items: [
              for (final p in etaplar)
                DropdownMenuItem(
                  value: p['kimlik'] as String,
                  child: Text(p['ad'] ?? p['kimlik']),
                ),
            ],
            onChanged: (v) => etap = v,
          ),
        ] else
          DropdownButtonFormField<String>(
            initialValue: kategori,
            decoration: const InputDecoration(labelText: 'Kategori'),
            items: [
              for (final k in kategoriler)
                DropdownMenuItem(
                  value: k['kod'] as String,
                  child: Text(k['ad']),
                ),
            ],
            onChanged: (v) => kategori = v,
          ),
        DropdownButtonFormField<String>(
          initialValue: kisi,
          decoration: const InputDecoration(labelText: 'Kişi'),
          items: [
            for (final p in widget.kisiler)
              DropdownMenuItem(
                value: p['kimlik'] as String,
                child: Text(p['ad']),
              ),
          ],
          onChanged: (v) => kisi = v,
        ),
        DropdownButtonFormField<String>(
          initialValue: tur,
          decoration: const InputDecoration(labelText: 'İş türü'),
          items: const [
            DropdownMenuItem(value: 'SURELI', child: Text('Süreli')),
            DropdownMenuItem(value: 'ANLIK', child: Text('Anlık')),
          ],
          onChanged: (v) => setState(() => tur = v!),
        ),
        TextField(
          controller: sure,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Tahmini süre · dakika'),
        ),
        TextField(
          controller: sira,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Sıra'),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Onay gerekli'),
          value: onay,
          onChanged: (v) => setState(() => onay = v!),
        ),
        if (onay)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Onayı bekle'),
            value: beklet,
            onChanged: (v) => setState(() => beklet = v!),
          ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: d.yonetimAcik
              ? () async {
                  if (ad.text.trim().isEmpty ||
                      kisi == null ||
                      int.tryParse(sure.text) == null ||
                      (int.tryParse(sira.text) ?? 0) < 1 ||
                      (projeDisi ? kategori == null : widget.proje == null)) {
                    return;
                  }
                  await isle(context, () async {
                    await d.yonetim(
                      'IS.PLANSIZ_TANIMLADIM',
                      girdiler: {
                        'nereye': projeDisi ? 'PROJE_DISI' : 'PROJE',
                        'is_tanimi': ad.text.trim(),
                        'tur': tur,
                        'onay_gerekli': onay,
                        'onay_beklet': beklet,
                        'kisi': kisi,
                        'birim': widget.birim ?? d.birim,
                        'sira': int.parse(sira.text),
                        'tahmini_sure_dk': int.parse(sure.text),
                        if (projeDisi) 'kategori': kategori,
                        if (!projeDisi) 'proje': widget.proje,
                        if (!projeDisi && etap != null) 'etap': etap,
                      },
                    );
                  });
                }
              : null,
          child: const Text('Tanımla ve sıraya koy'),
        ),
      ],
    );
  }
}
