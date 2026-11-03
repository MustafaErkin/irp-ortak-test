#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
if [[ -f "$HOME/irp_gizli/supabase.env" ]]; then
  set -a
  . "$HOME/irp_gizli/supabase.env"
  set +a
fi
exec "$HOME/.irp_venv/bin/python" -I -B sunucu.py
