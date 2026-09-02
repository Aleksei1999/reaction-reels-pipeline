"""Транскрибирует full.wav во всех reaction-папках → audio/full_words.json (word-level)."""
import sys, json, os, pathlib, whisper

model_name = os.environ.get("WHISPER_MODEL", "small")
model = whisper.load_model(model_name)
for wav in sys.argv[1:]:
    wav = pathlib.Path(wav)
    out = wav.parent / "full_words.json"
    res = model.transcribe(str(wav), language="ru", word_timestamps=True, verbose=False)
    words = [{"s": round(w["start"], 2), "e": round(w["end"], 2), "w": w["word"].strip()}
             for seg in res["segments"] for w in seg.get("words", []) if w["end"] > w["start"]]
    segs = [{"s": round(s["start"], 2), "e": round(s["end"], 2), "t": s["text"].strip()}
            for s in res["segments"]]
    out.write_text(json.dumps({"words": words, "segments": segs}, ensure_ascii=False, indent=1))
    print(f"{wav.parent.parent.name}: {len(words)} слов, {len(segs)} сегментов -> {out}", flush=True)
