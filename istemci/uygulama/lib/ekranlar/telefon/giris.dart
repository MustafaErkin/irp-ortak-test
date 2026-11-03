import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../durum/uygulama_durumu.dart';
import 'ortak.dart';
import '../../sahte/fikstur_bulutu.dart';

class Giris extends StatefulWidget {
  const Giris({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  State<Giris> createState() => _GirisState();
}

class _GirisState extends State<Giris> {
  final _kod = TextEditingController(), _ilk = TextEditingController();
  final _pin = TextEditingController(), _tekrar = TextEditingController();
  String _rakamlar = '';
  Timer? _timer;
  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in [_kod, _ilk, _pin, _tekrar]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _rakam(String r) async {
    setState(
      () => _rakamlar = r == 'sil'
          ? (_rakamlar.isEmpty
                ? ''
                : _rakamlar.substring(0, _rakamlar.length - 1))
          : (_rakamlar + r),
    );
    if (_rakamlar.length == 6) {
      await isle(context, () async {
        await widget.durum.kilitAc(_rakamlar);
      });
      if (mounted) setState(() => _rakamlar = '');
    }
  }

  Widget _alan(
    String yazi,
    TextEditingController c, {
    bool gizli = false,
    bool sayi = false,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextField(
      controller: c,
      obscureText: gizli,
      autocorrect: false,
      enableSuggestions: !gizli,
      keyboardType: sayi ? TextInputType.number : TextInputType.text,
      inputFormatters: sayi
          ? [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(6),
            ]
          : null,
      decoration: InputDecoration(labelText: yazi),
    ),
  );
  @override
  Widget build(BuildContext context) {
    final d = widget.durum;
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 36),
              Text(
                d.kayit == null ? 'Sibernetik IRP' : d.ad,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 32),
              if (d.mesaj != null) Bant(d.mesaj!),
              if (d.kayit == null) ...[
                const Text(
                  'Bu telefonu kaydet',
                  style: TextStyle(fontSize: 21, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 24),
                _alan('Kişi kodu', _kod),
                _alan('İlk şifre (yetkiliden)', _ilk, gizli: true),
                _alan('Kendi şifren (6 rakam)', _pin, gizli: true, sayi: true),
                _alan('Şifreni tekrar yaz', _tekrar, gizli: true, sayi: true),
                Dugme(
                  'KAYDET',
                  bas: d.mesgul
                      ? null
                      : () => isle(
                          context,
                          () => d.kaydol(
                            _kod.text,
                            _ilk.text,
                            _pin.text,
                            _tekrar.text,
                          ),
                        ),
                ),
                const SizedBox(height: 20),
                if (d.bulut is FiksturBulutu)
                  Text(
                    (d.bulut as FiksturBulutu).gosteriIpucu,
                    textAlign: TextAlign.center,
                  ),
              ] else ...[
                const Text(
                  '6 rakamlı şifreni gir',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                Semantics(
                  label: '${_rakamlar.length} rakam girildi',
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      for (var i = 0; i < 6; i++)
                        Container(
                          width: 14,
                          height: 14,
                          margin: const EdgeInsets.symmetric(horizontal: 7),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: Theme.of(context).colorScheme.onSurface,
                            ),
                            color: i < _rakamlar.length
                                ? Theme.of(context).colorScheme.onSurface
                                : Colors.transparent,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                if (d.kilitSaniye > 0)
                  Text(
                    '${d.kilitSaniye} saniye bekle',
                    textAlign: TextAlign.center,
                  ),
                for (final satir in [
                  ['1', '2', '3'],
                  ['4', '5', '6'],
                  ['7', '8', '9'],
                  ['', '0', 'sil'],
                ])
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                      children: [
                        for (final r in satir)
                          Expanded(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 5,
                              ),
                              child: r.isEmpty
                                  ? const SizedBox()
                                  : Dugme(
                                      r == 'sil' ? 'SİL' : r,
                                      renk: 'sade',
                                      bas:
                                          d.mesgul ||
                                              d.kilitSaniye > 0 ||
                                              _rakamlar.length >= 6
                                          ? null
                                          : () => _rakam(r),
                                    ),
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
              if (d.mesgul)
                const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
