# reaction-reels-pipeline

FFmpeg + Whisper пайплайн для монтажа вертикальных reaction-рилсов (мото/авто-контент).
Каждый рил = **hook (2-3с чёрно-белый) → part1 (реакция на bg с лицом в круге + word-level субтитрами) → part2 (talking-head фуллскрин + субтитры + bg-cutaway вставки) → grunge-переходы на швах**.

## Что потребуется

- **ffmpeg** (`brew install ffmpeg` — с libx264, freetype, fontconfig, libass)
- **Python 3.10+** + `pip install -U openai-whisper yt-dlp`
- **Шрифт** `Gilroy ExtraBold` установить в систему (`~/Library/Fonts/` на macOS). Если нет — заменить в `templates/style_part1.ass` / `style_part2.ass` на любой heavy sans-serif (Impact, Anton, Montserrat Black и т.п.)
- **Grunge-переход mp4** — 3-5 сек чёрный overlay с плёночными шумами. Пример: [Vertical Vintage Grunge Transitions](https://www.google.com/search?q=vertical+vintage+grunge+transitions+overlay+mp4) — скачать 1 файл, положить путь в `TRANS` в `render.sh`.

## Структура рабочей папки

```
reaction-XX/
├── src/
│   ├── bg.mp4             # мото-видео (контент для реакции), 10-30с
│   ├── person_full.mov    # исходная запись с телефона (реакт + разбор)
│   ├── person_react.mov   # нарезка: только реакция (~= длительности bg)
│   ├── person_talk.mp4    # нарезка: talking-head разбор
│   ├── word_ass.py        # скопировать из scripts/
│   └── render.sh          # сгенерируется build_render.py или скопировать из templates/
├── audio/
│   ├── voice.wav          # extracted из person_react
│   ├── talk.wav           # extracted из person_talk
│   ├── style_part1.ass    # скопировать из templates/
│   ├── style_part2.ass    # скопировать из templates/
│   ├── subs_words.ass     # сгенерит word_ass.py по voice.wav
│   ├── talk_words.ass     # сгенерит word_ass.py по talk.wav
│   └── hook.ass           # руками: 2-3 хук-слова (см. пример в reaction-08 памяти)
└── out/
    ├── hook.mp4, part1.mp4, part2_clean.mp4, trans.mov
    └── reactionN_v1.mp4   # финалка
```

## Workflow (шаг за шагом)

**0. Скачать zip с контентом** — обычно zip содержит `bg.mp4` (мото) + `IMG_XXXX.MOV` (запись с камеры). Распаковать в `reaction-XX/src/`, переименовать `IMG_XXXX.MOV` → `person_full.mov`.

**1. Транскрибировать person_full → найти где реакт заканчивается и talk начинается:**
```bash
python3 scripts/whisper_json.py reaction-XX/src/person_full.mov > reaction-XX/audio/full_words.json
```

Правило: react ≈ длительности bg.mp4 (человек смотрит bg один раз). Talk = всё что после. Найти паузу >0.5с в транскрипте — там seam.

**2. Нарезать person_full → person_react.mov + person_talk.mp4:**
```bash
# React (short — same length as bg)
ffmpeg -ss <react_start> -i src/person_full.mov -t <react_dur> -c copy src/person_react.mov

# Talk (long — everything after)
ffmpeg -ss <talk_start> -i src/person_full.mov -t <talk_dur> \
  -c:v libx264 -crf 18 -preset veryfast -c:a aac -b:a 192k src/person_talk.mp4
```

**3. Извлечь аудио и сгенерить word-level субтитры:**
```bash
ffmpeg -y -i src/person_react.mov -vn -ac 1 -ar 16000 audio/voice.wav
ffmpeg -y -i src/person_talk.mp4  -vn -ac 1 -ar 16000 audio/talk.wav

cp templates/style_part1.ass templates/style_part2.ass audio/
cp scripts/word_ass.py src/

python3 src/word_ass.py audio/voice.wav --out audio/subs_words.ass --style-header audio/style_part1.ass
python3 src/word_ass.py audio/talk.wav  --out audio/talk_words.ass --style-header audio/style_part2.ass
```

**4. Написать `audio/hook.ass` вручную** — 2-3 punchy слова из voice.wav. Пример:
```
Dialogue: 0,0:00:00.00,0:00:00.68,Default,,0,0,0,,ПОСЛЕДНИЕ
Dialogue: 0,0:00:00.68,0:00:01.62,Default,,0,0,0,,СЕКУНДЫ\NМОТОЦИКЛИСТА
```

**5. Скопировать `render.sh`, отредактировать переменные:**
```bash
cp templates/render.sh src/render.sh
# Edit: HOOK_DUR, HOOK_REACT_SS (когда в react.mov звучат хук-слова),
#       HOOK_BG_SS (момент удара в bg для чёрно-белого),
#       crop=x:y (координаты лица для круга 500x500),
#       overlay enable windows для bg-cutaways во время talk.
```

**6. Собрать:**
```bash
bash src/render.sh
# → out/reactionN_v1.mp4
```

## Автогенератор render.sh

`scripts/build_render.py` умеет собирать render.sh для нескольких рилов сразу из dict-конфига (пример внутри). Полезно когда 5+ рилов подряд с одинаковой структурой.

## Правила и tips (из практики)

- **Face crop** обычно `w=500 h=500 x=670-750 y=30-150` (варьируется по кадру, подбираем в CapCut или fmpeg `select=eq(n,0)` → скриншот).
- **Hook** = 2-3 punchy слова из voice-транскрипта. Стандарт: интро («СМОТРИМ», «ДАВАЙ») ИЛИ панч-фраза («БЕЗУМНЫХ / 40 МЕТРОВ В ЧАС», «НЕ УМЕЕШЬ / ТОРМОЗИТЬ»). `HOOK_DUR = длительность_хук_слов + ~1с паддинга`.
- **BG-cutaways в talk** (если talk >30с): каждые 8-10с окно 3-5с fullscreen bg-вставка. Talk-аудио НЕ прерываем — только видеослой меняется. Реализовано через `-stream_loop -1 -i bg.mp4` + `overlay=enable='between(t,a1,b1)+between(t,a2,b2)+...'`.
- **Grunge-переход** на швах: `TRANS_DUR=0.5`, colorkey чёрный, overlay с `enable=between(...)`.
- **Rendering 2 рилов параллельно ОК** (через `bash render.sh &`). 3+ уже перегружает CPU.

## Готовые примеры

`examples/reaction-XX/` — пустой скелет папки. Скопируй → распакуй свой zip → следуй workflow.

## Автор

Aleksei Fomenko / Fomart
