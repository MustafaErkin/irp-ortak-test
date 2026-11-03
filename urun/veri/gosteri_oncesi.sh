#!/bin/bash
# Karar 144: gösteri başlangıcı boş Senaryo 1 firmasıdır; eski geçmiş yüklenmez.
set -euo pipefail
cd "$(dirname "$0")/../.."
BUGUN="${1:?Tarih ver, ör. 2026-11-09}"
set -a; . ~/irp_gizli/supabase.env; set +a
~/.irp_venv/bin/python -I -B urun/veri/senaryo1_hazirla.py --temiz-baslat --bugun "$BUGUN"
bash istemci/mac_derle.sh ayar
bash istemci/mac_derle.sh web --calistir
bash istemci/mac_derle.sh apk
if "$HOME/Library/Android/sdk/platform-tools/adb" devices | sed 1d | grep -q 'device$'; then
  bash istemci/mac_derle.sh kur
else
  echo 'Web ve üç rollü APK hazır; USB telefon bağlı olmadığı için APK kurulmadı.'
fi
