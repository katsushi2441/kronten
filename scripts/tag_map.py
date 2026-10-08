#!/usr/bin/env python3
"""地図の声に網目状の論点を付け、論点ごと・出どころごとの割合を map.json に足す（2026-10-08 作成）。

  .venv/bin/python scripts/tag_map.py --slug kodomo-sns     # outputs/<slug>/taxonomy.json の論点で判定
→ outputs/<slug>/tags.json（声ごとの論点）と map.json の "mesh"
"""
import argparse, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kronten import report, sources, taxonomy  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--batch", type=int, default=10)
    a = ap.parse_args()
    conf = json.load(open(os.path.join(ROOT, "data", "maps.json"), encoding="utf-8"))[a.slug]
    items = []
    if conf.get("tracker"):
        items += sources.load_tracker(conf["tracker"])[1]
    if conf.get("reactions"):
        items += sources.load_reactions(conf["reactions"])
    if conf.get("mirai"):
        items += sources.load_mirai(conf["mirai"])
    out = os.path.join(ROOT, "outputs", a.slug)
    labels = json.load(open(os.path.join(out, "taxonomy.json"), encoding="utf-8"))["labels"]
    tp = os.path.join(out, "tags.json")
    done = json.load(open(tp, encoding="utf-8")) if os.path.exists(tp) else {}
    t0 = time.time()
    todo = [it for it in items if it["id"] not in done]
    for i in range(0, len(todo), a.batch):
        chunk = todo[i:i + a.batch]
        for it, tg in zip(chunk, taxonomy.tag_batch(labels, [x["text"] for x in chunk])):
            done[it["id"]] = tg
        json.dump(done, open(tp, "w", encoding="utf-8"))
        print(f"\r{min(i + a.batch, len(todo))}/{len(todo)} {time.time() - t0:.0f}秒", end="", flush=True)
    print()
    tags = [done.get(it["id"], []) for it in items]
    mp = os.path.join(out, "map.json")
    m = json.load(open(mp, encoding="utf-8"))
    m["mesh"] = taxonomy.stats(labels, items, tags, report.group_of)
    json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({r["name"]: {g: v["pct"] for g, v in r["by_group"].items()} for r in m["mesh"]["rows"]}, ensure_ascii=False, indent=0))
    print("2つ以上の論点に当たる声", m["mesh"]["multi"], "% ／ どれにも当たらない声", m["mesh"]["none"], "%")


if __name__ == "__main__":
    main()
