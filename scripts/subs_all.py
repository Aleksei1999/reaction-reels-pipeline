"""Генерит word-level ASS для voice.wav/talk.wav во всех reaction-папках.
Модель одна на все файлы — грузится один раз (в отличие от word_ass.py на файл)."""
import os, sys, pathlib, whisper

MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
model = whisper.load_model(MODEL)
print(f"модель {MODEL} загружена", flush=True)

def fmt(t):
    h = int(t//3600); t -= h*3600
    m = int(t//60);   t -= m*60
    s = int(t); cs = int(round((t-s)*100))
    if cs == 100: s += 1; cs = 0
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"

for d in sys.argv[1:]:
    d = pathlib.Path(d)
    for wav, style, out in (("voice.wav", "style_part1.ass", "subs_words.ass"),
                            ("talk.wav",  "style_part2.ass", "talk_words.ass")):
        src = d/"audio"/wav
        if not src.exists(): continue
        res = model.transcribe(str(src), language="ru", word_timestamps=True, verbose=False)
        words = [w for seg in res["segments"] for w in seg.get("words", []) if w["end"] > w["start"]]
        lines = [(d/"audio"/style).read_text(), "[Events]",
                 "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
        for w in words:
            t = w["word"].strip().strip(",.!?…\"«»").upper()
            if not t: continue
            lines.append(f"Dialogue: 0,{fmt(w['start'])},{fmt(w['end'])},Default,,0,0,0,,{t}")
        (d/"audio"/out).write_text("\n".join(lines) + "\n")
        txt = " ".join(w["word"].strip() for w in words)
        print(f"{d.name}/{out}: {len(words)} слов | {txt[:110]}", flush=True)
