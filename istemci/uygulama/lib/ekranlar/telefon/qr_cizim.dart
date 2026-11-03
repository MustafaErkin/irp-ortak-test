import 'dart:async';

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'ortak.dart';

Future<void> cizimAc(
  BuildContext context,
  Map<String, String> harita,
  String kod,
) async {
  final yol = harita[kod.trim()];
  if (yol == null) {
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Bu QR tanınmadı')));
    return;
  }
  await Navigator.push(
    context,
    MaterialPageRoute<void>(
      builder: (_) => Scaffold(
        appBar: AppBar(title: const Text('Çizim')),
        body: Column(
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('İki parmakla büyütüp kaydırabilirsin'),
            ),
            Expanded(
              child: InteractiveViewer(
                minScale: .5,
                maxScale: 8,
                child: Center(
                  child: Image.asset(
                    yol,
                    semanticLabel: 'Sentetik örnek teknik çizim',
                  ),
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('GÖSTERİ · SENTETİK ÇİZİM'),
            ),
          ],
        ),
      ),
    ),
  );
}

class QrCizim extends StatefulWidget {
  const QrCizim({super.key, required this.harita});
  final Map<String, String> harita;
  @override
  State<QrCizim> createState() => _QrCizimState();
}

class _QrCizimState extends State<QrCizim> {
  final _kod = TextEditingController();
  MobileScannerController? _kamera;
  bool _aciliyor = false;
  void _kameraAc() {
    // Tarayıcıda CDN kütüphanesi indirilmez. Yerleşik API yoksa elle kod girilir.
    MobileScannerPlatform.instance.setWebBarcodeReader(
      WebBarcodeReader.barcodeDetector,
    );
    setState(
      () => _kamera = MobileScannerController(
        formats: const [BarcodeFormat.qrCode],
      ),
    );
  }

  Future<void> _ac(String kod) async {
    if (_aciliyor) return;
    _aciliyor = true;
    await _kamera?.stop();
    if (!mounted) return;
    await cizimAc(context, widget.harita, kod);
    _aciliyor = false;
    if (mounted && _kamera != null) await _kamera!.start();
  }

  @override
  void dispose() {
    _kod.dispose();
    unawaited(_kamera?.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('QR ile çizim')),
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Parçanın üzerindeki QR kodunu okut.'),
            const SizedBox(height: 20),
            Container(
              height: 280,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Theme.of(context).colorScheme.outline,
                ),
              ),
              child: _kamera == null
                  ? const Icon(Icons.qr_code_scanner, size: 112)
                  : ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: MobileScanner(
                        controller: _kamera,
                        onDetect: (capture) {
                          for (final b in capture.barcodes) {
                            if (b.rawValue != null) {
                              unawaited(_ac(b.rawValue!));
                              break;
                            }
                          }
                        },
                        errorBuilder: (_, _) => const Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(
                            child: Text(
                              'Kamera açılamadı. Kamera iznini kontrol et veya kodu aşağıya yaz.',
                            ),
                          ),
                        ),
                      ),
                    ),
            ),
            const SizedBox(height: 20),
            if (_kamera == null) Dugme('KAMERAYI AÇ', bas: _kameraAc),
            const SizedBox(height: 24),
            TextField(
              controller: _kod,
              decoration: const InputDecoration(
                labelText: 'QR metni veya parça kodu',
              ),
            ),
            const SizedBox(height: 16),
            Dugme('ÇİZİMİ AÇ', bas: () => _ac(_kod.text)),
          ],
        ),
      ),
    ),
  );
}
