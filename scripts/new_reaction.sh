#!/bin/bash
# Создаёт рабочую папку рилса: bash scripts/new_reaction.sh 01 [ROOT]
set -e
cd "$(dirname "$0")/.."
REPO="$(pwd)"
N="${1:?usage: new_reaction.sh <NN> [root]}"
ROOT="${2:-$HOME/Desktop/монтаж/reactions}"
DIR="$ROOT/reaction-$N"
mkdir -p "$DIR"/{src,audio,out}
cp templates/style_part1.ass templates/style_part2.ass "$DIR/audio/"
cp scripts/word_ass.py "$DIR/src/"
cp templates/render.sh "$DIR/src/render.sh"
chmod +x "$DIR/src/render.sh"
echo "$DIR готова. Клади src/bg.mp4 и src/person_full.mov"
