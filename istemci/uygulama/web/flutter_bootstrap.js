{{flutter_js}}
{{flutter_build_config}}

// Çizim motoru ve yazılar bu dağıtımdan gelir; dış CDN açılmaz.
_flutter.loader.load({config: {
  canvasKitBaseUrl: 'canvaskit/',
  canvasKitVariant: 'full',
  fontFallbackBaseUrl: 'assets/fontlar/'
}});

// İlk çevrimiçi yüklemeden sonraki açılışlar için uygulama kabuğu.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('irp_offline.js').catch(() => {
    console.info('Çevrimdışı uygulama kabuğu saklanamadı.');
  });
}
