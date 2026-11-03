import 'package:desktop_drop/desktop_drop.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:irp_cekirdek/irp_cekirdek.dart';

import '../../bulut/uygulama_bulutu.dart';
import '../../durum/kanit.dart';
import '../../durum/uygulama_durumu.dart';
import '../telefon/ortak.dart';
import 'web.dart';

class Islerim extends StatefulWidget {
  const Islerim({super.key, required this.durum});
  final UygulamaDurumu durum;
  @override
  State<Islerim> createState() => _IslerimState();
}

class _IslerimState extends State<Islerim> {
  final secili = <String>{};
  Json? teslim;
  @override
  Widget build(BuildContext context) {
    final d = widget.durum;
    final gs = d
        .satirlar('GOREV')
        .where((g) => !['BITTI', 'IPTAL'].contains(g['durum']))
        .toList();
    final yeni = gs.where((g) => g['kabul_ani'] == null).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        IkiSutun(
          sol: Kutu(
            'İşlerim',
            children: [
              if (gs.isEmpty) const Text('Açık görevin yok.'),
              if (yeni.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: FilledButton(
                    key: const Key('toplu-kabul'),
                    onPressed: d.mesgul
                        ? null
                        : () => isle(context, () async {
                            final ids = secili.isEmpty
                                ? yeni.map((g) => g['kimlik']).toSet()
                                : secili;
                            await d.olay(
                              'GOREV.KABUL_ETTIM',
                              hedefler: [
                                for (final g in yeni.where(
                                  (g) => ids.contains(g['kimlik']),
                                ))
                                  {
                                    'tur': 'GOREV',
                                    'kimlik': g['kimlik'],
                                    'surum': null,
                                  },
                              ],
                            );
                            setState(() => secili.clear());
                          }),
                    child: Text(
                      '${secili.isEmpty ? yeni.length : secili.length} görevi kabul et',
                    ),
                  ),
                ),
              for (final g in gs)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: g['kabul_ani'] == null
                        ? Checkbox(
                            value: secili.contains(g['kimlik']),
                            onChanged: (v) => setState(() {
                              if (v == true) {
                                secili.add(g['kimlik']);
                              } else {
                                secili.remove(g['kimlik']);
                              }
                            }),
                          )
                        : const Icon(Icons.task_alt),
                    title: Text(baslik(g)),
                    subtitle: Text(
                      '${g['teslim_tarihi'] ?? '—'} · ${g['zaman_degeri'] ?? 0} sa\n${durumAdi(g['durum'])}${g['dosya_gerekli'] == true ? ' · Dosya gerekli' : ''}',
                    ),
                    isThreeLine: true,
                    trailing:
                        g['kabul_ani'] != null && g['durum'] != 'ONAY_BEKLIYOR'
                        ? TextButton(
                            key: Key('teslim-${g['kimlik']}'),
                            onPressed: () => setState(() => teslim = g),
                            child: const Text('Tamamla'),
                          )
                        : null,
                  ),
                ),
            ],
          ),
          sag: teslim == null
              ? const Kutu(
                  'Teslim',
                  children: [
                    Icon(Icons.upload_file, size: 48),
                    SizedBox(height: 12),
                    Text(
                      'Teslim etmek için bir görevin Tamamla düğmesini seç.',
                    ),
                  ],
                )
              : TeslimForm(
                  key: ValueKey(teslim!['kimlik']),
                  durum: d,
                  gorev: teslim!,
                  tamam: () => setState(() => teslim = null),
                ),
        ),
        const SizedBox(height: 24),
        Kutu(
          'Mesai sonu',
          children: [
            if (d.satirlar('GUN_ISLERI').isEmpty)
              const Text('Bekleyen gün sonu işi yok.'),
            for (final g
                in d
                    .satirlar('GUN_ISLERI')
                    .where((g) => g['tur'] == 'MESAI_SONU'))
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(g['gun']),
                trailing: TextButton(
                  key: Key('gun-gonder-${g['gun']}'),
                  onPressed: d.mesgul ? null : () => _gunGonder(g['gun']),
                  child: const Text('Günü gönder'),
                ),
              ),
          ],
        ),
      ],
    );
  }

  Future<void> _gunGonder(String gun) async {
    final c = TextEditingController();
    await guvenliDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Mesai sonu · $gun'),
        content: SizedBox(
          width: 400,
          child: TextField(
            controller: c,
            decoration: const InputDecoration(
              labelText: 'Açıklama / tanımsız süre',
            ),
            maxLines: 3,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () async {
              final ok = await isle(context, () async {
                await widget.durum.olay(
                  'GUN_SONU.GONDERDIM',
                  girdiler: {
                    'gun': gun,
                    'aciklama': c.text.trim(),
                    'tanimsiz_aciklama': c.text.trim(),
                  },
                );
              });
              if (ok && ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Gönder'),
          ),
        ],
      ),
    );
    c.dispose();
  }
}

class TeslimForm extends StatefulWidget {
  const TeslimForm({
    super.key,
    required this.durum,
    required this.gorev,
    required this.tamam,
  });
  final UygulamaDurumu durum;
  final Json gorev;
  final VoidCallback tamam;
  @override
  State<TeslimForm> createState() => _TeslimFormState();
}

class _TeslimFormState extends State<TeslimForm> {
  final dosyalar = <HazirFoto>[];
  final aciklama = TextEditingController();
  String? neden, hata;
  bool ustunde = false, hazirlaniyor = false;
  @override
  void dispose() {
    aciklama.dispose();
    super.dispose();
  }

  Future<void> dosyaSec() async {
    await isle(context, () async {
      final xs = await FilePicker.pickFiles();
      for (final f in xs) {
        final x = HazirDosya.dosya(await f.readAsBytes(), f.name);
        if (mounted) setState(() => dosyalar.add(x));
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.durum, g = widget.gorev;
    final son = g['son_teslim_ani'] ?? sonTeslimAni(g)?.isoformat();
    final gec =
        son != null &&
        d.cihaz!.simdiDuzeltilmis().farkAl(an(son)).inSeconds > 0;
    return Kutu(
      'Teslim · ${baslik(g)}',
      children: [
        DropTarget(
          onDragEntered: (_) => setState(() => ustunde = true),
          onDragExited: (_) => setState(() => ustunde = false),
          onDragDone: (detay) async {
            setState(() => hazirlaniyor = true);
            await isle(context, () async {
              for (final f in detay.files) {
                if (f is DropItemDirectory) continue;
                final x = HazirDosya.dosya(await f.readAsBytes(), f.name);
                if (mounted) setState(() => dosyalar.add(x));
              }
            });
            if (mounted) setState(() => hazirlaniyor = false);
          },
          child: Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: ustunde
                  ? Theme.of(context).colorScheme.primaryContainer
                  : null,
              border: Border.all(color: Theme.of(context).colorScheme.outline),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                const Icon(Icons.file_upload_outlined, size: 32),
                const SizedBox(height: 8),
                const Text('Dosyaları buraya sürükleyin'),
                TextButton(
                  onPressed: hazirlaniyor ? null : dosyaSec,
                  child: const Text('Dosya seç'),
                ),
              ],
            ),
          ),
        ),
        for (final f in dosyalar)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(f.ad),
            subtitle: Text('${f.bytes.length} bayt'),
            trailing: IconButton(
              tooltip: 'Dosyayı kaldır',
              onPressed: () => setState(() => dosyalar.remove(f)),
              icon: const Icon(Icons.close),
            ),
          ),
        if (g['dosya_gerekli'] == true)
          const Padding(
            padding: EdgeInsets.only(top: 12),
            child: Text('Dosya gerekli'),
          ),
        if (gec) ...[
          const SizedBox(height: 16),
          const Text('Teslim tarihi geçti. Gecikme nedenini belirt.'),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            key: const Key('gecikme-nedeni'),
            initialValue: neden,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Gecikme nedeni'),
            items: [
              for (final k in d.kodlar.where(
                (k) =>
                    k['liste'] == 'DURUS_NEDENI' &&
                    k['aktif'] == true &&
                    k['ust'] != null,
              ))
                DropdownMenuItem(
                  value: 'DURUS_NEDENI.${k['kod']}',
                  child: Text(
                    '${etiket('${k['ust']}')} · ${etiket('${k['ad']}')}',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (v) => setState(() => neden = v),
          ),
        ],
        const SizedBox(height: 16),
        TextField(
          key: const Key('teslim-aciklama'),
          controller: aciklama,
          decoration: InputDecoration(
            labelText: gec ? 'Gecikme açıklaması' : 'Not (isteğe bağlı)',
          ),
          maxLines: 3,
        ),
        if (hata != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              hata!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        const SizedBox(height: 18),
        FilledButton(
          key: const Key('teslim-gonder'),
          onPressed: d.mesgul || hazirlaniyor
              ? null
              : () async {
                  if (g['dosya_gerekli'] == true && dosyalar.isEmpty) {
                    setState(() => hata = 'Teslim için dosya ekle');
                    return;
                  }
                  if (gec && (neden == null || aciklama.text.trim().isEmpty)) {
                    setState(
                      () => hata = 'Gecikme nedeni ve açıklaması gerekli',
                    );
                    return;
                  }
                  final ok = await isle(context, () async {
                    await d.olay(
                      'GOREV.TAMAMLADIM',
                      hedefler: [
                        {'tur': 'GOREV', 'kimlik': g['kimlik'], 'surum': null},
                      ],
                      girdiler: {
                        if (gec) 'gecikme_nedeni': neden,
                        if (gec) 'gecikme_aciklamasi': aciklama.text.trim(),
                        if (!gec && aciklama.text.trim().isNotEmpty)
                          'not': aciklama.text.trim(),
                      },
                      fotograflar: dosyalar,
                    );
                  });
                  if (ok) widget.tamam();
                },
          child: const Text('Teslimi tamamla'),
        ),
      ],
    );
  }
}
