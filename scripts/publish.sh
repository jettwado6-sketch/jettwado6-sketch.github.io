#!/bin/bash
# data/ を書き換えたあと、これを実行すればサイトに反映されます。
#   ./scripts/publish.sh              → 「サイト更新」というメモで反映
#   ./scripts/publish.sh "9月の説明会" → メモを自分で書く
#
# git の順番（コミット→取り込み→push）を間違えると弾かれるので、
# ここでまとめて面倒を見ています。

set -euo pipefail
cd "$(dirname "$0")/.."

# JSON が壊れていたら反映しない（壊れたまま公開されるのを防ぐ）
for f in data/*.json; do
  python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$f" \
    || { echo "❌ $f の書式が壊れています。カンマや括弧を確認してください。"; exit 1; }
done

git add -A
if git diff --cached --quiet; then
  echo "変更はありませんでした。"
  exit 0
fi

echo "── 変更されたファイル ──"
git diff --cached --name-only | sed 's/^/  /'

git commit -qm "${1:-サイト更新}"
git pull --rebase --autostash -q origin main   # 自動更新のコミットを先に取り込む
git push -q origin main

echo
echo "✅ 反映しました。1〜2分で https://yukikotani5.github.io/ に出ます。"
echo "   進行状況: https://github.com/yukikotani5/yukikotani5.github.io/actions"
