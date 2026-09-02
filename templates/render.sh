#!/bin/bash
# Сборка одного reaction-рилса. Все параметры — в src/config.env рядом.
# Порядок: hook (ч/б) → part1 (реакция на bg + лицо в круге) → part2 (разбор) + grunge на швах.
set -e
cd "$(dirname "$0")/.."
REPO="${REPO:-$HOME/reaction-reels-pipeline}"
FFMPEG="${FFMPEG:-ffmpeg}"      # нужен с libass: brew install ffmpeg-full
FFPROBE="${FFPROBE:-ffprobe}"
# шрифт берём из репозитория, а не из системы — тогда рендер повторяем на любой машине
FONTSDIR="${FONTSDIR:-$REPO/fonts}"

# ---- параметры рилса ----
[ -f src/config.env ] && . src/config.env

BG_SRC="${BG_SRC:-src/bg.mp4}"
TRANS="${TRANS:-$REPO/assets/grunge_trans.mov}"
TRANS_DUR="${TRANS_DUR:-0.5}"
TRANS_SRC_SS="${TRANS_SRC_SS:-0}"
CIRCLE="${CIRCLE:-500}"          # диаметр круга с лицом
CIRCLE_X="${CIRCLE_X:-30}"       # позиция круга в кадре
CIRCLE_Y="${CIRCLE_Y:-100}"
CROP_BOX="${CROP_BOX:-500}"      # квадрат вокруг лица в исходнике (scripts/face_crop.py)
CROP_X="${CROP_X:-690}"
CROP_Y="${CROP_Y:-150}"
TALK_CROP_X="${TALK_CROP_X:-}"   # пусто = по центру
HOOK_SRC="${HOOK_SRC:-react}"    # react | talk — откуда берём хук-фразу
HOOK_SS="${HOOK_SS:-0}"          # смещение внутри этого файла
HOOK_BG_SS="${HOOK_BG_SS:-0}"    # момент удара в bg для ч/б подложки
HOOK_DUR="${HOOK_DUR:-2.5}"
CUTAWAYS="${CUTAWAYS:-}"         # напр. "6:10 18:22" — окна bg-вставок в part2
VOICE_VOL="${VOICE_VOL:-1.6}"
BG_VOL="${BG_VOL:-0.15}"

REEL="${REEL:-$(basename "$PWD" | sed -E 's/^reaction-0*//')}"
OUT_FINAL="${OUT_FINAL:-out/reaction${REEL}_v1.mp4}"

CIRCLE_FILTER="crop=w=$CROP_BOX:h=$CROP_BOX:x=$CROP_X:y=$CROP_Y,scale=$CIRCLE:$CIRCLE,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(hypot(X-W/2,Y-H/2),W/2-4),255,0)'"
if [ -n "$TALK_CROP_X" ]; then TALK_X="$TALK_CROP_X"; else TALK_X="(iw-1080)/2"; fi

# ---------- PART 1: реакция на bg + лицо в круге + word-субтитры ----------
"$FFMPEG" -y -i "$BG_SRC" -i src/person_react.mov \
  -filter_complex "
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[bg];
    [1:v]$CIRCLE_FILTER[circle];
    [bg][circle]overlay=x=$CIRCLE_X:y=$CIRCLE_Y:shortest=1[vid];
    [vid]ass=f=audio/subs_words.ass:fontsdir=$FONTSDIR[vout];
    [1:a]volume=$VOICE_VOL[voice];
    [0:a]volume=$BG_VOL[music];
    [voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]
  " \
  -map "[vout]" -map "[aout]" -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest out/part1.mp4

# ---------- PART 2: разбор фуллскрин + субтитры (+ bg-вставки) ----------
if [ -n "$CUTAWAYS" ]; then
  ENABLE=""
  for w in $CUTAWAYS; do
    a="${w%%:*}"; b="${w##*:}"
    [ -n "$ENABLE" ] && ENABLE="$ENABLE+"
    ENABLE="${ENABLE}between(t,$a,$b)"
  done
  "$FFMPEG" -y -stream_loop -1 -i "$BG_SRC" -i src/person_talk.mp4 \
    -filter_complex "
      [1:v]scale=-1:1920,crop=1080:1920:x=$TALK_X:y=0,setsar=1,fps=30[talk];
      [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[bgf];
      [talk][bgf]overlay=enable='$ENABLE'[vmix];
      [vmix]ass=f=audio/talk_words.ass:fontsdir=$FONTSDIR[vfinal];
      [1:a]volume=$VOICE_VOL[aout]
    " \
    -map "[vfinal]" -map "[aout]" -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
    -c:a aac -b:a 192k -shortest out/part2_clean.mp4
else
  "$FFMPEG" -y -i src/person_talk.mp4 \
    -filter_complex "
      [0:v]scale=-1:1920,crop=1080:1920:x=$TALK_X:y=0,setsar=1,fps=30[talk];
      [talk]ass=f=audio/talk_words.ass:fontsdir=$FONTSDIR[vfinal];
      [0:a]volume=$VOICE_VOL[aout]
    " \
    -map "[vfinal]" -map "[aout]" -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
    -c:a aac -b:a 192k out/part2_clean.mp4
fi

# ---------- Grunge-переход → out/trans.mov (RGBA) ----------
if [ ! -f out/trans.mov ]; then
  if "$FFPROBE" -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 "$TRANS" | grep -qE "argb|rgba|yuva"; then
    "$FFMPEG" -y -t "$TRANS_DUR" -i "$TRANS" -c:v png out/trans.mov
  else
    "$FFMPEG" -y -ss "$TRANS_SRC_SS" -t "$TRANS_DUR" -i "$TRANS" \
      -filter_complex "[0:v]scale=1080:1920,fps=30,setsar=1,colorkey=color=0x000000:similarity=0.18:blend=0.05,format=yuva420p[vout]" \
      -map "[vout]" -c:v png out/trans.mov
  fi
fi

# ---------- HOOK: ч/б стоп-момент + панч-слова ----------
case "$HOOK_SRC" in
  talk) HOOK_FILE="src/person_talk.mp4" ;;
  *)    HOOK_FILE="src/person_react.mov" ;;
esac
"$FFMPEG" -y \
  -ss "$HOOK_BG_SS" -t "$HOOK_DUR" -i "$BG_SRC" \
  -ss "$HOOK_SS"    -t "$HOOK_DUR" -i "$HOOK_FILE" \
  -filter_complex "
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,hue=s=0,eq=contrast=1.1[bg_bw];
    [1:v]$CIRCLE_FILTER,hue=s=0[circle_bw];
    [bg_bw][circle_bw]overlay=x=$CIRCLE_X:y=$CIRCLE_Y[vid];
    [vid]ass=f=audio/hook.ass:fontsdir=$FONTSDIR[vout];
    [1:a]volume=2.0[aout]
  " \
  -map "[vout]" -map "[aout]" -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -t "$HOOK_DUR" out/hook.mp4

# ---------- ФИНАЛ: склейка + grunge на швах ----------
P1_DUR=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out/part1.mp4)
HOOK_END=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out/hook.mp4)
SEAM_P1=$(echo "$HOOK_END + $P1_DUR" | bc -l)

sr() { echo "$(echo "$1 - $TRANS_DUR/2" | bc -l) $(echo "$1 + $TRANS_DUR/2" | bc -l)"; }
read S1_S S1_E <<< "$(sr $HOOK_END)"
read S2_S S2_E <<< "$(sr $SEAM_P1)"

"$FFMPEG" -y \
  -i out/hook.mp4 -i out/part1.mp4 -i out/part2_clean.mp4 -i out/trans.mov -i out/trans.mov \
  -filter_complex "
    [0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[base_v][aout];
    [3:v]setpts=PTS-STARTPTS+${S1_S}/TB[t1];
    [4:v]setpts=PTS-STARTPTS+${S2_S}/TB[t2];
    [base_v][t1]overlay=x=0:y=0:eof_action=pass:enable='between(t,${S1_S},${S1_E})'[o1];
    [o1][t2]overlay=x=0:y=0:eof_action=pass:enable='between(t,${S2_S},${S2_E})'[vout]
  " \
  -map "[vout]" -map "[aout]" -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k "$OUT_FINAL"

echo "DONE $OUT_FINAL"
