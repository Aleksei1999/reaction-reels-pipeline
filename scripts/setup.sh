#!/bin/bash
# Одноразовая подготовка машины под пайплайн.
set -e
cd "$(dirname "$0")/.."

echo "==> ffmpeg с libass"
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -qE "^ ..? ass "; then
  echo "    обычная формула ffmpeg идёт без libass — ставим ffmpeg-full"
  brew install ffmpeg-full
  echo '    добавь в ~/.zshrc:  export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"'
fi

echo "==> python venv + whisper + yt-dlp"
[ -d .venv ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python openai-whisper yt-dlp

echo "==> grunge-переход"
[ -f assets/grunge_trans.mov ] || bash scripts/make_grunge.sh

echo "==> шрифт"
ls ~/Library/Fonts/ | grep -qi gilroy && echo "    Gilroy найден" || echo "    ВНИМАНИЕ: Gilroy ExtraBold не установлен — положи в ~/Library/Fonts/"

echo "DONE"
