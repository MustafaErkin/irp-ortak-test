import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../durum/kanit.dart';
import '../../durum/uygulama_durumu.dart';
import 'ortak.dart';

class NotEkle extends StatefulWidget {
  const NotEkle({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  State<NotEkle> createState() => _NotEkleState();
}

class _NotEkleState extends State<NotEkle> {
  final _metin = TextEditingController(), _etiketler = TextEditingController();
  late final TextEditingController _hedef;
  String _tur = 'PARCA';
  HazirFoto? _foto;
  bool _yaziliyor = false;
  @override
  void initState() {
    super.initState();
    _hedef = TextEditingController(
      text: '${widget.durum.is_?['parca_kodu'] ?? ''}',
    );
  }

  @override
  void dispose() {
    _metin.dispose();
    _etiketler.dispose();
    _hedef.dispose();
    super.dispose();
  }

  Future<bool> _fotoSec() => isle(context, () async {
    final secim = await FilePicker.pickFiles(type: FileType.image);
    if (secim.isEmpty || !mounted) return;
    final f = secim.single;
    final hazir = HazirFoto.hazirla(await f.readAsBytes(), f.name);
    if (mounted) setState(() => _foto = hazir);
  });
  Future<void> _kaydet() async {
    setState(() => _yaziliyor = true);
    final tamam = await isle(context, () async {
      if (_metin.text.trim().isEmpty) throw ArgumentError('Notunu yaz');
      if (_hedef.text.trim().isEmpty) {
        throw ArgumentError('Notun bağlı olduğu kaydı seç');
      }
      await widget.durum.olay(
        'NOT.YAZDIM',
        girdiler: {
          'metin': _metin.text.trim(),
          'etiketler': _etiketler.text
              .split(',')
              .map((e) => e.trim())
              .where((e) => e.isNotEmpty)
              .toSet()
              .toList(),
        },
        hedefler: [
          {'tur': _tur, 'kimlik': _hedef.text.trim(), 'surum': null},
        ],
        fotograflar: _foto == null ? [] : [_foto!],
      );
    });
    if (!mounted) return;
    if (tamam) {
      Navigator.pop(context);
    } else {
      setState(() => _yaziliyor = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Not ekle')),
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _tur,
              decoration: const InputDecoration(labelText: 'Neye bağlı?'),
              items: const [
                DropdownMenuItem(value: 'PARCA', child: Text('Parça')),
                DropdownMenuItem(value: 'PROJE', child: Text('Proje')),
                DropdownMenuItem(value: 'GOREV', child: Text('Görev')),
                DropdownMenuItem(value: 'NESNE', child: Text('Nesne')),
              ],
              onChanged: _yaziliyor
                  ? null
                  : (v) => setState(() {
                      _tur = v!;
                      _hedef.text = _tur == 'PARCA'
                          ? '${widget.durum.is_?['parca_kodu'] ?? ''}'
                          : _tur == 'PROJE'
                          ? '${widget.durum.is_?['proje'] ?? ''}'
                          : '';
                    }),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _hedef,
              decoration: const InputDecoration(labelText: 'Bağlı kayıt kodu'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _metin,
              minLines: 4,
              maxLines: 8,
              decoration: const InputDecoration(labelText: 'Notun'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _etiketler,
              decoration: const InputDecoration(
                labelText: 'Etiketler (virgülle, isteğe bağlı)',
              ),
            ),
            const SizedBox(height: 16),
            if (_foto != null) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(
                  _foto!.bytes,
                  height: 180,
                  fit: BoxFit.cover,
                ),
              ),
              TextButton(
                onPressed: _yaziliyor
                    ? null
                    : () => setState(() => _foto = null),
                child: const Text('Fotoğrafı kaldır'),
              ),
            ],
            Dugme(
              'Fotoğraf ekle',
              renk: 'sade',
              bas: _yaziliyor ? null : _fotoSec,
            ),
            const SizedBox(height: 24),
            Dugme('KAYDET', bas: _yaziliyor ? null : _kaydet),
          ],
        ),
      ),
    ),
  );
}
