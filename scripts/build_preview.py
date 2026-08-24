#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プレビュー用の1ファイルHTMLを作る。

index.html は data/*.json を fetch して動くため、サーバーが必要です。
このスクリプトは CSS・JS・JSON・画像をすべて1枚のHTMLに埋め込むので、
ファイルをダブルクリックするだけで開けます（共有・確認用）。

  python3 scripts/build_preview.py  →  preview.html

※ 本番サイトは index.html の方です。こちらは中身が固定されるので自動更新されません。
"""

import base64
import json
import mimetypes
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "kotani-portfolio-preview/1.0"


def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()


def data_uri_from_file(p):
    full = os.path.join(ROOT, p)
    if not os.path.exists(full):
        return None
    mime = mimetypes.guess_type(full)[0] or "image/jpeg"
    with open(full, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def data_uri_from_url(url):
    """外部画像を取り込む（Artifact は外部ホストへの通信が遮断されるため）"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            blob = r.read()
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return f"data:{mime};base64," + base64.b64encode(blob).decode()
    except Exception as e:                                        # noqa: BLE001
        print(f"    画像を取得できませんでした（スキップ）: {url} … {e}", file=sys.stderr)
        return None


def main():
    html = read("index.html")
    css = read("assets/style.css")
    js = read("assets/app.js")

    bundle = {}
    for key, path in [("profile", "data/profile.json"),
                      ("publications", "data/publications.json"),
                      ("feeds", "data/feeds.json"),
                      ("media", "data/media.json"),
                      ("writings", "data/writings.json"),
                      ("talks", "data/talks.json"),
                      ("news", "data/news.json")]:
        bundle[key] = json.loads(read(path))

    # 画像をすべて data URI に置き換える
    print("  画像を埋め込み中 …")
    photo = data_uri_from_file(bundle["profile"].get("photo", "assets/profile.jpg"))
    if photo:
        bundle["profile"]["photo"] = photo

    # 発信カードのサムネイル（YouTube / note）
    for channel in bundle["feeds"].values():
        if not isinstance(channel, dict):
            continue
        for card in channel.values():
            if isinstance(card, dict) and card.get("thumbnail"):
                card["thumbnail"] = data_uri_from_url(card["thumbnail"])
    # 取材記事の画像
    for it in bundle["media"].get("items", []):
        if it.get("image"):
            it["image"] = data_uri_from_url(it["image"])

    # fetch() を埋め込みデータの参照に差し替える
    inline_js = js.replace(
        'const jget = (p) => fetch(p, { cache: "no-cache" })\n'
        '  .then((r) => { if (!r.ok) throw new Error(`${p}: ${r.status}`); return r.json(); });',
        "const jget = (p) => Promise.resolve(\n"
        "  window.__DATA__[p.replace('data/', '').replace('.json', '')]);"
    )
    if "window.__DATA__" not in inline_js:
        sys.exit("エラー: app.js の jget を置換できませんでした（app.js の書き換え後は "
                 "build_preview.py の置換文字列も合わせてください）")

    head_inject = (
        "<style>\n" + css + "\n</style>\n"
        "<script>window.__DATA__ = " +
        json.dumps(bundle, ensure_ascii=False) + ";</script>\n"
    )

    out = html
    # index.html 側はキャッシュ対策で ?v=… が付くため、正規表現で受ける
    out = re.sub(r'<link rel="stylesheet" href="assets/style\.css[^"]*">', lambda m: head_inject, out, count=1)
    out = re.sub(r'<script src="assets/app\.js[^"]*"></script>',
                 lambda m: "<script>\n" + inline_js + "\n</script>", out, count=1)
    out = re.sub(r'<img class="hero-photo" id="heroPhoto" src="[^"]*"',
                 f'<img class="hero-photo" id="heroPhoto" src="{photo or ""}"', out)
    # OGP の相対画像は1ファイル配布では意味がないので落とす
    out = re.sub(r'\s*<meta property="og:image"[^>]*>', "", out)
    # プレビューはタブ名として短い名前にする（本番 index.html は検索向けの長い title のまま）
    out = re.sub(r"<title>.*?</title>", "<title>小谷祐樹 ポートフォリオ</title>", out, count=1)

    dest = os.path.join(ROOT, "preview.html")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  → preview.html ({os.path.getsize(dest) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
