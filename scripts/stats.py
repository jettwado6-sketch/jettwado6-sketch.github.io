#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アクセス解析（GoatCounter）を読んで、要約を表示します。

  python3 scripts/stats.py            直近30日
  python3 scripts/stats.py 7          直近7日
  python3 scripts/stats.py 2026-08-24 指定日から今日まで

APIトークンはリポジトリに置きません。次のファイルから読みます。
  ~/.config/kotani-portfolio/goatcounter.env
      GOATCOUNTER_SITE=yukikotani5
      GOATCOUNTER_TOKEN=（Settings → API tokens で発行したもの）

環境変数 GOATCOUNTER_TOKEN が設定されていれば、そちらが優先されます。
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

CONF = os.path.expanduser("~/.config/kotani-portfolio/goatcounter.env")


def load_conf():
    conf = {}
    if os.path.exists(CONF):
        for line in open(CONF, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip()
    site = os.environ.get("GOATCOUNTER_SITE") or conf.get("GOATCOUNTER_SITE")
    token = os.environ.get("GOATCOUNTER_TOKEN") or conf.get("GOATCOUNTER_TOKEN")
    if not site or not token:
        sys.exit(f"サイトコードかトークンが見つかりません。{CONF} を確認してください。")
    return site, token


def api(site, token, path, params=None):
    url = f"https://{site}.goatcounter.com/api/v0/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit(
                "認証に失敗しました（401）。\n"
                "  GoatCounter の Settings → API tokens でトークンを作り直し、\n"
                f"  {CONF} の GOATCOUNTER_TOKEN を差し替えてください。\n"
                "  ※ トークン作成時に統計の読み取り権限にチェックが要ります。")
        if e.code == 403:
            sys.exit("権限がありません（403）。トークンに統計の読み取り権限を付けてください。")
        sys.exit(f"APIエラー {e.code}: {e.read()[:200].decode('utf-8','replace')}")


def bar(n, mx, width=28):
    return "█" * max(1, round(n / mx * width)) if mx and n else ""


def section(title, rows, total=None):
    print(f"\n── {title} ──")
    if not rows:
        print("  （データなし）")
        return
    mx = max(r[1] for r in rows)
    for name, cnt in rows:
        pct = f" {cnt / total * 100:4.1f}%" if total else ""
        print(f"  {str(name)[:34]:34} {cnt:>5}{pct}  {bar(cnt, mx)}")


def main():
    site, token = load_conf()
    arg = sys.argv[1] if len(sys.argv) > 1 else "30"
    if arg.count("-") == 2:
        start = arg
    else:
        start = (date.today() - timedelta(days=int(arg))).isoformat()
    end = date.today().isoformat()
    rng = {"start": start, "end": end}

    print(f"═══ アクセス解析  {start} 〜 {end} ═══")

    total = api(site, token, "stats/total", rng)
    tv, tu = total.get("total", 0), total.get("total_unique", 0)
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days or 1
    print(f"\n  閲覧 {tv:,} 回 / 訪問者 {tu:,} 人   （1日あたり {tv/days:.1f} 回）")

    # 流入元 ── どこから来たかが、このサイトでは一番重要
    refs = api(site, token, "stats/toprefs", rng).get("stats", [])
    section("流入元", [(r.get("name") or "直接アクセス・不明", r["count"]) for r in refs[:12]], tv)

    # 端末・環境
    for path, label in [("stats/browsers", "ブラウザ"),
                        ("stats/systems", "OS"),
                        ("stats/locations", "地域")]:
        try:
            st = api(site, token, path, rng).get("stats", [])
            section(label, [(r.get("name") or "不明", r["count"]) for r in st[:6]], tv)
        except SystemExit:
            raise
        except Exception:
            pass

    print("\n  ※ Cookieを使わない計測のため、同一人物の再訪は完全には追えません。")
    print("     数字は「おおよその傾向」として読んでください。")


if __name__ == "__main__":
    main()
