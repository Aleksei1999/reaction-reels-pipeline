# reaction-XX example folder

Скелет папки одного рила. Пустые `src/audio/out/` — сюда положишь и сгенеришь всё по workflow из корневого README.md.

## Быстрый чек-лист

- [ ] `src/bg.mp4` — контент-видео (мото и т.п.)
- [ ] `src/person_full.mov` — исходник с телефона
- [ ] `src/person_react.mov`, `src/person_talk.mp4` — нарезано
- [ ] `audio/voice.wav`, `audio/talk.wav` — extracted
- [ ] `audio/style_part1.ass`, `audio/style_part2.ass` — скопированы из templates
- [ ] `audio/subs_words.ass`, `audio/talk_words.ass` — сгенерены word_ass.py
- [ ] `audio/hook.ass` — вручную 2-3 хук-слова
- [ ] `src/word_ass.py` — скопировать из scripts
- [ ] `src/render.sh` — скопировать из templates и отредактировать переменные
- [ ] `bash src/render.sh` → `out/reactionN_v1.mp4`
