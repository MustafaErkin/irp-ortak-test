import 'package:flutter/material.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/uygulama_durumu.dart';
import 'ortak.dart';

class EylemPenceresi extends StatefulWidget {
  const EylemPenceresi({super.key, required this.durum, required this.kod});
  final UygulamaDurumu durum;
  final String kod;
  @override
  State<EylemPenceresi> createState() => _EylemPenceresiState();
}

class _EylemPenceresiState extends State<EylemPenceresi> {
  final _not = TextEditingController(), _bitis = TextEditingController();
  String? _grup, _neden;
  bool _yaziliyor = false;
  String? _notHatasi, _nedenHatasi;
  @override
  void dispose() {
    _not.dispose();
    _bitis.dispose();
    super.dispose();
  }

  bool get mola => widget.kod == 'IS.MOLA_VERDIM';
  bool get durus => widget.kod == 'IS.ARIZA_BILDIRDIM';
  bool get cnc =>
      widget.durum.is_?['tur'] == 'ANLIK' &&
      widget.durum.is_?['tezgah_rolu'] == 'BITIR';
  Future<void> _gonder() async {
    if (_yaziliyor) return;
    setState(() {
      _notHatasi = null;
      _nedenHatasi = null;
    });
    if (durus && _not.text.trim().isEmpty) {
      if (_neden == null) {
        setState(() => _nedenHatasi = 'Bir neden seçin veya açıklama yazın.');
        return;
      }
      if (_neden!.endsWith('_DIGER')) {
        setState(() => _notHatasi = 'Diğer seçeneği için açıklama yazın.');
        return;
      }
    }
    setState(() => _yaziliyor = true);
    final tamam = await isle(context, () async {
      final girdiler = <String, dynamic>{};
      if (mola || durus) {
        if (_not.text.trim().isNotEmpty) girdiler['not'] = _not.text.trim();
        if (durus && _neden != null) girdiler['neden'] = 'DURUS_NEDENI.$_neden';
        if (durus &&
            ((_neden == null && _not.text.trim().isEmpty) ||
                (_neden?.endsWith('_DIGER') == true &&
                    _not.text.trim().isEmpty))) {
          throw ArgumentError(
            'Bir neden seç ya da ne olduğunu yaz. Diğer seçeneğinde not gerekir',
          );
        }
      } else if (_bitis.text.trim().isNotEmpty) {
        final t = DateTime.tryParse(_bitis.text.trim());
        if (t == null ||
            !RegExp(r'(Z|[+-]\d{2}:\d{2})$').hasMatch(_bitis.text.trim())) {
          throw ArgumentError(
            'Bitiş anını saat dilimiyle yaz: 2026-10-22T14:58:00+03:00',
          );
        }
        girdiler['makine_bitis_ani'] = _bitis.text.trim();
      }
      await widget.durum.olay(widget.kod, girdiler: girdiler);
    });
    if (!mounted) return;
    if (tamam) {
      Navigator.pop(context);
    } else {
      setState(() => _yaziliyor = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final kodlar = widget.durum.kodlar;
    final nedenler = kodlar.where((k) => k['liste'] == 'DURUS_NEDENI').toList();
    final molaNotlari = kodlar
        .where((k) => k['liste'] == 'MOLA_NOTU')
        .map((k) => '${k['ad']}')
        .toList();
    final notlar = molaNotlari.isEmpty
        ? ['Namaz', 'Telefon', 'Sigara', 'WC', 'İhtiyaç']
        : molaNotlari;
    Widget secimler(List<Json> liste, bool grup) => Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final k in liste)
          ChoiceChip(
            label: Text(etiket('${k['ad']}')),
            selected: (grup ? _grup : _neden) == k['kod'],
            onSelected: _yaziliyor
                ? null
                : (sec) => setState(() {
                    if (grup) {
                      _grup = sec ? k['kod'] as String : null;
                      _neden = null;
                    } else {
                      _neden = sec ? k['kod'] as String : null;
                    }
                  }),
          ),
      ],
    );
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            mola
                ? 'Molaya çıkıyorsun'
                : durus
                ? 'Duruş: ne oldu?'
                : 'Onaylıyor musun?',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 20),
          if (mola) ...[
            const Text('Not (isteğe bağlı)'),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final n in notlar)
                  ChoiceChip(
                    label: Text(n),
                    selected: _not.text == n,
                    onSelected: _yaziliyor
                        ? null
                        : (s) => setState(() => _not.text = s ? n : ''),
                  ),
              ],
            ),
          ],
          if (durus) ...[
            secimler(nedenler.where((k) => k['ust'] == null).toList(), true),
            const SizedBox(height: 16),
            if (_grup != null) ...[
              Text(
                '${etiket(_grup!)} Sorunu Ayrıntısı',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 12),
              secimler(
                nedenler.where((k) => k['ust'] == _grup).toList(),
                false,
              ),
            ],
            if (_nedenHatasi != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  _nedenHatasi!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            TextButton(
              onPressed: _yaziliyor
                  ? null
                  : () => setState(() {
                      _neden = null;
                      _grup = null;
                    }),
              child: const Text('Yalnızca not yaz'),
            ),
          ],
          if (mola || durus) ...[
            const SizedBox(height: 16),
            TextField(
              controller: _not,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: 'Not yaz…',
                errorText: _notHatasi,
              ),
            ),
          ] else ...[
            Text('${widget.durum.is_?['islem'] ?? ''}'),
            if (widget.durum.is_?['onay_gerekli'] == true)
              const Text('Onay gerekli: lider onaylayınca biter'),
            if (cnc) ...[
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _yaziliyor
                    ? null
                    : () async {
                        final now = DateTime.now();
                        final day = await showDatePicker(
                          context: context,
                          initialDate: now,
                          firstDate: DateTime(2000),
                          lastDate: now,
                        );
                        if (day == null || !context.mounted) return;
                        final time = await showTimePicker(
                          context: context,
                          initialTime: TimeOfDay.fromDateTime(now),
                          builder: (context, child) => MediaQuery(
                            data: MediaQuery.of(context)
                                .copyWith(alwaysUse24HourFormat: true),
                            child: child!,
                          ),
                        );
                        if (time == null || !mounted) return;
                        setState(
                          () => _bitis.text = DateTime(
                            day.year,
                            day.month,
                            day.day,
                            time.hour,
                            time.minute,
                          ).toUtc().toIso8601String(),
                        );
                      },
                icon: const Icon(Icons.schedule),
                label: Text(
                  _bitis.text.isEmpty
                      ? 'Makine Bitişini Seç (İsteğe Bağlı)'
                      : 'Makine Bitişi: ${DateTime.parse(_bitis.text).toLocal().day}.${DateTime.parse(_bitis.text).toLocal().month} '
                            '${DateTime.parse(_bitis.text).toLocal().hour.toString().padLeft(2, '0')}:${DateTime.parse(_bitis.text).toLocal().minute.toString().padLeft(2, '0')}',
                ),
              ),
            ],
          ],
          const SizedBox(height: 24),
          ListenableBuilder(
            listenable: widget.durum,
            builder: (_, _) => Dugme(
              _yaziliyor
                  ? 'İşlem Sürüyor…'
                  : mola || durus
                  ? 'ONAYLA'
                  : 'TAMAMLA',
              renk: mola || durus ? 'mavi' : 'yesil',
              bas: !_yaziliyor && widget.durum.kapiAcik(widget.kod)
                  ? _gonder
                  : null,
            ),
          ),
          const SizedBox(height: 12),
          Dugme(
            'VAZGEÇ',
            renk: 'sade',
            bas: _yaziliyor ? null : () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }
}
