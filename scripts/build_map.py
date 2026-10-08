#!/usr/bin/env python3
"""論点AIマップを1つ作る。

  .venv/bin/python scripts/build_map.py --slug kodomo-sns --tracker kodomo-sns --reactions kodomo-sns
  .venv/bin/python scripts/build_map.py --slug mydata --theme "テーマ名" --csv data/opinions.csv

→ outputs/<slug>/map.json と map.html
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kronten import pipeline, report, sources  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--theme", default="")
    ap.add_argument("--tracker", help="xb4g 国会トラッカーの key")
    ap.add_argument("--reactions", help="kconsensus の論点 slug（ネットの声）")
    ap.add_argument("--csv", help="任意の CSV（text 列・attribute_* 列）")
    ap.add_argument("--k", type=int, default=0)
    a = ap.parse_args()
    items, theme = [], a.theme
    if a.tracker:
        name, its = sources.load_tracker(a.tracker)
        theme = theme or name
        items += its
        print(f"国会の発言（テーマの語を含むかたまり）: {len(its)}")
    if a.reactions:
        its = sources.load_reactions(a.reactions)
        items += its
        print(f"ネットの声: {len(its)}")
    if a.csv:
        its = sources.load_csv(a.csv)
        items += its
        print(f"CSV: {len(its)}")
    if not items:
        raise SystemExit("材料がありません")
    t0 = time.time()
    out = os.path.join(ROOT, "outputs", a.slug)
    m = pipeline.build(theme, items, k=a.k or None, cache=os.path.join(out, "embeddings.npy"))
    m["built_at"] = time.strftime("%Y-%m-%d %H:%M")
    os.makedirs(out, exist_ok=True)
    json.dump(m, open(os.path.join(out, "map.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(out, "map.html"), "w", encoding="utf-8").write(report.render(m))
    print(f"→ {out}/map.json・map.html（{len(items)}件・{m['k']}のまとまり・{time.time() - t0:.0f}秒）")


if __name__ == "__main__":
    main()
