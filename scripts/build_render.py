"""Generate render.sh for a reaction folder with hook + cutaways."""
import sys, os, textwrap

def build_hook_ass(hook_words, path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Gilroy ExtraBold,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def fmt(t):
        s=int(t); cs=int(round((t-s)*100))
        if cs==100: s+=1; cs=0
        return f"0:00:{s:02d}.{cs:02d}"
    lines = [header]
    for start, end, text in hook_words:
        lines.append(f"Dialogue: 0,{fmt(start)},{fmt(end)},Default,,0,0,0,,{text}")
    open(path,'w').write('\n'.join(lines) + '\n')

def build_render_sh(n, hook_react_ss, hook_bg_ss, hook_dur, talk_dur, cutaway_step=9, cutaway_len=4, crop_x=690, crop_y=120):
    # Cutaway windows: start at 6, every step, len len; skip if beyond talk_dur-2
    windows = []
    t = 6
    while t + cutaway_len <= talk_dur - 2:
        windows.append((t, t + cutaway_len))
        t += cutaway_step
    overlay_enable = '+'.join(f"between(t,{a},{b})" for a,b in windows) or "0"
    script = f'''#!/bin/bash
set -e
cd "$(dirname "$0")/.."
REPO="${{REPO:-$HOME/reaction-reels-pipeline}}"

FFMPEG="${{FFMPEG:-ffmpeg}}"
FFPROBE="${{FFPROBE:-ffprobe}}"
TRANS="${{TRANS:-$REPO/assets/grunge_trans.mov}}"
BG_SRC="src/bg.mp4"
TRANS_DUR=0.5
TRANS_SRC_SS=3
HOOK_DUR={hook_dur}
HOOK_REACT_SS={hook_react_ss}
HOOK_BG_SS={hook_bg_ss}

# PART 1: react + bg + subs + face circle
"$FFMPEG" -y \\
  -i "$BG_SRC" \\
  -i src/person_react.mov \\
  -filter_complex "
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[bg];
    [1:v]crop=w=500:h=500:x={crop_x}:y={crop_y},format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(hypot(X-W/2,Y-H/2),W/2-4),255,0)'[circle];
    [bg][circle]overlay=x=30:y=100:shortest=1[vid];
    [vid]ass=audio/subs_words.ass[vout];
    [1:a]volume=1.6[voice];
    [0:a]volume=0.15[music];
    [voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]
  " \\
  -map "[vout]" -map "[aout]" \\
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \\
  -c:a aac -b:a 192k \\
  -shortest \\
  out/part1.mp4

# PART 2: talk + subs + fullscreen bg cutaways (windows: {windows})
"$FFMPEG" -y \\
  -stream_loop -1 -i "$BG_SRC" \\
  -i src/person_talk.mp4 \\
  -filter_complex "
    [1:v]scale=-1:1920,crop=1080:1920:x=(iw-1080)/2:y=0,setsar=1,fps=30[talk];
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[bgf];
    [talk][bgf]overlay=enable='{overlay_enable}'[vmix];
    [vmix]ass=audio/talk_words.ass[vfinal];
    [1:a]volume=1.6[aout]
  " \\
  -map "[vfinal]" -map "[aout]" \\
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k \\
  -shortest \\
  out/part2_clean.mp4

# Grunge-переход → out/trans.mov (RGBA)
# Если TRANS уже с альфой (наш assets/grunge_trans.mov) — просто подрезаем.
# Если это обычный mp4-футаж на чёрном — выбиваем чёрный через colorkey.
if [ ! -f out/trans.mov ]; then
  if "$FFPROBE" -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 "$TRANS" | grep -qE "argb|rgba|yuva"; then
    "$FFMPEG" -y -t "$TRANS_DUR" -i "$TRANS" -c:v png out/trans.mov
  else
    "$FFMPEG" -y -ss "$TRANS_SRC_SS" -t "$TRANS_DUR" -i "$TRANS" \
      -filter_complex "[0:v]scale=1080:1920,fps=30,setsar=1,colorkey=color=0x000000:similarity=0.18:blend=0.05,format=yuva420p[vout]" \
      -map "[vout]" -c:v png out/trans.mov
  fi
fi

# HOOK: b&w bg + b&w face + hook.ass
"$FFMPEG" -y \\
  -ss "$HOOK_BG_SS" -t "$HOOK_DUR" -i "$BG_SRC" \\
  -ss "$HOOK_REACT_SS" -t "$HOOK_DUR" -i src/person_react.mov \\
  -filter_complex "
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,hue=s=0,eq=contrast=1.1[bg_bw];
    [1:v]crop=w=500:h=500:x={crop_x}:y={crop_y},format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lt(hypot(X-W/2,Y-H/2),W/2-4),255,0)',hue=s=0[circle_bw];
    [bg_bw][circle_bw]overlay=x=30:y=100[vid];
    [vid]ass=audio/hook.ass[vout];
    [1:a]volume=2.0[aout]
  " \\
  -map "[vout]" -map "[aout]" \\
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k \\
  -t "$HOOK_DUR" out/hook.mp4

# FINAL
P1_DUR=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out/part1.mp4)
HOOK_END=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 out/hook.mp4)
SEAM_H=$HOOK_END
SEAM_P1=$(echo "$HOOK_END + $P1_DUR" | bc -l)

sr() {{ echo "$(echo "$1 - $TRANS_DUR/2" | bc -l) $(echo "$1 + $TRANS_DUR/2" | bc -l)"; }}
read S1_S S1_E <<< "$(sr $SEAM_H)"
read S2_S S2_E <<< "$(sr $SEAM_P1)"

"$FFMPEG" -y \\
  -i out/hook.mp4 -i out/part1.mp4 -i out/part2_clean.mp4 \\
  -i out/trans.mov -i out/trans.mov \\
  -filter_complex "
    [0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[base_v][aout];
    [3:v]setpts=PTS-STARTPTS+${{S1_S}}/TB[t1];
    [4:v]setpts=PTS-STARTPTS+${{S2_S}}/TB[t2];
    [base_v][t1]overlay=x=0:y=0:eof_action=pass:enable='between(t,${{S1_S}},${{S1_E}})'[o1];
    [o1][t2]overlay=x=0:y=0:eof_action=pass:enable='between(t,${{S2_S}},${{S2_E}})'[vout]
  " \\
  -map "[vout]" -map "[aout]" \\
  -r 30 -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k \\
  out/reaction{n}_v1.mp4

echo "DONE reaction{n}_v1.mp4"
'''
    return script

REACTIONS = {
    12: {
        'hook_words': [(0.00, 0.68, "ПОСЛЕДНИЕ"), (0.68, 1.62, "СЕКУНДЫ\\NМОТОЦИКЛИСТА")],
        'hook_react_ss': 0.30, 'hook_bg_ss': 8, 'hook_dur': 2.0, 'talk_dur': 203,
    },
    13: {
        'hook_words': [(0.00, 0.44, "ЖЁЛКО"), (0.58, 0.86, "ПАЦАНА")],
        'hook_react_ss': 8.02, 'hook_bg_ss': 13, 'hook_dur': 2.0, 'talk_dur': 34,
    },
    14: {
        'hook_words': [(0.00, 0.48, "ДЕВОЧКА"), (0.48, 1.20, "ЗАКЛАДЫВАЕТ\\NРУЛЬ")],
        'hook_react_ss': 4.72, 'hook_bg_ss': 9, 'hook_dur': 2.0, 'talk_dur': 28,
    },
}

for n, c in REACTIONS.items():
    base = os.environ.get('REACTIONS_ROOT', os.path.expanduser('~/Desktop/монтаж/reactions')) + f'/reaction-{n}'
    build_hook_ass(c['hook_words'], f'{base}/audio/hook.ass')
    script = build_render_sh(n, c['hook_react_ss'], c['hook_bg_ss'], c['hook_dur'], c['talk_dur'])
    open(f'{base}/src/render.sh','w').write(script)
    os.chmod(f'{base}/src/render.sh', 0o755)
    print(f'reaction-{n}: render.sh + hook.ass written')
