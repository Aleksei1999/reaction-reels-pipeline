"""Раскладывает scripts/plan.json по рабочим папкам: src/config.env + audio/hook.ass + src/render.sh.

plan.json на рилс:
  react_start/react_end/talk_start/talk_end — тайминги в person_full (сек)
  hook_src (react|talk), hook_abs — где в person_full звучит хук-фраза
  hook_dur, hook_bg_ss — длина хука и момент удара в bg
  hook — [[start, end, "ТЕКСТ"], ...] относительно начала хука
Координаты лица берутся из scripts/face_crop.py (кэш faces.json рядом с plan.json).
"""
import json, os, pathlib, shutil, sys

HOOK_HEADER = """[Script Info]
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

def ts(t):
    s = int(t); cs = int(round((t - s) * 100))
    if cs == 100: s += 1; cs = 0
    return f"0:00:{s:02d}.{cs:02d}"

def main():
    repo = pathlib.Path(__file__).resolve().parent.parent
    plan = json.loads((repo / "scripts/plan.json").read_text())
    faces = json.loads((repo / "scripts/faces.json").read_text())
    root = pathlib.Path(os.environ.get("REACTIONS_ROOT", os.path.expanduser("~/Desktop/монтаж/reactions")))

    for n, p in plan.items():
        d = root / f"reaction-{n}"
        f = faces[n]
        base = p["react_start"] if p["hook_src"] == "react" else p["talk_start"]
        hook_ss = round(p["hook_abs"] - base, 2)
        talk_dur = p["talk_end"] - p["talk_start"]

        # bg-вставки в длинный разбор: окно 4с каждые 9с, не трогая последние 2с
        cut, t = [], 6.0
        if talk_dur >= 20:
            while t + 4 <= talk_dur - 2:
                cut.append(f"{t:g}:{t+4:g}"); t += 9
        cfg = [
            f'CROP_BOX={f["box"]}', f'CROP_X={f["x"]}', f'CROP_Y={f["y"]}',
            f'TALK_CROP_X={f["tx"]}',
            f'HOOK_SRC={p["hook_src"]}', f'HOOK_SS={hook_ss}',
            f'HOOK_BG_SS={p["hook_bg_ss"]}', f'HOOK_DUR={p["hook_dur"]}',
            f'CUTAWAYS="{" ".join(cut)}"',
        ]
        (d / "src/config.env").write_text("\n".join(cfg) + "\n")

        ass = [HOOK_HEADER] + [
            f"Dialogue: 0,{ts(a)},{ts(b)},Default,,0,0,0,,{txt}" for a, b, txt in p["hook"]
        ]
        (d / "audio/hook.ass").write_text("\n".join(ass) + "\n")

        shutil.copy(repo / "templates/render.sh", d / "src/render.sh")
        (d / "src/render.sh").chmod(0o755)
        print(f"reaction-{n}: config.env + hook.ass + render.sh"
              f"{' + cutaways ' + str(len(cut)) if cut else ''}")

if __name__ == "__main__":
    main()
