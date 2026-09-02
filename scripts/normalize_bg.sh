#!/bin/bash
# Приводит src/bg_orig.mp4 к вертикальному 1080x1920 → src/bg.mp4
#   1) cropdetect срезает вшитые чёрные поля (частая беда у сохранённых рилсов)
#   2) вертикальный контент  → scale+crop (как было)
#      горизонтальный/квадрат → вписывается целиком на размытый фон (иначе кроп режет пол-кадра)
#   bash scripts/normalize_bg.sh <папка reaction-XX>
set -e
FFMPEG="${FFMPEG:-ffmpeg}"
FFPROBE="${FFPROBE:-ffprobe}"
D="${1:?usage: normalize_bg.sh <dir>}"
SRC="$D/src/bg_orig.mp4"
OUT="$D/src/bg.mp4"

# CROP можно задать руками, если cropdetect зацепил вотермарк: CROP="crop=720:480:0:405"
CROP="${CROP:-}"
[ -n "$CROP" ] || CROP=$("$FFMPEG" -hide_banner -ss 2 -t 6 -i "$SRC" -vf "cropdetect=limit=24:round=2:reset=0" -f null - 2>&1 \
       | grep -o "crop=[0-9:]*" | tail -1)
CROP="${CROP:-crop=iw:ih:0:0}"
CW=$(echo "$CROP" | cut -d= -f2 | cut -d: -f1)
CH=$(echo "$CROP" | cut -d= -f2 | cut -d: -f2)
# 1080/1920 = 0.5625; всё заметно шире — вписываем, а не режем
WIDE=$(echo "$CW $CH" | awk '{print ($1/$2 > 0.65) ? 1 : 0}')

if [ "$WIDE" = "1" ]; then
  echo "  $(basename "$D"): ${CW}x${CH} широкий → вписываю на размытый фон"
  VF="[0:v]$CROP,split=2[fg][bl];
      [bl]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=42,eq=brightness=-0.10:saturation=1.15[bgb];
      [fg]scale=1080:-2:flags=lanczos[fgs];
      [bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30[vout]"
else
  echo "  $(basename "$D"): ${CW}x${CH} вертикальный → scale+crop"
  VF="[0:v]$CROP,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[vout]"
fi

"$FFMPEG" -y -i "$SRC" -filter_complex "$VF" -map "[vout]" -map 0:a? \
  -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p -c:a aac -b:a 192k "$OUT" 2>&1 \
  | grep -iE "^\[.*error|No such" | head -3 || true
"$FFPROBE" -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$OUT"
