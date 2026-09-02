"""Транскрибирует аудио через whisper с word-level timestamps
и генерирует ASS файл где каждое СЛОВО — отдельное событие."""
import sys, json, argparse
import whisper

def fmt_ts(t: float) -> str:
    h = int(t // 3600); t -= h*3600
    m = int(t // 60);   t -= m*60
    s = int(t); cs = int(round((t - s) * 100))
    if cs == 100: s += 1; cs = 0
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"

def build_ass(words, header):
    lines = [header, "[Events]",
             "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for w in words:
        start = fmt_ts(w["start"])
        end = fmt_ts(w["end"])
        text = w["word"].strip().replace(",", "").replace(".", "").replace("!", "").replace("?", "").upper()
        if not text: continue
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return "\n".join(lines) + "\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--out", required=True, help="ASS output path")
    p.add_argument("--style-header", required=True, help="path to ASS header (Script Info + V4+ Styles)")
    p.add_argument("--model", default="small")
    p.add_argument("--language", default="ru")
    args = p.parse_args()

    model = whisper.load_model(args.model)
    res = model.transcribe(args.audio, language=args.language, word_timestamps=True, verbose=False)

    words = []
    for seg in res["segments"]:
        for w in seg.get("words", []):
            if w["end"] > w["start"]:
                words.append(w)

    with open(args.style_header) as f:
        header = f.read()
    ass = build_ass(words, header)
    with open(args.out, "w") as f:
        f.write(ass)
    print(f"wrote {args.out}: {len(words)} words")

if __name__ == "__main__":
    main()
