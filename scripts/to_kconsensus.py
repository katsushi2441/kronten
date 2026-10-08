#!/usr/bin/env python3
"""論点AIマップで立てた論点を、Kurage 合意点マップ（kconsensus）の論点に渡す。

  .venv/bin/python scripts/to_kconsensus.py --map kodomo-sns --topic kodomo-sns          # 渡す候補を見るだけ
  .venv/bin/python scripts/to_kconsensus.py --map kodomo-sns --topic kodomo-sns --apply  # 書き込む

- 合意点マップにすでにある論点と意味が近いもの（埋め込みの近さが SIM 以上）は渡さない（同じ論点を2回押させない）。
- 渡した論点は source='kronten'。origin は、元の話題が国会の声中心なら diet、そうでなければ public。
- basis（根拠）に、話題の名前と論点AIマップのURLを入れる。
- 合意点マップの DB に書くと即本番。ネットの声への賛否の読み取りは、このあと kconsensus の
  scripts/import_reactions.py --slug <topic> で、まだ読んでいない組だけ読む。
"""
import argparse
import json
import os
import sqlite3
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from kronten import pipeline  # noqa: E402

KDB = "/home/kojima/work/kconsensus/data/kconsensus.sqlite"
SIM = 0.995  # 埋め込みでは「ほぼ同じ文」だけを落とす。e5 は数字の違い（13歳/16歳）を見分けられないので、
             # 同じ主張かどうかの判定は LLM に任せる（2026-10-08: 近さ0.93 で「13歳未満の禁止」が「16歳未満の禁止」の重複にされた）

CHECK = {"type": "object", "properties": {
    "policy": {"type": "boolean"}, "same_as": {"type": "integer"}, "reason": {"type": "string"}},
    "required": ["policy", "same_as", "reason"]}


def check(theme, cand, have):
    """LLM で2つを判定: テーマの政策として賛否を問える文か／既存の論点と同じ主張か（同じなら番号、違えば0）。"""
    lst = "\n".join(f"{i}. {t}" for i, t in enumerate(have, 1))
    prompt = (f"テーマ: {theme}\n\n既にある論点:\n{lst}\n\n新しい論点の候補: {cand}\n\n"
              "policy には、この候補がテーマについての政策や社会のルールとして、人が賛成か反対かを選べる文なら true、"
              "個別の事件や特定の職業の話でテーマから外れる、または賛否を選べない文なら false を入れます。\n"
              "same_as には、既にある論点のどれかと同じ主張なら、その番号を入れます。対象の年齢・範囲・手段が違えば別の主張です"
              "（例: 13歳未満の禁止と16歳未満の禁止は別）。同じものが無ければ 0 を入れます。\n"
              "reason には、判断の理由を30字以内で入れます。")
    body = json.dumps({"model": pipeline.LLM, "prompt": prompt, "stream": False, "format": CHECK, "think": False,
                       "options": {"temperature": 0, "num_predict": 200}}).encode()
    import urllib.request
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        pipeline.OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"}), timeout=600))
    try:
        return json.loads(r.get("response") or "{}")
    except json.JSONDecodeError:
        return {"policy": False, "same_as": 0, "reason": "判定できず"}
BASE = "https://kurage.exbridge.jp/kronten.php"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--topic", required=True, help="合意点マップの論点の slug")
    ap.add_argument("--max", type=int, default=6, help="一度に渡す論点の上限（押す側の負担を増やしすぎない）")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    m = json.load(open(os.path.join(ROOT, "outputs", a.map, "map.json"), encoding="utf-8"))
    con = sqlite3.connect(KDB)
    tid = con.execute("SELECT id FROM topic WHERE slug=?", (a.topic,)).fetchone()[0]
    have = [r[0] for r in con.execute("SELECT text FROM statement WHERE topic_id=?", (tid,))]
    cands = []
    for c in m["clusters"]:
        kokkai = sum(v for s, v in c["by_source"].items() if s.startswith("国会")) / c["size"]
        for p in c["propositions"]:
            cands.append({"text": p.rstrip("。"), "topic": c["name"], "size": c["size"],
                          "origin": "diet" if kokkai >= 0.6 else "public", "id": c["id"]})
    E = pipeline.embed([x["text"] for x in cands] + have)
    ce, he = E[:len(cands)], E[len(cands):]
    picked = []
    for i, x in enumerate(cands):
        near = float((he @ ce[i]).max()) if len(he) else 0
        dup_new = max([float(ce[j] @ ce[i]) for j in picked] or [0])
        x["near"] = round(near, 3)
        x["ok"] = near < SIM and dup_new < SIM
        if x["ok"]:
            # 既存＋ここまでに選んだ候補と比べて、LLM で判定する
            chk = check(m["theme"], x["text"], have + [cands[j]["text"] for j in picked])
            x["why"] = chk.get("reason", "")
            x["ok"] = bool(chk.get("policy")) and not chk.get("same_as")
            x["judge"] = "政策でない" if not chk.get("policy") else (f"{chk.get('same_as')}番と同じ" if chk.get("same_as") else "")
        if x["ok"]:
            picked.append(i)
    # 大きな話題の論点から順に、上限まで
    send = sorted([cands[i] for i in picked], key=lambda x: -x["size"])[:a.max]
    for x in cands:
        mark = "渡す" if x in send else ((x.get("judge") or "ほぼ同文") if not x["ok"] else "上限")
        print(f"  {mark} [{x['origin']}] {x['text']}（{x['topic']}・{x['size']}件）{('｜' + x['why']) if x.get('why') else ''}")
    if not a.apply:
        print(f"\n渡す候補 {len(send)}本（--apply で書き込む）")
        return
    with con:
        for x in send:
            con.execute("INSERT INTO statement (topic_id, text, origin, basis, source, created_at) "
                        "VALUES (?,?,?,?, 'kronten', datetime('now'))",
                        (tid, x["text"][:100], x["origin"],
                         f"論点AIマップの話題「{x['topic']}」（{x['size']}件）から {BASE}/t/{a.map}/#t{x['id']}"))
    print(f"\n{len(send)}本を合意点マップ「{a.topic}」に渡しました。次: kconsensus で import_reactions.py --slug {a.topic}")


if __name__ == "__main__":
    main()
