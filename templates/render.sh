#!/bin/bash
# ЭТО ПРИМЕР — конкретно рабочий render.sh для reaction-08 (мото lane splitting).
# При копировании в новый reaction-XX/src/render.sh отредактируй:
#   - TRANS         : путь до grunge-transition mp4 (см. README)
#   - crop x/y      : координаты лица для круга 500x500 (подобрать по кадру)
#   - HOOK_DUR      : длительность хука (~= длине хук-слов + 1с)
#   - -ss в HOOK    : где в bg.mp4 момент удара, где в person_react.mov хук-слова
#   - имя финалки   : out/reactionN_v1.mp4
set -e
cd "$(dirname "$0")/.."

TRANS="/Users/aleksejfomenko/Downloads/vertical-vintage-grunge-transitions-overlay-old-retro-film-video.mp4"
BG_SRC="src/bg.mp4"
TRANS_DUR=0.5
TRANS_SRC_SS=3

# Face crop: face center ~(940, 400) → crop 500x500 x=690, y=150
# PART 1
ffmpeg -y \
  -i "$BG_SRC" \
  -i src/person_react.mov \
  -filter_complex "
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[bg];
    [1:v]crop=w=500:h=500:x=690:y=150,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(hypot(X-W/2,Y-H/2),W/2-4),255,0)'[circle];
    [bg][circle]overlay=x=30:y=100:shortest=1[vid];
    [vid]ass=audio/subs_words.ass[vout];
    [1:a]volume=1.6[voice];
    [0:a]volume=0.15[music];
    [voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]
  " \
  -map "[vout]" -map "[aout]" \
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -shortest \
  out/part1.mp4

# PART 2: без chunks (нет пауз >0.9с), просто talk + subtitles
ffmpeg -y \
  -i src/person_talk.mp4 \
  -filter_complex "
    [0:v]scale=-1:1920,crop=1080:1920:x=(iw-1080)/2:y=0,setsar=1,fps=30[vout];
    [vout]ass=audio/talk_words.ass[vfinal];
    [0:a]volume=1.6[aout]
  " \
  -map "[vfinal]" -map "[aout]" \
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k \
  out/part2_clean.mp4

# Grunge
if [ ! -f out/trans.mov ]; then
  ffmpeg -y -ss "$TRANS_SRC_SS" -t "$TRANS_DUR" -i "$TRANS" \
    -filter_complex "[0:v]scale=1080:1920,drawbox=x=0:y=680:w=iw:h=420:color=black:t=fill,fps=30,setsar=1,colorkey=color=0x000000:similarity=0.18:blend=0.05,format=yuva420p[vout]" \
    -map "[vout]" -c:v qtrle out/trans.mov
fi

# HOOK: "БЕЗУМНЫХ / 40 МЕТРОВ В ЧАС" (voice ~10.04-11.72 → hook 0.04-1.72, ss=10) + bg 6-9 ч/б
HOOK_DUR=2.5
ffmpeg -y \
  -ss 7 -t "$HOOK_DUR" -i "$BG_SRC" \
  -ss 10 -t "$HOOK_DUR" -i src/person_react.mov \
  -filter_complex "
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,hue=s=0,eq=contrast=1.1[bg_bw];
    [1:v]crop=w=500:h=500:x=690:y=150,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(hypot(X-W/2,Y-H/2),W/2-4),255,0)',hue=s=0[circle_bw];
    [bg_bw][circle_bw]overlay=x=30:y=100[vid];
    [vid]ass=audio/hook.ass[vout];
    [1:a]volume=2.0[aout]
  " \
  -map "[vout]" -map "[aout]" \
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k \
  -t "$HOOK_DUR" out/hook.mp4

# ФИНАЛ
P1_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out/part1.mp4)
HOOK_END=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out/hook.mp4)
SEAM_H=$HOOK_END
SEAM_P1=$(echo "$HOOK_END + $P1_DUR" | bc -l)

sr() { echo "$(echo "$1 - $TRANS_DUR/2" | bc -l) $(echo "$1 + $TRANS_DUR/2" | bc -l)"; }
read S1_S S1_E <<< "$(sr $SEAM_H)"
read S2_S S2_E <<< "$(sr $SEAM_P1)"

ffmpeg -y \
  -i out/hook.mp4 -i out/part1.mp4 -i out/part2_clean.mp4 \
  -i out/trans.mov -i out/trans.mov \
  -filter_complex "
    [0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[base_v][aout];
    [3:v]setpts=PTS-STARTPTS+${S1_S}/TB[t1];
    [4:v]setpts=PTS-STARTPTS+${S2_S}/TB[t2];
    [base_v][t1]overlay=x=0:y=0:eof_action=pass:enable='between(t,${S1_S},${S1_E})'[o1];
    [o1][t2]overlay=x=0:y=0:eof_action=pass:enable='between(t,${S2_S},${S2_E})'[vout]
  " \
  -map "[vout]" -map "[aout]" \
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k \
  out/reaction8_v1.mp4

echo "DONE reaction8_v1.mp4"
