#!/usr/bin/env python3
"""みらい議会（チームみらい）のAIインタビュー回答データを全件取る（2026-10-08 作成）。

  /usr/bin/python3 scripts/fetch_mirai_gikai.py   → data/mirai_gikai/interviews.json

- API: https://gikai.team-mir.ai/api/open-data/interviews?agreeToTerms=true&limit=…&cursor=…
- データ出典：「みらい議会AIインタビュー（チームみらい）」 https://gikai.team-mir.ai/
  利用規約 https://gikai.team-mir.ai/developers/interview-data-terms ／ ライセンス CC BY 4.0
- 規約で禁じられていること: 回答者の再識別・それを目的とした照合、誹謗中傷、特定の個人・団体に不利益を与える使い方。
  使った成果物には上の出典・提供元URL・規約URL・ライセンスを書く。
- 1ページずつ2秒あけて取る（相手のサーバーに負担をかけない）。
"""
import json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "mirai_gikai", "interviews.json")
API = "https://gikai.team-mir.ai/api/open-data/interviews"


def main():
    items, cursor, n = [], "", 0
    while True:
        q = {"agreeToTerms": "true", "limit": "100"}
        if cursor:
            q["cursor"] = cursor
        d = json.load(urllib.request.urlopen(urllib.request.Request(API + "?" + urllib.parse.urlencode(q),
                                                                    headers={"User-Agent": "kronten/1.0 (https://kurage.exbridge.jp/kronten.php/)"}), timeout=90))
        items += d.get("items") or []
        n += 1
        cursor = d.get("nextCursor")
        print(f"\r{n}ページ {len(items)}件", end="", flush=True)
        if not cursor or not d.get("items"):
            break
        time.sleep(2)
    print()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"source": "みらい議会AIインタビュー（チームみらい）", "url": "https://gikai.team-mir.ai/",
               "terms": "https://gikai.team-mir.ai/developers/interview-data-terms", "license": "CC BY 4.0",
               "fetched_at": time.strftime("%Y-%m-%d %H:%M"), "items": items},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print("→", OUT)


if __name__ == "__main__":
    main()
