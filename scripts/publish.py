#!/usr/bin/env python3
"""outputs/<slug>/map.json を kurage の公開ページにして送る（1接続）。

  .venv/bin/python scripts/publish.py            # data/maps.json に書いたテーマすべて
  .venv/bin/python scripts/publish.py --dry      # 書き出すだけ（outputs/_site/）

送り先: /web/kurage_exbridge_jp/kronten.php と /web/kurage_exbridge_jp/kronten_data/
  kronten_data/index.html・about.html・t_<slug>.html・maps/<slug>.json
地図の点（points）は JSON から落とす（MCP では使わない・重い）。
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kronten import report  # noqa: E402

SITE = os.path.join(ROOT, "outputs", "_site")


def env():
    e = {}
    for ln in open("/home/kojima/work/aixec/.env", encoding="utf-8"):
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.strip().split("=", 1)
            e[k] = v.strip('"\'')
    return e


def main():
    conf = json.load(open(os.path.join(ROOT, "data", "maps.json"), encoding="utf-8"))
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(os.path.join(SITE, "kronten_data", "maps"))
    maps = []
    for slug, c in conf.items():
        p = os.path.join(ROOT, "outputs", slug, "map.json")
        if not os.path.exists(p):
            print("  地図が無い:", slug)
            continue
        m = json.load(open(p, encoding="utf-8"))
        maps.append((slug, m))
        open(os.path.join(SITE, "kronten_data", f"t_{slug}.html"), "w", encoding="utf-8").write(
            report.render(m, slug=slug, links=c.get("links", [])))
        slim = {k: v for k, v in m.items() if k != "points"}
        json.dump(slim, open(os.path.join(SITE, "kronten_data", "maps", f"{slug}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(SITE, "kronten_data", "index.html"), "w", encoding="utf-8").write(report.render_index(maps))
    open(os.path.join(SITE, "kronten_data", "about.html"), "w", encoding="utf-8").write(report.render_about())
    shutil.copy(os.path.join(ROOT, "php", "kronten.php"), os.path.join(SITE, "kronten.php"))
    files = [os.path.relpath(os.path.join(d, f), SITE) for d, _, fs in os.walk(SITE) for f in fs]
    print("書き出し:", len(files), "ファイル →", SITE)
    if "--dry" in sys.argv:
        return
    e = env()
    # 1接続で送る: curl の -T を並べると同じ接続で順に送る
    args = ["curl", "-sS", "--ftp-create-dirs", "-u", f"{e['FTP_USER']}:{e['FTP_PASS']}"]
    for f in files:
        args += ["-T", os.path.join(SITE, f), f"ftp://{e['FTP_HOST']}/web/kurage_exbridge_jp/{f}"]
    r = subprocess.run(args, capture_output=True, text=True)
    print("送信", "OK" if r.returncode == 0 else "失敗 " + r.stderr[-300:], len(files), "ファイル（1接続）")


if __name__ == "__main__":
    main()
