"""Whisper → JSON with word timestamps. Print to stdout."""
import sys, json, whisper
model = whisper.load_model('small')
res = model.transcribe(sys.argv[1], language='ru', word_timestamps=True, verbose=False)
words = []
for seg in res['segments']:
    for w in seg.get('words', []):
        if w['end'] > w['start']:
            words.append({'s': round(w['start'], 2), 'e': round(w['end'], 2), 'w': w['word'].strip()})
print(json.dumps({'words': words, 'duration': res.get('language', '')}, ensure_ascii=False))
