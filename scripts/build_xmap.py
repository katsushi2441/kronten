#!/usr/bin/env python3
"""Xの反応マップを作って公開する（1コマンド）。

  .venv/bin/python scripts/build_xmap.py https://x.com/<アカウント>/status/<番号>
  .venv/bin/python scripts/build_xmap.py <URL> --dry     # 作るだけ（outputs/x/）

→ https://kurage.exbridge.jp/kronten.php/x/<番号>（ページ・noindex）と .png（カード）
返信の集め方・載せないもの・限界は kronten/xmap.py の冒頭に書いた。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kronten import xcard, xmap  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "x")


def env():
    e = {}
    for ln in open("/home/kojima/work/aixec/.env", encoding="utf-8"):
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.strip().split("=", 1)
            e[k] = v.strip('"\'')
    return e


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    m = xmap.build(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, m["id"])
    json.dump(m, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    xcard.draw(m, base + ".png")
    open(base + ".html", "w", encoding="utf-8").write(xcard.page(m))
    print(f"返信 {m['n']}件（{m['sources']}）立場 {m['stance']}")
    for t in m["topics"]:
        print(f"  {t['name']}（{t['n']}件）{t['summary']}")
    if "--dry" in sys.argv:
        print("作った:", base + ".{json,png,html}")
        return 0
    e = env()
    u = f"ftp://{e['FTP_HOST']}/web/kurage_exbridge_jp"
    args = ["curl", "-sS", "--ftp-create-dirs", "-u", f"{e['FTP_USER']}:{e['FTP_PASS']}",
            "-T", base + ".html", f"{u}/kronten_data/x_{m['id']}.html",
            "-T", base + ".png", f"{u}/kronten_data/x_{m['id']}.png",
            "-T", os.path.join(ROOT, "php", "kronten.php"), f"{u}/kronten.php"]
    subprocess.run(args, check=True)
    print(f"公開: {xcard.BASE}/x/{m['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
