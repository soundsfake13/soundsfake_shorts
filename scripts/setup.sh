#!/usr/bin/env bash
# One-time setup per session: Python deps, Kokoro voice model, Inter fonts.
set -euo pipefail
KD="${KOKORO_DIR:-$HOME/.cache/kokoro}"
mkdir -p "$KD"

pip install --break-system-packages -q kokoro-onnx soundfile numpy pillow 2>&1 | grep -v -i "warning" || true
command -v ffmpeg >/dev/null || { echo "ffmpeg missing — install it (apt-get install -y ffmpeg)"; exit 1; }

BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s "$KD/kokoro.onnx" ] || curl -sSL -o "$KD/kokoro.onnx" "$BASE/kokoro-v1.0.onnx"
[ -s "$KD/voices.bin" ]  || curl -sSL -o "$KD/voices.bin"  "$BASE/voices-v1.0.bin"

# Fonts: use system Inter Display if present, otherwise download Inter from GitHub.
if [ ! -f /usr/share/fonts/opentype/inter/InterDisplay-Black.otf ]; then
  FD="$HOME/.cache/inter"
  if [ ! -f "$FD/InterDisplay-Black.otf" ]; then
    mkdir -p "$FD"; tmp=$(mktemp -d)
    curl -sSL -o "$tmp/inter.zip" https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip
    unzip -q -o "$tmp/inter.zip" -d "$tmp/x"
    find "$tmp/x" -name "InterDisplay-Black.otf" -o -name "InterDisplay-Bold.otf" | xargs -I{} cp {} "$FD/"
  fi
  echo "export FONT_DIR=$FD"
fi
echo "setup ok: model in $KD"
