import 'is_gorunumu.dart';

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';

import '../../durum/uygulama_durumu.dart';
import 'ortak.dart';
import 'eylem_penceresi.dart';
import 'not_ekle.dart';
import 'qr_cizim.dart';
import '../kisi_degistir.dart';

class Telefon extends StatelessWidget {
  const Telefon({super.key, required this.durum, required this.cizimler});
  final UygulamaDurumu durum;
  final Map<String, String> cizimler;

  void _not(BuildContext context) =>
      Navigator.of(context)
          .push(MaterialPageRoute<void>(builder: (_) => NotEkle(durum: durum)));
  void _liste(BuildContext context) => altPencere(
    context,
    SizedBox(
      height: MediaQuery.sizeOf(context).height * .65,
      child: Column(
        children: [
          Text(
            'Günün işleri (${durum.liste.length})',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: durum.liste.length,
              separatorBuilder: (_, _) => const Divider(),
              itemBuilder: (_, i) {
                final is_ = durum.isler[durum.liste[i]]!;
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${i + 1} · ${isAdi(is_)}'),
                  subtitle: Text(isBaglami(durum, is_)),
                  trailing: Text(
                    is_['kilitli'] == true
                        ? 'Ön İş Bekliyor'
                        : is_['kimlik'] == durum.hal['acik_is']
                        ? 'Şu An'
                        : '~${is_['tahmini_sure_dk'] ?? '—'} dk',
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Dugme('KAPAT', bas: () => Navigator.pop(context)),
          ),
        ],
      ),
    ),
  );
  void _menu(BuildContext context) => altPencere(
    context,
    Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Dugme(
            'Mesaiden çık',
            renk: 'sade',
            bas: durum.kapiAcik('MESAI.CIKTIM')
                ? () async {
                    if (await isle(context, () async {
                      await durum.olay('MESAI.CIKTIM');
                    })) {
                      if (context.mounted) Navigator.pop(context);
                      // Gösteri kipinde 6 rakamlı şifre yok; kilitlenirse açılamaz.
                      if (durum.gosteriKisileri.isEmpty) durum.kilitle();
                    }
                  }
                : null,
          ),
          const SizedBox(height: 12),
          Dugme(
            'Not ekle',
            renk: 'sade',
            bas: () {
              Navigator.pop(context);
              _not(context);
            },
          ),
          if (durum.gosteriKisileri.isNotEmpty) ...[
            const SizedBox(height: 12),
            TextButton(
              onPressed: durum.mesgul
                  ? null
                  : () {
                      Navigator.pop(context);
                      kisiDegistir(context, durum);
                    },
              child: const Text('Kişi değiştir'),
            ),
          ],
        ],
      ),
    ),
  );
  @override
  Widget build(BuildContext context) {
    if (durum.mesaiDenetimi && durum.mesaiBiliniyor && !durum.mesaiIcinde) {
      return Scaffold(
        body: SafeArea(
          child: Stack(
            children: [
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(28),
                  child: Text(
                    'Mesai Dışındasınız',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 25, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
              Align(
                alignment: Alignment.bottomCenter,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: TextButton(
                    onPressed: () => SystemNavigator.pop(),
                    child: const Text('Çıkış Yap'),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }
    final h = durum.hal, is_ = durum.is_;
    final d = !durum.mesaiIcinde
        ? 'MESAI_DISI'
        : !durum.calismaIcinde
        ? 'SABIT_MOLADA'
        : h['durum'] == 'CALISMIYOR' && is_?['kilitli'] == true
        ? 'ON_IS_BEKLIYOR'
        : h['durum'];
    final red = is_?['durum'] == 'REDDEDILDI';
    final nedenKodu = '${h['neden'] ?? ''}'.replaceFirst('DURUS_NEDENI.', '');
    final nedenler = durum.kodlar.where(
      (k) => k['liste'] == 'DURUS_NEDENI' && k['kod'] == nedenKodu,
    );
    final nedenMetni = nedenler.isEmpty
        ? 'Duruş bildirildi'
        : '${etiket('${nedenler.first['ust']}')} · ${etiket('${nedenler.first['ad']}')}';
    final bos = durum.liste.isEmpty && is_ == null;
    final baslik = switch (d) {
      'MOLADA' => 'MOLADA',
      'ARIZADA' =>
        h['devam_izni'] == true
            ? 'DURUŞ · DEVAM İZNİ VAR'
            : 'DURUŞ · ONAY BEKLENİYOR',
      'ONAY_BEKLIYOR' => 'ONAY BEKLENİYOR',
      'ON_IS_BEKLIYOR' => 'KİLİTLİ',
      'SABIT_MOLADA' => 'SABİT MOLA',
      'MESAI_DISI' =>
        durum.mesaiBiliniyor
            ? 'Mesai Dışındasınız'
            : 'Çalışma Takvimi Bekleniyor',
      _ => 'ŞU ANKİ İŞ',
    };
    void yaz(String kod) => isle(context, () async {
      await durum.olay(kod);
    });
    void pencere(String kod) =>
        altPencere(context, EylemPenceresi(durum: durum, kod: kod));
    Widget dugme(
      String yazi,
      String kod, {
      String renk = 'mavi',
      bool sor = false,
    }) => Dugme(
      yazi,
      renk: renk,
      bas: durum.kapiAcik(kod) ? () => sor ? pencere(kod) : yaz(kod) : null,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(durum.ad),
        actions: [
          Tooltip(
            message: durum.baglanti ? 'Çevrimiçi' : 'Çevrimdışı',
            child: Icon(
              Icons.circle,
              size: 12,
              color: durum.baglanti ? Colors.green : Colors.orange,
            ),
          ),
          TextButton(
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute<void>(
                builder: (_) => QrCizim(harita: cizimler),
              ),
            ),
            child: const Text('QR'),
          ),
          IconButton(
            onPressed: () => _menu(context),
            tooltip: 'Menü',
            icon: const Icon(Icons.more_horiz),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: durum.yenile,
          child: LayoutBuilder(
            builder: (context, olcu) => SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  minHeight: (olcu.maxHeight - 40).clamp(0, double.infinity),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (durum.kaliciHata)
                          const Bant(
                            'İşlem telefonda saklanamadı. Uygulamayı kapatmadan depolama alanını kontrol edin.',
                          ),
                        if (durum.islemHatasi != null) Bant(durum.islemHatasi!),
                        if (red) const Bant('Reddedildi'),
                        Container(
                          padding: const EdgeInsets.all(22),
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.surface,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: Theme.of(context).colorScheme.outline,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                baslik,
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.primary,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 13,
                                  letterSpacing: 1,
                                ),
                              ),
                              const SizedBox(height: 14),
                              Text(
                                !durum.mesaiIcinde
                                    ? (durum.mesaiBiliniyor
                                          ? 'Çalışma saatlerinizin dışındasınız.'
                                          : 'Güncel takvim için bağlantıyı kontrol edip ekranı yenileyin.')
                                    : bos
                                    ? 'Bugün için işin yok'
                                    : '${is_?['islem'] ?? 'İşin hazırlanıyor'}',
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              if (durum.mesaiIcinde && is_ != null) ...[
                                const SizedBox(height: 10),
                                Text(isBaglami(durum, is_)),
                                if (red)
                                  Text(
                                    '${is_['not_'] ?? 'Düzeltme bekleniyor'}',
                                  ),
                                if (d == 'ARIZADA') Text(nedenMetni),
                                if (d == 'MOLADA' && h['neden'] != null)
                                  Text('Not: ${h['neden']}'),
                                if (d == 'ON_IS_BEKLIYOR')
                                  Text(durum.kilitAciklamasi),
                                if (d == 'SABIT_MOLADA')
                                  const Text('Süre işe yazılmaz'),
                                if (is_['parca_kodu'] != null)
                                  TextButton(
                                    onPressed: () => cizimAc(
                                      context,
                                      cizimler,
                                      '${is_['parca_kodu']}',
                                    ),
                                    child: const Text('Çizimi aç'),
                                  ),
                              ],
                            ],
                          ),
                        ),
                        if (durum.mesaiIcinde && !bos) ...[
                          const SizedBox(height: 32),
                          if (is_?['tur'] == 'ANLIK')
                            const Center(
                              child: Text(
                                'Anlık',
                                style: TextStyle(fontSize: 34),
                              ),
                            )
                          else
                            Sayac(durum: durum),
                          const SizedBox(height: 8),
                          Text(
                            red
                                ? 'Yeniden İşleme'
                                : switch (d) {
                                    'CALISIYOR' => 'Çalışıyor',
                                    'MOLADA' => 'Mola',
                                    'ARIZADA' =>
                                      h['devam_izni'] == true
                                          ? 'İşine Devam Edebilirsin'
                                          : 'Ekip Liderinin Onayı Bekleniyor',
                                    'ONAY_BEKLIYOR' => 'İş Onayı Bekleniyor',
                                    'ON_IS_BEKLIYOR' => 'Bekleniyor',
                                    'SABIT_MOLADA' => 'Mola',
                                    'DEVAM_BEKLIYOR' =>
                                      'Devam Etmen Bekleniyor',
                                    _ => 'Başlamadı',
                                  },
                            textAlign: TextAlign.center,
                          ),
                        ],
                        const SizedBox(height: 24),
                        TextButton.icon(
                          onPressed: () => _liste(context),
                          icon: const Icon(Icons.keyboard_arrow_down),
                          iconAlignment: IconAlignment.end,
                          label: Text('Günün işleri (${durum.liste.length})'),
                        ),
                      ],
                    ),
                    Padding(
                      padding: const EdgeInsets.only(top: 24),
                      child: Column(
                        children: [
                          if (!durum.mesaiIcinde)
                            TextButton(
                              onPressed: durum.yenile,
                              child: const Text('Takvimi Yenile'),
                            )
                          else if (d == 'CALISIYOR') ...[
                            dugme(
                              'TAMAMLA',
                              'IS.TAMAMLADIM',
                              renk: 'yesil',
                              sor: true,
                            ),
                            const SizedBox(height: 14),
                            Row(
                              children: [
                                Expanded(
                                  child: dugme(
                                    'MOLA',
                                    'IS.MOLA_VERDIM',
                                    renk: 'sari',
                                    sor: true,
                                  ),
                                ),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: dugme(
                                    'DURUŞ',
                                    'IS.ARIZA_BILDIRDIM',
                                    renk: 'kirmizi',
                                    sor: true,
                                  ),
                                ),
                              ],
                            ),
                          ] else if (d == 'SABIT_MOLADA')
                            const SizedBox.shrink()
                          else if (d == 'DEVAM_BEKLIYOR') ...[
                            dugme(
                              'TAMAMLA',
                              'IS.TAMAMLADIM',
                              renk: 'yesil',
                              sor: true,
                            ),
                            const SizedBox(height: 14),
                            dugme('İŞİNE DEVAM ET', 'IS.DEVAM_ETTIM'),
                          ] else if (d == 'MOLADA' || d == 'ARIZADA' || red)
                            dugme('DEVAM ET', 'IS.DEVAM_ETTIM')
                          else if (d == 'MESAI_DISI')
                            dugme('MESAİYE GİR', 'MESAI.GIRDIM')
                          else if (is_?['tur'] == 'ANLIK') ...[
                            dugme(
                              'TAMAMLA',
                              'IS.TAMAMLADIM',
                              renk: 'yesil',
                              sor: true,
                            ),
                            const SizedBox(height: 14),
                            dugme(
                              'DURUŞ',
                              'IS.ARIZA_BILDIRDIM',
                              renk: 'kirmizi',
                              sor: true,
                            ),
                          ] else if (!bos)
                            dugme('BAŞLA', 'IS.BASLADIM'),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class Sayac extends StatefulWidget {
  const Sayac({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  State<Sayac> createState() => _SayacState();
}

class _SayacState extends State<Sayac> {
  late final Timer _timer;
  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.durum;
    var bas = d.hal['baslangic'];
    for (final k in d.gunluk) {
      if (!d.calisanEsitlemesi &&
          k['durum'] == 'BEKLIYOR' &&
          calisan.contains(k['olay']['eylem_kodu'])) {
        bas = k['olay']['oldugu_an'];
      }
    }
    final sn = bas == null || d.hal['durum'] == 'CALISMIYOR'
        ? 0
        : d.cihaz!
              .simdiDuzeltilmis()
              .farkAl(an(bas))
              .inSeconds
              .clamp(0, 9999999);
    final yazi = [
      sn ~/ 3600,
      sn ~/ 60 % 60,
      sn % 60,
    ].map((x) => '$x'.padLeft(2, '0')).join(':');
    return FittedBox(
      fit: BoxFit.scaleDown,
      child: Text(
        yazi,
        style: const TextStyle(
          fontSize: 48,
          fontFeatures: [FontFeature.tabularFigures()],
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
